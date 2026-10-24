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

### Desktop progress and process boundary

Persist important results/receipts. Allow coalescing or dropping obsolete progress events. A bounded queue cannot simultaneously promise lossless unlimited events and never block when the consumer stops. Avoid coupling durable tool completion to UI stdout consumption. A reconnecting UI should read committed state.

Protocol output and diagnostics require a deliberate process/channel boundary, but mandatory first-line `os.dup2` was not established as the universal remedy. Native libraries, callbacks, threads and process shutdown need proportionate implementation checks. These considerations do not require a new distributed infrastructure or a separate network research phase before document/context contracts can be written.

## Implemented first-version contracts

These are the selected executable contracts, with Q1 and Q3 updated on 2026-10-24 for version-bound editing, local candidate reuse and explicit continuation boundaries. They close Q1–Q3 at the design level. [CURRENT_STATE](CURRENT_STATE.md) records which behavior was tested. The first transport is non-streaming; the earlier dual-transport discussion remains a future compatibility boundary.

### Q1: document schema and commit

`schema.py` defines `Document` with `title`, `scope`, ordered `blocks`, a complete physical-page `pages` map, `claim` (`partial` or `complete`), and `known_gaps`. Each block has a stable task-local `id`, exact `markdown`, physical `pages`, and optional `source_note`. Each page has `printed`, `disposition`, and `note`. Disposition is `unprocessed`, `included`, `outside_scope`, or `omitted_non_content`. Printed labels remain strings; `unknown` and `none` have different meanings.

`edit_document` requires `base_version` and `expected_head`. The base supplies content; the expected head is the commit precondition. Default `mode="edit"` requires both identifiers to match, including null/null for an initial document. A mismatched ordinary edit fails with repair guidance and retains its candidate. The agent may explicitly choose `mode="rebuild"` to start from another task-owned saved version or a null (empty) base. This requires no separate human approval and imposes no reconstruction-size limit. Both modes still compare `expected_head` with the actual head inside the commit transaction. A stale expected head fails without silently rebasing or overwriting newer work. The saved document envelope records `edit_mode`, `parent` (the content base), and `expected_head`; the receipt also identifies the mode. These establish the requested operation, not semantic correctness.

Omitted content and metadata remain unchanged relative to the named base. `replace_blocks` replaces the full ordered list; top-level `reuse_candidate` copies a block list at a task-owned candidate's RFC 6901 JSON Pointer. These alternatives cannot be combined. Neither replays the candidate's old operation.

Sequential `operations` support `insert` after an existing ID (null means beginning), `replace`, `delete`, and `patch`. Each insert/replace supplies exactly one non-null content source: `blocks` or `reuse_candidate: {ref, pointer}`. A local candidate pointer selects one `Block` or a list of `Block` objects, such as `/operations/0/blocks` or `/operations/0/blocks/0`. The resolver checks task ownership, candidate kind, pointer syntax and block schema. It copies only those blocks, without importing other operations or rejected metadata. Existing target, unique block ID, page and asset checks still apply to the merged result. Candidates remain reusable after later versions are saved. Invalid inputs retain their new candidate and leave head unchanged. An empty block list is allowed as an explicit operation, not mistaken for a missing content source.

Patch offsets are zero-based, half-open Unicode code-point positions in the current block after earlier operations in this request. `expected` must match exactly. `page_updates` merges only supplied page fields before validating the entire result. The tool schema exposes the page fields, disposition values, edit modes and candidate-content choices to the model.

Every accepted call's raw argument string is retained as `candidate:<request>:<call-index>` before domain validation. Reuse works after rejection or a later save. The full native response is retained earlier, before native parsing. Invalid and truncated calls remain non-executable.

The document core writes immutable version files, flushes them, then commits the version registration, head and original operation receipt in one SQLite transaction. Unregistered prepared/version directories remain preserved but invisible; there is no automatic destructive cleanup. A replay returns its original receipt/version without rewinding a newer head. The whole Markdown document is parsed together, so cross-block references and footnotes can resolve. Preview sanitization does not rewrite saved Markdown. Image links must name registered local assets; version files and exports preserve those bytes.

`complete` is an agent content claim with structural checks: no known gaps or unprocessed pages, output provenance for included pages, and a note for outside-scope/non-content pages. These checks cannot establish source fidelity. Partial versions can be saved and exported at any time.

