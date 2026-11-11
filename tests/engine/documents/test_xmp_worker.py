"""Bounded XMP writer process: Job ownership, limits, report integrity and attempts. Synthetic, no provider."""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pymupdf
import pytest

import pdfmd.documents as documents_module
from pdfmd import xmp_worker
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher

WINDOWS = os.name == "nt"
VALUES = {"title": {"x-default": "t"}, "description": {"x-default": "d"}, "source": "urn:sha256:" + "a" * 64,
          "pdfmd": {"SchemaVersion": 1, "OccurrenceId": "1" * 32, "RepresentationId": "2" * 32, "RecordJSON": "{}"}}


def png() -> bytes:
    return pymupdf.Pixmap(pymupdf.csRGB, 8, 6, bytes([10, 80, 210] * 48), False).tobytes("png")


def attempts(folder: Path) -> list[Path]:
    return sorted(folder.glob("attempt-*"))


def fake_worker(tmp_path, monkeypatch, body: str) -> None:
    """Replace the worker command with a script that receives the same arguments and gate."""
    script = tmp_path / "fake_worker.py"
    script.write_text("import sys, time, json\nfrom pathlib import Path\n"
                      "args = sys.argv[1:]\nreport = Path(args[args.index('--report') + 1])\n"
                      "output = Path(args[args.index('--output') + 1])\n"
                      "assert sys.stdin.buffer.read(1) == b'g'\n" + textwrap.dedent(body), encoding="utf-8")
    monkeypatch.setattr(xmp_worker, "command", lambda arguments: [sys.executable, "-B", str(script), *arguments])


def save_setup(tmp_path):
    d = Dispatcher(Store(tmp_path / "workspace"))
    pdf = tmp_path / "one.pdf"
    with pymupdf.open() as document:
        document.new_page(width=300, height=200)
        document.save(pdf)
    job = d.evidence.create_job(str(pdf), "Worker boundary.")["id"]
    render = d.evidence.render_page(job, 1, 50)
    ev = [{"ref": render["ref"], "physical_page": 1, "region": None, "note": "n"}]
    args = {"base_version": None, "expected_head": None, "replace_blocks": [{"id": "b", "pages": [1], "markdown": "![x](asset:new/x)"}],
            "page_updates": {"1": {"disposition": "included"}},
            "asset_changes": [{"kind": "create", "client_key": "x", "facts": {"image_ref": render["ref"],
                "description": {"full": "f", "filename": "Bounded", "language": "en", "punctuation": "ascii", "basis": []},
                "locations": [{"physical_page": 1, "region": None, "basis": ev}]}}]}
    return d, job, render, args


# Limits and accounting ---------------------------------------------------------
def test_accepted_preparation_records_job_accounting_and_removes_its_attempt(tmp_path):
    stats = {}
    out = xmp_worker.enrich_bounded(png(), VALUES, tmp_path / "rep", stats=stats)
    assert out.startswith(b"\x89PNG") and not (tmp_path / "rep").exists()
    assert stats["exit"] == 0 and not stats["timed_out"] and stats["input_bytes"] == len(png())
    if WINDOWS:
        acc = stats["accounting"]
        assert acc["memory_limit_bytes"] == 256 * 1024 * 1024 and acc["job_cpu_limit_seconds"] == 5
        assert 0 < acc["peak_job_bytes"] < 256 * 1024 * 1024 and acc["user_cpu_seconds"] >= 0 and acc["processes"] >= 1


def test_rejection_reports_the_candidate_code_and_keeps_inputs(tmp_path):
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(b"not an image", VALUES, tmp_path / "rejected")
    assert failure.value.details["code"] == "unsupported_type" and failure.value.details["exit"] == 2
    [attempt] = attempts(tmp_path / "rejected")
    assert (attempt / "input.bin").read_bytes() == b"not an image" and not (attempt / "output.bin").exists()


