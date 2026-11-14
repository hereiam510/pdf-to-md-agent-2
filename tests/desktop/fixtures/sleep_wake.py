"""Drive the Windows engine against a scripted loopback socket for NET-01 T7."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from math import ceil
from pathlib import Path
import json
import subprocess
from tempfile import mkdtemp
from threading import Event, Thread
import time

from pdfmd.clocks import Clocks, SYSTEM_CLOCKS
from pdfmd.documents import Documents
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.schema import Limits, WaitPolicy
from pdfmd.storage import Store, file_digest
from tests.engine.execution.test_continuation import build_delivery, check_delivery
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native
from tests.engine.transport.test_streaming_delivery import stream_frames


ENDPOINT_PATH = "/v1/chat/completions"
MIN_SLEEP = 60
TIMING_TOLERANCE = 2
WAKE_ADMISSION_TOLERANCE = 5
DRY_DELAYS = {"wait": 2, "in-flight": 1}
REAL_DELAYS = {"wait": 120, "in-flight": 180}


def sample(boot_marker):
    working, interrupt = SYSTEM_CLOCKS.pair()
    return {"working": working, "interrupt": interrupt, "monotonic": SYSTEM_CLOCKS.monotonic(),
            "wall": SYSTEM_CLOCKS.wall(), "boot_marker": boot_marker}


def sleep_capability():
    result = subprocess.run(["powercfg.exe", "/a"], capture_output=True, text=True,
                            encoding="oem", errors="replace", timeout=15)
    output = result.stdout
    # Keep the full OS output, including on localized hosts where this summary is unknown.
    english = output.partition("The following sleep states are available on this system:")
    unavailable = "The following sleep states are not available on this system:"
    available = english[2].split(unavailable)[0]
    if "Standby (S0 Low Power Idle)" in available:
        kind = "Modern Standby (S0 Low Power Idle)"
    elif "Standby (S3)" in available:
        kind = "S3"
    elif english[1] or unavailable in output:
        kind = "Neither S3 nor Modern Standby available"
    else:
        kind = "Unknown"
    return {"command": ["powercfg.exe", "/a"], "returncode": result.returncode,
            "stdout": output, "stderr": result.stderr, "sleep_type": kind}


class LoopbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        script = self.server
        if self.path != ENDPOINT_PATH:
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers["Content-Length"]))
        request = {"received_wall": SYSTEM_CLOCKS.wall(), "payload_sha256": sha256(body).hexdigest(),
                   "stream": json.loads(body).get("stream", False)}
        script.requests.append(request)
        if script.case == "wait" and len(script.requests) == 1:
            request["response_status"] = 503
            self.send_response(503)
            self.send_header("Retry-After", str(script.delay))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if script.case == "in-flight" and len(script.requests) == 1:
            script.prompt("The loopback server has received the request and is holding its reply.", MIN_SLEEP)
            deadline = SYSTEM_CLOCKS.monotonic() + script.delay
            # Recompute against the actual elapsed clock after each poll, including on wake.
            while (remaining := deadline - SYSTEM_CLOCKS.monotonic()) > 0:
                if script.finished.wait(min(remaining, 0.25)):
                    return
        request.update(response_status=200, reply_released_wall=SYSTEM_CLOCKS.wall())
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(script.reply)))
        self.end_headers()
        self.wfile.write(script.reply)

    def log_message(self, *_):
        pass


class LoopbackScript(ThreadingHTTPServer):
    def __init__(self, case, delay, dry_run):
        super().__init__(("127.0.0.1", 0), LoopbackHandler)
        self.case, self.delay, self.dry_run = case, delay, dry_run
        self.requests = []
        self.sleep_prompt = None
        self.finished = Event()

    def prompt(self, boundary, minimum):
        self.sleep_prompt = {"wall": SYSTEM_CLOCKS.wall(), "minimum_sleep_seconds": minimum}
        instruction = ("Dry run. Keep the machine awake." if self.dry_run else
                       f"Put the machine to Sleep now. Wake it after at least {minimum} seconds, timed separately.")
        print(f"{boundary} {instruction}", flush=True)


def verify_delivery(store, job, version, image, source, destination):
    # The reply can name the already saved version in its report while its edit saves a new version.
    # Verify the new head and check that the selected delivery has the same document content.
    reopened = Store(store.root)
    documents = Documents(reopened)
    head = job["head"]
    saved = documents.version(job["id"], head)
    reported = documents.version(job["id"], job["delivery"])
    if saved["parent"] != version or head == version or saved["content"] != reported["content"]:
        raise ValueError("The run did not save a new version matching the reported document.")
    check_delivery(reopened, job, head, image, source, destination)
    return {"verified": True, "reopened_version": head, "reported_version": job["delivery"],
            "claim": saved["content"]["claim"], "source_pages": job["page_count"],
            "source_sha256": file_digest(source)[0], "image_path": image["asset_path"],
            "image_sha256": saved["assets"][image["asset_path"]]["sha256"],
            "zip": destination.name, "zip_sha256": file_digest(destination)[0]}


def evaluate(report):
    case = report["case"]
    dry_run = report["parameters"]["dry_run"]
    attempts, requests = report["attempts"], report["http_requests"]
    intervals, wake_events = report["suspended_intervals"], report["resumed_after_sleep"]
    start, end = report["clocks"]["start"], report["clocks"]["end"]
    wall_span = end["wall"] - start["wall"]
    working_span = end["working"] - start["working"]
    suspended = sum(item["duration_seconds"] for item in intervals)
    clock_gap = end["interrupt"] - start["interrupt"] - working_span
    active_growth = report["active_seconds"]["after"] - report["active_seconds"]["before"]
    report["timing"] = {"wall_span_seconds": wall_span, "working_span_seconds": working_span,
                        "clock_suspension_seconds": clock_gap, "recorded_suspension_seconds": suspended,
                        "active_growth_seconds": active_growth}
    expected_attempts = 2 if case == "wait" else 1
    accepted = attempts[-1] if attempts else {}
    transport = accepted.get("transport", {})
    prompt = report["sleep_prompt"]
    checks = {
        "powercfg_succeeded": report["powercfg"]["returncode"] == 0,
        "prompt_at_case_boundary": prompt is not None,
        "active_time_excludes_suspension": (0 <= active_growth <= working_span + 0.1
            and abs(active_growth - working_span) <= TIMING_TOLERANCE
            and abs(active_growth - (wall_span - suspended)) <= TIMING_TOLERANCE),
        "expected_attempt_count": len(attempts) == len(requests) == report["job"]["attempts"] == expected_attempts,
        "reply_accepted_without_wait_timeout": (accepted.get("status") == "accepted"
            and accepted.get("send_evidence") == "response_observed" and not accepted.get("failure_class")
            and transport.get("mode") == "streaming_progress" and transport.get("stop_cause") == "complete"
            and transport.get("protocol_complete") is True and all(item["stream"] for item in requests)),
        "job_completed": report["job"]["status"] == "completed" and report["job"]["stop_reason"] == "agent_report",
        "export_verified": report["delivery"]["verified"],
    }
    if dry_run:
        checks["no_suspension"] = not intervals and not wake_events and abs(clock_gap) < TIMING_TOLERANCE
    else:
        checks["single_measured_suspension"] = bool(prompt and len(intervals) == len(wake_events) == 1
            and wake_events[0]["data"] == intervals[0] and abs(clock_gap - suspended) <= TIMING_TOLERANCE
            and suspended >= prompt["minimum_sleep_seconds"] - TIMING_TOLERANCE)

    wake = intervals[0]["detected_wall"] if len(intervals) == 1 else None
    sleep_start = wake - suspended if wake is not None else None  # Approximate, bounded by checkpoint cadence.
    if case == "wait":
        schedules = report["retry_schedule"]
        schedule = schedules[0]["data"] if len(schedules) == 1 else {}
        cooldown = accepted.get("not_before", {})
        due = cooldown.get("due_wall")
        checks["server_cooldown_honored"] = bool(due is not None and prompt and len(attempts) == len(requests) == 2
            and attempts[0].get("http_status") == 503 and attempts[0].get("failure_class") == "transient_status"
            and attempts[0].get("send_evidence") == "response_observed" and schedule.get("source") == "retry_after"
            and schedule.get("delay_seconds") == report["parameters"]["delay_seconds"]
            and schedule.get("failed_attempt") == attempts[0]["id"] and schedule.get("due_wall") == due
            and attempts[0]["request"] == accepted["request"] and prompt["wall"] < due <= accepted["started"]
            and requests[0]["payload_sha256"] == requests[1]["payload_sha256"])
        if not dry_run:
            checks["retry_admitted_on_wake"] = bool(due is not None and wake is not None and prompt
                and prompt["wall"] - TIMING_TOLERANCE <= sleep_start < due <= wake
                and 0 <= accepted["started"] - wake <= WAKE_ADMISSION_TOLERANCE)
    elif not dry_run:
        released = requests[0].get("reply_released_wall") if requests else None
        checks["suspended_with_reply_pending"] = bool(released is not None and wake is not None and prompt
            and prompt["wall"] - TIMING_TOLERANCE <= sleep_start < released
            and wake <= released + TIMING_TOLERANCE)
    return {"passed": all(checks.values()) and not report["errors"], "checks": checks}


def run_case(case, delay, dry_run, directory, revision, powercfg):
    wait_policy = WaitPolicy().model_dump()
    with LoopbackScript(case, delay, dry_run) as script:
        store, job, version, image, source = build_delivery(directory, {
            "endpoint": f"http://127.0.0.1:{script.server_port}{ENDPOINT_PATH}", "model": "offline-sleep-fixture",
            "context_tokens": 65536, "output_tokens": 2048, "wait_policy": wait_policy})
        job_id = job["id"]
        value = native("chat_completions", tool("edit_document", {
            "base_version": version, "expected_head": version, "claim": "complete"}, "save"),
            tool("report", {"state": "complete", "version_id": version,
                            "message": "Complete synthetic source saved."}, "report"))
        script.reply = b"".join(stream_frames("chat_completions", value))
        gate = {}

        def retry_sleep(seconds):
            if case == "wait" and not gate:
                request = store.records("request", job_id)[0]
                gate.update(not_before=request["not_before"], retry_schedule=request["retry_schedule"])
                remaining = gate["not_before"]["due_monotonic"] - SYSTEM_CLOCKS.monotonic()
                script.prompt("HTTP 503 Retry-After is recorded and the engine is waiting.",
                              max(MIN_SLEEP, ceil(remaining) + TIMING_TOLERANCE))
            time.sleep(seconds)

        runtime = Runtime(store, Nexus(store, lambda _: "fixture-only", clocks=SYSTEM_CLOCKS,
                                       retry_sleep=retry_sleep))
        server_thread = Thread(target=script.serve_forever, daemon=True)
        before = store.get("job", job_id)["active_seconds"]
        errors = []
        server_thread.start()
        start = sample(SYSTEM_CLOCKS.boot_identity)
        try:
            runtime.run(job_id)
        except Exception as exc:
            errors.append(f"Runtime: {type(exc).__name__}: {exc}")
        finally:
            end = sample(None)
            runtime.close()
            script.finished.set()
            script.shutdown()
            server_thread.join()
        end["boot_marker"] = Clocks().boot_identity

    final = store.get("job", job_id)
    events = store.events(job_id, limit=-1)
    delivery = {"verified": False}
    if final["status"] == "completed":
        try:
            delivery = verify_delivery(store, final, version, image, source, directory / "delivery.zip")
        except Exception as exc:
            errors.append(f"Delivery verification: {type(exc).__name__}: {exc}")
    report = {"revision": revision, "case": case,
              "parameters": {"dry_run": dry_run, "delay_seconds": delay, "wait_policy": wait_policy,
                             "minimum_sleep_seconds": MIN_SLEEP},
              "powercfg": powercfg, "clocks": {"start": start, "end": end},
              "active_seconds": {"before": before, "after": final["active_seconds"]},
              "suspended_intervals": store.records("suspended_interval", job_id),
              "resumed_after_sleep": [event for event in events if event["type"] == "resumed_after_sleep"],
              "retry_schedule": [event for event in events if event["type"] == "retry_scheduled"],
              "cooldown_at_wait": gate, "sleep_prompt": script.sleep_prompt, "http_requests": script.requests,
              "attempts": store.records("attempt", job_id), "requests": store.records("request", job_id),
              "job": {field: final[field] for field in ("id", "status", "stop_reason", "attempts", "head", "delivery")},
              "delivery": delivery, "errors": errors}
    report["verdict"] = evaluate(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=tuple(REAL_DELAYS))
    parser.add_argument("--delay-seconds", type=int, help="Override this case's scripted delay in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Use short delays and leave the machine awake.")
    args = parser.parse_args()
    if not SYSTEM_CLOCKS.windows:
        parser.error("The harness uses the Windows working and interrupt clocks.")
    delay = args.delay_seconds
    if delay is None:
        delay = (DRY_DELAYS if args.dry_run else REAL_DELAYS)[args.case]
    maximum = (Limits().max_server_wait_seconds if args.case == "wait" else WaitPolicy().first_progress_seconds - 1)
    if not 1 <= delay <= maximum:
        parser.error(f"This case needs a delay between 1 and {maximum:g} seconds to stay within its request policy.")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    powercfg = sleep_capability()
    runs = Path(".local/test-runs").resolve()
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(mkdtemp(prefix=f"net-01-{args.case}-{stamp}-", dir=runs))
    path = directory / "report.json"
    print(f"Report: {path}", flush=True)
    report = run_case(args.case, delay, args.dry_run, directory, revision, powercfg)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{'PASS' if report['verdict']['passed'] else 'FAIL'}: {path}", flush=True)
    return 0 if report["verdict"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
