"""T3b enriched schema 2 saves (engine part). Synthetic sources, no provider calls.

Creates occurrences through edit_document asset_changes, assigns readable
collision-only names, embeds the provenance record as primary XMP with the
product-selected module and publishes the dependency union with originals.
Independent ExifTool readback is part of the integrated check, not these tests.
"""
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pymupdf
import pytest

import pdfmd.documents as documents_module
from pdfmd import asset_catalog, primary_xmp
from pdfmd.asset_naming import NameBudgetError, build, comparison_key
from pdfmd.asset_references import analyze, asset_uri, classify
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher

FIXTURES = Path(__file__).parents[2] / "fixtures" / "pdf"


def call(d, job, op, args):
    return d.execute(job, op, "edit_document", json.dumps(args, ensure_ascii=False))


def ev(ref, note="observed", page=1):
    return [{"ref": ref, "physical_page": page, "region": None, "note": note}]


def facts(image, label, *, figure=None, page=1, language="zh-Hant", punctuation="fullwidth", full=None):
    return {"image_ref": image["ref"],
            "description": {"full": full or f"完整描述：{label}", "filename": label, "language": language,
                            "punctuation": punctuation, "basis": ev(image["ref"], "image content", page)},
            "figure": ({"state": "known", "value": figure, "basis": ev(image["ref"], "figure label", page), "alternatives": []}
                       if figure else {"state": "none", "value": None, "basis": ev(image["ref"], "no figure label", page), "alternatives": []}),
            "locations": [{"physical_page": page, "region": None, "basis": ev(image["ref"], "location", page)}]}


def create(key, image, label, **kw):
    return {"kind": "create", "client_key": key, "facts": facts(image, label, **kw)}


def args(markdown, changes, *, base=None, printed=None, evidence=None):
    page = {"disposition": "included"}
    if printed is not None:
        page.update(printed=printed, printed_basis=ev(evidence, "printed label at page foot"))
    return {"base_version": base, "expected_head": base, "replace_blocks": [{"id": "b", "pages": [1], "markdown": markdown}],
            "page_updates": {"1": page}, "asset_changes": changes}


@pytest.fixture
def jpeg_job(tmp_path):
    d = Dispatcher(Store(tmp_path / "workspace"))
    job = d.evidence.create_job(str(FIXTURES / "rgb-jpeg.pdf"), "Deliver the source figure.")["id"]
    with pymupdf.open(FIXTURES / "rgb-jpeg.pdf") as pdf:
        xref = pdf[0].get_images()[0][0]
    jpeg = d.evidence.extract_image(job, 1, xref)
    png = d.evidence.render_page(job, 1, 72)
    assert jpeg["representation"] == "embedded_stream" and png["extension"] == "png"
    return d, job, jpeg, png


def record_from(data: bytes) -> dict:
    if data.startswith(primary_xmp.PNG_SIG):
        packet = primary_xmp.locate_png_primary(primary_xmp.parse_png(data))["packet"]
    else:
        packet = primary_xmp.locate_jpeg_primary(primary_xmp.parse_jpeg(data))["packet"]
    node = packet.props[(primary_xmp.PDFMD, "RecordJSON")]["node"]
    return json.loads("".join(c.data for c in node.childNodes))


def decoded(data: bytes):
    pix = pymupdf.Pixmap(data)
    return pix.width, pix.height, pix.n, pix.alpha, sha256(pix.samples).hexdigest()


