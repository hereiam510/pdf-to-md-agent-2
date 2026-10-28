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
    def __init__(self, root, connection):
        self.root, self.connection = Path(root), connection
        connection.row_factory = sqlite3.Row

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
            view = ReadView(root, catalog)
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


def inspect_current(view, graph, snapshot, job):
    current = view.get("job", job)
    if current.get("head"):
        verify_version(view, job, current["head"])
    state = snapshot.values
    if not state or not snapshot.next:
        return unavailable("no_resumable_request", "No current resumable request exists."), None
    key = state.get("pending") or f"{job}:{state['seq']}:{state['revision']}"
    request = view.maybe("request", key)
    if not request:
        return unavailable("no_resumable_request", "No frozen request at the current graph position."), None
    base = {"job": job, "request": key, "head": current["head"], "versions": [v["id"] for v in view.records("version", job)],
            "publication": {"status": "published" if request.get("accepted_ref") else "unpublished",
                            "accepted_ref": request.get("accepted_ref"), "request_status": request["status"]}}
    if not view.maybe("blob", f"accepted:{key}"):
        return {**unavailable("missing_staging", "No complete accepted staging; raw terminal alone cannot authorize this recovery."), **base}, None
    try:
        checked = inspect_acceptance(view, job, key)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {**unavailable("evidence_unconfirmed", str(exc)), **base,
                **getattr(exc, "observations", {})}, None
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
        return {**unavailable("evidence_unconfirmed", str(exc)), **base, **facts}, None
    basis_records = catalog_basis(view, job)
    basis = digest({"catalog": basis_records, "graph": checkpoint_basis(snapshot)})
    eligible = checked["boundary"]["status"] == "finish_conflict" and all(op["certainty"] != "unknown" for op in ops)
    reasons = [] if eligible else ["Unknown tool effect prevents local resolution." if any(op["certainty"] == "unknown" for op in ops)
                                 else "Receive evidence is compatible; use ordinary validated continuation." if checked["boundary"]["status"] == "compatible"
                                 else "Receive failure is outside the supported finish-boundary class."]
    display = {**base, **facts, "status": "eligible" if eligible else "unsupported", "eligible": eligible, "basis": basis, "reasons": reasons,
        "attempt": checked["attempt_id"], "accepted_staging_ref": checked["ref"], "native_ref": checked["native"]["ref"], "stream_ref": checked["stream_ref"],
        "storage": {"status": "verified"}, "provenance": {"status": "verified"},
        "reconstruction": {"status": "matches" if checked["reconstructed"] else "unknown"}, "receive_boundary": checked["boundary"],
        "effects": {"status": "unknown" if any(op["certainty"] == "unknown" for op in ops) else "established",
                    "operations": [{k: op[k] for k in ("operation", "certainty", "candidate_ref", "prior_skipping")} for op in ops]},
        "original_usage": checked["attempt"].get("usage"), "saved_usage": checked["accepted"].get("usage"),
        "finished": checked["attempt"].get("finished"), "transition": transition["case"]}
    return display, {"checked": checked, "operations": ops, "transition": transition,
                     "catalog": basis_records, "graph": checkpoint_basis(snapshot), "job": current}


def diagnose(root, job):
    try:
        with existing_task_lease(Path(root) / f"task-{job}.lock") as leased:
            with inspection(root, job, locked=leased) as (view, graph, snapshot):
                committed = view.records("conflict_resolution", job)
                state = snapshot.values
                pending = state.get("pending") or (f"{job}:{state['seq']}:{state['revision']}" if state else None)
                if committed and (view.maybe("conflict_resolution", pending) or not view.maybe("blob", f"accepted:{pending}")):
                    latest = view.maybe("conflict_resolution", pending) or committed[-1]
                    receipt = view.json(latest["ref"], job)
                    try:
                        projection = projection_status(graph, job, receipt)
                        reasons = []
                    except Conflict as exc:
                        projection, reasons = "blocked", [str(exc)]
                    return {"status": "resolved", "eligible": False, "request": latest["request"],
                            "resolution_ref": latest["ref"], "projection": projection, "reasons": reasons,
                            "verification_basis": "committed_resolution", "attempt": receipt["attempt"],
                            "accepted_staging_ref": receipt["accepted_staging_ref"], "receive_boundary": receipt["receive_boundary"],
                            "storage": {"status": "verified_at_resolution"}, "provenance": {"status": "verified_at_resolution"},
                            "reconstruction": {"status": "verified_at_resolution"}, "effects": {"status": "verified_at_resolution"},
                            "publication": {"status": "published" if receipt["original_request"]["accepted_ref"] else "unpublished"}}
                display, _ = inspect_current(view, graph, snapshot, job)
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
    receipt = runtime.store.json(authority["ref"], job)
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
                for blob in aliases:
                    prior = store.get_tx(db, "blob", blob["ref"])
                    if prior and prior != blob:
                        raise Conflict("Recovery alias conflicts with an existing immutable object.")
                    store.put_tx(db, "blob", blob["ref"], job, blob)
                for record in operation_records:
                    store.put_tx(db, "operation", record["id"], job, record)
                for kind, identity, value in ctx["writes"]:
                    store.put_tx(db, kind, identity, job, value)
                store.put_tx(db, "conflict_resolution", key, job, authority)
            committed(store, receipt)
            return finish_projection(store, job, authority)
    except Timeout as exc:
        raise Conflict("Task has an active executor. Stop it before local recovery.") from exc


def finish_projection(store, job, authority):
    from .runtime import Runtime
    from .nexus import Nexus
    # Do not initialize a missing/unsupported graph while completing a decision.
    with inspection(store.root, job, locked=True) as (view, graph, _):
        projection_status(graph, job, view.json(authority["ref"], job))
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
