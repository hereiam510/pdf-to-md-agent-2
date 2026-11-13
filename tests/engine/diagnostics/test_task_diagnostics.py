"""F01/F02 synthetic catalog/API checks. Mock transports cannot use a provider."""
from hashlib import sha256
import json
import threading

from fastapi.testclient import TestClient
import httpx
import pytest

from pdfmd.diagnostics import Diagnostics, Unavailable
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, make_payload
from pdfmd.recovery import diagnose, resolve
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.server import create_app
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher
from tests.engine.execution.test_accepted_evidence_recovery import historical
from tests.engine.execution.test_continuation import delivery
from tests.engine.diagnostics.test_diagnostic_attribution_reasons import two_attempts, retained_native
from tests.engine.transport.test_response_repairs import native
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_stream_terminal import forbidden


def hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def seed_events(store, job, other, count):
    with store.transaction() as db:
        db.execute('DELETE FROM events WHERE job IN (?,?)', (job, other))
        for i in range(count):
            db.execute('INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)', (other, 'other', '{}', i))
            db.execute('INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)', (job, 'synthetic', json.dumps({'index': i}), i))
    return store.events(job, limit=count + 1)


@pytest.mark.parametrize('count', [0, 1, 100, 101, 1000, 1103])
def test_complete_event_boundary_refresh_ownership_and_no_copy_per_page(setup, source, count, monkeypatch):
    store, job = setup
    other = Evidence(store).create_job(str(source), 'Other isolated task.')['id']
    expected = seed_events(store, job['id'], other, count)
    import pdfmd.diagnostics as module
    copies = []
    original = module.copy_catalog
    monkeypatch.setattr(module, 'copy_catalog', lambda *args: (copies.append(True), original(*args))[1])
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.events(job['id'])
        assert page['total'] == count and page['last'] == count
        newest = page
        pages = [page['events']]
        while page['older']:
            page = service.events(job['id'], cursor=page['older'])
            pages.insert(0, page['events'])
        actual = [e for items in pages for e in items]
        assert [e['seq'] for e in actual] == [e['seq'] for e in expected]
        assert len({e['id'] for e in actual}) == count
        assert all(e['job'] == job['id'] for e in actual)
        if count:
            assert page['first'] == 1
            again = service.events(job['id'], cursor=newest['oldest'])
            forward = list(again['events'])
            while again['newer']:
                again = service.events(job['id'], cursor=again['newer'])
                forward.extend(again['events'])
            assert [e['seq'] for e in forward] == [e['seq'] for e in expected]
        assert len(copies) == 1
        assert hashes(store.root) == before
        with pytest.raises(Unavailable):
            service.events(other, cursor=newest['oldest'])
        with pytest.raises(ValueError):
            service.events(job['id'], cursor=newest['oldest'], limit=99)
        # Intentional writer interval. The existing boundary remains unchanged.
        store.event(job['id'], 'new_arrival', {})
        stable = service.events(job['id'], cursor=newest['recent'])
        assert stable['total'] == count
        fresh = service.events(job['id'])
        assert fresh['total'] == count + 1 and fresh['events'][-1]['type'] == 'new_arrival'
        service.close(job['id'], fresh['view'])
        with pytest.raises(Unavailable):
            service.events(job['id'], cursor=fresh['oldest'])
    finally:
        service.close()


def test_api_validation_poll_is_bounded_and_authentication(setup, source, monkeypatch):
    store, job = setup
    other = Evidence(store).create_job(str(source), 'Other')['id']
    seed_events(store, job['id'], other, 1103)
    app = create_app(store.root, 'synthetic-only', transport=httpx.MockTransport(forbidden))
    with TestClient(app, headers={'Authorization': 'Bearer synthetic-only'}) as client:
        assert client.get(f'/jobs/{job["id"]}/activity', headers={'Authorization': ''}).status_code == 401
        for limit in (0, -1, 201, 'no'):
            assert client.get(f'/jobs/{job["id"]}/activity', params={'limit': limit}).status_code == 422
        first = client.get(f'/jobs/{job["id"]}/activity').json()
        assert first['total'] == 1103 and first['last'] == 1103
        oldest = client.get(f'/jobs/{job["id"]}/activity', params={'cursor': first['oldest']}).json()
        assert oldest['first'] == 1
        assert client.get(f'/jobs/{other}/activity', params={'cursor': first['oldest']}).json()['status'] == 'unavailable'
        assert client.get(f'/jobs/{job["id"]}/activity', params={'cursor': 'forged'}).json()['status'] == 'unavailable'
        before = hashes(store.root)
        monkeypatch.setattr(Diagnostics, 'events', forbidden)
        monkeypatch.setattr(Diagnostics, 'records', forbidden)
        monkeypatch.setattr('pdfmd.recovery.inspection', forbidden)
        monkeypatch.setattr(Store, 'bytes', forbidden)
        for _ in range(3):
            value = client.get(f'/jobs/{job["id"]}').json()
            assert 'events' not in value and value['event_summary']['count'] == 1103
        assert hashes(store.root) == before


