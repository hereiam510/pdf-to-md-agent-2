"""T3b review corrections AR-T3B-01..04 and the enriched AR-T3A-02 residual. Synthetic, no provider."""
from hashlib import sha256
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

import pdfmd.documents as documents_module
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


def ev(ref, page=1, note="observed", region=None):
    return [{"ref": ref, "physical_page": page, "region": region, "note": note}]


def create(key, image, label, page=1, basis=None, **extra):
    facts = {"image_ref": image["ref"],
             "description": {"full": label, "filename": label, "language": "en", "punctuation": "ascii", "basis": []},
             "locations": [{"physical_page": page, "region": None, "basis": basis or ev(image["ref"], page)}], **extra}
    return {"kind": "create", "client_key": key, "facts": facts}


def body(markdown, changes, *, base=None, pages=None, **extra):
    return {"base_version": base, "expected_head": base, "replace_blocks": [{"id": "b", "pages": [1], "markdown": markdown}],
            "page_updates": pages or {"1": {"disposition": "included"}}, "asset_changes": changes, **extra}


def call(d, job, op, args):
    return d.execute(job, op, "edit_document", json.dumps(args, ensure_ascii=False))


@pytest.fixture
def two_pages(tmp_path):
    pdf = tmp_path / "two.pdf"
    with pymupdf.open() as document:
        for number in (1, 2):
            document.new_page(width=300, height=200).insert_text((20, 40), f"Synthetic page {number}")
        document.save(pdf)
    d = Dispatcher(Store(tmp_path / "workspace"))
    job = d.evidence.create_job(str(pdf), "Review corrections.")["id"]
    return d, job, d.evidence.render_page(job, 1, 50), d.evidence.render_page(job, 2, 50)


# AR-T3B-01 ------------------------------------------------------------------
def test_location_must_agree_with_the_image_derivation(two_pages):
    d, job, page1, page2 = two_pages
    mismatch = call(d, job, "mismatch", body("![x](asset:new/x)", [create("x", page1, "Actual first page", page=2)]))
    assert mismatch["data"]["error_code"] == "ASSET_FACT_INVALID" and "recorded from physical page [1]" in mismatch["data"]["error"]
    claimed = create("x", page1, "Claimed", page=2, basis=ev(page1["ref"], 1))
    unsupported = call(d, job, "unsupported", body("![x](asset:new/x)", [claimed]))
    assert unsupported["data"]["error_code"] == "ASSET_FACT_INVALID" and "differs from the image's recorded page" in unsupported["data"]["error"]
    assert d.store.get("job", job)["head"] is None
    # A genuine repeated occurrence on page 2 cites separate page-2 evidence.
    repeated = create("x", page1, "Repeated", page=2, basis=ev(page2["ref"], 2, "same picture also printed on page 2"))
    ok = call(d, job, "repeated", body("![x](asset:new/x)", [repeated]))
    assert ok["ok"], ok
    assert ok["data"]["asset_changes"][0]["asset_path"] == "assets/Repeated-i2.png"


def test_dangling_wrong_kind_and_off_region_evidence_rejects_in_every_scope(two_pages):
    d, job, page1, page2 = two_pages
    missing = [{"ref": "does-not-exist", "physical_page": 1, "region": None, "note": "n"}]
    cases = {
        "printed": body("Text", [], pages={"1": {"disposition": "included", "printed": "58", "printed_basis": missing}},
                        source_update={"kind": "book"}),
        "source": body("Text", [], source_update={"title": {"state": "known", "value": "T", "basis": missing, "alternatives": []}}),
        "caption": body("![x](asset:new/x)", [create("x", page1, "C", caption={"state": "known", "value": "Cap", "basis": missing, "alternatives": []})]),
    }
    for name, args in cases.items():
        result = call(d, job, name, args)
        assert result["data"]["error_code"] == "ASSET_NOT_OWNED" and "does-not-exist" in result["data"]["error"], (name, result)
    candidate = call(d, job, "candidate-ref", body("Text", [], source_update={"title": {
        "state": "known", "value": "T", "basis": [{"ref": "candidate:printed", "physical_page": None, "region": None, "note": "n"}],
        "alternatives": []}}))
    assert candidate["data"]["error_code"] == "ASSET_FACT_INVALID" and "candidate record" in candidate["data"]["error"]
    crop = d.evidence.render_page(job, 1, 72, region=[0, 0, 100, 100])
    off = call(d, job, "off-region", body("![x](asset:new/x)", [create("x", crop, "Crop", basis=ev(crop["ref"], 1, region=[150, 120, 200, 180]))]))
    assert off["data"]["error_code"] == "ASSET_FACT_INVALID" and "outside the region" in off["data"]["error"]
    assert d.store.get("job", job)["head"] is None
    # A caption read from another page's evidence is legitimate and not forced to the image page.
    caption = {"state": "known", "value": "Caption printed overleaf", "basis": ev(page2["ref"], 2), "alternatives": []}
    ok = call(d, job, "caption-ok", body("![x](asset:new/x)", [create("x", page1, "Figure", caption=caption)]))
    assert ok["ok"], ok


