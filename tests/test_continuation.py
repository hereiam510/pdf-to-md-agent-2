"""Local failure injection. No provider calls and no claim about model judgment."""
import json
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.server import Engine
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_response_repairs import native, seed_compaction, handoff
from test_runtime import tool


@pytest.fixture
def delivery(tmp_path, route):
    source = tmp_path / 'source.pdf'
    pdf = pymupdf.open()
    text = ['First page. Preserve 25 mg.', 'Second page. Do not omit this paragraph.']
    for value in text:
        pdf.new_page().insert_text((72, 72), value)
    pdf.save(source)
    pdf.close()
    store = Store(tmp_path / 'workspace')
    job = Evidence(store).create_job(str(source), 'Convert both complete pages.',
                                     {**route, 'vision': True, 'image_tokens': 1024})
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job['id'], 2)
    args = {'base_version': None, 'expected_head': None, 'replace_blocks': [
        {'id': f'p{i+1}', 'pages': [i+1], 'markdown': value} for i, value in enumerate(text)] + [
        {'id': 'figure', 'pages': [2], 'markdown': f"![Source]({image['asset_path']})"}],
        'page_updates': {str(i): {'printed': 'none', 'disposition': 'included'} for i in [1, 2]}, 'claim': 'complete'}
    version = dispatcher.execute(job['id'], 'seed', 'edit_document', json.dumps(args))['data']['version_id']
    return store, job, version, image, source


def use_protocol(store, job, protocol):
    store.update_job(job['id'], route={**job['route'], 'protocol': protocol,
        'endpoint': 'http://127.0.0.1:8317/v1/' + ('responses' if protocol == 'responses' else 'chat/completions')})


def continue_job(store, job, transport, amendment=''):
    engine = Engine(store.root, transport=transport)
    try:
        engine.start(job['id'], 'fixture-only', amendment=amendment)
        engine.futures[job['id']].result(timeout=30)
    finally:
        engine.close()


def check_delivery(store, job, version, image, source, destination):
    reopened = Documents(Store(store.root))
    content = reopened.version(job['id'], version)
    assert store.bytes(content['source_ref'], job['id']) == source.read_bytes()
    assert reopened.export(job['id'], version, str(destination))['verified']
    with pymupdf.open(source) as pdf, zipfile.ZipFile(destination) as archive:
        markdown = archive.read('document.md').decode('utf-8')
        assert all(line in markdown for page in pdf for line in page.get_text().splitlines())
        assert archive.read(image['asset_path']) == store.bytes(image['ref'], job['id'])
        assert json.loads(archive.read('document.json')) == content
        for name in archive.namelist():
            assert archive.read(name) == (reopened.root / version / name).read_bytes()


@pytest.mark.parametrize('protocol', ['chat_completions', 'responses'])
@pytest.mark.parametrize('new_instruction', [False, True])
def test_cancelled_batch_respects_new_instructions_and_preserves_delivery(delivery, tmp_path, protocol, new_instruction):
    store, job, version, image, source = delivery
    use_protocol(store, job, protocol)
    seen = []
    destructive = {'base_version': version, 'expected_head': version, 'claim': 'partial',
                   'operations': [{'kind': 'delete', 'id': 'p2'}, {'kind': 'delete', 'id': 'figure'}]}

    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            value = native(protocol, tool('context_update', {'pin': [{'ref': image['ref'], 'view': 'image'}], 'notes': 'Keep original pixels.'}, 'policy'),
                           tool('edit_document', destructive, 'delete'))
            if protocol == 'responses':
                value['output'].insert(0, {'type': 'reasoning', 'encrypted_content': 'retained-reasoning', 'summary': []})
        else:
            messages = payload.get('messages', payload.get('input'))
            outputs = [m for m in messages if m.get('role') == 'tool' or m.get('type') == 'function_call_output']
            assert [m.get('tool_call_id', m.get('call_id')) for m in outputs] == ['policy', 'delete']
            result = json.loads(outputs[1].get('content', outputs[1].get('output')))
            if new_instruction:
                assert result['data']['execution'] == 'not_started' and not result['ok']
                assert 'Preserve both pages and image' in json.dumps(payload)
                assert store.get('job', job['id'])['head'] == version
            else:
                assert result['ok']
            if protocol == 'responses':
                assert 'retained-reasoning' in json.dumps(payload)
            value = native(protocol, tool('report', {'state': 'waiting', 'message': 'Ready for your decision.'}, 'report'))
        return httpx.Response(200, json=value)

    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture-only', transport))
    execute = runtime.dispatcher.execute
    def cancel(*args):
        result = execute(*args)
        store.update_job(job['id'], cancel_requested=True)
        return result
    runtime.dispatcher.execute = cancel
    runtime.run(job['id'])
    collecting = runtime.graph.get_state({'configurable': {'thread_id': job['id']}}).values
    assert collecting['pinned'] == [] and collecting['notes'] == ''
    completed_call = next(op for op in store.records('operation', job['id']) if op['tool'] == 'context_update')
    raw_receipt = store.bytes(completed_call['result_ref'], job['id'])
    assert not store.json(completed_call['result_ref'], job['id'])['admission']['applied']
    runtime.close()
    assert store.get('job', job['id'])['stop_reason'] == 'cancelled'
    continue_job(store, job, transport, 'Preserve both pages and image. Ask before editing.' if new_instruction else '')
    assert len(seen) == 2
    current = store.get('job', job['id'])
    assert current['status'] == 'waiting' and current['attempts'] == 2
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture-only', transport))
    state = runtime.graph.get_state({'configurable': {'thread_id': job['id']}}).values
    runtime.close()
    assert store.bytes(completed_call['result_ref'], job['id']) == raw_receipt
    disposition = store.json(state['context_feedback'], job['id'])['summary']
    if new_instruction:
        assert state['pinned'] == [] and state['notes'] == ''
        assert disposition['status'] == 'superseded' and disposition['reason'] == 'new_instructions'
        check_delivery(store, job, current['head'], image, source, tmp_path / 'preserved.zip')
        pending = store.records('request', job['id'])[0]
        assert store.json(f"candidate:{pending['id']}:1", job['id']) == destructive
    else:
        assert image['ref'] in state['pinned'] and state['notes'] == 'Keep original pixels.'
        assert disposition['status'] == 'applied'
        assert current['head'] != version
        assert [b['id'] for b in Documents(store).version(job['id'], current['head'])['content']['blocks']] == ['p1']