@pytest.mark.skipif(not WINDOWS, reason="Windows Job object limits")
def test_memory_limit_stops_a_running_worker_and_keeps_inputs(tmp_path):
    # A 25.8 MB PNG fits the 256 MiB limit but not 96 MiB: the engine's Job stops
    # the running worker (MemoryError), not merely its start.
    big = pymupdf.Pixmap(pymupdf.csRGB, 3000, 3000, random.Random(1).randbytes(3000 * 3000 * 3), False).tobytes("png")
    assert xmp_worker.enrich_bounded(big, VALUES, tmp_path / "control").startswith(b"\x89PNG")
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(big, VALUES, tmp_path / "memory", memory_bytes=96 * 1024 * 1024)
    assert failure.value.details["code"] == "process_failed" and failure.value.details["exit"] not in (0, 2)
    [attempt] = attempts(tmp_path / "memory")
    assert "MemoryError" in (attempt / "stderr.txt").read_text("utf-8", "replace")
    assert (attempt / "input.bin").read_bytes() == big and not (attempt / "output.bin").exists()


def test_wall_limit_terminates_the_worker(tmp_path, monkeypatch):
    fake_worker(tmp_path, monkeypatch, "time.sleep(30)\n")
    started = time.perf_counter()
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(png(), VALUES, tmp_path / "wall", wall_seconds=1)
    assert failure.value.details["timed_out"] and failure.value.details["code"] == "process_failed"
    assert time.perf_counter() - started < 10


