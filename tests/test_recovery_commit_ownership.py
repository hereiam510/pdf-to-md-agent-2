"""Publication must never adopt or overwrite a foreign catalog row after A."""
import pytest

from pdfmd.storage import Conflict
from test_accepted_evidence_recovery import historical
from test_runtime import tool


@pytest.mark.parametrize("collision", ["blob", "operation", "context_disposition", "conflict_resolution"])
def test_foreign_publication_target_aborts_the_entire_catalog_decision(setup, monkeypatch, collision):
    import pdfmd.recovery as recovery
    store, job, key, _, _ = historical(setup, monkeypatch, "chat_completions", calls=
        [tool("context_update", {"notes": "Preserved intent"}, "ctx")] if collision == "context_disposition" else None)
    diagnosis = recovery.diagnose(store.root, job["id"])
    injected = {}
    def after_a(store, receipt):
        op = receipt["operations"][0]
        if collision == "blob":
            candidate = next(b for b in store.records("blob", job["id"]) if b["kind"] == "recovery_candidate"
                and b["meta"].get("operation") == op["operation"] and "args_hash" in b["meta"])
            identity, value = op["result_ref"], {**candidate, "ref": op["result_ref"], "kind": "tool_result"}
        elif collision == "operation":
            identity, value = op["operation"], op["settled"]
        elif collision == "context_disposition":
            kind, identity, value = receipt["context"]["writes"][0]
            assert kind == collision
        else:
            identity = key
            value = {"job": job["id"], "request": key, "ref": receipt["ref"], "choice": receipt["choice"], "basis": receipt["basis"]}
        store.put(collision, identity, "foreign-task", value)
        injected.update(identity=identity, value=value)
    monkeypatch.setattr(recovery, "prepared", after_a)
    with pytest.raises((ValueError, Conflict)):
        recovery.resolve(store, job["id"], key, diagnosis["basis"])
    assert store.get(collision, injected["identity"], job="foreign-task") == injected["value"]
    assert not store.records("conflict_resolution", job["id"])
    assert not store.records("operation", job["id"])
    assert not store.maybe("blob", f"conflict-resolution:{key}")
    assert not store.maybe("blob", f"candidate:{key}:0")
