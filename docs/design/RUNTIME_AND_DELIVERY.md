# Durable runtime, continuation and delivery contract

## Basis for this revision

**Design identity:** Existing implemented contract; no separate historical design revision ID was recorded. This 2026-10-31 organization does not change adopted meaning, reset acceptance or create a newly adopted design revision. HEAD `ba8bad3` plus pre-existing uncommitted implementation is the entry worktree; see [implementation evidence](../history/IMPLEMENTATION_HISTORY.md) for actual source/check identities and limits.

- **Applicable shared rules:** [requirements, captured edition](../history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md#acceptance-and-cost), [architecture, captured edition](../history/contracts/20261031_0157_ARCHITECTURE.md#responsibilities), and [preceding shared contract](../history/contracts/20261031_0157_CONTRACTS.md#q3-execution-recovery-and-delivery). Current topic rules below retain that edition's effective guarantees; today's global owners are reached through [the contract navigator](../INDEX.md#initial-contract-basis).
- **Choices and reasons:** [applicable decision entry](../decisions/REBUILD.md#reopening-policy) and [supporting discussion / contract closure](../decisions/INITIAL_CONTRACTS.md#q3-persistence-recovery-and-stop-contract). The detailed rule sections retain additional supporting entries; carried-forward choices remain applicable.
- **Verification:** adoption and local mechanism checks do not establish real-route compatibility, full fourteen-page fidelity or installed-product readiness. Follow the specific evidence entries below and [current verification](../INDEX.md#find-by-topic).

<a id="preserved-source-edition"></a>
## Design versions

| Design identity / status | Meaning and saved basis |
| --- | --- |
| Observation-only time isolation, 2026-11-05 (implemented) | [Observer exception](#active-time-measurement-and-unmeasured-intervals), required by the separately authorized [observation-only invariant](CONTEXT_MANAGEMENT.md#observation-only-increment). The pre-observer runtime rule is retained in Git at `f9cabb9cee4161f5020fb3e57f2db960dd3b6f0c`; [reproduced failure and verification](../verification/20261105_0220_USAGE_OBSERVATION.md) and [implementation rationale](../decisions/CONTEXT_MANAGEMENT.md#observation-only-isolation-implementation-2026-11-05) bind this refinement. |
| Current carried-forward design | The adoption identity and consequential corrections are stated in the basis above. This documentation edit does not change their meaning or create a new behavioral revision. |
| Pre-filing source edition, captured 2026-10-31 01:57 UTC+08:00 | [Complete preceding owner](../../docs/history/contracts/20261031_0157_CONTRACTS.md). It retains the rule body and its captured shared requirements/architecture. Capture time is not original adoption time. |

Earlier identities not recorded remain unknown. For later material changes, preserve the preceding rule and its dependencies before replacement and extend this table; routine editorial changes retain the adopted identity.

## 3. Persistence, recovery and stop behavior

### State ownership

Use one authoritative record for each of these:

- Frozen model request and its attempts.
- Accepted native reply.
- Pending tool batch/progress.
- Operation receipt.
- Document version.
- Export intent.
- Effective compact context policy.

Exact record placement remains an implementation choice. A four-module/six-table sketch is not a complete specification. Specify which graph state is authoritative and which can be rebuilt from durable receipts.

Recovery of the same request uses the frozen input. A fresh context policy or newer head can influence a later request, not silently mutate the old request. Persist attempt/budget consumption before dispatch. Reuse a complete accepted saved reply before deciding to call the model again. Do not concatenate partial replies from separate attempts or execute incomplete JSON.

### Recovery boundaries

| Durable boundary | Required behavior on re-entry |
| --- | --- |
| A frozen request exists. No accepted reply exists. | Reconcile attempt/budget/cancellation state. Same-request replay keeps frozen input. Q3 permits a distinct request for explicit failed-request Continue or an amended, never-sent request. |
| A complete reply is accepted. Its tool batch remains unfinished. | Reconcile the same batch. New human amendments supersede unstarted calls with paired unexecuted receipts; completed effects remain. Do not silently omit calls or advance before settling them. |
| The tool committed. Its response/projection/checkpoint is missing. | Return/reconstruct the historical receipt and its necessary current-batch effects without repeating the local commit |
| The entire batch settled. Graph continuation remains incomplete. | Restore the necessary deterministic graph/context effects, then prepare the next request at a safe boundary |
| Local external effect remains unknown | Stop with preserved work and a specific unresolved outcome. Do not blindly replay an OCR/script/process operation. |

A `ToolMessage` alone may not reproduce a tool's graph `Command`/context-state effect. Conversely, replay must not reapply stale policy over a newer settled state. Reconciliation is scoped to the accepted pending batch and explicit effect identities. A call can finish after another call with a higher creation sequence. Creation order and `max(event_seq)` are not a completion timeline. Define causal/application progress rather than inferring it from wall-clock timestamps.

Graph checkpoints, SQLite commits and immutable external files do not form one atomic transaction. Define visibility and reconciliation at these limited boundaries. First-version single-writer recovery does not promise arbitrary historical-job migration, exactly-once remote generation or unconditional recovery from every hard crash.

### Shared limits and transport behavior

Normal and compaction sends use one durable budget/cancellation gate, including direct entry and resume paths. Limits survive restart and graph rollback. Distinguish request inactivity from whole-job active time. Define wait/backoff accounting. Do not reset attempts, turns or time allowances on resume or hide nested SDK/proxy retries.

Nexus owns network retry for normal and compaction requests. The attempt records `may_have_been_sent` at admission, `not_sent` when a connect/pool failure proves no send, and `response_observed` when headers arrive. TLS certificate verification is a configuration failure. Write/read failures, expired response waits, incomplete streams and unresolved admissions are `lost_after_send`. HTTP 408, 429, 500, 502, 503 and 504 are `transient_status`. Other non-success statuses are configuration failures. Complete rejected replies retain the existing validation and Continue path. An unresolved send can have unknown completion and usage, including after a successful retry.

New requests freeze `automatic_retry`, `max_attempts_per_request` and `max_server_wait_seconds` with the input and route. The defaults are on, three attempts and 300 seconds. Historical requests retain their recorded replay gate. Backoff uses full jitter from zero to the exponential ceiling (2 seconds initially, capped at 60). A valid `Retry-After` supplies a relative delay from delay-seconds or the HTTP date difference. A valid response `Date` takes precedence over the local receipt time for that difference. Negative delays become zero. Invalid values fall back to backoff.

Headers establish the status, class and server cooldown before the optional diagnostic read. The engine keeps only a fixed allowlisted JSON code/type, `unrecognized`, or `unavailable`. The read is Stop-aware and bounded to 16 KiB and five seconds. Error bodies, messages, request IDs and raw headers are withheld. A known status remains known if the read stalls or fails. A diagnostic label does not establish context overflow or remote settlement.

A parsed server delay creates `not_before` even when retry is disabled, exhausted or over the wait limit. A retryable settlement with an available automatic retry also commits `retry_schedule` before waiting. Retry uses process monotonic time in-process and the sleep-inclusive Windows interrupt clock on same-boot re-entry. With an untrusted basis it persists one replacement deadline for the full original delay. Wall time only supplies the display time. Waiting consumes active time, polls Stop and task allowances at least once per second and consumes no attempt. Admission consumes the attempt atomically and records any enforced cooldown. A server delay above the configured limit pauses without shortening the delay. Only Nexus schedules retries.

Streaming and non-streaming share accepted-response/tool/persistence semantics. Preserve native candidate information with safe handling of errors and sensitive fragments. A transport fragment is evidence, not automatically an executable native response. Respect explicit cancellation. Respect user questions. No routine reminder may override them.

### Stop, task completion and export

Execution stop reason, agent content-completion claim and package consistency are separate records. A question for the user can enter a waiting state. A second no-tool answer is not automatically a question. Bounded continuation feedback is now implemented as specified in Q3 below. It asks the model to express an existing necessary question through `report(waiting)` without assuming a user answer; it does not certify completion or require a conversion method.

Saved versions remain exportable by the host without further model use. Partial work retains a draft/partial label. Explicit version selection determines Markdown, JSON, HTML, assets and ZIP. Neither a mutable head nor a newly generated summary may change that selection during export.

Verify actual intended members and bytes. A manifest identity alone does not establish actual ZIP/file consistency. The export directory and ZIP are separate publication effects. A single rename cannot atomically publish both. Re-entry must preserve unrelated outputs and reconcile known output identities before repeating publication. A finalizer node cannot guarantee packaging after every crash/cancellation/exit.

### Local diagnostic read boundary

Task-bound finite activity pages expose stable global-sequence identity, task-filtered coverage and explicit refresh. Sequence gaps are not task event counts. The event boundary is neither a complete record-change cursor nor a cross-catalog/graph snapshot. Diagnostic reads preserve original databases/sidecars/files, invoke no execution/recovery authority, and expose refreshable stale/unavailable limits. Historical execution, usage, timing and graph unknowns remain unknown. Full/raw/field/range/native-pixel evidence access retains task/ref ownership validation. The [local API/lifecycle guide](LOCAL_DIAGNOSTICS.md#task-activity-and-local-diagnostic-api) explains implementation; no durable schema or acceptance/recovery semantics change.

### Desktop progress and process boundary

Persist important results/receipts. Allow coalescing or dropping obsolete progress events. A bounded queue cannot simultaneously promise lossless unlimited events and never block when the consumer stops. Avoid coupling durable tool completion to UI stdout consumption. A reconnecting UI should read committed state.

Protocol output and diagnostics require a deliberate process/channel boundary, but mandatory first-line `os.dup2` was not established as the universal remedy. Native libraries, callbacks, threads and process shutdown need proportionate implementation checks. These considerations do not require a new distributed infrastructure or a separate network research phase before document/context contracts can be written.


### Q3: execution, recovery and delivery

Chat Completions `tool_calls` may be absent, null, or an array. Absent/null means no executable calls; non-array non-null values are rejected. This interpretation does not rewrite the original native message. A nonempty text-only reply still follows its normal continuation or compaction contract; empty, refused, truncated or invalid calls do not become executable. See the official [Chat Completions response schema](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). Actual Nexus route validation remains separately recorded in [implementation evidence](../history/IMPLEMENTATION_HISTORY.md).

`catalog.sqlite` owns jobs, requests, attempts, operation receipts, committed context dispositions/effects, version registration and exports. `graph.sqlite` owns LangGraph checkpoints with synchronous durability. External immutable objects own the retained bytes. A cross-process file lock permits one task executor; manual editing uses the same lock. Independent jobs can run separately. These stores do not form a shared transaction.

Request identity is `<job>:<sequence>:<revision>`; member operation identity appends the accepted call index. Same-request re-entry uses frozen bytes. An accepted reply wins over a new send. One validated, idempotent Nexus settlement publishes an already saved `accepted:<request>` pointer and its actual attempt metadata in one catalog transaction, and also repairs older states whose pointer exists but attempt settlement is missing. Complete matching re-entry preserves original time/usage; contradictory provenance or known metadata is rejected without partial publication. Immutable evidence is saved first, outside this transaction. [The streaming design](STREAMING_RECEIVE.md#accepted-result-settlement) owns field authority and validation order. The dispatcher similarly reconciles `result:<operation>` before repeating work. A committed document can reconstruct its missing projection from the atomic original receipt. Captured context calls reconstruct the same ordered revision; only a committed Q2 settlement establishes its policy effect. An interrupted OCR/script operation without a settled result stops as `local_outcome_unknown`.

Each frozen request records `instruction_basis`, the hash of its ordered user amendments. Tool writes and head changes alone do not supersede their own batch. Before each uncompleted call, compare that basis with current amendments. When they differ:

- A completed operation returns its original receipt. Committed document/context effects are not undone or repeated; a saved context call without policy commitment is preserved as content and follows Q2's uncommitted-revision rules.
- An unstarted operation saves its original candidate and a durable `skipping` marker, then a paired result with `ok=false`, `skipped=true`, `execution="not_started"` and reason `superseded_by_user_amendment`. The candidate remains available for the agent's next decision. Every accepted call retains its native result pairing.
- A started operation without a recoverable receipt cannot be labeled unexecuted. It stops as `local_outcome_unknown`, with original files retained. This increment does not add general local-effect reconciliation.

After the batch settles, coordination restores committed context effects before evaluating outstanding intent. New amendments supersede an uncommitted revision without changing its original instruction basis. An old `report` receipt remains historical but cannot terminate new instructions. The next model request contains the latest amendments and outcomes; the agent chooses its method, tool and reconstruction scope. A plain Continue without an amendment resumes the original accepted batch. A same-text new amendment is still a new entry in the ordered amendment list.

The user's Start/Continue API permits a new request after a configuration failure or a rejected reply. No calls from a rejected reply execute. An amended prepared request with no send attempts can also be superseded. Before graph advancement, an immutable `continuation:<old-request>` receipt stores the reason, diagnostic, retained native-response reference when available, attempt IDs and next revision. Graph state carries its reference. Re-entry projects the receipt through coordination before preparing new input. Normal or compaction input carries the continuation feedback.

An unresolved admission or a scheduled retry re-enters the existing request and uses its frozen policy. Pauses use `network_retry_exhausted`, `network_retry_disabled`, `retry_wait_exceeds_limit` or `provider_configuration_error`. The first three expose **Retry**. The configuration pause exposes **Continue**.

**Explicit network Retry.** Under the task lock, `retry_request` must identify the current retryable paused request. A pending server cooldown blocks the action until its deadline. Runtime commits `continuation:<old-request>` with reason `explicit_network_retry`, the original payload and attempts, the human authorization and any applicable cooldown. The successor uses the current task state and retry settings, and its first admission also honors the cooldown. A repeat click or re-entry after the receipt grants no second successor. Locally accepted evidence takes precedence over replacement.

**Explicit interrupted-compaction recovery.** The desktop offers **Resume context organization** only for the graph's current `unknown` compaction without locally accepted bytes or an already recorded continuation. The action sends `recover_compaction_request` with that exact request ID. Under the task lock, the server validates the choice before changing instructions/settings or clearing cancellation; a stale or unrelated ID cannot authorize another successor. This is a human decision to permit a replacement despite unknown upstream completion/cost, not a new automatic retry default or an assertion of remote cancellation. Normal unknown model requests and unknown local tool effects are outside this action.

Runtime records `continuation:<old-request>` with reason `explicit_compaction_recovery`, the selected request, its original payload reference and attempts, and the next history revision before advancing the graph. The old request, native/partial bytes, attempt, route and replay policy stay unchanged. A crash after the receipt but before its checkpoint recovers that same transition; after graph advancement a stale click cannot create another transition. Locally accepted bytes, including a response saved before its request pointer, win over replacement. The subsequent request is assembled and capacity-checked from current valid state. Context policy, saved documents, original receipts, correction episodes and consumed request/time allowances are not reset. One explicit choice permits one successor transition; if that successor is also unknown, ordinary Continue cannot recursively authorize another replacement. It requires a separate explicit choice. A successful replacement can then continue ordinary task execution.

Attempts and request-budget consumption commit before dispatch. Defaults are 80 model attempts and 7,200 active seconds per task. Normal, compaction and response-correction calls share those totals. The [shared retry rules](#shared-limits-and-transport-behavior) govern per-request eligibility. Active-time and cancellation checks also precede new tools and poll network/child-process waits.


### Continuation feedback and delivery settlement

A no-tool answer is retained in history and schedules application continuation feedback. `report` selects `complete`, `partial`, or `waiting`; completion requires an explicit structurally complete saved version. An existing question must be reported as waiting, without inventing a user answer. The run stop reason, selected version's claim and export verification remain separate. Reopening does not itself resume or spend inference. The user can resume, reply, or export saved work.

`max_response_repairs` defaults to 2 and can be configured for new tasks in Connection settings; zero disables automatic corrections. It bounds correction requests following consecutive text-only normal replies and, independently, consecutive invalid handoffs. A settled normal tool batch clears the normal counter; a valid applied handoff clears the compaction counter. This is not a detector of semantic progress in arbitrary tool loops. The default is an adjustable engineering choice, not a measured optimal number or a quota on source-reading methods.

Each failure retains immutable `repair:<request>` feedback with its original accepted-response reference, diagnostic, count and basis (current document head and user amendments). Graph state carries a reference to that record. A correction changes context and receives a new request identity; it is not a resend of the accepted response. A restart or plain Continue does not reset the count. A new user amendment or edited document head starts a new correction episode at `prepare`; consumed attempts and time never reset. Exceeding the correction allowance yields `response_repair_exhausted`, preserves all work, and sends no further request. Reopening an exhausted episode alone cannot replenish it.

Handoff archives use `handoff:<request>` identities. `response_correction`, `context_compacted` and `request_continued` events have transactional deduplication receipts in `catalog.sqlite`. These cover replay after feedback/handoff/continuation persistence but before graph checkpoint completion. Applied handoffs recover their historical acceptance under Q2, including after a new amendment; global receipt immutability is not relaxed. The graph and catalog still do not share a transaction. General unknown-effect reconciliation and semantic no-progress detection remain separate. Capacity admission and independent pins are specified in Q2; they do not change recovery budgets or authorize new inference.

Export takes an immutable version and an explicit external ZIP path. Markdown, structured document, preview, manifest and assets come from that version. It needs no model call. Each attempt exclusively creates a short temporary ZIP in the destination folder, closes its writer, verifies its member names and bytes, and publishes by exclusive hard link. A known retry or concurrent attempt settles against matching members and bytes at the destination. An unrelated destination is preserved. When it appears during publication, the attempt retains its verified preparation and reports a conflict that names the destination and the retained file. Normal cleanup only targets the attempt's own temporary file. An unwritable destination produces a diagnostic naming the path. Filesystems without the required hard-link operation remain outside this verified route.

### Existing-task settings and active-time accounting

The authenticated `POST /jobs/{job}/settings` API changes a stopped task under the same cross-process task lock used by execution and editing. Start/Continue may also explicitly supply settings. Validation and a `task_settings` before/after record commit with the job update in one catalog transaction. Settings writes never change attempts, known active seconds, amendments, saved versions or frozen requests. Empty/omitted fields retain their effective values; invalid or disallowed changes reject the entire update.

Before any request is prepared, validated route and limit settings can be changed. Once a request exists or any attempt is consumed, capacity, response waiting, per-request retry settings and total request/time allowances can change. Capacity, waiting and retry changes apply to newly prepared normal and compaction requests. Existing requests, including prepared requests with no attempts, retain their route, bytes and policy. A settings change sends nothing and grants no recovery choice. Protocol, endpoint, model, vision mode, generation parameters, historical replay and response-correction settings require a task without a frozen request.

The desktop's **Task limits** dialog edits the supported capacity, waiting and budget values for the selected task and displays effective values and consumed usage. **Response waiting** selects streaming progress waiting or the legacy complete-response deadline. The legacy **Request deadline (seconds)** range is 1 through 3,600, including fractional seconds, with an unchanged legacy default of 180. The [streaming design](STREAMING_RECEIVE.md#streaming-progress-waiting) specifies the streaming defaults and independent timers. Connection settings supply defaults for an unconfigured task; Continue on a configured task uses its saved settings. Updating connection defaults does not silently replace them. GET job responses include effective route/limits, per-request frozen route/replay policy, and recorded unknown active-time intervals.

For a legacy route with missing/null `wait_policy`, the deadline starts at exchange entry and measures working-state time. Incoming bytes do not restart it. HTTPX has no read timeout; write and pool retain the frozen route deadline, and connect uses `min(30, timeout_seconds)`. The [streaming design](STREAMING_RECEIVE.md#streaming-progress-waiting) gives the corresponding progress waits. Changes to a stopped task's retry settings apply to newly frozen requests.

Each new attempt has a small `transport` observation, separate from native-reply and handoff acceptance. It records `deadline_seconds`, `connect_timeout_seconds`, `settled`, `stop_cause`, safe exception type, header/first-body/last-body/complete-body elapsed seconds, received body bytes, `body_complete` and elapsed exchange seconds. The existing attempt `http_status` is set from observed headers even if the successful body later times out. A missing header time/status means not observed, not proof that the upstream sent nothing. Body counters measure decoded bytes received from a successful HTTP response, not wire bytes, tokens, generation progress or billed usage. Arbitrary non-success error bodies and authorization/header values are not stored.

`stop_cause` distinguishes `complete`, `http_error`, `request_deadline`, connect/read/write/pool timeout, other transport timeout/error, user Stop and active-time exhaustion. `body_complete=true` means successful-body EOF, not valid native output or an accepted handoff. False means successful-body reading started but did not finish; null means it did not start, including withheld HTTP-error bodies. First/last body times remain null when no nonempty success-body chunk was observed. Partial successful bodies remain archived and cannot execute tools. Unknown upstream completion, cancellation and usage remain unknown.

The deadline is checked at successful-body EOF as well as during pending waits. A late complete body cannot bypass the check because a synchronous segment prevented the polling task from running. Its exact bytes are retained as a complete `native_response` with `within_deadline=false`, without an accepted reply or executed tools; the request remains at the unknown-outcome recovery gate. It is not mislabeled as a partial body. This is local receipt/acceptance evidence, not a measurement of upstream completion time. A timely complete body followed by a transport-close failure is likewise preserved with its observed completeness; it does not silently create acceptance.

Legacy receive observations settle when the exchange exits and are saved with the attempt, not continuously journaled per chunk. A hard termination can leave the initial `settled=false` record; its initial null/zero fields are not a final measurement. Older attempts have no such observation and are not backfilled or reinterpreted. Accepted-response reconciliation recovers already committed acceptance without inventing missing transport observations. The [streaming design](STREAMING_RECEIVE.md#streaming-progress-waiting) specifies streaming observation checkpoints. A generic complete-response rejection and a complete but unacceptable handoff retain their existing failure/correction rules; changing a waiting policy neither accepts them nor resets their correction budget.

### Active-time measurement and unmeasured intervals

`active_seconds` measures known working-state time within active invocations, including model, retry and tool waits. Windows uses `QueryUnbiasedInterruptTime`; other platforms keep `time.monotonic()`. At checkpoints and wait polls, the advance of `QueryInterruptTime` minus the working-clock advance measures suspension. Every suspension is excluded from active time. A measured interval of at least two seconds records `suspended_interval` and emits a wake event. Its wall time identifies detection, which occurs after execution resumes. The active-time transaction advances `active_since` and the known total together. Normal shutdown settles the remainder and clears the active marker.

For the explicitly supplied [observation-only usage observer](CONTEXT_MANAGEMENT.md#observation-only-increment), synchronous diagnostic compute/I/O is measured separately and excluded from ordinary active seconds. This preserves the observer's ordinary-path invariant: a slow or failed observer cannot itself exhaust the conversion allowance. The shared ActiveTime owner adjusts only its in-process mark; no configured limit or ordinary commit changes. Normal construction has no observer. [Mechanism and controlled-clock evidence](../guides/CONTEXT_AND_EVIDENCE.md#observation-only-usage-anchoring) explain the boundary; an interrupted diagnostic interval still follows the unknown-tail rule below.

After hard termination, restart atomically preserves any stale marker as an `active_time_gap` record and starts a new interval. The record retains both wall observations, their signed difference, `active_seconds=null` and `budget_policy=known_active_only`. The wall span is not an active-duration measurement; clock changes can affect it. All previously recorded consumption remains charged. The uncertain tail is neither charged as all downtime nor recorded as zero work. The budget uses known active seconds, and the UI/API disclose the unmeasured intervals. A crash during a long uncheckpointed in-process operation can leave a substantial unknown tail; this policy is not a strict lifetime-work or cost bound. Gap creation and marker replacement commit together, preventing duplicate settlement on re-entry.

## Acceptance and evidence correspondence

[Runtime](../../src/pdfmd/runtime.py) coordinates; [Nexus](../../src/pdfmd/nexus.py) owns frozen requests/attempts; [storage](../../src/pdfmd/storage.py) and the document core own committed facts; [active time](../../src/pdfmd/active_time.py) owns measured consumption. [Execution guidance](../guides/EXECUTION_AND_DELIVERY.md) explains the boundaries and reasons.

| Condition / guarantee | Discriminating check and expected result |
| --- | --- |
| Stop interrupts an accepted tool batch and the user later amends instructions | [Continuation tests](../../tests/engine/execution/test_continuation.py): reconcile committed effects once, retain receipts and candidates, skip obsolete unstarted calls, and do not let an old report complete new work. |
| A request is unknown or a local process has started without a known outcome | `test_unknown_outcome_cannot_acquire_a_new_id_or_reset_replay_limits` and `test_started_local_process_is_not_replayed_or_mislabeled_skipped`: preserve uncertainty and frozen policy; refuse unsafe replay. This refusal does not supply R03's still-missing general recovery capability. |
| A failed-response Continue receipt commits before its graph checkpoint | `test_continue_receipt_survives_checkpoint_gap_without_new_authorization`: reopen the same committed successor without minting another transition or resetting consumption. |
| Task limits change while a request is already frozen | [Settings tests](../../tests/engine/execution/test_task_settings.py): new requests use the new settings, frozen bytes/replay policy remain exact, invalid changes are atomic, and exhausted correction/replay episodes stay exhausted. |
| Restart finds an unfinished active-time interval | The settings stale-interval control and [active-time tests](../../tests/engine/execution/test_active_time.py): preserve known consumption and label an unmeasured tail; neither charge all downtime nor invent zero work. |
| Model budget is exhausted or work is partial | Existing continuation/settings delivery controls and [desktop continuation](../../tests/desktop/specs/continuation-workflow.spec.ts): reopen/edit/export the explicit saved version independently of inference, retaining scope and source/image bytes. |

Evidence is recorded in [continuation](../history/IMPLEMENTATION_HISTORY.md#continuation-and-integration-increment), [settings/time](../history/IMPLEMENTATION_HISTORY.md#phase-2-existing-task-settings-and-active-time), [organization regression](../verification/20261031_1646_PROJECT_ORGANIZATION.md) and [accepted-result settlement](STREAMING_RECEIVE.md#accepted-result-settlement). These local/synthetic results do not establish arbitrary power-loss safety, remote cancellation or general unknown-process recovery. R03 and broader R07 retain their [finding dispositions](../reviews/RUNTIME_FINDINGS.md#issue-navigation); no new execution is authorized by this correspondence.