def freeze_prepared(store, job, *, proposal_ref=None):
    key = job['id'] + ':prepared:0'
    service = Nexus(store, forbidden, httpx.MockTransport(forbidden))
    route = Route.model_validate(job['route'])
    service.freeze(job['id'], key, make_payload(route, 'Synthetic', [], []), 'compaction',
        {'capacity': {'fits': False, 'input_estimate': 65000, 'capacity': 65536, 'output_reserve': 2048},
         'projection': [], 'covered': [], 'deferred': [], 'revision': 0,
         **({'proposal_ref': proposal_ref} if proposal_ref else {})})
    return key


def matching_requests(store, job, *, calls=None, protocol='chat_completions'):
    """File-backed same-task equal-content responses; transport is explicitly offline."""
    calls = calls or [tool('read_document', {})]
    if protocol == 'responses':
        job = store.update_job(job['id'], route={**job['route'], 'protocol': protocol,
                                               'endpoint': 'https://synthetic.invalid/v1/responses'})
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(
        lambda _: httpx.Response(200, json=native(protocol, *calls))))
    keys = [job['id'] + ':equal-a:0', job['id'] + ':equal-b:0']
    for key in keys:
        service.freeze(job['id'], key, make_payload(Route.model_validate(job['route']), 'Synthetic', [], []), 'normal', {})
        service.send(job['id'], key)
    call = store.json(f'accepted:{keys[0]}', job['id'])['calls'][0]
    op = {'id': keys[0] + ':0', 'tool': call['name'], 'status': 'done',
          'args_hash': sha256(encode([call['name'], call['arguments']])).hexdigest(), 'result': {}}
    store.put('operation', op['id'], job['id'], op)
    return keys, op


def test_wrong_published_pointer_cannot_confirm_equal_content_join(setup):
    store, job = setup
    (a, b), op = matching_requests(store, job)
    request = store.get('request', a)
    store.put('request', a, job['id'], {**request, 'accepted_ref': f'accepted:{b}'})
    # A's valid canonical staging is deliberately still present: no fallback.
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'operation', op['id'])
        assert detail['request'] is None, detail
        assert detail['request_association']['status'] == 'unconfirmed'
        request_detail = service.detail(job['id'], page['view'], 'request', a)
        link = next(x for x in request_detail['links'] if x['ref'] == f'accepted:{b}')
        assert link['status'] == 'unavailable'
        assert detail['request_association']['reason'] == link['reason']
        assert not request_detail['operations']
        assert request_detail['unconfirmed_operations'][0]['id'] == op['id']
        assert request_detail['unconfirmed_operations'][0]['reason'] == link['reason']
    finally:
        service.close()
    assert hashes(store.root) == before


def test_mixed_record_shapes_retain_good_rows_and_captured_pagination(setup):
    store, job = setup
    raw = [('good-new', {'status': 'prepared', 'attempts': []}), ('bad-array', []),
           ('good-middle', {'status': 'prepared', 'attempts': []}), ('bad-null', None),
           ('bad-attempts', {'attempts': 'abc'}), ('bad-json', '{broken'),
           ('good-old', {'status': 'prepared', 'attempts': []})]
    with store.transaction() as db:
        for index, (key, data) in enumerate(raw):
            db.execute('INSERT INTO records VALUES(?,?,?,?,?)',
                       ('request', key, job['id'], data if key == 'bad-json' else json.dumps(data), 100-index))
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'], limit=3)
        pages = [page]
        while page['next']:
            page = service.records(job['id'], cursor=page['next'], limit=3)
            pages.append(page)
        items = [item for page in pages for item in page['items']]
        assert [item['id'] for item in items] == [key for key, _ in raw]
        assert [item['created'] for item in items] == [100-i for i in range(len(raw))]
        assert [page['offset'] for page in pages] == [0, 3, 6]
        assert all(page['total'] == 7 for page in pages)
        for item in items:
            if item['id'].startswith('bad'):
                assert item['diagnostic_status'] == 'unavailable' and item['reason']
                assert 'attempts' not in item
            else:
                assert item['attempts'] == 0
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('damage', ['descriptor-ref', 'descriptor-kind', 'descriptor-task', 'descriptor-request',
                                  'attempt-id', 'attempt-request', 'membership-missing', 'membership-duplicate',
                                  'canonical-alias', 'response-root', 'calls-shape', 'call-shape'])
