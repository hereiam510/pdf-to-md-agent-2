from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import base64
import re
import zipfile

import pytest
from fastapi.testclient import TestClient

from pdfmd.asset_references import (analyze, asset_uri, assess, classify, dependencies,
                                    ReferenceError, rewrite)
from pdfmd.documents import Documents
from pdfmd.server import create_app
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import edit, call


def legacy_embed_only(monkeypatch):
    """Reproduce the pre-T3a embed-only collector to build a historical incomplete fixture.

    This is a fixture constructor for AR-7 controls, not a production save path.
    """
    import pdfmd.documents as documents_module
    real = documents_module.dependencies
    monkeypatch.setattr(documents_module, "dependencies", lambda analysis, registered, **kw: {
        path: uses for path, uses in real(analysis, registered, **kw).items() if any(u.role == "image" for u in uses)})


def blocks(*texts):
    return [{"id": f"b{i}", "pages": [], "markdown": text} for i, text in enumerate(texts)]


@pytest.mark.parametrize("name", ["Comparison-p58&p61.png", "Comparison-p58&i67.png", "圖 (2)+字.png", "literal%2F%25.png"])
def test_uri_roundtrip_exactly_once(name):
    path = "assets/" + name
    uri = asset_uri(path)
    assert classify(uri, "image") == ("asset", path)
    assert "%26" in uri if "&" in name else True
    assert classify("https://example.test/" + uri, "hyperlink") == ("unrelated", None)
    assert classify(uri.replace("assets/", "Assets/"), "hyperlink")[0] == "invalid"


@pytest.mark.parametrize("destination", ["./assets/a.png", "../assets/a.png", "/assets/a.png", "a/ASSETS/a.png",
    "assets/../a.png", "assets/x/a.png", "assets\\a.png", "assets/a.png?x", "assets/a.png#x", "assets/a.png?",
    "assets/%2E%2E", "assets/%2Fa.png", "assets/%5ca.png", "assets%2fa.png", "assets/%GG.png", "assets/%FF.png"])
def test_reserved_variants_reject_without_lookup(destination):
    assert classify(destination, "hyperlink")[0] == "invalid"


def test_external_citations_fragments_and_plus_are_not_aliases():
    for value in ["#fn1", "https://host/assets/a.png?q", "//host/assets/a.png", "chapter.html", "mailto:a@host"]:
        assert classify(value, "hyperlink")[0] == "unrelated"
    assert classify("assets/a+b.png", "image") == ("asset", "assets/a+b.png")
    assert classify("assets/a%252Fb.png", "image") == ("asset", "assets/a%2Fb.png")
    for value in ["https://host/a.png", "file:///C:/a.png", "data:image/png;base64,AAAA", "blob:https://host/key",
                  "pdfmd-preview://snapshot/foreign/key", "chapter.png", "#x"]:
        assert classify(value, "image")[0] == "invalid"
        interpretation = analyze(blocks(f'![unsupported]({value})'), {})
        with pytest.raises(ReferenceError) as error:
            dependencies(interpretation, set())
        assert error.value.issue['destination'] == value
        assert error.value.issue['role'] == 'image'


def test_parsing_does_not_repair_malformed_uri_escapes():
    result = analyze(blocks('[x](assets/a%GG.png) ![y](assets/a%FF.png)'), {})
    assert [r.destination for r in result.references] == ['assets/a%GG.png', 'assets/a%FF.png']
    with pytest.raises(ReferenceError):
        dependencies(result, {'assets/a%GG.png', 'assets/a%FF.png'})
    assert classify('\tassets/a.png', 'hyperlink')[0] == 'invalid'


def test_definition_inside_footnote_and_tab_indentation_stays_source_bound():
    source = blocks('[outer][r] note[^n]\r\n\r\n[^n]: body\r\n\r\n    [r]: <assets/a.png> "title"\r\n\r\n'
                    '- item\r\n\r\n\t[tab](assets/b.png)')
    result = analyze(source, {})
    assert not result.issues
    assert {r.destination for r in result.references} == {'assets/a.png', 'assets/b.png'}
    for ref in result.references:
        span = ref.span
        assert span and source[0]['markdown'][span.start:span.end] == span.expected
    changed = rewrite(source, {}, result, {'assets/a.png': 'assets/c.png', 'assets/b.png': 'assets/d.png'})
    assert '\r\n    [r]: <assets/c.png> "title"' in changed[0]['markdown']
    assert '\r\n\t[tab](assets/d.png)' in changed[0]['markdown']