The desktop treats a selected version as ready only after loading content with the matching task and version identity. Pending/failed reads hide the previous content and disable editing/export; failed reads have a local retry. Late responses for previous selections are ignored. An edit session captures the loaded base, expected head, mode and draft blocks together. It remains bound to them if the head advances. Save uses the session's captured fields; a conflict retains the draft and the backend candidate. Version/task switches are disabled while editing until save or explicit discard. Historical versions offer **Rebuild from this version**, with an explanation that later content is not included. Manual saves remain partial claims. Export always targets the loaded saved version; unsaved edits are excluded and identified as such in the editor.

### Q2: context transitions

Graph state holds request IDs, the handoff reference, history revision, released/pinned references, continuity notes and compact response-correction entries. Full native responses, candidates, evidence, feedback and frozen inputs remain in immutable external objects. Request assembly is transient. Native call/result pairs and required reasoning items remain in the projection. Released authored arguments become explicit archive references only in that projection; execution always uses the original accepted call.

The current portable estimator charges the UTF-8 byte length of the complete assembled non-image payload, plus 1,024 units and a configured allowance per native image. It then reserves configured output capacity. This is a conservative heuristic, not provider token usage or a proven upper bound for every route. Missing image allowances block a pixel request. Capacity values must be configured for the route; a generic HTTP failure does not change them.

`context_update` lets the agent release/pin exact saved objects and replace continuity notes. Release changes input retention, not storage. The model-facing `pin` array contains explicit selections: `{"ref":"...","view":"index|image|full|raw"}` with optional `json_pointer`, `start` and `end` for precise content. `index` injects reference, kind, byte size, provenance and a retrieval instruction; it makes no full-content claim. `image` injects saved native pixels and requires a vision route with a configured image allowance. `full` injects complete JSON/text, or an exact field and/or half-open string/array range. A candidate's full root view preserves its authored UTF-8 syntax; root ranges use Unicode characters. `raw` injects Base64 bytes, optionally a half-open byte range; it cannot use JSON Pointer. An encoded `image_stream` also has byte semantics for `full`. Display-image files require `image`, `raw` or `index`, rather than treating image metadata as full pixels. Index/image views reject selectors. Invalid selections reject the update. Bare references from retained calls/checkpoints keep the existing kind-derived full/image representation; new tool guidance asks for explicit selections.

Several selections of the same reference in one update are retained together and replace that reference's prior selections. Other references stay pinned. Release removes all selections of the named reference; a subsequent pin in the same update takes precedence. Pins hydrate in a separate transient section independently of their original history. Historical occurrences identify the selected representation instead of duplicating the entire body, and `body_in_context` is false when only an index or partial selection is pinned. Pinning a result does not recursively load referenced objects. Image pixels are explicitly absent from text-only compaction requests and restored in normal input; a new image pin on a text-only route is rejected.

**Admission precedes application.** The runtime supplies the current policy to a transient preflight in `Context`. The proposed whole update (including release and notes) is assembled through normal input selection, with task instructions, handoff, history, tool schemas, native images and output reserve. Native call identities and their projected arguments/results are included; context-update arguments use explicit exact archive references and their outcomes use visible control receipts. Later unsettled tools have explicit placeholders and are listed in `unsettled_operations`; their future results are not known. Receipt size is included in the estimate. Invalid selections and proposals whose required policy cannot fit return `ok=false` before changing policy; all previous pins, releases and notes remain active. Full result references expose capacity diagnostics and alternatives such as an index, exact range or corresponding `image_ref`; Base64 stream cost remains explicit in tool guidance. No full pin silently becomes an index, and no expiration or automatic unpin is introduced.

**History-pressure proposals remain inactive.** When full input cannot be admitted but the exact proposed required policy fits, the tool saves `context_proposal` in its immutable result, even if current settings prevent compaction. `ok=true` acknowledges saved work, while `admission.applied=false`, `status="awaiting_admission"` and `policy_unchanged=true` explicitly deny application. Graph state retains `context_waiting`, the proposal result reference. It never depends on the model repeating the intent in its summary. Full policy/candidate records remain external and readable.