def test_shared_artifact_and_join_controls(setup, damage):
    from tests.engine.execution.test_accepted_evidence_recovery import replace_blob
    store, job = setup
    (key, _), op = matching_requests(store, job)
    ref = f'accepted:{key}'
    request = store.get('request', key)
    descriptor = store.get('blob', ref)
    aid = request['attempts'][0]
    if damage.startswith('descriptor-'):
        field = {'descriptor-ref': 'ref', 'descriptor-kind': 'kind', 'descriptor-task': 'job'}.get(damage)
        descriptor = {**descriptor, field: 'wrong'} if field else {**descriptor, 'meta': {**descriptor['meta'], 'request': 'wrong'}}
        store.put('blob', ref, job['id'], descriptor)
    elif damage.startswith('attempt-'):
        attempt = store.get('attempt', aid)
        store.put('attempt', aid, job['id'], {**attempt, damage.removeprefix('attempt-'): 'wrong'})
    elif damage.startswith('membership-'):
        store.put('request', key, job['id'], {**request, 'attempts': [] if damage.endswith('missing') else [aid, aid]})
    elif damage == 'canonical-alias':
        value = store.json(ref, job['id'])
        ref = 'synthetic-alias'
        store.blob(job['id'], 'accepted_response', value, descriptor['meta'], key=ref)
        store.put('request', key, job['id'], {**request, 'accepted_ref': ref})
    else:
        value = store.json(ref, job['id'])
        value = [] if damage == 'response-root' else {**value, 'calls': {} if damage == 'calls-shape' else [{'id': 'x', 'name': 'read_document', 'arguments': {}}]}
        replace_blob(store, job['id'], ref, encode(value))
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.events(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        link = next(x for x in detail['links'] if x['ref'] == ref)
        operation = service.detail(job['id'], page['view'], 'operation', op['id'])
        assert link['status'] == 'unavailable'
        assert operation['request'] is None and operation['origin'] == 'unattributed'
        assert operation['request_association']['reason'] == link['reason']
        assert detail['operations'] == []
        assert detail['unconfirmed_operations'][0]['reason'] == link['reason']
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('damage', ['request-id', 'request-task', 'operation-tool', 'operation-digest', 'operation-index', 'operation-range'])
def test_selected_identity_and_exact_operation_call_controls(setup, damage):
    store, job = setup
    (key, _), op = matching_requests(store, job)
    if damage.startswith('request-'):
        request = store.get('request', key)
        store.put('request', key, job['id'], {**request, 'id' if damage == 'request-id' else 'job': 'wrong'})
    else:
        field = {'operation-tool': 'tool', 'operation-digest': 'args_hash', 'operation-index': 'id', 'operation-range': 'id'}[damage]
        op = {**op, field: key + (':00' if damage == 'operation-index' else ':1') if field == 'id' else 'wrong'}
        store.put('operation', op['id'], job['id'], op)
    service = Diagnostics(store.root)
    before = hashes(store.root)
    try:
        page = service.events(job['id'])
        detail = service.detail(job['id'], page['view'], 'operation', op['id'])
        assert detail['request'] is None and detail['request_association']['reason']
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('protocol,published', [('chat_completions', True), ('responses', False)])
def test_confirmed_call_controls_keep_publication_and_exact_raw_access(setup, protocol, published, monkeypatch):
    store, job = setup
    (key, _), op = matching_requests(store, job, protocol=protocol)
    if not published:
        request = store.get('request', key)
        store.put('request', key, job['id'], {**request, 'accepted_ref': None, 'status': 'in_flight'})
    service = Diagnostics(store.root)
    before = hashes(store.root)
    # Projection must not turn into a new eligibility/stream/settlement owner.
    monkeypatch.setattr('pdfmd.acceptance.inspect_acceptance', forbidden)
    monkeypatch.setattr('pdfmd.recovery.inspect_acceptance', forbidden)
    try:
        page = service.events(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        operation = service.detail(job['id'], page['view'], 'operation', op['id'])
        expected = 'published' if published else 'unpublished'
        assert operation['request'] == key
        assert operation['request_association']['publication'] == expected
        assert detail['operations'][0]['publication'] == expected
        opened = service.evidence(job['id'], page['view'], f'accepted:{key}', mode='raw')
        assert opened['complete'] is True
        import base64
        assert base64.b64decode(opened['data']) == store.bytes(f'accepted:{key}', job['id'])
        assert 'graph readiness not inferred' in operation['request_association']['meaning']
    finally:
        service.close()
    assert hashes(store.root) == before


def test_row_shapes_api_reopen_nonrequest_empty_and_query_failure(setup, source, monkeypatch):
    import sqlite3
    store, job = setup
    other = Evidence(store).create_job(str(source), 'Other')['id']
    bad = [('array', []), ('scalar', 1), ('null', None), ('string', 'text'), ('attempts-string', {'attempts': 'abc'}),
           ('attempts-dict', {'attempts': {}}), ('attempts-null', {'attempts': None}), ('attempts-missing', {}),
           ('attempts-member', {'attempts': [1]}), ('summary-shape', {'attempts': [], 'status': {}})]
    with store.transaction() as db:
        for i, (key, data) in enumerate([('good', {'status': 'prepared', 'attempts': []}), *bad]):
            db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('request', key, job['id'], json.dumps(data), 100-i))
        db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('context_commit', 'bad-context', job['id'], '{broken', 1))
        db.execute('INSERT INTO records VALUES(?,?,?,?,?)', ('context_commit', 'good-context', job['id'], '{}', 0))
    for _ in range(2):
        # App construction is setup; only the following reads are measured.
        app = create_app(store.root, 'synthetic-only', transport=httpx.MockTransport(forbidden))
        with TestClient(app, headers={'Authorization': 'Bearer synthetic-only'}) as client:
            before = hashes(store.root)
            overview = client.get(f'/jobs/{job["id"]}').json()
            assert len(overview['requests']) == 11 and overview['event_summary']
            assert next(x for x in overview['requests'] if x['id'] == 'good')['attempts'] == 0
            assert all(x['reason'] for x in overview['requests'] if x.get('diagnostic_status') == 'unavailable')
            assert any('no eligibility conclusion' in reason for reason in overview['diagnostic_limitations'])
            page = client.get(f'/jobs/{job["id"]}/diagnostics', params={'limit': 3}).json()
            assert page['status'] == 'ok' and page['total'] == 11 and page['items'][0]['id'] == 'good'
            items = list(page['items'])
            while page['next']:
                page = client.get(f'/jobs/{job["id"]}/diagnostics', params={'limit': 3, 'cursor': page['next']}).json()
                items.extend(page['items'])
            assert [x['id'] for x in items] == ['good', *[key for key, _ in bad]]
            assert all(x['diagnostic_status'] == 'unavailable' and x['reason'] for x in items[1:])
            context = client.get(f'/jobs/{job["id"]}/diagnostics', params={'kind': 'context_commit'}).json()
            assert context['total'] == 2 and context['items'][0]['reason'] == 'Malformed record JSON.'
            assert context['items'][1]['id'] == 'good-context'
            detail = client.get(f'/jobs/{job["id"]}/diagnostics/record', params={'view': page['view'], 'kind': 'request', 'key': 'array'}).json()
            assert detail['status'] == 'unavailable' and detail['reason']
            empty = client.get(f'/jobs/{other}/diagnostics').json()
            assert empty['status'] == 'ok' and empty['total'] == 0 and empty['items'] == []
            cross = client.get(f'/jobs/{other}/diagnostics', params={'view': page['view']}).json()
            assert cross['status'] == 'unavailable'
            def failed(*args, **kwargs):
                raise sqlite3.DatabaseError('Synthetic catalog query failure')
            with monkeypatch.context() as patch:
                patch.setattr(app.state.engine.diagnostics, 'records', failed)
                failed_page = client.get(f'/jobs/{job["id"]}/diagnostics').json()
                assert failed_page['status'] == 'unavailable' and 'query failure' in failed_page['reason']
            assert hashes(store.root) == before


