import json

import pytest
from fastapi.testclient import TestClient

from pdfmd.documents import render
from pdfmd.schema import Route
from pdfmd.server import create_app
from pdfmd.tools import Dispatcher


def test_loopback_api_rejects_missing_or_wrong_token(tmp_path):
    with TestClient(create_app(tmp_path / "workspace", "local-secret")) as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/health", headers={"Authorization": "Bearer local-secret"}).json()["ready"]


def test_untrusted_html_and_remote_endpoint_guards(route):
    output = render('<script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(1)"><p>Keep me</p>')
    assert "<script>" not in output and "onerror=" not in output and "javascript:" not in output
    assert "Keep me" in output
    for endpoint in ["http://example.com/v1/chat/completions", "https://user:password@example.com/v1/chat/completions", "https://example.com/v1/chat/completions?key=secret"]:
        with pytest.raises(ValueError):
            Route.model_validate({**route, "endpoint": endpoint})


def test_scripts_require_process_opt_in_and_keep_complete_logs(setup):
    store, job = setup
    args = json.dumps({"code": "import os, pymupdf\nprint('x' * 10000)\nprint(pymupdf.open(os.environ['PDFMD_SOURCE']).page_count)\n", "timeout_seconds": 30})
    disabled = Dispatcher(store).execute(job["id"], "off", "run_script", args)
    assert not disabled["ok"]
    enabled = Dispatcher(store, scripts=True).execute(job["id"], "on", "run_script", args)
    assert enabled["ok"] and enabled["data"]["exit_code"] == 0
    assert not enabled["data"]["preview_complete"]
    assert len(store.bytes(enabled["data"]["logs"]["stdout"], job["id"])) > 10000