def http_edit(client, job_url, key, body):
    response = client.post(job_url + "/edit", json=body, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return response.json()


def http_export_members(client, job_url, version, destination):
    response = client.post(job_url + "/export", json={"version_id": version, "destination": str(destination)})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["asset_reference_check"]["status"] == "ok"
    with zipfile.ZipFile(result["path"]) as package:
        return {name: package.read(name) for name in package.namelist()}


def test_selected_module_is_the_qualified_candidate():
    assert asset_catalog.module_identity() == asset_catalog.SELECTED_XMP_SHA256
    qualified = Path(__file__).parents[3] / "tools" / "qualification" / "primary_xmp.py"
    assert sha256(qualified.read_bytes()).hexdigest() == asset_catalog.SELECTED_XMP_SHA256


def test_bounded_worker_output_equals_the_qualified_prepare_command(jpeg_job, tmp_path):
    """Invocation recheck: the bounded worker runs the same prepare -> byte-identical output to the CLI."""
    d, job, jpeg, png = jpeg_job
    module = files("pdfmd").joinpath("primary_xmp.py")
    for image, long in ((png, False), (jpeg, False), (jpeg, True)):
        data = d.store.bytes(image["ref"], job)
        values = {"title": {"x-default": "测试图像", "zh-CN": "测试图像"}, "description": {"x-default": "d\r\n中文"},
                  "source": "urn:sha256:" + "a" * 64,
                  "pdfmd": {"SchemaVersion": 1, "OccurrenceId": "1" * 32, "RepresentationId": "2" * 32,
                            "RecordJSON": json.dumps({"long": "大字" * (40000 if long else 10)}, ensure_ascii=False)}}
        (tmp_path / "in").write_bytes(data)
        (tmp_path / "values.json").write_text(json.dumps(values, ensure_ascii=False), "utf-8")
        out = tmp_path / ("out" + str(long) + image["extension"])
        status = subprocess.run([sys.executable, "-B", str(module), "prepare", "--input", str(tmp_path / "in"), "--output", str(out),
                                 "--values", str(tmp_path / "values.json"), "--report", str(tmp_path / "report.json")])
        assert status.returncode == 0
        folder = tmp_path / ("worker" + str(long) + image["extension"])
        assert asset_catalog.enrich(data, values, folder) == out.read_bytes()
        assert not folder.exists()  # removed after an accepted preparation


def test_create_png_and_dct_jpeg_with_readable_names_and_standalone_records(jpeg_job, tmp_path):
    d, job, jpeg, png = jpeg_job
    text = "![圖](asset:new/fig)\n\n[整頁 & 原圖](asset:new/page) `asset:new/fig` <!-- asset:new/page -->"
    result = call(d, job, "create", args(text, [create("fig", jpeg, "新聞基本屬性: 示意/比較", figure="圖4–2"),
                                                 create("page", png, "新聞基本屬性", language="zh-Hant")],
                                         printed="58", evidence=png["ref"]))
    assert result["ok"], result
    changes = {c["client_key"]: c for c in result["data"]["asset_changes"]}
    assert changes["fig"]["asset_path"] == "assets/新聞基本屬性： 示意／比較-p58-圖4–2.jpeg"
    assert changes["page"]["asset_path"] == "assets/新聞基本屬性-p58.png"
    version = result["data"]["version_id"]
    saved = d.documents.version(job, version)
    assert saved["schema_version"] == 2 and saved["asset_policy"]["naming"] == "readable-180-v1"
    markdown = saved["content"]["blocks"][0]["markdown"]
    assert changes["fig"]["asset_uri"] in markdown and "`asset:new/fig`" in markdown and "<!-- asset:new/page -->" in markdown
    roles = {(r.role, classify(r.destination, r.role)[1]) for r in analyze(saved["content"]["blocks"], saved["content"]["pages"]).references}
    assert roles == {("image", changes["fig"]["asset_path"]), ("hyperlink", changes["page"]["asset_path"])}
    folder = d.documents.root / version
    members = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    original = jpeg["originals"][0]["path"]
    assert members == {"document.json", "document.md", "preview.html", "manifest.json", original,
                       changes["fig"]["asset_path"], changes["page"]["asset_path"]}
    assert (folder / original).read_bytes() == d.store.bytes(jpeg["originals"][0]["ref"], job)
    assert d.documents.reference_check(job, version) == {"status": "ok", "issues": []}
    for key, image in (("fig", jpeg), ("page", png)):
        data = (folder / changes[key]["asset_path"]).read_bytes()
        pre = d.store.bytes(image["ref"], job)
        assert data != pre and decoded(data) == decoded(pre)
        assert sha256(data).hexdigest() == changes[key]["enriched_sha256"]
        record = record_from(data)
        entry = saved["asset_catalog"][changes[key]["occurrence_id"]]
        assert record == entry["representation"]["provenance_record"] == saved["assets"][changes[key]["asset_path"]]["provenance"]
        assert record["locations"][0]["printed"] == {"state": "known", "value": "58", "basis": ev(png["ref"], "printed label at page foot"),
                                                     "alternatives": [], "legacy_hint": None}
        assert record["image"]["sha256"] == sha256(pre).hexdigest()
        assert record["naming"]["assigned_basename"] == changes[key]["asset_path"][7:]
    jpeg_record = record_from((folder / changes["fig"]["asset_path"]).read_bytes())
    assert jpeg_record["image"]["originals"][0]["sha256"] == sha256((folder / original).read_bytes()).hexdigest()
    # Replay returns the original receipt; the exported ZIP relocates with the same bytes.
    assert call(d, job, "create", args(text, [create("fig", jpeg, "新聞基本屬性: 示意/比較", figure="圖4–2"),
                                               create("page", png, "新聞基本屬性", language="zh-Hant")],
                                       printed="58", evidence=png["ref"]))["data"] == result["data"]
    exported = d.documents.export(job, version, str(tmp_path / "out" / "export.zip"))
    with zipfile.ZipFile(exported["path"]) as archive:
        archive.extractall(tmp_path / "moved")
    moved = tmp_path / "moved"
    for change in changes.values():
        assert (moved / change["asset_path"]).read_bytes() == (folder / change["asset_path"]).read_bytes()
    alone = tmp_path / "alone"
    alone.mkdir()
    (alone / "renamed copy.jpeg").write_bytes((moved / changes["fig"]["asset_path"]).read_bytes())
    assert record_from((alone / "renamed copy.jpeg").read_bytes())["source"]["source_sha256"] == d.store.get(
        "blob", d.store.get("job", job)["source_ref"], job=job)["sha256"]


def test_correct_one_image_reopens_exports_and_replays_with_historical_bytes(jpeg_job, tmp_path):
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app

    d, job, jpeg, _ = jpeg_job
    old_path = "assets/Source figure-i1.jpeg"
    old_uri = asset_uri(old_path)
    request = args(f"![Figure](asset:new/fig)\n\n[Open figure][fig]\n\nKeep literal `{old_uri}`.",
                   [create("fig", jpeg, "Source figure")])
    request["replace_blocks"].append({"id": "references", "pages": [1], "markdown": "[fig]: asset:new/fig"})
    auth = {"Authorization": "Bearer synthetic-only"}
    job_url = f"/jobs/{job}"

    with TestClient(create_app(d.store.root, "synthetic-only"), headers=auth) as client:
        created = http_edit(client, job_url, "create", request)
        assert created["ok"], created
        [first] = created["data"]["asset_changes"]
        assert first["asset_path"] == old_path
        base = created["data"]["version_id"]
        original_export = http_export_members(client, job_url, base, tmp_path / "original.zip")
        correction = {"base_version": base, "expected_head": base,
                      "asset_changes": [{"kind": "correct", "occurrence_id": first["occurrence_id"],
                                         "changes": {"description": facts(jpeg, "Corrected 圖")["description"]}}]}
        corrected = http_edit(client, job_url, "correct", correction)
        assert corrected["ok"], corrected
        [change] = corrected["data"]["asset_changes"]
        version = corrected["data"]["version_id"]
        assert change["occurrence_id"] == first["occurrence_id"]
        assert change["representation_id"] != first["representation_id"]
        assert change["client_key"] is None and change["previous_path"] == old_path
        assert change["asset_path"] == "assets/Corrected 圖-i1.jpeg"
        newer = http_edit(client, job_url, "newer", {"base_version": version, "expected_head": version, "title": "Later title"})
        assert newer["ok"], newer

    with TestClient(create_app(d.store.root, "synthetic-only"), headers=auth) as client:
        for selected, expected in [(base, first), (version, change)]:
            response = client.get(job_url + "/versions/" + selected)
            assert response.status_code == 200, response.text
            saved = response.json()
            assert saved["version"] == selected and saved["asset_reference_check"]["status"] == "ok"
            path, uri = expected["asset_path"], expected["asset_uri"]
            assert set(saved["assets"]) == {path}
            assert f"![Figure]({uri})" in saved["markdown"] and f"[fig]: {uri}" in saved["markdown"]
            assert f"Keep literal `{old_uri}`." in saved["markdown"]
            [resource] = saved["preview_transfer"]["resources"]
            members = http_export_members(client, job_url, selected, tmp_path / f"{selected}.zip")
            exported_html = members["preview.html"].decode()
            assert f'src="{uri}"' in exported_html and f'href="{uri}"' in exported_html
            assert members["document.md"].decode() == saved["markdown"]
            assert resource["sha256"] == expected["enriched_sha256"] == sha256(members[path]).hexdigest()
            assert record_from(members[path]) == saved["assets"][path]["provenance"]
            assert record_from(members[path])["naming"]["assigned_basename"] == Path(path).name
            assert decoded(members[path]) == decoded(original_export[old_path])
            [original] = saved["originals"]
            assert members[original] == original_export[original]
            if selected == base:
                assert members == original_export
            else:
                assert old_path not in members
                assert record_from(members[path])["description"] == correction["asset_changes"][0]["changes"]["description"]
        assert http_edit(client, job_url, "correct", correction) == corrected

    assert d.store.get("job", job)["head"] == newer["data"]["version_id"]
    assert len(d.store.records("version", job)) == 3
    assert {(name["name"], name["status"]) for name in d.store.records("asset_name", job)} == {
        (Path(old_path).name, "assigned"), (Path(change["asset_path"]).name, "assigned")}


def test_shared_printed_page_correction_rolls_back_reopens_and_links_later(tmp_path, monkeypatch):
    from threading import Event

    from fastapi.testclient import TestClient
    from filelock import FileLock
    from pdfmd.server import create_app

    source = tmp_path / "Shared page.pdf"
    with pymupdf.open(FIXTURES / "rgb-jpeg.pdf") as pdf:
        page = pdf[0]
        page.insert_text((20, page.rect.height - 10), "59")
        xref = page.get_images()[0][0]
        pdf.save(source)
    with pymupdf.open(source) as pdf:
        assert "59" in pdf[0].get_text().split()
    d = Dispatcher(Store(tmp_path / "workspace"))
    job = d.evidence.create_job(str(source), "Verify a shared printed-page correction.")["id"]
    png = d.evidence.render_page(job, 1, 72)
    jpeg = d.evidence.extract_image(job, 1, xref)
    request = args("![Page](asset:new/page)\n\n[Open page][page]\n\n[page]: asset:new/page",
                   [create("page", png, "Page view"), create("figure", jpeg, "Source figure")],
                   printed="58", evidence=png["ref"])
    auth = {"Authorization": "Bearer synthetic-only"}
    job_url = f"/jobs/{job}"

    with TestClient(create_app(d.store.root, "synthetic-only"), headers=auth) as client:
        created = http_edit(client, job_url, "create", request)
        assert created["ok"], created
        old_page, old_figure = created["data"]["asset_changes"]
        base = created["data"]["version_id"]
        original = d.documents.version(job, base)
        before = http_export_members(client, job_url, base, tmp_path / "before.zip")
        correction = {"base_version": base, "expected_head": base,
                      "page_updates": {"1": {"printed": "59", "printed_basis": ev(png["ref"], "59 at the page foot")}}}
        with FileLock(d.store.root / f"task-{job}.lock"):
            blocked = client.post(job_url + "/edit", json=correction, headers={"Idempotency-Key": "locked"})
            assert blocked.status_code == 409
        assert d.store.maybe("operation", f"manual:{job}:locked") is None

        first_ready = Event()
        registered = []
        real_register, real_enrich = Store.blob_from_file, documents_module.enrich

        def register(self, job_id, kind, path, meta=None, **kwargs):
            blob = real_register(self, job_id, kind, path, meta, **kwargs)
            if kind == "enriched_image" and meta["occurrence_id"] == old_page["occurrence_id"]:
                registered.append(blob["ref"])
                first_ready.set()
            return blob

        def fail_after_first(store, ref, job_id, values, folder):
            if ref == jpeg["ref"]:
                assert first_ready.wait(30), "first representation was never registered"
                raise asset_catalog.FactError("Injected failure preparing the second image.", "ASSET_ENRICHMENT_FAILED")
            return real_enrich(store, ref, job_id, values, folder)

        with monkeypatch.context() as patch:
            patch.setattr(Store, "blob_from_file", register)
            patch.setattr(documents_module, "enrich", fail_after_first)
            failed = http_edit(client, job_url, "failed", correction)
        assert not failed["ok"] and failed["data"]["error_code"] == "ASSET_ENRICHMENT_FAILED"
        assert "second image" in failed["data"]["error"]
        assert d.store.json(failed["candidate_ref"], job) == correction
        assert len(registered) == 1 and record_from(d.store.bytes(registered[0], job))["locations"][0]["printed"]["value"] == "59"
        assert d.store.get("job", job)["head"] == base and len(d.store.records("version", job)) == 1
        assert d.documents.version(job, base) == original
        assert http_export_members(client, job_url, base, tmp_path / "after-failure.zip") == before
        assert {(r["name"], r["status"]) for r in d.store.records("asset_name", job)} == {
            ("Page view-p58.png", "assigned"), ("Source figure-p58.jpeg", "assigned"),
            ("Page view-p59.png", "released"), ("Source figure-p59.jpeg", "released")}

        corrected = http_edit(client, job_url, "correct", correction)
        assert corrected["ok"], corrected
        version = corrected["data"]["version_id"]
        by_occurrence = {change["occurrence_id"]: change for change in corrected["data"]["asset_changes"]}
        assert set(by_occurrence) == {old_page["occurrence_id"], old_figure["occurrence_id"]}
        page, figure = (by_occurrence[old["occurrence_id"]] for old in (old_page, old_figure))
        assert page["asset_path"] == "assets/Page view-p59.png"
        assert figure["asset_path"] == "assets/Source figure-p59.jpeg"
        later = http_edit(client, job_url, "link", {"base_version": version, "expected_head": version,
                         "operations": [{"kind": "insert", "after_id": "b", "blocks": [{"id": "linked-figure",
                                         "pages": [1], "markdown": f"[Open figure](asset:id/{figure['occurrence_id']})"}]}]})
        assert later["ok"], later
        latest = later["data"]["version_id"]

    with TestClient(create_app(d.store.root, "synthetic-only"), headers=auth) as client:
        for selected, expected in [(base, [old_page]), (version, [page]), (latest, [page, figure])]:
            response = client.get(job_url + "/versions/" + selected)
            assert response.status_code == 200, response.text
            saved = response.json()
            assert saved["version"] == selected and saved["asset_reference_check"]["status"] == "ok"
            assert set(saved["assets"]) == {change["asset_path"] for change in expected}
            members = http_export_members(client, job_url, selected, tmp_path / f"{selected}.zip")
            assert set(name for name in members if name.startswith("assets/")) == set(saved["assets"])
            assert members["document.md"].decode() == saved["markdown"]
            html = members["preview.html"].decode()
            assert f'src="{expected[0]["asset_uri"]}"' in html and f'href="{expected[0]["asset_uri"]}"' in html
            if selected == base:
                assert members == before
                continue
            assert saved["content"]["pages"]["1"]["printed"] == "59"
            for old, change in [(old_page, page), (old_figure, figure)]:
                representation = saved["asset_catalog"][change["occurrence_id"]]["representation"]
                assert change["previous_path"] == old["asset_path"]
                assert representation["id"] == change["representation_id"] != old["representation_id"]
                assert representation["asset_path"] == change["asset_path"]
                data = d.store.bytes(representation["enriched_ref"], job)
                assert sha256(data).hexdigest() == change["enriched_sha256"]
                record = record_from(data)
                assert record == representation["provenance_record"]
                assert record["locations"][0]["printed"]["value"] == "59"
                assert record["naming"]["assigned_basename"] == Path(change["asset_path"]).name
                assert decoded(data) == decoded(d.store.bytes(representation["image_ref"], job))
                if change in expected:
                    assert members[change["asset_path"]] == data
            if selected == latest:
                assert f'href="{figure["asset_uri"]}"' in html
                [original_path] = saved["originals"]
                assert members[original_path] == d.store.bytes(saved["originals"][original_path]["ref"], job)
        assert http_edit(client, job_url, "correct", correction) == corrected
        assert http_edit(client, job_url, "failed", correction) == failed
    assert d.store.get("job", job)["head"] == latest
    assert len(d.store.records("version", job)) == 3


@pytest.mark.parametrize("schema_version", [1, 2])
def test_edit_streams_every_base_member_even_when_removing_it(jpeg_job, monkeypatch, schema_version):
    d, job, jpeg, png = jpeg_job
    if schema_version == 1:
        markdown = f"![jpeg]({jpeg['asset_path']}) ![png]({png['asset_path']})"
        changes = []
    else:
        markdown = "![jpeg](asset:new/jpeg) ![png](asset:new/png)"
        changes = [create("jpeg", jpeg, "JPEG"), create("png", png, "PNG")]
    saved = call(d, job, "create", args(markdown, changes))
    assert saved["ok"], saved
    base = saved["data"]["version_id"]
    folder = d.documents.root / base
    envelope = d.documents.version(job, base)
    assert envelope.get("schema_version", 1) == schema_version
    assert len(envelope["assets"]) == 2
    [original] = envelope["originals"]
    original_path = folder / original
    original_bytes = original_path.read_bytes()
    read_bytes = Path.read_bytes

    def guard(path):
        assert not (path.is_relative_to(folder) and path != folder / "document.json"), path
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guard)
    update = args("Images removed.", [], base=base)
    original_path.write_bytes(bytes([original_bytes[0] ^ 1]) + original_bytes[1:])
    rejected = call(d, job, "bad-base", update)
    assert not rejected["ok"] and original in rejected["data"]["error"]
    assert d.store.get("blob", rejected["candidate_ref"], job=job)
    assert d.store.get("job", job)["head"] == base
    original_path.write_bytes(original_bytes)
    result = call(d, job, "good-base", update)
    assert result["ok"], result
    new = d.documents.version(job, result["data"]["version_id"])
    assert new["assets"] == new["originals"] == {}