def test_prepared_no_dispatch_context_facts_and_no_initializers(setup, monkeypatch):
    store, job = setup
    key = freeze_prepared(store, job)
    before = hashes(store.root)
    service = Diagnostics(store.root)
    for target in (Store, Runtime, Dispatcher):
        monkeypatch.setattr(target, '__init__', forbidden)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        assert detail['boundary'] == 'prepared; no dispatch attempt recorded'
        assert detail['attempts'] == []
        assert detail['frozen_preparation']['meta']['capacity']['fits'] is False
        assert detail['publication']['pointer'] is None
        assert 'unchecked' in detail['graph']
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('protocol', ['chat_completions', 'responses'])
def test_partial_a_zero_b_attribution_and_exact_access(setup, protocol):
    store, job, key, (a, b), raw, _ = two_attempts(setup, protocol)
    native_ref = retained_native(store, job, key, a)
    request = store.get('request', key)
    store.put('request', key, job['id'], {**request, 'response_ref': native_ref})
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        assert [x['id'] for x in detail['attempts']] == [a, b]
        assert detail['attempts'][1]['record']['transport']['received_body_bytes'] == 0
        links = {link['ref']: link for link in detail['links']}
        assert links[f'raw-stream:{a}']['facts']['attempt'] == a
        assert links[f'raw-stream:{a}']['facts']['relation'] == 'earlier_attempt'
        assert links[native_ref]['facts']['attempt'] == a
        import base64
        opened = service.evidence(job['id'], page['view'], f'raw-stream:{a}', mode='raw')
        assert base64.b64decode(opened['data']) == raw and opened['complete']
        selected = service.evidence(job['id'], page['view'], f'raw-stream:{a}', mode='raw', start=1, end=7)
        assert base64.b64decode(selected['data']) == raw[1:7] and not selected['complete']
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('published', [False, True])
@pytest.mark.parametrize('gap', [False, True])
def test_resolution_publication_and_receipt_does_not_prove_graph(setup, monkeypatch, published, gap):
    store, job, key, reply, _ = historical(setup, monkeypatch, 'chat_completions', published)
    diagnosis = diagnose(store.root, job['id'])
    if gap:
        def stop(*_): raise RuntimeError('synthetic interruption after catalog commit')
        with monkeypatch.context() as patch:
            patch.setattr('pdfmd.recovery.committed', stop)
            with pytest.raises(RuntimeError): resolve(store, job['id'], key, diagnosis['basis'])
    else:
        resolve(store, job['id'], key, diagnosis['basis'])
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        assert bool(detail['publication']['pointer']) is published
        assert detail['publication']['staging_ref'] == f'accepted:{key}'
        assert any(x['kind'] == 'conflict_resolution' and x['id'] == key for x in detail['related'])
        receipt = service.detail(job['id'], page['view'], 'conflict_resolution', key)
        assert receipt['projection'].startswith('unchecked')
        opened = service.evidence(job['id'], page['view'], receipt['record']['ref'])
        assert opened['value']['original_request']['accepted_ref'] == (reply and f'accepted:{key}' if published else None)
        assert detail['saved_acceptance_facts']['original_usage'] == (reply['usage'] if published else None)
    finally:
        service.close()
    assert hashes(store.root) == before