Admission compares proposed and active policy against the same history, settled results, placeholders and outcome envelope. An update cannot admit itself merely by making additional previously visible bodies individually too large: those additional capacity deferrals lead to saved intent and compaction. Explicit agent-selected releases and pin representations are honored. Context-update native arguments are clearly labeled exact archive references; their result projection always includes a small applied/waiting/rejected control receipt and full-result reference. Complete authored arguments, policies and diagnostics remain immutable and readable. This avoids duplicate large notes/policy bodies without silently replacing a requested full pin or deferring its control status.

Subsequent valid updates while waiting compose in accepted call order against that proposed policy. They link to the previous proposal; later notes replace earlier notes, and release/pin keep their existing selection semantics. This pending chain is one atomic proposed policy at settlement. Invalid or irreducibly oversized later updates reject without erasing the earlier chain or changing the active policy. Other tools and explicit reports retain their normal behavior; a report can stop with an unapplied proposal still saved.

At an unfrozen request boundary, `coordinate` first restores a committed decision or preflights the exact composed proposal against the current handoff/history, schemas, image allowance, output reserve and bounded outcome. A fitting result with no additional unselected deferrals applies without compulsory compaction. Otherwise, a durable `context_check` records a waiting observation, its source state, route, instructions, head, reason and diagnostics. `compaction` means another reduction can run; `capacity_blocked` or `capacity_configuration` requires settings/instructions to permit another check. These observations are not immutable terminal decisions: Continue rechecks an unfrozen waiting step. A temporarily unusable active required input or unavailable compaction input retains the pending intent. If active required input can work but proposed required content cannot fit, or the selection is invalid, settlement rejects with a precise result reference. Invalid initial/oversized updates still reject before replacing an earlier pending chain.

`coordinate` checkpoints the decision or waiting observation before `prepare` assembles/freezes a request. A subsequent capacity failure cannot leave a committed terminal decision presented as pending in the graph. New instructions may supersede pending intent even if its outcome cannot currently be sent; decision validity and outcome delivery are separate. Reopening must not resurrect a rejected/superseded chain. Complete diagnostics remain in the immutable settlement. Existing full-only settlements also project a bounded status/reference receipt without rewriting the original. Normal/compaction inputs receive only status, applied flag, proposal/receipt references and a fixed reason code. While waiting, normal admission reserves the complete native envelope of a bounded prospective outcome, with actual references and room for reason/slot lengths. `outcome_reserve` reports this additional charged estimate; it is not token usage. Future settings/instructions still require a fresh capacity check.

Compaction normally uses active notes and selections. Explicit releases in a valid pending chain may reduce a labeled, transient compaction view without applying any part of the policy. Original selections, pending intent and bytes remain saved; final whole-policy admission is still required. A final handoff must leave room for a feasible pending policy and outcome. Otherwise bounded handoff correction preserves the old history and rejected candidate. When history is empty but a handoff remains, a handoff-only compaction can reduce it. Every accepted compaction must strictly reduce assembled input, and existing request/time/repair budgets remain in force. No-progress, interruption or exhaustion preserves pending work; it does not reset consumption or force semantic loss to meet a size target.

New human amendments supersede a proposal chain that has not settled. An already committed settlement is a historical effect and is recovered even after newer amendments or limit changes. `context-settlement:<request-slot>` stores its source state basis, applied/rejected/superseded outcome and compact graph changes. Recovery validates that basis and replays the outcome, including across the settlement/event/freeze/checkpoint gaps and an amended unsent-request transition. A request already frozen without a settlement is used unchanged; proposal coordination does not rebuild it or bypass unknown-outcome replay gates. A separate `context_feedback` reference exposes the eventual outcome without rewriting the original awaiting-compaction tool receipt. It stays in normal input and intervening compaction until a subsequent tool batch settles.

Accepted and rejected decisions are immutable tool receipts. Only successful receipts carry the resulting compact `context_policy`; the single graph writer restores them in accepted batch order, including after the receipt/pointer/checkpoint gap, without a new admission decision under changed instructions or limits. A dispatcher without runtime state cannot apply context updates. Checkpoints contain references/selections and notes, not hydrated bodies. The next actual request is checked again before freezing because later tools, amendments or settings can change its size. Rejection alone does not repair an already oversized old context or guarantee that future results will fit. The estimator remains the documented UTF-8/image heuristic, not provider token usage or a proven universal bound.