def test_distinct_occurrences_with_equal_pixels_get_separate_identity_and_a_collision_suffix(jpeg_job):
    d, job, jpeg, png = jpeg_job
    result = call(d, job, "twin", args("![a](asset:new/a) ![b](asset:new/b)",
                                        [create("a", png, "Same label"), create("b", png, "Same label")],
                                        printed="58", evidence=png["ref"]))
    assert result["ok"], result
    a, b = result["data"]["asset_changes"]
    assert a["occurrence_id"] != b["occurrence_id"]
    assert a["asset_path"] == "assets/Same label-p58.png" and b["asset_path"] == "assets/Same label-p58（2）.png"
    english = call(d, job, "english", args("![c](asset:new/c)", [create("c", png, "Same label", punctuation="ascii", language="en")],
                                           base=result["data"]["version_id"]))
    assert english["ok"], english
    # "（2）" and " (2)" are different complete names, so the English suffix starts at 2.
    assert english["data"]["asset_changes"][0]["asset_path"] == "assets/Same label-p58 (2).png"
    case = call(d, job, "case", args("![c](asset:new/c)", [create("c", png, "SAME LABEL", punctuation="ascii", language="en")],
                                     base=english["data"]["version_id"]))
    assert case["data"]["asset_changes"][0]["asset_path"] == "assets/SAME LABEL-p58 (3).png"


