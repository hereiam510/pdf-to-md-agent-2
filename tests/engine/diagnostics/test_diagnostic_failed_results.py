"""D03 file-backed result-boundary controls. No Nexus or model invocation."""
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from pdfmd.diagnostics import Diagnostics
from pdfmd.documents import Documents
from pdfmd.server import create_app
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher
from tests.engine.execution.test_continuation import delivery
from tests.engine.diagnostics.test_task_diagnostics import hashes
from tests.engine.transport.test_stream_terminal import forbidden


SHAPE_REASON = 'Descriptor metadata/kind has an unsupported shape.'


def seed(directory):
    route = {'endpoint': 'https://synthetic.invalid/v1/chat/completions', 'model': 'offline-D03',
             'protocol': 'chat_completions', 'context_tokens': 65536, 'output_tokens': 2048}
    store, job, version, image, source = delivery.__wrapped__(directory, route)
    jid = job['id']
    store.update_job(jid, name='D03 synthetic')
    dispatcher = Dispatcher(store)
    cases = []
    head = version
    # Each edit has its own real immutable commit, independent of its attachments.
    for label, field, metadata in [('candidate-null', 'candidate_ref', None),
                                    ('result-array', 'result_ref', []),
                                    ('candidate-scalar', 'candidate_ref', 7),
                                    ('invalid-commit', 'result_ref', None),
                                    ('invalid-files', 'candidate_ref', None),
                                    ('valid', None, {})]:
        request = f'{jid}:{label}'
        op = request + ':0'
        args = json.dumps({'base_version': head, 'expected_head': head, 'claim': 'complete'})
        result = dispatcher.execute(jid, op, 'edit_document', args)['data']
        assert 'version_id' in result, result
        head = result['version_id']
        aid = request + ':attempt'
        payload = store.blob(jid, 'request_input', {'messages': []}, {'request': request})['ref']
        accepted = store.blob(jid, 'accepted_response', {'calls': [{'id': 'call', 'name': 'edit_document', 'arguments': args}]},
                              {'request': request, 'attempt': aid}, key=f'accepted:{request}')['ref']
        store.put('attempt', aid, jid, {'id': aid, 'request': request, 'status': 'accepted', 'usage': None})
        store.put('request', request, jid, {'id': request, 'job': jid, 'kind': 'normal', 'status': 'accepted',
                   'payload_ref': payload, 'route': job['route'], 'meta': {}, 'attempts': [aid], 'accepted_ref': accepted})
        record = store.get('operation', op)
        # Model an optional retained result beside the independent inline receipt.
        result_ref = store.blob(jid, 'tool_result', result, {'operation': op}, key=f'result:{op}')['ref']
        record = {**record, 'result_ref': result_ref}
        store.put('operation', op, jid, record)
        cases.append({'label': label, 'operation': op, 'request': request, 'version': head,
                      'field': field, 'ref': record[field] if field else record['candidate_ref'], 'raw_meta': metadata})
    inputs = []
    for label, metadata in [('null', None), ('array', []), ('scalar', 'rejected')]:
        request = f'{jid}:input-{label}'
        aid = request + ':attempt'
        ref = store.blob(jid, 'request_input', {'messages': ['Original frozen input']}, {'request': request})['ref']
        store.put('attempt', aid, jid, {'id': aid, 'request': request, 'status': 'failed', 'usage': None})
        store.put('request', request, jid, {'id': request, 'job': jid, 'kind': 'normal', 'status': 'failed',
                   'payload_ref': ref, 'route': job['route'], 'meta': {'capacity': {'fits': True}},
                   'attempts': [aid], 'accepted_ref': None})
        store.put('blob', ref, jid, {**store.get('blob', ref), 'meta': metadata})
        inputs.append({'request': request, 'attempt': aid, 'ref': ref, 'raw_meta': metadata})
    Documents(store).export(jid, version, str(directory / 'existing-delivery.zip'))
    # All document setup/export precedes deliberate damage.
    for case in cases:
        if case['field']:
            ref = case['ref']
            store.put('blob', ref, jid, {**store.get('blob', ref), 'meta': case['raw_meta']})
        if case['label'] == 'invalid-commit':
            record = store.get('operation', case['operation'])
            store.put('operation', case['operation'], jid, {**record, 'result': {**record['result'], 'parent': 'wrong-parent'}})
        if case['label'] == 'invalid-files':
            (store.root / 'versions' / case['version'] / 'document.md').write_bytes(b'Synthetic damaged commit member.')
    return {'job': jid, 'version': version, 'head': head, 'image': image, 'cases': cases, 'inputs': inputs,
            'network': 'Direct synthetic records and local document setup; no Nexus/model invocation.'}


