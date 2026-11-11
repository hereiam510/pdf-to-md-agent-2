"""Bounded child process for primary-XMP enrichment (T3b writer boundary).

The engine never runs the writer in its own process. ``enrich_bounded`` starts a
short-lived worker: the frozen engine relaunches itself with ``--xmp-prepare``;
a development engine runs ``python -I -m pdfmd.xmp_worker``.

Process lifetime (AR-T3B-05). On Windows the *engine* creates a kill-on-close Job
with the memory and CPU limits and keeps its only handle. The worker is created
suspended, assigned to the Job and only then resumed, so it and every process it
starts (such as the interpreter behind a venv launcher) run inside the Job. It also
blocks on a one-byte stdin gate opened after assignment. The engine enforces the wall limit by
terminating the Job, and if the engine itself dies its handle closes and Windows
kills the worker. On POSIX the worker sets address-space and CPU rlimits after the
gate (untested fallback; no engine-death guarantee).

Classification (AR-T3B-06). The exit status and timeout are decided first; the
report is parsed defensively and only trusted when it agrees with the status and
the output hashes. Anything else fails closed as ``process_failed`` with the raw
files kept.

Attempts (AR-T3B-07). Each launch writes into its own attempt folder under the
representation's preparation folder; success removes only that attempt.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Condition, Lock
import time
import uuid

MEMORY_BYTES = 256 * 1024 * 1024  # floor, and the T1-F06 qualification value
MEMORY_BASE = 64 * 1024 * 1024
MEMORY_PER_INPUT_BYTE = 8         # measured peak is about 13 MiB + 5 x encoded bytes for PNGs
MEMORY_CEILING = 2 * 1024 ** 3
CPU_SECONDS = 5
WALL_SECONDS = 15
GATE = b"g"


POOL_FRACTION = 0.30              # share of physical RAM for all writer workers together
POOL_MIN = 1536 * 1024 * 1024     # 1.5 GiB
POOL_MAX = 8 * 1024 ** 3
MINIMUM_HOST_RAM = 8 * 1024 ** 3  # declared minimum host (8 GB RAM, 4 logical cores)


class WorkerFailure(Exception):
    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


def physical_memory() -> int:
    if sys.platform == "win32":
        import ctypes

        class STATUS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong) for n in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile",
                                                  "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]
        status = STATUS()
        status.dwLength = ctypes.sizeof(STATUS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return MINIMUM_HOST_RAM
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")


class WriterPool:
    """Engine-wide admission for bounded writer workers.

    A worker starts only when its full Job memory limit fits in the unreserved
    capacity and fewer than ``max_workers`` are running; admission is first come,
    first served, so a large image is not starved by a stream of small ones.
    Reserving the limit (not the expected use) keeps even a pathological packet
    from pushing the host into paging. Time limits start after admission.
    """

    def __init__(self, capacity_bytes: int, max_workers: int):
        self.capacity, self.max_workers = capacity_bytes, max(1, max_workers)
        self.reserved = self.running = self.peak_running = 0
        self._condition = Condition()
        self._queue: list[object] = []

    @classmethod
    def for_host(cls) -> "WriterPool":
        capacity = min(POOL_MAX, max(POOL_MIN, int(POOL_FRACTION * physical_memory())))
        return cls(capacity, (os.cpu_count() or 2) - 1)

    def admit(self, memory_bytes: int):
        from contextlib import contextmanager

        @contextmanager
        def admission():
            if memory_bytes > self.capacity:
                raise WorkerFailure(f"Preparing this image needs about {memory_bytes / 2**20:.0f} MiB, more than this "
                                    f"computer's {self.capacity / 2**20:.0f} MiB writer pool ({POOL_FRACTION:.0%} of RAM). "
                                    "Deliver a smaller source representation (e.g. a lower-DPI render or a region).",
                                    {"stage": "process", "code": "over_budget", "memory_bytes": memory_bytes,
                                     "pool_bytes": self.capacity})
            ticket = object()
            with self._condition:
                self._queue.append(ticket)
                while (self._queue[0] is not ticket or self.reserved + memory_bytes > self.capacity
                       or self.running >= self.max_workers):
                    self._condition.wait()
                self._queue.pop(0)
                self.reserved += memory_bytes
                self.running += 1
                self.peak_running = max(self.peak_running, self.running)
                self._condition.notify_all()
            try:
                yield
            finally:
                with self._condition:
                    self.reserved -= memory_bytes
                    self.running -= 1
                    self._condition.notify_all()
        return admission()


POOL: WriterPool | None = None
_POOL_LOCK = Lock()


def pool() -> WriterPool:
    global POOL
    with _POOL_LOCK:
        if POOL is None:
            POOL = WriterPool.for_host()
        return POOL


# ---------------------------------------------------------------- engine side
class EngineJob:
    """A kill-on-close Windows Job owned by the engine for one worker."""

    def __init__(self, memory_bytes: int, cpu_seconds: int):
        import ctypes as C
        from ctypes import wintypes as W

        class BASIC(C.Structure):
            _fields_ = [("ProcessTime", C.c_longlong), ("JobTime", C.c_longlong), ("Flags", W.DWORD),
                        ("Min", C.c_size_t), ("Max", C.c_size_t), ("Active", W.DWORD), ("Affinity", C.c_size_t),
                        ("Priority", W.DWORD), ("Scheduling", W.DWORD)]

        class IO(C.Structure):
            _fields_ = [(n, C.c_ulonglong) for n in ("ReadOp", "WriteOp", "OtherOp", "Read", "Write", "Other")]

        class EXT(C.Structure):
            _fields_ = [("Basic", BASIC), ("IO", IO), ("ProcessMemory", C.c_size_t),
                        ("JobMemory", C.c_size_t), ("PeakProcess", C.c_size_t), ("PeakJob", C.c_size_t)]

        class ACCOUNTING(C.Structure):
            _fields_ = [("TotalUserTime", C.c_longlong), ("TotalKernelTime", C.c_longlong),
                        ("ThisPeriodUserTime", C.c_longlong), ("ThisPeriodKernelTime", C.c_longlong),
                        ("PageFaults", W.DWORD), ("TotalProcesses", W.DWORD), ("ActiveProcesses", W.DWORD),
                        ("Terminated", W.DWORD)]

        self.C, self.EXT, self.ACCOUNTING = C, EXT, ACCOUNTING
        k = self.k = C.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.restype = W.HANDLE
        k.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
        k.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
        k.QueryInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]
        k.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
        k.TerminateJobObject.argtypes = [W.HANDLE, W.UINT]
        k.OpenProcess.restype = W.HANDLE
        k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        k.CloseHandle.argtypes = [W.HANDLE]
        self.handle = k.CreateJobObjectW(None, None)
        limits = EXT()
        limits.Basic.Flags = 0x2000 | 0x200 | 0x4  # kill on job close, job memory, job user-CPU time
        limits.Basic.JobTime = cpu_seconds * 10_000_000
        limits.JobMemory = memory_bytes
        if not self.handle or not k.SetInformationJobObject(self.handle, 9, C.byref(limits), C.sizeof(limits)):
            raise C.WinError(C.get_last_error())

    def assign_and_resume(self, pid: int) -> None:
        """Assign a process created suspended, then resume it.

        Nothing in the worker runs before it is a Job member, so a launcher (such as
        a venv python.exe redirector) cannot start an interpreter outside the Job.
        """
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_SUSPEND_RESUME
        process = self.k.OpenProcess(0x0100 | 0x0001 | 0x0800, False, pid)
        if not process:
            raise self.C.WinError(self.C.get_last_error())
        try:
            if not self.k.AssignProcessToJobObject(self.handle, process):
                raise self.C.WinError(self.C.get_last_error())
            ntdll = self.C.WinDLL("ntdll")
            ntdll.NtResumeProcess.argtypes = [self.C.c_void_p]
            if ntdll.NtResumeProcess(process) != 0:
                raise OSError("Could not resume the bounded worker after Job assignment.")
        finally:
            self.k.CloseHandle(process)

    def terminate(self) -> None:
        self.k.TerminateJobObject(self.handle, 1)

    def accounting(self) -> dict:
        C, ext, acc = self.C, self.EXT(), self.ACCOUNTING()
        result = {}
        if self.k.QueryInformationJobObject(self.handle, 9, C.byref(ext), C.sizeof(ext), None):
            result.update(peak_job_bytes=ext.PeakJob, memory_limit_bytes=ext.JobMemory,
                          job_cpu_limit_seconds=ext.Basic.JobTime / 10_000_000)
        if self.k.QueryInformationJobObject(self.handle, 1, C.byref(acc), C.sizeof(acc), None):
            result.update(user_cpu_seconds=acc.TotalUserTime / 10_000_000,
                          kernel_cpu_seconds=acc.TotalKernelTime / 10_000_000, processes=acc.TotalProcesses)
        return result

    def close(self) -> None:
        if self.handle:
            self.k.CloseHandle(self.handle)  # kill-on-close: no Job member survives
            self.handle = None


def memory_budget(input_bytes: int) -> int:
    """Job memory for one preparation, sized from the encoded image bytes (AR-T3B-08)."""
    return max(MEMORY_BYTES, MEMORY_BASE + MEMORY_PER_INPUT_BYTE * input_bytes)


def command(arguments: list[str]) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--xmp-prepare", *arguments]
    return [sys.executable, "-I", "-B", "-m", "pdfmd.xmp_worker", *arguments]


def _read_report(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _text(value) -> bool:
    return isinstance(value, str) and bool(value)


def checked_budget(input_bytes: int, memory_bytes: int | None) -> int:
    if memory_bytes is not None:
        return memory_bytes
    memory_bytes = memory_budget(input_bytes)
    if memory_bytes > pool().capacity:  # this host's writer pool is smaller than the global ceiling
        raise WorkerFailure(f"The image is {input_bytes / 2**20:.1f} MiB; preparing it would need about "
                            f"{memory_bytes / 2**20:.0f} MiB, more than this computer's {pool().capacity / 2**20:.0f} MiB "
                            f"writer pool ({POOL_FRACTION:.0%} of RAM). Deliver a smaller source representation "
                            "(e.g. a lower-DPI render or a region).",
                            {"stage": "process", "code": "over_budget", "input_bytes": input_bytes,
                             "memory_bytes": memory_bytes, "pool_bytes": pool().capacity})
    if memory_bytes > MEMORY_CEILING:
        raise WorkerFailure(f"The image is {input_bytes / 2**20:.1f} MiB; preparing it would need about "
                            f"{memory_bytes / 2**20:.0f} MiB, above the {MEMORY_CEILING / 2**20:.0f} MiB writer "
                            "ceiling. Deliver a smaller source representation (e.g. a lower-DPI render or a region).",
                            {"stage": "process", "code": "over_budget", "input_bytes": input_bytes,
                             "memory_bytes": memory_bytes, "ceiling_bytes": MEMORY_CEILING})
    return memory_bytes


def new_attempt(folder: Path) -> Path:
    attempt = folder / f"attempt-{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    attempt.mkdir(parents=True)
    return attempt


def finish(attempt: Path) -> None:
    """Remove an accepted attempt, and its representation folder once empty."""
    import shutil
    shutil.rmtree(attempt, ignore_errors=True)
    try:
        attempt.parent.rmdir()
    except OSError:
        pass


def enrich_bounded(data: bytes, values: dict, folder: Path, *, memory_bytes: int | None = None,
                   cpu_seconds: int = CPU_SECONDS, wall_seconds: float = WALL_SECONDS,
                   stats: dict | None = None) -> bytes:
    """Bytes convenience for tests and measurement; the save path uses ``prepare_object``."""
    from hashlib import sha256
    memory_bytes = checked_budget(len(data), memory_bytes)
    attempt = new_attempt(folder)
    (attempt / "input.bin").write_bytes(data)
    output, digest = run_attempt(attempt, sha256(data).hexdigest(), len(data), values, memory_bytes=memory_bytes,
                                 cpu_seconds=cpu_seconds, wall_seconds=wall_seconds, stats=stats)
    result = output.read_bytes()
    if sha256(result).hexdigest() != digest:
        raise WorkerFailure("The bounded XMP writer's output changed after validation. The attempt is retained.",
                            {"stage": "process", "code": "output_mismatch", "attempt": attempt.name})
    finish(attempt)
    return result


def prepare_object(store, ref: str, job: str, values: dict, folder: Path, *, memory_bytes: int | None = None,
                   cpu_seconds: int = CPU_SECONDS, wall_seconds: float = WALL_SECONDS,
                   stats: dict | None = None) -> tuple[Path, Path, str]:
    """Prepare a store object and return the attempt folder, output path and validated digest.

    The object is copied into the attempt in chunks and must hash to its recorded
    identity. The caller registers the output file against the digest and then calls ``finish``.
    """
    record = store.get("blob", ref, job=job)
    memory_bytes = checked_budget(record["bytes"], memory_bytes)
    attempt = new_attempt(folder)
    store.copy_object(ref, job, attempt / "input.bin")
    output, digest = run_attempt(attempt, record["sha256"], record["bytes"], values, memory_bytes=memory_bytes,
                                 cpu_seconds=cpu_seconds, wall_seconds=wall_seconds, stats=stats)
    return attempt, output, digest


def run_attempt(attempt: Path, input_sha256: str, input_bytes: int, values: dict, *, memory_bytes: int,
                cpu_seconds: int, wall_seconds: float, stats: dict | None) -> tuple[Path, str]:
    """Launch the bounded worker and return the output path and verified SHA-256.

    Raises ``WorkerFailure`` with ``code`` set to the candidate's rejection code
    (exit 2 with a valid report) or ``process_failed`` / ``invalid_report`` /
    ``output_mismatch``. The attempt folder is kept on every failure.
    """
    from .storage import file_digest
    source, output, values_path, report = (attempt / "input.bin", attempt / "output.bin",
                                           attempt / "values.json", attempt / "report.json")
    values_path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    arguments = ["prepare", "--input", str(source), "--output", str(output), "--values", str(values_path),
                 "--report", str(report), "--memory-bytes", str(memory_bytes), "--cpu-seconds", str(cpu_seconds)]
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    queued = time.perf_counter()
    with pool().admit(memory_bytes):  # engine-wide writer pool; limits start after admission
        queued_seconds = round(time.perf_counter() - queued, 3)
        job = EngineJob(memory_bytes, cpu_seconds) if sys.platform == "win32" else None
        status, timed_out, started = None, False, time.perf_counter()
        try:
            with (attempt / "stdout.txt").open("wb") as out, (attempt / "stderr.txt").open("wb") as err:
                process = subprocess.Popen(command(arguments), stdin=subprocess.PIPE, stdout=out, stderr=err,
                                           env=env, shell=False,
                                           creationflags=0x4 if job is not None else 0)  # CREATE_SUSPENDED
                try:
                    if job is not None:
                        job.assign_and_resume(process.pid)  # before any worker code runs
                    try:
                        process.stdin.write(GATE)
                        process.stdin.close()
                    except OSError:
                        pass  # the worker already exited; its status decides
                    try:
                        status = process.wait(timeout=wall_seconds)
                    except subprocess.TimeoutExpired:
                        timed_out = True
                        job.terminate() if job is not None else process.kill()
                        status = process.wait()
                except BaseException:
                    if job is not None:
                        job.terminate()
                    process.kill()  # also covers a failed Job assignment
                    process.wait()
                    raise
            accounting = job.accounting() if job is not None else {}
        finally:
            if job is not None:
                job.close()
    details = {"exit": status, "timed_out": timed_out, "elapsed_seconds": round(time.perf_counter() - started, 3),
               "accounting": accounting, "input_bytes": input_bytes, "queued_seconds": queued_seconds,
               "bounds": {"memory_bytes": memory_bytes, "cpu_seconds": cpu_seconds, "wall_seconds": wall_seconds},
               "attempt": attempt.name, "report_present": report.exists()}
    if stats is not None:
        stats.update(details)
    candidate = _read_report(report)
    details["report_valid"] = candidate is not None
    if timed_out or status not in (0, 2):
        stderr = (attempt / "stderr.txt").read_text("utf-8", "replace")[-4000:]
        cpu = accounting.get("user_cpu_seconds", 0)
        if timed_out:
            limit = f"its {wall_seconds:g} s wall-time limit"
        elif "MemoryError" in stderr or accounting.get("peak_job_bytes", 0) >= 0.95 * memory_bytes:
            limit = f"its {memory_bytes / 2**20:.0f} MiB memory limit"
        elif cpu >= 0.95 * cpu_seconds:
            limit = f"its {cpu_seconds} s CPU limit"
        else:
            limit = None
        reason = (f"reached {limit} (exit status {status}). An existing XMP packet with very many nodes can need far "
                  "more than the image size suggests" if limit else f"ended with exit status {status}")
        details["limit"] = limit
        raise WorkerFailure(f"The bounded XMP writer process {reason}; no output was accepted. The attempt's inputs "
                            "and logs are retained.", {**details, "stage": "process", "code": "process_failed"})
    if status == 2:
        if candidate and candidate.get("accepted") is False and all(_text(candidate.get(k)) for k in ("stage", "code", "message")):
            raise WorkerFailure(f"Primary-XMP enrichment rejected the image at {candidate['stage']} ({candidate['code']}): "
                                f"{candidate['message']}", {**details, "stage": candidate["stage"], "code": candidate["code"]})
        raise WorkerFailure("The XMP writer reported a rejection without a valid report. The attempt is retained.",
                            {**details, "stage": "process", "code": "invalid_report"})
    if not (candidate and candidate.get("accepted") is True and _text(candidate.get("output_sha256"))
            and _text(candidate.get("input_sha256")) and output.is_file()):
        raise WorkerFailure("The XMP writer exited successfully without a valid report and output; the result is not "
                            "used. The attempt is retained.", {**details, "stage": "process", "code": "invalid_report"})
    output_digest, _ = file_digest(output)
    if output_digest != candidate["output_sha256"] or candidate["input_sha256"] != input_sha256:
        raise WorkerFailure("The bounded XMP writer's output does not match its report. The attempt is retained.",
                            {**details, "stage": "process", "code": "output_mismatch"})
    return output, output_digest


# ---------------------------------------------------------------- worker side
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="xmp-prepare")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    for name in ("--input", "--output", "--values", "--report"):
        p.add_argument(name, required=True, type=Path)
    p.add_argument("--memory-bytes", type=int, default=MEMORY_BYTES)
    p.add_argument("--cpu-seconds", type=int, default=CPU_SECONDS)
    args = parser.parse_args(argv)
    if sys.stdin.buffer.read(1) != GATE:  # the engine opens the gate only after Job assignment
        return 3
    if sys.platform != "win32":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (args.memory_bytes, args.memory_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (args.cpu_seconds, args.cpu_seconds))
    from . import primary_xmp  # imported inside the bounded process
    return primary_xmp.prepare(argparse.Namespace(input=args.input, output=args.output, values=args.values,
                                                  report=args.report, inject=None))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
