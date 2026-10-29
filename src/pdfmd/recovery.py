"""Explicit local historical resolution: inspect, prepare, commit, project.

No model/tool execution takes place here. Catalog authority is separate from
immutable candidates and from the exact LangGraph successor it authorizes.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from filelock import FileLock, Timeout
from langgraph.checkpoint.sqlite import SqliteSaver

from .acceptance import EvidenceCheckError, inspect_acceptance
from .context_outcomes import outcome, policy_ref
from .storage import Conflict, Store, encode


CHOICE = "preserve_and_replan"
MESSAGE = ("The user chose local recovery of a historical receive-boundary conflict. "
           "Original acceptance, evidence and consumption remain unchanged. Calls below are history, "
           "not execution authorization. Completed effects are retained; not-started calls were not executed. "
           "Re-plan from current saved work. Explicitly reselect any uncommitted context intent.")


def digest(value):
    return sha256(encode(value)).hexdigest()


def ro_connect(path):
    # mode=ro observes the live WAL. immutable=1 would be incorrect here.
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=0)


class ReadView(Store):
    """Store's pure readers on a pinned RO transaction, without Store setup."""
    def __init__(self, root, connection, job=None):
        self.root, self.connection, self.job = Path(root), connection, job
        connection.row_factory = sqlite3.Row

    def get(self, kind, key, *, job=None):
        if self.job is not None and job not in (None, self.job):
            raise ValueError("Evidence view cannot cross task ownership.")
        return super().get(kind, key, job=self.job or job)

    def maybe(self, kind, key):
        return self.get_tx(self.connection, kind, key, job=self.job)

    @contextmanager
    def _db(self):
        yield self.connection

    @contextmanager
    def transaction(self):
        raise RuntimeError("This evidence view is read-only.")
        yield

    def connect(self):
        raise RuntimeError("Readers must use the pinned catalog snapshot.")


class ReadSaver(SqliteSaver):
    """Narrow 3.1.2 schema adapter; normal setup performs writes even on reads."""
    def setup(self):
        # SELECT checks the supported columns without creating/migrating schema.
        self.conn.execute("SELECT thread_id,checkpoint_ns,checkpoint_id,parent_checkpoint_id,type,checkpoint,metadata FROM checkpoints LIMIT 0")
        self.conn.execute("SELECT thread_id,checkpoint_ns,checkpoint_id,task_id,task_path,idx,channel,type,value FROM writes LIMIT 0")


def no_execution(*args, **kwargs):
    raise RuntimeError("Read-only graph inspection cannot execute nodes.")


def readonly_graph(connection):
    from .runtime import build_graph
    return build_graph(SimpleNamespace(**{name: no_execution for name in
        ("coordinate", "prepare", "model", "tools", "compact")}), ReadSaver(connection))


@contextmanager
def existing_task_lease(path):
    """Probe/hold an existing executor lock without creating or changing bytes."""
    try:
        stream = open(path, "rb")
    except FileNotFoundError:
        yield False
        return
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield True
    finally:
        # Closing releases the lease. Never unlink a writer's lock path.
        stream.close()


def catalog_basis(view, job):
    # Candidates have no authority, so abandoned A objects cannot poison retry.
    return [tuple(row) for row in view.connection.execute(
        "SELECT kind,id,job,data FROM records WHERE job=? AND NOT (kind='blob' AND json_extract(data,'$.kind')='recovery_candidate') ORDER BY kind,id", (job,))]


def checkpoint_basis(snapshot):
    return {"config": snapshot.config, "values": dict(snapshot.values), "next": list(snapshot.next)}


def verify_version(view, job, version):
    record = view.get("version", version, job=job)
    versions_root = (view.root / "versions").resolve()
    directory = (versions_root / version).resolve()
    if directory.parent != versions_root:
        raise ValueError("Invalid document version identity.")
    for name, expected in record["files"].items():
        target = (directory / name).resolve()
        if not target.is_relative_to(directory):
            raise ValueError("Invalid document package member.")
        if sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError("Document commit files disagree with their registered version.")
    saved = json.loads((directory / "document.json").read_bytes())
    if (saved["job"] != job or saved["version"] != version
            or saved["source_ref"] != view.get("job", job)["source_ref"]):
        raise ValueError("Document commit ownership disagrees with its version.")
    return saved


def completed_effect(view, job, op, call, data, ok):
    """A matching envelope also needs a recognizable retained effect/result."""
    name = call["name"]
    if data.get("execution") == "not_started":
        return not ok and data.get("skipped") is True
    if not ok:
        if name in {"run_script", "ocr_page", "preview_document"}:
            return False  # A generic error cannot prove process/effect completion.
        return isinstance(data.get("error"), str) or data.get("context_rejected") is True
    if name == "edit_document":
        return True  # The atomic operation/version/file relation is checked below.
    if name == "report":
        intent = data.get("report_intent")
        if intent != json.loads(call["arguments"]):
            raise ValueError(f"Report receipt contradicts original arguments: {op}")
        if intent.get("version_id"):
            version = verify_version(view, job, intent["version_id"])
            if intent["state"] == "complete" and version["content"]["claim"] != "complete":
                raise ValueError(f"Completion claim has no complete saved version: {op}")
        return intent.get("state") in {"complete", "partial", "waiting"}
    if name == "context_update":
        saved = data.get("context_saved")
        return bool(saved and saved.get("operation") == op and saved.get("candidate_ref") == f"candidate:{op}"
                    and saved.get("instruction_basis") == view.get("request", op.rsplit(":", 1)[0], job=job)["instruction_basis"]
                    and all(k in saved for k in ("policy", "intents", "base_ref"))) or "context_intent" in data
    if name in {"render_page", "extract_image", "preview_document"}:
        ref = data.get("image_ref")
        if not ref:
            return False
        image = view.get("blob", ref, job=job)
        view.bytes(ref, job)
        if image["kind"] != "image" or data.get("ref") != ref:
            raise ValueError(f"Image effect/result identity conflicts: {op}")
        for item in image["meta"].get("originals", []):
            view.bytes(item["ref"], job)
        return True
    if name == "inspect_context":
        return data.get("snapshot_request") == op.rsplit(":", 1)[0] and bool(data.get("snapshot_payload_ref"))
    if name in {"inspect_pdf", "read_document", "read_evidence", "ocr_page"}:
        ref = data.get("ref")
        if ref:
            view.bytes(ref, job)
            if data.get("version_id"):
                verify_version(view, job, data["version_id"])
            return True
        return name == "read_document" and data.get("head", "missing") is None and isinstance(data.get("message"), str)
    if name == "run_script":
        if type(data.get("exit_code")) is not int or not isinstance(data.get("logs"), dict) or not isinstance(data.get("files"), list):
            return False
        refs = [(ref, "process_log") for ref in data["logs"].values()] + [(item["ref"], "script_output") for item in data["files"]]
        if set(data["logs"]) != {"stdout", "stderr"}:
            return False
        for ref, kind in refs:
            blob = view.get("blob", ref, job=job)
            if blob["kind"] != kind or blob["meta"].get("operation") != op:
                raise ValueError(f"Process output ownership conflicts: {op}")
            view.bytes(ref, job)
        return True
    return False