def test_reuse_removal_and_name_ownership_across_versions(jpeg_job):
    d, job, jpeg, png = jpeg_job
    first = call(d, job, "first", args("![p](asset:new/p)", [create("p", png, "Page view")], printed="58", evidence=png["ref"]))
    v1 = first["data"]["version_id"]
    occurrence = first["data"]["asset_changes"][0]["occurrence_id"]
    path = first["data"]["asset_changes"][0]["asset_path"]
    reuse = call(d, job, "reuse", {"base_version": v1, "expected_head": v1, "replace_blocks": [
        {"id": "b", "pages": [1], "markdown": f"See [the page](asset:id/{occurrence}) again."}]})
    assert reuse["ok"], reuse
    v2 = reuse["data"]["version_id"]
    saved = d.documents.version(job, v2)
    assert saved["asset_catalog"][occurrence]["representation"]["asset_path"] == path and reuse["data"]["asset_changes"] == []
    assert (d.documents.root / v2 / path).read_bytes() == (d.documents.root / v1 / path).read_bytes()
    removed = call(d, job, "remove", {"base_version": v2, "expected_head": v2,
                                      "replace_blocks": [{"id": "b", "pages": [1], "markdown": "No image now."}]})
    v3 = removed["data"]["version_id"]
    assert d.documents.version(job, v3)["assets"] == {} and occurrence in d.documents.version(job, v3)["asset_catalog"]
    assert not (d.documents.root / v3 / path).exists() and (d.documents.root / v1 / path).exists()
    newcomer = call(d, job, "newcomer", args("![n](asset:new/n)", [create("n", png, "Page view")], base=v3))
    assert newcomer["data"]["asset_changes"][0]["asset_path"] == "assets/Page view-p58（2）.png"