def test_document_atomic_event_gap_reuse_skip_unknown_and_manual(delivery, monkeypatch):
    store, job, seed, _, _ = delivery
    args = {'base_version': seed, 'expected_head': seed, 'claim': 'partial'}
    # Document-owned transaction commits before the version_saved event. The
    # dispatcher does not need to publish an envelope to establish that fact.
    dispatch = Dispatcher(store)
    digest, candidate = dispatch.capture(job['id'], 'manual:atomic', 'edit_document', json.dumps(args))
    with monkeypatch.context() as patch:
        patch.setattr(store, 'event', forbidden)
        with pytest.raises(BaseException):
            dispatch.documents.edit(job['id'], 'manual:atomic', args, digest, candidate['ref'])
    op = store.get('operation', 'manual:atomic')
    version = op['result']['version_id']
    assert not any(e['type'] == 'version_saved' and e['data'].get('version_id') == version for e in store.events(job['id']))
    assert dispatch.reconcile(job['id'], 'manual:atomic', 'edit_document', json.dumps(args))['data']['version_id'] == version
    dispatch.skip(job['id'], 'skipped', 'read_document', '{}')
    digest, candidate = dispatch.capture(job['id'], 'unknown', 'run_script', '{}')
    store.put('operation', 'unknown', job['id'], {'id': 'unknown', 'tool': 'run_script', 'status': 'started', 'args_hash': digest, 'candidate_ref': candidate['ref']})
    # Model historical missing operation metadata while retaining the complete
    # source-led immutable seed version. This is fixture setup, not inspection.
    with store.transaction() as db:
        db.execute("DELETE FROM records WHERE kind='operation' AND id='seed'")
    before = hashes(store.root)
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'], 'operation')
        atomic = service.detail(job['id'], page['view'], 'operation', 'manual:atomic')
        assert atomic['effect'].startswith('committed document version') and atomic['version'] == version
        assert atomic['origin'] == 'manual' and atomic['execution_history'].startswith('unknown')
        saved = service.detail(job['id'], page['view'], 'version', version)
        assert saved['operations'][0]['id'] == 'manual:atomic'
        assert service.detail(job['id'], page['view'], 'operation', 'skipped')['effect'].startswith('not_started')
        assert service.detail(job['id'], page['view'], 'operation', 'unknown')['effect'] == 'pending/unknown effects'
        seed_detail = service.detail(job['id'], page['view'], 'version', seed)
        assert seed_detail['origin'] == 'unattributed'
        assert seed_detail['verification'].startswith('version files checked')
    finally:
        service.close()
    assert hashes(store.root) == before