# AR-T3B-02 ------------------------------------------------------------------
def test_null_source_facts_reject_and_a_damaged_base_is_repairable(two_pages, monkeypatch):
    d, job, page1, _ = two_pages
    for field in ("title", "creators", "kind"):
        result = call(d, job, f"null-{field}", body("Text", [], source_update={field: None}))
        assert not result["ok"] and f"cannot be null: {field}" in result["data"]["error"]
    # Reproduce a base saved before the fix: a null title in source_facts.
    real = documents_module.default_source
    monkeypatch.setattr(documents_module, "default_source", lambda *a: {**real(*a), "title": None})
    monkeypatch.setattr(documents_module, "validate_source", lambda source: None)
    damaged = call(d, job, "damaged", body("Text", [], source_update={"kind": "book"}))
    monkeypatch.undo()
    v = damaged["data"]["version_id"]
    assert d.documents.version(job, v)["source_facts"]["title"] is None
    blocked = call(d, job, "blocked", body("![x](asset:new/x)", [create("x", page1, "After")], base=v))
    assert blocked["data"]["error_code"] == "ASSET_FACT_INVALID" and "source_update.title" in blocked["data"]["error"]
    repaired = call(d, job, "repaired", body("![x](asset:new/x)", [create("x", page1, "After")], base=v,
                                             source_update={"title": {"state": "unknown", "value": None, "basis": [], "alternatives": []}}))
    assert repaired["ok"], repaired
    r = repaired["data"]["version_id"]
    assert d.documents.version(job, r)["source_facts"]["title"]["state"] == "unknown"
    # An explicit empty list is a valid value, distinct from null (unchanged embedded facts, so allowed).
    empty = call(d, job, "empty-list", body("Text", [], base=r, source_update={"creators": []}))
    assert empty["ok"], empty


# AR-T3B-03 ------------------------------------------------------------------
@pytest.mark.parametrize("crash_at", ["before_enrichment", "after_staging"])
def test_resumed_operation_keeps_its_reserved_name_and_failed_operations_release(two_pages, monkeypatch, crash_at):
    d, job, page1, _ = two_pages
    requests = {op: body("![x](asset:new/x)", [create("x", page1, "Reserved")]) for op in ("op1", "op2")}
    monkeypatch.setattr(documents_module.Documents, "_release", lambda *a, **k: None)  # process loss: nothing settles
    if crash_at == "before_enrichment":
        monkeypatch.setattr(documents_module, "enrich", lambda *a: (_ for _ in ()).throw(RuntimeError("crash")))
    else:
        real_open = Path.open
        def crash_open(self, mode="r", *a, **kw):
            if mode == "xb" and self.name == "manifest.json":
                raise RuntimeError("crash")
            return real_open(self, mode, *a, **kw)
        monkeypatch.setattr(Path, "open", crash_open)
    for op, request in requests.items():
        with pytest.raises(RuntimeError):
            d.documents.edit(job, op, request, op + "-hash", "candidate:none")
    monkeypatch.undo()
    names = {r["operation"]: r["name"] for r in d.store.records("asset_name", job)}
    assert names == {"op1": "Reserved-i1.png", "op2": "Reserved-i1 (2).png"}
    d.documents._release(job, "op1")  # op1 settles as a failure
    resumed = d.documents.edit(job, "op2", requests["op2"], "op2-hash", "candidate:none")
    assert resumed["asset_changes"][0]["asset_path"] == "assets/Reserved-i1 (2).png"
    statuses = {(r["name"], r["status"]) for r in d.store.records("asset_name", job)}
    assert statuses == {("Reserved-i1.png", "released"), ("Reserved-i1 (2).png", "assigned")}


def test_settled_failure_releases_every_pending_name_of_the_operation(two_pages, monkeypatch):
    d, job, page1, _ = two_pages
    request = body("![a](asset:new/a) ![b](asset:new/b)", [create("a", page1, "First"), create("b", page1, "Second")])
    real_enrich = documents_module.enrich

    def crash_on_second(store, ref, job, values, folder):
        if "Second" in values["title"]["x-default"]:
            raise RuntimeError("crash")
        return real_enrich(store, ref, job, values, folder)
    monkeypatch.setattr(documents_module.Documents, "_release", lambda *a, **k: None)
    monkeypatch.setattr(documents_module, "enrich", crash_on_second)
    with pytest.raises(RuntimeError):
        d.documents.edit(job, "both", request, "both-hash", "candidate:none")
    monkeypatch.undo()
    assert {r["status"] for r in d.store.records("asset_name", job)} == {"pending"}
    d.documents._release(job, "both")
    assert {r["status"] for r in d.store.records("asset_name", job)} == {"released"}


