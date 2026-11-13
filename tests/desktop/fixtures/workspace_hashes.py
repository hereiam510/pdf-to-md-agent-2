"""Durable workspace snapshots for desktop diagnostic fixtures."""
from hashlib import sha256
from pathlib import Path


SQLITE_WALS = {"catalog.sqlite-wal", "graph.sqlite-wal"}
SQLITE_WAL_INDEXES = {"catalog.sqlite-shm", "graph.sqlite-shm"}


def workspace_hashes(directory: Path) -> dict[str, str]:
    """Hash durable workspace files, including any WAL with bytes."""
    hashes = {}
    for path in directory.rglob("*"):
        name = path.relative_to(directory).as_posix()
        # SQLite regenerates these indexes from the WAL as connections come and go.
        if name in SQLITE_WAL_INDEXES or not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            if name in SQLITE_WALS:
                continue  # SQLite closed the sidecar after enumeration.
            raise
        if name not in SQLITE_WALS or data:
            hashes[name] = sha256(data).hexdigest()
    return hashes
