# Network failure handling: discussion

## Current question and authority

2026-11-14, Asia/Singapore. After the [post-merge recommendation](ASSET_REFERENCES.md#next-step-recommendation-after-the-merge), the user said: "i think we need to establish the handling of network problems, before entering stage B". This set the direction for a [Stage C](../PHASE_PLAN.md#c-continue-through-ordinary-interruptions) network increment before the next Stage B batch. Interrupted OCR and scripts ([R03](../WORK_ITEMS.md#runtime-and-engineering-inventory)) are a separate interruption family.

The [runtime contract](../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) owns the effective rules. The [NET-01 tickets](../batches/NET-01/tickets.md#planning-basis-and-authority) own implementation authority.

## Baseline before NET-01

The model request path is `Nexus.send` in [nexus.py](../../src/pdfmd/nexus.py). It uses `httpx` 0.28.1 with HTTP/2, `trust_env=False` and no redirects. Each frozen request records a `replay_policy` (`replay_unknown`, `max_attempts_per_request`) that later settings cannot change. Task defaults are no automatic transport retry and no unknown-outcome replay (`replay_unknown=false`, one attempt per request). The desktop offers a checkbox for bounded replay when creating a task.

| What happened | Recorded as | Recovery available at the baseline |
| --- | --- | --- |
| HTTP error status received (for example 408, 429, 5xx, 401) | Request `http_error`; the error body is withheld to protect credentials ([R04](../reviews/RUNTIME_FINDINGS.md#r04--http-errors-lose-diagnostic-body-and-have-no-automatic-retry)) | Explicit Continue creates a new request identity with continuation feedback. Nothing is automatic, and `Retry-After` is not read. |
| Connection refused, DNS failure, connect timeout or pool timeout | `stop_cause` such as `connect_timeout` or `transport_error`, but the request status is `unknown` | Only replay, if the task was created with replay enabled. Ordinary Continue cannot move an `unknown` request to a new identity. With default settings the task has no supported way to continue. |
| Connection dropped or timed out after sending (read error, incomplete stream, idle or deadline timeout) | Request `unknown`; received bytes are kept | Same as above. The interrupted-compaction action covers only compaction requests. |
| Malformed or rejected complete reply | Request `rejected` | Explicit Continue, plus the existing automatic response repairs. |

Observed incidence: the [A02 large run](../batches/R01CAL-A02/verification.md#t2-results-and-operational-boundaries) ended on an HTTP 408 at 107.7 seconds, before the local 180-second deadline, with no usage or body. No dropped-connection or connect failure is recorded in a live run in this repository. How often each class happens on the user's network and Nexus route is unknown.

### NET-01 — a request that never left the machine is treated as an unknown outcome

`httpx.ConnectError` and `httpx.ConnectTimeout` mean the connection was never established, so the provider never received the request. The current code classifies them like a mid-response drop: status `unknown`. With default settings, re-entry stops with "Configured replay is disabled or exhausted. Remote completion and cost are unknown." That message is untrue for this case, and the task cannot continue. A short Wi-Fi drop or a stopped local Nexus proxy at the moment of a send is enough to strand a task. This is a supported reading of the source; it has not been reproduced in a run here. Severity P2 for Stage B autonomy: it blocks delivery after an ordinary interruption with no cost uncertainty to justify the stop.

## Official guidance checked

- **httpx 0.28.** Transport `retries` covers only `ConnectError` and `ConnectTimeout`. The documentation directs read/write errors and status codes such as 503 to a general retry mechanism. [Transports](https://www.python-httpx.org/advanced/transports/)
- **LangGraph 1.2 `RetryPolicy`.** A node retry re-runs the whole node, with at-least-once semantics, and discards graph writes from the failed attempt. Defaults are 3 attempts, 0.5 s initial interval, factor 2, 128 s cap and jitter. By default it retries httpx exceptions only for 5xx. It has no `Retry-After` support. Side effects in the node must be idempotent. [Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)

Implication: the app already has an idempotent durable boundary for model sends (frozen request bytes, durable attempts, an accepted reply wins over a new send). Whichever retry mechanism is chosen must go through that boundary, so consumed attempts and allowances stay truthful.

## Failure classes and the proposed treatment

The handling should follow what is actually known about the request, not the exception type alone.

| Class | Known about the provider | Proposed default |
| --- | --- | --- |
| **Not sent**: connection refused, DNS failure, connect timeout, pool timeout | Did not receive the request | Retry automatically with backoff. Record the attempt as unsent. This needs no unknown-cost permission. |
| **Told to wait**: 429, or 503 with `Retry-After` | Refused the request (overclaim, corrected in the [review reconciliation](#independent-review-and-reconciliation): retry is justified, zero upstream work is not proven) | Wait for the stated time (bounded), then retry automatically. |
| **Possibly processed**: 408, 500, 502, 504, or a drop or timeout after sending | May have generated and counted usage | Open choice A below. |
| **Configuration error**: 400, 401, 403, 404, 413, 422 | Rejected by the provider or proxy | No retry. Stop with an actionable message. Never relabel this as context overflow. |
| **Long outage**: automatic retries exhausted | Unknown or unreachable | Stop with all work preserved, a "network unavailable" reason and a one-click Retry. |

Every class keeps the existing rules: shared request and active-time allowances, Stop takes effect during a backoff wait, an accepted reply always wins, no duplicate tool execution, and nothing is hidden in nested SDK or proxy retries.

## Mechanism options

1. **Bounded retry inside the existing send boundary (recommended).** Extend `Nexus.send` and its re-entry gate with the classification above, a retry budget per request and `Retry-After` handling. Waits poll Stop and active time like the existing request waits. Restart during a wait resumes from the durable attempt record. This follows the httpx guidance and keeps one owner for attempts and cost truth.
2. **LangGraph `RetryPolicy` on the model node.** This is framework-native, and node re-entry would reach the same durable gate. It cannot honor `Retry-After`, and its sleep is outside the app's Stop and active-time accounting. ~~Retries would also re-run the request preparation before the gate.~~ (Corrected in the [second review](#second-review-corrections): `prepare` is a separate graph node, so a `model` node retry does not rerun it.) It could serve generic node faults later.
3. **Explicit user action only.** Add a **Retry request** action for normal `unknown` requests, like the interrupted-compaction action, with no automatic retry. This is the smallest change, but it needs the user at every network blip, against the "little handling" goal.

Options 1 and 3 combine naturally: automatic bounded retry first, then the explicit Retry action after a long outage.

## Open choices for the user

- **A. Possibly processed failures.** Retry automatically (for example up to two retries) and record the possible duplicate generation and unknown usage, or stop and ask? On the current subscription route a duplicate costs quota rather than a known fee. Recommended: automatic, bounded, and visible in the activity log.
- **B. Long outages.** After the automatic retries, stop and wait for the user's Retry, or keep waiting for the network inside the task's active-time allowance? Recommended: stop with a one-click Retry, which keeps waits bounded and visible.
- **C. Error diagnostics (R04).** Keep only an allowlisted set of safe fields (status, `Retry-After`, request ID, and the error type and code from a JSON body), never the arbitrary body. Recommended: yes, as part of this increment.
- **D. Defaults for new tasks.** Make bounded retry the new default and keep a setting to turn it off? Existing frozen requests keep their recorded policy.
- **E. Which failures have you actually seen?** Wi-Fi drops, the local proxy stopping, 429 rate limits, 5xx errors, slow replies, or the laptop sleeping. The answer sets priority and the live acceptance case.

## Planned acceptance (sketch)

Offline, through the real `Nexus.send` path, with httpx `MockTransport` and a local fault server: connection refused, DNS failure, connect timeout, 429 with and without `Retry-After`, 503, 408, 502, 401, a reset in the middle of a stream, an idle timeout, Stop during a backoff wait, process restart during a wait, and allowance exhaustion during retries. Check that an accepted reply wins, attempts and allowances are recorded truthfully, no tool runs twice, the error body never appears in records, and saved, reopened and exported versions are unchanged. Then one desktop check with the network adapter disabled and re-enabled during a real task, which needs a separately authorized provider interval.

## User decisions (2026-11-14)

The user accepted the recommended answers to choices A to D and answered E:

- **A. Possibly processed failures:** retry automatically within a visible limit, recording the possible duplicate generation and unknown usage.
- **B. Long outages:** after the automatic retries, pause with all work preserved and offer a one-click Retry.
- **C. Error diagnostics:** keep only safe diagnostic information, never the arbitrary body. The [review reconciliation](#independent-review-and-reconciliation) refines what "safe" means.
- **D. Defaults:** bounded retry becomes the default for new tasks, with a setting to turn it off. Requests already frozen keep their recorded policy.
- **E. Observed problems:** Wi-Fi drops, the proxy stopping, server errors, slow replies and the laptop sleeping. Rate limits are not a problem the user sees. They still follow the general HTTP rule, but need no dedicated work or live case.

These decisions set the direction for a spec. They do not authorize implementation or a provider interval.

## Independent review and reconciliation

On 2026-11-14 the user supplied an independent source and documentation review (no tests or provider calls). It agreed with the direction and proposed four corrections. Assessment of each:

1. **Only connection-establishment errors prove "not sent" (agreed).** Missing response bytes alone do not prove the provider received nothing. `httpx.ConnectError`, `ConnectTimeout` and `PoolTimeout` mean no request bytes left on a connection. `WriteError` and `WriteTimeout` can happen part way through sending, so they stay in the possibly-processed class. The app creates a new `AsyncClient` for each attempt ([nexus.py](../../src/pdfmd/nexus.py)), so a stale pooled connection cannot disguise a sent request as a connect failure. Refinement from this review: httpx also reports TLS certificate failures as `ConnectError`. Those are configuration problems and must not be retried automatically, so the classification has to inspect the underlying cause, not only the exception type. [HTTPX exceptions](https://www.python-httpx.org/exceptions/)
2. **Retry eligibility is separate from outcome certainty (agreed; corrects this file's table).** A 429 or 503 justifies a retry but does not prove zero upstream work or usage. `Retry-After` is timing guidance, not a receipt. If the stated delay exceeds the allowed wait, pause instead of retrying early. [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
3. **The Retry action needs a durable recovery transition (agreed).** Extend the existing [explicit compaction recovery](../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) in `resume_pending` ([runtime.py](../../src/pdfmd/runtime.py)) to normal unknown requests. One action authorizes one successor request. The original request, payload, attempts and consumption stay unchanged. The choice is recorded before the graph advances, so a restart recovers it and a duplicate click cannot create a second successor. The alternative, granting more attempts to the same frozen request, was considered and rejected: it would change a request's recorded replay gate, which the adopted contract keeps immutable.
4. **Diagnostics need value validation, not only field names (agreed; replaces choice C's field allowlist).** A field such as `error.code` can carry arbitrary text. Record a locally defined failure category, an upstream code only when it matches a known set, a parsed `Retry-After` value, and a request ID only when it matches a strict format and length. Upstream messages stay excluded. (Scope narrowed in the [second review](#second-review-corrections): the exclusion applies to public diagnostics and non-success bodies, not to the private SSE error evidence the streaming contract keeps.)

The review also proposed three total attempts (the first plus two retries) with exponential backoff and jitter, which matches choice A. The UI shows the attempt number, the next retry time and the failure category. Retry waits count as active time; time paused for the user does not. Retry control belongs in the shared Nexus service and covers normal and compaction requests. httpx transport retries and LangGraph node retries must not become a second, hidden retry layer.

### Reconciled handling

| Situation | Handling | Recorded outcome |
| --- | --- | --- |
| Connection could not be established (refused, DNS failure, connect or pool timeout), including a stopped local proxy | Retry with backoff | Attempt marked unsent; no unknown-cost claim. A refused loopback connection reports that the Nexus proxy is not reachable at its host and port. |
| Connection lost, incomplete stream, timeout after sending, or a transient HTTP status (408, 429, 500, 502, 503, 504) | Retry within the limit; honor `Retry-After` up to the allowed wait, otherwise pause | Possible duplicate generation and unknown usage retained |
| Authentication, certificate, configuration or invalid-request error (400, 401, 403, 404, 413, 422, TLS verification) | Pause with an actionable reason; never repeat unchanged input automatically | Category and validated code only |
| Automatic retries exhausted | Pause with work preserved and offer Retry, which creates one durable successor | Original request and consumption unchanged |
| Accepted reply already saved | Reuse it; send nothing | Existing settlement |
| User Stop or exhausted allowance | Stop retries and waits immediately | Existing stop reasons |

## Second review corrections

2026-11-14. The user supplied a second independent comment on this file (source and documentation only; no sleep test). Each point was checked against the repository:

1. **Sleep clock (confirmed).** The project's interpreter is Python 3.12.14, and `time.get_clock_info('monotonic')` reports `GetTickCount64()`. That tick count keeps running through sleep and hibernation, whereas [QueryUnbiasedInterruptTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttime) counts only time in the working state. So the current `ActiveTime` can charge sleep as active time, and request timers can expire on wake. The earlier candidate of comparing the wall clock with the monotonic clock does not work, because both advance during sleep. The direction is a sleep-excluding clock for active-time accounting, plus Electron [`powerMonitor`](https://www.electronjs.org/docs/latest/api/power-monitor) suspend and resume events to coordinate in-flight requests. How the two integrate still needs verification. `pyproject.toml` allows Python up to 3.14, and the monotonic clock's Windows implementation changed in 3.13, so the spec should name the clock explicitly rather than rely on `time.monotonic()`. (Third review: an interpreter upgrade would not help, because `QueryPerformanceCounter`, used from 3.13, also counts sleep.)
2. **Sleep handling depends on the state (agreed).** It is not one classification:
   - sleeping during a backoff wait creates no new failed attempt;
   - a reply already accepted and saved still wins on wake;
   - only an unresolved in-flight request takes the uncertain-outcome retry path;
   - a stopped or paused task stays stopped or paused.

   A measured suspended interval is different from the existing [unmeasured crash tail](../design/RUNTIME_AND_DELIVERY.md#active-time-measurement-and-unmeasured-intervals). Neither silently consumes the active-time allowance.
3. **Streaming is already the default for new connections (agreed; corrects the earlier slow-reply question).** [WaitingSettings.tsx](../../src/renderer/features/settings/WaitingSettings.tsx) sets 600 seconds to first progress, 300 seconds between progress and no total cutoff. Saved routes keep their settings, so the T5 runs used the A03 non-streaming 180-second policy they inherited. Streaming shows whether progress was observed. It cannot prove a generation has stalled, because buffering or hidden reasoning can be silent. The real spec question is whether an existing task's future requests may change wait policy, while frozen requests keep theirs. (Third review: the adopted contract already allows this, so it is not an open question.)
4. **Diagnostics keep a preservation exception (agreed).** The [streaming contract](../design/STREAMING_RECEIVE.md#accepted-result-settlement) keeps original SSE error bytes from an HTTP-success stream as private evidence. That stays. Arbitrary messages are excluded from public diagnostics, and non-success HTTP bodies stay withheld. A request ID that passes a format check is still not proven free of sensitive data, so it stays a private diagnostic field unless the spec shows a reason to display it.
5. **Unsent attempts count against existing limits (agreed; answers the earlier open question).** Each admitted connection or send attempt consumes the per-request and task attempt allowances, as now, even if it fails before sending. It is recorded as `unsent` and never shown as billed inference. This bounds repeated connection failures with no new budget. Waiting and reopening consume no attempt.

Also corrected: a `model` node retry does not rerun `prepare`, which is a separate node in [`build_graph`](../../src/pdfmd/runtime.py). Nexus stays the retry owner because it owns durable attempts, acceptance and cancellation. Offline fixtures can establish most recovery behavior. Real sleep and wake needs its own observed case.

## Earlier spec questions (superseded 2026-11-14)

Preserved as first written. The [second](#second-review-corrections) and [third](#third-review-corrections) review corrections answer or replace these items; the [current questions](#questions-for-the-spec) list what remains.

- **Laptop sleep.** `ActiveTime` and the request waits use `time.monotonic()`. Whether that clock advances during Windows sleep on the pinned Python build needs a check. If it does, a sleep in the middle of a request could be charged as active time and could expire the request deadline or idle timer on wake, turning a possibly completed reply into an unknown outcome. Candidate approach: detect suspend and resume (for example Electron `powerMonitor` events in the desktop process, or a jump between the wall clock and the monotonic clock), record the suspended interval as unmeasured rather than active, and treat the interrupted request as a connection lost after sending.
- **Slow replies.** A timeout on a slow reply is a possibly-processed failure, so retrying it can repeat a generation that was still running. Streaming progress waits already separate "slow but alive" from "stalled". The live route used so far is non-streaming with a 180-second deadline, where the two look the same. The spec should decide whether conversions should use the streaming route by default, and how a deadline timeout counts toward the retry limit.
- **Unsent attempts and allowances.** Decide whether an attempt that was never sent counts toward the per-request attempt limit and the task's request allowance, or only toward its own backoff limit. It is recorded either way.
- **Existing HTTP-error path.** A request with status `http_error` currently cannot be replayed; only an explicit Continue creates a successor. Transient statuses need to reach the retry path, while configuration errors keep the explicit route.
- **Live acceptance.** One authorized desktop interval with the network adapter turned off and on during a send, the local proxy stopped and restarted, and a sleep and wake during a request.

The planned offline acceptance above also gains these cases: a duplicate Retry click, an accepted reply saved immediately before a crash, a TLS certificate failure, and a `Retry-After` longer than the allowed wait. Recovery is checked through the saved, reopened and exported output, with no duplicated local effects and no reset of consumption.

## Third review corrections

2026-11-14. The user supplied a third independent comment (source and documentation only; no application or sleep test). Each point was checked:

1. **Changing an existing task's wait settings is already supported (confirmed).** The [settings contract](../design/RUNTIME_AND_DELIVERY.md#existing-task-settings-and-active-time-accounting) lets a stopped task change `wait_policy`, and the change applies to newly prepared normal and compaction requests. Frozen requests keep their original route and wait policy. Saving settings sends nothing and grants no replay permission. The spec reuses this unchanged.
2. **A real sleep test needs no model run (agreed).** Windows suspend and resume can be exercised with the desktop app connected to a local scripted server. That checks clock accounting, event handling, retry limits and saved-output recovery without provider calls. A later live Nexus check would add route-specific behavior separately. Putting the laptop to sleep is disruptive, so the user chooses the test window.
3. **Separate time meanings (agreed).** The sleep-excluding clock governs active-time consumption only. It does not replace every timer. A server-requested delay is real elapsed time: if `Retry-After` asks for 60 seconds and the laptop sleeps for five minutes, the delay has passed and is not restarted on wake. Interrupted requests follow their own rules (below). Microsoft documents that [`QueryPerformanceCounter`](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps) also counts standby, hibernate and connected standby, so the Python 3.13 clock change does not solve this.
4. **Diagnostic boundary (agreed).** The rule is "excluded from public diagnostics". Private retained evidence, including the SSE error bytes the streaming contract keeps, stays inspectable through the deliberate raw-evidence access. Keeping a newly captured request ID private does not by itself justify capturing it; the spec must justify any new capture or leave it out.
5. **Current questions only (agreed).** The earlier question list is kept above as history. The section below lists only the remaining work.

## Questions for the spec

The retry-then-pause direction, the attempt limits, the diagnostic boundary and the existing wait-settings rule are settled. The [NET-01 draft spec](../batches/NET-01/spec.md) (2026-11-14) answers the items below and adds the fourth review's clarifications; it leaves two [decisions to confirm](../batches/NET-01/spec.md#decisions-to-confirm). The remaining design work was:

- **Sleep and wake coordination.**
  - Use a sleep-excluding clock (`QueryUnbiasedInterruptTime`) for active-time consumption, and record a measured suspended interval separately from the unmeasured crash tail.
  - Use Electron `powerMonitor` suspend and resume events to coordinate the engine, and define how the engine learns of them.
  - Define per-state rules on wake: backoff wait, accepted reply, in-flight request, stopped or paused task.
  - Decide which timers use elapsed real time (a server-requested delay) and which use active time.
- **Durable retry scheduling.**
  - Record each scheduled retry (attempt number, reason, earliest next time) so a restart during a wait resumes it without an extra attempt.
  - Make Stop and the allowances end a wait immediately.
  - Show the attempt number, next retry time and failure category in the desktop app.
  - Cover normal and compaction requests in the shared Nexus service.
  - The Retry action after exhaustion creates one durable successor, extending the explicit compaction-recovery transition.
- **Transient HTTP failures through the same policy.**
  - Route 408, 429, 500, 502, 503 and 504 to automatic retry, even though they are currently stored as `http_error`, which only an explicit Continue can follow.
  - Keep configuration errors, including TLS verification failures inside `ConnectError`, on the explicit route.
  - Record validated diagnostic categories and codes only.
- **Acceptance.**
  - Offline fault fixtures first, through the real send path.
  - Then a real Windows sleep and wake against a local scripted server, in a test window the user chooses.
  - A live Nexus check of route-specific behavior is a separate, later selection.

The planned offline acceptance above also gains these cases: a duplicate Retry click, an accepted reply saved immediately before a crash, a TLS certificate failure, a `Retry-After` longer than the allowed wait, and a sleep that outlasts a server-requested delay. Recovery is checked through the saved, reopened and exported output, with no duplicated local effects and no reset of consumption.
