# NET-01 verification

[Spec and acceptance](spec.md#acceptance) · [Tickets](tickets.md#sequence-and-dependencies)

## T1 — Windows clocks and active time

On Windows 10 build 19045 with Python 3.12.14, the no-sleep probe read working and interrupt clocks as 94,999.0214518 seconds each and obtained the startup marker `windows-startup:6467:639300964757914923`. The initial `kernel32` lookup for `QueryInterruptTime` failed on this host. The real-time API set lookup worked. The [execution guide](../../guides/EXECUTION_AND_DELIVERY.md#implemented-task-settings-and-active-time) describes the bindings and fallback. The simulated workbench case excludes both one and ten seconds of suspension and records the ten-second interval.

## T2 — Failure classes and diagnostics

The [NET-01 graph cases](../../../tests/engine/execution/test_network_recovery.py) use synthetic replies and a saved two-page PDF with a rendered figure. They verify per-attempt send evidence and unknown usage, retain success-stream prefixes, and check that credential-like error text stays out of the object store. The diagnostic tests shorten the production five-second bound to exercise expiry without a slow fixture. The fixed allowlist, 16 KiB bound, Stop and status retention are tested separately from reply acceptance.

## T3 — Scheduling and response waiting

The same graph cases use controllable working, monotonic, wall and interrupt clocks. They exercise both deadline domains, including forward/backward wall jumps, reboot and a missing boot basis. The task retains its original attempt count through waits and admits the next attempt against the remaining delay and current task allowances. Simulated sleep advances retry delays and preserves response waiting time in both streaming and legacy modes.

## T4 — Explicit recovery

The graph tests fault after the continuation receipt, reopen and recover it, and replay the same Retry choice. They check exactly one successor with current settings, a preserved original request and cooldown carry-over. A local acceptance staged before interruption wins without redispatch. Configuration and native validation cases exercise explicit Continue.

## T5 — Desktop recovery

The [loopback desktop case](../../../tests/desktop/specs/network-retry.spec.ts) disconnects the local server during a send, restarts it, clicks Retry through the real Electron bridge and terminates the engine during a persisted wait. After reopening it verifies the same input is resent, an HTTP 401 uses Continue, a duplicate Retry creates no successor, and a delayed success finishes the task. The first successful run took 54.5 seconds. It reopened the saved synthetic document and verified the ZIP's source text and exact member bytes. The first attempt at the test opened the activity snapshot before the retry event committed. The task view now displays the current retry schedule directly and the historical activity snapshot retains its explicit refresh boundary.

## T6 — Offline integration

The NET-01 matrix passed all 61 cases at `01c546d`. The following table maps each acceptance case to its check.

| Case | Check in the graph suite |
| --- | --- |
| A1, A2, A4 | `test_retry_preserves_payload_and_delivered_version` |
| A3 | `test_retry_preserves_payload_and_delivered_version`, `test_stream_break_or_incomplete_prefix_preserves_evidence` |
| A5 | `test_configuration_requires_continue` |
| A6 | `test_retry_after_forms` |
| A7–A9, A15, A15b | `test_retry_receipt_cooldown_and_current_policy` |
| A10 | `test_legacy_frozen_request_never_gets_new_automatic_policy` |
| A11 | `test_wait_respects_controls_and_sleep_elapsed_time` |
| A12 | `test_wait_restart_uses_interrupt_clock` |
| A13, A14 | `test_attempt_recovery_distinguishes_admission_dispatch_and_acceptance` |
| A16 | `test_compaction_retry_uses_shared_gate` |
| A17 | `test_wait_respects_controls_and_sleep_elapsed_time`, `test_receive_clocks_at_exchange_start`, `test_tool_sleep_is_excluded_from_active_time` |
| A18 | `test_configuration_requires_continue` and `test_http_diagnostics_are_isolated` |
| A18b | `test_http_diagnostics_are_isolated` |
| A19 | `test_receive_clocks_at_exchange_start` |
| A20 | `test_complete_rejection_requires_continue` |

### Regression findings

- **NET-01-F01.** An initial retry admission cleared previous response and stream pointers, hiding earlier bytes from the recovery inspector after a later attempt produced no body. Preserve request-level diagnostic pointers and keep attempt pointers attributed only to their owning attempt. The earlier-attempt diagnostic and desktop attribution tests cover this.
- **NET-01-F02.** A local exception after a stream chunk commit left the reconstructed raw object without its request/attempt pointers. Publish proven pointers while leaving the admission unresolved. The durable-suffix test covers this.
- **NET-01-F03.** Test fixtures that meant to exercise pre-NET-01 recovery inherited new defaults. Mark their frozen records with the historical policy or explicitly configure the intended new policy. Continue tests now use a configuration error. The legacy deadline tests expect `read=None` and independently check the frozen write/pool timeout and the local deadline under C1.
- **NET-01-F04.** Actual Windows loopback refusal reached HTTPX through an AnyIO wrapper that suppressed display of the underlying exception context. The classifier now walks both exception links and nested exception groups. A loopback port reserved without a listener reproduced the issue and verified the corrected proxy wording.
- **NET-01-F05.** The transport group passed 780 cases and failed 20 stream-item cases on the revised rejection wording. The restored wording identifies the absence of a complete valid reply. The affected 24-case whole/chunked stream matrix passed on rerun. The diagnostics/documents group passed 347 cases and failed three one-attempt fixture assertions because the fixtures allowed automatic retry. Those three cases passed after setting their retry policy explicitly.
- **NET-01-F06.** The observer clock fixture patched process monotonic time instead of injecting the working clock. Two trial fault-injection hooks also required the ordinary freeze call shape. The test now injects the execution clock, the ordinary freeze call keeps its existing arguments, and the trial HTTP 400 check verifies its configuration classification and the independent overflow evidence gate. All four cases passed on rerun.
- **NET-01-F07.** Desktop diagnostic fixtures assumed one timeout attempt, and Task limits submitted unchanged retry fields with unrelated edits. The fixtures now select one attempt explicitly, and the form submits retry fields when edited. Both protocols passed each rerun.
- **NET-01-F08.** A cold Chat Completions streaming fixture reached its held progress boundary after the assertion timed out. The test now allows 45 seconds for that observation. The server held the same boundary, and both streaming protocols passed on rerun.

### Documentation impact

The [runtime contract](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) owns the failure, policy and durable retry rules. Its [recovery](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) and [active-time](../../design/RUNTIME_AND_DELIVERY.md#active-time-measurement-and-unmeasured-intervals) sections explain the choice and sleep boundaries. The streaming and engineering guides, historical R04 entry, user instructions, and Stage C and work selection references were reconciled against these owners.

### Combined verdict

T6 passed on the combined offline evidence. The complete Python suite ran 1,879 cases and passed 1,852. The targeted rerun passed all 94 selected cases. JUnit identity comparison confirmed that those 94 cover all 27 earlier failures. The final 61-case NET-01 matrix included the separately exercised Windows loopback refusal, jittered backoff during simulated suspension and the rejected-reply Continue path under both frozen policies.

The complete desktop run passed 113 of 118 cases. All five earlier failures passed their focused reruns covering diagnostics, streaming and task settings. The final development build also passed the NET-01 desktop wake/cooldown and loopback termination/export tests. The full desktop run used a 240-second Playwright timeout after earlier fixture timeouts. The application's deadlines stayed the same.

TypeScript checking, the development build, the frozen-engine startup/TLS/XMP smoke checks and repository documentation checks passed. The local logs under `build/net-01-*.log` retain the whole-run results and reruns. Suite coverage comes from the full runs plus targeted checks of corrections, with no single all-green whole-suite run on the final revision. Real Windows sleep and wake remain with [T7](tickets.md#t7--real-windows-sleep-and-wake-check). Live route testing requires its own selection.

## Review of the implementation at `28cd1df`

Standalone review on 2026-11-14 of `ae579d0..28cd1df` against the [spec](spec.md) (N1–N7, C1, C2) and the [tickets](tickets.md). It read the clock, network, Nexus, runtime, server, Electron bridge and renderer changes. No code was changed. Checks run at `28cd1df`:

- `tests/engine/execution/test_network_recovery.py`, `tests/engine/execution/test_active_time.py` and `tests/engine/transport/test_request_deadline.py`: 96 of 96 passed (JUnit, 81.6 s).
- `tools/docs/check_docs.py`: no errors.
- Three reads of the real boot marker on this host: 0.45–0.93 s each, with the same value every time.

**Verdict.** The implementation matches the adopted design. It covers all five failure classes, send evidence, the frozen policy, cooldowns that are written even when no retry remains, the clock domains and restart fallback, Retry and Continue validated under the task lock, the Electron forwarding, and diagnostics that never persist the body. No finding blocks offline acceptance. One gap should close before a PR: there is no complete all-green Python suite run on the final revision.

- **NET-01-RV1 (verification gap, should close before a PR).** The full Python suite ran once, with 1,852 of 1,879 passing. After that run, `113f44b` changed `src/pdfmd/runtime.py` and `a5c10cf` changed the wording in `src/pdfmd/nexus.py`; only targeted reruns cover those changes. The [combined verdict](#combined-verdict) discloses this gap but does not name the commit the full runs used. Check: run `pytest tests/engine` once at the final revision, and record that commit with the pass and fail counts.
- **NET-01-F09 (defect, low).** `Runtime.repair` keeps `continuation_feedback`, and `prepare` copies the receipt's `not_before` into every request it freezes while that feedback stays set (`runtime.py`, the `freeze` helper in `prepare`). After a network Retry, a successor that needs a response correction re-inherits the original cooldown without its `satisfied_by`. In the same process or the same boot the cooldown has already passed, so nothing happens. After a reboot, or when the boot marker is unavailable, the fallback renews the full original delay, so the corrected request waits that long again and the wait counts as active time. That is late, not early, but needless. Direction: carry the cooldown only into the first successor, for example by skipping it once the successor has admitted an attempt. Check: a Retry followed by a missing-tool-call repair across a simulated boot change does not wait again.
- **NET-01-RV2 (efficiency, revisit on evidence).** While a network pause is shown, every 1.5-second job poll calls `Engine.network_recovery`. That builds a full `Runtime` (graph compile, SQLite connection, WAL pragma) under the engine guard and the task lock. It works, and the cost has not been measured. The renewal-on-view is intended, because it sets the replacement deadline when recovery begins. Revisit if UI latency or lock contention is observed.
- **NET-01-RV3 (robustness, low).** The boot marker spawns PowerShell (`Get-WinEvent`) with a 3-second timeout the first time it is needed. That can happen inside a running exchange (`record_headers` → `network.deadline`), where it blocks the event loop for that time. A timeout, a cleared System log or a changed marker falls back to the conservative rule, which is late, never early. Microsoft documents `Get-WinEvent`; nothing formally documents Kernel-General event 12 as a boot identity. The fallback contains both risks.

**Next step.** Run the full suite at the final revision (RV1) and record the result. Fix F09 within NET-01 scope with its check. Then prepare the PR. [T7](tickets.md#t7--real-windows-sleep-and-wake-check) still needs a user-chosen window. RV2 and RV3 stay recorded here without a scheduled remedy.

**Disposition.** On 2026-11-14 the user agreed with all four findings. F09 and RV1 are planned as [T6a](tickets.md#t6a--carry-the-retry-cooldown-only-into-the-first-successor) and [T6b](tickets.md#t6b--final-revision-suite-run), and the PR as [T6c](tickets.md#t6c--draft-pull-request). RV2 and RV3 keep the revisit conditions above.
