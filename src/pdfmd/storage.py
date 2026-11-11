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


CHUNK = 1 << 20  # streaming unit: engine memory does not grow with object size


def file_digest(path: Path) -> tuple[str, int]:
    """SHA-256 and size of a file, read in chunks."""
    digest, size = sha256(), 0
    with Path(path).open("rb") as source:
        while block := source.read(CHUNK):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


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
        if not self._object_intact(target, digest, len(raw)):
            self._restore(target, raw, digest)
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

    def _restore(self, target: Path, raw: bytes, digest: str) -> None:
        """Write a missing/corrupt content-addressed object from verified identical bytes.

        All writers to one address hold identical bytes. The stage is removed on
        every failure (write, flush, sync, verification or replace). If replace
        fails but a concurrent writer already left the verified bytes in place,
        the repair has succeeded; otherwise the original failure is reported.
        """
        self._stage(target, digest, len(raw), lambda out: out.write(raw))

    def _stage(self, target: Path, digest: str, size: int, write) -> None:
        tmp = target.with_name(f".{digest}.{uid()}.tmp")
        try:
            with tmp.open("xb") as out:
                write(out)
                out.flush()
                os.fsync(out.fileno())
            if not self._object_intact(tmp, digest, size):
                raise ValueError("Staged object failed its integrity check; the existing object was left unchanged.")
            try:
                os.replace(tmp, target)
            except OSError as exc:
                if self._object_intact(target, digest, size):
                    return
                raise ValueError("Could not restore the content-addressed object; close readers and retry.") from exc
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _object_intact(path: Path, digest: str, size: int) -> bool:
        """True when ``path`` holds exactly the content for ``digest`` (missing or unreadable is False)."""
        try:
            if path.stat().st_size != size:
                return False
            return file_digest(path) == (digest, size)
        except OSError:
            return False

    def blob_from_file(self, job: str, kind: str, path: Path, meta: dict | None = None,
                       *, key: str | None = None, expected_sha256: str | None = None) -> dict:
        """Register a file in chunks, checking any SHA-256 established by the caller."""
        digest, size = file_digest(path)
        if expected_sha256 is not None and digest != expected_sha256:
            raise ValueError("The source file does not match the expected SHA-256.")
        target = self.root / "objects" / digest

        def copy(out):
            with Path(path).open("rb") as source:
                while block := source.read(CHUNK):
                    out.write(block)
        if not self._object_intact(target, digest, size):
            self._stage(target, digest, size, copy)
        if file_digest(path) != (digest, size):
            raise ValueError("The source file changed while it was registered.")
        record = {"ref": key or uid(), "job": job, "kind": kind, "sha256": digest, "bytes": size, "meta": meta or {}}
        with self.transaction() as db:
            previous = self.get_tx(db, "blob", record["ref"])
            if previous:
                if previous != record:
                    raise Conflict("An immutable reference already contains different data.")
                return previous
            self.put_tx(db, "blob", record["ref"], job, record)
        return record

    def verify_object(self, ref: str, job: str) -> tuple[Path, dict]:
        """Path of a task-owned object after a streamed integrity check."""
        record = self.get("blob", ref, job=job)
        path = self.root / "objects" / record["sha256"]
        if not self._object_intact(path, record["sha256"], record["bytes"]):
            raise ValueError("Saved object failed its integrity check.")
        return path, record

    def head(self, ref: str, job: str, size: int = 16) -> bytes:
        record = self.get("blob", ref, job=job)
        with (self.root / "objects" / record["sha256"]).open("rb") as source:
            return source.read(size)

    def copy_object(self, ref: str, job: str, target: Path) -> dict:
        """Copy an object to a new file in chunks; the copy must hash to the recorded identity."""
        record = self.get("blob", ref, job=job)
        digest, size = sha256(), 0
        target = Path(target)
        try:
            with (self.root / "objects" / record["sha256"]).open("rb") as source, target.open("xb") as out:
                while block := source.read(CHUNK):
                    digest.update(block)
                    size += len(block)
                    out.write(block)
                out.flush()
                os.fsync(out.fileno())
        except OSError:
            target.unlink(missing_ok=True)
            raise
        if digest.hexdigest() != record["sha256"] or size != record["bytes"]:
            target.unlink(missing_ok=True)
            raise ValueError("Saved object failed its integrity check.")
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

    def event_summary(self, job: str) -> dict:
        """Small poll indicator, not a change cursor or a task snapshot."""
        with self._db() as db:
            count, latest = db.execute("SELECT count(*),max(seq) FROM events WHERE job=?", (job,)).fetchone()
        return {"count": count, "latest_seq": latest}

    def events(self, job: str, after: int = 0, limit: int = 200) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM events WHERE job=? AND seq>? ORDER BY seq LIMIT ?",
                              (job, after, limit)).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
