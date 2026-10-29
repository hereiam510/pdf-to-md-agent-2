"""Offline desktop fixture and source-led export audit; no real-task access."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_accepted_evidence_recovery import historical
from test_continuation import delivery
from test_diagnostic_attribution_reasons import two_attempts, head_refusal_fixture
from pdfmd.recovery import inspection


def hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def prepare(directory, protocol, mode):
    route = {"endpoint": "https://synthetic.invalid/v1/" + ("responses" if protocol == "responses" else "chat/completions"),
        "model": "offline-attribution-only", "protocol": protocol, "context_tokens": 65536, "output_tokens": 2048}
    store, job, version, image, source = delivery.__wrapped__(directory, route)
    # A second explicit saved version tests selected-version export separately
    # from latest-head lookup. Both retain the same source text and image.
    from pdfmd.documents import Documents
    from pdfmd.tools import Dispatcher
    blocks = Documents(store).version(job["id"], version)["content"]["blocks"]
    edited = Dispatcher(store).execute(job["id"], "manual-version", "edit_document", json.dumps({
        "base_version": version, "expected_head": version, "replace_blocks": blocks + [
            {"id": "manual-note", "pages": [2], "markdown": "Manual retained note."}], "claim": "complete"}))
    head = edited["data"]["version_id"]
    if mode == "attribution":
        store, job, key, (a, b), raw, _ = two_attempts((store, job), protocol)
        extra = {"a": a, "b": b, "raw_hex": raw.hex(), "stream_ref": f"raw-stream:{a}", "mock_sends": 2}
    else:
        with pytest.MonkeyPatch.context() as patch:
            store, job, key, _, _ = head_refusal_fixture((store, job), patch, protocol)
        # Keep an independent explicit version readable for source/export checks.
        (store.root / "versions" / head / "document.json").rename(directory / "preserved-head-document.json")
        store.update_job(job["id"], status="blocked", stop_reason="accepted_evidence_conflict")
        extra = {}
    value = {"job": job["id"], "request": key, "version": version, "head": head,
        "image": image, "source": str(source), "mode": mode, "actual_network_sends": 0, **extra}
    (directory / "fixture.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def verify(directory):
    value = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    before = hashes(directory / "workspace")
    with inspection(directory / "workspace", value["job"]) as (view, _, _):
        folder = view.root / "versions" / value["version"]
        with zipfile.ZipFile(directory / "delivery.zip") as archive, pymupdf.open(value["source"]) as pdf:
            expected = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
            assert set(archive.namelist()) == expected
            for name in archive.namelist():
                assert archive.read(name) == (folder / name).read_bytes()
            markdown = archive.read("document.md").decode("utf-8")
            lines = [line for page in pdf for line in page.get_text().splitlines()]
            assert all(line in markdown for line in lines) and "Manual retained note." not in markdown
            assert view.bytes(view.get("job", value["job"])["source_ref"], value["job"]) == Path(value["source"]).read_bytes()
            image = pymupdf.Pixmap(archive.read(value["image"]["asset_path"]))
            original = pdf[1].get_pixmap(dpi=144, alpha=False)
            assert image.samples == original.samples and (image.width, image.height) == (original.width, original.height)
            assert view.bytes(value["stream_ref"], value["job"]) == bytes.fromhex(value["raw_hex"])
            report = {"verified": True, "explicit_version": value["version"], "different_head": value["head"],
                "source_lines": lines, "image_pixels": [image.width, image.height], "exact_member_set": sorted(expected),
                "raw_sha256": sha256(bytes.fromhex(value["raw_hex"])).hexdigest(), "actual_network_sends": 0}
    assert hashes(directory / "workspace") == before
    report["audit_unchanged"] = True
    (directory / "source-export-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    action, path, *args = sys.argv[1:]
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    if action == "prepare": result = prepare(directory, *args)
    elif action == "hash": result = hashes(directory / "workspace")
    elif action == "verify": result = verify(directory)
    else: raise ValueError(action)
    print(json.dumps(result))