@pytest.mark.parametrize('damage', ['missing', 'corrupt', 'mismatch', 'foreign', 'stale'])
def test_scoped_missing_corrupt_mismatch_stale_does_not_erase_independent_facts(setup, monkeypatch, source, damage):
    store, job, key, reply, _ = historical(setup, monkeypatch, 'chat_completions')
    ref = reply['native_ref']
    blob = store.get('blob', ref)
    service = Diagnostics(store.root)
    try:
        if damage == 'missing': (store.root / 'objects' / blob['sha256']).unlink()
        elif damage == 'corrupt': (store.root / 'objects' / blob['sha256']).write_bytes(b'corrupt')
        elif damage == 'mismatch': store.put('blob', ref, job['id'], {**blob, 'meta': {**blob['meta'], 'attempt': 'wrong'}})
        elif damage == 'foreign':
            other = Evidence(store).create_job(str(source), 'Other')['id']
            store.put('blob', ref, other, {**blob, 'job': other})
        page = service.records(job['id'])
        if damage == 'stale':
            store.update_job(job['id'], last_message='intentional writer')
            with pytest.raises(Unavailable) as caught: service.detail(job['id'], page['view'], 'request', key)
            assert caught.value.status == 'stale'
        else:
            before = hashes(store.root)
            detail = service.detail(job['id'], page['view'], 'request', key)
            assert detail['attempts'] and detail['publication']['pointer']
            broken = next(link for link in detail['links'] if link['ref'] == ref)
            assert broken['status'] == 'unavailable'
            assert hashes(store.root) == before
    finally:
        service.close()


def test_usage_zero_unknown_conflict_and_rejected_raw_remain_separate(setup, monkeypatch):
    store, job, key, reply, _ = historical(setup, monkeypatch, 'chat_completions')
    attempt = store.get('attempt', store.get('request', key)['attempts'][0])
    store.put('attempt', attempt['id'], job['id'], {**attempt, 'usage': 0})
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        assert detail['attempts'][0]['record']['usage'] == 0
        assert detail['attempts'][0]['usage_state'] == 'reported'
        assert detail['saved_acceptance_facts']['saved_usage'] == reply['usage']
        assert detail['raw_usage'][0]['usage'] == reply['usage']
    finally: service.close()
    request = store.get('request', key)
    store.put('request', key, job['id'], {**request, 'status': 'rejected', 'accepted_ref': None})
    store.put('attempt', attempt['id'], job['id'], {**attempt, 'status': 'rejected', 'usage': None})
    service = Diagnostics(store.root)
    try:
        page = service.records(job['id'])
        detail = service.detail(job['id'], page['view'], 'request', key)
        assert detail['attempts'][0]['usage_state'] == 'unknown'
        assert detail['raw_usage'][0]['usage'] == reply['usage']
        assert 'not a settlement' in detail['raw_usage'][0]['meaning']
    finally: service.close()


def test_live_wal_included_and_writer_changes_distinct_from_inspector(setup):
    store, job = setup
    writer = store.connect()
    try:
        writer.execute('INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)', (job['id'], 'committed_in_live_wal', '{}', 1))
        writer.commit()
        assert (store.root / 'catalog.sqlite-wal').stat().st_size > 0
        before = hashes(store.root)
        service = Diagnostics(store.root)
        try:
            first = service.events(job['id'])
            assert first['events'][-1]['type'] == 'committed_in_live_wal'
            assert hashes(store.root) == before
            done = threading.Event()
            def write():
                store.event(job['id'], 'legitimate_writer', {})
                done.set()
            thread = threading.Thread(target=write); thread.start(); thread.join(timeout=5)
            assert done.is_set()
            # New writer data does not enter the captured event boundary.
            stable_before = hashes(store.root)
            assert service.events(job['id'], cursor=first['recent'])['total'] == first['total']
            assert hashes(store.root) == stable_before
            fresh = service.events(job['id'])
            assert fresh['total'] == first['total'] + 1
        finally: service.close()
    finally: writer.close()