def test_whole_document_roles_spans_and_precise_rewrite():
    source = blocks(
        '😀 [full][r] [r][] [r] ![alt][r]\r\n\r\n[![inner](assets/b.png)](assets/a.png "outer")\r\n\r\n'
        '| column | note |\r\n|---|---|\r\n| [table][r] | note[^n] |\r\n\r\n'
        '`assets/a.png [r]`\r\n\r\n```md\r\n![literal](assets/a.png)\r\n```\r\n\r\n<!-- <img src="assets/a.png"> -->',
        '[r]:\r\n  <assets/a.png> "definition title"\r\n\r\n[r]: assets/inactive.png\r\n\r\n'
        '[^n]: note [foot][r] and ^[![inline](assets/b.png)]\r\n\r\n'
        '> - nested [link](assets/a.png)\r\n\r\n'
        '<A HREF=assets/a.png>raw</A> <img SRC=\'assets/b.png\' alt="Raw">')
    analysis = analyze(source, {})
    assert not analysis.issues
    union = dependencies(analysis, {"assets/a.png", "assets/b.png"})
    assert set(union) == {"assets/a.png", "assets/b.png"}
    assert {r.role for r in union["assets/a.png"]} == {"image", "hyperlink"}
    assert len(analysis.references) == 12
    for ref in analysis.references:
        span = ref.span
        assert span and source[int(span.block_id[1:])]["markdown"][span.start:span.end] == span.expected
    full = analysis.references[0]
    assert full.block_id == "b0" and full.span.block_id == "b1"
    target = asset_uri("assets/新圖-p58&p61 (2).png")
    rewritten = rewrite(source, {}, analysis, {"assets/a.png": target})
    assert rewritten[0]["markdown"].startswith('😀 [full][r] [r][] [r] ![alt][r]\r\n')
    assert '`assets/a.png [r]`' in rewritten[0]["markdown"]
    assert '![literal](assets/a.png)' in rewritten[0]["markdown"]
    assert '<!-- <img src="assets/a.png"> -->' in rewritten[0]["markdown"]
    assert '[r]: assets/inactive.png' in rewritten[1]["markdown"]
    assert f'<A HREF={target}>' in rewritten[1]["markdown"]
    assert f'<{target}> "definition title"' in rewritten[1]["markdown"]
    assert source[1]["markdown"].count("assets/a.png") == 3  # input untouched
    wrong = deepcopy(source)
    wrong[1]["markdown"] = wrong[1]["markdown"].replace("assets/a.png", "assets/z.png", 1)
    with pytest.raises(ReferenceError, match="guard"):
        rewrite(wrong, {}, analysis, {"assets/a.png": target})


def test_escaped_destinations_and_table_pipe_preserve_original_spelling():
    source = blocks('[x](assets/a\\(2\\).png "title") <a href="assets/a&amp;b.png">raw</a>\n\n'
                    '|h|\n|-|\n|[pipe](assets/a\\|b.png)|')
    analysis = analyze(source, {})
    assert not analysis.issues
    assert [r.destination for r in analysis.references] == ["assets/a(2).png", "assets/a&b.png", "assets/a%7Cb.png"]
    assert [r.span.expected for r in analysis.references] == [r"assets/a\(2\).png", "assets/a&amp;b.png", r"assets/a\|b.png"]
    changed = rewrite(source, {}, analysis, {r.destination: "assets/new.png" for r in analysis.references})
    assert changed[0]["markdown"] == '[x](assets/new.png "title") <a href="assets/new.png">raw</a>\n\n|h|\n|-|\n|[pipe](assets/new.png)|'


@pytest.mark.parametrize("text", ['<img src="assets/a.png" SRC="assets/a.png">', '<a href="assets/a.png" href="assets/b.png">x</a>',
    '<img src="assets/a.png" srcset="assets/b.png 2x">', '<picture><source srcset="assets/a.png"><img src="assets/a.png"></picture>',
    '<svg><a href="assets/a.png">x</a></svg>', '<a href="assets/a.png"><a href="assets/b.png">x</a></a>'])
