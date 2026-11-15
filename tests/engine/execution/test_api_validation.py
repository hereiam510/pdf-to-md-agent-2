import json

import httpx
import pytest
from fastapi.testclient import TestClient

from pdfmd.server import create_app
from tests.engine.documents.test_documents import edit
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native


@pytest.fixture
def client(tmp_path):
    def reply(request):
        return httpx.Response(200, json=native("chat_completions", tool("report", {
            "state": "waiting", "message": "Offline validation fixture."})))
    with TestClient(create_app(tmp_path / "api", "local", transport=httpx.MockTransport(reply)),
                    headers={"Authorization": "Bearer local"}) as client:
        yield client


@pytest.mark.parametrize("suffix,body,field", [
    ("", {"scope": "all"}, "path"),
    ("", {"path": "source.pdf"}, "scope"),
    ("", {"path": [], "scope": "all"}, "path"),
    ("", {"path": "source.pdf", "scope": 42}, "scope"),
    ("/task/start", None, "body"),
    ("/task/start", {"scripts": []}, "scripts"),
    ("/task/start", {"amendment": {}}, "amendment"),
    ("/task/settings", None, "body"),
    ("/task/settings", {"route": []}, "route"),
    ("/task/settings", {"limits": 42}, "limits"),
    ("/task/edit", {"base_version": None}, "expected_head"),
    ("/task/edit", {"expected_head": None}, "base_version"),
    ("/task/edit", {**edit(), "replace_blocks": [{"id": "body", "pages": [1]}]}, "markdown"),
    ("/task/edit", {**edit(), "replace_blocks": [{"id": "body", "pages": [1], "markdown": []}]}, "markdown"),
    ("/task/export", {"destination": "out.zip"}, "version_id"),
    ("/task/export", {"version_id": "version"}, "destination"),
    ("/task/export", {"version_id": [], "destination": "out.zip"}, "version_id"),
    ("/task/export", {"version_id": "version", "destination": {}}, "destination"),
    ("/task/accepted-evidence-resolution", {"basis": "basis"}, "request"),
    ("/task/accepted-evidence-resolution", {"request": "request"}, "basis"),
    ("/task/accepted-evidence-resolution", {"request": [], "basis": "basis"}, "request"),
    ("/task/accepted-evidence-resolution", {"request": "request", "basis": {}}, "basis"),
])
def test_malformed_body_names_field(client, suffix, body, field):
    response = client.post("/jobs" + suffix, json=body)
    assert response.status_code == 422, response.text
    assert any(field in error["loc"] for error in response.json()["detail"])


@pytest.mark.parametrize("suffix", ["start", "settings"])
@pytest.mark.parametrize("patch,field", [
    ({"route": {"context_tokens": []}}, "context_tokens"),
    ({"limits": {"max_requests": {}}}, "max_requests"),
])
def test_nested_settings_errors_are_client_errors(client, source, route, suffix, patch, field):
    job = client.post("/jobs", json={"path": str(source), "scope": "all", "route": route}).json()
    response = client.post(f"/jobs/{job['id']}/{suffix}", json={"key": "offline", **patch} if suffix == "start" else patch)
    assert response.status_code == 400, response.text
    assert field in response.json()["error"]
    assert not client.app.state.engine.store.records("request", job["id"])


def test_import_nested_route_missing_field(client, source):
    response = client.post("/jobs", json={"path": str(source), "scope": "all", "route": {}})
    assert response.status_code == 422
    assert any("endpoint" in error["loc"] for error in response.json()["detail"])


def test_edit_validation_retains_original_candidate(client, source):
    job = client.post("/jobs", json={"path": str(source), "scope": "all"}).json()
    body = {**edit(), "replace_blocks": [{"id": "body", "pages": [1], "markdown": "保留 😀"}],
            "expected_head": 7}
    response = client.post(f"/jobs/{job['id']}/edit", json=body)
    assert response.status_code == 422
    store = client.app.state.engine.store
    [candidate] = [b for b in store.records("blob", job["id"]) if b["kind"] == "candidate"]
    assert json.loads(store.bytes(candidate["ref"], job["id"])) == body
    assert store.get("job", job["id"])["head"] is None


def test_valid_desktop_calls_and_defaults(client, source, route, tmp_path):
    imported = client.post("/jobs", json={"path": str(source), "scope": "all"})
    assert imported.status_code == 200
    job = imported.json()["id"]
    assert client.post(f"/jobs/{job}/settings", json={}).status_code == 200
    settings = client.post(f"/jobs/{job}/settings", json={"route": route, "limits": {"max_requests": 2}})
    assert settings.status_code == 200
    assert settings.json()["limits"]["max_requests"] == 2
    saved = client.post(f"/jobs/{job}/edit", json=edit(), headers={"Idempotency-Key": "desktop-edit"})
    assert saved.status_code == 200 and saved.json()["ok"]
    version = saved.json()["data"]["version_id"]
    exported = client.post(f"/jobs/{job}/export", json={"version_id": version, "destination": str(tmp_path / "output.zip")})
    assert exported.status_code == 200 and exported.json()["verified"]
    started = client.post(f"/jobs/{job}/start", json={"key": "offline", "amendment": "Continue.", "scripts": False})
    assert started.status_code == 200
    engine = client.app.state.engine
    engine.futures[job].result(timeout=30)
    current = engine.store.get("job", job)
    assert current["amendments"] == ["Continue."] and current["status"] == "waiting"


def test_direct_conflict_selection_uses_native_validation(client):
    with pytest.raises(ValueError, match="request"):
        client.app.state.engine.resolve_conflict("task", {"basis": "basis"})