def test_unknown_and_legacy_printed_labels_use_physical_locator(jpeg_job):
    d, job, jpeg, png = jpeg_job
    legacy = {"base_version": None, "expected_head": None, "replace_blocks": [{"id": "b", "pages": [1], "markdown": "Draft."}],
              "page_updates": {"1": {"printed": "xii", "disposition": "included"}}}
    v1 = call(d, job, "legacy", legacy)["data"]["version_id"]
    assert d.documents.version(job, v1)["schema_version"] == 1
    result = call(d, job, "fallback", {"base_version": v1, "expected_head": v1,
                                       "replace_blocks": [{"id": "b", "pages": [1], "markdown": "![x](asset:new/x)"}],
                                       "asset_changes": [create("x", png, "Overview")]})
    assert result["ok"], result
    change = result["data"]["asset_changes"][0]
    assert change["asset_path"] == "assets/Overview-i1.png"
    record = d.documents.version(job, result["data"]["version_id"])["asset_catalog"][change["occurrence_id"]]["representation"]["provenance_record"]
    assert record["locations"][0]["printed"] == {"state": "unknown", "value": None, "basis": [], "alternatives": [], "legacy_hint": "xii"}


def test_legacy_hash_path_adoption_and_unadopted_rejection(jpeg_job):
    d, job, jpeg, png = jpeg_job
    old = {"base_version": None, "expected_head": None,
           "replace_blocks": [{"id": "b", "pages": [1], "markdown": f"![old]({png['asset_path']}) and [link]({png['asset_path']})"}],
           "page_updates": {"1": {"printed": "58", "disposition": "included"}}}
    v1 = call(d, job, "old", old)["data"]["version_id"]
    same = {"base_version": v1, "expected_head": v1, "replace_blocks": [{"id": "b", "pages": [1], "markdown": f"![old]({png['asset_path']})"}],
            "asset_changes": [create("other", jpeg, "Other")]}
    unadopted = call(d, job, "unadopted", {**same, "replace_blocks": [{"id": "b", "pages": [1], "markdown": f"![old]({png['asset_path']}) ![o](asset:new/other)"}]})
    assert not unadopted["ok"] and unadopted["data"]["error_code"] == "ASSET_NOT_OWNED"
    assert "legacy_path" in unadopted["data"]["error"]
    adopted = call(d, job, "adopt", {"base_version": v1, "expected_head": v1,
                                     "asset_changes": [{**create("p", png, "Adopted page"), "legacy_path": png["asset_path"]}]})
    assert adopted["ok"], adopted
    change = adopted["data"]["asset_changes"][0]
    assert change["previous_path"] == png["asset_path"] and change["asset_path"] == "assets/Adopted page-i1.png"
    markdown = d.documents.version(job, adopted["data"]["version_id"])["content"]["blocks"][0]["markdown"]
    assert markdown == f"![old]({change['asset_uri']}) and [link]({change['asset_uri']})"


@pytest.mark.parametrize("mutate,code", [
    (lambda a, png, diag: a["asset_changes"][0]["facts"].update(image_ref=diag["ref"]), "ASSET_FACT_INVALID"),
    (lambda a, png, diag: a["replace_blocks"][0].update(markdown="![x](asset:new/missing)"), "ASSET_REFERENCE_INVALID"),
    (lambda a, png, diag: a["asset_changes"][0]["facts"]["locations"][0].update(physical_page=9), "ASSET_FACT_INVALID"),
    (lambda a, png, diag: a["asset_changes"][0]["facts"]["description"].update(filename="長" * 60), "ASSET_NAME_BUDGET"),
    (lambda a, png, diag: a["page_updates"]["1"].pop("printed_basis"), "ASSET_FACT_INVALID"),
    (lambda a, png, diag: a["asset_changes"].append({"kind": "correct", "occurrence_id": "x", "changes": {}}), "ASSET_FACT_INVALID"),
])
def test_rejections_keep_head_candidate_and_release_names(jpeg_job, mutate, code):
    d, job, jpeg, png = jpeg_job
    diagnostic = d.evidence.image(job, d.store.bytes(png["ref"], job), "png", {"purpose": "saved-output diagnostic preview"})
    bad = args("![x](asset:new/x)", [create("x", png, "Retry label")], printed="58", evidence=png["ref"])
    mutate(bad, png, diagnostic)
    result = call(d, job, "bad", bad)
    assert not result["ok"] and result["data"]["error_code"] == code, result
    assert result["data"]["issues"][0]["code"] == code
    assert result["candidate_ref"] in result["data"]["error"]
    assert d.store.get("job", job)["head"] is None
    assert d.store.json(result["candidate_ref"], job) == bad
    if code == "ASSET_NAME_BUDGET":
        details = result["data"]["issues"][0]["details"]
        assert details["maximum"] == 180 and details["remaining_description_bytes"] < 180
    good = call(d, job, "good", args("![x](asset:new/x)", [create("x", png, "Retry label")], printed="58", evidence=png["ref"]))
    assert good["ok"] and good["data"]["asset_changes"][0]["asset_path"] == "assets/Retry label-p58.png"