Normal assembly first tries the complete selected input. If it does not fit, the app assesses each unpinned, unreleased argument/result/image against the required anchor, current handoff, pins, feedback, tool schemas and its native batch scaffold, with the other unprotected bodies in that batch represented by references. Only a body that cannot fit in this input is capacity-deferred; no text is silently sliced and no fixed field subset is selected. If that minimum scaffold itself cannot fit, normal assembly leaves this case to compaction. This is a mechanical size decision, not a judgment that the body is irrelevant. Multiple individually fitting bodies that overflow in aggregate are not automatically evicted. The complete assembled request is checked again before freezing; remaining history pressure uses compaction.

A deferred result records `body_in_message=false`, `body_in_context=false`, its exact result/candidate references, saved byte size, original warnings and coverage, result keys, and a full-read tool argument. For a saved evidence selection, `source_view` preserves its source reference, pointer/range and original selection metadata; `body_in_message=false` distinguishes that saved selection from delivered evidence. `value_keys` supplies navigation for an object-valued selection, not a fidelity claim. Nested and outer warning/coverage fields are retained separately when both exist. Authored arguments become explicitly labeled `archived_arguments_ref` projections. Omitted pixels keep their image reference and an absence notice. Full/raw/field/range access remains available from the complete immutable originals; a later oversized full read may also need deferral. Exact field/range reads are selectable without a compulsory summary, index, OCR or script stage. Frozen normal-request metadata records the before-admission estimate, selected capacity deferrals and pinned references; graph state does not acquire the hydrated bodies.

Compaction selects a fitting oldest complete batch prefix. A pin does not stop that prefix: its complete selected object is independent of the history and survives application of the handoff. Normal and compaction assembly share per-object projection logic, but measure their own actual envelopes. Compaction measures the anchor, previous handoff, pins, correction feedback, already selected batches and the proposed batch. It first defers individually unfit objects, then, if aggregate pressure remains, defers the object with the largest measured saving until the segment fits or no improving projection remains. It retains fitting objects in the same batch, never slices their text, and does not re-project earlier selected batches or silently release pins. This size-based compaction projection does not change normal admission's rule against evicting individually fitting bodies under aggregate pressure. Frozen compaction metadata and the handoff archive record each affected request and exact deferred references; their semantic relevance remains unresolved.

A later batch that fits alone but cannot join the selected prefix stays uncovered when that prefix offers body reduction in normal input. The app checks this mechanically against each selected batch's normal projection and its all-reference form. If the prefix contains only references with no positive body saving, compaction instead attempts to include a per-object projection of the next batch in the actual remaining space. There is no fixed minimum prefix/summary size, field whitelist or semantic usefulness claim. Actual handoff acceptance still checks the complete normal input, including replacement of the previous handoff. If required instructions plus pins exceed normal capacity, or no fitting compaction segment exists, execution stops with `capacity_blocked` and preserves the exact pins and all work. It does not claim that a larger context limit was discovered.

The summary request uses the same frozen-request service, budgets and cancellation gate. Its six fields are `task`, `current_state`, `unfinished_work`, `dependencies`, `references`, and `cautions`, each a string or string list. The replacement must carry needed facts from its predecessor. The app records exact covered request IDs, source references, deferred bodies and history revision independently of the summary text.

A handoff applies only to the matching prefix/revision and only if it reduces the entire normal input, including its own references. A partial reduction can apply while uncovered history remains, even if another compaction is needed. A handoff covering the last history batch must additionally produce fitting normal input; otherwise it is archived but rejected, preserving the previous active history/handoff for bounded correction. This prevents the demonstrated oversized-input/empty-history dead end without demanding that every partial pass reach the final target. A schema, revision, reduction or request failure leaves the previous context active. Model-authored schema/reduction/final-capacity failures and unexpected compaction tool calls receive bounded correction feedback; state conflicts and storage faults are not treated as model mistakes. A new fitting compaction request includes the diagnostic and original covered history. Rejected candidate text is considered only after selecting that history and is included only if the complete payload still fits; it cannot displace selected evidence. Otherwise its exact reference and omission status remain explicit. Compaction tools are never dispatched. Original handoffs and their archive links remain retrievable. Schema validity, net reduction and fitting capacity do not prove semantic completeness.

