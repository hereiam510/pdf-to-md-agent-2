"""On-demand catalog facts. No task initialization, execution or recovery writes.

Navigation owns short-lived private SQLite copies, not a durable projection.
The source is read as files (including WAL); SQLite opens only the copies.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager, closing, nullcontext
from hashlib import sha256
import hmac
import json
from pathlib import Path
import re
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import threading
import time

from .evidence import Evidence
from .recovery import ReadView, diagnostic_facts, ro_connect, verify_version
from .storage import encode
from .streaming import StreamDecoder, StreamError
from .usage import interpret_usage


KINDS = {"request", "operation", "version", "context_commit", "context_disposition",
         "context_policy", "conflict_resolution", "event_receipt", "blob"}
NAMES = ("catalog.sqlite", "catalog.sqlite-wal", "catalog.sqlite-journal")
SUMMARY_FIELDS = ("status", "tool", "claim", "parent", "kind", "reason", "request", "receipt_ref", "proposal_ref")
AVAILABLE = "available; integrity checked, acceptance not inferred"


def record_summary(data, kind):
    """Validate only the shapes consumed by this list, not a domain schema."""
    if not isinstance(data, dict):
        raise ValueError("Record JSON root must be an object.")
    for field in SUMMARY_FIELDS:
        if field in data and data[field] is not None and not isinstance(data[field], str):
            raise ValueError(f"Summary field {field} must be a string or null when present.")
    item = {field: data[field] for field in SUMMARY_FIELDS if field in data}
    if kind == "request":
        attempts = data.get("attempts")
        if not isinstance(attempts, list) or any(not isinstance(aid, str) or not aid for aid in attempts):
            raise ValueError("Request attempts must be a recorded list of attempt identities.")
        item["attempts"] = len(attempts)
    return item


def artifact_facts(view, job, ref, request=None, *, request_key=None, descriptor=None):
    """Factual ownership and retained call shape, never acceptance eligibility.

    Both evidence links and call joins use this rule. Published pointers cannot
    redirect canonical staging, even when equal bytes or a valid alias exist.
    No native parsing, stream reconstruction, settlement or graph read occurs.
    """
    if not isinstance(ref, str) or not ref:
        raise ValueError("Artifact reference must be a non-empty string.")
    blob = view.get("blob", ref, job=job) if descriptor is None else descriptor
    if not isinstance(blob, dict) or blob.get("ref") != ref or blob.get("job") != job:
        raise ValueError("Descriptor identity/ownership mismatch.")
    if not isinstance(blob.get("meta"), dict) or not isinstance(blob.get("kind"), str):
        raise ValueError("Descriptor metadata/kind has an unsupported shape.")
    facts = {"kind": blob["kind"], "bytes": blob["bytes"], "meta": blob["meta"]}
    if request is not None:
        key = request_key if request_key is not None else request.get("id")
        if not isinstance(key, str) or request.get("id") != key or request.get("job") != job:
            raise ValueError("Selected request identity/task is inconsistent.")
        record_summary(request, "request")
        owner = blob["meta"].get("attempt")
        if (not isinstance(owner, str) or blob["meta"].get("request") != key
                or request["attempts"].count(owner) != 1):
            raise ValueError("Artifact request/attempt ownership is unconfirmed.")
        attempt = view.get("attempt", owner, job=job)
        if not isinstance(attempt, dict) or attempt.get("request") != key or attempt.get("id") != owner:
            raise ValueError("Retained attempt disagrees with artifact ownership.")
        facts.update(request=key, attempt=owner,
                     relation="latest_attempt" if owner == request["attempts"][-1] else "earlier_attempt")
        if blob["kind"] == "accepted_response" or ref == request.get("accepted_ref") or ref == f"accepted:{key}":
            if blob["kind"] != "accepted_response":
                raise ValueError("Accepted artifact kind mismatch.")
            if ref != f"accepted:{key}" or request.get("accepted_ref") not in (None, ref):
                raise ValueError("Published pointer and canonical staging identity disagree.")
            accepted = view.json(ref, job)  # also checks the exact retained bytes
            if not isinstance(accepted, dict) or not isinstance(accepted.get("calls"), list):
                raise ValueError("Retained response must be an object with a calls list.")
            for call in accepted["calls"]:
                if not isinstance(call, dict) or any(not isinstance(call.get(field), str) for field in ("id", "name", "arguments")):
                    raise ValueError("Retained call identity/name/arguments have an unsupported shape.")
            facts["publication"] = "published" if request.get("accepted_ref") else "unpublished"
            return facts, accepted
    view.bytes(ref, job)
    return facts, None


class Unavailable(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class CatalogView(ReadView):
    def bytes(self, ref, job):
        record = self.get("blob", ref, job=job)
        if (record.get("ref") != ref or record.get("job") != job
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", "")))):
            raise ValueError("Evidence identity/digest is inconsistent.")
        if not (self.root / "objects" / record["sha256"]).resolve().is_relative_to((self.root / "objects").resolve()):
            raise ValueError("Evidence object is outside this store.")
        return super().bytes(ref, job)


def identity(root):
    result = {}
    for name in NAMES:
        try:
            st = (root / name).stat()
            if name.endswith(".sqlite") or st.st_size:
                result[name] = (st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)
        except FileNotFoundError:
            pass
    if "catalog.sqlite" not in result:
        raise Unavailable("unavailable", "No catalog exists. Inspection creates nothing in the task store.")
    return result


def copy_catalog(root, target):
    """Two bounded file passes; never open source SQLite or copy graph/SHM."""
    before = identity(root)
    if before.get("catalog.sqlite-journal", (0,))[0]:
        raise Unavailable("stale", "An unresolved rollback journal prevents a stable catalog read.")
    deadline = time.monotonic() + 5
    hashes = []
    for writing in (True, False):
        current = {}
        for name in before:
            digest = sha256()
            with (root / name).open("rb") as source:
                with (target / name).open("wb") if writing else nullcontext() as output:
                    while part := source.read(1024 * 1024):
                        if time.monotonic() > deadline:
                            raise Unavailable("unavailable", "Catalog capture exceeded its read window. Refresh when quieter.")
                        digest.update(part)
                        if writing:
                            output.write(part)
            current[name] = digest.hexdigest()
        hashes.append(current)
        if identity(root) != before:
            raise Unavailable("stale", "Catalog changed during capture. Refresh for a new view.")
    if hashes[0] != hashes[1]:
        raise Unavailable("stale", "Catalog bytes changed during capture. Refresh for a new view.")
    return before


class Diagnostics:
    """Process-local read sessions expire after 15 minutes; at most eight copies.

    The token is task-bound. Signed page cursors also bind kind, direction,
    anchor and page size. Shutdown/close/expiry removes private temporary files.
    """
    def __init__(self, root):
        self.root = Path(root)
        self.sessions = {}
        self.lock = threading.Lock()
        self.secret = secrets.token_bytes(32)

    def close(self, job=None, token=None):
        with self.lock:
            for key, session in list(self.sessions.items()):
                if (token is None or key == token) and (job is None or session["job"] == job):
                    self.sessions.pop(key)["temp"].cleanup()

    def _cursor(self, token, kind, direction, anchor, limit):
        raw = encode([token, kind, direction, anchor, limit])
        return base64.urlsafe_b64encode(raw + hmac.digest(self.secret, raw, "sha256")).decode()

    def _decode(self, cursor, kind, limit):
        try:
            raw = base64.b64decode(cursor, altchars=b"-_", validate=True)
            if not hmac.compare_digest(raw[-32:], hmac.digest(self.secret, raw[:-32], "sha256")):
                raise ValueError()
            token, found, direction, anchor, size = json.loads(raw[:-32])
            if found != kind or size != limit:
                raise ValueError()
            return token, direction, anchor
        except (ValueError, TypeError):
            raise ValueError("Invalid cursor or page size changed. Refresh to start a new traversal.") from None

    @contextmanager
    def read(self, job, token=None, *, fresh=False):
        if not self.lock.acquire(timeout=2):
            raise Unavailable("unavailable", "Another diagnostic read is busy. Try again.")
        try:
            now = time.time()
            for key, session in list(self.sessions.items()):
                if now - session["captured_at"] > 900:
                    self.sessions.pop(key)["temp"].cleanup()
            if token is None:
                if len(self.sessions) >= 8:
                    self.sessions.pop(next(iter(self.sessions)))["temp"].cleanup()
                temp = TemporaryDirectory(prefix="pdfmd-catalog-navigation-")
                try:
                    stamp = copy_catalog(self.root, Path(temp.name))
                    token = secrets.token_urlsafe(24)
                    session = {"temp": temp, "job": job, "captured_at": time.time(), "identity": stamp}
                    self.sessions[token] = session
                except BaseException:
                    temp.cleanup()
                    raise
            session = self.sessions.get(token)
            if not session or session["job"] != job:
                raise Unavailable("unavailable", "View expired, closed, or belongs to another task. Refresh.")
            if fresh and identity(self.root) != session["identity"]:
                raise Unavailable("stale", "Catalog changed since this view. Refresh before opening details.")
            with closing(ro_connect(Path(session["temp"].name) / "catalog.sqlite")) as db:
                deadline = time.monotonic() + 2
                db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                db.execute("BEGIN")
                view = CatalogView(self.root, db, job)
                view.get("job", job, job=job)
                meta = {"view": token, "job": job, "captured_at": session["captured_at"],
                        "consistency": "private catalog snapshot including WAL; immutable files checked on demand",
                        "graph": "unchecked; use Inspect saved acceptance for authoritative recovery diagnosis",
                        "event_boundary_is_change_cursor": False}
                yield view, meta
                if fresh and identity(self.root) != session["identity"]:
                    raise Unavailable("stale", "Catalog changed during detail inspection. Refresh.")
        finally:
            self.lock.release()

    def events(self, job, *, cursor=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("Event page size must be 1 through 200.")
        token, direction, anchor = self._decode(cursor, "events", limit) if cursor else (None, "recent", None)
        with self.read(job, token) as (view, meta):
            db = view.connection
            total, high = db.execute("SELECT count(*),max(seq) FROM events WHERE job=?", (job,)).fetchone()
            where, args = "job=?", [job]
            if direction in {"older", "newer"}:
                where += " AND seq" + ("<?" if direction == "older" else ">?")
                args.append(anchor)
            descending = direction in {"recent", "older"}
            rows = db.execute(f"SELECT * FROM events WHERE {where} ORDER BY seq {'DESC' if descending else 'ASC'} LIMIT ?", (*args, limit)).fetchall()
            if descending:
                rows.reverse()
            events = []
            for row in rows:
                try:
                    data = json.loads(row["data"])
                except ValueError:
                    data = {"diagnostic_limitation": "Corrupt event JSON; retained raw value follows.", "raw": row["data"]}
                events.append({**dict(row), "data": data, "id": f"{job}:{row['seq']}"})
            first = db.execute("SELECT count(*) FROM events WHERE job=? AND seq<?", (job, rows[0]["seq"])).fetchone()[0] + 1 if rows else 0
            last = first + len(rows) - 1 if rows else 0
            cur = lambda d, a=None: self._cursor(meta["view"], "events", d, a, limit)
            return {"status": "ok", **meta, "events": events, "total": total, "boundary_seq": high,
                    "order": "ascending catalog seq within each page", "first": first, "last": last,
                    "older": cur("older", rows[0]["seq"]) if first > 1 else None,
                    "newer": cur("newer", rows[-1]["seq"]) if last < total else None,
                    "oldest": cur("oldest"), "recent": cur("recent"), "limit": limit}

    def records(self, job, kind="request", *, token=None, cursor=None, limit=50):
        if kind not in KINDS or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Unknown diagnostic kind or page size (1 through 100).")
        if cursor:
            found, _, offset = self._decode(cursor, kind, limit)
            if token and token != found:
                raise ValueError("Cursor belongs to another view.")
            token = found
        else:
            offset = 0
        with self.read(job, token) as (view, meta):
            total = view.connection.execute("SELECT count(*) FROM records WHERE job=? AND kind=?", (job, kind)).fetchone()[0]
            rows = view.connection.execute("SELECT id,data,created FROM records WHERE job=? AND kind=? ORDER BY created DESC,id DESC LIMIT ? OFFSET ?", (job, kind, limit, offset)).fetchall()
            items = []
            for row in rows:
                try:
                    data = json.loads(row["data"])
                    item = record_summary(data, kind)
                    items.append({**item, "id": row["id"], "created": row["created"]})
                except (ValueError, TypeError) as exc:
                    # Keep the captured position/count/cursor even for bad rows.
                    # JSON errors and supported-JSON shape errors are local facts.
                    reason = "Malformed record JSON." if isinstance(exc, json.JSONDecodeError) else str(exc)
                    items.append({"id": row["id"], "created": row["created"],
                                  "diagnostic_status": "unavailable", "reason": reason})
            return {"status": "ok", **meta, "kind": kind, "items": items, "total": total,
                    "offset": offset, "next": self._cursor(meta["view"], kind, "next", offset + len(items), limit) if offset + len(items) < total else None}

    def detail(self, job, token, kind, key):
        if kind not in KINDS:
            raise ValueError("Unknown diagnostic kind.")
        with self.read(job, token, fresh=True) as (view, meta):
            record = view.get(kind, key, job=job)
            if not isinstance(record, dict) or record.get("job", job) != job or record.get("id", key) != key:
                raise ValueError("Record shape/ownership is inconsistent.")
            record_summary(record, kind)
            result = {"status": "ok", **meta, "kind": kind, "id": key, "record": record,
                      "limitations": ["Saved/complete claims do not establish source fidelity.",
                                       "Events are not a complete transaction log; no hidden model reasoning is inferred."], "links": []}
            if kind == "request":
                self._request(view, job, key, record, result)
            elif kind == "operation":
                self._operation(view, job, key, record, result)
            elif kind == "version":
                self._version(view, job, key, record, result)
            else:
                for field in ("receipt_ref", "proposal_ref", "ref"):
                    if isinstance(record.get(field), str):
                        result["links"].append(self.reference(view, job, record[field]))
                if kind == "conflict_resolution":
                    result["projection"] = "unchecked; a catalog resolution receipt alone does not prove graph readiness"
            return result

    @staticmethod
    def reference(view, job, ref, request=None, *, operation=None, input_request=None, kinds=None,
                  kind_reason="Request artifact kind mismatch."):
        """Raw descriptor observations never occupy validated fact fields.

        Publish facts only after integrity, provenance and the selected role pass.
        Role checks run last so they cannot replace an earlier failure reason.
        The raw fields retain absence/null/unsupported shapes for explanation.
        """
        link = {"ref": ref, "status": "unavailable"}
        try:
            blob = view.get("blob", ref, job=job)
            link["raw_descriptor"] = blob
            facts, _ = artifact_facts(view, job, ref, request, descriptor=blob)
            if kinds is not None and facts["kind"] not in kinds:
                raise ValueError(kind_reason)
            if operation is not None and facts["meta"].get("operation") != operation:
                raise ValueError("Operation ownership mismatch.")
            if input_request is not None and (facts["kind"] != "request_input" or facts["meta"].get("request") != input_request):
                raise ValueError("Frozen input ownership/kind mismatch.")
            link.update(status=AVAILABLE, facts=facts)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            link["reason"] = str(exc)
        return link

    def _request(self, view, job, key, record, result):
        attempts = []
        for aid in record.get("attempts", []):
            try:
                attempt = view.get("attempt", aid, job=job)
                if attempt.get("request") != key or attempt.get("id") != aid:
                    raise ValueError("Attempt does not belong to the selected request.")
                receive = view.maybe("stream_receive", aid)
                if receive and (receive.get("attempt") != aid or receive.get("request") != key):
                    raise ValueError("Receive observation ownership disagrees with its attempt.")
                attempts.append({"id": aid, "record": attempt, "receive_record": receive,
                                 "usage_state": ("not_sent" if attempt.get("send_evidence") == "not_sent" else
                                                 "unknown" if attempt.get("usage") is None else "reported"),
                                 "time_meaning": "started/finished are recorded wall times; transport elapsed offsets are local receive observations, not provider TTFT"})
            except (OSError, ValueError, TypeError, KeyError) as exc:
                attempts.append({"id": aid, "status": "unavailable", "reason": str(exc)})
        result["attempts"] = attempts
        result["boundary"] = ("prepared; no dispatch attempt recorded" if not attempts else
                              "recorded attempt(s); inspect individual receive, native publication and committed effects below; graph position unchecked")
        result["frozen_preparation"] = {k: record.get(k) for k in ("kind", "payload_ref", "route", "meta", "instruction_basis", "replay_policy")}
        try:
            staging = f"accepted:{key}" if view.maybe("blob", f"accepted:{key}") else None
        except (ValueError, KeyError, TypeError) as exc:
            staging = f"accepted:{key}"
            result["limitations"].append("Staging descriptor unavailable: " + str(exc))
        result["publication"] = {"pointer": record.get("accepted_ref"), "staging_ref": staging,
                                 "meaning": "recorded publication/staging; artifact existence alone does not validate acceptance or handoff"}
        refs = [record.get(field) for field in ("response_ref", "stream_ref", "accepted_ref")]
        if result["publication"]["staging_ref"]:
            refs.append(result["publication"]["staging_ref"])
        # Discover per-attempt retained native/raw artifacts by explicit metadata,
        # not pointer inheritance or time proximity. Stream chunks remain exact refs.
        for row in view.connection.execute("SELECT id,data FROM records WHERE job=? AND kind='blob'", (job,)):
            try:
                blob = json.loads(row["data"])
                # Raw discovery only selects candidates; reference validates each
                # before any ownership, usage or navigable fact is published.
                if (isinstance(blob, dict) and isinstance(blob.get("meta"), dict)
                        and blob["meta"].get("request") == key and blob.get("kind") in {"native_response", "assembled_response", "partial_native_response", "raw_stream"}):
                    refs.append(row["id"])
            except (ValueError, TypeError, AttributeError):
                continue
        roles = (("response_ref", {"native_response", "assembled_response", "partial_native_response"}),
                 ("stream_ref", {"raw_stream"}), ("accepted_ref", {"accepted_response"}))
        result["links"] = []
        for ref in dict.fromkeys(r for r in refs if r):
            # A shared pointer must satisfy every role in which it is used.
            selected = [allowed for field, allowed in roles if record.get(field) == ref]
            kinds = set.intersection(*selected) if selected else None
            role_names = "/".join(field for field, _ in roles if record.get(field) == ref)
            result["links"].append(self.reference(view, job, ref, record, kinds=kinds,
                                                 kind_reason=f"{role_names} artifact kind mismatch."))
        result["raw_usage"] = []
        for link in result["links"]:
            if link["status"] == AVAILABLE and link["facts"]["kind"] in {"native_response", "assembled_response"}:
                try:
                    native = view.json(link["ref"], job)
                    usage = interpret_usage(record["route"]["protocol"], native.get("usage"))
                    result["raw_usage"].append({"ref": link["ref"], "attempt": link["facts"]["attempt"], "usage": native.get("usage"),
                                                "validation": {"status": usage.status, "reason": usage.reason, "usage": usage.value},
                                                "meaning": ("assembled derived usage; not an original report; not a settlement or billed cost"
                                                    if link["facts"]["kind"] == "assembled_response" else
                                                    "native raw report; not a settlement or billed cost")})
                except (ValueError, TypeError, AttributeError, OSError) as exc:
                    result["limitations"].append("Raw usage unavailable: " + str(exc))
            if link["status"] == AVAILABLE and link["facts"]["kind"] == "raw_stream":
                try:
                    decoder = StreamDecoder(record["route"]["protocol"])
                    try:
                        decoder.feed(view.bytes(link["ref"], job))
                    except StreamError:
                        pass  # Already observed usage stays attributable even in rejected raw.
                    for observation in decoder.usage_observations:
                        result["raw_usage"].append({"ref": link["ref"], "attempt": link["facts"]["attempt"],
                            **observation, "meaning": "native raw SSE report; not a settlement or billed cost",
                            "validation": {"status": decoder.usage.status, "reason": decoder.usage.reason, "usage": decoder.usage.value}})
                except (ValueError, TypeError, AttributeError, OSError) as exc:
                    result["limitations"].append("Raw stream usage unavailable: " + str(exc))
        try:
            result["saved_acceptance_facts"] = diagnostic_facts(view, job, key)
            facts = result["saved_acceptance_facts"]
            original, saved = facts.get("original_usage"), facts.get("saved_usage")
            result["usage_comparison"] = ("unknown (one or both reports unavailable)" if original is None or saved is None else
                                          "inconsistent recorded reports; no reconciliation performed" if original != saved else
                                          "recorded original and saved usage agree; billing/cost unknown")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["limitations"].append("Saved acceptance facts unavailable: " + str(exc))
        result["related"] = []
        # These are exact domain aliases or stored request keys, never timestamp joins.
        for kind, identity_ in (("event_receipt", f"{job}:context_compacted:{key}"),
                                ("context_commit", f"context-settlement:{key}"),
                                ("context_disposition", f"context-proposal:{key}"),
                                ("conflict_resolution", key)):
            try:
                item = view.maybe(kind, identity_)
                if item:
                    result["related"].append({"kind": kind, "id": identity_, "record": item})
            except (ValueError, KeyError, TypeError) as exc:
                result["limitations"].append(f"{kind}: {exc}")
        # Frozen references can name an earlier proposal. Do not substitute an
        # alias derived from this request, infer adjacency, or re-prepare input.
        meta = record.get("meta", {})
        if not isinstance(meta, dict):
            result["limitations"].append("Frozen preparation metadata has an unsupported shape.")
            meta = {}
        frozen_context = meta.get("context_snapshot", {})
        snapshot = frozen_context.get("state", {}) if isinstance(frozen_context, dict) else None
        if not isinstance(snapshot, dict):
            result["limitations"].append("Frozen context snapshot has an unsupported shape.")
            snapshot = {}
        explicit_refs = [meta.get("proposal_ref"), *(snapshot.get(field) for field in
                         ("context_waiting", "context_check", "context_feedback", "context_latest", "handoff"))]
        for ref in dict.fromkeys(value for value in explicit_refs if isinstance(value, str)):
            link = self.reference(view, job, ref)
            link["association"] = "explicit frozen preparation/context snapshot reference"
            result["links"].append(link)
            for kind in ("context_disposition", "context_commit"):
                try:
                    item = view.maybe(kind, ref)
                    if item:
                        result["related"].append({"kind": kind, "id": ref, "record": item})
                        if isinstance(item.get("receipt_ref"), str) and item["receipt_ref"] != ref:
                            result["links"].append(self.reference(view, job, item["receipt_ref"]))
                except (ValueError, TypeError, KeyError) as exc:
                    result["limitations"].append(f"{kind} {ref}: {exc}")
        if record.get("payload_ref"):
            link = self.reference(view, job, record["payload_ref"], input_request=key)
            result["links"].append(link)
        for ref in (f"handoff:{key}", f"repair:{key}", f"context-settlement:{key}", f"context-proposal:{key}", f"continuation:{key}", f"conflict-resolution:{key}"):
            try:
                if view.maybe("blob", ref):
                    result["links"].append(self.reference(view, job, ref))
            except (ValueError, TypeError) as exc:
                result["limitations"].append(f"{ref}: {exc}")
        result["operations"] = []
        result["unconfirmed_operations"] = []
        associations = {}
        try:
            for op in view.records("operation", job):
                if isinstance(op, dict) and isinstance(op.get("id"), str) and op["id"].rpartition(":")[0] == key:
                    association = self.operation_request(view, job, op, cache=associations)
                    if association["status"] == "confirmed":
                        result["operations"].append({"id": op["id"], "origin": "matched saved call and operation arguments",
                                                     "publication": association["publication"]})
                    else:
                        result["unconfirmed_operations"].append({"id": op["id"], **association})
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            result["limitations"].append("Operation inventory incomplete: " + str(exc))
        unique = {}
        for link in result["links"]:
            old = unique.get(link["ref"])
            if old is None or link["status"] == "unavailable":
                unique[link["ref"]] = link
        result["links"] = list(unique.values())
        result["events"] = self.related_events(view, job, "request", key)
        result["limitations"].append("No usage sum is inferred: attempts may be unknown/inconsistent and native categories may overlap. Context reasons not recorded remain unknown; no preparation/tokenization is rerun.")

    @staticmethod
    def related_events(view, job, field, key):
        # json_valid prevents one malformed event from hiding independent records.
        rows = view.connection.execute("SELECT * FROM events WHERE job=? AND json_valid(data) AND json_extract(data,?)=? ORDER BY seq", (job, f"$.{field}", key))
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def _operation(self, view, job, key, record, result):
        data = record.get("result")
        for field in ("candidate_ref", "result_ref"):
            if record.get(field):
                link = self.reference(view, job, record[field], operation=key)
                result["links"].append(link)
                if field == "result_ref" and link["status"] == AVAILABLE:
                    try:
                        loaded = view.json(record[field], job)
                        if data is not None and data != loaded:
                            raise ValueError("Inline and retained operation results disagree.")
                        data = loaded
                    except (OSError, ValueError, TypeError) as exc:
                        result["limitations"].append(str(exc))
        data = data if isinstance(data, dict) else {}
        result["result"] = data
        skipped = data.get("execution") == "not_started" and data.get("skipped") is True
        result["effect"] = "not_started (recorded skip)" if skipped else "receipt recorded; effect needs tool-specific evidence" if record.get("status") == "done" else "pending/unknown effects"
        result["execution_history"] = "unknown: individual fresh executions and receipt-reuse returns are not durably logged; an existing receipt can be returned without another effect"
        result["events"] = self.related_events(view, job, "operation", key)
        # The operation prefix is accepted only when a retained request and its
        # exact call-index identity exist; manual IDs are shown separately.
        association = self.operation_request(view, job, record)
        result["request_association"] = association
        request_key = association.get("request") if association["status"] == "confirmed" else None
        result["request"] = request_key
        result["origin"] = "manual" if key.startswith("manual:") else "request-linked" if request_key else "unattributed"
        if record.get("tool") == "edit_document" and data.get("version_id"):
            try:
                saved = verify_version(view, job, data["version_id"])
                if (record.get("status") != "done" or record.get("result") != data
                        or saved.get("candidate_ref") != record.get("candidate_ref") or saved.get("parent") != data.get("parent")):
                    raise ValueError("Atomic operation/version lineage disagrees.")
                result["effect"] = "committed document version (atomic operation/version receipt and files checked)"
                result["version"] = data["version_id"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                result["effect"] = "unknown: document lineage unavailable"
                result["limitations"].append(str(exc))

    @staticmethod
    def operation_request(view, job, record, *, cache=None):
        """An ID prefix alone is not a causal join; match the retained call."""
        association = {"status": "unconfirmed"}
        try:
            request_key, _, index = record["id"].rpartition(":")
            if not re.fullmatch(r"0|[1-9][0-9]*", index) or record.get("job", job) != job:
                raise ValueError("Operation has no canonical request/call-index identity.")
            association["candidate_request"] = request_key
            cache = {} if cache is None else cache
            if request_key not in cache:
                try:
                    request = view.get("request", request_key, job=job)
                    if not isinstance(request, dict):
                        raise ValueError("Selected request JSON root must be an object.")
                    ref = request.get("accepted_ref")
                    if ref is None:
                        ref = f"accepted:{request_key}"
                    cache[request_key] = artifact_facts(view, job, ref, request, request_key=request_key)
                except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
                    cache[request_key] = str(exc)
            checked = cache[request_key]
            if isinstance(checked, str):
                raise ValueError(checked)
            facts, accepted = checked
            if accepted is None:
                raise ValueError("Accepted artifact kind mismatch.")
            call = accepted["calls"][int(index)]
            if call["name"] != record["tool"] or sha256(encode([call["name"], call["arguments"]])).hexdigest() != record["args_hash"]:
                raise ValueError("Operation tool/exact argument digest disagrees with the retained call.")
            return {"status": "confirmed", "request": request_key, "publication": facts["publication"],
                    "meaning": "recorded call relationship; acceptance, stream completeness and graph readiness not inferred"}
        except (ValueError, KeyError, TypeError, IndexError, OSError, AttributeError) as exc:
            return {**association, "reason": str(exc)}

    def _version(self, view, job, key, record, result):
        result["operations"] = []
        try:
            for op in view.records("operation", job):
                if isinstance(op.get("result"), dict) and op["result"].get("version_id") == key:
                    result["operations"].append({"id": op["id"], "candidate_ref": op.get("candidate_ref"),
                                                 "origin": "manual" if op["id"].startswith("manual:") else "recorded operation"})
            result["origin"] = "unattributed" if not result["operations"] else "linked by atomic receipt; inspect operation for validation"
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            result["origin"] = "unknown: operation inventory unavailable"
            result["limitations"].append(str(exc))
        try:
            saved = verify_version(view, job, key)
            result["verification"] = "version files checked; source fidelity not assessed"
            result["candidate_ref"] = saved.get("candidate_ref")
            if saved.get("candidate_ref"):
                result["links"].append(self.reference(view, job, saved["candidate_ref"]))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result.update(verification="unavailable", limitation=str(exc))

    def evidence(self, job, token, ref, *, mode="full", pointer="", start=None, end=None):
        with self.read(job, token, fresh=True) as (view, meta):
            result = Evidence(view).read(job, ref, mode, pointer, start, end)
            if result.get("image_ref"):
                blob = view.get("blob", ref, job=job)
                ext = blob["meta"]["extension"]
                mime = "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"
                result["url"] = f"data:{mime};base64," + base64.b64encode(view.bytes(ref, job)).decode()
            return {"status": "ok", **meta, **result}