def operations(view, job, key, reply):
    """Prove pairing/effects using bytes and causal receipts, never reconcile."""
    result = []
    for index, call in enumerate(reply["calls"]):
        op = f"{key}:{index}"
        args_hash = digest([call["name"], call["arguments"]])
        old = view.maybe("operation", op)
        candidate_ref = f"candidate:{op}"
        candidate = view.maybe("blob", candidate_ref)
        if candidate:
            if (candidate["job"] != job or candidate["kind"] != "candidate"
                    or candidate["meta"] != {"operation": op, "tool": call["name"]}
                    or view.bytes(candidate_ref, job) != call["arguments"].encode("utf-8")):
                raise ValueError(f"Candidate ownership/arguments conflict: {op}")
        if old and (view.get("operation", op, job=job) != old or old.get("id") != op
                    or old.get("tool") != call["name"] or old.get("args_hash") != args_hash
                    or old.get("candidate_ref") != candidate_ref or not candidate):
            raise ValueError(f"Operation identity/arguments conflict: {op}")
        staged = view.maybe("blob", f"result:{op}")
        data = None
        ok = False
        if staged:
            if (not old or staged["job"] != job or staged["kind"] != "tool_result"
                    or staged["meta"].get("operation") != op
                    or (staged["meta"].get("args_hash") != args_hash and not (call["name"] == "edit_document" and "result" in old))):
                raise ValueError(f"Result provenance conflicts: {op}")
            data = view.json(staged["ref"], job)
            ok = staged["meta"].get("ok", old.get("ok", True))
            if "result" in old and data != old["result"]:
                raise ValueError(f"Document result projection conflicts: {op}")
            if old.get("result_ref") not in (None, staged["ref"]) or old.get("ok", ok) != ok:
                raise ValueError(f"Result pointer/outcome conflicts: {op}")
        elif old and old.get("status") == "done" and "result" in old:
            if call["name"] != "edit_document":
                raise ValueError(f"Inline result is not a document commit: {op}")
            data, ok = old["result"], old.get("ok", True)
        if data is not None:
            if old["status"] not in {"started", "done", "skipping"}:
                raise ValueError(f"Unknown operation lifecycle: {op}")
            if not isinstance(data, dict):
                raise ValueError(f"Tool result is not a result object: {op}")
            if old["status"] == "skipping" and not (data.get("skipped") and data.get("execution") == "not_started"):
                raise ValueError(f"A skipping intent has conflicting effect evidence: {op}")
            if call["name"] == "edit_document" and ok:
                if ("result" not in old or old["status"] != "done" or data != old["result"]
                        or data.get("candidate_ref") != candidate_ref):
                    raise ValueError(f"Document effect lacks its atomic commit receipt: {op}")
                saved = verify_version(view, job, data["version_id"])
                if saved.get("candidate_ref") != candidate_ref or saved["parent"] != data["parent"]:
                    raise ValueError(f"Document effect provenance conflicts: {op}")
            if call["name"] == "context_update" and ok:
                saved = data.get("context_saved")
                if saved and (saved.get("operation") != op or saved.get("candidate_ref") != candidate_ref):
                    raise ValueError(f"Context result ownership conflicts: {op}")
            certainty = "not_started" if data.get("execution") == "not_started" else "completed"
            if not completed_effect(view, job, op, call, data, ok):
                certainty = "unknown"
        elif old and old.get("status") != "skipping":
            certainty = "unknown"
        else:
            # No record is absence of start only if no registered document/result effect contradicts it.
            if any(verify_version(view, job, v["id"]).get("candidate_ref") == candidate_ref
                   for v in view.records("version", job)):
                raise ValueError(f"Unpaired document effect exists: {op}")
            certainty = "not_started"
        result.append({"operation": op, "call": call, "args_hash": args_hash, "candidate_ref": candidate_ref,
                       "original": old, "result_blob": staged, "data": data, "ok": ok,
                       "certainty": certainty, "prior_skipping": bool(old and old["status"] == "skipping")})
    return result


