# Execution, recovery, and delivery engineering handoff

This guide explains durable execution responsibilities, failure reasoning and considered Q3 options without requiring the original chat export. [The implemented contracts](../CONTRACTS.md#implemented-first-version-contracts) now select the exact first-version schemas and transitions; they supersede statements below that these choices remain open. Other example IDs, nodes and state labels remain explanatory notation. [CURRENT_STATE](../CURRENT_STATE.md) records verification and its limits.

[CONTRACTS](../CONTRACTS.md) owns the effective boundaries and [OPEN_QUESTIONS](../OPEN_QUESTIONS.md) states their closure conditions. [Document engine](DOCUMENT_ENGINE.md) explains content, editing, validation, and file/metadata commits. [Context and evidence](CONTEXT_AND_EVIDENCE.md) explains context policy, input selection, capacity, and compaction. [Integration](INTEGRATION_AND_MODEL_BOUNDARY.md) explains native protocols and framework wiring. The [detailed reference](../reference/03-documents-delivery-and-recovery.md) retains the proposal/correction chain. [Bundled source material](../reference/sources/INDEX.md) is optional audit evidence.

The preferred design uses a small Python LangGraph StateGraph, one shared Nexus request service, and a shared tool dispatcher. It also uses compact graph state, SQLite metadata, and immutable external content. These responsibilities may share one process. The graph provides control and checkpoint primitives. It does not atomically commit remote generation, filesystem results, SQLite changes, and its own checkpoint. The first-version recommendation uses one active writer per task rather than a general multi-writer branch system.

## Accepted-result settlement

`Nexus._settle_accepted` owns publication for normal send and local reconcile. It repairs both a missing request pointer and an already published pointer whose attempt was left unfinished by the earlier two-commit implementation. Changing only write order would move the partial-publication window. Independent send/reconcile patches would duplicate ownership, diagnostics and replay rules. One short catalog transaction now settles both metadata records, after immutable acceptance evidence has been saved. This is the bounded R13 correction, not an event journal or a transaction spanning files and graph checkpoints.

Evidence preparation precedes `BEGIN IMMEDIATE`. The deterministic `accepted:<request>` blob must have the right kind, task, request, unique member attempt and finite original `received_at`. The frozen-input descriptor/bytes, native descriptor/bytes and exact parsed accepted projection must agree. Legacy acceptance requires a complete `native_response`. Streaming requires a complete `raw_stream` linked to a complete `assembled_response` of the frozen protocol, both owned by the same request/attempt. `registration_only` partial preservation is ineligible. Reopen strictly verifies chunk order/files/checkpoint/aggregate through `read_stream`, replays the attempt-local decoder, compares the assembled native bytes and validates the parsed accepted projection. It never manufactures acceptance from terminal SSE or raw bytes alone. Normal send reuses only its freshly archived, strictly reconstructed stream descriptor to avoid a second constituent-file pass; descriptor equality and native/staging validation still apply. No file reads or decoder reconstruction occur inside the write transaction.

Inside the transaction, task-scoped row reads recheck current request/attempt IDs, member identity, eligible states, frozen route/input/replay fields and validated evidence/observation descriptors. A change between validation and publication is an explicit conflict, with no metadata writes. Publication merges only acceptance fields into current records so newer unrelated fields survive. Before publication, request diagnostic pointers may legitimately refer to an earlier failed attempt on this request; their field-specific kind and ownership are checked even when their descriptors were already loaded. Acceptance replaces these earlier diagnostic pointers while retaining their original blobs. A different pointer on the accepted attempt is a conflict; once the accepted pointer exists, conflicting native/stream pointers are also rejected. A different attempt's usage or a known contradictory usage/status/stream reference is never silently overwritten.

| Field | Authority and re-entry rule |
| --- | --- |
| Request `status`, `accepted_ref`, `response_ref`, applicable `stream_ref` | Validated accepted/native/stream identities, published together with the selected attempt. Frozen payload, replay policy, attempts and other current fields are preserved. |
| Attempt `status`, `usage` | Accepted staging must equal a fresh complete-native parse. Only its actual member attempt becomes accepted. Known prior usage must agree; missing known usage is filled; native unknown remains null. No budget or usage total is incremented during settlement. |
| Attempt `finished` | Fill a missing/null value from staging's original `received_at`. Preserve an existing finite historical finish time, including the older send-time value after staging. Never use reopen time. |
| `http_status`, `transport` | New staging retains the settled receive observation, including legacy non-streaming cleanup/deadline diagnostics. Older staging can use its same-attempt `stream_receive` observation. Existing settled diagnostics must agree with the available authority. Absent legacy diagnostics stay absent/unknown; acceptance does not invent HTTP 200 or cleanup success. |
| `started`, `remote_cancelled`, unrelated fields | Preserve current values. A missing cancellation value is recorded as unknown, never inferred from local completion. Other attempts and their unknown usage/cancellation remain untouched. |

Staging captures `received_at` with the sender's wall clock after complete native validation. It records the original acceptance-staging moment. Transport observations separately retain body/protocol elapsed timings. Recovery reads these saved facts; it makes no new measurement of the original reply's arrival or remote completion.

| Saved state | Recovery outcome |
| --- | --- |
| Complete valid staging, no pointer | Validate and atomically publish request plus its attempt. |
| Complete valid staging and pointer, attempt still `in_flight`/unknown or missing known usage/finish | Validate the same chain and repair that attempt, even though the pointer already exists. |
| Fully settled matching records | Return the same accepted result; do not write either record again or refresh time/usage. |
| Conflicting pointer, staging, member attempt, native/stream chain or known usage | Refuse explicitly; preserve files and current metadata for diagnosis. |
| No accepted staging/pointer, only complete-looking raw or terminal SSE | No acceptance is synthesized; the original frozen replay/unknown-outcome gate remains effective. |

The historical counterexample is staging → request-pointer commit → interruption before attempt commit. The old reconcile skipped this state forever because its repair gate required a missing pointer. The new common responsibility does not use that gate. An exception or abrupt own-process exit after the first metadata UPDATE now leaves both metadata records unpublished; independently committed staging remains available for later repair. A separate Runtime handoff validation is still necessary for compaction; native acceptance alone neither adopts context nor dispatches compaction tools.

This uses existing Python 3.12.14 / SQLite 3.53.1 and `Store.transaction`, without dependency or framework changes. Consulted official [Python 3.12 transaction control](https://docs.python.org/3.12/library/sqlite3.html#transaction-control) and [SQLite transaction semantics](https://www.sqlite.org/lang_transaction.html) support explicit transaction/rollback and current reads under `BEGIN IMMEDIATE`. Catalog atomicity does not imply file/graph atomicity or power-loss safety. [R13](../reviews/RUNTIME_REVIEW_2026-10.md#r13--accepted-result-settlement-consistency-selected-2026-10-28) owns evidence and limits.

## Implemented task settings and active time

Phase 2 addresses two observed failures: an existing task ignored explicit allowance/capacity changes, and a stale execution timestamp charged all offline time as active work. [The Q3 contract](../CONTRACTS.md#existing-task-settings-and-active-time-accounting) owns exact fields and semantics. The implementation retains the single-writer graph, frozen requests, exact originals and autonomous tool selection.

`Engine.configure` and Start/Continue share `_configure` under the cross-process task lock. A short catalog transaction validates the full merged settings, restricts changes after a request is frozen, records the before/after values, and writes the job. A failed validation changes nothing. The task's consumed attempts/time and saved work are not part of the settings patch. The Electron **Task limits** form submits explicit task values; Start uses global connection defaults only when that task has no route. This avoids silently reverting a saved per-task increase on the next Continue.

The later option-A increment adds an explicit request deadline to this same path. Its effect lasts for subsequent newly frozen requests in the task, including normal and compaction requests; no one-off override or global default update is involved. For example, saving 600 seconds leaves an old 180-second unknown request unchanged. Ordinary Continue still respects that old replay gate. A separately authorized exact-request recovery records its existing continuation choice, then prepares a new request with 600 seconds. Saving settings alone performs no inference and does not reset consumed time, attempts or correction episodes.

Nexus retains header status and bounded receive observations even when a later body wait fails. This distinguishes local total-deadline expiry, HTTP errors, client timeout classes, Stop and budget exhaustion without inferring upstream causation. Full HTTP-body receipt, valid native output, valid handoff application and correct saved conversion remain separate stages. [Q3](../CONTRACTS.md#existing-task-settings-and-active-time-accounting) owns the fields, partial-body privacy boundary and hard-termination limits. Existing automatic handoff corrections are unchanged: a future one-request diagnostic experiment must explicitly stop at its agreed boundary rather than assume invalid handoffs already stop automatically.

Three values must remain distinct: the task's latest capacity for future input, a pending request's original frozen route/input, and total task allowances. For example, raising context capacity from 65,536 to 131,072 changes the next newly prepared request, while an already prepared request keeps its original 65,536 configuration and exact payload. Raising total requests from 1 to 10 preserves the first consumed attempt and does not expand that request's original replay ceiling. `Nexus.freeze` snapshots replay policy; `send` reads that snapshot for replay eligibility and current job totals for whole-task admission. Existing pre-snapshot records retain the now-immutable task recovery policy. Supported settings changes cannot reopen an exhausted correction episode or unknown local effect.

`ActiveTime` measures a running invocation with `time.monotonic()`. It saves known elapsed deltas and a wall observation together at request/preparation/tool boundaries and at one-second intervals during network/child-process polling. Each budget gate also includes the current unsaved monotonic delta. A clean exit saves the remainder. There is no background scheduler or separate heartbeat thread. Wall times identify observations; they do not measure current execution duration. The wall marker is sampled alongside the monotonic reading before persistence, so time spent waiting for that transaction remains in the next measured delta or unknown crash tail rather than falling between the two observations.

Suppose a task has 17 recorded active seconds and restarts 10,000 wall seconds after its last durable observation. It keeps the 17 seconds and records an unknown interval between those observations, with `active_seconds=null`. It does not charge 10,000 seconds or label the interval zero. The next run adds its own measured time. Its budget is explicitly **known-active-only**, and UI/API show the unknown interval separately. This keeps normal continuation usable while acknowledging that a hard kill during an uncheckpointed operation may lose the exact active portion of that tail. It does not guarantee a strict all-time work limit, zero remote cost, or remote cancellation. Backward wall-clock adjustments remain visible as a signed wall span, without reducing known consumption.

Checkpointing time and replacing an interrupted marker use catalog transactions, independently of graph checkpoints. An interrupted transaction cannot both increment a total and leave its old accounting cursor committed. Likewise, recording an unknown interval and replacing its marker is atomic. The existing task lock supplies ownership; no new cross-store atomicity claim is made.

Official guidance consulted before this implementation: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) distinguishes graph checkpoints from application data; [Python 3.12 monotonic time](https://docs.python.org/3.12/library/time.html#time.monotonic) defines the in-run elapsed clock; [React state](https://react.dev/reference/react/useState) supplies the dialog's local form state. Dependency pins and the supported graph lifecycle are unchanged. [CURRENT_STATE](../CURRENT_STATE.md) owns verification results and unresolved scope.

## Implemented streaming receive persistence

The R02 integration selected on 2026-10-28 retains `Store.blob` and its content-addressed immutable files. Every nonempty decoded HTTP-body chunk is registered as `stream:<attempt>:<index>` with request, attempt, zero-based index and receipt elapsed time before interpretation or progress advancement. New files are flushed/fsynced before the FULL SQLite registration commit; identical content can reuse a physical object while keeping separate chunk identities. Stop/budget control still queries current job data after persistence. Decoder/progress observation follows. No timed flush, memory-only durability or batch of uncommitted chunks is introduced.

`stream_receive` replaces its growing reference list with a fixed-field `cursor`: format `ordered_chunks_v1`, durable `chunk_count`, `bytes`, incremental prefix `sha256` and `last_chunk_ref` (null for zero chunks). Field count and digest size are constant; numeric encodings grow with their value, rather than with a reference list. Transport fields still describe observed receive/protocol/progress facts. The cursor records the durable prefix known to that checkpoint; it is neither an accepted-response marker nor an instruction to discard any later durable records. Received, registered, checkpointed, native-validated, handoff-validated and published are separate facts.

The cursor-only prototype removed cumulative list serialization but retained essentially all elapsed cost. The selected second variable is `Store.connection_scope` around the synchronous Nexus exchange, including HTTP cleanup. It owns one thread-confined SQLite handle with `synchronous=FULL`. `transaction` still issues BEGIN IMMEDIATE and commits each blob registration and each observation separately. Fresh SELECT statements read current Stop/budget state; neither job data nor read transactions are cached. Nested scopes reuse the owner; only it closes the handle on every exit. Nested write transactions are rejected before they can roll back their caller. Other threads and Store instances use their own handles. Final archive, native validation and acceptance staging remain outside the receive scope. Reusing the handle avoids repeated connection/PRAGMA/open/close work without making a transaction span chunks. No graph lifecycle or dependency change is selected.

`Store.read_stream(job, request, attempt)` takes a consistent catalog snapshot, checks request/attempt ownership and discovers all deterministic per-attempt chunk records. It orders by numeric identity, requires contiguous indexes starting at zero and matching reference/metadata/job identities, then checks every object's length and SHA-256. It validates the checkpoint prefix's count, byte count, digest and last reference. Legacy `stream_receive.chunks` is read as an exact prefix list; no migration or rewrite is needed. A missing object, index gap/duplicate/wrong identity, bad digest or checkpoint ahead of the durable sequence raises an integrity error. A valid suffix beyond an older observation is retained and returned in full with a separate `checkpoint_count`; it does not acquire decoded/protocol/acceptance status. Absence of a record cannot prove that upstream sent no additional data.

For complete protocol settlement, `archive_stream` reconstructs and verifies this durable sequence against the in-process received bytes before archiving `raw_stream` with `chunk_validation="reconstructed"`. Its final `meta.chunks` manifest is written once. An unaccepted incomplete protocol has a separate preservation path: if cursor count/bytes/digest/last reference match the received prefix, archive those exact bytes and deterministic already committed references with `chunk_validation="registration_only"`. It does not reread every file during Stop/disconnect settlement, and makes no reconstruction/acceptance claim. A cursor mismatch still falls back to strict reconstruction, discovering any registered suffix beyond the observation. This avoids a measured multi-second fresh-file verification tail after the body was already closed; it does not delay chunk fsync/registration. The reader always verifies files/order/checkpoint and published aggregate, regardless of the archive's validation label. A later missing/corrupt constituent is an integrity failure even when the partial raw aggregate is still usable evidence.

The separately saved `assembled_response` links its source stream and attempt. Native validation precedes `accepted:<request>` staging; request/attempt pointer publication follows. Reconcile verifies acceptance blob request/attempt/kind/reference as well as stream/assembled evidence relationships before recovering or returning accepted streaming output. A mismatched stage must not copy a later attempt's usage into an older unknown attempt. Terminal bytes found by `read_stream` alone never cause parsing, acceptance, sending or tool execution. Complete native validation remains necessary for tools; compaction's handoff validation remains an additional later gate.

The reader's `data`, ordered `chunks`, `chunk_count`, `received_bytes` and `sha256` describe its verified durable sequence. In particular, `received_bytes` here means reconstructed durable length, not a claim that the last transport observation caught up. `checkpoint_count` describes the observed prefix and `checkpoint_present` distinguishes an absent observation from an observed zero. Neither missing observations nor missing usage become known zero. Chunk fragments may split UTF-8; exact `raw` evidence reads retain the bytes even when a fragment cannot be decoded alone as text.

Received bytes, immutable chunk registration, the latest observation and complete accepted output are separate facts. An interruption between chunk registration and observation can leave durable chunk evidence beyond the checkpoint; inspect per-attempt indexed records rather than treating the checkpoint as proof that nothing else arrived. Ordinary completion archives the exact aggregate as `raw_stream`, derives a separately identified `assembled_response`, validates the complete native reply and stages acceptance before tool dispatch. Reopen recovers staged acceptance without sending; unaccepted interrupted data remains subject to the frozen unknown-outcome gate. Local Stop says nothing about remote cancellation or final cost. [The streaming contract](../CONTRACTS.md#streaming-progress-waiting) owns these boundaries.

[R02's current result](../reviews/RUNTIME_REVIEW_2026-10.md#r02-storage-increment-authorized--2026-10-28) owns prototype/final comparisons, selected disposition, remaining linear costs and evidence limits. Journals, segmented storage, data caches and timed flush remain unselected. File lengths, logical encoded sizes and sampled WAL peaks are not actual device writes. Official references consulted for the installed Python3.12/SQLite3.53.1 behavior are [Python transaction and connection control](https://docs.python.org/3.12/library/sqlite3.html), [SQLite FULL synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous) and [WAL lifecycle](https://www.sqlite.org/wal.html). A Python connection context manager does not close its handle; owned handles are explicitly closed. FULL asks SQLite/VFS to synchronize commits; file fsync and SQLite cannot prove the operating system/device honored every persistence request. Process termination checks do not establish OS-crash or power-loss safety, and the catalog/files/graph remain separate commit domains.

## Implemented continuation boundaries

The 2026-10-24 increment resolves two practical failures: resuming an accepted batch could run an obsolete edit before the model saw the user's new instructions, and Continue after an HTTP/rejected reply could reopen the same permanently rejected request. [Q3](../CONTRACTS.md#q3-execution-recovery-and-delivery) owns the exact contract. The implementation keeps the existing graph and separates these cases at entry and tool boundaries:

| Observed durable state | Action and rationale |
| --- | --- |
| Tool has a receipt, including a document committed before graph completion | Recover the same result and any context intent. Preserve useful effects without duplicate commits or rollback. |
| Accepted tool has not started, and amendments changed | Preserve its candidate; settle an explicit unexecuted result under the original call identity. Then let the model decide using the new instructions. |
| Tool started but has no recoverable receipt | Keep the unknown local outcome and files. Do not claim it was skipped or assume no effect. General reconciliation remains separate work. |
| Request was prepared but never attempted, and amendments changed | Retain it and record a new-input transition. Sending known-obsolete unsent input adds no recovery value. |
| HTTP error or complete transport with rejected/truncated native reply; user presses Continue | Retain failure evidence, record the Continue decision and assemble a new request from current state. Never execute a partial call from the old reply. |
| Attempt is unknown/in flight during ordinary Continue or re-entry | Keep the same request and original replay gate. New instructions do not prove the earlier generation never happened. |
| Current compaction is unknown; user explicitly selects Resume context organization | Validate the exact current request under the task lock, preserve it and its unknown cost, then durably authorize one successor transition. This does not change its replay gate or permit automatic repeated replacements. |
| Handoff application receipt committed, but graph completion did not | Recover the original validated transition after matching its prefix/revision and immutable archive. Preserve historical capacity diagnostics; then prepare current input with new amendments/head. An archived candidate alone is not an application receipt. |

`Nexus.reconcile` and `Dispatcher.reconcile` read durable acceptance/result facts before any replacement decision. `instruction_basis` hashes only the ordered human amendments. A normal document save by the agent cannot accidentally invalidate the remaining calls in its own batch. On amendment, all genuinely unstarted old calls receive paired unexecuted results, not just writes. This avoids maintaining a speculative tool-category filter and returns method selection to the model. The app does not reject future equivalent actions that the model chooses under the new instructions.

Skipping itself has a durable intermediate `skipping` marker. A crash after that marker, after its result object, or before graph completion resumes the same skip; it cannot later execute the superseded call. Settled context intents still apply at the pending batch boundary. A historical completion report is preserved but cannot close the new instruction.

Explicit failed-request continuation first saves `continuation:<request>`, including the next revision and diagnostic/reference. Only then does the runtime use LangGraph's supported state update and return through `coordinate` and `prepare`. The stable record covers the gap between the catalog and graph stores without pretending they share a transaction. Feedback reaches both normal and compaction requests. Original attempts/time, correction counts, retained history, saved versions and unknown fees remain intact. New input can still encounter capacity or budget limits.

`Engine.start` conveys the user's Start/Continue action. Merely opening the desktop reads state. Plain runtime re-entry can recover a previously persisted Continue decision but cannot create that decision for an HTTP/rejected reply. This separates deliberate continuation from transparent recovery without requiring routine approvals for normal agent tools.

Stage B exposed a different entry need: a user pause during a compaction with frozen replay disabled. After explicit human adoption, `recover_compaction_request` names that exact pending request. Validation precedes configuration so a stale click cannot add an amendment, clear Stop or recover a later request. Locally saved accepted bytes take precedence. Otherwise the existing `continuation:<request>` identity records `explicit_compaction_recovery`, original payload/attempt references and the next revision before graph advancement. A receipt/checkpoint interruption resumes that same choice; a later unknown successor requires a new explicit choice. Current state is replanned and capacity-checked, so a fitting normal continuation does not force another compaction. Saved documents, active policy, previous unknown records, correction counts and consumption remain intact. [Q3](../CONTRACTS.md#q3-execution-recovery-and-delivery) owns the narrow exception, and `tests/test_compaction_recovery.py` plus its desktop fixture verify these boundaries. General normal-request and local-tool unknown recovery are not inferred from it.

Tests in `tests/test_continuation.py` inject the relevant persistence gaps, exercise both native protocols and byte-check preserved delivery. `tests/desktop/continuation-workflow.spec.ts` drives the real Electron/Python path with loopback scripted replies. Its test-only `boundary-hook/sitecustomize.py` delays return from a genuinely settled context tool so the UI can press Stop at a deterministic boundary. The hook is absent from normal app startup. An earlier test interrupted a running script instead: that correctly produced `local_outcome_unknown`, and is not evidence of safe script cancellation/replay. No real model judgment, source-quality benchmark or arbitrary crash guarantee follows from these tests.

<a id="ownership-and-entry-points"></a>
## 1. Ownership and entry points

| Responsibility | Authoritative facts | What another layer may retain |
|---|---|---|
| Nexus request service | Prepared request, actual send attempts, consumed limits, accepted complete native reply | The graph can retain stable references and purpose/status. |
| Accepted-batch executor / dispatcher | Accepted tool-call list, per-operation identity/input, progress, outcomes and necessary completion effects | Graph continuation can project that progress. One receipt cannot represent the whole batch. |
| Document/evidence services | Registered versions, fixed evidence/assets, committed operation results and promised pointers | A checkpoint can reference them, without undoing later committed facts. |
| Graph/context owner | Compact policy projection, proposal/settlement references, processed batches and work continuation | Catalog commits establish context effects; graph checkpoints recover them. Hydrated images/OCR remain transient request content. |
| Export responsibility | Task-scoped chosen version/scope, destination intent, actual publication/results | A model completion statement is one content claim, not proof of package consistency. Another task using the same document must not silently replace this selection. |
| Process/task lifecycle | Cancellation, waiting/stop reason, supervised local attempt state and relevant limits | UI events notify the user. Durable records remain available after reconnect. |

This is an ownership map, not six required modules or tables. One physical database can store several authorities. Two databases did not cause the historical policy-regression bug. Interpreting an old receipt as current state caused it. Co-location alone cannot fix that logic.

The discussion preferred the small graph because a batch-owning node can directly order tools, reconcile progress, and prepare the next input. An illustrative loop is `prepare -> model -> tool_batch -> prepare`, with a delivery/stop assessment after a no-tool response. The implemented graph adds a separate `coordinate` checkpoint before `prepare` so outcome projection does not depend on input preparation succeeding. `prepare` can be deterministic without adding a model call. Semantic compaction is a separate accounted model decision even if preparation invokes it.

Do not assume every invocation, restart, or branch enters through prepare. Framework checkpoint successors or `update_state(as_node=...)` can continue later in the graph. The model-service entry and actual-send boundary must therefore enforce their own identity, budget, cancellation, and accepted-reply checks. There is no hidden second scheduler merely to keep a framework's prebuilt-agent shape.

**Source basis:** EVT-0878, EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="request-and-attempt-identity"></a>
## 2. Request, attempt, accepted response, and operation identities

One ID cannot safely represent all of the following:

| Identity | Meaning and continuity rule |
|---|---|
| Task / execution context | The authorized work and its durable original allowances. Reopening it does not replenish them. |
| Logical model step | One intended model judgment. Persist a fresh identity for new input or deliberate regeneration. Recovery of the same prepared judgment retains it. |
| Input view / frozen request | The exact selected input plus route/model settings, generation parameters, and tool schemas for that judgment. The view may be resent as several attempts. |
| Attempt | One actual request send and its observed outcome. Consume/record its allowance before sending. |
| Accepted native response | The complete response accepted for that request. Its tool-call list supplies executable intent. |
| Tool batch | The full accepted call list from that response, including ordering/dependencies and progress. |
| Application operation | One accepted effect with stable scoped identity and complete effective input. Recovery reuses it. A different input cannot overwrite it. |
| Framework message/checkpoint | Runtime representation/progress. It relates to the above records but is not a substitute for their causal identities. |

The review rejected `parent_model_request_id == input_view_id` as a universal equivalence. A service can resend one view. A task turn can prepare different views. Accepted replies generate the calls to execute.

A provider `tool_call_id` alone can collide across parent responses. A tuple such as `(thread_id, checkpoint_ns, tool_call_id)` remains insufficient unless uniqueness across its full scope is established. Preserve the accepted parent response relationship and app operation identity. Record the input fingerprint for inconsistency detection.

Likewise `(job_id, checkpoint_ns, model_turn_seq)` describes a straight-line proposal, not all new judgments. A checkpoint namespace is not necessarily a branch identity. A no-tool answer can reach END without incrementing the proposed counter. Later user input can then collide.

Deliberate regeneration can use byte-identical prompts but still be a new decision. A hash of the input identifies content equality, not intent or operation identity. Exact app entry rules must decide when to continue the existing prepared step and when to create a new one.

<a id="request-record-names-and-entry-rules"></a>
### Request records and explicit entry intentions

The source sketches named the durable intended decision `model_step_id`. They used `request_ref` for an immutable request location. They used `request_fingerprint` or `request_sha256` to check its fixed content. A proposed `requests/<model_step_id>.json` layout illustrated external payload storage while Graph State kept compact references. Those spellings and paths are examples.

The fingerprint boundary must include the selected route/protocol/model, generation settings, tool schemas, and actual selected content. Hashing text alone or mutable filenames does not satisfy that boundary. `input_view_id` identifies the assembled view. It relates to step, attempt, and accepted-reply identities but is not interchangeable with them.

ATT-27 made the entry intentions explicit through names such as `resume_interrupted_job()`, `branch_or_regenerate()`, and `append_user_input()`. A resume finds the same prepared step. It reuses an accepted complete reply if present. Otherwise, it reconciles attempts and remaining allowance before any permitted resend.

New user input or deliberate regeneration requires a new judgment and durable step identity, even when the fingerprint is unchanged. The proposed `step_intent="new_judgment_required"` expresses that decision. It does not prove a resumed graph will pass through `prepare_step`. A display `branch_seq`, UUID choice, or counter cannot replace the entry rule. Generalized branching remains deferred.

The prepared request fixes more than text messages. It includes the selected route/model/protocol configuration, generation parameters, tool definitions, required native items, selected content and exact image/artifact versions. Large request content can live in immutable files while graph state retains small references, fingerprints, and compact policy. Re-resolving `latest`, swapping a newer crop, or applying a fresh policy after preparation changes the request. The input assembler selects evidence. Encoding obeys that selection instead of scanning all old artifacts and restoring released images.

Before sending, retrieve any complete accepted reply for the same logical step/request. If present, reuse it and continue its batch instead of generating again. Storing `accepted_reply_id` only in graph message metadata misses the interval where the service saved the reply but the graph did not checkpoint. The lookup needs a durable app step identity that survives that gap.

If no complete accepted reply exists, inspect attempt records. Absence of a reply is not proof the request was never sent. Unknown remote outcome remains possible. Same-ID/different-input recovery is an error to reconcile. It must not silently overwrite the original prepared request.

<a id="hashes-and-identity"></a>
### What a hash proves, and what the operation identity adds

| Check | What equality establishes | What it does not establish |
|---|---|---|
| Raw candidate/reply payload hash | The preserved bytes being inspected are the same retained payload. | Valid syntax, a complete call, or correct PDF content. A parsed dictionary is a separate representation and cannot stand in for original wire bytes. |
| Prepared request fingerprint | The frozen content/configuration/schema being reused agrees with that prepared decision's specified fingerprint boundary. | That two byte-identical prompts are the same intended judgment, or that the earlier attempt was never sent. |
| Effective operation input fingerprint | The tool, target/base, resolved references/defaults, and submitted changes match that operation's fixed input boundary. | That the operation is still eligible to commit against today's head, or that a different accepted call with identical content is a duplicate. |
| Saved asset/package member hash | The checked bytes agree with the expected bytes. | Which source/region/settings produced them, semantic correctness, complete publication, or absence of extra/missing package members. |

The app identity supplies task/accepted-parent/operation scope. Fingerprints detect inconsistent reuse of that identity. Their canonical serialization and exact covered fields remain contract work. Preserve native/raw and resolved representations without pretending one hash identifies all of them. Resolving a candidate reference expands an input for execution. Rewriting its pointer to a different candidate under the same operation ID changes meaning, not merely formatting.

**Source basis:** EVT-0855, EVT-0878, EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107. ATT-21–ATT-29.

<a id="accepted-batch-execution"></a>
## 3. Accepted batch execution and ordering

Persist the complete accepted call list before relying on execution progress. Calls execute from their original complete arguments, not a shortened model-facing history projection. Incomplete JSON or concatenated fragments from separate attempts must never become an executable call. Domain validation can reject an individual call with a precise result, while preserving its received candidate arguments.

A batch-owning executor is responsible for all declared calls and the point at which the next model input becomes valid. Finding a committed receipt for A does not settle B. Before the next new request:

1. Restore completed results and necessary intents/effects.
2. Execute or reconcile outstanding calls according to their contracts.
3. Account for any stop. A stopped unfinished batch does not become a completed batch merely because one call succeeded.

“Settled” includes an accurately recorded validation/error outcome. It does not mean every tool succeeded. If A saved a version and B's arguments were rejected, preserve A's success and B's candidate/error. Once the executor accounts for the accepted batch's actual outcomes, a later model decision can propose a new valid B operation.

Do not rewrite the accepted B arguments under its old identity. Do not silently omit B. Do not resend A to make the batch appear uniformly successful. Malformed or incomplete native calls take the preservation/error path. That path does not authorize execution merely because the app saved a raw candidate.

Do not assume that adopting `create_agent` preserves the old controller's sequential execution. The reviewed implementation dispatched tools through separate `Send("tools", ...)` paths. Two distinct orderings matter:

- **Context intent order:** settle intents according to the trusted accepted-parent declaration order, not the order concurrent I/O finishes. Persist policy and processed-batch state coherently at the defined sequential boundary.
- **Actual effect order:** a deterministic intent list does not order edits, file writes, or previews. If B depends on A's version, the executor must express that dependency or use explicit versions and service preconditions.

A small sequential tool-batch node is a valid first-version choice and does not impose a PDF extraction recipe. Independent reads may later parallelize under their actual resource/side-effect contract. A fixed-version reopen is not unsafe merely because it is called a document tool. Conversely, OCR/render can create files, assets, and child processes. Leaving the PDF unchanged does not make these operations universally pure.

The review rejected an in-memory declaration-order lock as recovery machinery. A may complete, and the framework may restore its pending write without rerunning A. B can then wait forever for A to signal a new in-memory event. Durable progress and the executor's complete batch ownership must determine what remains. A read of `latest` can also race a later writer even if each writer waits for earlier writers. Bind the read/export/preview to its intended version or define its dependency at acceptance.

### Completion includes effects beyond display text

Some tools produce a `ToolMessage` plus a graph `Command` or context intent. Replaying only the visible message can leave a necessary current-batch state update absent. Preserve the domain result and supported completion semantics. If the implementation supports only `Command.update`, it cannot silently discard other forms such as `goto` or `graph`. Concentrating state writes may simplify the final implementation, but does not remove required effects.

At the same time, an old completion must not force a newer state backward. Suppose batch X settled policy 7 to 8 and a later batch settled 9. Replay of X reports its completed processing and retains 9. An incomplete original transition can use its receipt only under compatible parent state. Incompatible modification needs an explicit conflict, not `max(policy_rev)` or unconditional activation of the old result.

Stable message IDs are useful but limited. A reducer can replace an existing same-ID message. After compaction removes it, replay may append it again. Do not scan every successful receipt and inject historical ToolMessages into current input. Reconcile the accepted pending batch/runtime work, not an unbounded global journal. Protocol pair validity must survive projection and recovery.

Progress also needs a defined causal boundary. An operation created with sequence 10 can finish after sequence 11. Neither `max(event_seq)` nor the latest timestamp safely substitutes for per-call completion and processed-effect identity. Record which accepted calls/effects remain outstanding. Under sequential execution, a small batch cursor plus explicit records can track this information. It does not require a general event-sourcing system.

The earlier controller's `next_call` and pending-operation identity illustrated this cursor responsibility. It means “which declaration still needs an accounted outcome,” not “the first absent display message.” Recovery needs the accepted call list and each call's durable result, error, unfinished state, or stop reason. A cursor alone cannot prove that an externally committed operation did not happen. Conversely, a framework pending write may already contain a result that need not be executed again.

**Source basis:** EVT-0878, EVT-0914, EVT-0942, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-21–ATT-30.

<a id="operation-replay"></a>
## 4. Operation replay and resolved defaults

Persist resolved defaults at the operation's declared start boundary, after any required earlier batch dependency. These values stay bound to that operation on recovery:

- An omitted version that resolved to V10.
- Selected source, region, and render parameters.
- The output location and attempt directory. A later new operation may resolve defaults again. This prevents a retry of “preview current” from quietly previewing a different version.

For `save(...)` followed by `preview(version omitted)`, resolving both calls at batch acceptance could bind preview to the pre-save version. Under the discussed sequential-start option, preview resolves the current version once, after the preceding save settles. It records that exact version before doing its own work. Explicit version arguments remain preferable when already known.

The final contract must state the resolution point. “remove the word latest” does not remove a dynamic default. It must also distinguish the originally accepted arguments from the effective arguments with recorded defaults, so recovery can check both without resolving them anew.

The proposed record names `resolved_version_id`, `output_dir`, and `attempt_dir` make this binding concrete: they record the values actually chosen for execution, not defaults to evaluate again after restart. The suggested operation tuple `(task_id, model_step_id, call_index, tool_call_id)` also tried to give a provider call task/parent/order context. It is an illustrative key, not a finalized uniqueness rule. The accepted parent reply and fixed effective input still need an unambiguous relationship. Declaration index does not itself serialize effects.

Same operation identity with the same complete effective input reuses its original result. The service rejects the same identity with changed parameters, tool, target, or fixed references. A new accepted operation with similar content is not automatically the old operation. Optional content deduplication needs the full scope/base/target/content, and does not infer semantic intention.

| Operation | Recovery facts and boundary |
|---|---|
| Fixed-version read/reopen | Resolve the original exact version/evidence. Do not substitute today's head. |
| Save/edit | Find its committed registration/receipt. If only a prepared result exists, finish only under the original expected base/target. Otherwise, retain it and return conflict. |
| Select delivery | Return the original selection receipt. Do not overwrite a later legitimate selection. Target/scope validity is separate from requiring a fully completed document. |
| Source render | Check PDF identity, physical page/region, DPI/engine settings, attempt state, and output completeness. It needs no saved document version. |
| Output preview | Check selected document version and view parameters, including whether this is ordinary reading or an expanded diagnostic view. |
| Export | Reconcile the specified immutable version, destination identity, intended members and actual bytes, separately from working head. |
| OCR / child process | Inspect its recorded attempt and files/process state. Safe parallelism, safe reuse, and safe rerun are separate questions. Preserve useful output. Uncertain local effects require reconciliation or stop. |
| Host-user script | Retain complete arguments/logs and known effects. Do not blindly rerun an outcome-unknown script merely because no success receipt exists. |

Suppose A produced V12 and B later produced V13. Replay A returns “A produced V12” and leaves head V13. Suppose C selected V10 and D later selected V11. Replay C returns C's historical result without selecting V10 again. A historical receipt is a fact at commit time, not a fresh command to establish the same pointer today.

Successful version metadata does not replace started/outcome-unknown records. No receipt may mean the effect never happened, the process is still running, or the effect completed before its receipt was saved. File/hash equality alone cannot establish whether a render used the requested source/region/DPI. Use the operation's complete fixed inputs and actual result/attempt facts.

**Source basis:** EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-25–ATT-30.

<a id="recovery-transitions"></a>
## 5. Recovery transitions and durability gaps

Q3 must assign an owner and finite re-entry behavior at each boundary below. These are scenarios to specify, not claims that all such failures occurred in the old app or that every hard crash will be recoverable.

| Durable facts on re-entry | Required next decision/action | Invalid shortcut |
|---|---|---|
| Prepared request exists, but no accepted reply exists | Reconcile attempts, consumed limits, cancellation and configured replay eligibility before another send of that frozen request. | Assume no reply means no remote work/cost. |
| Attempt may have been sent, and remote outcome is unknown | Apply enabled bounded model replay under original limits, preserving uncertainty and potential overlap. | Claim local timeout canceled the upstream generation. |
| Service accepted a complete reply, but graph lacks it | Retrieve by durable logical request/step identity and recover its accepted batch. | Send another model request because graph metadata lacks an ID. |
| Executor accepted the reply, but only some calls are complete | Reuse completed results/effects and reconcile all remaining calls in that same batch. | Advance after the first receipt found. |
| Immutable version payload is ready, but metadata is absent | Verify identity/completeness and original expected base/target before finishing the defined commit. Preserve conflict output. | Delete it as abandoned or advance head over a newer version. |
| Tool committed, but result projection/checkpoint is absent | Return/reconstruct its historical receipt and necessary current-batch completion effects. | Repeat the local commit or treat projection error as write failure. |
| Whole batch settled, but graph continuation is absent | Restore supported deterministic continuation effects, then assemble the next request at a safe boundary. | Re-inject all historical receipts or regress compact policy. |
| External local effect remains unknown | Inspect/reconcile within the operation contract. If the effect cannot be established, preserve work and stop with a specific unknown outcome. | Blindly repeat OCR/script/process work. |
| Stop, waiting, or cancellation is recorded | Respect that state and original limits. A defined explicit continuation may alter cancellation, but not replenish allowances by itself. | Restart as a fresh unlimited run or add a reminder to every stop. |
| Export partly published | Check original output identity, selected version, directory and archive contents, then finish/reconcile the declared effects without overwriting unrelated output. | Assume one rename atomically published directory and ZIP. |

Graph checkpoints, metadata transactions, and external files are separate durability boundaries. A runtime checkpointer is not a transaction manager for outside effects. Modes described as `sync`, `async`, and `exit` have different persistence timing. Select and verify the actual supported behavior of the pinned framework version. The historical `durability="sync"` argument concerned writing a prior checkpoint before the next step, not exactly-once remote generation or universal power-loss safety.

Use supported framework state/history/resume and pending-write facilities rather than treating diagnostic task descriptions as an executable tool-call array. `StateSnapshot.tasks` describes runtime tasks. The app should not invent a competing scheduler from those descriptions. A batch-owning node can retain durable app progress because the framework does not automatically checkpoint each nested call. Reuse framework-recorded completion where available and app receipts across the remaining effect/checkpoint gap.

Restoring an old graph snapshot cannot erase later committed document versions, request attempts, consumed budgets, or external effects. An old request still reuses its own frozen input. Once its accepted batch is settled, a new decision can assemble a current view. These two rules coexist: historical input consistency and preservation of later facts protect different responsibilities.

An exception that runs `finally` and flushes data is not a hard process-kill test. Broken IPC can leave a child working. The old R1/R2 exercises injected bounded network/stream failures. They did not establish arbitrary crash recovery, natural prolonged-outage behavior, or migration of old job formats. No backward compatibility is required for the rebuild.

<a id="historical-fault-relay"></a>
### Historical fault injection and its exact scope

The old `tools/experiment_fault_relay.py` was a closed experiment helper, not a product API or production transport. Its CLI bound a loopback listener and a fixed Nexus upstream, path and model. It armed faults after matching the controller's request, published draft and receipt, with requested positions still unprocessed. Those structural checks did not establish source usefulness, which required independent review.

| Mode | Historical injected condition |
| --- | --- |
| R1 | After the partial-work gate matched, a 90-second monotonic timer controlled local HTTP 503 rejection before any upstream connection. Timer expiry and later forwarding were separate events. |
| R2 | One cut followed at least 64 accumulated alphanumeric characters from content or tool-argument deltas in complete, nonterminal Chat SSE frames. |

The R2 counter used Python `str.isalnum()`, including qualifying Unicode characters. It did not count bytes, tokens, punctuation, heartbeat comments or mere frame arrivals. The observer disabled further cuts after a finish reason or `[DONE]`. The relay forwarded through the triggering complete frame, then closed both connection handles. Complete frames could still contain incomplete tool arguments, which never authorized execution.

If no qualifying interval appeared, the helper recorded `fault_unexercised`. It forwarded ordinary bytes incrementally without reconstructing or joining attempts. Its records contained safe timestamps, hashes, stages and forwarding facts, not provider bodies, arbitrary headers or credentials. A stop file closed the listener, active handles and timer.

These mechanics explain what the old trials exercised. They do not establish a natural outage, a new application dependency or permission for another trial. [SUP-25](../reference/sources/support/SUP-25.txt) preserves the selected helper logic. [SUP-26](../reference/sources/support/SUP-26.txt) preserves its historical scope description.

**Source basis:** EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. Earlier recovery qualifications appear in [reference 02](../reference/02-context-state-and-evidence.md#persistence-and-replay).

<a id="budgets-cancellation-and-stop"></a>
## 6. Persistent budgets, cancellation, and stop reasons

All actual model sends pass the shared service's final gate, including ordinary reasoning, semantic compaction, configured overflow re-preparation, and an optional reminder. A gate only at the graph's starting node can be bypassed by a restored successor or alternate edge. Persist consumption/attempt identity before dispatch, then preserve observed outcome, known usage, unknown cost, and remaining allowance. Do not hide nested SDK/proxy retries that multiply the configured policy.

Keep the following quantities distinct and define their accounting in the open contract:

| Quantity | What needs an explicit rule |
|---|---|
| Logical decisions / model rounds | When a new intended step consumes the original task allowance. |
| Physical attempts | Every actual send, including enabled retry or capacity-recovery send. |
| Request inactivity or transport timeout | Which connection/header/body/idle boundary is observed and what outcome is actually known. |
| Whole-job active time / elapsed time | Whether waiting, backoff, local preflight, tools, and user waiting count. Restart must not reset accumulated facts. |
| Context/input and output reserve | The actual assembled request and selected route, separate from request bytes and nominal provider window. |
| Cost/usage | Known observed usage and unknown/possibly duplicated inference. A local failure or later success does not erase uncertainty. |

The historical examples select no new retry count, 60–120-second backoff, 180-second timeout, 100-round cap, or universal context threshold. Old zero-retry defaults and finite trials do not become new-repository defaults. Exact eligibility/limits need configuration within the authorized task.

Unknown remote generation and unknown local effects have different handling. When bounded unknown-outcome model replay is enabled and allowance remains, it does not require routine human proof that the original generation stopped. Record possible duplicate inference, remote overlap, and unknown fee/usage. Local abort, timeout, or a successful later attempt does not prove cancellation, continuation of the first generation, or zero cost. A script/OCR operation with an unreconciled local outcome stops under its own effect contract rather than being blindly replayed.

The app can read already durable accepted results when the model allowance is exhausted. Reading them does not send a request. This does not grant authority for every unfinished tool to run past another applicable limit. Preserve the pending batch/stop reason and useful work. Host-callable export of a specified saved version remains possible without further model tokens, subject to its own execution time, storage, cancellation, and publication rules.

<a id="historical-retry-hierarchy"></a>
### Historical retry hierarchy and manual resume

The old controller distinguished three modes. These names and limits explain its policy. They do not select rebuild defaults.

| Historical configuration | Automatic eligibility | Ceiling per preserved model round |
|---|---|---|
| `automatic_retries > 0` | Eligible transient replay, including recognized queue failures. | `1 + automatic_retries` app HTTP attempts, including the original. Queue attempts consume this allowance even when `queue_retries` is larger. |
| `automatic_retries = 0`, `queue_retries > 0` | Only recognized pre-generation queue failures. | `1 + queue_retries` app HTTP attempts, including the original. |
| Both options equal zero | No automatic replay. | The original attempt plus at most two explicit resumptions retains a three-attempt ceiling. |

Thus, `automatic_retries: 2` allowed three app HTTP attempts for that preserved round. The queue option did not add another retry allowance. The controller persisted attempts and consumed budget before dispatch. Resume and restart retained the original turn, active-time and per-round attempt budgets. Two permitted explicit resumptions did not replenish those budgets.

All attempts and waits shared the original cumulative active deadline and maximum turns. A retry was not a new model round. Successful recovery preserved earlier unknown attempts and their unresolved usage. A later local-only continuation did not charge the same accepted historical ambiguity again.

The old policy specified one accountable app retry owner to prevent configurable SDK or proxy layers from silently multiplying its allowance. Opaque upstream retries remained a limitation. Three app attempts did not guarantee three upstream generations or a monetary ceiling.

This hierarchy covered the historical transport and recognized-queue policy. It did not settle every future admission or capacity-recovery policy. The rebuild retains durable accounting and explicit bounded eligibility. [Capacity re-preparation](#capacity-rejection-is-not-ordinary-same-input-retry) still needs its separate rules while sharing task totals.

**Source basis:** SUP-09, historical TOOLS retry-budget and retry-owner passages.

<a id="historical-retry-delay"></a>
### Historical backoff values and calculation

The old `RunConfig` supplied these defaults and bounds:

| Field | Historical default | Accepted range |
| --- | --- | --- |
| `retry_initial_delay` | 2 seconds | 0–60 seconds, inclusive. |
| `retry_max_delay` | 30 seconds | 0–300 seconds, inclusive. |
| `retry_jitter` | 0.25 | 0–1, inclusive, as a dimensionless proportion. |
| `queue_retry_delay` | 15 seconds | 0–60 seconds, inclusive. |

For an eligible automatic retry, `attempt` meant the failed attempt's one-based number, including the original send as 1. The controller calculated:

```text
local = min(retry_max_delay, retry_initial_delay * 2**(attempt - 1))
local = min(retry_max_delay, local * (1 + uniform(0, retry_jitter)))
delay = max(local, retry_after_seconds)
```

Thus, jitter only added a nonnegative proportion before the second cap. With the defaults, the first local delay ranged from 2 to 2.5 seconds. A valid `Retry-After` of 59 seconds could exceed the 30-second local cap. An absent accepted header contributed zero, not an extra delay.

For recognized queue-only recovery with `automatic_retries=0`, `queue_retry_delay` replaced `local` before the final maximum. It did not add another exponential wait or retry allowance. Positive `automatic_retries` retained the automatic calculation even for eligible queue failures.

The controller persisted `retry_wait_seconds` and `retry_not_before` before its cancellable wait. Resume used the remaining wait against that timestamp instead of drawing fresh jitter. Attempts and waits still shared the original active deadline, cancellation state and attempt allowance. A larger header delay did not extend the task deadline.

[SUP-24](../reference/sources/support/SUP-24.txt) preserves the historical configuration, formula and wait code. These numbers do not choose rebuild defaults or settle the open capacity-recovery policy.

<a id="send-boundary-sequence"></a>
### Same-request recovery at the service boundary

The service follows this sequence:

1. Locate the prepared logical decision and check its fixed input identity.
2. Recover any complete accepted result.
3. Only if a fresh send is needed, assess original attempt state, remaining limits, cancellation, and actual request capacity.
4. For that fresh send, persist attempt consumption before dispatch. Save the received native result and its acceptance outcome before graph continuation depends on it. Exact record/state names and timeout accounting remain Q3 choices.

This order avoids two opposite errors. A zero model allowance does not discard an answer already obtained and saved. Conversely, missing graph state does not permit another send without examining attempts already charged to the task. If a compaction used the last allowed attempt, the app can still inspect and validly apply its stored result. A subsequent ordinary request is not free.

The prepared request may be too large, or its route may no longer apply. A later authorized re-preparation must receive its own identity and preserve the earlier attempt's history. Silently changing the frozen payload is not same-request replay.

Cancellation takes precedence at the actual work boundary, including after successful compaction and before the next request. Do not require a final model handoff before honoring pause/cancel. A defined explicit continuation can clear cancellation but does not itself reset attempts/turns/time. A genuine question waits for user input. A technical blocker, exhausted allowance, or generic no-tool stall is not automatically a question for the user.

### Capacity rejection is not ordinary same-input retry

A deterministic local projection consumes no HTTP attempt but uses time. An actual reduced resend does consume an attempt and shared totals. With retries zero, defining every send as `1 + automatic_retries` would leave no separate capacity-recovery send. Therefore, the policies need separate explicit eligibility and bounds while sharing total accounting. “One immediate overflow resend” remained a proposal.

Only a supported capacity diagnosis and a changed view that improves the relevant limit justify re-preparation. Generic HTTP 500/502 is not overflow evidence. HTTP 413 concerns request bytes and may include `Retry-After`. It does not reveal token capacity or justify always resending immediately.

Rejection of a locally estimated 80k input does not prove an 80k model window. Record route/model/protocol, upstream error/count/limit where available, and local estimate/method separately. A provisional safety budget can be adjusted deliberately without rewriting a provider specification or changing unrelated routes.

Streaming and non-streaming use the same complete-response acceptance, operation, persistence, and stop semantics. Partial fragments remain evidence. Never splice them across attempts into executable JSON. Retain useful received native content with appropriate handling of sensitive/error fragments. Preserve distinctions between protocol completion, schema validity, and content correctness.

**Source basis:** EVT-0855, EVT-0878, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-22/26–ATT-30.

<a id="context-work-and-frozen-input"></a>
## 7. Context work uses the same durable execution boundary

R01 changes new unfrozen capacity observations, not execution identity. [The context guide](CONTEXT_AND_EVIDENCE.md#capacity-accounting) owns the shared BPE proxy, offline data, explicit fallback and uncertainty semantics. Recover historical handoff/settlement effects and existing frozen requests before any current estimate; never rewrite receipt/usage or revive committed needs-revision content. Prospective app-authored outcome metadata uses the same canonical ordering and latest-candidate anchor as the eventual saved settlement, so embedded JSON strings produce the same native payload and BPE reservation. An old equal-byte-length assumption is insufficient for that boundary. Original model/tool content is unaffected.

The single built-in executor keeps a compact policy projection in graph state: selections, pin/release choices, notes or references, compaction boundary and processed batches. Context calls save intents; the coordinator admits the complete revision. Its catalog transaction commits disposition and any active-policy effect, which the graph then recovers. The historical graph-only simplification rejected a competing policy scheduler; the current commit/current-policy records provide checkpoint-gap authority without adding another decision writer. Request budgets, committed documents and external-operation receipts likewise remain service facts because graph rollback cannot undo them. [Q2/Q3](../CONTRACTS.md#q2-context-transitions) owns this current boundary.

Transient hydration belongs to request assembly. Returning giant OCR/images as persistent state updates refills every checkpoint. The input service follows the settled selection and resolves the corresponding immutable evidence. It does not make a second independent relevance decision.

A save that omits a context delta does not silently release everything unpinned. Pin/release conflicts need an explicit merged outcome. Reducers do not determine semantic importance by themselves.

Semantic compaction is real model work with a purpose, frozen input, identity, attempt records, accepted output, budgets, and cancellation. It cannot be an untracked call inside a supposedly free prepare function. It can share the same service in the same Python backend without another communications stack. A successful compaction edge must return through the same checks before further work.

Each compaction records the history actually supplied, prior handoff/coverage, uncovered history, and base revision. Apply only the covered range and preserve unprocessed messages and complete protocol pairs. The app should supply program-known message IDs and revision anchors. The summarizer should not reconstruct them. Check format/nonblank/refusal, exact replacement scope, current revision, and resulting capacity. These checks do not prove semantic losslessness or require a second review-model call.

Distinguish progress from readiness for normal inference. Reducing 140k to 100k toward an 80k target can be useful even though another compaction is needed. Check the complete resulting view including summary/anchor overhead. A normal request must fit the final input/output allowance. Intermediate compaction need not already reach it.

Preserve originals on invalid/stale/no-progress output and use bounded original allowances to stop if no fitting request can be assembled. Do not automatically resend the same oversized normal request after failure.

The recommended handoff is self-sufficient for continuation: effective requirements, current scope/version, unfinished work, exact useful references, decisions, cautions, and cross-page dependencies. A delta-only note can lose meaning when its anchor changes.

For example, a handoff omits “next-page rows use the prior header” because it is already in an anchor. That information disappears if a later anchor only says “processing page 18.” An anchor stored on disk does not prove that future input assembly includes it. That alternative would need exact anchor inclusion or reconsolidation. It is not the V1 prerequisite.

Authoring arguments can be as large as tool results. Keep original calls for pending execution/replay. A later model-input projection may replace completed historical body text with exact references. Latest drafts and unresolved candidates can partly leave input when irrelevant portions are safely retrievable. There is no fixed recent-K or superseded-only retention rule.

A just-generated call was not in the prior model input, so projecting it before first return does not necessarily invalidate that prior prefix. Rewriting earlier sent history differs. Neither a permanent verbatim window nor a claimed 90% saving is established. Frozen snapshots protect replay independently of cache policy.

The [context guide](CONTEXT_AND_EVIDENCE.md) contains the detailed policy/capacity algorithms and examples. This section states what their execution boundary must preserve.

**Source basis:** EVT-0878, EVT-0914, EVT-0942, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="completion-and-waiting"></a>
## 8. Execution stop, content completion, and package consistency

Use separate dimensions rather than one terminal label that mixes them:

| Dimension | Examples of information it records |
|---|---|
| Execution | Running, waiting on a real question, canceled, limited by budget/time, blocked by a specific technical/unknown-effect outcome, stopped without complete delivery. |
| Content claim | Which scope/version the agent considers complete, known gaps/errors, draft/partial status, and source-review observations where performed. |
| Package consistency | Which version/scope was selected, which output files/archive were built, actual consistency checks, and publication outcome. |

<a id="stop-label-meanings"></a>
### Why the historical terminal labels were split

ATT-28 proposed `completed_verified_delivery`, `exported_honest_draft`, `waiting_for_user_clarification`, `stopped_operational_limit`, and `stopped_unreconciled_effect` as five mutually exclusive terminal states. They mix facts that can coexist: a canceled or budget-limited execution may have exported an honest draft. The later `execution_status`, `content_status`, and `delivery_status` names express separate dimensions, not a frozen three-field schema. In particular, `completed_verified_delivery` must not imply source acceptance merely because package bytes match a version. A label such as `exported_package_verified_against_version` describes that narrower consistency check.

The waiting aliases `awaiting_user`, `waiting_for_user_input`, and `waiting_for_user_clarification` are meaningful only with a concrete question to answer. `clarification_prompt` was a suggested place to retain it. A generic technical fault or repeated no-tool reply can instead be `stopped_incomplete` with its actual reason. `stopped_unreconciled_effect` also needs to distinguish local effect uncertainty from an unknown remote model outcome, because the latter can permit configured bounded replay. Exact state names remain Q3 work. The distinctions prevent a UI from asking the user to resolve a question that was never posed.

A canceled run can contain a useful exported draft. A consistent ZIP can contain incomplete content. A valid schema or no-tool final answer cannot establish source fidelity. A selected good V10 can coexist with experimental V11 and an unused candidate. Those do not automatically block delivery. Only known necessary unfinished work affects the completion claim.

A no-tool answer may ask a real question, explain a blocker, merely narrate a planned tool action, prematurely claim completion, or actually finish. The implemented agent protocol uses `report` to declare complete, partial or waiting intent. For text without that declaration, the response-correction increment gives bounded feedback to continue useful work or formalize the intended report. It explicitly states that no user answer has arrived. A question becomes waiting through `report(waiting)`; the controller does not infer semantic completion or classify question marks. Whether a real model reliably follows this instruction remains a model-quality question.

The historical one-shot reminder proposal required persisted identity, finite counts, normal accounting and stop precedence. The implemented policy now permits `max_response_repairs` corrections (default 2, configurable for new tasks), with independent normal-response and compaction episodes. Feedback lives at `repair:<request>`; the graph carries only its reference, count and current-head/amendment basis. Re-entry reuses accepted replies and saved feedback rather than sending the same request again. Plain Continue does not replenish the allowance. New user instructions or an edited head establish a new episode while consumed task attempts/time remain unchanged. Explicit reports, cancellation and budgets retain precedence. This is not a general semantic-progress detector or a guarantee that the model will act correctly.

Invalid handoff JSON, schema, reduction or unexpected tool calls follow the same feedback mechanism. A new compaction request keeps the covered history and diagnostic; the rejected candidate text is included only when the complete input fits. Previous context remains active until a valid replacement applies. State mismatches and local storage faults do not become model repair prompts. `handoff:<request>` and transactional event receipts cover replay after archive/feedback persistence and before checkpoint completion. This does not make the graph checkpoint and catalog one transaction.

The no-tool decision can therefore be expressed without inventing a completion detector:

| Known condition | Retained behavior |
|---|---|
| User canceled, a limit is exhausted, or a local effect cannot be reconciled | Record that stop reason and preserve available work. No reminder overrides it. |
| Agent declares a specific necessary question with `report(waiting)` | Store the question and wait for its answer. Do not run a continuation reminder after this explicit report. |
| A saved version/scope is already selected and only packaging is missing | Use the host-callable export path under its applicable limits. A new model judgment is unnecessary for known packaging intent. |
| Agent reports completion | Bind the content claim to its actual version/scope and retain known gaps/review evidence. A statement alone does not certify fidelity. |
| Text-only reply without a report, with execution still permitted | Use the configured bounded correction to request the next action or an explicit report. If the text asked a necessary question, request `report(waiting)` without assuming an answer. Do not pretend completion or fabricate a user question. |
| The same stall persists after its allowed reminder | Preserve results and report incomplete stopping. Restart does not create a fresh reminder allowance. |

**Source basis:** EVT-0968, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-25–ATT-30.

<a id="process-and-progress"></a>
## 9. Local processes, progress, and desktop IPC

Process isolation and side-effect tracking serve different purposes. Trusted scripts are process-opt-in/off by default and run with host-user permissions. They are not an OS sandbox. Enabling them permits autonomous own-task use under the agreed task scope. Source text and recorded commands remain inert data. Separate attempt/output directories can avoid collisions, but do not isolate model context, privileges, or unknown external effects.

Read-only inspection, explicit termination, and salvage must be separate actions. Historical names `inspect_attempt`, `terminate_attempt`, and `salvage_attempt` express that distinction without requiring those exact APIs. Inspecting or copying useful output must not silently kill a running child. A proposed `terminate_running_process=True` made termination explicit.

Windows Job Objects and `FILE_SHARE_READ` snapshots were possible mechanics. A real implementation must determine whether reading a live file is stable/allowed and report conflicts/incompleteness. These options do not create a required general process-salvage subsystem.

Preserve useful complete images, logs, and partial outputs in an interrupted attempt. Do not clear `attempt_dir` as a routine prelude to rerunning. Check source/settings/completeness before reuse, and create a distinct new attempt for necessary reruns. Complete decoding of saved output and bounds on inspection matter. Rescued output is not proof that the whole operation or task completed. Original full logs/files remain available despite tool response-size limits.

For the eventual desktop, structured progress can describe preparation/capacity, request/attempt/backoff, streamed character count, OCR page progress, candidate retention, and committed versions. These are notifications about work, not the source of truth. “OCR page completed” means evidence extraction, not conversion/source acceptance. Version diffs read explicit saved versions rather than reconstructing prose from progress events.

The historical direction was asynchronous JSON over standard input/output, with exact framing open. IPC is communication between the desktop and Python processes. Protocol messages and diagnostics require distinct deliberate channels. A library printing text into the protocol stream can corrupt framing. The proposed universal first-line `os.dup2` remedy was withdrawn because native callbacks, libraries, threads, Windows behavior, and packaging need the actual implementation context. The retained requirement is correct channel separation, not a mandated redirection recipe.

A bounded queue cannot guarantee unlimited non-droppable replies, producers that never wait, and indefinite receiver failure simultaneously. If the UI stops reading, a pipe eventually fills. Keep ordinary progress off the conversion core's critical path.

- Coalesce outdated progress.
- Persist important results for request-ID lookup.
- Use a snapshot/sequence or revision on reconnect.

Declare queue/storage limits and how new work is limited or rejected. Both protocol and diagnostics pipes need appropriate consumption. Dropping obsolete “page 5” progress after “page 6” is different from dropping the only receipt for a committed version.

The proposed `state_seq` / `state_watermark` event would tell the UI that newer committed state is available. `dropped_intermediate_events` would report coalesced notifications. It would not reconstruct lost authoritative results. Similarly, `evidence_extracted` and `version_committed` distinguish OCR evidence from a saved draft. A proposed `diff(V11, V12)` reads those two actual versions.

A ring buffer, watermark, or separate async sender can support this notification design. None removes finite pipe/storage limits. None permits an unbounded stream of lossless control replies while the receiver is absent. These names are explanatory event sketches. Final IPC framing and schema remain open.

The [integration guide](INTEGRATION_AND_MODEL_BOUNDARY.md#desktop-process-boundary) covers the desktop/native protocol ownership. This guide supplies the durability and finite-failure limits.

**Source basis:** EVT-0855, EVT-0878, EVT-1040, EVT-1068, EVT-1107, EVT-1147. ATT-21/22/27–ATT-30.

<a id="explicit-version-export"></a>
## 10. Explicit-version export and publication

Export operates on a specified saved version and effective scope. The conceptual delivery intent is `(version_id, scope_rev)` plus the defined destination/output choices. It must not silently become “whatever head is latest when packaging finishes.” If V10 is good and V11 is an experimental table edit, selecting V10 means exporting V10 even while work on V11 continues.

Delivery intent belongs to the current task, rather than one unqualified global selection on the source document. The document core owns committed versions and their provenance. The task owns which version and scope it chooses to deliver. Choosing an existing V10 must be expressible without creating a dummy edited V12. Selecting the just-created version can remain a convenience of a commit, but it does not replace direct existing-version selection. General branch UI or merge support is unnecessary to preserve this ownership distinction.

The host/CLI/UI can export existing saved content without another model call. The old `Workspace.export(document, version)` and CLI dispatch already demonstrated that responsibility. The rebuild should preserve the capability, not their exact API. Exhausted model tokens do not make saved content inaccessible. Export still consumes time/disk and has its own cancellation/publication behavior.

The proposed `export_package(version_id, destination, delivery_label)` named the same host-callable responsibility more explicitly. It chooses immutable content, an output destination, and an honest label without asking a model to regenerate or approve it. `finalize_run_node` named a possible caller inside the graph, not the sole owner or a guarantee that a finalizer always runs. Persisted intent and results let a host action perform or reconcile export after the inference loop stops.

The selected version determines Markdown, JSON, HTML, source-derived images/assets, and ZIP. Keep the relevant body/maps/assets consistent across representations. A draft remains labeled draft/partial with known gaps. Selecting/exporting it must not gain a hidden “full task complete” precondition. Likewise export success must not upgrade the content claim.

<a id="historical-package-members"></a>
### Historical package members

The earlier implementation used the following layout for one saved snapshot. These names illustrate member roles rather than fix the rebuild's filenames.

| Historical member | Role for the selected saved version |
| --- | --- |
| `document.md` | The saved Markdown reading content, with relative links to its required assets. |
| `document.json` | The structured document, version/source identity, page mapping, content status, Markdown, and asset metadata. |
| `preview.html` | The safe HTML reading preview generated from that saved Markdown and version. |
| `manifest.json` | The version identity and file-hash map for `document.md`, `document.json`, `preview.html`, and the referenced asset files. |
| `assets/<referenced-file>` | Zero or more referenced asset files from that saved version. The package excludes unrelated workspace assets. |

The ZIP contained `manifest.json` plus the files listed in its member map. An empty `assets/` directory was not a required ZIP entry. Final member names and layout remain open under Q3. The retained requirement is consistent artifacts and resolvable relative links for the explicitly selected version.

A proportionate consistency check compares intended members and actual bytes against the selected version. A manifest identity alone does not prove that files were written correctly or that the ZIP contains those same members. Source fidelity is a further content question. Package consistency cannot certify that every figure label or paragraph is correct.

Directory publication and ZIP publication are two effects. A rename of one cannot atomically publish both. Persist enough identity/intent/outcome to reconcile re-entry: which version/scope, destination, artifacts, and known completed publication belong to this operation. Preserve unrelated files and do not overwrite a different existing output merely because the original desired name is occupied. Exact output naming, idempotence/replacement behavior, and crash visibility remain Q3 choices.

<a id="export-publication-sequence"></a>
### Build, check, publish, and re-enter

The discussed requirements imply the following finite responsibilities. Their exact filesystem layout and transaction representation remain open:

1. Resolve and retain the export's specified immutable version, task/scope, content label, destination, and operation identity. If a later task selects another version, this export still refers to its original version.
2. Obtain the canonical document and its required assets. Build portable Markdown, document JSON, safe HTML, and the intended image set. Do not copy unrelated workspace files, credentials, requests, or logs into the package. Relative links must resolve within the delivered package.
3. Prepare the output directory and archive from that same selection. Keep draft/gap metadata consistent with the selected scope/version. Packaging does not regenerate missing source content or upgrade the completion claim.
4. Compare the intended member set and actual written files/ZIP member bytes with the selected result. Detect missing, extra, or differing members under the declared package contract. Checking only the manifest file's hash cannot detect a changed image or absent Markdown member.
5. Publish each declared output and retain its actual outcome/identity. The point at which the directory becomes visible and the point at which the ZIP becomes visible may differ. A single completed publication is not evidence that both finished.
6. On re-entry, first reconcile known publications and useful prepared files. If the directory is complete but the ZIP is unpublished, preserve the matching directory.

   Finish or rebuild only the unresolved archive work as the export contract permits. The destination may instead contain another operation's output. In that case, report the conflict or use an explicitly defined separate destination. Do not replace that output as if it belonged to this export.
7. Return the original export outcome when that same operation already completed. Replaying the export receipt neither moves the working head nor restores an old delivery selection over a newer one. A fresh export to another destination is a separate operation even when it contains the same version bytes.

This is separate from the immutable-version commit. A failed export can leave a valid saved version available for a later host action. A committed export receipt can outlive the currently selected delivery. The implementation must define what to report if an already-published file is subsequently removed or changed. Its historical receipt cannot honestly certify the present bytes without checking them.

An all-exit finalizer cannot promise packaging after hard termination, shutdown, cancellation, or every graph failure. Cancellation first stops new model/tool work. Whether a large already-running package operation may continue depends on the task's defined policy. A later host action can export saved work. Automatically producing the newest draft must not replace the explicitly selected delivery. All-exit packaging is not a V1 prerequisite.

**Source basis:** EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-23–ATT-30. SUP-05, SUP-06.

<a id="worked-recovery-sequence"></a>
## 11. Worked recovery sequence

This sequence combines the discussed boundaries to make their interaction explicit. It is an explanatory scenario, not a prescribed conversion workflow or claim of implementation.

1. Prepare logical decision Q using V10, chosen OCR evidence, route/settings, and tool schemas. Save that exact request. Before send attempt 1, record the consumed allowance.
2. Save a complete accepted response with a batch containing A and B. A edits V10 to produce V11. B previews the resulting intended version. The batch owner resolves their defined dependency. It does not let B read an unrelated future `latest`.
3. A stages/validates immutable content and commits V11's registration, promised head change, and operation receipt. The process stops before B and before the graph records full continuation.
4. Re-entry locates Q and its accepted response, so it sends no replacement model call. It returns A's original result and restores necessary current-batch effects. It determines that B remains unfinished.
5. If B has a complete suitable saved artifact, reuse it. If its local process outcome is uncertain, inspect/reconcile within the contract and stop if unresolved. Do not delete useful attempt output or blindly duplicate a process.
6. Once the entire batch is settled and applicable limits/cancellation permit, prepare the next model decision from current facts. If another legitimate later commit already made V12 current, neither A's receipt nor the old graph snapshot sets head back to V11.
7. The agent may select the older good V10 for delivery rather than the experimental V11/V12. Export uses that explicit version/scope. If inference is stopped, a host action can still package saved V10 under the export contract and honestly report its content state.

An unknown remote attempt before step 2 uses bounded model replay only when enabled and within original limits. An unknown local effect after step 3 uses effect-specific reconciliation. Their uncertainty and recovery permissions are different. Neither resets the job's accumulated budget.

<a id="q3-closure-and-implementation-order"></a>
## 12. Q3 closure and implementation order

The exact executable contract still needs to identify authoritative records and supported transitions for these boundaries:

- Prepared request, attempt, and accepted reply.
- Complete batch progress, operation effect/receipt, and graph/context completion.
- Stop/waiting/cancel and export publication. It must specify:

- How new intended judgments obtain identities, how recovery finds old ones, and which entry paths may continue a prepared request.
- Which input/configuration/defaults are frozen and how same-ID/different-input inconsistencies are rejected.
- How the whole accepted batch resumes, which graph completion forms are supported, and how stale effects avoid regressing later state.
- What save/selection/export commits promise, which prepared files can finish conditionally, and how local unknown outcomes stop with useful work preserved.
- How original attempts/turn/time/cancellation state persists, including wait/backoff accounting and configured unknown-outcome replay eligibility.
- How execution stop, content claim, and actual package outcome remain distinct and how explicit continuation is interpreted.

Choose finite behavior at these boundaries. Do not add universal migration, exactly-once remote generation, generalized branch coordination, mandatory process salvage, or all-crash recovery. The four-module/six-table sketch was incomplete because it did not assign all these responsibilities. That is not an instruction to build more tables. Existing checkpointer/journal/record facilities may supply them.

A useful first implementation increment connects a real bounded source/scope through shared Nexus/tools, candidate preservation, save/reopen, basic capacity behavior, and specified-version export. It should not postpone candidate retention until after the first validation failure. Nor should it postpone capacity until a document exceeds 40 pages. One inspect already reached 191,662 characters historically. Advanced DOM comparison conveniences, generalized concurrency, malformed-call extraction, cache tuning, reminders, and automatic exit packaging need not block that increment.

Later verification should inspect the actual contract boundaries and source-led saved/reopened/exported reading proportionately. Scripted mocks can exercise crash gaps and identity rules. They cannot establish model understanding, source fidelity, natural adoption, equal-quality savings, or installed desktop readiness. The old 228 checks and R1/R2 completed trials do not certify new integration. These suggested verification boundaries are not standing permission for live provider experiments.

**Controlling scope:** EVT-1148 and EVT-1166. The only unresolved first-version design areas remain Q1 document/reference semantics, Q2 capacity/handoff, and Q3 persistence/recovery/stop.
