# Rebuild contracts

These contracts consolidate the agreed boundaries and the final recommended tradeoffs in EVT-1166. The [implemented first-version contracts](#implemented-first-version-contracts) below select the exact schemas and transitions for Q1–Q3. The earlier mechanism examples remain explanatory. Additional mechanisms from the discussion retain their status in the reference records.

Detailed local explanations accompany these contracts: [document engine](design/DOCUMENT_ENGINE.md), [context and evidence](design/CONTEXT_AND_EVIDENCE.md), and [execution and delivery](design/EXECUTION_AND_DELIVERY.md). These explain data shapes, sequencing, examples and failure cases without requiring the chat export. Illustrative field names do not silently close open schema choices.

## 1. Document updates and candidate references

### Identity and original content

Keep source identities, derived evidence identities, received candidate identities, committed document versions and operation identities distinct. A content hash establishes byte identity, not ownership, scope, whether the agent saw the data, or whether it remains in the current document. An unqualified path, mutable `head`, timestamp or hash alone must not ambiguously select a source/version.

Preserve complete received native responses/tool arguments before framework parsing or tool schema validation can discard useful content. An accepted response and an executable tool call are later states. Framework tool middleware may run after native JSON parsing. Malformed calls may never reach that middleware. Retention therefore begins in the Nexus receiving layer, with dispatch-layer retention as an additional boundary.

Preserve what was actually received. Do not claim missing trailing content was saved. A rejected or incomplete call remains non-executable. A candidate reference identifies exact original content and its source operation/version/range. A repaired new request has its own identity.

### Edits and validation

The first version should support exact reuse of complete candidate content, pure insertion/append and partial page-map updates. Preserve unchanged body and metadata by default.

Apply a local metadata patch in this sequence:

1. Merge it into the explicitly named base version.
2. Validate the resulting complete map/structure.
3. Conditionally commit against the expected head.

A stale base must not silently become today's latest version. Do not require the model to regenerate all prose or resend a full map merely to repair one entry.

A referenced prior candidate is usable even if a later save exists. Adoption in an ancestor records historical use, not proof that every part survives in the current version. Unused candidate material need not all be adopted or explicitly rejected before a task can complete.

Distinguish reusing content from replaying operations. A `block_ops` object can delete/reorder/replace content. Copying its prose differs from executing that operation sequence against a changed base. Operations need applicability checks against the intended base. Literal patching must have defined target and match semantics. Unique byte matching prevents ambiguous replacement but does not establish semantic correctness.

The agent can choose a larger reconstruction when the source requires it. Local-edit support is an ergonomic capability, not a mandate to use the smallest edit. Logical output blocks do not dictate a token/chunk/storage size or require a complex semantic dependency graph.

### Commit and replay

Recommended body authority: immutable version files. SQLite owns version registration, head/pointers and the unique operation receipt. Stage the file payload. Validate it before the metadata commit that makes it visible. Define cleanup/reconciliation for files without a committed registration. Do not maintain a second independently mutable body as an equal authority.

Operation retries return the original committed receipt and its produced version. A newer head does not invalidate that receipt and must not be rewound. A receipt describes the historical operation. It is not a fresh selection/update of the current document. Validation rejection, successful commit and failure to build/return a model-facing projection are distinguishable outcomes.

No memory-only lock is a durable uniqueness guarantee. The first version uses one active writer per task plus persistent operation identity and short metadata transactions. SQLite ordering does not automatically serialize parallel graph-state `Command` updates. Graph policy updates must have a defined single writer.

### Partial-content salvage boundary

Preserving malformed originals is required. Automatically indexing complete subobjects from an incomplete response is a deferred useful option, not a first-version dependency. If added, automatic indexing must satisfy these conditions:

- Identify closed exact source spans within one attempt/call.
- Handle escapes, duplicate keys and array order.
- Preserve the original hash/span.
- Create a new valid operation for reuse.

Tolerant parsing that closes strings/braces, synthesizes defaults or merges attempts is not proof of a complete original subobject. Extractability is not source correctness.

## 2. Context capacity and handoff

### Two coordinated responsibilities

Evidence management controls what source results, images, OCR and saved content are loaded, kept, released and precisely retrieved. History compaction reorganizes older conversation/work history and continuation state. They share a capacity budget but are not the same operation.

The agent judges relevance and semantic continuation needs. The app observes capacity and requires organization when necessary. The app may prioritize releasable content. It does not judge semantic necessity from high OCR confidence, small text differences, completed page counts or storage presence.

Protect effective user requirements and later amendments, unresolved dependencies and useful work. Save unsaved useful material before removing it from input. Exact originals and references remain retrievable. Latest drafts and unfinished candidates may be partly released. They need not wait for a successor version or stay entirely resident.

### Assembled-request budget

Configure effective capacity and output reserve for the selected route/model. Assess the actual assembled request, including instructions, schemas, native message overhead, images, tool results, draft arguments and continuation state. An estimate is not an exact provider token count. Unknown native/image costs require explicit conservative handling. Unknown does not mean zero.

Do not infer the model's nominal window from a local estimate of a rejected request. A provider refusal may reflect endpoint limits, route mismatch, output reserve, image encoding or another error. Only supported diagnosis should trigger context-specific re-preparation. Generic HTTP 500/502 alone is not overflow evidence. Transport replay and context-changed re-preparation are distinct request operations, both charged to persistent task budgets.

### Release and rolling compaction

Prefer releasing saved content that is currently unnecessary, then compact older work history when needed. This is an ordering guide, not a mandatory field preset, permanent history-retention rule or unconditional immediate release after saving. Large authored arguments in assistant tool calls can dominate context just as tool results do.

Retain an immutable native journal. Build a separate valid model-input projection, keeping tool-call/result pairing and provider-required native items intact. Do not execute the projection as an original call. The app computes exact covered message/range identities and revision anchors rather than asking the summarizer to reconstruct bookkeeping.

A compaction request may cover only a fitting portion of history. Preserve uncovered history. Its result may be valid progress even if the total context is still above the normal-send threshold. Check reduction on the assembled context, including summary/reference overhead. Do not require each partial compaction to reach the final target. No fixed recent `K`, universal percentage, fixed two/three-summary guarantee or claimed 90% saving is selected.

Each compaction request has frozen input, task/step identity, attempt records, budget and cancellation checks through the same Nexus service. It cannot be a hidden untracked model call inside `prepare_step`. Apply a successful result against its intended history revision/coverage boundary.

On failure, preserve original records. Reassess the context. Do not silently erase input. Do not send the same oversized normal request.

### Continuation content

The recommended first-version handoff is self-sufficient for continuing the task: effective requirements, task/scope, current saved version, unfinished work/dependencies, useful candidate/evidence references and necessary cautions. It need not duplicate complete originals. It does not claim semantic losslessness merely because message IDs or schema validation pass.

A delta-only summary can omit information from an anchor only if it explicitly preserves that dependency. Do not adopt such summaries otherwise. The first-version recommendation avoids that dependency. Working notes, continuity snapshots, document state and recovery receipts can share references but have different purposes and lifecycles.

### State and caching

Keep small context policy in graph state as the single executor's policy authority, following EVT-0878. An additional external policy-version/activation system is unnecessary. Graph state should not retain transient hydration as messages.

Tools can report intents. One settlement writer applies them at a safe boundary and records the processed accepted batch. Any independent deltas still need explicit conflict rules. `max(policy_rev)` can silently discard parallel changes and is not a merge algorithm.

A global journal scan must not resurrect compacted tool history or old policy states. Service-owned request budgets, committed documents and external-effect receipts remain durable outside rollback of that graph state.

A model input view records what the app assembled for a request. Attempt records separately establish dispatch. Neither proves what the model understood. Request identity, attempts, accepted tool-batch identity, tool execution, message visibility and semantic source coverage are distinct. Stable IDs must survive retries and resume. Using a new recovery checkpoint as an accepted batch's identity can cause duplicate dispatch.

Prefer stable instructions, schemas, ordering and appendable prefixes where practical. Updating/removing tail-injected state also changes the prior request prefix. Putting dynamic state last does not guarantee cache preservation. Cache considerations cannot force useless history to remain resident, and smaller input cannot alone establish lower whole-task cost.

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
| A frozen request exists. No accepted reply exists. | Reconcile attempt/budget/cancellation state. Apply the configured bounded policy before another send of that request. |
| A complete reply is accepted. Its tool batch remains unfinished. | Resume the same accepted batch and its outstanding calls. Do not regenerate the reply or advance immediately to another model step. |
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

### Desktop progress and process boundary

Persist important results/receipts. Allow coalescing or dropping obsolete progress events. A bounded queue cannot simultaneously promise lossless unlimited events and never block when the consumer stops. Avoid coupling durable tool completion to UI stdout consumption. A reconnecting UI should read committed state.

Protocol output and diagnostics require a deliberate process/channel boundary, but mandatory first-line `os.dup2` was not established as the universal remedy. Native libraries, callbacks, threads and process shutdown need proportionate implementation checks. These considerations do not require a new distributed infrastructure or a separate network research phase before document/context contracts can be written.

## Implemented first-version contracts

These are the selected executable contracts as of 2026-10-23. They close Q1–Q3 at the design level. [CURRENT_STATE](CURRENT_STATE.md) records which behavior was tested. The first transport is non-streaming; the earlier dual-transport discussion remains a future compatibility boundary.

### Q1: document schema and commit

`schema.py` defines `Document` with `title`, `scope`, ordered `blocks`, a complete physical-page `pages` map, `claim` (`partial` or `complete`), and `known_gaps`. Each block has a stable task-local `id`, exact `markdown`, physical `pages`, and optional `source_note`. Each page has `printed`, `disposition`, and `note`. Disposition is `unprocessed`, `included`, `outside_scope`, or `omitted_non_content`. Printed labels remain strings; `unknown` and `none` have different meanings.

`edit_document` requires `base_version` and `expected_head`. Null selects the initial empty document/head. The base supplies content; the expected head is the commit precondition. The caller can deliberately select a different saved base, but a stale expected head fails without overwriting newer work. Omitted content and metadata remain unchanged. `replace_blocks` replaces the full ordered list; `reuse_candidate` copies the exact list at a task-owned candidate's RFC 6901 JSON Pointer. These alternatives cannot be combined. Neither replays the candidate's old operation.

Sequential `operations` support `insert` after an existing ID (null means beginning), `replace`, `delete`, and `patch`. Patch offsets are zero-based, half-open Unicode code-point positions in the current block after earlier operations in this request. `expected` must match exactly. `page_updates` merges only supplied page fields before validating the entire result. The tool schema exposes the page fields and disposition values to the model.

Every accepted call's raw argument string is retained as `candidate:<request>:<call-index>` before domain validation. Reuse works after rejection or a later save. The full native response is retained earlier, before native parsing. Invalid and truncated calls remain non-executable.

The document core writes immutable version files, flushes them, then commits the version registration, head and original operation receipt in one SQLite transaction. Unregistered prepared/version directories remain preserved but invisible; there is no automatic destructive cleanup. A replay returns its original receipt/version without rewinding a newer head. The whole Markdown document is parsed together, so cross-block references and footnotes can resolve. Preview sanitization does not rewrite saved Markdown. Image links must name registered local assets; version files and exports preserve those bytes.

`complete` is an agent content claim with structural checks: no known gaps or unprocessed pages, output provenance for included pages, and a note for outside-scope/non-content pages. These checks cannot establish source fidelity. Partial versions can be saved and exported at any time.

### Q2: context transitions

Graph state holds request IDs, the handoff reference, history revision, released/pinned references, continuity notes and compact response-correction entries. Full native responses, candidates, evidence, feedback and frozen inputs remain in immutable external objects. Request assembly is transient. Native call/result pairs and required reasoning items remain in the projection. Released authored arguments become explicit archive references only in that projection; execution always uses the original accepted call.

The current portable estimator charges the UTF-8 byte length of the complete assembled non-image payload, plus 1,024 units and a configured allowance per native image. It then reserves configured output capacity. This is a conservative heuristic, not provider token usage or a proven upper bound for every route. Missing image allowances block a pixel request. Capacity values must be configured for the route; a generic HTTP failure does not change them.

`context_update` lets the agent release/pin complete saved results, candidates or images and replace its continuity notes. Release changes input retention, not storage. One writer settles intents in accepted batch order. If normal input still exceeds capacity, the app chooses a fitting oldest complete batch prefix for compaction. It does not remove pinned prefix material. If a single batch is too large, its exact bodies can be explicitly deferred to saved references for the summary request; their semantic relevance remains unresolved. If no fitting segment exists, execution stops with `capacity_blocked` and keeps all work.

The summary request uses the same frozen-request service, budgets and cancellation gate. Its six fields are `task`, `current_state`, `unfinished_work`, `dependencies`, `references`, and `cautions`, each a string or string list. The replacement must carry needed facts from its predecessor. The app records exact covered request IDs, source references, deferred bodies and history revision independently of the summary text.

A handoff applies only to the matching prefix/revision and only if it reduces the entire normal input, including its own references. It can apply even when more compaction is needed. Uncovered history remains. A schema, revision, reduction or request failure leaves the previous context active. Model-authored schema/reduction failures and unexpected compaction tool calls receive bounded correction feedback; state conflicts and storage faults are not treated as model mistakes. A new fitting compaction request includes the diagnostic and original covered history. The rejected candidate text is included only if the complete payload still fits; otherwise its exact reference and omission status remain explicit. Compaction tools are never dispatched. Original handoffs and their archive links remain retrievable. Schema validity and net reduction do not prove semantic completeness.

### Q3: execution, recovery and delivery

`catalog.sqlite` owns jobs, requests, attempts, operation receipts, version registration and exports. `graph.sqlite` owns LangGraph checkpoints with synchronous durability. External immutable objects own the retained bytes. A cross-process file lock permits one task executor; manual editing uses the same lock. Independent jobs can run separately. These stores do not form a shared transaction.

Request identity is `<job>:<sequence>:<revision>`; member operation identity appends the accepted call index. A frozen request wins on node re-entry. An accepted reply wins over a new send. The receiver reconciles an already saved `accepted:<request>` object if its request pointer was not committed. The dispatcher similarly reconciles `result:<operation>` before repeating work. A committed document can reconstruct its missing projection from the atomic original receipt. A complete batch replays its deterministic context intents before proceeding. An interrupted OCR/script operation without a settled result stops as `local_outcome_unknown`.

Attempts and request-budget consumption commit before dispatch. Defaults are 80 model attempts, 7,200 active seconds, no automatic transport retry, and no unknown-outcome replay. Optional bounded transport replay applies only on re-entry and retains the original limits. Normal, compaction and response-correction calls share the gate. Active-time and cancellation checks also precede new tools. Network waits are polled locally for stop/budget conditions. An abrupt process death leaves an unresolved interval that is conservatively charged through restart; a local stop never establishes remote cancellation or known cost. The offline-time overcharge and updates to limits on existing jobs remain known defects outside the response-correction increment.

A no-tool answer is retained in history and schedules application continuation feedback. `report` selects `complete`, `partial`, or `waiting`; completion requires an explicit structurally complete saved version. An existing question must be reported as waiting, without inventing a user answer. The run stop reason, selected version's claim and export verification remain separate. Reopening does not itself resume or spend inference. The user can resume, reply, or export saved work.

`max_response_repairs` defaults to 2 and can be configured for new tasks in Connection settings; zero disables automatic corrections. It bounds correction requests following consecutive text-only normal replies and, independently, consecutive invalid handoffs. A settled normal tool batch clears the normal counter; a valid applied handoff clears the compaction counter. This is not a detector of semantic progress in arbitrary tool loops. The default is an adjustable engineering choice, not a measured optimal number or a quota on source-reading methods.

Each failure retains immutable `repair:<request>` feedback with its original accepted-response reference, diagnostic, count and basis (current document head and user amendments). Graph state carries a reference to that record. A correction changes context and receives a new request identity; it is not a resend of the accepted response. A restart or plain Continue does not reset the count. A new user amendment or edited document head starts a new correction episode at `prepare`; consumed attempts and time never reset. Exceeding the correction allowance yields `response_repair_exhausted`, preserves all work, and sends no further request. Reopening an exhausted episode alone cannot replenish it.

Handoff archives use `handoff:<request>` identities. `response_correction` and `context_compacted` events have transactional deduplication receipts in `catalog.sqlite`. These cover replay after feedback/handoff persistence but before graph checkpoint completion. The graph and catalog still do not share a transaction. Truncated native responses, unknown transport outcomes, large-result deferral, prepared-request replacement and general no-progress tool-loop detection are not changed by this increment.

Export takes an immutable version and an explicit external ZIP path. It verifies actual ZIP names and bytes against that version, publishes without replacing an existing unrelated file, and reconciles an existing known export. Markdown, structured document, preview, manifest and assets come from that version. It needs no model call. The local filesystem must support the current exclusive hard-link publication operation; other filesystem publication strategies are unverified.