def context_transition(view, job, state, request, ops):
    """Restore only committed policy; retire related uncommitted intent explicitly."""
    from .context_updates import ContextUpdates
    from .context_revisions import POLICY
    changes, writes = {}, []
    waiting = state.get("context_waiting")
    if waiting:
        pending_blob = view.get("blob", waiting, job=job["id"])
        pending_body = view.json(waiting, job["id"])
        pending = pending_body.get("context_proposal") if isinstance(pending_body, dict) else None
        if (pending_blob["kind"] not in {"context_proposal", "tool_result"} or not isinstance(pending, dict)
                or not isinstance(pending.get("policy"), dict) or "instruction_basis" not in pending):
            raise ValueError("The pending context relationship cannot be confirmed.")
        view.maybe("context_disposition", waiting)  # Enforce catalog ownership, even for unrelated pending intent.
    # Current coordinator's committed decision may precede its checkpoint.
    settlement_ref = ContextUpdates.ref(request["id"])
    commit = view.maybe("context_commit", settlement_ref)
    if commit:
        saved = view.json(settlement_ref, job["id"])
        if (commit.get("receipt_ref") != settlement_ref or saved["basis"] != ContextUpdates.basis(state)
                or commit.get("proposal_ref") != waiting or commit.get("status") != saved["feedback"]["status"]):
            raise ValueError("Committed context settlement has an unconfirmed transition basis.")
        changes.update(saved["changes"])
    active = view.maybe("context_policy", job["id"])
    projected = {**state, **changes}
    if active:
        saved = view.json(active["receipt_ref"], job["id"])
        authority = view.get("context_commit", active["receipt_ref"], job=job["id"])
        if (authority["status"] != "applied" or saved["feedback"]["status"] != "applied"
                or active["ref"] != policy_ref(active["policy"])
                or any(saved["changes"].get(k) != v for k, v in active["policy"].items())):
            raise ValueError("Active context policy lacks matching committed authority.")
        if policy_ref(projected) != active["ref"]:
            raise ValueError("Active context policy is not linked to this graph transition.")
    for op in ops:
        data = op["data"] or {}
        if "context_intent" in data:
            policy = data.get("context_policy")
            if not policy or not active or policy_ref(policy) != active["ref"]:
                raise ValueError("Historical context effect lacks an exact committed policy basis.")
            changes.update({k: policy.get(k, v) for k, v in POLICY.items()})
    own = f"context-proposal:{request['id']}"
    blob = view.maybe("blob", own)
    proposal = view.json(own, job["id"])["context_proposal"] if blob else None
    context_ops = [op["operation"] for op in ops if op["call"]["name"] == "context_update"]
    if proposal and (proposal.get("batch") != request["id"] or proposal.get("instruction_basis") != request["instruction_basis"]
                     or any(op not in context_ops for op in proposal["operations"])):
        raise ValueError("Context proposal does not belong to the conflicted batch.")
    disposition = view.maybe("context_disposition", own)
    if disposition and disposition["status"] not in {"eligible_pending", "applied", "superseded", "needs_agent_revision"}:
        raise ValueError("Unknown context disposition.")
    related = list(proposal.get("supersedes", [])) if proposal else []
    for op in ops:
        base = (op["data"] or {}).get("context_saved", {}).get("base_ref")
        if base and base == waiting:
            related.append(base)
    if proposal and proposal.get("base_ref") in related:
        related = list(dict.fromkeys(related + [proposal["base_ref"]]))
    # Related ancestors remain superseded, never implicitly revived. Unrelated pending survives.
    if not commit and waiting in related:
        changes.update(context_waiting=None, context_check=None)
        for ancestor in related:
            prior = view.maybe("context_disposition", ancestor)
            if not prior or prior["status"] == "eligible_pending":
                writes.append(("context_disposition", ancestor, {"proposal_ref": ancestor,
                    "status": "superseded", "reason": "replacement_revision", "replacement_ref": own}))
    uncommitted = context_ops and not (disposition and disposition["status"] in {"applied", "superseded", "needs_agent_revision"})
    feedback = None
    if uncommitted:
        proposal_ref = own if proposal else f"recovery-context:{request['id']}"
        feedback_ref = f"recovery-context-outcome:{request['id']}"
        feedback = {"summary": outcome("needs_agent_revision", proposal_ref, feedback_ref, "historical_conflict_replan"),
                    "operations": context_ops, "message": MESSAGE, "original_proposal_ref": own if proposal else None}
        writes.append(("context_disposition", proposal_ref, {"proposal_ref": proposal_ref,
                      "status": "needs_agent_revision", "reason": "historical_conflict_replan", "receipt_ref": feedback_ref}))
        if waiting == own:
            changes.update(context_waiting=None, context_check=None)
        changes.update(context_feedback=feedback_ref, context_latest=proposal_ref)
    return {"changes": changes, "writes": writes, "feedback": feedback, "proposal": proposal,
            "operations": context_ops, "settlement_ref": settlement_ref if commit else None}


