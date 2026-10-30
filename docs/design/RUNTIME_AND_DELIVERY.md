# Durable runtime, continuation and delivery contract

## Basis for this revision

**Design identity:** Existing implemented contract; no separate historical design revision ID was recorded. This 2026-10-31 organization does not change adopted meaning, reset acceptance or create a newly adopted design revision. HEAD `ba8bad3` plus pre-existing uncommitted implementation is the entry worktree; see [current state](../CURRENT_STATE.md) for actual source/check identities and limits.

- **Applicable shared rules:** [requirements, captured edition](../history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md#acceptance-and-cost), [architecture, captured edition](../history/contracts/20261031_0157_ARCHITECTURE.md#responsibilities), and [preceding shared contract](../history/contracts/20261031_0157_CONTRACTS.md#q3-execution-recovery-and-delivery). Current topic rules below retain that edition's effective guarantees; today's global owners are reached through [the contract navigator](../CONTRACTS.md).
- **Choices and reasons:** [applicable decision entry](../decisions/REBUILD.md#reopening-policy) and [supporting discussion / contract closure](../decisions/INITIAL_CONTRACTS.md#q3-persistence-recovery-and-stop-contract). The detailed rule sections retain additional supporting entries; carried-forward choices remain applicable.
- **Verification:** adoption and local mechanism checks do not establish real-route compatibility, full fourteen-page fidelity or installed-product readiness. Follow the specific evidence entries below and [current verification](../CURRENT_STATE.md#verification-basis).

## Preserved source edition

The [entry source edition](../../docs/history/contracts/20261031_0157_CONTRACTS.md) preserves the preceding combined owner, its original statements and links to captured shared rules. Capture time `20261031_0157` is not a reconstructed older adoption time. Earlier version identities/snapshots unavailable in the records remain unclaimed. Later substantive changes must retain a version list and exact basis; unrelated cosmetic edits need no new version.

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

When bounded unknown-outcome model replay is enabled, it need not demand routine human proof that the remote generation stopped. Preserve possible duplicate inference, remote overlap and unknown usage/cost. Local abort, timeout or later success does not prove remote cancellation, original-generation continuation or zero cost. Eligibility/limits/default values need configuration. Old experiment values are not new defaults.

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

Chat Completions `tool_calls` may be absent, null, or an array. Absent/null means no executable calls; non-array non-null values are rejected. This interpretation does not rewrite the original native message. A nonempty text-only reply still follows its normal continuation or compaction contract; empty, refused, truncated or invalid calls do not become executable. See the official [Chat Completions response schema](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). Actual Nexus route validation remains separately recorded in CURRENT_STATE.

`catalog.sqlite` owns jobs, requests, attempts, operation receipts, committed context dispositions/effects, version registration and exports. `graph.sqlite` owns LangGraph checkpoints with synchronous durability. External immutable objects own the retained bytes. A cross-process file lock permits one task executor; manual editing uses the same lock. Independent jobs can run separately. These stores do not form a shared transaction.

Request identity is `<job>:<sequence>:<revision>`; member operation identity appends the accepted call index. Same-request re-entry uses frozen bytes. An accepted reply wins over a new send. One validated, idempotent Nexus settlement publishes an already saved `accepted:<request>` pointer and its actual attempt metadata in one catalog transaction, and also repairs older states whose pointer exists but attempt settlement is missing. Complete matching re-entry preserves original time/usage; contradictory provenance or known metadata is rejected without partial publication. Immutable evidence is saved first, outside this transaction. [The streaming design](STREAMING_RECEIVE.md#accepted-result-settlement) owns field authority and validation order. The dispatcher similarly reconciles `result:<operation>` before repeating work. A committed document can reconstruct its missing projection from the atomic original receipt. Captured context calls reconstruct the same ordered revision; only a committed Q2 settlement establishes its policy effect. An interrupted OCR/script operation without a settled result stops as `local_outcome_unknown`.

Each frozen request records `instruction_basis`, the hash of its ordered user amendments. Tool writes and head changes alone do not supersede their own batch. Before each uncompleted call, compare that basis with current amendments. When they differ:

- A completed operation returns its original receipt. Committed document/context effects are not undone or repeated; a saved context call without policy commitment is preserved as content and follows Q2's uncommitted-revision rules.
- An unstarted operation saves its original candidate and a durable `skipping` marker, then a paired result with `ok=false`, `skipped=true`, `execution="not_started"` and reason `superseded_by_user_amendment`. The candidate remains available for the agent's next decision. Every accepted call retains its native result pairing.
- A started operation without a recoverable receipt cannot be labeled unexecuted. It stops as `local_outcome_unknown`, with original files retained. This increment does not add general local-effect reconciliation.

After the batch settles, coordination restores committed context effects before evaluating outstanding intent. New amendments supersede an uncommitted revision without changing its original instruction basis. An old `report` receipt remains historical but cannot terminate new instructions. The next model request contains the latest amendments and outcomes; the agent chooses its method, tool and reconstruction scope. A plain Continue without an amendment resumes the original accepted batch. A same-text new amendment is still a new entry in the ordered amendment list.

The user's Start/Continue API permits a new request after `http_error` or `rejected` (including a complete transport carrying a truncated or malformed native reply). No calls from a rejected reply execute. An amended prepared request with no send attempts can also be superseded. Before graph advancement, an immutable `continuation:<old-request>` receipt stores the reason, diagnostic, retained native-response reference when available, attempt IDs and next revision. Graph state carries its reference; the supported LangGraph state-update path resumes through coordination before preparing new input. Re-entry recovers this recorded choice instead of requiring another click. Normal or compaction input carries the continuation feedback. Old requests, accepted history, candidates and versions remain available; old frozen bytes are never rewritten.

Plain process re-entry does not independently authorize a new request after an HTTP/rejected failure. Ordinary Continue and new amendments cannot move `unknown` or `in_flight` requests to a new ID: their frozen input and replay gate remain authoritative. The explicit unknown-compaction choice below is a separate, request-scoped authorization. Accepted local bytes take precedence over a fresh send. HTTP failure is not proof of zero cost or remote cancellation. Error bodies are withheld to protect credentials; status/diagnostic and unknown usage remain recorded.

**Explicit interrupted-compaction recovery.** The desktop offers **Resume context organization** only for the graph's current `unknown` compaction without locally accepted bytes or an already recorded continuation. The action sends `recover_compaction_request` with that exact request ID. Under the task lock, the server validates the choice before changing instructions/settings or clearing cancellation; a stale or unrelated ID cannot authorize another successor. This is a human decision to permit a replacement despite unknown upstream completion/cost, not a new automatic retry default or an assertion of remote cancellation. Normal unknown model requests and unknown local tool effects are outside this action.

Runtime records `continuation:<old-request>` with reason `explicit_compaction_recovery`, the selected request, its original payload reference and attempts, and the next history revision before advancing the graph. The old request, native/partial bytes, attempt, route and replay policy stay unchanged. A crash after the receipt but before its checkpoint recovers that same transition; after graph advancement a stale click cannot create another transition. Locally accepted bytes, including a response saved before its request pointer, win over replacement. The subsequent request is assembled and capacity-checked from current valid state. Context policy, saved documents, original receipts, correction episodes and consumed request/time allowances are not reset. One explicit choice permits one successor transition; if that successor is also unknown, ordinary Continue cannot recursively authorize another replacement. It requires a separate explicit choice. A successful replacement can then continue ordinary task execution.

Attempts and request-budget consumption commit before dispatch. Defaults are 80 model attempts, 7,200 active seconds, no automatic transport retry, and no unknown-outcome replay. Optional bounded transport replay applies only on re-entry. Each newly frozen request stores its `replay_policy` (`replay_unknown`, `max_attempts_per_request`) alongside its original route and payload. Its original gate governs subsequent attempts even if task-level values differ. Preserved pre-snapshot requests use the task recovery policy, which settings updates cannot change after any request is prepared. Normal, compaction and response-correction calls share current task total allowances. Active-time and cancellation checks also precede new tools and poll network/child-process waits. A local stop never establishes remote cancellation or known cost.


### Continuation feedback and delivery settlement

A no-tool answer is retained in history and schedules application continuation feedback. `report` selects `complete`, `partial`, or `waiting`; completion requires an explicit structurally complete saved version. An existing question must be reported as waiting, without inventing a user answer. The run stop reason, selected version's claim and export verification remain separate. Reopening does not itself resume or spend inference. The user can resume, reply, or export saved work.

`max_response_repairs` defaults to 2 and can be configured for new tasks in Connection settings; zero disables automatic corrections. It bounds correction requests following consecutive text-only normal replies and, independently, consecutive invalid handoffs. A settled normal tool batch clears the normal counter; a valid applied handoff clears the compaction counter. This is not a detector of semantic progress in arbitrary tool loops. The default is an adjustable engineering choice, not a measured optimal number or a quota on source-reading methods.

Each failure retains immutable `repair:<request>` feedback with its original accepted-response reference, diagnostic, count and basis (current document head and user amendments). Graph state carries a reference to that record. A correction changes context and receives a new request identity; it is not a resend of the accepted response. A restart or plain Continue does not reset the count. A new user amendment or edited document head starts a new correction episode at `prepare`; consumed attempts and time never reset. Exceeding the correction allowance yields `response_repair_exhausted`, preserves all work, and sends no further request. Reopening an exhausted episode alone cannot replenish it.

Handoff archives use `handoff:<request>` identities. `response_correction`, `context_compacted` and `request_continued` events have transactional deduplication receipts in `catalog.sqlite`. These cover replay after feedback/handoff/continuation persistence but before graph checkpoint completion. Applied handoffs recover their historical acceptance under Q2, including after a new amendment; global receipt immutability is not relaxed. The graph and catalog still do not share a transaction. General unknown-effect reconciliation and semantic no-progress detection remain separate. Capacity admission and independent pins are specified in Q2; they do not change recovery budgets or authorize new inference.

Export takes an immutable version and an explicit external ZIP path. It verifies actual ZIP names and bytes against that version, publishes without replacing an existing unrelated file, and reconciles an existing known export. Markdown, structured document, preview, manifest and assets come from that version. It needs no model call. The local filesystem must support the current exclusive hard-link publication operation; other filesystem publication strategies are unverified.

### Existing-task settings and active-time accounting

The authenticated `POST /jobs/{job}/settings` API changes a stopped task under the same cross-process task lock used by execution and editing. Start/Continue may also explicitly supply settings. Validation and a `task_settings` before/after record commit with the job update in one catalog transaction. Settings writes never change attempts, known active seconds, amendments, saved versions or frozen requests. Empty/omitted fields retain their effective values; invalid or disallowed changes reject the entire update.

Before any request is prepared, validated route/limit settings can be changed. Once a request exists or any attempt is consumed, only `context_tokens`, `output_tokens`, `image_tokens`, `timeout_seconds`, `wait_policy`, `max_requests` and `max_active_seconds` can change. Capacity and waiting settings apply to newly prepared requests; an existing request, including a never-sent prepared one, retains its original route, bytes and applicable replay limit. A waiting-policy change applies to both normal and compaction requests in that task until explicitly changed again; it is not a one-successor override. Changing settings sends nothing, does not authorize unknown-outcome replay, add per-request replay attempts or extend a correction episode. Protocol, endpoint, model, vision mode, generation parameters, recovery and correction policy changes are outside this existing-task update contract.

The desktop's **Task limits** dialog edits the supported capacity, waiting and budget values for the selected task and displays effective values and consumed usage. **Response waiting** selects streaming progress waiting or the legacy complete-response deadline. The legacy **Request deadline (seconds)** range is 1 through 3,600, including fractional seconds, with an unchanged legacy default of 180. The [streaming design](STREAMING_RECEIVE.md#streaming-progress-waiting) specifies the streaming defaults and independent timers. Connection settings supply defaults for an unconfigured task; Continue on a configured task uses its saved settings. Updating connection defaults does not silently replace them. GET job responses include effective route/limits, per-request frozen route/replay policy, and recorded unknown active-time intervals.

For a legacy route with missing/null `wait_policy`, the request deadline measures total monotonic elapsed time in the exchange; incoming body data does not restart it. The HTTP client uses the same frozen value for read/write/pool waits and `min(30, timeout_seconds)` for connection establishment. Stop and the persistent active-time budget remain independent interruption gates. A stopped task's new settings cannot mutate the selected old request: explicit unknown-compaction recovery uses its existing durable choice and prepares a distinct successor with the current route. Re-entry recovers that choice rather than granting another successor; locally accepted reply bytes still win.

Each new attempt has a small `transport` observation, separate from native-reply and handoff acceptance. It records `deadline_seconds`, `connect_timeout_seconds`, `settled`, `stop_cause`, safe exception type, header/first-body/last-body/complete-body elapsed seconds, received body bytes, `body_complete` and elapsed exchange seconds. The existing attempt `http_status` is set from observed headers even if the successful body later times out. A missing header time/status means not observed, not proof that the upstream sent nothing. Body counters measure decoded bytes received from a successful HTTP response, not wire bytes, tokens, generation progress or billed usage. Arbitrary non-success error bodies and authorization/header values are not stored.

`stop_cause` distinguishes `complete`, `http_error`, `request_deadline`, connect/read/write/pool timeout, other transport timeout/error, user Stop and active-time exhaustion. `body_complete=true` means successful-body EOF, not valid native output or an accepted handoff. False means successful-body reading started but did not finish; null means it did not start, including withheld HTTP-error bodies. First/last body times remain null when no nonempty success-body chunk was observed. Partial successful bodies remain archived and cannot execute tools. Unknown upstream completion, cancellation and usage remain unknown.

The deadline is checked at successful-body EOF as well as during pending waits. A late complete body cannot bypass the check because a synchronous segment prevented the polling task from running. Its exact bytes are retained as a complete `native_response` with `within_deadline=false`, without an accepted reply or executed tools; the request remains at the unknown-outcome recovery gate. It is not mislabeled as a partial body. This is local receipt/acceptance evidence, not a measurement of upstream completion time. A timely complete body followed by a transport-close failure is likewise preserved with its observed completeness; it does not silently create acceptance.

Legacy receive observations settle when the exchange exits and are saved with the attempt, not continuously journaled per chunk. A hard termination can leave the initial `settled=false` record; its initial null/zero fields are not a final measurement. Older attempts have no such observation and are not backfilled or reinterpreted. Accepted-response reconciliation recovers already committed acceptance without inventing missing transport observations. The [streaming design](STREAMING_RECEIVE.md#streaming-progress-waiting) specifies streaming observation checkpoints. A generic complete-response rejection and a complete but unacceptable handoff retain their existing failure/correction rules; changing a waiting policy neither accepts them nor resets their correction budget.

### Active-time measurement and unmeasured intervals

`active_seconds` is known monotonic elapsed time within active invocations, including model/tool waits, not CPU time or a provider bill. `ActiveTime` checkpoints at preparation, tool boundaries and request entry, and approximately once per second while polling network/child-process waits. Each short transaction adds the measured delta and advances `active_since`, the last durable wall-clock observation. In-process budget checks include the not-yet-checkpointed monotonic delta. Normal shutdown settles the remainder and clears the active marker. User waiting between invocations is not active execution.

After hard termination, restart atomically preserves any stale marker as an `active_time_gap` record and starts a new interval. The record retains both wall observations, their signed difference, `active_seconds=null` and `budget_policy=known_active_only`. The wall span is not an active-duration measurement; clock changes can affect it. All previously recorded consumption remains charged. The uncertain tail is neither charged as all downtime nor recorded as zero work. The budget uses known active seconds, and the UI/API disclose the unmeasured intervals. A crash during a long uncheckpointed in-process operation can leave a substantial unknown tail; this policy is not a strict lifetime-work or cost bound. Gap creation and marker replacement commit together, preventing duplicate settlement on re-entry.
