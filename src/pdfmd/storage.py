"""Short SQLite metadata transactions and immutable, content-addressed bytes."""
from __future__ import annotations

from contextlib import closing, contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import time
from threading import local
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
        self._connections = local()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "objects").mkdir(exist_ok=True)
        with closing(self.connect()) as db:
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
    def connection_scope(self):
        """Reuse one thread-confined handle, never a transaction or cached data."""
        if getattr(self._connections, "active", None) is not None:
            yield
            return
        db = self.connect()
        self._connections.active = db
        try:
            yield
        finally:
            del self._connections.active
            db.close()

    @contextmanager
    def _db(self):
        db = getattr(self._connections, "active", None)
        if db is not None:
            yield db
        else:
            db = self.connect()
            try:
                yield db
            finally:
                db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._db() as db:
            if db.in_transaction:
                raise Conflict("Nested write transactions are not supported.")
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @staticmethod
    def get_tx(db: sqlite3.Connection, kind: str, key: str, *, job: str | None = None) -> dict | None:
        row = db.execute("SELECT job,data FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is not None and job is not None and row[0] != job:
            raise ValueError(f"Inconsistent {kind} ownership for this task: {key}")
        return json.loads(row[1]) if row else None

    @staticmethod
    def put_tx(db: sqlite3.Connection, kind: str, key: str, job: str, value: dict) -> None:
        db.execute("""INSERT INTO records VALUES(?,?,?,?,?)
            ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data""",
                   (kind, key, job, encode(value).decode(), time.time()))

    def get(self, kind: str, key: str, *, job: str | None = None) -> dict:
        with self._db() as db:
            row = db.execute("SELECT job,data FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is None or (job is not None and row[0] != job):
            raise ValueError(f"Unknown {kind} reference for this task: {key}")
        return json.loads(row[1])

    def maybe(self, kind: str, key: str) -> dict | None:
        with self._db() as db:
            return self.get_tx(db, kind, key)

    def put(self, kind: str, key: str, job: str, value: dict) -> None:
        with self.transaction() as db:
            self.put_tx(db, kind, key, job, value)

    def records(self, kind: str, job: str | None = None) -> list[dict]:
        with self._db() as db:
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
        if len(data) != record["bytes"] or sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Saved object failed its integrity check.")
        return data

    def json(self, ref: str, job: str) -> Any:
        return json.loads(self.bytes(ref, job))

    @contextmanager
    def read_snapshot(self):
        """Reuse a caller's pinned read; otherwise end this read on every exit."""
        with self._db() as db:
            own_snapshot = not db.in_transaction
            if own_snapshot:
                db.execute("BEGIN")
            try:
                yield db
            finally:
                if own_snapshot:
                    db.rollback()

    def read_stream(self, job: str, request: str, attempt: str) -> dict:
        """Read verified durable evidence, never infer acceptance or send a request.

        The observation can lag registered chunks. Read a consistent catalog
        snapshot, then immutable files; include the suffix without inventing
        observation/protocol facts. Legacy list checkpoints remain readable.
        """
        prefix = f"stream:{attempt}:"
        with self.read_snapshot() as db:
            def owned(kind, key):
                row = db.execute("SELECT job,data FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
                if row is not None and row["job"] != job:
                    raise ValueError("Stream catalog ownership is inconsistent.")
                return json.loads(row["data"]) if row is not None else None
            owner = owned("request", request)
            sending = owned("attempt", attempt)
            receipt = owned("stream_receive", attempt)
            aggregate = owned("blob", f"raw-stream:{attempt}")
            rows = db.execute("SELECT id,job,data FROM records WHERE kind='blob' AND id>=? AND id<?",
                              (prefix, prefix + "\uffff")).fetchall()
        if (owner is None or owner.get("job") != job or attempt not in owner.get("attempts", [])
                or sending is None or sending.get("request") != request):
            raise ValueError("Stream request/attempt ownership is inconsistent.")
        if receipt is not None and (receipt.get("attempt") != attempt or receipt.get("request") != request):
            raise ValueError("Stream checkpoint ownership is inconsistent.")
        if receipt is None:
            checkpoint_count = 0
            cursor = None
        elif "cursor" in receipt:
            cursor = receipt["cursor"]
            if not isinstance(cursor, dict) or cursor.get("format") != "ordered_chunks_v1":
                raise ValueError("Unknown stream checkpoint format.")
            checkpoint_count = cursor.get("chunk_count")
        else:
            cursor = None
            if not isinstance(receipt.get("chunks"), list):
                raise ValueError("Stream checkpoint has no valid prefix.")
            checkpoint_count = len(receipt["chunks"])
        if type(checkpoint_count) is not int or not 0 <= checkpoint_count <= len(rows):
            raise ValueError("Stream checkpoint exceeds the durable chunk sequence.")
        # Reference suffixes, not timestamps or lexicographic order, own order.
        rows = sorted(rows, key=lambda row: int(row["id"][len(prefix):]))
        refs, parts = [], []
        digest = sha256()
        prefix_bytes, prefix_digest = 0, digest.hexdigest()
        for index, row in enumerate(rows):
            record = json.loads(row["data"])
            meta = record.get("meta", {})
            expected = prefix + str(index)
            if (row["id"] != expected or row["job"] != job or record.get("ref") != expected
                    or record.get("job") != job or record.get("kind") != "stream_chunk"
                    or meta.get("request") != request or meta.get("attempt") != attempt
                    or type(meta.get("index")) is not int or meta["index"] != index):
                raise ValueError("Stream chunk identity/order is inconsistent.")
            part = self._stream_bytes(record)
            if not part:
                raise ValueError("A registered stream chunk is empty.")
            refs.append(expected)
            parts.append(part)
            digest.update(part)
            if index < checkpoint_count:
                prefix_bytes += len(part)
                prefix_digest = digest.hexdigest()
        if cursor is not None:
            last = refs[checkpoint_count - 1] if checkpoint_count else None
            if (type(cursor.get("bytes")) is not int or cursor["bytes"] != prefix_bytes
                    or cursor.get("sha256") != prefix_digest or cursor.get("last_chunk_ref") != last):
                raise ValueError("Stream checkpoint does not match its durable prefix.")
        elif receipt is not None and receipt["chunks"] != refs[:checkpoint_count]:
            raise ValueError("Legacy stream checkpoint order is inconsistent.")
        data = b"".join(parts)
        if aggregate is not None:
            meta = aggregate.get("meta", {})
            if (aggregate.get("job") != job or aggregate.get("kind") != "raw_stream"
                    or aggregate.get("ref") != f"raw-stream:{attempt}"
                    or meta.get("request") != request or meta.get("attempt") != attempt
                    or meta.get("chunks") != refs or self._stream_bytes(aggregate) != data):
                raise ValueError("Published raw stream does not match its durable chunks.")
        return {"data": data, "chunks": refs, "chunk_count": len(refs),
                "received_bytes": len(data), "sha256": digest.hexdigest(),
                "checkpoint_count": checkpoint_count, "checkpoint_present": receipt is not None}

    def _stream_bytes(self, record: dict) -> bytes:
        try:
            data = (self.root / "objects" / record["sha256"]).read_bytes()
        except FileNotFoundError as exc:
            raise ValueError("Saved stream evidence is missing.") from exc
        if len(data) != record["bytes"] or sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Saved stream evidence failed its integrity check.")
        return data

    def event(self, job: str, kind: str, data: dict) -> None:
        with self.transaction() as db:
            db.execute("INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)",
                       (job, kind, encode(data).decode(), time.time()))

    def event_once(self, job: str, kind: str, key: str, data: dict) -> None:
        """Record a replayable node's event and deduplication receipt together."""
        identity = f"{job}:{kind}:{key}"
        with self.transaction() as db:
            previous = self.get_tx(db, "event_receipt", identity)
            if previous is not None:
                if previous != data:
                    raise Conflict("A replayed event does not match its original receipt.")
                return
            db.execute("INSERT INTO events(job,type,data,created) VALUES(?,?,?,?)",
                       (job, kind, encode(data).decode(), time.time()))
            self.put_tx(db, "event_receipt", identity, job, data)

    def events(self, job: str, after: int = 0, limit: int = 200) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM events WHERE job=? AND seq>? ORDER BY seq LIMIT ?",
                              (job, after, limit)).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
