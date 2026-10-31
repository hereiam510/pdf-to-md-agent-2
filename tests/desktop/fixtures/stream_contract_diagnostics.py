"""New isolated synthetic rejected stream, never a real task or live driver."""
from pathlib import Path
import json
import sys
from hashlib import sha256
import httpx
import pymupdf
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store, encode

directory = Path(sys.argv[2])
if sys.argv[1] == 'prepare':
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'synthetic.pdf'
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), 'Synthetic diagnostics source: preserve 25 mg.')
    pdf.save(source)
    pdf.close()
    route = Route(endpoint='https://synthetic.invalid/v1/chat/completions', model='offline-fixture',
                  context_tokens=65536, output_tokens=2048, wait_policy={})
    store = Store(directory / 'workspace')
    job = Evidence(store).create_job(str(source), 'Synthetic stream diagnostics only.', route.model_dump())
    secret = 'SYNTHETIC-UPSTREAM-FINISH-PRIVATE-TO-RAW'
    raw = b'data: ' + encode({'id': 'synthetic-response', 'choices': [{'index': 0,
        'delta': {'role': 'assistant', 'content': 'Retained evidence'}, 'finish_reason': secret}],
        'usage': {'prompt_tokens': True, 'completion_tokens': 2}}) + b'\n\ndata: [DONE]\n\n'
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self): yield raw
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(lambda _: httpx.Response(200, stream=Body())))
    request = service.freeze(job['id'], job['id'] + ':0:0', make_payload(route, 'Synthetic', [], []), 'normal', {})
    try: service.send(job['id'], request['id'])
    except StopRun as exc: assert exc.reason == 'response_rejected'
    else: raise AssertionError('Unsupported finish cannot be accepted')
    store.update_job(job['id'], name='Stream contract synthetic', status='blocked', stop_reason='response_rejected',
                     last_message='Synthetic stream rejected; original evidence retained.')
    info = {'job': job['id'], 'request': request['id'], 'secret': secret, 'sha256': sha256(raw).hexdigest()}
    (directory / 'fixture.json').write_text(json.dumps(info), encoding='utf-8')
else:
    info = json.loads((directory / 'fixture.json').read_text(encoding='utf-8'))
    store = Store(directory / 'workspace')
    job = store.get('job', info['job'])
    request = store.get('request', info['request'])
    assert job['attempts'] == 1 and request['status'] == 'rejected' and request['accepted_ref'] is None
    assert sha256(store.bytes(request['stream_ref'], info['job'])).hexdigest() == info['sha256']
    assert not store.records('operation', info['job']) and not store.records('version', info['job'])
print(json.dumps(info))