def successor(view, job, snapshot, checked, ops):
    state, request = dict(snapshot.values), checked["request"]
    key = request["id"]
    if (request["kind"] not in {"normal", "compaction"}
            or (snapshot.next in {("model",), ("tools",)} and request["kind"] != "normal")
            or (snapshot.next == ("compact",) and request["kind"] != "compaction")):
        raise ValueError("Request kind contradicts the resumable graph phase.")
    if (not snapshot.next or state.get("job") != job["id"]
            or key != (state.get("pending") or f"{job['id']}:{state['seq']}:{state['revision']}")
            or snapshot.next not in {("model",), ("tools",), ("compact",), ("prepare",), ("coordinate",)}):
        raise ValueError("Request is not at the current supported resumable graph position.")
    ctx = context_transition(view, job, state, request, ops)
    patch = {**ctx["changes"], "pending": None, "next": "prepare", "terminal": False, "report": None,
             "revision": state["revision"] + 1}
    case = "N" if request["kind"] == "normal" else "C2"
    handoff = None
    repairs = dict(state.get("repairs", {}))
    if case == "N":
        if key in state["history"]:
            raise ValueError("Pending normal request is already in graph history.")
        patch.update(history=[*state["history"], key], seq=state["seq"] + 1)
        repairs.pop("normal", None)
    else:
        receipt = view.maybe("event_receipt", f"{job['id']}:context_compacted:{key}")
        if receipt:
            archive_ref = f"handoff:{key}"
            archive = view.json(archive_ref, job["id"])
            meta = request["meta"]
            covered = meta["covered"]
            from .history import batch_identity
            originals = [batch_identity(view, job["id"], item)["evidence_ref"] for item in covered]
            resolutions = [batch_identity(view, job["id"], item)["resolution_ref"] for item in covered]
            if (meta["revision"] != state["revision"] or state["history"][:len(covered)] != covered
                    or receipt.get("covered") != covered or receipt.get("handoff_ref") != archive_ref
                    or archive.get("request") != key or archive.get("covered") != covered
                    or archive.get("originals") != originals or archive.get("previous_archive_ref") != state.get("handoff")
                    or archive.get("deferred") != meta["deferred"] or archive.get("projection", []) != meta.get("projection", [])
                    or archive.get("resolution_refs", [None] * len(covered)) != resolutions
                    or archive.get("content") != json.loads(checked["accepted"]["text"])):
                raise ValueError("Committed handoff/archive/coverage does not match its original transition.")
            patch.update(handoff=archive_ref, history=state["history"][len(covered):])
            repairs.pop("compaction", None)
            case, handoff = "C1", {"archive_ref": archive_ref, "receipt": receipt, "covered": covered}
    patch["repairs"] = repairs
    return {"case": case, "patch": patch, "context": ctx, "handoff": handoff,
            "report": {"original": state.get("report"), "successor_control": "replan"}}


def unavailable(code, message):
    return {"eligible": False, "status": code, "reasons": [message],
            "verification": {name: "unavailable" for name in ("original", "saved", "raw", "operations")},
            **{name: {"status": "unknown"} for name in ("storage", "provenance", "reconstruction", "receive_boundary", "publication", "effects")}}


@contextmanager
def inspection(root, job, *, locked=False):
    """Read stable private copies including WAL; never open task DBs in SQLite.

    SQLite mode=ro itself may create original WAL sidecars. Source file reads,
    task-lease probes and before/after identities avoid that side effect. A
    changed source interval is unavailable, never an actionable mixed snapshot.
    SQLite interprets the copied WAL itself; no custom WAL reconstruction.
    """
    root = Path(root)
    if not (root / "graph.sqlite").is_file():
        raise ValueError("missing_graph: No saved graph exists; diagnosis creates nothing.")
    names = [name + suffix for name in ("catalog.sqlite", "graph.sqlite") for suffix in ("", "-wal", "-journal")]
    def source_files():
        files = {}
        for name in names:
            try:
                path = root / name
                raw = path.read_bytes()
                files[name] = (raw, path.stat().st_mtime_ns)
            except FileNotFoundError:
                if name.endswith(".sqlite"):
                    raise
        return files
    original = source_files()
    if any(name.endswith("-journal") and raw for name, (raw, _) in original.items()):
        raise Conflict("stale_view: An unresolved rollback journal prevents a stable WAL-only diagnostic view.")
    with TemporaryDirectory(prefix="pdfmd-diagnosis-") as scratch:
        scratch = Path(scratch)
        for name, (raw, _) in original.items():
            (scratch / name).write_bytes(raw)
        with closing(ro_connect(scratch / "catalog.sqlite")) as catalog, closing(ro_connect(scratch / "graph.sqlite")) as graph_db:
            catalog.execute("BEGIN")
            graph_db.execute("BEGIN")
            view = ReadView(root, catalog, job)
            graph = readonly_graph(graph_db)
            snapshot = graph.get_state({"configurable": {"thread_id": job}})
            yield view, graph, snapshot
        def durable_bytes(files):
            # Read-only polling can touch mtimes or create/remove an empty WAL.
            # Neither contains a changed SQLite page/commit. Nonempty WAL and
            # all main bytes remain part of the exact consistency guard.
            return {name: raw for name, (raw, _) in files.items()
                    if not (name.endswith("-wal") and not raw)}
        if durable_bytes(original) != durable_bytes(source_files()):
            raise Conflict("stale_view: Task changed during diagnosis. Refresh before selecting recovery.")
        if not locked:
            with existing_task_lease(root / f"task-{job}.lock"):
                pass


