# NET-01 specification: network failure handling

[Tickets](tickets.md) · [Discussion](../../discussions/NETWORK_RECOVERY.md#questions-for-the-spec) · [Register](../../WORK_ITEMS.md#runtime-and-engineering-inventory) · [Stage C](../../PHASE_PLAN.md#c-continue-through-ordinary-interruptions)

## Status and authority

Draft prepared 2026-11-14 (Asia/Singapore) at the user's request ("prepare the spec"). The direction, attempt limits, diagnostic boundary and Retry transition come from the [user decisions](../../discussions/NETWORK_RECOVERY.md#user-decisions-2026-11-14) and three reconciled reviews in the [network discussion](../../discussions/NETWORK_RECOVERY.md). The fourth review comment (2026-11-14) added the clarifications on clock meaning, the status list and attempt states that are written into N2, N1 and N3 below.

**Revision 2 (2026-11-14).** A fifth review comment found five problems in revision 1. Each was checked against the code and corrected here:

- The restart delay was not immune to clock changes (N2).
- Admission recorded `sent=true` before anything was sent (N3).
- Retry could bypass a server-requested delay (N4).
- Diagnostic body reads had no time bound (N6).
- N1 misdescribed how rejected replies are handled.

C1 was revised to the reviewer's recommendation, which also covers httpx's own timers. The revised C2 drops the 30-second wake cutoff and limits the 2-second threshold to reporting. Earlier revisions were not committed to Git. Whether they can be recovered exactly from conversation records or other sources has not been checked. The revision summaries are not exact snapshots.

**Revision 3 (2026-11-14).** A sixth review comment recommended the revised C1 and C2 and found these remaining problems, all corrected:

- A server cooldown must persist even when no automatic retry remains (N3, A15b).
- The record of revision 1 was wrong (corrected above).
- Planned tests were worded as if already run (C1, A19).
- C1's detection-time statement was too narrow, and the response-wait timers keep their existing starting points.
- The restart fallback now sets one replacement deadline, with the same wording in N2 and N4.

**Adopted 2026-11-14.** After the design review ended with a recommendation to adopt, the user confirmed C1 and C2 as revised in [decisions to confirm](#decisions-to-confirm) ("Confirm and plan tickets"). This spec is now the adopted target for NET-01. Everything not stated here is ordinary implementation freedom. Adoption and ticket planning authorize no implementation, provider call or sleep test; implementation needs its own request. The [tickets](tickets.md) own execution. When implementation begins, the adopted rules move into the [runtime contract](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) and this spec links to them.

## Outcome

A conversion continues through ordinary network problems without the user's help, and pauses with a one-click Retry when it cannot. The problems the user named are Wi-Fi drops, the local proxy stopping, server errors, slow replies and the laptop sleeping. Records stay truthful about what was sent, what may have been generated and what was consumed.

This closes [NET-01](../../discussions/NETWORK_RECOVERY.md#net-01--a-request-that-never-left-the-machine-is-treated-as-an-unknown-outcome) and the diagnostic part of [R04](../../reviews/RUNTIME_FINDINGS.md#r04--http-errors-lose-diagnostic-body-and-have-no-automatic-retry) as the first [Stage C](../../PHASE_PLAN.md#c-continue-through-ordinary-interruptions) interruption family, before the next Stage B batch.

## Baseline

`master` at merge commit `e60fa00`. The relevant code:

- [`nexus.py`](../../../src/pdfmd/nexus.py): `Nexus.send` (re-entry gate, attempt admission, failure classification) and `exchange`;
- [`runtime.py`](../../../src/pdfmd/runtime.py): `resume_pending` and the explicit compaction recovery;
- [`active_time.py`](../../../src/pdfmd/active_time.py) and [`waiting.py`](../../../src/pdfmd/waiting.py);
- [`schema.py`](../../../src/pdfmd/schema.py): `Limits`;
- [`server.py`](../../../src/pdfmd/server.py): the start/continue API;
- the desktop task view and settings in [`main.tsx`](../../../src/renderer/main.tsx).

Pinned versions are unchanged: Python 3.12.14, httpx 0.28.1, LangGraph 1.2.16 and Electron 45.0.0.

## Scope

**In scope:** normal and compaction model requests sent through the shared Nexus service; failure classification; automatic bounded retry; durable retry scheduling; pause and the Retry action; Windows sleep and wake during a run; safe diagnostics for failed requests; desktop display and settings; offline and local-server acceptance.

**Out of scope:** interrupted OCR and scripts ([R03](../../WORK_ITEMS.md#runtime-and-engineering-inventory)); dedicated rate-limit work (the user does not see rate limits, though 429 follows N1); automatic resumption of a paused task when the network returns; non-Windows clock behavior ([XPLAT-01](../../WORK_ITEMS.md#context-capability-and-delivery-work), which keeps today's clock there); a live Nexus interval.

## Preserved guarantees

These existing rules stay in force and the acceptance checks protect them:

- An accepted reply saved locally always wins over a new send ([Q3](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery)).
- A frozen request's bytes, route and `replay_policy` never change. Settings changes apply to newly prepared requests only ([settings contract](../../design/RUNTIME_AND_DELIVERY.md#existing-task-settings-and-active-time-accounting)).
- Each admitted attempt commits its consumption before dispatch. Consumption is never reset by restart, Retry or settings.
- No tool from a failed or unaccepted reply runs. No accepted tool runs twice.
- A failure never proves remote cancellation, zero usage or known cost. Nothing claims exactly-once remote generation.
- Non-success HTTP bodies are never persisted. SSE error bytes inside an HTTP-success stream stay private evidence under the [streaming contract](../../design/STREAMING_RECEIVE.md#accepted-result-settlement). Generic HTTP errors are never relabeled as context overflow.
- Stop and the task allowances interrupt any wait promptly.
- One retry owner: httpx transport retries and LangGraph `RetryPolicy` stay unused for model requests.

## Design

### N1 — Failure classes

Nexus classifies every failed attempt by what is known about the request, not by the exception name alone.

| Class | Includes | Send evidence (N3) | Automatic action |
| --- | --- | --- | --- |
| `unsent` | `httpx.ConnectError` (except TLS verification), `ConnectTimeout`, `PoolTimeout`, DNS failure, refused connection | `not_sent` | Retry |
| `lost_after_send` | `WriteError`, `WriteTimeout`, `ReadError`, `RemoteProtocolError`, `ReadTimeout`, incomplete stream, request wait expiry, a process ending after admission with no recorded outcome | `may_have_been_sent`, or `response_observed` when headers or body bytes were received | Retry |
| `transient_status` | Exactly 408, 429, 500, 502, 503, 504 | `response_observed` | Retry, honoring `Retry-After` (N2) |
| `configuration` | TLS certificate verification failure (a `ConnectError` whose cause is `ssl.SSLCertVerificationError`), 400, 401, 403, 404, 413, 422, and every other non-success status, including 501 and 505 | `response_observed`, or `not_sent` for TLS | Pause; no automatic resend of unchanged input |
| `rejected_reply` | A complete HTTP-success reply that fails native validation | `response_observed` | Unchanged: the request becomes `rejected`, the run stops with `response_rejected`, and explicit Continue permits a successor. The automatic response repairs cover other cases (accepted text-only normal replies and invalid compaction handoffs) and do not apply here. |

The status list is explicit. Other 5xx codes such as 501 and 505 indicate unsupported functionality or protocol, so they pause. A refused connection to a loopback address reports that the Nexus proxy is not reachable at its configured host and port.

`transient_status` attempts keep request status `http_error` for history, but the re-entry gate routes them through N2 while retries remain. `configuration` attempts keep the existing explicit Continue route. This removes the current rule that every `http_error` can only be followed by an explicit Continue.

### N2 — Retry policy, delays and clocks

**Frozen policy.** Each newly frozen request records its retry policy with its `replay_policy`:

- `automatic_retry` (new tasks: on);
- `max_attempts_per_request` (new tasks: 3, which is the first attempt plus two retries);
- backoff of 2 seconds, doubling, capped at 60 seconds, with full jitter;
- `max_server_wait_seconds` (new tasks: 300).

These defaults are adjustable recommendations, not measured optima. Requests frozen before this change keep their recorded policy, so automatic retry does not apply to them. The existing `replay_unknown` setting becomes the user-facing **Retry automatically after network problems** checkbox for new tasks. With it off, every retryable failure pauses with Retry (N4).

**Delay sources.**

- Backoff gives a relative delay in seconds.
- `Retry-After` is parsed once, when the response arrives, into a relative delay:
  - a delay-seconds value is used as given;
  - an HTTP date is converted by subtracting the response `Date` header when it is present and valid, and otherwise by subtracting the local wall clock at receipt;
  - a negative result becomes zero;
  - a value that cannot be parsed is ignored in favor of backoff.
- A delay longer than `max_server_wait_seconds` is never shortened. The run pauses with reason `retry_wait_exceeds_limit` and consumes no attempt.
- Only the parsed number is kept, never the raw header.

**Clock meanings.** Three different times are in use, each with its own clock:

| Meaning | Clock | Sleep | System clock changes |
| --- | --- | --- | --- |
| Active-time consumption | Working-state time (N5) | Excluded | Not affected |
| Retry and server delays, measured in-process | Process monotonic clock (`time.monotonic()`; on Windows `GetTickCount64` in 3.12 and `QueryPerformanceCounter` from 3.13, both of which include sleep) | Included, so a delay that passes during sleep is over on wake | Not affected |
| A delay across a process restart, same boot | Durable deadline on the sleep-inclusive system interrupt-time clock (`QueryInterruptTime`), plus the OS boot identity | Included | Not affected: the remaining delay is the stored deadline minus the current interrupt time, floored at zero |
| A delay across a reboot, or when the stored basis is missing or invalid | None trusted | — | Conservative fallback: when recovery begins, set one replacement deadline equal to the full original delay counted from that moment, and persist it with the current boot identity. Later checks use that deadline and do not restart the delay. This can be late, never early. |

Revision 1 proposed recomputing the remaining delay from a wall-clock due time, clamped to the range 0 to the original delay. That did not preserve elapsed time. For a 60-second delay restarted after 20 seconds, a forward clock jump gives zero remaining (an early retry), and a backward jump gives 60 instead of 40. The interrupt-time deadline avoids both. `due_wall` is still recorded, but only to display the next retry time.

The boot identity comes from a documented OS source chosen during implementation. If the identity cannot be read or does not match, the fallback applies.

Request wait timers (first progress, idle progress, total deadline) follow the proposed decision C1 in [decisions to confirm](#decisions-to-confirm).

### N3 — Attempt states and durable scheduling

Three facts stay separate in records and in the UI:

Two durable records come before the next attempt:

- **Server cooldown.** Whenever a failed attempt carries a parsed `Retry-After`, Nexus writes `not_before` on the request in the same transaction that settles the attempt. It holds the delay, the interrupt-time deadline and boot identity (N2), and `due_wall` for display. This happens whether or not an automatic retry remains, and whether or not automatic retry is enabled. For example, a third attempt that returns 429 with `Retry-After: 600` still records a 600-second cooldown that the manual Retry in N4 must respect.

1. **Retry scheduled.** After a retryable failure with attempts remaining and automatic retry enabled, Nexus writes `retry_schedule` on the request in the same transaction. It holds:
   - the failed attempt ID and class;
   - the delay and its source (`backoff` or `retry_after`);
   - the interrupt-time deadline and boot identity (N2), and `due_wall` for display;
   - the next attempt number.

   The scheduled attempt is admitted no earlier than both its own deadline and any `not_before`.

   Waiting, restarting and reopening consume nothing.
2. **Attempt admitted.** When the delay is over, the existing admission transaction checks Stop and the allowances, increments the request and task attempt counts and records the attempt. Consumption still commits before dispatch.

   Each attempt carries a `send_evidence` value:
   - `may_have_been_sent`: set at admission and kept unless later evidence changes it. A crash right after admission leaves it here; nothing claims bytes left the machine.
   - `not_sent`: set only when N1 proves the connection was never established.
   - `response_observed`: set when status headers or body bytes were received.

   A write failure stays `may_have_been_sent`, because it does not show how much was transmitted. Retry eligibility is decided conservatively, but the historical record never claims more than the evidence. Every admitted attempt consumes the per-request and task allowances, including `not_sent` ones. A `not_sent` attempt is never shown as billed inference.
3. **Reply accepted.** This is the existing settlement and is unchanged.

The wait runs inside `Nexus.send` on the engine thread. It polls Stop and the active-time allowance at least once a second and counts as active time. If the process ends during a wait, re-entry finds `retry_schedule`, recomputes the remaining delay (N2) and waits without consuming an attempt. If the process ends after admission with the outcome unresolved, re-entry classifies that attempt as `lost_after_send`. Another send consumes another attempt, and earlier consumption stays recorded.

### N4 — Pause and the Retry action

The run pauses (job `blocked`) with all work preserved in four cases:

| Case | Stop reason |
| --- | --- |
| Attempts used up | `network_retry_exhausted` |
| Automatic retry turned off | `network_retry_disabled` |
| Server asked for a longer wait than allowed | `retry_wait_exceeds_limit` |
| A `configuration` failure | `provider_configuration_error` |

Each pause message names the class, attempts used and what may have been generated.

**Retry** (for `unsent`, `lost_after_send` and `transient_status` pauses) extends the [explicit compaction recovery](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) to normal requests:

- The desktop sends `retry_request` with the exact pending request ID. The server validates it under the task lock before changing anything.
- Runtime writes `continuation:<request>` with reason `explicit_network_retry`, authorization `{kind: human_network_retry, request}`, the original payload reference and the attempts. It writes this before advancing the graph.
- One choice authorizes one successor. The successor is prepared from current state with a short continuation note that no reply from the failed request was applied. It gets a fresh retry policy from the current task settings.
- A server-requested delay carries over. If the failed request has a `not_before` that has not yet passed (for example a 600-second `Retry-After` that caused a `retry_wait_exceeds_limit` pause), the server rejects an earlier `retry_request`. The desktop shows "Retry available at *time*" until then. The continuation receipt and the successor's first attempt also record and respect that `not_before`, so a fresh request identity never discards the delay. `not_before` is checked with the N2 restart rules: interrupt-time deadline in the same boot, otherwise the N2 fallback: one replacement deadline of the full original server delay, set when recovery begins.
- A duplicate click finds the receipt and does nothing. A crash after the receipt recovers the same transition. A locally accepted reply still wins.
- The original request, payload, attempts and consumption never change.

For `configuration` pauses, the existing explicit Continue stays, normally after the user corrects settings.

### N5 — Sleep and wake (Windows)

**Detection in the engine.** Detection happens after execution resumes. The engine sees that a suspension occurred and measures its duration. It records the time it noticed the suspension, not exact sleep start and end times, which a sampling interval cannot provide. The engine reads two Windows clocks through `ctypes`, with no new dependency:

- `QueryInterruptTime`, which includes sleep;
- `QueryUnbiasedInterruptTime`, which excludes it.

Both are available on Windows 10. The difference between their advances is the suspended time. The engine checks it at every active-time checkpoint and wait poll. All suspended time is excluded from active time, however short. A suspension of 2 seconds or more is also recorded as a `suspended_interval` (measured duration and the wall time when it was detected) with an activity event; shorter ones are not reported. The 2-second value is a reporting threshold only. Electron `powerMonitor` was considered as the primary signal and not chosen. The engine owns the accounting, runs without the desktop in API tests, and would otherwise need a cross-process event that could race the measurement. The desktop shows suspension from the engine's records.

**Active time.** On Windows, `ActiveTime` measures with `QueryUnbiasedInterruptTime`, so sleep is never charged. A `suspended_interval` is a measured exclusion. The existing `active_time_gap` stays reserved for genuinely unmeasured crash tails. Neither consumes the allowance. Other platforms keep `time.monotonic()` under XPLAT-01.

**Rules on wake, by state:**

| State when sleep began | On wake |
| --- | --- |
| Backoff or server delay | Sleep counted toward the delay (N2). If the delay is over, admit the next attempt now. No failed attempt is created. |
| Request in flight | Per decision C1: the remaining configured waiting budget resumes. A dead connection ends as `lost_after_send` and follows N2. |
| Accepted reply saved, settlement or graph advance pending | Existing re-entry; the accepted reply wins and nothing is sent |
| Tool running | Active time excludes the sleep; tool behavior is otherwise unchanged (R03 stays separate) |
| Task stopped, paused or not running | Nothing resumes |

### N6 — Diagnostics (R04)

For a failed attempt, records keep:

- the N1 class;
- the HTTP status;
- an upstream error type or code, only when it exactly matches a fixed set defined in code (otherwise `unrecognized`);
- the parsed `Retry-After` delay;
- the existing timing observations.

To read the type or code, Nexus may read up to 16 KiB of a JSON error body into memory, within a separate 5-second bound, and parse it there. The bytes are then discarded, never persisted or logged. This read is optional and isolated:

- The status, the class and any `Retry-After` value come from the headers and are recorded before the read starts.
- A slow, stalled, oversized, malformed or failed read ends the read, records the code as `unavailable` and changes nothing else. It never turns a known HTTP failure into a transport timeout and never delays recovery beyond the bound.
- Stop interrupts the read like any other wait. Upstream messages and request IDs are not captured; no need has been shown that would justify capturing them. Private SSE error evidence is unchanged and stays inspectable through the existing raw-evidence access.

### N7 — Desktop

- **While retrying:** activity shows "Attempt *n* of *m*", the failure class in plain words (for example "Connection lost after sending" or "Nexus proxy not reachable at 127.0.0.1:port"), and the local time of the next retry.
- **After a wake:** activity shows "Resumed after sleep (*duration*)".
- **When paused:** the task view shows the reason, attempts used, the note that a repeated request may duplicate upstream work, and a **Retry** button (or **Continue** for configuration errors). The button is disabled while a request is running.
- **Settings:** connection settings show the **Retry automatically after network problems** checkbox (default on) and the attempts per request.

## Decisions to confirm

Both confirmed by the user on 2026-11-14, as written below.

- **C1 — Request waiting across sleep (revised; recommended: resume the remaining budget).**
  - The response-wait timers in `RequestWait` (first progress, idle progress and total deadline) measure working-state time. A sleep neither expires nor extends them, and on wake the remaining configured budget continues. Their starting points do not change: first-progress and total waiting start when the exchange starts, as today, not after the upload finishes.
  - There is no extra cutoff after waking. Revision 1's 30-second no-byte cutoff is dropped: it would abandon a legitimate silent generation with hundreds of seconds left, and receiving bytes does not prove generation progress anyway.
  - httpx has its own connect, read, write and pool timers, measured with its own clock, which includes sleep. Changing `RequestWait` alone would not change them. Today the streaming path sets read to none, with connect up to 30 s, write 30 s and pool 30 s. The legacy non-streaming path sets all four to the route's `timeout_seconds`, with connect at most 30 s.
    - Under C1 the httpx read timeout is none in both paths, so `RequestWait` is the only response-wait timer.
    - Connect, pool and write stay as short httpx timers. If one of them expires because of a sleep, N1 classifies it (`unsent` for connect and pool, `lost_after_send` for write), and N2 retries.
    - Both paths must be verified by A19.
  - Tradeoff: a connection that died during sleep is detected only when the transport reports it or the remaining wait allowance runs out. With the streaming defaults, that is the remainder of the 600-second first-progress allowance if no progress has arrived yet, or of the 300-second idle allowance afterward. Custom settings and the legacy total deadline give different limits.
  - Alternative: end every in-flight exchange on wake and retry. That is simpler, but it always discards a reply that may still be arriving and spends an attempt.
- **C2 — Default numbers (revised).** Three attempts per request; backoff from 2 seconds, doubling, capped at 60 seconds, with full jitter; a 300-second maximum server-requested wait; a 2-second reporting threshold for detected suspensions (all suspended time is excluded from active time regardless); and a 5-second bound on the diagnostic body read. All are adjustable starting values, not measured optima.

## Acceptance

Run through the real `Nexus.send` and graph path, with the task's saved, reopened and exported output checked after recovery.

**Offline fixtures** use httpx `MockTransport`, a local fault server and a controllable clock. Each case checks its expected record and also that no tool runs twice, consumption is never reset, no error body is persisted and the selected version and ZIP are unchanged.

| # | Case | Expected |
| --- | --- | --- |
| A1 | Connection refused, then success | One `unsent` attempt and one accepted; both consume allowance; pause message absent; refused-proxy wording on loopback |
| A2 | DNS failure; connect timeout; pool timeout | Each classified `unsent`; retried |
| A3 | Reset mid-stream; incomplete stream; read timeout | `lost_after_send`; possible duplicate recorded; retried |
| A4 | 408, 429, 500, 502, 503, 504 | Retried; status kept |
| A5 | 501, 505, 400, 401, 404, 413, 422; TLS verification failure | Pause `provider_configuration_error`; no automatic resend |
| A6 | `Retry-After` as seconds and as an HTTP date, with and without a `Date` header; unparseable value | Correct delay; fallback to backoff |
| A7 | `Retry-After` above the limit | Pause `retry_wait_exceeds_limit`; no attempt consumed; not shortened |
| A8 | Three failures | Pause `network_retry_exhausted` after exactly three admitted attempts |
| A9 | Automatic retry off | First retryable failure pauses `network_retry_disabled` |
| A10 | Request frozen before the change | Keeps its recorded policy; no automatic retry |
| A11 | Stop and allowance exhaustion during a wait | Wait ends within one poll; no extra attempt |
| A12 | 60-second delay; process killed after 20 seconds; restart with no clock change, with the wall clock moved 100 seconds forward, and with it moved 50 seconds back; then a restart with a different boot identity or missing basis, followed by repeated checks | Same boot: the retry is admitted about 40 seconds after restart in all three cases, never earlier. Fallback: one replacement deadline 60 seconds from the start of recovery, not restarted by later checks. No attempt consumed by waiting. |
| A13 | Process killed after admission, before dispatch; and killed after dispatch before any reply | Both attempts recorded `may_have_been_sent` (never `not_sent`, never `response_observed`); re-entry classifies `lost_after_send`; the next send consumes a new attempt; earlier consumption kept |
| A14 | Accepted reply saved immediately before a crash | Re-entry settles it; nothing sent |
| A15 | Retry clicked once, twice and after a crash following the receipt | Exactly one successor; original request unchanged; the successor uses the current settings' policy |
| A15b | 600-second `Retry-After` in three situations: above the wait limit, on the third and last attempt (429), and with automatic retry disabled; Retry clicked at once, after a restart, after a simulated reboot, and after the delay | `not_before` recorded in all three situations; Retry rejected before it with "Retry available at *time*"; accepted after it; the successor's first attempt is no earlier than `not_before`; after the simulated reboot, one replacement deadline is set and not restarted by later checks |
| A16 | Compaction request failures | Same classes and retries as normal requests |
| A17 | Simulated suspension (controllable clock pair) during a backoff wait, during an in-flight request (C1), during a tool, and longer than a server delay; plus a 1-second suspension | Rules in N5; active time excludes every suspension, including the 1-second one; a `suspended_interval` is recorded only for 2 seconds or more; no failed attempt from sleep alone |
| A18 | Error body containing a credential-like string and arbitrary text | Not persisted; unrecognized codes recorded as `unrecognized` |
| A18b | Error headers then a stalled body; a body over 16 KiB; malformed JSON; Stop during the body read | Read ends within the 5-second bound or on Stop; status, class and `Retry-After` kept; code `unavailable`; never reclassified as a transport timeout |
| A19 | Sleep (simulated clock pair) during a streaming request and during a legacy non-streaming request whose reply arrives after the wake; and a short `timeout_seconds` legacy request without sleep | No response-wait timer expires because of sleep in either path (connect, pool and write timers may, and are then classified by N1); the reply is accepted; without sleep the legacy deadline still ends the exchange as `lost_after_send` |
| A20 | A native-validation failure in an HTTP-success reply | Unchanged: `rejected`, stop `response_rejected`, explicit Continue permits a successor; no automatic retry or repair |

**Desktop with a local scripted server** (no provider calls): stop and restart the server during a send, delay a reply, and kill the engine during a wait. Check the activity wording, Retry, Continue, settings and the saved, reopened and exported result.

**Real Windows sleep and wake** against the local scripted server, in a test window the user chooses: sleep during a backoff wait and during an in-flight request. Check `suspended_interval`, the active-time totals and recovery.

A live Nexus check of route-specific behavior is a separate, later selection.

## Documents to update during implementation

- [RUNTIME_AND_DELIVERY](../../design/RUNTIME_AND_DELIVERY.md): transport behavior, recovery boundaries, the Retry transition and active-time measurement.
- [STREAMING_RECEIVE](../../design/STREAMING_RECEIVE.md) where wait timers change under C1.
- The [execution guide](../../guides/EXECUTION_AND_DELIVERY.md) and the [integration guide's failure section](../../guides/INTEGRATION_AND_MODEL_BOUNDARY.md#11-concrete-integration-failures-and-the-retained-response).
- The R04 and NET-01 rows in [WORK_ITEMS](../../WORK_ITEMS.md#runtime-and-engineering-inventory).
- User-facing wording wherever settings or recovery are described.

## Readiness

Adopted and planned into [tickets](tickets.md) on 2026-11-14. The remaining details (field names, event names, the fixed upstream code set, fixture layout) are ordinary implementation choices within this design.
