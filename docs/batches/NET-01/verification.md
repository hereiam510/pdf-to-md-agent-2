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

The focused graph suite passed all 58 cases. The following table maps each acceptance case to its check.

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
| A20 | `test_historical_policy_and_complete_rejection` |

### Regression findings

- **NET-01-F01.** An initial retry admission cleared previous response and stream pointers, hiding earlier bytes from the recovery inspector after a later attempt produced no body. Preserve request-level diagnostic pointers and keep attempt pointers attributed only to their owning attempt. The earlier-attempt diagnostic and desktop attribution tests cover this.
- **NET-01-F02.** A local exception after a stream chunk commit left the reconstructed raw object without its request/attempt pointers. Publish proven pointers while leaving the admission unresolved. The durable-suffix test covers this.
- **NET-01-F03.** Test fixtures that meant to exercise pre-NET-01 recovery inherited new defaults. Mark their frozen records with the historical policy or explicitly configure the intended new policy. Continue tests now use a configuration error. The legacy deadline tests expect `read=None` and independently check the frozen write/pool timeout and the local deadline under C1.
- **NET-01-F04.** Actual Windows loopback refusal reached HTTPX through an AnyIO wrapper that suppressed display of the underlying exception context. The classifier now walks both exception links and nested exception groups. A loopback port reserved without a listener reproduced the issue and verified the corrected proxy wording.
- **NET-01-F05.** The transport group passed 780 cases and failed 20 stream-item cases on the revised rejection wording. The restored wording identifies the absence of a complete valid reply. The affected 24-case whole/chunked stream matrix passed on rerun. The diagnostics/documents group passed 347 cases and failed three one-attempt fixture assertions because the fixtures allowed automatic retry. Those three cases passed after setting their retry policy explicitly.

### Documentation impact

The [runtime contract](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) owns the failure, policy and durable retry rules. Its [recovery](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) and [active-time](../../design/RUNTIME_AND_DELIVERY.md#active-time-measurement-and-unmeasured-intervals) sections explain the choice and sleep boundaries. The streaming and engineering guides, historical R04 entry, user instructions, and Stage C and work selection references were reconciled against these owners.

### Combined verdict

The 58-case NET-01 graph suite passed, plus the separate real loopback-refusal check. A 153-case targeted engine run passed, covering active time, acceptance settlement, task settings and compaction recovery. Fourteen transport and settlement checks passed after the pointer corrections, and six Retry and historical policy checks passed on the final code. All eight targeted desktop checks passed, including both protocols' historical compaction and earlier-attempt evidence cases, the wake/cooldown fixture and the loopback termination/export case. TypeScript checking, the development build and repository documentation checks passed. The frozen engine built at `61ae1f7` and passed startup, local TLS setup and the XMP worker relaunch smoke check.

Complete-suite verification remains open. The first broad runs started before the fixture and diagnostic pointer corrections. The desktop run also hit timeouts in existing Responses context-delivery cases. The subsequent all-tests desktop run uses a 240-second runner timeout, with no changes to the app's request deadlines. See the retained local logs under `build/net-01-*.log`. An all-green offline result remains necessary for T6. Real Windows sleep and wake remain with [T7](tickets.md#t7--real-windows-sleep-and-wake-check). Live route testing requires its own selection.
