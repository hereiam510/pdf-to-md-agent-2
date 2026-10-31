"""Test-only scheduling hook. Never included in the application Python path."""
import os
from pathlib import Path
import time


if os.environ.get('PDFMD_TEST_BOUNDARY'):
    from pdfmd.tools import Dispatcher

    original_execute = Dispatcher.execute

    def execute_at_boundary(self, job, operation, name, raw_arguments):
        result = original_execute(self, job, operation, name, raw_arguments)
        marker = Path(os.environ['PDFMD_TEST_BOUNDARY'])
        if name == 'context_update' and 'pause-after-settlement-fixture' in raw_arguments and not marker.exists():
            marker.write_text('The real tool result is settled; waiting for UI Stop.', encoding='utf-8')
            deadline = time.monotonic() + 45
            while not self.store.get('job', job)['cancel_requested']:
                if time.monotonic() > deadline:
                    raise RuntimeError('The desktop fixture did not press Stop at the settled boundary.')
                time.sleep(0.05)
        return result

    Dispatcher.execute = execute_at_boundary