def diagnostic_facts(view, job, key=None, *, checked=None, receipt=None):
    """Project recorded facts once; missing evidence is not originally unknown usage.

    Blob availability checks verify descriptor/bytes, not a new constituent SSE
    audit. Only inspect_acceptance supplies checked-now reconstruction facts.
    """
    current = view.get("job", job)
    facts = {"job": job, "request": key, "head": current.get("head"),
             "versions": [v["id"] for v in view.records("version", job)],
             "verification": {name: "unknown" for name in ("original", "saved", "raw", "operations")},
             "evidence_availability": {}, "fact_errors": []}
    try:
        if current.get("head"):
            verify_version(view, job, current["head"])
        facts["head_verification"] = "checked_now"
    except (ValueError, OSError, KeyError, TypeError) as exc:
        facts["head_verification"] = "unavailable"
        facts["fact_errors"].append("Current head is unavailable/inconsistent: " + str(exc))
    if key is None:
        return facts
    request = receipt["original_request"] if receipt else view.get("request", key, job=job)
    if request.get("id") != key or request.get("job") != job:
        raise Conflict("Diagnostic request ownership is inconsistent.")
    attempt = checked["attempt"] if checked else receipt["original_attempt"] if receipt else None
    if attempt is None and request.get("attempts"):
        attempt = view.get("attempt", request["attempts"][-1], job=job)
    if attempt and (attempt.get("request") != key or attempt.get("id") not in request["attempts"]):
        raise Conflict("Diagnostic attempt ownership is inconsistent.")
    facts.update(publication={"status": "published" if request.get("accepted_ref") else "unpublished",
                              "accepted_ref": request.get("accepted_ref"), "request_status": request["status"]},
                 original_request_status=request["status"], original_attempt_status=attempt.get("status") if attempt else None,
                 original_failure=request.get("failure"),
                 original_usage=attempt.get("usage") if attempt else None,
                 original_usage_state=("unavailable" if attempt and "usage" not in attempt else
                                       "known" if attempt and attempt["usage"] is not None else "unknown"),
                 finished=attempt.get("finished") if attempt else None,
                 original_finish=attempt.get("finished") if attempt else None)
    facts["verification"]["original"] = "checked_now"
    if attempt:
        facts["attempt"] = attempt["id"]
    stage_ref = receipt["accepted_staging_ref"] if receipt else f"accepted:{key}"
    if receipt or view.maybe("blob", stage_ref):
        facts["accepted_staging_ref"] = stage_ref
    # Retain receipt-linked references even if the corresponding file is gone.
    if receipt:
        facts.update(resolution_ref=receipt["ref"], resolution_head=receipt["observed_job"].get("head"))
        for field, kinds in (("native_ref", {"native_response", "assembled_response"}), ("stream_ref", {"raw_stream"})):
            references = [ref for ref, descriptor in receipt["evidence"].items()
                          if descriptor["kind"] in kinds and descriptor["meta"].get("request") == key
                          and descriptor["meta"].get("attempt") == receipt["attempt"]]
            if len(references) == 1:
                facts[field] = references[0]
            elif references:
                facts["fact_errors"].append(f"Resolution has ambiguous {field} for its selected attempt.")
    elif checked:
        facts.update(native_ref=checked["native"]["ref"], stream_ref=checked["stream_ref"])
    else:
        for target, field in (("native_ref", "response_ref"), ("stream_ref", "stream_ref")):
            if request.get(field):
                facts[target] = request[field]

    def available(ref):
        try:
            descriptor = view.get("blob", ref, job=job)
            if descriptor.get("ref") != ref or descriptor.get("job") != job:
                raise Conflict("Evidence ownership is inconsistent.")
            if receipt and ref in receipt["evidence"] and descriptor != receipt["evidence"][ref]:
                raise Conflict("Evidence descriptor changed since resolution.")
            view.bytes(ref, job)
            facts["evidence_availability"][ref] = {"status": "available"}
            return True
        except (ValueError, OSError, KeyError, TypeError) as exc:
            facts["evidence_availability"][ref] = {"status": "unavailable", "reason": str(exc)}
            facts["fact_errors"].append(f"Evidence {ref} is unavailable/inconsistent: {exc}")
            return False

    if facts.get("accepted_staging_ref") and available(stage_ref):
        try:
            descriptor = view.get("blob", stage_ref, job=job)
            if descriptor["kind"] != "accepted_response" or descriptor["meta"].get("request") != key:
                raise Conflict("Acceptance staging ownership is inconsistent.")
            saved = checked["accepted"] if checked else view.json(stage_ref, job)
            facts.update(saved_usage=saved["usage"],
                         saved_usage_state="known" if saved["usage"] is not None else "unknown")
            facts["verification"]["saved"] = "verified_at_resolution" if receipt else "checked_now" if checked else "unavailable"
            facts.update(native_ref=saved["native_ref"], stream_ref=saved.get("stream_ref"))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            facts["fact_errors"].append("Saved reply projection is unavailable/inconsistent: " + str(exc))
    if "saved_usage_state" not in facts:
        facts["saved_usage_state"] = "unavailable"
        facts["verification"]["saved"] = "unavailable"
    for field in ("native_ref", "stream_ref", "resolution_ref"):
        if facts.get(field):
            available(facts[field])
    facts["verification"]["raw"] = ("unavailable" if facts.get("stream_ref") and
        facts["evidence_availability"][facts["stream_ref"]]["status"] != "available" else
        "verified_at_resolution" if receipt else "checked_now" if checked else "unknown")
    if receipt:
        facts["effects"] = {"status": "verified_at_resolution", "operations": [
            {**{name: op[name] for name in ("operation", "certainty", "candidate_ref", "result_ref", "prior_skipping")},
             "tool": op["call"]["name"], "verification": "verified_at_resolution"} for op in receipt["operations"]]}
        facts["verification"]["operations"] = "verified_at_resolution"
        for op in receipt["operations"]:
            available(op["candidate_ref"])
            available(op["result_ref"])
        try:
            from .history import batch_reply
            batch_reply(view, job, key)
        except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError) as exc:
            facts["fact_errors"].append("Resolved pairing is unavailable/inconsistent: " + str(exc))
            facts["verification"]["saved"] = facts["verification"]["operations"] = "unavailable"
    return facts


