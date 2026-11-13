"""New isolated F01/F02 UI/API inputs. Every network send uses MockTransport."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import httpx
import pymupdf
import pytest

from tests.desktop.fixtures.workspace_hashes import workspace_hashes
from tests.engine.execution.test_continuation import delivery
from tests.engine.diagnostics.test_task_diagnostics import freeze_prepared, seed_events
from tests.engine.execution.test_accepted_evidence_recovery import historical
from tests.engine.diagnostics.test_diagnostic_attribution_reasons import two_attempts, retained_native
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native
from pdfmd.documents import Documents
from pdfmd.diagnostics import Diagnostics
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, make_payload
from pdfmd.recovery import diagnose, resolve
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher


def hashes(directory):
    result = {f'workspace/{name}': digest for name, digest in workspace_hashes(directory / 'workspace').items()}
    for name in ('source.pdf', 'existing-delivery.zip'):
        path = directory / name
        if path.is_file():
            result[name] = sha256(path.read_bytes()).hexdigest()
    return result


def prepare(directory):
    route = {'endpoint': 'https://synthetic.invalid/v1/chat/completions', 'model': 'offline-F01-F02', 'protocol': 'chat_completions', 'context_tokens': 65536, 'output_tokens': 2048}
    store, job, version, image, source = delivery.__wrapped__(directory, route)
    jid = job['id']
    store.update_job(jid, name='Diagnostics synthetic')
    dispatcher = Dispatcher(store)
    key = jid + ':0:0'
    edit = {'base_version': version, 'expected_head': version, 'claim': 'complete'}
    calls = [tool('edit_document', edit, 'atomic'), tool('read_document', {}, 'skip'), tool('run_script', {'code': 'pass'}, 'unknown')]
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, json=native('chat_completions', *calls))))
    service.freeze(jid, key, make_payload(Route.model_validate(job['route']), 'Synthetic', [], []), 'normal', {'capacity': {'input_estimate': 1200, 'capacity': 65536, 'output_reserve': 2048, 'fits': True}})
    reply = service.send(jid, key)
    digest, candidate = dispatcher.capture(jid, key + ':0', 'edit_document', json.dumps(edit))
    with pytest.MonkeyPatch.context() as patch:
        def interrupted(*_): raise RuntimeError('Synthetic missing event after atomic commit')
        patch.setattr(store, 'event', interrupted)
        try: dispatcher.documents.edit(jid, key + ':0', edit, digest, candidate['ref'])
        except RuntimeError: pass
    head = store.get('operation', key + ':0')['result']['version_id']
    # The existing receipt is actually reused; individual returns are not logged.
    dispatcher.reconcile(jid, key + ':0', 'edit_document', json.dumps(edit))
    dispatcher.skip(jid, key + ':1', 'read_document', reply['calls'][1]['arguments'])
    digest, candidate = dispatcher.capture(jid, key + ':2', 'run_script', reply['calls'][2]['arguments'])
    store.put('operation', key + ':2', jid, {'id': key + ':2', 'tool': 'run_script', 'args_hash': digest, 'candidate_ref': candidate['ref'], 'status': 'started'})
    earlier_proposal_ref = f'context-proposal:{key}'
    store.blob(jid, 'context_proposal', {'context_proposal': {'batch': key, 'operations': [], 'policy': {'notes': 'Explicit earlier-revision fixture; not an applied policy.'}}}, key=earlier_proposal_ref)
    store.put('context_disposition', earlier_proposal_ref, jid, {'proposal_ref': earlier_proposal_ref, 'status': 'eligible_pending'})
    prepared = freeze_prepared(store, job, proposal_ref=earlier_proposal_ref)
    context_ref = f'context-settlement:{key}'
    store.blob(jid, 'context_settlement', {'feedback': {'status': 'waiting', 'reason': 'history_pressure', 'capacity': {'input_estimate': 65000}}, 'changes': {}}, key=context_ref)
    store.put('context_commit', context_ref, jid, {'receipt_ref': context_ref, 'proposal_ref': f'context-proposal:{key}', 'status': 'waiting'})
    # An explicit fixture conflict preserves raw accepted usage separately.
    aid = store.get('request', key)['attempts'][0]
    attempt = store.get('attempt', aid)
    store.put('attempt', aid, jid, {**attempt, 'usage': 0})
    runtime = Runtime(store, service)
    runtime.graph.update_state({'configurable': {'thread_id': jid}}, {'job': jid, 'seq': 0, 'revision': 0, 'history': [], 'pending': key, 'next': 'tools'}, as_node='model')
    runtime.close()
    Documents(store).export(jid, version, str(directory / 'existing-delivery.zip'))
    extra = {}
    for name in ('Interleaved synthetic', 'Empty synthetic', 'Exact boundary synthetic', 'Attribution synthetic', 'Published resolution synthetic', 'Staging resolution synthetic', 'Handoff rejection synthetic', 'Rejected raw synthetic'):
        task = Evidence(store).create_job(str(source), 'Synthetic diagnostic fixture.', route)
        task = store.update_job(task['id'], name=name)
        extra[name] = {'job': task['id']}
        if name.startswith('Attribution'):
            _, task, request, (a, b), raw, _ = two_attempts((store, task), 'chat_completions')
            native_ref = retained_native(store, task, request, a)
            record = store.get('request', request)
            store.put('request', request, task['id'], {**record, 'response_ref': native_ref})
            extra[name].update(request=request, a=a, b=b, stream_ref=f'raw-stream:{a}', raw_hex=raw.hex())
        elif 'resolution' in name:
            published = name.startswith('Published')
            with pytest.MonkeyPatch.context() as patch:
                _, task, request, _, _ = historical((store, task), patch, 'chat_completions', published=published)
            diagnosis = diagnose(store.root, task['id'])
            with pytest.MonkeyPatch.context() as patch:
                if not published:
                    def gap(*_): raise RuntimeError('Synthetic catalog receipt before graph projection')
                    patch.setattr('pdfmd.recovery.committed', gap)
                try: resolve(store, task['id'], request, diagnosis['basis'])
                except RuntimeError:
                    if published: raise
            extra[name].update(request=request, published=published)
        elif name.startswith('Handoff'):
            request = task['id'] + ':0:0'
            nexus = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, json=native('chat_completions', text='{}'))))
            runtime = Runtime(store, nexus)
            nexus.freeze(task['id'], request, make_payload(Route.model_validate(task['route']), 'Synthetic', [], []), 'compaction', {'covered': [], 'revision': 0, 'deferred': []})
            runtime.compact({'job': task['id'], 'pending': request, 'seq': 0, 'revision': 0, 'history': [], 'repairs': {}})
            runtime.close()
            extra[name].update(request=request)
        elif name.startswith('Rejected'):
            value = native('chat_completions', text='Retained invalid completion')
            value['choices'][0]['finish_reason'] = 'length'
            nexus = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
            request = task['id'] + ':0:0'
            nexus.freeze(task['id'], request, make_payload(Route.model_validate(task['route']), 'Synthetic', [], []), 'normal', {})
            from pdfmd.nexus import StopRun
            try: nexus.send(task['id'], request)
            except StopRun: pass
            extra[name].update(request=request)
    seed_events(store, jid, extra['Interleaved synthetic']['job'], 1103)
    with store.transaction() as db:
        db.execute('DELETE FROM events WHERE job=?', (extra['Empty synthetic']['job'],))
        db.execute('DELETE FROM events WHERE job=?', (extra['Exact boundary synthetic']['job'],))
        db.executemany('INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)', [(extra['Exact boundary synthetic']['job'], 'boundary', json.dumps({'index': i}), i) for i in range(100)])
    expected = store.events(jid, limit=1200)
    result = {'job': jid, 'request': key, 'prepared': prepared, 'version': version, 'head': head, 'image': image,
              'events': [e['seq'] for e in expected], 'native_ref': reply['native_ref'], 'earlier_proposal_ref': earlier_proposal_ref, 'context_ref': context_ref, 'tasks': extra, 'network': 'MockTransport only; no real provider calls'}
    (directory / 'fixture.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def verify(directory):
    value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
    before = hashes(directory)
    folder = directory / 'workspace' / 'versions' / value['version']
    diagnostic = Diagnostics(directory / 'workspace')
    try:
        with diagnostic.read(value['job']) as (view, _):
            saved = json.loads((folder / 'document.json').read_bytes())
            assert view.bytes(saved['source_ref'], value['job']) == (directory / 'source.pdf').read_bytes()
    finally:
        diagnostic.close()
    with pymupdf.open(directory / 'source.pdf') as pdf, zipfile.ZipFile(directory / 'existing-delivery.zip') as archive:
        markdown = archive.read('document.md').decode('utf-8')
        lines = [line for page in pdf for line in page.get_text().splitlines()]
        assert all(line in markdown for line in lines)
        names = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
        assert set(archive.namelist()) == names
        for name in names: assert archive.read(name) == (folder / name).read_bytes()
        pix = pymupdf.Pixmap(archive.read(value['image']['asset_path']))
        original = pdf[1].get_pixmap(dpi=144, alpha=False)
        assert pix.samples == original.samples and (pix.width, pix.height) == (original.width, original.height)
        result = {'source_lines': lines, 'image_pixels': [pix.width, pix.height], 'zip_members': sorted(names), 'all_members_exact': True, 'selected_version': value['version'], 'head': value['head']}
    assert hashes(directory) == before
    result['audit_no_write'] = True
    return result


def consistency(directory):
    """Intentional synthetic corruption, entirely outside inspection intervals."""
    value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
    store = Store(directory / 'workspace')
    jid, a = value['job'], value['request']
    accepted = store.json(f'accepted:{a}', jid)
    calls = [tool(call['name'], json.loads(call['arguments']), call['id']) for call in accepted['calls']]
    b = jid + ':equal-b:0'
    job = store.get('job', jid)
    nexus = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(
        lambda _: httpx.Response(200, json=native('chat_completions', *calls))))
    nexus.freeze(jid, b, make_payload(Route.model_validate(job['route']), 'Synthetic B', [], []), 'normal', {})
    nexus.send(jid, b)
    request = store.get('request', a)
    store.put('request', a, jid, {**request, 'accepted_ref': f'accepted:{b}'})
    call = accepted['calls'][0]
    store.put('operation', b + ':0', jid, {'id': b + ':0', 'tool': call['name'], 'status': 'started',
              'args_hash': sha256(encode([call['name'], call['arguments']])).hexdigest()})
    mixed = [('bad-array', []), ('bad-json', '{broken'), ('bad-attempts-string', {'attempts': 'abc'}),
             ('bad-attempts-dict', {'attempts': {}}), ('bad-missing-attempts', {}),
             ('bad-summary', {'attempts': [], 'status': {}})]
    mixed += [(f'good-{i:02}', {'id': f'good-{i:02}', 'job': jid, 'status': 'prepared', 'attempts': []}) for i in range(51)]
    mixed += [('bad-null', None), ('bad-scalar', 7)]
    order = [a, 'bad-array', b, value['prepared'], *[key for key, _ in mixed if key != 'bad-array']]
    with store.transaction() as db:
        for key, data in mixed:
            db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('request', key, jid,
                       data if key == 'bad-json' else json.dumps(data), 0))
        for index, key in enumerate(order):
            db.execute("UPDATE records SET created=? WHERE kind='request' AND id=?", (10000-index, key))
        db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('context_commit', 'bad-context-json', jid, '{broken', 10000))
    value.update(equal_b=b, request_order=order, corruption='A published pointer selects B; A canonical staging remains intact',
                 equal_b_raw_sha256=sha256(store.bytes(f'accepted:{b}', jid)).hexdigest(),
                 network='All fixture sends use explicit MockTransport. App inspection performs no sends.')
    (directory / 'fixture.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
    return value


if __name__ == '__main__':
    action, path = sys.argv[1:3]
    directory = Path(path)
    if action == 'prepare':
        directory.mkdir(parents=True, exist_ok=False)
        result = prepare(directory)
    elif action == 'hash': result = hashes(directory)
    elif action == 'facts':
        value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
        service = Diagnostics(directory / 'workspace')
        try:
            with service.read(value['job']) as (view, _):
                rows = view.connection.execute("SELECT kind,id,job,data FROM records WHERE kind IN ('job','request','attempt','stream_receive','operation','version','context_policy','context_commit','context_disposition','conflict_resolution') ORDER BY kind,id").fetchall()
                result = {f"{row['kind']}/{row['id']}": {'job': row['job'], 'sha256': sha256(row['data'].encode()).hexdigest()} for row in rows}
        finally:
            service.close()
    elif action == 'verify': result = verify(directory)
    elif action == 'consistency': result = consistency(directory)
    elif action == 'arrive':
        value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
        store = Store(directory / 'workspace')
        store.event(value['job'], 'new_after_boundary', {'meaning': 'intentional fixture writer'})
        result = {'intentional_writer': True}
    elif action == 'stale':
        value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
        Store(directory / 'workspace').update_job(value['job'], status='paused')
        result = {'intentional_writer': True}
    elif action == 'damage':
        value = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
        store = Store(directory / 'workspace')
        blob = store.get('blob', value['native_ref'], job=value['job'])
        path = store.root / 'objects' / blob['sha256']
        (directory / 'preserved-original-native').write_bytes(path.read_bytes())
        path.write_bytes(b'Synthetic corrupt native artifact; original preserved separately.')
        result = {'intentional_fixture_damage': True, 'ref': value['native_ref']}
    else: raise ValueError(action)
    print(json.dumps(result))
