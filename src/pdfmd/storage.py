"""Short SQLite metadata transactions and immutable, content-addressed bytes."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator
from uuid import uuid4


def encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def uid() -> str:
    return uuid4().hex


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "objects").mkdir(exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, job TEXT NOT NULL,
                    data TEXT NOT NULL, created REAL NOT NULL,
                    PRIMARY KEY (kind,id)
                );
                CREATE INDEX IF NOT EXISTS record_job ON records(job,kind,created);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT NOT NULL,
                    type TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL
                );
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.root / "catalog.sqlite", timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get_tx(db: sqlite3.Connection, kind: str, key: str) -> dict | None:
        row = db.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def put_tx(db: sqlite3.Connection, kind: str, key: str, job: str, value: dict) -> None:
        db.execute("""INSERT INTO records VALUES(?,?,?,?,?)
            ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data""",
                   (kind, key, job, encode(value).decode(), time.time()))

    def get(self, kind: str, key: str, *, job: str | None = None) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT job,data FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is None or (job is not None and row[0] != job):
            raise ValueError(f"Unknown {kind} reference for this task: {key}")
        return json.loads(row[1])

    def maybe(self, kind: str, key: str) -> dict | None:
        with self.connect() as db:
            return self.get_tx(db, kind, key)

    def put(self, kind: str, key: str, job: str, value: dict) -> None:
        with self.transaction() as db:
            self.put_tx(db, kind, key, job, value)

    def records(self, kind: str, job: str | None = None) -> list[dict]:
        with self.connect() as db:
            if job is None:
                rows = db.execute("SELECT data FROM records WHERE kind=? ORDER BY created", (kind,)).fetchall()
            else:
                rows = db.execute("SELECT data FROM records WHERE kind=? AND job=? ORDER BY created", (kind, job)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def update_job(self, job: str, **changes: Any) -> dict:
        with self.transaction() as db:
            data = self.get_tx(db, "job", job)
            if data is None:
                raise ValueError("Task does not exist.")
            data.update(changes)
            data["updated"] = time.time()
            self.put_tx(db, "job", job, job, data)
        return data

    def blob(self, job: str, kind: str, data: bytes | Any, meta: dict | None = None,
             *, key: str | None = None) -> dict:
        raw = data if isinstance(data, bytes) else encode(data)
        digest = sha256(raw).hexdigest()
        target = self.root / "objects" / digest
        if not target.exists():
            tmp = target.with_name(f".{digest}.{uid()}.tmp")
            with tmp.open("xb") as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            # All writers to this content address have identical bytes.
            os.replace(tmp, target)
        record = {"ref": key or uid(), "job": job, "kind": kind, "sha256": digest,
                  "bytes": len(raw), "meta": meta or {}}
        with self.transaction() as db:
            previous = self.get_tx(db, "blob", record["ref"])
            if previous:
                if previous != record:
                    raise Conflict("An immutable reference already contains different data.")
                return previous
            self.put_tx(db, "blob", record["ref"], job, record)
        return record

    def bytes(self, ref: str, job: str) -> bytes:
        record = self.get("blob", ref, job=job)
        data = (self.root / "objects" / record["sha256"]).read_bytes()
        if sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Saved object failed its integrity check.")
        return data

    def json(self, ref: str, job: str) -> Any:
        return json.loads(self.bytes(ref, job))

    def event(self, job: str, kind: str, data: dict) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)",
                       (job, kind, encode(data).decode(), time.time()))

    def events(self, job: str, after: int = 0, limit: int = 200) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM events WHERE job=? AND seq>? ORDER BY seq LIMIT ?",
                              (job, after, limit)).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