def test_foreign_task_evidence_is_not_adopted(jpeg_job, tmp_path):
    d, job, jpeg, png = jpeg_job
    other = d.evidence.create_job(str(FIXTURES / "rgb-smask.pdf"), "Other task.")["id"]
    foreign = d.evidence.render_page(other, 1, 72)
    result = call(d, job, "foreign", args("![x](asset:new/x)", [create("x", foreign, "Foreign")]))
    assert result["data"]["error_code"] == "ASSET_NOT_OWNED" and other not in result["data"]["error"]


def test_stale_head_and_write_failure_publish_nothing_and_release_names(jpeg_job, monkeypatch):
    d, job, jpeg, png = jpeg_job
    base = call(d, job, "base", {"base_version": None, "expected_head": None,
                                 "replace_blocks": [{"id": "b", "pages": [1], "markdown": "Draft."}],
                                 "page_updates": {"1": {"disposition": "included"}}})["data"]["version_id"]
    stale = call(d, job, "stale", {**args("![x](asset:new/x)", [create("x", png, "Contested")]), "base_version": None,
                                   "expected_head": None, "mode": "rebuild"})
    assert stale["data"]["error_code"] == "HEAD_CONFLICT" and d.store.get("job", job)["head"] == base
    real_open = Path.open

    def fail_open(self, mode="r", *a, **kw):
        if mode == "xb" and self.name == "manifest.json":
            raise OSError("disk full")
        return real_open(self, mode, *a, **kw)
    monkeypatch.setattr(Path, "open", fail_open)
    failed = call(d, job, "write-fail", args("![x](asset:new/x)", [create("x", png, "Contested")], base=base))
    monkeypatch.undo()
    assert not failed["ok"] and d.store.get("job", job)["head"] == base
    ok = call(d, job, "after", args("![x](asset:new/x)", [create("x", png, "Contested")], base=base))
    assert ok["data"]["asset_changes"][0]["asset_path"] == "assets/Contested-i1.png"


def test_interrupted_preparation_resumes_with_its_reserved_identity(jpeg_job, monkeypatch):
    d, job, jpeg, png = jpeg_job
    request = args("![x](asset:new/x)", [create("x", png, "Resumed")], printed="58", evidence=png["ref"])
    monkeypatch.setattr(documents_module.Documents, "_release", lambda *a: None)  # a crash cannot settle
    monkeypatch.setattr(documents_module, "enrich", lambda *a: (_ for _ in ()).throw(RuntimeError("crash")))
    raw = json.dumps(request, ensure_ascii=False)
    digest = sha256(json.dumps(["edit_document", raw]).encode()).hexdigest()
    with pytest.raises(RuntimeError):
        d.documents.edit(job, "op-crash", request, digest, "candidate:none")
    pending = [r for r in d.store.records("asset_name", job) if r["status"] == "pending"]
    assert len(pending) == 1 and pending[0]["operation"] == "op-crash"
    occurrence = d.store.get("asset_preparation", "op-crash")["ids"]["x"]["occurrence_id"]
    # Another writer cannot take the unresolved operation's name.
    d.store.put("asset_preparation", "op-other", job, {"id": "op-other", "args_hash": "x", "ids": {"k": {}}, "status": "preparing"})
    taken = d.documents._reserve(job, "op-other", "other-occurrence",
                                 lambda n: "Resumed-p58" + ("" if n is None else f"（{n}）") + ".png", "k")
    assert taken[0] == "Resumed-p58（2）.png"
    monkeypatch.undo()
    d.documents._release(job, "op-other", [taken[2]])
    resumed = d.documents.edit(job, "op-crash", request, digest, "candidate:none")
    change = resumed["asset_changes"][0]
    assert change["asset_path"] == "assets/Resumed-p58.png" and change["occurrence_id"] == occurrence
    assert d.store.get("asset_preparation", "op-crash")["status"] == "committed"
    assert {r["status"] for r in d.store.records("asset_name", job)} == {"assigned", "released"}


def test_names_policy_boundaries():
    printed = {1: {"state": "known", "value": "58"}, 2: {"state": "known", "value": "59"}, 4: {"state": "unknown", "value": None}}
    single = [{"kind": "single", "pages": [1]}]
    assert build("A:B<>|?*\"\\/\tx.", single, printed, None, "png", "ascii") == "A：B＜＞｜？＊＂＼／ x-p58.png"
    assert build("CON", single, printed, None, "png", "ascii") == "CON-p58.png"
    assert build("x", [{"kind": "range", "pages": [1, 2]}], printed, None, "png", "ascii") == "x-p58–p59.png"
    assert build("x", single + [{"kind": "single", "pages": [4]}], printed, None, "png", "ascii") == "x-p58&i4.png"
    assert build("...", single, printed, None, "png", "ascii") == "image-p58.png"
    assert build("é", single, printed, None, "png", "ascii") == "é-p58.png"
    fixed = len("-p58.png")
    assert len(build("a" * (180 - fixed), single, printed, None, "png", "ascii").encode()) == 180
    with pytest.raises(NameBudgetError) as overflow:
        build("a" * (181 - fixed), single, printed, None, "png", "ascii")
    assert overflow.value.details["remaining_description_bytes"] == 180 - fixed
    with pytest.raises(NameBudgetError):
        build("a" * (180 - fixed), single, printed, None, "png", "ascii", collision=2)
    assert comparison_key("Straße.png") == comparison_key("STRASSE.PNG")
    assert comparison_key("é.png") == comparison_key("É.PNG")
    assert comparison_key("Ａ.png") != comparison_key("A.png")