def assert_failed(link, ref, metadata):
    assert link['ref'] == ref and link['status'] == 'unavailable'
    assert link['reason'] == SHAPE_REASON
    assert 'facts' not in link
    assert not any(field in link for field in ('kind', 'meta', 'bytes', 'attempt', 'relation'))
    assert link['raw_descriptor']['meta'] == metadata


def test_failed_attachments_keep_independent_commit_and_request_facts(tmp_path):
    value = seed(tmp_path)
    before = hashes(tmp_path / 'workspace')
    service = Diagnostics(tmp_path / 'workspace')
    try:
        view = service.events(value['job'])['view']
        for case in value['cases']:
            detail = service.detail(value['job'], view, 'operation', case['operation'])
            link = next(item for item in detail['links'] if item['ref'] == case['ref'])
            if case['field']:
                assert_failed(link, case['ref'], case['raw_meta'])
            else:
                assert link['facts']['meta']['operation'] == case['operation']
            assert detail['request_association']['status'] == 'confirmed'
            if case['label'] in ('invalid-commit', 'invalid-files'):
                assert 'version' not in detail and detail['effect'].startswith('unknown:')
                expected = ('Atomic operation/version lineage disagrees.' if case['label'] == 'invalid-commit'
                            else 'Document commit files disagree with their registered version.')
                assert expected in detail['limitations']
            else:
                assert detail['version'] == case['version'] and detail['effect'].startswith('committed')
                saved = service.detail(value['job'], view, 'version', case['version'])
                assert saved['verification'].startswith('version files checked')
        for case in value['inputs']:
            detail = service.detail(value['job'], view, 'request', case['request'])
            assert detail['attempts'][0]['record']['id'] == case['attempt']
            assert detail['publication']['pointer'] is None
            assert detail['frozen_preparation']['meta']['capacity']['fits'] is True
            assert_failed(next(link for link in detail['links'] if link['ref'] == case['ref']), case['ref'], case['raw_meta'])
    finally:
        service.close()
    assert hashes(tmp_path / 'workspace') == before


@pytest.mark.parametrize('metadata', [None, [], 7, 'bad', False])
@pytest.mark.parametrize('field', ['candidate_ref', 'result_ref'])
def test_operation_shapes_and_reason_precedence(tmp_path, metadata, field):
    value = seed(tmp_path)
    case = value['cases'][-1]
    store = Store(tmp_path / 'workspace')
    op = store.get('operation', case['operation'])
    ref = op[field]
    store.put('blob', ref, value['job'], {**store.get('blob', ref), 'meta': metadata})
    service = Diagnostics(store.root)
    try:
        view = service.events(value['job'])['view']
        detail = service.detail(value['job'], view, 'operation', case['operation'])
        assert_failed(next(link for link in detail['links'] if link['ref'] == ref), ref, metadata)
        assert detail['version'] == case['version']
    finally: service.close()


