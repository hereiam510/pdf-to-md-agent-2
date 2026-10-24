import json
import zipfile

import pytest
import pymupdf

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


def edit(blocks=None):
    return {"base_version": None, "expected_head": None,
            "replace_blocks": blocks or [{"id": "body", "pages": [1], "markdown": "本文件 **25 mg** / μg / e\u0301"}],
            "page_updates": {"1": {"printed": "none", "disposition": "included"}}}


def call(dispatcher, job, op, data):
    return dispatcher.execute(job, op, "edit_document", json.dumps(data, ensure_ascii=False))


def test_rejected_candidate_reused_exactly_and_replayed_after_new_head(setup):
    store, job = setup
    d = Dispatcher(store)
    bad = edit()
    bad["page_updates"]["2"] = {"printed": "none"}
    result = call(d, job["id"], "bad", bad)
    assert not result["ok"]
    assert store.get("job", job["id"])["head"] is None
    repaired = {"base_version": None, "expected_head": None, "reuse_candidate": {"ref": result["candidate_ref"]},
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}}
    first = call(d, job["id"], "fix", repaired)
    one = first["data"]["version_id"]
    content = d.documents.version(job["id"], one)["content"]
    assert content["blocks"][0]["markdown"] == bad["replace_blocks"][0]["markdown"]
    patch = {"base_version": one, "expected_head": one, "page_updates": {"1": {"printed": "iii"}},
             "operations": [{"kind": "insert", "after_id": "body", "blocks": [{"id": "end", "pages": [1], "markdown": "End."}]}]}
    two = call(d, job["id"], "append", patch)["data"]["version_id"]
    assert call(d, job["id"], "fix", repaired) == first
    assert store.get("job", job["id"])["head"] == two
    assert d.documents.version(job["id"], two)["content"]["blocks"][0] == content["blocks"][0]
    page = d.documents.version(job["id"], two)["content"]["pages"]["1"]
    assert page["printed"] == "iii" and page["disposition"] == "included"
    stale = call(d, job["id"], "stale", patch)
    assert not stale["ok"] and store.get("job", job["id"])["head"] == two


def test_whole_document_render_export_and_exact_patch(setup, tmp_path):
    store, job = setup
    d = Dispatcher(store)
    args = edit([{"id": "first", "pages": [1], "markdown": "[link][target] with a note[^n]."},
                 {"id": "definitions", "pages": [1], "markdown": "[target]: https://example.com\n\n[^n]: Footnote."}])
    one = call(d, job["id"], "save", args)["data"]["version_id"]
    html = (d.documents.root / one / "preview.html").read_text("utf-8")
    assert 'href="https://example.com"' in html and "Footnote." in html
    patch = {"base_version": one, "expected_head": one,
             "operations": [{"kind": "patch", "id": "first", "start": 0, "end": 6, "expected": "wrong!", "text": "new"}]}
    assert not call(d, job["id"], "wrong", patch)["ok"]
    archive = tmp_path / "delivery.zip"
    receipt = d.documents.export(job["id"], one, str(archive))
    assert receipt["verified"] and receipt["claim"] == "partial"
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            assert z.read(name) == (d.documents.root / one / name).read_bytes()
    assert d.documents.export(job["id"], one, str(archive)) == receipt
    archive.write_bytes(b"unrelated")
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        d.documents.export(job["id"], one, str(archive))
    assert archive.read_bytes() == b"unrelated"


def test_source_image_bytes_in_explicit_version_export(setup, tmp_path):
    store, job = setup
    d = Dispatcher(store)
    image = d.evidence.render_page(job["id"], 1)
    args = edit([{"id": "figure", "pages": [1], "markdown": f"![Source]({image['asset_path']})"}])
    one = call(d, job["id"], "image-save", args)["data"]["version_id"]
    archive = tmp_path / "image.zip"
    d.documents.export(job["id"], one, str(archive))
    with zipfile.ZipFile(archive) as z:
        assert z.read(image["asset_path"]) == store.bytes(image["ref"], job["id"])