def test_http_edit_idempotency_key_returns_the_original_receipt(jpeg_job):
    import httpx
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app
    d, job, jpeg, png = jpeg_job

    def forbidden(request):
        raise AssertionError("No provider request is allowed.")
    app = create_app(d.store.root, "synthetic-only", transport=httpx.MockTransport(forbidden))
    body = args("![x](asset:new/x)", [create("x", png, "Keyed")], printed="58", evidence=png["ref"])
    with TestClient(app, headers={"Authorization": "Bearer synthetic-only"}) as client:
        first = client.post(f"/jobs/{job}/edit", json=body, headers={"Idempotency-Key": "desktop:retry-1"}).json()
        again = client.post(f"/jobs/{job}/edit", json=body, headers={"Idempotency-Key": "desktop:retry-1"}).json()
        assert first["ok"] and again["data"] == first["data"]
        assert first["data"]["asset_changes"][0]["asset_path"] == "assets/Keyed-p58.png"
        other = {**body, "claim": "partial"}
        conflict = client.post(f"/jobs/{job}/edit", json=other, headers={"Idempotency-Key": "desktop:retry-1"})
        assert conflict.status_code >= 400
        assert client.post(f"/jobs/{job}/edit", json=body, headers={"Idempotency-Key": "bad key!"}).status_code >= 400
    assert len(d.store.records("version", job)) == 1


# ---------------------------------------------------------------- AR-10 across engine processes
def _two_engines(tmp_path, d, job, specs: dict[str, dict]) -> dict[str, dict]:
    """Run two engine processes on one store; A reserves first, B after A holds its name."""
    import time
    sync = tmp_path / "sync"
    sync.mkdir()
    root = Path(__file__).parents[3]
    processes = {}
    for role, spec in specs.items():
        path = sync / f"{role}.spec.json"
        path.write_text(json.dumps({"root": str(d.store.root), "job": job, "role": role, "sync": str(sync), **spec},
                                   ensure_ascii=False), encoding="utf-8")
        processes[role] = subprocess.Popen([sys.executable, "-B", "-m", "tests.engine.documents.allocation_child", str(path)],
                                           cwd=root)

    def wait_for(name):
        for _ in range(6000):
            if (sync / name).exists():
                return
            assert all(p.poll() is None for p in processes.values()), f"an engine exited before {name}"
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {name}")
    try:
        wait_for("A.ready")
        wait_for("B.ready")  # both loaded the operation's preparation record before either reserved
        (sync / "A.go").write_text("go")
        wait_for("A.reserved")
        (sync / "B.go").write_text("go")
        for role, process in processes.items():
            assert process.wait(180) == 0, role
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.kill()
    return {role: json.loads((sync / f"{role}.json").read_text(encoding="utf-8")) for role in specs}


def test_engines_in_separate_processes_never_share_a_name(jpeg_job, tmp_path):
    d, job, jpeg, png = jpeg_job
    body = args("![x](asset:new/x)", [create("x", png, "Same label")], printed="58", evidence=png["ref"])
    results = _two_engines(tmp_path, d, job, {"A": {"operation": "op-a", "arguments": body},
                                              "B": {"operation": "op-b", "arguments": body}})
    # Held concurrently: the second process saw a real pending conflict and took the next suffix.
    pending_names = {"A": "Same label-p58.png", "B": "Same label-p58（2）.png"}
    winner = [role for role, result in results.items() if result["ok"]]
    assert len(winner) == 1, results
    [winner], loser = winner, ({"A", "B"} - set(winner)).pop()
    assert results[loser]["data"]["error_code"] == "HEAD_CONFLICT"
    assert results[winner]["data"]["asset_changes"][0]["asset_path"] == "assets/" + pending_names[winner]
    names = {r["name"]: r for r in d.store.records("asset_name", job)}
    assert names[pending_names[winner]]["status"] == "assigned"
    assert names[pending_names[loser]]["status"] == "released"  # the failed save gives its name back
    assert d.store.get("job", job)["head"] == results[winner]["data"]["version_id"]
    # A new occurrence after the race gets the first name no current binding holds.
    head = d.store.get("job", job)["head"]
    later = call(d, job, "op-later", args("![x](asset:id/%s) ![y](asset:new/y)" % results[winner]["data"]["asset_changes"][0]["occurrence_id"],
                                          [create("y", png, "Same label")], base=head, printed="58", evidence=png["ref"]))
    assert later["ok"], later
    assert later["data"]["asset_changes"][0]["asset_path"] == "assets/" + pending_names[loser]


def test_attempts_of_one_operation_in_two_processes_share_one_identity(jpeg_job, tmp_path):
    d, job, jpeg, png = jpeg_job
    body = args("![x](asset:new/x)", [create("x", png, "Same label")], printed="58", evidence=png["ref"])
    results = _two_engines(tmp_path, d, job, {"A": {"operation": "op-same", "arguments": body},
                                              "B": {"operation": "op-same", "arguments": body}})
    assert results["A"]["ok"] and results["B"]["ok"], results
    assert results["A"]["data"] == results["B"]["data"]  # one receipt, not two versions
    [change] = results["A"]["data"]["asset_changes"]
    assert change["asset_path"] == "assets/Same label-p58.png"
    assert len(d.store.records("version", job)) == 1
    assert [(r["name"], r["status"]) for r in d.store.records("asset_name", job)] == [("Same label-p58.png", "assigned")]
    assert d.store.get("asset_preparation", "op-same")["ids"]["x"]["occurrence_id"] == change["occurrence_id"]
    later = call(d, job, "op-later", args("![y](asset:new/y)", [create("y", png, "Same label")],
                                          base=results["A"]["data"]["version_id"], printed="58", evidence=png["ref"]))
    assert later["data"]["asset_changes"][0]["asset_path"] == "assets/Same label-p58（2）.png"