An application receipt, not the existence of a handoff archive, establishes that a handoff was applied. If that receipt committed before the graph checkpoint, re-entry first checks the same prefix/revision and immutable archive. It then recovers the original transition using the receipt's historical before/after estimates; it does not recalculate those historical facts from a changed amendment or document head. The receipt must still match the covered requests and archive reference. Rejected or merely archived candidates have no successful application receipt and must undergo normal validation. After recovery, `prepare` assembles and checks current input with the latest amendments/head. A previously accepted transition neither grants capacity for new input nor authorizes another model send. Pins, uncovered history, original bytes and task consumption remain intact.

### Q3: execution, recovery and delivery

`catalog.sqlite` owns jobs, requests, attempts, operation receipts, version registration and exports. `graph.sqlite` owns LangGraph checkpoints with synchronous durability. External immutable objects own the retained bytes. A cross-process file lock permits one task executor; manual editing uses the same lock. Independent jobs can run separately. These stores do not form a shared transaction.

Request identity is `<job>:<sequence>:<revision>`; member operation identity appends the accepted call index. Same-request re-entry uses frozen bytes. An accepted reply wins over a new send. The receiver reconciles an already saved `accepted:<request>` object if its request pointer was not committed. The dispatcher similarly reconciles `result:<operation>` before repeating work. A committed document can reconstruct its missing projection from the atomic original receipt. A complete batch replays its deterministic context intents before proceeding. An interrupted OCR/script operation without a settled result stops as `local_outcome_unknown`.

Each frozen request records `instruction_basis`, the hash of its ordered user amendments. Tool writes and head changes alone do not supersede their own batch. Before each uncompleted call, compare that basis with current amendments. When they differ:

- A completed operation returns its original receipt and required context intent. Its effect is not undone or repeated.
- An unstarted operation saves its original candidate and a durable `skipping` marker, then a paired result with `ok=false`, `skipped=true`, `execution="not_started"` and reason `superseded_by_user_amendment`. The candidate remains available for the agent's next decision. Every accepted call retains its native result pairing.
- A started operation without a recoverable receipt cannot be labeled unexecuted. It stops as `local_outcome_unknown`, with original files retained. This increment does not add general local-effect reconciliation.

After the batch settles, historical context intents are restored. An old `report` receipt remains historical but cannot terminate new instructions. The next model request contains the latest amendments and outcomes; the agent chooses its method, tool and reconstruction scope. A plain Continue without an amendment resumes the original accepted batch. A same-text new amendment is still a new entry in the ordered amendment list.

The user's Start/Continue API permits a new request after `http_error` or `rejected` (including a complete transport carrying a truncated or malformed native reply). No calls from a rejected reply execute. An amended prepared request with no send attempts can also be superseded. Before graph advancement, an immutable `continuation:<old-request>` receipt stores the reason, diagnostic, retained native-response reference when available, attempt IDs and next revision. Graph state carries its reference; LangGraph `update_state(..., as_node="model")` resumes through `prepare`. Re-entry recovers this recorded choice instead of requiring another click. Normal or compaction input carries the continuation feedback. Old requests, accepted history, candidates and versions remain available; old frozen bytes are never rewritten.

Plain process re-entry does not independently authorize a new request after an HTTP/rejected failure. `unknown` or `in_flight` requests cannot use this new-ID path, even with new amendments: the original request, frozen input and configured replay gate remain authoritative. Accepted bytes take precedence over either path. HTTP failure is not proof of zero cost or remote cancellation. Error bodies are withheld to protect credentials; status/diagnostic and unknown usage remain recorded.

Attempts and request-budget consumption commit before dispatch. Defaults are 80 model attempts, 7,200 active seconds, no automatic transport retry, and no unknown-outcome replay. Optional bounded transport replay applies only on re-entry. Each newly frozen request stores its `replay_policy` (`replay_unknown`, `max_attempts_per_request`) alongside its original route and payload. Its original gate governs subsequent attempts even if task-level values differ. Preserved pre-snapshot requests use the task recovery policy, which settings updates cannot change after any request is prepared. Normal, compaction and response-correction calls share current task total allowances. Active-time and cancellation checks also precede new tools and poll network/child-process waits. A local stop never establishes remote cancellation or known cost.

### PDF coordinates and image delivery

`inspect_pdf` uses PyMuPDF **unrotated page points, top-left origin** for `rect`, text/image bounding boxes and extraction content. `rotated_rect`, `rotation`, `rotation_matrix` and `derotation_matrix` separately describe the displayed page. A CropBox offset does not change the contract to absolute PDF coordinates. Native extraction fields and complete originals are retained; coordinates are not rounded or rewritten inside extracted content.