def test_result_blob_reconciles_before_operation_pointer_commit(setup, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    original = store.put
    injected = []

    def fail_pointer(kind, key, owner, value):
        if kind == "operation" and value["status"] == "done" and not injected:
            injected.append(True)
            raise RuntimeError("injected receipt gap")
        return original(kind, key, owner, value)

    monkeypatch.setattr(store, "put", fail_pointer)
    with pytest.raises(RuntimeError):
        dispatcher.execute(job["id"], "inspect", "inspect_pdf", '{}')
    blobs = len(store.records("blob", job["id"]))
    recovered = dispatcher.execute(job["id"], "inspect", "inspect_pdf", '{}')
    assert recovered["ok"]
    assert len(store.records("blob", job["id"])) == blobs


def test_ordinary_edit_rejects_other_base_but_explicit_rebuild_keeps_head_guard(setup):
    store, job = setup
    d = Dispatcher(store)
    one = call(d, job['id'], 'v1', edit())['data']['version_id']
    two = call(d, job['id'], 'v2', {
        'base_version': one, 'expected_head': one,
        'operations': [{'kind': 'insert', 'after_id': 'body', 'blocks': [
            {'id': 'new', 'pages': [1], 'markdown': 'Keep this newer work.'}]}]
    })['data']['version_id']
    original = d.documents.version(job['id'], two)
    for index, base in enumerate([one, None]):
        args = {'base_version': base, 'expected_head': two, 'title': 'Metadata only'}
        rejected = call(d, job['id'], f'reject-{index}', args)
        assert not rejected['ok'] and "mode='rebuild'" in rejected['data']['error']
        assert store.json(rejected['candidate_ref'], job['id']) == args
        assert store.get('job', job['id'])['head'] == two
        assert d.documents.version(job['id'], two) == original
    # Rebuilding is an agent-selected operation, with no separate approval gate.
    rebuilt = call(d, job['id'], 'rebuild', {'mode': 'rebuild', 'base_version': one, 'expected_head': two})
    assert rebuilt['ok'] and rebuilt['data']['edit_mode'] == 'rebuild'
    three = rebuilt['data']['version_id']
    assert d.documents.version(job['id'], three)['content'] == d.documents.version(job['id'], one)['content']
    stale = call(d, job['id'], 'stale-rebuild', {'mode': 'rebuild', 'base_version': one, 'expected_head': two})
    assert not stale['ok'] and 'Head changed' in stale['data']['error']
    assert store.get('job', job['id'])['head'] == three
    empty = call(d, job['id'], 'empty-rebuild', {'mode': 'rebuild', 'base_version': None, 'expected_head': three})
    assert empty['ok']
    assert d.documents.version(job['id'], empty['data']['version_id'])['content']['blocks'] == []
    assert d.documents.version(job['id'], two) == original


@pytest.mark.parametrize('kind,single', [('insert', False), ('replace', True)])
def test_local_candidate_repair_preserves_newer_work_source_and_export(tmp_path, kind, single):
    source = tmp_path / 'two-pages.pdf'
    pdf = pymupdf.open()
    for text in ['First page. Keep 25 mg.\nA second paragraph to preserve.', 'Second page. Keep every value: 42.']:
        page = pdf.new_page()
        page.insert_text((72, 72), text)
    pdf.save(source)
    source_bytes = source.read_bytes()
    source_text = [page.get_text() for page in pdf]
    pdf.close()
    store = Store(tmp_path / 'workspace')
    job = Evidence(store).create_job(str(source), 'Both complete pages.')
    d = Dispatcher(store)
    image = d.evidence.render_page(job['id'], 1)
    image_bytes = store.bytes(image['ref'], job['id'])
    blocks = [{'id': 'body', 'pages': [1], 'markdown': source_text[0].splitlines()[0]},
              {'id': 'figure', 'pages': [1], 'markdown': f"![Source page]({image['asset_path']})"}]
    if kind == 'replace':
        blocks.append({'id': 'second', 'pages': [2], 'markdown': 'Unfinished draft.'})
    initial = edit(blocks)
    if kind == 'replace':
        initial['page_updates']['2'] = {'disposition': 'included'}
    one = call(d, job['id'], 'first', initial)['data']['version_id']
    candidate_block = {'id': 'second', 'pages': [2], 'markdown': source_text[1], 'source_note': 'Physical page 2'}
    rejected_args = {'base_version': one, 'expected_head': one,
                     'operations': [{'kind': 'insert', 'after_id': 'body', 'blocks': [candidate_block]},
                                    {'kind': 'delete', 'id': 'figure'}],
                     'page_updates': {'3': {'disposition': 'included'}}}
    rejected = call(d, job['id'], 'rejected', rejected_args)
    assert not rejected['ok']
    candidate_bytes = store.bytes(rejected['candidate_ref'], job['id'])
    # A later save does not invalidate useful candidate content.
    newer = call(d, job['id'], 'newer', {'base_version': one, 'expected_head': one,
        'operations': [{'kind': 'insert', 'after_id': 'body', 'blocks': [
            {'id': 'later', 'pages': [1], 'markdown': source_text[0].splitlines()[1]}]}]})['data']['version_id']
    before = d.documents.version(job['id'], newer)
    pointer = '/operations/0/blocks/0' if single else '/operations/0/blocks'
    change = {'kind': kind, 'reuse_candidate': {'ref': rejected['candidate_ref'], 'pointer': pointer}}
    change.update({'after_id': 'figure'} if kind == 'insert' else {'id': 'second'})
    repaired = call(d, job['id'], 'repair', {'base_version': newer, 'expected_head': newer,
        'operations': [change], 'page_updates': {'2': {'printed': 'none', 'disposition': 'included'}}, 'claim': 'complete'})
    assert repaired['ok'], repaired
    version_id = repaired['data']['version_id']
    # Recreate the store/document reader, then export this explicit immutable version.
    reopened = Documents(Store(store.root))
    final = reopened.version(job['id'], version_id)
    unchanged = [block for block in before['content']['blocks'] if block['id'] != 'second']
    assert [block for block in final['content']['blocks'] if block['id'] != 'second'] == unchanged
    assert next(b for b in final['content']['blocks'] if b['id'] == 'second') == candidate_block
    assert final['content']['pages']['1'] == before['content']['pages']['1']
    assert final['assets'] == before['assets']  # The candidate's delete operation was not replayed.
    assert reopened.version(job['id'], newer) == before
    assert store.bytes(rejected['candidate_ref'], job['id']) == candidate_bytes
    assert source.read_bytes() == source_bytes
    archive = tmp_path / 'delivery.zip'
    assert reopened.export(job['id'], version_id, str(archive))['verified']
    with zipfile.ZipFile(archive) as z:
        saved = json.loads(z.read('document.json'))
        assert saved == final
        markdown = z.read('document.md').decode('utf-8')
        for text in source_text:
            assert all(line in markdown for line in text.splitlines())
        assert '<!-- PDF pages: 2 | printed pages: 2=none -->' in markdown
        assert z.read(image['asset_path']) == image_bytes
        for name in z.namelist():
            assert z.read(name) == (reopened.root / version_id / name).read_bytes()


@pytest.mark.parametrize('problem', ['both', 'neither', 'foreign', 'not-candidate', 'wrong-type', 'bad-index', 'bad-escape', 'missing-target', 'duplicate-id'])
def test_local_candidate_validation_retains_rejection_without_changing_head(setup, problem):
    store, job = setup
    d = Dispatcher(store)
    one = call(d, job['id'], 'first', edit())['data']['version_id']
    block = {'id': 'body' if problem == 'duplicate-id' else 'added', 'markdown': 'e\u0301, μg, **literal**', 'pages': [1]}
    original = {'operations': [{'blocks': [block]}], 'not-blocks': 'text'}
    candidate = store.blob('another-job' if problem == 'foreign' else job['id'],
                           'evidence' if problem == 'not-candidate' else 'candidate', original)
    path = {'wrong-type': '/not-blocks', 'bad-index': '/operations/-1/blocks',
            'bad-escape': '/operations/~2/blocks'}.get(problem, '/operations/0/blocks')
    change = {'kind': 'insert', 'after_id': 'missing' if problem == 'missing-target' else 'body',
              'reuse_candidate': {'ref': candidate['ref'], 'pointer': path}}
    if problem == 'both':
        change['blocks'] = [block]
    if problem == 'neither':
        del change['reuse_candidate']
    args = {'base_version': one, 'expected_head': one, 'operations': [change]}
    result = call(d, job['id'], 'invalid', args)
    assert not result['ok']
    assert store.get('job', job['id'])['head'] == one
    assert store.json(result['candidate_ref'], job['id']) == args


def test_candidate_pointer_escapes_and_sequential_operations_preserve_exact_text(setup):
    store, job = setup
    d = Dispatcher(store)
    one = call(d, job['id'], 'first', edit())['data']['version_id']
    text = 'e\u0301 / μg / 不 / <span>  exact  </span>'
    candidate = store.blob(job['id'], 'candidate', {'a/b~c': {'id': 'extra', 'pages': [1], 'markdown': text}})
    result = call(d, job['id'], 'local', {'base_version': one, 'expected_head': one, 'operations': [
        {'kind': 'insert', 'after_id': None, 'reuse_candidate': {'ref': candidate['ref'], 'pointer': '/a~1b~0c'}},
        {'kind': 'patch', 'id': 'extra', 'start': 0, 'end': 2, 'expected': 'e\u0301', 'text': 'e\u0301'},
        {'kind': 'insert', 'after_id': 'body', 'blocks': []},
        {'kind': 'replace', 'id': 'body', 'blocks': []}
    ]})
    assert result['ok'], result
    content = d.documents.version(job['id'], result['data']['version_id'])['content']
    assert len(content['blocks']) == 1 and content['blocks'][0]['markdown'] == text