def inspect_current(view, graph, snapshot, job):
    current = view.get("job", job)
    state = snapshot.values
    if not state or not snapshot.next:
        return {**unavailable("no_resumable_request", "No current resumable request exists."), **diagnostic_facts(view, job)}, None
    key = state.get("pending") or f"{job}:{state['seq']}:{state['revision']}"
    request = view.maybe("request", key)
    if not request:
        return {**unavailable("no_resumable_request", "No frozen request at the current graph position."), **diagnostic_facts(view, job)}, None
    base = diagnostic_facts(view, job, key)
    if not view.maybe("blob", f"accepted:{key}"):
        return {**unavailable("missing_staging", "No complete accepted staging; raw terminal alone cannot authorize this recovery."), **base}, None
    try:
        checked = inspect_acceptance(view, job, key)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {**unavailable("evidence_unconfirmed", str(exc)), **base,
                **getattr(exc, "observations", {})}, None
    base = diagnostic_facts(view, job, key, checked=checked)
    facts = {"storage": {"status": "verified"}, "provenance": {"status": "verified"},
             "reconstruction": {"status": "matches" if checked["reconstructed"] else "unknown"}, "receive_boundary": checked["boundary"],
             "attempt": checked["attempt_id"], "accepted_staging_ref": checked["ref"], "native_ref": checked["native"]["ref"], "stream_ref": checked["stream_ref"]}
    orphan_candidates = []
    for blob in view.records("blob", job):
        if blob["kind"] != "recovery_candidate":
            continue
        operation = blob["meta"].get("operation", "")
        if operation.startswith(key + ":"):
            orphan_candidates.append(blob["ref"])
        elif not blob["meta"]:
            body = view.json(blob["ref"], job)
            if isinstance(body, dict) and body.get("ref") == f"conflict-resolution:{key}" and body.get("request") == key:
                orphan_candidates.append(blob["ref"])
    facts["preparation"] = {"status": "uncommitted_candidates" if orphan_candidates else "not_prepared",
                            "candidate_refs": orphan_candidates, "authoritative": False}
    try:
        ops = operations(view, job, key, checked["accepted"])
        transition = successor(view, current, snapshot, checked, ops)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {**unavailable("evidence_unconfirmed", str(exc)), **base, **facts,
                "provenance": {"status": "unknown", "scope": "operation/context/handoff association"}}, None
    basis_records = catalog_basis(view, job)
    basis = digest({"catalog": basis_records, "graph": checkpoint_basis(snapshot)})
    eligible = checked["boundary"]["status"] == "finish_conflict" and all(op["certainty"] != "unknown" for op in ops) and not base["fact_errors"]
    reasons = [] if eligible else ["Unknown tool effect prevents local resolution." if any(op["certainty"] == "unknown" for op in ops)
                                 else "Receive evidence is compatible; use ordinary validated continuation." if checked["boundary"]["status"] == "compatible"
                                 else "Receive failure is outside the supported finish-boundary class."]
    display = {**base, **facts, "status": "eligible" if eligible else "unsupported", "eligible": eligible, "basis": basis, "reasons": reasons,
        "attempt": checked["attempt_id"], "accepted_staging_ref": checked["ref"], "native_ref": checked["native"]["ref"], "stream_ref": checked["stream_ref"],
        "storage": {"status": "verified"}, "provenance": {"status": "verified"},
        "reconstruction": {"status": "matches" if checked["reconstructed"] else "unknown"}, "receive_boundary": checked["boundary"],
        "effects": {"status": "unknown" if any(op["certainty"] == "unknown" for op in ops) else "established",
                    "operations": [{**{k: op[k] for k in ("operation", "certainty", "candidate_ref", "prior_skipping")},
                                    "result_ref": op["result_blob"]["ref"] if op["result_blob"] else None,
                                    "tool": op["call"]["name"], "verification": "checked_now"} for op in ops]},
        "original_usage": checked["attempt"].get("usage"), "saved_usage": checked["accepted"].get("usage"),
        "finished": checked["attempt"].get("finished"), "transition": transition["case"]}
    display["verification"]["operations"] = "checked_now"
    display["reasons"].extend(base["fact_errors"])
    return display, {"checked": checked, "operations": ops, "transition": transition,
                     "catalog": basis_records, "graph": checkpoint_basis(snapshot), "job": current}


def recovery_boundary(snapshot, receipt):
    """An exact owned successor, not merely some later marked descendant."""
    return (dict(snapshot.values) == {**receipt["graph_basis"]["values"], **receipt["successor"]}
            and snapshot.next == ("coordinate",))


def select_subject(view, graph, snapshot, job):
    """Identity and checkpoint relationships select; catalog order never does."""
    state = snapshot.values
    if view.get("job", job).get("status") == "completed" or state.get("terminal"):
        return None, "none"
    key = state.get("pending") if state else None
    if not key and state and snapshot.next:
        derived = f"{job}:{state['seq']}:{state['revision']}"
        if view.maybe("request", derived):
            key = derived
    if key:
        return key, "current_request"
    from .history import resolution_receipt
    boundaries = []
    for authority in view.records("conflict_resolution", job):
        # Unrelated bad historical receipts must not replace a current request.
        try:
            receipt = resolution_receipt(view, job, authority["request"])
            if recovery_boundary(snapshot, receipt) and projection_status(graph, job, receipt) == "ready":
                boundaries.append(receipt["request"])
        except (ValueError, OSError, KeyError, TypeError):
            continue
    if len(boundaries) == 1:
        return boundaries[0], "recovery_boundary"
    return None, "none"


def historical_resolutions(view, job, primary):
    """Secondary retained identities, never continuation authority."""
    from .history import resolution_receipt
    entries = []
    for authority in sorted(view.records("conflict_resolution", job), key=lambda row: row["request"]):
        if authority["request"] == primary:
            continue
        entry = {"request": authority["request"], "resolution_ref": authority["ref"], "status": "historical"}
        try:
            resolution_receipt(view, job, authority["request"])
            entry["verification"] = "verified_at_resolution"
        except (ValueError, OSError, KeyError, TypeError) as exc:
            entry.update(verification="unavailable", reason=str(exc))
        entries.append(entry)
    return entries