def test_native_accepted_handoff_rejection_keeps_usage_and_links(setup):
    store, job = setup
    key = job['id'] + ':0:0'
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, json=native('chat_completions', text='{}'))))
    runtime = Runtime(store, service)
    try:
        route = Route.model_validate(job['route'])
        service.freeze(job['id'], key, make_payload(route, 'Synthetic', [], []), 'compaction', {'covered': [], 'revision': 0, 'deferred': []})
        state = {'job': job['id'], 'seq': 0, 'revision': 0, 'pending': key, 'history': [], 'repairs': {}}
        changed = runtime.compact(state)
        assert changed['repairs']['compaction']['feedback_ref'] == f'repair:{key}'
    finally: runtime.close()
    before = hashes(store.root)
    diagnostics = Diagnostics(store.root)
    try:
        page = diagnostics.records(job['id'])
        detail = diagnostics.detail(job['id'], page['view'], 'request', key)
        assert detail['attempts'][0]['record']['status'] == 'accepted'
        assert detail['attempts'][0]['record']['usage'] is not None
        repair = diagnostics.evidence(job['id'], page['view'], f'repair:{key}')['value']
        assert repair['code'] == 'invalid_handoff'
        assert any(e['data'].get('code') == 'invalid_handoff' for e in detail['events'])
        assert any(link['ref'] == f'repair:{key}' for link in detail['links'])
    finally: diagnostics.close()
    assert hashes(store.root) == before


def test_normal_acceptance_operation_join_and_context_commit_gap(setup):
    store, job = setup
    key = job['id'] + ':0:0'
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, json=native('chat_completions', tool('read_document', {})))))
    route = Route.model_validate(job['route'])
    service.freeze(job['id'], key, make_payload(route, 'Synthetic', [], []), 'normal', {})
    reply = service.send(job['id'], key)
    call = reply['calls'][0]
    dispatcher = Dispatcher(store)
    result = dispatcher.execute(job['id'], key + ':0', call['name'], call['arguments'])
    assert dispatcher.execute(job['id'], key + ':0', call['name'], call['arguments']) == result
    # Explicit synthetic catalog context facts, matching the actual publication
    # schema, intentionally without the following event/graph projection.
    ref = f'context-settlement:{key}'
    store.blob(job['id'], 'context_settlement', {'feedback': {'status': 'waiting', 'reason': 'history_pressure', 'capacity': {'input_estimate': 65000}}, 'changes': {}}, key=ref)
    store.put('context_commit', ref, job['id'], {'receipt_ref': ref, 'proposal_ref': f'context-proposal:{key}', 'status': 'waiting'})
    diagnostics = Diagnostics(store.root)
    before = hashes(store.root)
    try:
        page = diagnostics.records(job['id'])
        detail = diagnostics.detail(job['id'], page['view'], 'request', key)
        assert detail['publication']['pointer'] == f'accepted:{key}'
        assert detail['operations'][0]['id'] == key + ':0'
        operation = diagnostics.detail(job['id'], page['view'], 'operation', key + ':0')
        assert operation['request'] == key and operation['execution_history'].startswith('unknown')
        assert detail['related'][0]['record']['receipt_ref'] == ref
        assert diagnostics.evidence(job['id'], page['view'], ref)['value']['feedback']['reason'] == 'history_pressure'
        with pytest.raises(ValueError): diagnostics.evidence(job['id'], page['view'], '../../outside')
    finally: diagnostics.close()
    assert hashes(store.root) == before


def test_session_expiry_capture_change_and_record_pagination(setup, monkeypatch):
    store, job = setup
    for i in range(103): store.put('operation', f'unknown-{i}', job['id'], {'id': f'unknown-{i}', 'status': 'started', 'tool': 'unknown'})
    diagnostics = Diagnostics(store.root)
    try:
        first = diagnostics.records(job['id'], 'operation')
        second = diagnostics.records(job['id'], 'operation', token=first['view'], cursor=first['next'])
        third = diagnostics.records(job['id'], 'operation', token=first['view'], cursor=second['next'])
        assert len({x['id'] for page in (first, second, third) for x in page['items']}) == 103
        assert third['next'] is None
        diagnostics.sessions[first['view']]['captured_at'] -= 901
        with pytest.raises(Unavailable): diagnostics.records(job['id'], token=first['view'])
        import pdfmd.diagnostics as module
        original = module.identity
        observations = []
        def changing(root):
            value = original(root)
            observations.append(True)
            if len(observations) > 1: value['synthetic-change'] = (1, 2, 3, 4)
            return value
        monkeypatch.setattr(module, 'identity', changing)
        with pytest.raises(Unavailable) as caught: diagnostics.events(job['id'])
        assert caught.value.status == 'stale'
    finally: diagnostics.close()