def test_ambiguous_or_unsupported_markup_is_rejected(text):
    result = analyze(blocks(text), {})
    # Nested anchors may repair to an identical resource multiset; require the
    # scanner/render equivalence check to reject structure-changing markup too.
    assert result.issues
    with pytest.raises(ReferenceError):
        dependencies(result, {"assets/a.png", "assets/b.png"})


def test_input_handles_literals_and_unknown_bindings():
    source = blocks('[new](asset:new/figure_a) ![existing](asset:id/occ_1)\n\n`[literal](asset:new/unused)`\n\n[undefined][none]')
    result = analyze(source, {})
    assert [r.destination for r in result.references] == ["asset:new/figure_a", "asset:id/occ_1"]
    with pytest.raises(ReferenceError, match="handle"):
        dependencies(result, {"assets/a.png"})
    assert set(dependencies(result, {"assets/a.png"}, handles={"asset:new/figure_a": "assets/a.png", "asset:id/occ_1": "assets/a.png"})) == {"assets/a.png"}
    updated = rewrite(source, {}, result, {r.destination: "assets/a.png" for r in result.references})
    dependencies(analyze(updated, {}), {"assets/a.png"})
    assert '`[literal](asset:new/unused)`' in updated[0]["markdown"]
    missing = analyze(blocks('[x](assets/a.png)'), {})
    with pytest.raises(ReferenceError) as error:
        dependencies(missing, {"assets/A.png"})
    assert error.value.issue["code"] == "ASSET_NOT_OWNED"
    ambiguous = replace(missing.references[0], span=None)
    missing.references = [ambiguous]
    with pytest.raises(ReferenceError) as error:
        dependencies(missing, {"assets/a.png"})
    assert error.value.issue["code"] == "ASSET_SPAN_AMBIGUOUS"


@pytest.mark.parametrize("destination", ["asset:new/key", "asset&#58;new/key", "asset:id/unknown", "<asset:new/key>", "ASSET:new/key"])
def test_unresolved_handles_never_publish_and_candidate_is_reusable(setup, destination):
    store, job = setup
    dispatcher = Dispatcher(store)
    raw = edit([{"id": "b", "pages": [1], "markdown": destination if destination.startswith('<') else f'[x]({destination})'}])
    result = call(dispatcher, job["id"], "handle", raw)
    assert not result["ok"] and store.get("job", job["id"])["head"] is None
    assert store.json(result["candidate_ref"], job["id"]) == raw
    literal = edit([{"id": "b", "pages": [1], "markdown": '`[x](asset:new/key)`'}])
    assert call(dispatcher, job["id"], "literal", literal)["ok"]


def test_historical_incomplete_is_inspectable_exactly_exportable_without_healing(setup, tmp_path, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], 1)
    args = edit([{"id": "b", "pages": [1], "markdown": f'[source]({image["asset_path"]})'}])
    legacy_embed_only(monkeypatch)
    saved = call(dispatcher, job["id"], "historical", args)["data"]["version_id"]
    monkeypatch.undo()
    folder = dispatcher.documents.root / saved
    before = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    selected = dispatcher.documents.selected(job["id"], saved)
    assert selected["asset_reference_check"]["status"] == "incomplete"
    assert selected["asset_reference_check"]["issues"][0]["code"] == "missing_version_asset"
    assert '<a rel="noopener noreferrer">source</a>' in selected["preview"]
    assert "data:image" not in selected["preview"] and image["asset_path"] in selected["markdown"]
    assert store.bytes(image["ref"], job["id"])  # still present, cannot heal
    target = tmp_path / "old.zip"
    receipt = dispatcher.documents.export(job["id"], saved, str(target))
    assert receipt["verified"] and "asset_reference_check" not in receipt
    with zipfile.ZipFile(target) as archive:
        assert {n: archive.read(n) for n in archive.namelist()} == before
    assert {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()} == before