`render_page(region=...)` and `ocr_page(region=...)` accept that same unrotated frame. Omit the region for the complete visible page. Rendering converts the region to the rotated page rectangle internally and keeps the source page orientation. The result records both `region` and `rotated_region`, actual integer `pixel_origin`, dimensions, DPI, `page_to_pixel` and `pixel_to_page`. Each mapping is a six-number affine matrix `[a,b,c,d,e,f]`: `x'=a*x+c*y+e`, `y'=b*x+d*y+f`. Pixel coordinates refer to the saved image's top-left origin; pixel centers are at half-integer positions. The transform uses MuPDF's actual raster origin, including fractional-clip rounding. OCR output boxes remain image pixels and can be mapped back with `pixel_to_page`. OCR recognition quality is not established by a correct crop.

`extract_image` separates a display image from original encoded PDF streams. The unchanged source PDF remains authoritative. Before deriving the display image, the app retains exact `xref_stream_raw` bytes for the image and any SMask as task-owned `image_stream` objects. Each stream records its source hash/reference, xref, filter, object dictionary, role and extraction version. These are encoded PDF streams, not a claim that every stream is a standalone image file; color-space and other indirect dependencies remain in the source PDF.

The returned `asset_path`/`image_ref` selects a native-dimension display asset. Compatible unchanged embedded JPEG bytes stay unchanged. Other cases decode the PDF image directly and use PNG; CMYK converts to RGB before a source soft mask is composed, and JPX is delivered as a browser-readable PNG. The app does not publish the RGB JPEG that `Document.extract_image()` may reencode from CMYK. Provenance records `representation`, `original_bytes_equal`, `original_ref`, `originals`, color conversion, source/display bit depth, mask xref, decoder version and actual steps. PNG encoding is lossless for the decoded samples; it does not make preceding color conversion lossless. The bounded verified image cases use 8-bit components. Higher-depth decoding is explicitly warned about and retains encoded originals; preservation of high-depth display precision and arbitrary PDF image/color semantics is not certified by these checks.

A stencil (`ImageMask`) is a coverage component whose appearance depends on the page graphics state. Default extraction returns `representation="stencil_mask"`, `display_semantics="coverage_only"`, explicit warnings, `image_ref` and original streams, **without an `asset_path`**. The component remains readable as native pixels or exact bytes but is not registered as a faithful deliverable figure. `occurrences` lists each placement on the selected page, with zero-based occurrence number, unrotated region, image-to-page transform and retrieval arguments. The same xref can have different paint colors at different occurrences.

The agent may select `extract_image(page, xref, occurrence, dpi)`, call `render_page` for its chosen region, or use another source-led method. An explicit occurrence uses the shared page renderer and produces a registered PNG of that region with page rotation, paint, background and overlapping content preserved. Provenance identifies `rendered_occurrence`, source image kind, source/xref, selected occurrence and region, any page clipping, DPI, affine mappings, original streams, decoder and a warning that the crop is not an isolated embedded image. `original_bytes_equal=false` distinguishes rendered appearance from the retained stream. No occurrence is chosen automatically. Native extraction dimensions do not describe this DPI-selected rendered crop.

Images support native display-pixel reads and exact `view='raw'` byte ranges. Encoded stream `full`/`raw` reads return Base64 bytes with half-open byte ranges, while `index` exposes metadata. JSON Pointer remains available for structured evidence; a pointer on a binary stream is rejected explicitly. No summary gate, compulsory extraction method, resampling rule or agent tool quota is added.

Saving a document includes only its referenced display assets and their associated original image/mask streams. The version's `originals` map records their provenance and portable paths, `originals/<xref>-<hash>.<extension>`. Xref preserves source-object identity even when distinct streams have identical bytes. The manifest covers these files, and reopening and ZIP export verify them with the same immutable-version machinery as Markdown and images. Original streams are not inserted as broken preview images. The complete source PDF remains in the task store; it is not automatically copied into the delivery ZIP.

### Existing-task settings and active-time accounting

The authenticated `POST /jobs/{job}/settings` API changes a stopped task under the same cross-process task lock used by execution and editing. Start/Continue may also explicitly supply settings. Validation and a `task_settings` before/after record commit with the job update in one catalog transaction. Settings writes never change attempts, known active seconds, amendments, saved versions or frozen requests. Empty/omitted fields retain their effective values; invalid or disallowed changes reject the entire update.