# AR-T3B-05 -----------------------------------------------------------------------
@pytest.mark.skipif(not WINDOWS, reason="Windows Job object lifetime")
def test_worker_is_in_the_engine_job_before_input_and_dies_with_the_engine(tmp_path):
    marker, done = tmp_path / "started.txt", tmp_path / "finished.txt"
    script = tmp_path / "slow_worker.py"
    script.write_text(textwrap.dedent(f"""
        import ctypes, sys, time
        from pathlib import Path
        assert sys.stdin.buffer.read(1) == b'g'
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        k.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
        inside = ctypes.c_int()
        assert k.IsProcessInJob(k.GetCurrentProcess(), None, ctypes.byref(inside))
        Path({str(marker)!r}).write_text(f"in_job={{inside.value}}")
        time.sleep(6)
        Path({str(done)!r}).write_text("finished")
    """), encoding="utf-8")
    engine = tmp_path / "engine.py"
    engine.write_text(textwrap.dedent(f"""
        import sys
        from pathlib import Path
        from pdfmd import xmp_worker
        xmp_worker.command = lambda arguments: [sys.executable, "-B", {str(script)!r}, *arguments]
        xmp_worker.enrich_bounded(b"x", {{}}, Path({str(tmp_path / 'prep')!r}), wall_seconds=60)
    """), encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-B", str(engine)])
    for _ in range(300):
        if marker.exists():
            break
        time.sleep(0.05)
    assert marker.read_text() == "in_job=1"  # assigned before the gate opened
    process.kill()  # hard engine termination: its Job handle closes
    process.wait()
    time.sleep(8)
    assert not done.exists(), "the worker outlived the engine"
    [attempt] = attempts(tmp_path / "prep")
    assert (attempt / "input.bin").read_bytes() == b"x"


# AR-T3B-06 -----------------------------------------------------------------------
@pytest.mark.parametrize("body,code,exit_code", [
    ("report.write_text('{')\nsys.exit(19)\n", "process_failed", 19),
    ("report.write_text('{')\nsys.exit(0)\n", "invalid_report", 0),
    ("report.write_text(json.dumps({'accepted': True, 'output_sha256': 'x', 'input_sha256': 'y'}))\noutput.write_bytes(b'z')\nsys.exit(0)\n",
     "output_mismatch", 0),
    ("sys.exit(0)\n", "invalid_report", 0),
    ("report.write_text('[1]')\nsys.exit(2)\n", "invalid_report", 2),
])
def test_partial_or_invalid_reports_fail_closed_with_the_process_status(tmp_path, monkeypatch, body, code, exit_code):
    fake_worker(tmp_path, monkeypatch, body)
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(png(), VALUES, tmp_path / "rep")
    assert failure.value.details["code"] == code and failure.value.details["exit"] == exit_code
    assert len(attempts(tmp_path / "rep")) == 1


def test_timeout_during_report_write_is_a_timeout(tmp_path, monkeypatch):
    fake_worker(tmp_path, monkeypatch, "report.write_text('{')\ntime.sleep(30)\n")
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(png(), VALUES, tmp_path / "rep", wall_seconds=1)
    assert failure.value.details["timed_out"] and failure.value.details["code"] == "process_failed"


def test_invalid_report_through_edit_is_a_typed_failure_and_the_next_save_succeeds(tmp_path, monkeypatch):
    d, job, render, args = save_setup(tmp_path)
    fake_worker(tmp_path, monkeypatch, "report.write_text('{')\nsys.exit(19)\n")
    failed = d.execute(job, "broken", "edit_document", json.dumps(args))
    assert failed["data"]["error_code"] == "ASSET_ENRICHMENT_FAILED" and "exit status 19" in failed["data"]["error"]
    assert d.store.get("job", job)["head"] is None
    assert not [r for r in d.store.records("asset_name", job) if r["status"] == "pending"]
    monkeypatch.undo()
    ok = d.execute(job, "next", "edit_document", json.dumps(args))
    assert ok["ok"] and ok["data"]["asset_changes"][0]["asset_path"] == "assets/Bounded-i1.png"


# AR-T3B-07 -----------------------------------------------------------------------
def test_interrupted_attempt_logs_survive_a_successful_same_operation_retry(tmp_path, monkeypatch):
    d, job, render, args = save_setup(tmp_path)
    fake_worker(tmp_path, monkeypatch, "print('interrupted attempt log')\nsys.exit(19)\n")
    monkeypatch.setattr(documents_module.Documents, "_release", lambda *a, **k: None)  # process loss: nothing settles
    with pytest.raises(ValueError):
        d.documents.edit(job, "op", args, "op-hash", "candidate:none")
    monkeypatch.undo()
    resumed = d.documents.edit(job, "op", args, "op-hash", "candidate:none")
    assert resumed["asset_changes"][0]["asset_path"] == "assets/Bounded-i1.png"
    [kept] = list((d.store.root / "preparation").rglob("attempt-*"))
    assert (kept / "stdout.txt").read_text().strip() == "interrupted attempt log"
    assert (kept / "input.bin").read_bytes() == d.store.bytes(render["ref"], job)
    path = resumed["asset_changes"][0]["asset_path"]
    saved = d.documents.version(job, resumed["version_id"])
    assert (d.documents.root / resumed["version_id"] / path).read_bytes() == d.store.bytes(saved["assets"][path]["ref"], job)


def test_worker_command_is_a_separate_process(tmp_path, monkeypatch):
    d, job, render, args = save_setup(tmp_path)
    commands = []
    real = xmp_worker.command
    monkeypatch.setattr(xmp_worker, "command", lambda arguments: commands.append(real(arguments)) or commands[-1])
    assert d.execute(job, "save", "edit_document", json.dumps(args))["ok"]
    assert commands and commands[0][1:5] == ["-I", "-B", "-m", "pdfmd.xmp_worker"]


# AR-T3B-08 sizing ---------------------------------------------------------------
def noise_png(side: int) -> bytes:
    return pymupdf.Pixmap(pymupdf.csRGB, side, side, random.Random(side).randbytes(side * side * 3), False).tobytes("png")


def test_memory_budget_scales_with_encoded_bytes():
    MiB = 2 ** 20
    assert xmp_worker.memory_budget(1 * MiB) == 256 * MiB
    assert xmp_worker.memory_budget(100 * MiB) == 64 * MiB + 800 * MiB
    assert xmp_worker.memory_budget(248 * MiB) <= xmp_worker.MEMORY_CEILING < xmp_worker.memory_budget(249 * MiB)


@pytest.mark.skipif(not WINDOWS, reason="Windows Job object limits")
@pytest.mark.parametrize("side", [4300, 6000])  # 52.9 MiB (failed at the fixed 256 MiB) and ~103 MiB
def test_large_valid_pngs_fit_the_sized_budget(tmp_path, side):
    data = noise_png(side)
    stats = {}
    out = xmp_worker.enrich_bounded(data, VALUES, tmp_path / "big", stats=stats)
    assert out.startswith(b"\x89PNG") and len(out) > len(data)
    assert stats["bounds"]["memory_bytes"] == xmp_worker.memory_budget(len(data)) > 256 * 2 ** 20
    assert stats["accounting"]["peak_job_bytes"] < stats["bounds"]["memory_bytes"]


def test_over_ceiling_input_is_rejected_before_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(xmp_worker, "MEMORY_CEILING", 300 * 2 ** 20)
    data = noise_png(4300)
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(data, VALUES, tmp_path / "over")
    assert failure.value.details["code"] == "over_budget" and "lower-DPI render" in str(failure.value)
    assert not (tmp_path / "over").exists()


@pytest.mark.skipif(not WINDOWS, reason="Windows Job object limits")
def test_dom_heavy_existing_xmp_is_rejected_with_an_explicit_memory_limit(tmp_path):
    sys.path.insert(0, str(Path(__file__).parents[3] / "tools" / "qualification"))
    from measure_writer_budget import heavy_xmp_jpeg
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(heavy_xmp_jpeg(), VALUES, tmp_path / "heavy")
    # Memory, CPU or wall can fire first depending on host speed; each must be named.
    assert failure.value.details["limit"] in {"its 256 MiB memory limit", "its 5 s CPU limit", "its 15 s wall-time limit"}
    assert "very many nodes" in str(failure.value)


# Writer pool and parallel preparation ---------------------------------------------
SLOW = "Path(str(report) + '.start').write_text(str(time.time()))\ntime.sleep(1.0)\nsys.exit(19)\n"


def overlap(folders) -> int:
    """Maximum number of fake workers whose [start, start + 1 s) intervals overlap."""
    starts = sorted(float(p.read_text()) for f in folders for p in Path(f).rglob("report.json.start"))
    return max(sum(1 for t in starts if s <= t < s + 0.95) for s in starts)


def run_parallel(n, folder_root, memory_bytes):
    def one(i):
        try:
            xmp_worker.enrich_bounded(png(), VALUES, folder_root / f"w{i}", memory_bytes=memory_bytes)
        except xmp_worker.WorkerFailure:
            pass
    with ThreadPoolExecutor(n) as executor:
        list(executor.map(one, range(n)))


def test_concurrent_first_access_initializes_one_pool(monkeypatch):
    monkeypatch.setattr(xmp_worker, "POOL", None)
    first_query, second_request, second_query = Event(), Event(), Event()
    lock = Lock()
    queries = []

    def host_memory():
        with lock:
            queries.append(1)
            first = len(queries) == 1
        if first:
            first_query.set()
            assert second_request.wait(5)
            # Give an unsynchronized caller a chance to enter the host query.
            second_query.wait(0.5)
        else:
            second_query.set()
        return 8 * 2**30

    def competing_access():
        second_request.set()
        return xmp_worker.pool()

    monkeypatch.setattr(xmp_worker, "physical_memory", host_memory)
    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(xmp_worker.pool)
        assert first_query.wait(5)
        second = executor.submit(competing_access)
        assert first.result(timeout=5) is second.result(timeout=5)
    assert len(queries) == 1


def test_pool_memory_reservation_limits_concurrency(tmp_path, monkeypatch):
    fake_worker(tmp_path, monkeypatch, SLOW)
    monkeypatch.setattr(xmp_worker, "POOL", xmp_worker.WriterPool(600 * 2 ** 20, 8))
    run_parallel(4, tmp_path, 256 * 2 ** 20)  # two 256 MiB reservations fit in 600 MiB, three do not
    assert overlap([tmp_path]) == 2 and xmp_worker.POOL.peak_running == 2 and xmp_worker.POOL.reserved == 0


def test_pool_worker_cap_limits_concurrency(tmp_path, monkeypatch):
    fake_worker(tmp_path, monkeypatch, SLOW)
    monkeypatch.setattr(xmp_worker, "POOL", xmp_worker.WriterPool(64 * 2 ** 30, 3))
    run_parallel(6, tmp_path, 256 * 2 ** 20)
    assert overlap([tmp_path]) == 3 and xmp_worker.POOL.peak_running == 3


def test_pool_admission_is_first_come_first_served(monkeypatch):
    import threading
    pool = xmp_worker.WriterPool(1000, 4)
    order, release = [], threading.Event()

    def hold():
        with pool.admit(600):
            release.wait(5)
    first = threading.Thread(target=hold)
    first.start()
    time.sleep(0.2)

    def take(name, size):
        with pool.admit(size):
            order.append(name)
    big = threading.Thread(target=take, args=("big", 900))
    big.start()
    time.sleep(0.2)
    small = threading.Thread(target=take, args=("small", 100))  # would fit now, but must not overtake "big"
    small.start()
    time.sleep(0.3)
    assert order == []
    release.set()
    for thread in (first, big, small):
        thread.join(5)
    assert order == ["big", "small"]


def test_image_over_this_hosts_pool_is_rejected_before_any_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(xmp_worker, "POOL", xmp_worker.WriterPool(300 * 2 ** 20, 2))
    with pytest.raises(xmp_worker.WorkerFailure) as failure:
        xmp_worker.enrich_bounded(noise_png(4300), VALUES, tmp_path / "host")
    assert failure.value.details["code"] == "over_budget" and "writer pool (30% of RAM)" in str(failure.value)
    assert not (tmp_path / "host").exists()


def test_a_saves_images_are_prepared_in_parallel(tmp_path, monkeypatch):
    d, job, render, args = save_setup(tmp_path)
    second, third = d.evidence.render_page(job, 1, 60), d.evidence.render_page(job, 1, 70)
    for key, image in (("y", second), ("z", third)):
        args["asset_changes"].append({**args["asset_changes"][0], "client_key": key,
                                      "facts": {**args["asset_changes"][0]["facts"], "image_ref": image["ref"],
                                                "description": {**args["asset_changes"][0]["facts"]["description"], "filename": f"Bounded {key}"},
                                                "locations": [{"physical_page": 1, "region": None,
                                                               "basis": [{"ref": image["ref"], "physical_page": 1, "region": None, "note": "n"}]}]}})
    args["replace_blocks"][0]["markdown"] = "![x](asset:new/x) ![y](asset:new/y) ![z](asset:new/z)"
    monkeypatch.setattr(xmp_worker, "POOL", xmp_worker.WriterPool(64 * 2 ** 30, 8))
    real = xmp_worker.run_attempt

    def slow(attempt, *a, **k):
        (attempt / "started").write_text(str(time.time()))
        time.sleep(1.0)
        return real(attempt, *a, **k)
    monkeypatch.setattr(xmp_worker, "run_attempt", slow)
    started = time.perf_counter()
    result = d.execute(job, "parallel", "edit_document", json.dumps(args))
    assert result["ok"], result
    assert [c["client_key"] for c in result["data"]["asset_changes"]] == ["x", "y", "z"]  # request order kept
    assert time.perf_counter() - started < 3.0  # three 1 s waits overlapped
    assert xmp_worker.POOL.peak_running >= 2


def test_saves_on_two_tasks_run_concurrently_through_the_pool(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(xmp_worker, "POOL", xmp_worker.WriterPool(64 * 2 ** 30, 8))
    a = save_setup(tmp_path / "a")
    b = save_setup(tmp_path / "b")
    results = {}

    def run(name, setup):
        d, job, render, args = setup
        results[name] = d.execute(job, "save", "edit_document", json.dumps(args))
    threads = [threading.Thread(target=run, args=(n, s)) for n, s in (("a", a), ("b", b))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    assert results["a"]["ok"] and results["b"]["ok"]
    assert results["a"]["data"]["asset_changes"][0]["asset_path"] == results["b"]["data"]["asset_changes"][0]["asset_path"]


def test_substituted_validated_output_does_not_publish(tmp_path, monkeypatch):
    d, job, render, args = save_setup(tmp_path)
    first = d.execute(job, "base", "edit_document", json.dumps({
        **args, "asset_changes": [], "replace_blocks": [{"id": "b", "pages": [1], "markdown": "Text only."}],
    }))
    assert first["ok"], first
    base = first["data"]["version_id"]
    args.update(base_version=base, expected_head=base)
    real = xmp_worker.run_attempt

    def substitute(*args, **kwargs):
        output, digest = real(*args, **kwargs)
        output.write_bytes(output.with_name("input.bin").read_bytes())
        return output, digest

    with monkeypatch.context() as patch:
        patch.setattr(xmp_worker, "run_attempt", substitute)
        rejected = d.execute(job, "substitute", "edit_document", json.dumps(args))
    assert not rejected["ok"] and rejected["data"]["error_code"] == "ASSET_INTEGRITY_FAILED"
    assert "expected SHA-256" in rejected["data"]["error"]
    assert d.store.get("job", job)["head"] == base
    assert [record["id"] for record in d.store.records("version", job)] == [base]
    assert d.store.get("operation", "substitute")["ok"] is False
    assert d.store.get("blob", rejected["candidate_ref"], job=job)
    assert not [record for record in d.store.records("blob", job) if record["kind"] == "enriched_image"]
    [attempt] = list((d.store.root / "preparation").rglob("attempt-*"))
    assert (attempt / "output.bin").read_bytes() == d.store.bytes(render["ref"], job)
    assert json.loads((attempt / "report.json").read_text("utf-8"))["accepted"]
    assert d.execute(job, "correct-output", "edit_document", json.dumps(args))["ok"]