@pytest.mark.parametrize('gap', ['document', 'result_pointer', 'policy_settlement', 'report'])
def test_completed_effects_reconcile_but_old_report_does_not_end_new_instruction(delivery, tmp_path, gap, monkeypatch):
    store, job, version, image, source = delivery
    seen = []
    first = {'document': tool('edit_document', {'base_version': version, 'expected_head': version, 'title': 'Preserved title'}),
             'result_pointer': tool('context_update', {'pin': [{'ref': image['ref'], 'view': 'image'}], 'notes': 'Restored policy.'}),
             'policy_settlement': tool('context_update', {'pin': [{'ref': image['ref'], 'view': 'image'}], 'notes': 'Restored policy.'}),
             'report': tool('report', {'state': 'complete', 'version_id': version, 'message': 'Old completion.'})}[gap]
    def reply(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=native('chat_completions', first if len(seen) == 1 else
            tool('report', {'state': 'waiting', 'message': 'New instructions received.'})))
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture-only', transport))
    if gap == 'result_pointer':
        original = store.put
        def fail(kind, key, owner, value):
            if kind == 'operation' and value['status'] == 'done' and value['tool'] == 'context_update':
                raise RuntimeError('receipt before pointer')
            return original(kind, key, owner, value)
        monkeypatch.setattr(store, 'put', fail)
    elif gap == 'policy_settlement':
        original = runtime.context_updates.finish
        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('policy settlement before graph checkpoint')
        runtime.context_updates.finish = fail
    else:
        original = runtime.dispatcher.execute
        def fail(*args):
            original(*args)
            raise RuntimeError('effect before checkpoint')
        runtime.dispatcher.execute = fail
    with pytest.raises(RuntimeError):
        runtime.run(job['id'])
    runtime.close()
    monkeypatch.undo()
    head = store.get('job', job['id'])['head']
    versions = len(store.records('version', job['id']))
    continue_job(store, job, transport, 'Preserve the completed work; ask before any further change.')
    assert len(seen) == 2 and 'Preserve the completed work' in json.dumps(seen[-1])
    current = store.get('job', job['id'])
    assert current['status'] == 'waiting' and current['last_message'] == 'New instructions received.'
    assert current['head'] == head and len(store.records('version', job['id'])) == versions
    resumed = Runtime(store, Nexus(store, lambda _: 'fixture-only', transport))
    state = resumed.graph.get_state({'configurable': {'thread_id': job['id']}}).values
    resumed.close()
    if gap in {'result_pointer', 'policy_settlement'}:
        outcome = store.json(state['context_feedback'], job['id'])['summary']
        if gap == 'policy_settlement':
            assert image['ref'] in state['pinned'] and state['notes'] == 'Restored policy.'
            assert outcome['status'] == 'applied'
        else:
            assert state['pinned'] == [] and state['notes'] == '' and outcome['status'] == 'superseded'
    check_delivery(store, job, head, image, source, tmp_path / 'delivery.zip')