Before any request is prepared, validated route/limit settings can be changed. Once a request exists or any attempt is consumed, only `context_tokens`, `output_tokens`, `image_tokens`, `max_requests` and `max_active_seconds` can change. Capacity settings apply to newly prepared requests; an existing request, including a never-sent prepared one, retains its original route, bytes and applicable replay limit. Changing a total allowance does not add per-request replay attempts or extend a correction episode. Protocol, endpoint, model, vision mode, generation parameters, timeout, recovery and correction policy changes are outside this existing-task update contract.

The desktop's **Task limits** dialog edits those five supported values for the selected task and displays effective values and consumed usage. Connection settings supply defaults for an unconfigured task; Continue on a configured task uses its saved settings. Updating global defaults does not silently replace them. GET job responses include effective route/limits, per-request frozen route/replay policy, and recorded unknown active-time intervals.

`active_seconds` is known monotonic elapsed time within active invocations, including model/tool waits, not CPU time or a provider bill. `ActiveTime` checkpoints at preparation, tool boundaries and request entry, and approximately once per second while polling network/child-process waits. Each short transaction adds the measured delta and advances `active_since`, the last durable wall-clock observation. In-process budget checks include the not-yet-checkpointed monotonic delta. Normal shutdown settles the remainder and clears the active marker. User waiting between invocations is not active execution.

After hard termination, restart atomically preserves any stale marker as an `active_time_gap` record and starts a new interval. The record retains both wall observations, their signed difference, `active_seconds=null` and `budget_policy=known_active_only`. The wall span is not an active-duration measurement; clock changes can affect it. All previously recorded consumption remains charged. The uncertain tail is neither charged as all downtime nor recorded as zero work. The budget uses known active seconds, and the UI/API disclose the unmeasured intervals. A crash during a long uncheckpointed in-process operation can leave a substantial unknown tail; this policy is not a strict lifetime-work or cost bound. Gap creation and marker replacement commit together, preventing duplicate settlement on re-entry.

A no-tool answer is retained in history and schedules application continuation feedback. `report` selects `complete`, `partial`, or `waiting`; completion requires an explicit structurally complete saved version. An existing question must be reported as waiting, without inventing a user answer. The run stop reason, selected version's claim and export verification remain separate. Reopening does not itself resume or spend inference. The user can resume, reply, or export saved work.

`max_response_repairs` defaults to 2 and can be configured for new tasks in Connection settings; zero disables automatic corrections. It bounds correction requests following consecutive text-only normal replies and, independently, consecutive invalid handoffs. A settled normal tool batch clears the normal counter; a valid applied handoff clears the compaction counter. This is not a detector of semantic progress in arbitrary tool loops. The default is an adjustable engineering choice, not a measured optimal number or a quota on source-reading methods.

Each failure retains immutable `repair:<request>` feedback with its original accepted-response reference, diagnostic, count and basis (current document head and user amendments). Graph state carries a reference to that record. A correction changes context and receives a new request identity; it is not a resend of the accepted response. A restart or plain Continue does not reset the count. A new user amendment or edited document head starts a new correction episode at `prepare`; consumed attempts and time never reset. Exceeding the correction allowance yields `response_repair_exhausted`, preserves all work, and sends no further request. Reopening an exhausted episode alone cannot replenish it.

Handoff archives use `handoff:<request>` identities. `response_correction`, `context_compacted` and `request_continued` events have transactional deduplication receipts in `catalog.sqlite`. These cover replay after feedback/handoff/continuation persistence but before graph checkpoint completion. Applied handoffs recover their historical acceptance under Q2, including after a new amendment; global receipt immutability is not relaxed. The graph and catalog still do not share a transaction. General unknown-effect reconciliation and semantic no-progress detection remain separate. Capacity admission and independent pins are specified in Q2; they do not change recovery budgets or authorize new inference.

Export takes an immutable version and an explicit external ZIP path. It verifies actual ZIP names and bytes against that version, publishes without replacing an existing unrelated file, and reconciles an existing known export. Markdown, structured document, preview, manifest and assets come from that version. It needs no model call. The local filesystem must support the current exclusive hard-link publication operation; other filesystem publication strategies are unverified.
