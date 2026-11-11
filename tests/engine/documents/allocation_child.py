"""One engine process for the cross-process allocation tests (T3b, AR-10).

Opens an existing task store, pauses at name reservation until the parent
releases it, then saves one enriched create through its own Dispatcher.

  python -B -m tests.engine.documents.allocation_child SPEC_JSON
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from pdfmd import documents
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


def wait_for(path: Path, seconds: float = 120) -> None:
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(f"No release signal: {path.name}")
        time.sleep(0.02)


def main(spec: dict) -> None:
    sync, role = Path(spec["sync"]), spec["role"]
    original = documents.Documents._reserve

    def reserve(self, *args, **kwargs):
        # Reached after the operation's preparation record is loaded or created.
        (sync / f"{role}.ready").write_text("ready")
        wait_for(sync / f"{role}.go")
        result = original(self, *args, **kwargs)
        (sync / f"{role}.reserved").write_text(json.dumps(result[:2], ensure_ascii=False), encoding="utf-8")
        return result
    documents.Documents._reserve = reserve
    d = Dispatcher(Store(spec["root"]))
    result = d.execute(spec["job"], spec["operation"], "edit_document", json.dumps(spec["arguments"], ensure_ascii=False))
    (sync / f"{role}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