@pytest.mark.parametrize('name', ['run_script', 'ocr_page'])
def test_started_local_process_is_not_replayed_or_mislabeled_skipped(delivery, name):
    store, job, version, image, source = delivery
    seen = []
    value = native('chat_completions', tool(name, {}))
    transport = httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(200, json=value))
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture-only', transport), scripts=True)
    def crash(*args):
        raise KeyboardInterrupt('simulated process death after operation started')
    runtime.dispatcher.dispatch = crash
    with pytest.raises(KeyboardInterrupt):
        runtime.run(job['id'])
    runtime.close()
    continue_job(store, job, transport, 'Preserve existing work and use the new instructions.')
    assert len(seen) == 1
    assert store.get('job', job['id'])['stop_reason'] == 'local_outcome_unknown'
    operation = next(op for op in store.records('operation', job['id']) if op['tool'] == name)
    assert operation['status'] == 'started' and 'result_ref' not in operation
    assert store.get('job', job['id'])['head'] == version


@pytest.mark.parametrize('protocol', ['chat_completions', 'responses'])
@pytest.mark.parametrize('failure', ['http', 'truncated'])
def test_continue_after_failed_response_uses_new_input_and_delivers(delivery, tmp_path, protocol, failure):
    store, job, version, image, source = delivery
    use_protocol(store, job, protocol)
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            if failure == 'http':
                return httpx.Response(502, text='fixture-secret must not enter records')
            value = native(protocol, tool('edit_document', {'base_version': version, 'expected_head': version,
                'operations': [{'kind': 'delete', 'id': 'p2'}]}))
            if protocol == 'responses':
                value.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
            else:
                value['choices'][0]['finish_reason'] = 'length'
        elif len(seen) == 2:
            assert 'Keep the complete scope and repair locally.' in json.dumps(payload)
            assert 'Request continuation record' in json.dumps(payload)
            assert not any(m.get('role') == 'tool' or m.get('type') == 'function_call_output'
                           for m in payload.get('messages', payload.get('input')))
            value = native(protocol, tool('edit_document', {'base_version': version, 'expected_head': version,
                                                           'title': 'Recovered complete document'}))
        else:
            value = native(protocol, tool('report', {'state': 'complete', 'message': 'Complete saved result.',
                                                     'version_id': store.get('job', job['id'])['head']}))
        return httpx.Response(200, json=value)
    transport = httpx.MockTransport(reply)
    for _ in range(2):  # A plain crash re-entry cannot grant a new failed-request continuation.
        runtime = Runtime(store, Nexus(store, lambda _: 'fixture', transport))
        runtime.run(job['id'])
        runtime.close()
    assert len(seen) == 1 and store.get('job', job['id'])['head'] == version
    old_request = store.records('request', job['id'])[0]
    original_payload = store.bytes(old_request['payload_ref'], job['id'])
    assert not old_request['accepted_ref']
    continue_job(store, job, transport, 'Keep the complete scope and repair locally.')
    current = store.get('job', job['id'])
    assert current['status'] == 'completed' and current['attempts'] == len(seen) == 3
    assert store.bytes(old_request['payload_ref'], job['id']) == original_payload
    assert store.get('request', old_request['id'])['status'] == ('http_error' if failure == 'http' else 'rejected')
    attempt = store.get('attempt', old_request['attempts'][0])
    assert attempt['usage'] is None and attempt['remote_cancelled'] is None
    assert store.get('job', job['id'])['limits'] == job['limits']
    assert not any(op['id'].startswith(old_request['id'] + ':') for op in store.records('operation', job['id']))
    assert 'fixture-secret' not in json.dumps(store.records('request', job['id']))
    check_delivery(store, job, current['head'], image, source, tmp_path / 'recovered.zip')


def test_repeated_failed_continue_preserves_original_request_budget(delivery):
    store, job, version, _, _ = delivery
    store.update_job(job['id'], limits={**job['limits'], 'max_requests': 2})
    seen = []
    transport = httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(502))
    for _ in range(4):
        continue_job(store, job, transport)
    assert len(seen) == store.get('job', job['id'])['attempts'] == 2
    assert store.get('job', job['id'])['stop_reason'] == 'budget_exhausted'
    assert len(store.records('request', job['id'])) == 3  # The third stays prepared, with no attempt.
    assert store.get('job', job['id'])['head'] == version