def resolved_diagnosis(view, graph, snapshot, job, key):
    from .history import resolution_receipt
    try:
        receipt = resolution_receipt(view, job, key)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Keep the selected identity and independently readable recorded facts.
        # A corrupt/missing receipt cannot turn K into another ready resolution.
        facts = diagnostic_facts(view, job, key)
        return {**facts, "status": "resolved", "eligible": False, "projection": "blocked",
                "resolution_ref": view.get("conflict_resolution", key, job=job)["ref"],
                "reasons": ["Committed resolution is unavailable/inconsistent: " + str(exc), *facts["fact_errors"]]}
    facts = diagnostic_facts(view, job, key, receipt=receipt)
    try:
        projection = projection_status(graph, job, receipt)
        reasons = []
        if projection == "ready" and not recovery_boundary(snapshot, receipt):
            projection = "historical"
            reasons.append("This resolution was projected before later graph progress; it does not establish current readiness.")
    except Conflict as exc:
        projection, reasons = "blocked", [str(exc)]
    lineage = projection
    if facts["fact_errors"]:
        projection = "blocked"
        reasons.extend(facts["fact_errors"])
    return {**facts, "status": "resolved", "eligible": False,
            "projection": projection, "projection_lineage": lineage, "reasons": reasons,
            "verification_basis": "committed_resolution", "receive_boundary": receipt["receive_boundary"],
            "storage": {"status": "verified_at_resolution"}, "provenance": {"status": "verified_at_resolution"},
            "reconstruction": {"status": "verified_at_resolution"}}


def diagnose(root, job):
    try:
        with existing_task_lease(Path(root) / f"task-{job}.lock") as leased:
            with inspection(root, job, locked=leased) as (view, graph, snapshot):
                key, kind = select_subject(view, graph, snapshot, job)
                if key and view.maybe("conflict_resolution", key):
                    display = resolved_diagnosis(view, graph, snapshot, job, key)
                elif key:
                    display, _ = inspect_current(view, graph, snapshot, job)
                    if display.get("request") is None:
                        display["request"] = key
                else:
                    display = {**unavailable("no_resumable_request", "No current frozen request or immediate local recovery boundary exists."),
                               **diagnostic_facts(view, job)}
                display["subject"] = {"kind": kind, "request": key, "job": job}
                display["historical_resolutions"] = historical_resolutions(view, job, key)
                display["reasons"].extend(reason for reason in display.get("fact_errors", [])
                                         if reason not in display["reasons"])
            return display
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        if isinstance(exc, OSError) and not isinstance(exc, FileNotFoundError):
            return unavailable("busy", "Task is active or its read-only view is unavailable. Stop it and retry.")
        message = str(exc)
        code = "stale_view" if isinstance(exc, Conflict) and message.startswith("stale_view") else "missing_graph" if message.startswith("missing_graph") else "unsupported_schema" if isinstance(exc, sqlite3.Error) else "evidence_unconfirmed"
        return {**unavailable(code, message if not isinstance(exc, AttributeError) else "Saved native structure is unsupported by the parser; this is not proof of disk corruption."),
                **(exc.observations if isinstance(exc, EvidenceCheckError) else {})}


def projection_status(graph, job, receipt):
    """Prove original position or a marked successor on the actual parent chain."""
    snapshot = graph.get_state({"configurable": {"thread_id": job}})
    ref, key = receipt["ref"], receipt["request"]
    source = receipt["graph_basis"]
    if checkpoint_basis(snapshot) == source:
        return "pending"
    if snapshot.values.get("resolutions", {}).get(key) != ref:
        raise Conflict("Graph has no matching resolution marker on its current lineage.")
    cursor = snapshot
    while cursor and cursor.values:
        if cursor.values.get("resolutions", {}).get(key) == ref:
            if cursor.parent_config == source["config"]:
                expected = {**source["values"], **receipt["successor"]}
                if dict(cursor.values) != expected or cursor.next != ("coordinate",):
                    raise Conflict("Marked recovery successor disagrees with committed authority.")
                return "ready"
        if not cursor.parent_config:
            break
        cursor = graph.get_state(cursor.parent_config)
    raise Conflict("Graph diverged from the recorded recovery basis; no projection was written.")


def project(runtime, job, authority):
    from .history import resolution_receipt
    receipt = resolution_receipt(runtime.store, job, authority["request"])
    if projection_status(runtime.graph, job, receipt) == "pending":
        runtime.graph.update_state(receipt["graph_basis"]["config"], receipt["successor"], as_node="tools")
    return {"request": authority["request"], "resolution_ref": authority["ref"], "projection": "ready"}


def project_committed(runtime, job):
    for authority in runtime.store.records("conflict_resolution", job):
        project(runtime, job, authority)


def stage_alias(store, job, alias, kind, value, meta=None):
    candidate = store.blob(job, "recovery_candidate", value, meta)
    return {**candidate, "ref": alias, "kind": kind}


