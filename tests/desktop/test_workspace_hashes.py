from contextlib import closing
from hashlib import sha256
import sqlite3

import pytest

from tests.desktop.fixtures.task_diagnostics import hashes as task_diagnostics_hashes
from tests.desktop.fixtures.workspace_hashes import workspace_hashes


@pytest.mark.parametrize("name", ["catalog.sqlite", "graph.sqlite"])
def test_workspace_snapshot_ignores_empty_wal_lifecycle_and_hashes_committed_wal(tmp_path, name):
    database = tmp_path / name
    wal = tmp_path / f"{name}-wal"
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        conn.execute("CREATE TABLE durable (value TEXT)")
        conn.commit()

    baseline = workspace_hashes(tmp_path)
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("SELECT * FROM durable").fetchall() == []
        assert wal.read_bytes() == b""
        assert workspace_hashes(tmp_path) == baseline
        conn.execute("INSERT INTO durable VALUES ('kept')")
        conn.commit()
        data = wal.read_bytes()
        assert data
        assert workspace_hashes(tmp_path) == {**baseline, wal.name: sha256(data).hexdigest()}

    assert not wal.exists()
    checkpointed = workspace_hashes(tmp_path)
    assert set(checkpointed) == set(baseline) == {name}
    assert checkpointed[name] != baseline[name]


def test_workspace_snapshot_preserves_ordinary_files_even_if_empty(tmp_path):
    version = tmp_path / "versions" / "v1"
    version.mkdir(parents=True)
    output = version / "document.md"
    output.write_bytes(b"")
    unrelated_wal = version / "catalog.sqlite-wal"
    unrelated_wal.write_bytes(b"")
    baseline = workspace_hashes(tmp_path)
    assert baseline == {f"versions/v1/{path.name}": sha256(b"").hexdigest() for path in (output, unrelated_wal)}

    output.write_bytes(b"a new byte")
    assert workspace_hashes(tmp_path)["versions/v1/document.md"] != baseline["versions/v1/document.md"]
    output.unlink()
    assert "versions/v1/document.md" not in workspace_hashes(tmp_path)


def test_task_diagnostics_snapshot_includes_source_and_export_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "catalog.sqlite").write_bytes(b"catalog")
    (workspace / "catalog.sqlite-wal").touch()
    (tmp_path / "source.pdf").write_bytes(b"source")
    export = tmp_path / "existing-delivery.zip"
    export.write_bytes(b"export")
    before = task_diagnostics_hashes(tmp_path)
    assert before == {
        "workspace/catalog.sqlite": sha256(b"catalog").hexdigest(),
        "source.pdf": sha256(b"source").hexdigest(),
        "existing-delivery.zip": sha256(b"export").hexdigest(),
    }
    export.write_bytes(b"different export")
    assert task_diagnostics_hashes(tmp_path)[export.name] != before[export.name]