def test_selected_preview_uses_version_bytes_not_mutable_blobs_and_corruption_blocks(setup, tmp_path, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], 1)
    path = image["asset_path"]
    args = edit([{"id": "b", "pages": [1], "markdown": f'\U0001f4c4 [source]({path}) ![alt]({path})'}])
    saved = call(dispatcher, job["id"], "mixed", args)["data"]["version_id"]
    monkeypatch.setattr(store, "bytes", lambda *args: pytest.fail("Selected preview must not read a task blob"))
    selected = dispatcher.documents.selected(job["id"], saved)
    assert selected["asset_reference_check"] == {"status": "ok", "issues": []}
    assert selected["preview"].count("pdfmd-resource-0") == 2
    file = dispatcher.documents.root / saved / path
    transfer = selected['preview_transfer']
    assert transfer['job'] == job['id'] and transfer['version'] == saved
    assert len(transfer['resources']) == 1
    resource = transfer['resources'][0]
    assert base64.b64decode(resource['base64']) == file.read_bytes()
    assert resource['length'] == file.stat().st_size
    assert resource['sha256'] == sha256(file.read_bytes()).hexdigest()
    assert resource['mime'] == 'image/png' and resource['asset'] == path
    for slot in transfer['slots']:
        assert selected['preview'].encode('utf-16-le')[slot['start']*2:slot['end']*2].decode('utf-16-le') == slot['expected'] == resource['key']
    file.write_bytes(file.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        dispatcher.documents.selected(job["id"], saved)
    with pytest.raises(ValueError, match="integrity"):
        dispatcher.documents.export(job["id"], saved, str(tmp_path / "bad.zip"))
    assert not (tmp_path / "bad.zip").exists()


def test_unavailable_assessment_disables_selected_targets_without_hiding_raw_markdown(setup, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job['id'], 1)
    path = image['asset_path']
    saved = call(dispatcher, job['id'], 'save', edit([{'id': 'b', 'pages': [1], 'markdown': f'[source]({path}) ![alt]({path})'}]))['data']['version_id']
    monkeypatch.setattr('pdfmd.asset_references.analyze', lambda *args: (_ for _ in ()).throw(RuntimeError('injected')))
    selected = dispatcher.documents.selected(job['id'], saved)
    assert selected['asset_reference_check']['status'] == 'unavailable'
    assert 'data:image' not in selected['preview'] and 'href=' not in selected['preview']
    assert 'alt (image unavailable)' in selected['preview'] and path in selected['markdown']


def test_associated_original_inventory_and_analysis_failure_are_distinct(monkeypatch):
    saved = {"schema_version": 1, "content": {"blocks": blocks('![a](assets/abc.png)'), "pages": {}},
             "assets": {"assets/abc.png": {"sha256": "digest", "provenance": {"originals": [{"ref": "r", "path": "originals/x.bin"}]}}}, "originals": {}}
    check, _ = assess(saved, {"assets/abc.png": "digest"})
    assert check["status"] == "incomplete" and any(i["code"] == "missing_associated_original" for i in check["issues"])
    monkeypatch.setattr("pdfmd.asset_references.analyze", lambda *args: (_ for _ in ()).throw(RuntimeError("injected")))
    check, analysis = assess(saved, {})
    assert check["status"] == "unavailable" and analysis is None and check["issues"][0]["code"] == "analysis_unavailable"


def test_host_api_adds_live_check_without_changing_receipts(setup, tmp_path, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], 1)
    legacy_embed_only(monkeypatch)
    saved = call(dispatcher, job["id"], "old", edit([{"id": "b", "pages": [1], "markdown": f'[x]({image["asset_path"]})'}]))["data"]["version_id"]
    monkeypatch.undo()
    with TestClient(create_app(store.root, "test-token"), headers={"Authorization": "Bearer test-token"}) as client:
        selected = client.get(f'/jobs/{job["id"]}/versions/{saved}').json()
        assert selected["asset_reference_check"]["status"] == "incomplete"
        response = client.post(f'/jobs/{job["id"]}/export', json={"version_id": saved, "destination": str(tmp_path / "api.zip")})
        assert response.status_code == 200, response.text
        assert response.json()["asset_reference_check"]["status"] == "incomplete"
    assert all("asset_reference_check" not in receipt for receipt in store.records("export", job["id"]))