def resolve(store, job, key, basis, *, choice=CHOICE):
    if choice != CHOICE:
        raise Conflict("Only the explicit preserve-and-replan choice is supported.")
    lock = FileLock(str(store.root / f"task-{job}.lock"))
    try:
        with lock.acquire(timeout=0):
            existing = store.maybe("conflict_resolution", key)
            if existing:
                existing = store.get("conflict_resolution", key, job=job)
                if existing.get("job") != job or existing.get("choice") != choice:
                    raise Conflict("This request already has a different resolution.")
                return finish_projection(store, job, existing)
            with inspection(store.root, job, locked=True) as (view, graph, snapshot):
                display, plan = inspect_current(view, graph, snapshot, job)
            if display.get("request") != key or display.get("basis") != basis:
                raise Conflict("Stale diagnostic basis. Refresh and explicitly select recovery again.")
            if not display["eligible"]:
                raise Conflict("This evidence/effect case cannot receive local recovery: " + "; ".join(display["reasons"]))
            aliases, operation_records = [], []
            dispositions = []
            for op in plan["operations"]:
                candidate = store.maybe("blob", op["candidate_ref"])
                if candidate is None:
                    aliases.append(stage_alias(store, job, op["candidate_ref"], "candidate", op["call"]["arguments"].encode(),
                                               {"operation": op["operation"], "tool": op["call"]["name"]}))
                data, ok = op["data"], op["ok"]
                if data is None:
                    data = {"skipped": True, "execution": "not_started", "candidate_ref": op["candidate_ref"],
                            "reason": "superseded_by_user_amendment" if op["prior_skipping"] else "historical_conflict_replan",
                            "message": MESSAGE}
                result_ref = f"result:{op['operation']}"
                if op["result_blob"] is None:
                    aliases.append(stage_alias(store, job, result_ref, "tool_result", data,
                        {"operation": op["operation"], "args_hash": op["args_hash"], "ok": ok}))
                record = {**(op["original"] or {}), "id": op["operation"], "tool": op["call"]["name"],
                          "args_hash": op["args_hash"], "status": "done", "candidate_ref": op["candidate_ref"], "result_ref": result_ref, "ok": ok}
                operation_records.append(record)
                dispositions.append({**{k: op[k] for k in ("operation", "call", "args_hash", "candidate_ref", "certainty", "prior_skipping")},
                                     "result_ref": result_ref, "original": op["original"], "settled": record})
            ctx = plan["transition"]["context"]
            if ctx["feedback"]:
                feedback = ctx["feedback"]
                proposal_ref = feedback["summary"]["proposal_ref"]
                if ctx["proposal"] is None:
                    aliases.append(stage_alias(store, job, proposal_ref, "recovery_context", {
                        "context_proposal": {"batch": key, "operations": ctx["operations"], "complete": False,
                            "reason": "historical_conflict_replan", "policy_applied": False}}))
                aliases.append(stage_alias(store, job, feedback["summary"]["receipt_ref"], "recovery_context_outcome", feedback))
            ref = f"conflict-resolution:{key}"
            patch = {**plan["transition"]["patch"], "resolutions": {**plan["graph"]["values"].get("resolutions", {}), key: ref}}
            receipt = {"version": 1, "ref": ref, "job": job, "request": key, "attempt": plan["checked"]["attempt_id"],
                       "choice": choice, "basis": basis, "graph_basis": plan["graph"], "successor": patch,
                       "observed_job": plan["job"], "accepted_staging_ref": plan["checked"]["ref"],
                       "original_request": plan["checked"]["request"], "original_attempt": plan["checked"]["attempt"],
                       "evidence": plan["checked"]["evidence"], "receive_boundary": plan["checked"]["boundary"],
                       "operations": dispositions, "context": ctx, "handoff": plan["transition"]["handoff"],
                       "report": plan["transition"]["report"], "case": plan["transition"]["case"], "message": MESSAGE}
            aliases.append(stage_alias(store, job, ref, "conflict_resolution", receipt))
            prepared(store, receipt)  # Boundary for controlled own-process interruption tests.
            # Recheck graph outside B; all supported graph writers hold this task lock.
            with inspection(store.root, job, locked=True) as (_, graph, snapshot):
                if checkpoint_basis(snapshot) != plan["graph"]:
                    raise Conflict("Graph changed while preparing recovery candidates.")
            authority = {"job": job, "request": key, "ref": ref, "choice": choice, "basis": basis}
            with store.transaction() as db:
                view = ReadView(store.root, db)
                if catalog_basis(view, job) != plan["catalog"]:
                    raise Conflict("Task/evidence changed while preparing recovery; refresh and select again.")
                # The per-task basis cannot see foreign rows with colliding
                # primary keys. Check every publication target's SQL owner in
                # this same transaction before adopting or updating it.
                if store.get_tx(db, "conflict_resolution", key, job=job) is not None:
                    raise Conflict("This request already has a committed resolution.")
                for blob in aliases:
                    prior = store.get_tx(db, "blob", blob["ref"], job=job)
                    if prior and prior != blob:
                        raise Conflict("Recovery alias conflicts with an existing immutable object.")
                    store.put_tx(db, "blob", blob["ref"], job, blob)
                for record in operation_records:
                    store.get_tx(db, "operation", record["id"], job=job)
                    store.put_tx(db, "operation", record["id"], job, record)
                for kind, identity, value in ctx["writes"]:
                    store.get_tx(db, kind, identity, job=job)
                    store.put_tx(db, kind, identity, job, value)
                store.put_tx(db, "conflict_resolution", key, job, authority)
            committed(store, receipt)
            return finish_projection(store, job, authority)
    except Timeout as exc:
        raise Conflict("Task has an active executor. Stop it before local recovery.") from exc
    except (OSError, sqlite3.Error) as exc:
        raise Conflict("Local recovery storage view is temporarily unavailable. Any committed decision is retained; refresh and finish that same local recovery.") from exc


def finish_projection(store, job, authority):
    from .runtime import Runtime
    from .nexus import Nexus
    from .history import resolution_receipt
    # After B, current mutable catalog/head/settings are not a new selection
    # basis. Read canonical authority in one SQLite snapshot; do not copy a
    # polling catalog/WAL or revoke the choice for harmless housekeeping.
    with store.read_snapshot() as db:
        receipt = resolution_receipt(ReadView(store.root, db, job), job, authority["request"])
    if not (store.root / "graph.sqlite").is_file():
        raise Conflict("The committed recovery has no saved graph; no graph was created.")
    # This is the explicit mutation path, so SQLite's sidecar bookkeeping is
    # permitted. SELECT-only saver setup still rejects unsupported schema
    # before any Runtime can initialize it. Task lock protects graph lineage.
    with closing(ro_connect(store.root / "graph.sqlite")) as connection:
        connection.execute("BEGIN")
        status = projection_status(readonly_graph(connection), job, receipt)
    if status == "ready":
        projected(store, authority)
        return {"request": authority["request"], "resolution_ref": authority["ref"], "projection": "ready"}
    runtime = Runtime(store, Nexus(store, no_execution))
    try:
        result = project(runtime, job, authority)
        projected(store, authority)
        return result
    finally:
        runtime.close()


# No-op boundaries: a failed/abrupt caller leaves the durable A/B/C facts intact.
def prepared(store, receipt):
    pass


def committed(store, receipt):
    pass


def projected(store, authority):
    pass