def test_corrupt_event_is_retained_in_page_and_bad_record_identity_refuses(setup):
    store, job = setup
    with store.transaction() as db:
        db.execute('INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)', (job['id'], 'corrupt', '{broken', 1))
    key = freeze_prepared(store, job)
    request = store.get('request', key)
    store.put('request', key, job['id'], {**request, 'id': 'wrong'})
    diagnostics = Diagnostics(store.root)
    before = hashes(store.root)
    try:
        page = diagnostics.events(job['id'])
        damaged = next(item for item in page['events'] if item['type'] == 'corrupt')
        assert damaged['data']['raw'] == '{broken' and page['total'] == len(page['events'])
        with pytest.raises(ValueError): diagnostics.detail(job['id'], page['view'], 'request', key)
    finally: diagnostics.close()
    assert hashes(store.root) == before


def test_corrupt_unrelated_operation_or_staging_keeps_request_facts(setup, monkeypatch):
    store, job, key, _, _ = historical(setup, monkeypatch, 'chat_completions')
    with store.transaction() as db:
        db.execute("INSERT INTO records VALUES(?,?,?,?,?)", ('operation', 'corrupt-op', job['id'], '{broken', 1))
        db.execute("UPDATE records SET data=? WHERE kind='blob' AND id=?", ('{broken', f'accepted:{key}'))
    before = hashes(store.root)
    diagnostics = Diagnostics(store.root)
    try:
        page = diagnostics.events(job['id'])
        detail = diagnostics.detail(job['id'], page['view'], 'request', key)
        assert detail['attempts'] and detail['frozen_preparation']
        assert detail['publication']['pointer'] == f'accepted:{key}'
        assert any('Staging descriptor unavailable' in item for item in detail['limitations'])
        assert any('Operation inventory incomplete' in item for item in detail['limitations'])
    finally: diagnostics.close()
    assert hashes(store.root) == before


def test_explicit_earlier_context_proposal_check_and_frozen_input_are_direct_links(setup):
    store, job = setup
    proposal = 'context-proposal:earlier-request'
    store.blob(job['id'], 'context_proposal', {'context_proposal': {'batch': 'earlier-request', 'operations': []}}, key=proposal)
    runtime = Runtime(store, Nexus(store, forbidden, httpx.MockTransport(forbidden)))
    try:
        check = runtime.context_updates.wait(job, {'seq': 1, 'revision': 1, 'history': [], 'context_waiting': proposal}, 'compaction', 'Recorded synthetic history pressure', capacity={'fits': False})['context_check']
    finally: runtime.close()
    key = job['id'] + ':later:0'
    feedback = f'context-settlement:{key}'
    store.blob(job['id'], 'context_settlement', {'feedback': {'reason': 'recorded'}}, key=feedback)
    service = Nexus(store, forbidden, httpx.MockTransport(forbidden))
    route = Route.model_validate(job['route'])
    request = service.freeze(job['id'], key, make_payload(route, 'Synthetic', [], []), 'compaction',
        {'proposal_ref': proposal, 'context_snapshot': {'state': {'context_check': check, 'context_feedback': feedback}}})
    store.put('context_disposition', proposal, job['id'], {'proposal_ref': proposal, 'status': 'eligible_pending'})
    diagnostics = Diagnostics(store.root)
    before = hashes(store.root)
    try:
        page = diagnostics.events(job['id'])
        detail = diagnostics.detail(job['id'], page['view'], 'request', key)
        links = {link['ref']: link for link in detail['links']}
        for ref in (proposal, check, request['payload_ref'], feedback):
            assert links[ref]['status'].startswith('available')
        assert len(links) == len(detail['links'])
        assert any(item['id'] == proposal for item in detail['related'])
        assert diagnostics.evidence(job['id'], page['view'], check)['value']['reason'] == 'compaction'
        assert diagnostics.evidence(job['id'], page['view'], request['payload_ref'])['value']['model'] == route.model
    finally: diagnostics.close()
    assert hashes(store.root) == before