# AR-T3B-04 ------------------------------------------------------------------
def test_http_keys_are_scoped_by_task_and_replay_after_a_newer_head(two_pages, tmp_path):
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app
    d, job, page1, _ = two_pages
    other = d.evidence.create_job(str(tmp_path / "two.pdf"), "Second task.")["id"]

    def forbidden(request):
        raise AssertionError("No provider request is allowed.")
    app = create_app(d.store.root, "synthetic-only", transport=httpx.MockTransport(forbidden))
    text = {"base_version": None, "expected_head": None, "replace_blocks": [{"id": "b", "pages": [1], "markdown": "Text"}],
            "page_updates": {"1": {"disposition": "included"}}}
    with TestClient(app, headers={"Authorization": "Bearer synthetic-only"}) as client:
        key = {"Idempotency-Key": "desktop:same-key"}
        first = client.post(f"/jobs/{job}/edit", json=text, headers=key).json()
        second = client.post(f"/jobs/{other}/edit", json=text, headers=key).json()
        assert first["ok"] and second["ok"] and first["data"]["version_id"] != second["data"]["version_id"]
        head = first["data"]["version_id"]
        newer = client.post(f"/jobs/{job}/edit", json={**text, "base_version": head, "expected_head": head},
                            headers={"Idempotency-Key": "desktop:next"}).json()
        assert newer["ok"]
        lost_response_retry = client.post(f"/jobs/{job}/edit", json=text, headers=key).json()
        assert lost_response_retry["data"] == first["data"]
    assert d.store.get("job", job)["head"] == newer["data"]["version_id"]


# AR-T3A-02 enriched residual -------------------------------------------------
def test_corrupt_enriched_object_restores_from_a_verified_saved_copy(two_pages):
    d, job, page1, _ = two_pages
    created = call(d, job, "create", body("![x](asset:new/x)", [create("x", page1, "Kept")]))
    v1 = created["data"]["version_id"]
    change = created["data"]["asset_changes"][0]
    obj = d.store.root / "objects" / change["enriched_sha256"]
    obj.write_bytes(b"\x00" * obj.stat().st_size)  # same-length corruption
    reuse = call(d, job, "reuse", {"base_version": v1, "expected_head": v1,
                                   "replace_blocks": [{"id": "b", "pages": [1], "markdown": f"[again](asset:id/{change['occurrence_id']})"}]})
    assert reuse["ok"], reuse
    assert sha256(obj.read_bytes()).hexdigest() == change["enriched_sha256"]
    assert any(e["type"] == "enriched_object_restored" for e in d.store.events(job))


def test_unrecoverable_enriched_and_original_failures_give_accurate_guidance(tmp_path):
    fixtures = Path(__file__).parents[2] / "fixtures" / "pdf"
    d = Dispatcher(Store(tmp_path / "workspace"))
    job = d.evidence.create_job(str(fixtures / "rgb-jpeg.pdf"), "Guidance.")["id"]
    with pymupdf.open(fixtures / "rgb-jpeg.pdf") as pdf:
        xref = pdf[0].get_images()[0][0]
    jpeg = d.evidence.extract_image(job, 1, xref)
    created = call(d, job, "create", body("![x](asset:new/x)", [create("x", jpeg, "Figure")]))
    v1 = created["data"]["version_id"]
    change = created["data"]["asset_changes"][0]
    reuse = {"base_version": v1, "expected_head": v1,
             "replace_blocks": [{"id": "b", "pages": [1], "markdown": f"![again](asset:id/{change['occurrence_id']})"}]}
    original = d.store.root / "objects" / jpeg["originals"][0]["path"].split("-", 1)[1].rsplit(".", 1)[0]
    saved_original = original.read_bytes()
    original.write_bytes(b"\x00" * len(saved_original))
    failed = call(d, job, "original", reuse)
    assert failed["data"]["error_code"] == "ASSET_INTEGRITY_FAILED"
    assert "retained original stream" in failed["data"]["error"] and "extract_image" in failed["data"]["error"]
    assert "image destination" in failed["data"]["error"]
    original.write_bytes(saved_original)
    # A later version without the image becomes the base; then the only saved
    # copy (in v1) and the object are both damaged, so nothing verified remains.
    v2 = call(d, job, "drop", {"base_version": v1, "expected_head": v1,
                               "replace_blocks": [{"id": "b", "pages": [1], "markdown": "No image."}]})["data"]["version_id"]
    obj = d.store.root / "objects" / change["enriched_sha256"]
    obj.write_bytes(b"\x00" * obj.stat().st_size)
    saved = d.documents.root / v1 / change["asset_path"]
    saved.write_bytes(b"\x00" * saved.stat().st_size)
    lost = call(d, job, "lost", {**reuse, "base_version": v2, "expected_head": v2})
    assert lost["data"]["error_code"] == "ASSET_INTEGRITY_FAILED"
    assert "Re-extracting the source image cannot rebuild it" in lost["data"]["error"] and change["asset_path"] in lost["data"]["error"]
    assert d.store.get("job", job)["head"] == v2