def test_attempt_finding_its_operation_published_releases_leftover_names(jpeg_job, monkeypatch):
    d, job, jpeg, png = jpeg_job
    request = args("![x](asset:new/x)", [create("x", png, "Late")], printed="58", evidence=png["ref"])
    raw = json.dumps(request, ensure_ascii=False)
    digest = sha256(json.dumps(["edit_document", raw]).encode()).hexdigest()
    original = documents_module.Documents._prepare_images
    state = {"nested": False}

    def prepare(self, job_id, pending, kept):
        if not state["nested"]:
            # Another attempt of the same operation publishes first and a stale
            # pending name of this operation remains, as before the shared record.
            state["nested"] = True
            first = self.edit(job_id, "op-late", request, digest, "candidate:none")
            d.store.put("asset_name", "stale", job_id, {"id": "stale", "job": job_id, "key": "stale", "name": "Late-p58（2）.png",
                                                         "occurrence_id": "other", "operation": "op-late", "status": "pending"})
            state["first"] = first
        return original(self, job_id, pending, kept)
    monkeypatch.setattr(documents_module.Documents, "_prepare_images", prepare)
    late = d.documents.edit(job, "op-late", request, digest, "candidate:none")
    assert late == state["first"]
    assert d.store.get("asset_name", "stale")["status"] == "released"
    assert {r["status"] for r in d.store.records("asset_name", job)} == {"assigned", "released"}
    assert len(d.store.records("version", job)) == 1


def test_failed_attempt_reuses_the_peer_commit_before_projection(jpeg_job, monkeypatch):
    d, job, _, png = jpeg_job
    peer = Dispatcher(d.store)
    request = args("![x](asset:new/x)", [create("x", png, "First commit")])
    raw = json.dumps(request, ensure_ascii=False)
    digest, candidate = peer.capture(job, "same", "edit_document", raw)

    def fail_after_peer_commits(*_):
        peer.documents.edit(job, "same", request, digest, candidate["ref"])
        assert d.store.maybe("blob", "result:same") is None
        raise OSError("Writer failed in the second attempt.")

    monkeypatch.setattr(d.documents, "_prepare_images", fail_after_peer_commits)
    result = call(d, job, "same", request)
    assert result["ok"], result
    assert call(peer, job, "same", request) == result
    assert d.store.get("operation", "same")["result"] == result["data"]
    assert d.store.json(result["result_ref"], job) == result["data"]
    assert d.store.get("job", job)["head"] == result["data"]["version_id"]
    assert len(d.store.records("version", job)) == 1


def test_delayed_edit_start_replays_the_completed_operation(jpeg_job, monkeypatch):
    d, job, _, png = jpeg_job
    peer = Dispatcher(d.store)
    request = args("![x](asset:new/x)", [create("x", png, "First commit")])
    begin = d._begin_edit
    receipts = []

    def finish_peer_first(*args):
        receipts.append(call(peer, job, "same", request))
        return begin(*args)

    monkeypatch.setattr(d, "_begin_edit", finish_peer_first)
    result = call(d, job, "same", request)
    assert result["ok"] and receipts == [result]
    assert d.store.get("operation", "same")["result"] == result["data"]
    assert len(d.store.records("version", job)) == 1


def test_delayed_preparation_keeps_the_committed_version_link(jpeg_job, monkeypatch):
    d, job, _, png = jpeg_job
    peer = Dispatcher(d.store)
    request = args("![x](asset:new/x)", [create("x", png, "First commit")])
    page_rects = d.documents._page_rects
    receipts = []

    def finish_peer_first(task):
        receipts.append(call(peer, job, "same", request))
        return page_rects(task)

    monkeypatch.setattr(d.documents, "_page_rects", finish_peer_first)
    result = call(d, job, "same", request)
    assert result["ok"] and receipts == [result]
    preparation = d.store.get("asset_preparation", "same")
    assert preparation["status"] == "committed" and preparation["version"] == result["data"]["version_id"]
    assert [r["status"] for r in d.store.records("asset_name", job)] == ["assigned"]


def test_failed_edit_receipt_and_name_release_roll_back_together(jpeg_job, monkeypatch):
    d, job, _, png = jpeg_job
    request = args("![x](asset:new/x)", [create("x", png, "Reserved")])
    put_tx = d.store.put_tx

    def preparation_failed(*_):
        raise OSError("Local preparation failed.")

    def interrupt_failure_commit(db, kind, key, owner, value):
        if kind == "operation" and key == "interrupted" and value["status"] == "done":
            raise OSError("Interrupted before the failure receipt commits.")
        return put_tx(db, kind, key, owner, value)

    with monkeypatch.context() as patch:
        patch.setattr(d.documents, "_prepare_images", preparation_failed)
        patch.setattr(d.store, "put_tx", interrupt_failure_commit)
        with pytest.raises(OSError, match="Interrupted before"):
            call(d, job, "interrupted", request)

    assert d.store.get("operation", "interrupted")["status"] == "started"
    assert d.store.maybe("blob", "result:interrupted") is None
    assert d.store.get("asset_preparation", "interrupted")["status"] == "preparing"
    [reservation] = d.store.records("asset_name", job)
    assert reservation["status"] == "pending"
    resumed = call(d, job, "interrupted", request)
    assert resumed["ok"], resumed
    assert resumed["data"]["asset_changes"][0]["occurrence_id"] == reservation["occurrence_id"]
