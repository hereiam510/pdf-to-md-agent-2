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

NET-01 passed offline closeout based on the [T6 integration](#t6--offline-integration), the [F09 repair checks](#t6a--retry-cooldown-inheritance) and the [final-revision check](#t6b--final-revision-suite-run). Real Windows sleep and wake remain with [T7](tickets.md#t7--real-windows-sleep-and-wake-check). Live route testing requires its own selection.

**Earlier T6 evidence.** The Python suite ran 1,879 cases and passed 1,852. The targeted rerun passed all 94 selected cases. JUnit identity comparison confirmed that those 94 cover all 27 earlier failures. The 61-case NET-01 matrix included Windows loopback refusal, jittered backoff during simulated suspension and the rejected-reply Continue path under both frozen policies.

The earlier complete desktop run passed 113 of 118 cases. All five earlier failures passed their focused reruns covering diagnostics, streaming and task settings. The development build also passed the NET-01 desktop wake/cooldown and loopback termination/export tests. The full desktop run used a 240-second Playwright timeout after earlier fixture timeouts. The application's deadlines stayed the same.

TypeScript checking, the development build, the frozen-engine startup/TLS/XMP smoke checks and repository documentation checks passed at T6. The local logs under `build/net-01-*.log` retain the whole-run results and reruns.

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

**Disposition.** On 2026-11-14 the user agreed with all four findings. See [T6a for F09](#t6a--retry-cooldown-inheritance), [T6b for RV1](#t6b--final-revision-suite-run) and [T6c](tickets.md#t6c--draft-pull-request) for publication. RV2 and RV3 keep the revisit conditions above.

## T6a — Retry cooldown inheritance

**NET-01-F09 fixed at `42f8c8e`.** The continuation receipt already stores the first successor's revision. `Runtime.prepare` carries over its `not_before` when that revision matches the request being frozen. Normal response repair, compaction repair and successful compaction advance the revision. They can still carry the original continuation message into new input. Nexus enforces the first successor's cooldown at admission, and Runtime retains the existing limit on response corrections.

- The two `test_retry_cooldown_applies_only_to_first_successor` cases failed with the added tests against the original runtime (`b67edf3`, `pytest -q tests/engine/execution/test_network_recovery.py -k cooldown_applies_only`). Both correction requests inherited the old `not_before`. Local JUnit: `build/net-01-t6a-before-20261114-113458.xml`.
- With the fix, both cases admit the first successor only after the renewed cooldown following a simulated restart. They reopen an accepted text-only successor with a changed or missing boot marker. Re-entry admits the correction immediately with no inherited `not_before`, keeps the Retry note, and preserves the original request, successor and receipt. Each case reopens and exports the saved two-page synthetic document and verifies the source text, image and ZIP member bytes.
- `pytest -q` on `tests/engine/execution/test_network_recovery.py`, `tests/engine/execution/test_continuation.py` and `tests/engine/context/test_compaction_recovery.py` passed 111 cases, with zero failures or skips. That includes the 61 existing NET-01 cases and two new regressions. Local JUnit: `build/net-01-t6a-focused-20261114-113534.xml`.

**Documentation impact.** The [Q3 contract](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) now states where cooldown inheritance ends. [N4](spec.md#n4--pause-and-the-retry-action) already binds the delay to the first successor's admission. The [execution guide](../../guides/EXECUTION_AND_DELIVERY.md#implemented-continuation-boundaries) still describes the receipt transition and feedback used by both request kinds. The README Retry instructions still apply. Stage C's remaining acceptance and the work register's selection stay governed by their existing conditions.

## T6b — Final-revision suite run

**NET-01-RV1 closed.** The checks below ran on the clean implementation revision `42f8c8e`.

- `.venv\Scripts\python.exe -m pytest tests/engine --junitxml=build/net-01-t6b-engine-42f8c8e-20261114-113715.xml` passed all **1,879** engine cases in 32m 39s, with zero failures, errors or skips. The earlier Python run also included four desktop-helper cases. A separate `pytest -q tests/desktop/test_workspace_hashes.py` on the same revision passed all four. Its JUnit report is `build/net-01-t6b-desktop-helpers-42f8c8e-20261114-121021.xml`.
- `pnpm build` passed TypeScript checking and built the development app. `pnpm test:desktop network-retry.spec.ts` passed both tests in 50.1 seconds. The loopback run verified recovery after a server restart and engine termination, the saved version reopening, and a byte-verified ZIP. Retained local evidence: `.local/test-runs/net-01-t6b-42f8c8e-20261114-113715/`. The build and test logs are `build/net-01-t6b-desktop-42f8c8e-20261114-113715-build.log` and `build/net-01-t6b-desktop-42f8c8e-20261114-113715.log`.
- `.venv\Scripts\python.exe tools/docs/check_docs.py` passed. The final records were checked again after this write.

## Review of the closeout at `b3eed35`

Standalone review on 2026-11-14 of `28cd1df..b3eed35` (T6a–T6c). No code was changed.

- **T6a.** The fix in `Runtime.prepare` carries the receipt's `not_before` only while the state revision equals the receipt's successor revision. In `runtime.py`, only `repair`, `tools` and `resume_pending` advance the revision, and `coordinate` and the context-update recovery keep it. So the first successor freezes at the receipt revision and always inherits the cooldown, whether it is a normal request or a compaction. Every later request, including a correction or the request after a compaction, freezes without it. The regression case failed before the fix and passes after it, as recorded in [T6a](#t6a--retry-cooldown-inheritance). The Q3 contract sentence matches the behavior.
- **T6b.** `e9bbdb8` and `b3eed35` change only records, so the 1,879-case engine run and the Electron network tests at `42f8c8e` cover the code on the PR head. RV1 is closed.
- **T6c.** [Draft PR #2](https://github.com/hereiam510/pdf-to-md-agent-2/pull/2) is open against `master` at `b3eed35`, which matches the local branch. It is mergeable and has no review yet. The repository runs no CI checks, so the evidence for the PR is the local record above. The description accurately states the problem, the changes, the offline evidence and the open items (T7, live route, RV2, RV3).
- Rerun at `b3eed35`: `test_network_recovery.py`, `test_continuation.py` and `test_compaction_recovery.py` passed 111 of 111 (JUnit, 284 s).

**Verdict.** No new findings. NET-01 is offline-accepted on the PR head. What remains before NET-01's Windows acceptance is [T7](tickets.md#t7--real-windows-sleep-and-wake-check). T7 has no prepared harness yet: a local scripted server, a fixture task and a capture of `suspended_interval`, the active-time totals and the exported result.

**Disposition.** The user agreed on 2026-11-14. The harness, real runs and merge are planned as [T7a, T7b](tickets.md#t7--real-windows-sleep-and-wake-check) and [T8](tickets.md#t8--mark-pr-2-ready-and-merge).
