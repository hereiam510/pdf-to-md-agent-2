"""D03 setup/damage is explicit; all other actions are file-only inspection."""
from hashlib import sha256
import json
from pathlib import Path
import sys

from tests.engine.diagnostics.test_diagnostic_failed_results import seed
from tests.desktop.fixtures import task_diagnostics as existing
from pdfmd.diagnostics import Diagnostics


def facts(directory, value):
    service = Diagnostics(directory / 'workspace')
    try:
        with service.read(value['job']) as (view, _):
            return {f"{row['kind']}/{row['id']}": {'job': row['job'], 'sha256': sha256(row['data'].encode()).hexdigest()}
                    for row in view.connection.execute('SELECT kind,id,job,data FROM records ORDER BY kind,id')}
    finally: service.close()


if __name__ == '__main__':
    action, path = sys.argv[1:3]
    directory = Path(path)
    if action == 'prepare':
        directory.mkdir(parents=True, exist_ok=False)
        value = seed(directory)
        # Export verifier uses these two equivalent initial delivery identities.
        value['native_ref'] = value['cases'][-1]['ref']
        (directory / 'fixture.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
        result = value
    elif action == 'hash': result = existing.hashes(directory)
    elif action == 'facts': result = facts(directory, json.loads((directory / 'fixture.json').read_text()))
    elif action == 'verify': result = existing.verify(directory)
    else: raise ValueError(action)
    print(json.dumps(result))