def test_api_local_failures_and_valid_exact_access(tmp_path):
    value = seed(tmp_path)
    app = create_app(tmp_path / 'workspace', 'synthetic-only', transport=httpx.MockTransport(forbidden))
    with TestClient(app, headers={'Authorization': 'Bearer synthetic-only'}) as client:
        prefix = f"/jobs/{value['job']}"
        assert client.get(prefix).status_code == 200
        before = hashes(tmp_path / 'workspace')
        view = client.get(prefix + '/activity').json()['view']
        for kind, cases, field in [('operation', value['cases'], 'operation'), ('request', value['inputs'], 'request')]:
            for case in cases:
                detail = client.get(prefix + '/diagnostics/record', params={'view': view, 'kind': kind, 'key': case[field]}).json()
                assert detail['status'] == 'ok'
                if kind == 'request' or case.get('field'):
                    assert_failed(next(link for link in detail['links'] if link['ref'] == case['ref']), case['ref'], case['raw_meta'])
        ref = value['cases'][-1]['ref']
        exact = client.get(prefix + '/diagnostics/evidence', params={'view': view, 'ref': ref, 'mode': 'raw', 'start': 1, 'end': 6}).json()
        assert exact['status'] == 'ok' and exact['range'] == [1, 6] and exact['complete'] is False
        assert hashes(tmp_path / 'workspace') == before


@pytest.mark.parametrize('index', [0, 1, 2])
def test_frozen_input_shape_is_local(tmp_path, index):
    value = seed(tmp_path)
    case = value['inputs'][index]
    service = Diagnostics(tmp_path / 'workspace')
    try:
        view = service.events(value['job'])['view']
        detail = service.detail(value['job'], view, 'request', case['request'])
        assert_failed(next(link for link in detail['links'] if link['ref'] == case['ref']), case['ref'], case['raw_meta'])
        assert detail['attempts'][0]['record']['id'] == case['attempt']
    finally: service.close()


def test_failed_request_and_related_descriptors_do_not_confirm_relationships(tmp_path):
    value = seed(tmp_path)
    case = value['cases'][-1]
    store = Store(tmp_path / 'workspace')
    request = store.get('request', case['request'])
    accepted = store.get('blob', request['accepted_ref'])
    context_ref = store.blob(value['job'], 'context_proposal', {'original': 'retained'}, {}, key='explicit-context')['ref']
    store.put('request', case['request'], value['job'], {**request, 'meta': {'proposal_ref': context_ref}})
    for metadata in (None, [], 7):
        # Intentional writers precede each separately captured read-only view.
        store.put('blob', accepted['ref'], value['job'], {**accepted, 'meta': metadata})
        store.put('blob', context_ref, value['job'], {**store.get('blob', context_ref), 'meta': metadata})
        before = hashes(store.root)
        service = Diagnostics(store.root)
        try:
            view = service.events(value['job'])['view']
            detail = service.detail(value['job'], view, 'request', case['request'])
            assert detail['attempts'][0]['record']['id'] == request['attempts'][0]
            for ref in (accepted['ref'], context_ref):
                assert_failed(next(link for link in detail['links'] if link['ref'] == ref), ref, metadata)
            assert not detail['operations']
            assert detail['unconfirmed_operations'][0]['reason'] == SHAPE_REASON
            operation = service.detail(value['job'], view, 'operation', case['operation'])
            assert operation['version'] == case['version']
            assert operation['request'] is None and operation['request_association']['reason'] == SHAPE_REASON
        finally: service.close()
        assert hashes(store.root) == before


def test_missing_metadata_and_valid_shape_role_mismatch_have_no_facts(tmp_path):
    value = seed(tmp_path)
    case = value['cases'][-1]
    store = Store(tmp_path / 'workspace')
    original = store.get('blob', case['ref'])
    for metadata, expected in [('absent', SHAPE_REASON), ({'operation': 'another'}, 'Operation ownership mismatch.')]:
        blob = {key: val for key, val in original.items() if key != 'meta'}
        if metadata != 'absent': blob['meta'] = metadata
        store.put('blob', case['ref'], value['job'], blob)
        service = Diagnostics(store.root)
        try:
            view = service.events(value['job'])['view']
            detail = service.detail(value['job'], view, 'operation', case['operation'])
            link = next(link for link in detail['links'] if link['ref'] == case['ref'])
            assert link['status'] == 'unavailable' and link['reason'] == expected and 'facts' not in link
            assert ('meta' in link['raw_descriptor']) == (metadata != 'absent')
            assert detail['version'] == case['version']
        finally: service.close()