@pytest.mark.parametrize('replay', [False, True])
def test_unknown_outcome_cannot_acquire_a_new_id_or_reset_replay_limits(delivery, replay):
    store, job, version, _, _ = delivery
    store.update_job(job['id'], limits={**job['limits'], 'replay_unknown': replay, 'max_attempts_per_request': 2})
    seen = []
    def fail(request):
        seen.append(request.content)
        raise httpx.ReadError('injected missing response')
    transport = httpx.MockTransport(fail)
    for index in range(4):
        continue_job(store, job, transport, f'Preserve both pages. Instruction {index}.')
    assert len(seen) == (2 if replay else 1)
    assert len(set(seen)) == 1
    assert len(store.records('request', job['id'])) == 1
    assert not any(b['kind'] == 'request_continuation' for b in store.records('blob', job['id']))
    assert store.get('job', job['id'])['stop_reason'] == 'unknown_outcome'
    assert store.get('job', job['id'])['head'] == version


@pytest.mark.parametrize('gap', ['before_checkpoint', 'after_checkpoint'])
def test_continue_receipt_survives_checkpoint_gap_without_new_authorization(delivery, gap):
    store, job, version, _, _ = delivery
    seen = []
    def reply(request):
        seen.append(json.loads(request.content))
        return httpx.Response(502) if len(seen) == 1 else httpx.Response(200, json=native('chat_completions',
            tool('report', {'state': 'complete', 'message': 'Preserved.', 'version_id': version})))
    service = Nexus(store, lambda _: 'fixture', httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    runtime.run(job['id'])
    if gap == 'before_checkpoint':
        original = runtime.resume_pending
        def fault(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('continuation receipt before checkpoint')
        runtime.resume_pending = fault
    else:
        original = runtime.graph.update_state
        def fault(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('continuation checkpoint before invoke')
        runtime.graph.update_state = fault
    with pytest.raises(RuntimeError):
        runtime.run(job['id'], continue_failed=True)
    runtime.close()
    resumed = Runtime(store, service)
    resumed.run(job['id'])  # Persisted Continue intent survives without a second click.
    resumed.close()
    assert len(seen) == 2 and store.get('job', job['id'])['status'] == 'completed'
    assert len([b for b in store.records('blob', job['id']) if b['kind'] == 'request_continuation']) == 1
    assert len([e for e in store.events(job['id']) if e['type'] == 'request_continued']) == 1


def test_unsent_frozen_request_is_replaced_after_amendment(delivery):
    store, job, version, _, _ = delivery
    seen = []
    transport = httpx.MockTransport(lambda req: seen.append(json.loads(req.content)) or httpx.Response(200,
        json=native('chat_completions', tool('report', {'state': 'waiting', 'message': 'New instructions received.'}))))
    service = Nexus(store, lambda _: 'fixture', transport)
    runtime = Runtime(store, service)
    original = service.freeze
    def fault(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('prepared input before graph checkpoint')
    service.freeze = fault
    with pytest.raises(RuntimeError):
        runtime.run(job['id'])
    runtime.close()
    frozen = store.records('request', job['id'])[0]
    assert not frozen['attempts'] and not seen
    continue_job(store, job, transport, 'Do not edit anything. Ask for the new scope.')
    assert len(seen) == 1 and 'Ask for the new scope' in json.dumps(seen[0])
    assert not store.get('request', frozen['id'])['attempts']
    assert len(store.records('request', job['id'])) == 2
    assert store.get('job', job['id'])['head'] == version


@pytest.mark.parametrize('gap', ['skip_marker', 'result_pointer', 'checkpoint'])
def test_skipped_tool_receipt_is_recoverable_at_each_local_gap(delivery, gap, monkeypatch):
    store, job, version, _, _ = delivery
    seen = []
    def reply(request):
        seen.append(json.loads(request.content))
        if len(seen) == 1:
            value = native('chat_completions', tool('inspect_pdf', {}, 'read'), tool('edit_document',
                {'base_version': version, 'expected_head': version, 'replace_blocks': [], 'claim': 'partial'}, 'erase'))
        else:
            value = native('chat_completions', tool('report', {'state': 'waiting', 'message': 'Preserved.'}))
        return httpx.Response(200, json=value)
    service = Nexus(store, lambda _: 'fixture', httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    execute = runtime.dispatcher.execute
    def stop(*args):
        result = execute(*args)
        store.update_job(job['id'], cancel_requested=True)
        return result
    runtime.dispatcher.execute = stop
    runtime.run(job['id'])
    runtime.close()
    store.update_job(job['id'], cancel_requested=False, amendments=['Preserve the saved result.'])
    runtime = Runtime(store, service)
    original = store.put
    if gap == 'checkpoint':
        skip = runtime.dispatcher.skip
        def fail(*args):
            skip(*args)
            raise RuntimeError('after skipped receipt')
        runtime.dispatcher.skip = fail
    else:
        def fail(kind, key, owner, value):
            if kind == 'operation' and value['tool'] == 'edit_document' and key != 'seed':
                if gap == 'skip_marker' and value['status'] == 'skipping':
                    original(kind, key, owner, value)
                    raise RuntimeError('after skip marker')
                if gap == 'result_pointer' and value['status'] == 'done':
                    raise RuntimeError('after skipped result')
            return original(kind, key, owner, value)
        monkeypatch.setattr(store, 'put', fail)
    with pytest.raises(RuntimeError):
        runtime.run(job['id'])
    runtime.close()
    monkeypatch.undo()
    resumed = Runtime(store, service)
    resumed.run(job['id'])
    resumed.close()
    assert len(seen) == 2 and store.get('job', job['id'])['head'] == version
    assert len(store.records('version', job['id'])) == 1
    operation = next(op for op in store.records('operation', job['id']) if op['tool'] == 'edit_document' and op['id'] != 'seed')
    assert operation['status'] == 'done' and not operation['ok']
    assert store.json(operation['result_ref'], job['id'])['execution'] == 'not_started'


@pytest.mark.parametrize('failure', ['http', 'truncated'])
def test_continue_after_failed_compaction_preserves_history_and_delivery(delivery, tmp_path, failure):
    store, job, version, image, source = delivery
    seen, compactions = [], []
    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if payload.get('tools'):
            value = native('chat_completions', tool('report', {'state': 'complete', 'version_id': version, 'message': 'Preserved.'}))
        else:
            compactions.append(payload)
            if len(compactions) == 1 and failure == 'http':
                return httpx.Response(502)
            value = native('chat_completions', text=json.dumps(handoff(job, current_state='Complete version saved: ' + version)))
            if len(compactions) == 1:
                value['choices'][0]['finish_reason'] = 'length'
            else:
                assert 'request_continuation' in payload['messages'][1]['content']
                assert 'Preserve the complete saved result' in payload['messages'][1]['content']
        return httpx.Response(200, json=value)
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture', transport))
    original = seed_compaction(runtime, store, job)
    runtime.run(job['id'])
    state = runtime.graph.get_state({'configurable': {'thread_id': job['id']}}).values
    assert state['history'] == ['large-history'] and state['handoff'] is None
    runtime.close()
    assert len(seen) == 1
    continue_job(store, job, transport, 'Preserve the complete saved result while compacting.')
    assert len(seen) == 3 and len(compactions) == 2
    assert store.get('job', job['id'])['status'] == 'completed'
    assert store.json(original['ref'], job['id'])['value'] == 'Retained evidence. ' * 10000
    check_delivery(store, job, version, image, source, tmp_path / 'after-compaction.zip')


def test_accepted_bytes_win_over_continue_even_before_request_pointer_commit(delivery, monkeypatch):
    store, job, version, _, _ = delivery
    seen = []
    def reply(request):
        seen.append(json.loads(request.content))
        value = (tool('edit_document', {'base_version': version, 'expected_head': version,
                  'replace_blocks': [], 'claim': 'partial'}, 'obsolete') if len(seen) == 1 else
                 tool('report', {'state': 'waiting', 'message': 'New instructions received.'}))
        return httpx.Response(200, json=native('chat_completions', value))
    transport = httpx.MockTransport(reply)
    original = store.put
    def fail(kind, key, owner, value):
        if kind == 'request' and value['status'] == 'accepted':
            raise RuntimeError('accepted bytes before request pointer')
        return original(kind, key, owner, value)
    monkeypatch.setattr(store, 'put', fail)
    runtime = Runtime(store, Nexus(store, lambda _: 'fixture', transport))
    with pytest.raises(RuntimeError):
        runtime.run(job['id'])
    runtime.close()
    monkeypatch.undo()
    continue_job(store, job, transport, 'Preserve all saved blocks and ask before changing them.')
    assert len(seen) == 2 and store.get('job', job['id'])['head'] == version
    assert not any(b['kind'] == 'request_continuation' for b in store.records('blob', job['id']))
    output = next(m for m in seen[-1]['messages'] if m.get('tool_call_id') == 'obsolete')
    assert json.loads(output['content'])['data']['execution'] == 'not_started'
    accepted = store.records('request', job['id'])[0]
    assert accepted['status'] == 'accepted' and len(accepted['attempts']) == 1
