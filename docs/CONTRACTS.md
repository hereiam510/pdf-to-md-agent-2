# Rebuild contracts

These contracts consolidate the agreed boundaries and the final recommended tradeoffs in EVT-1166. The exact schemas and transition details listed in [OPEN_QUESTIONS](OPEN_QUESTIONS.md) remain open. No pseudocode or example here certifies an implementation. Additional mechanisms from the discussion are preserved in the reference records with their status.

## 1. Document updates and candidate references

### Identity and original content

Keep source identities, derived evidence identities, received candidate identities, committed document versions and operation identities distinct. A content hash establishes byte identity, not ownership, scope, whether the agent saw the data, or whether it remains in the current document. An unqualified path, mutable `head`, timestamp or hash alone must not ambiguously select a source/version.

Preserve complete received native responses/tool arguments before framework parsing or tool schema validation can discard useful content. An accepted response and an executable tool call are later states. Framework tool middleware may run after native JSON parsing; malformed calls may never reach that middleware. Retention therefore begins in the Nexus receiving layer, with dispatch-layer retention as an additional boundary.

Preserve what was actually received. Do not claim missing trailing content was saved. A rejected or incomplete call remains non-executable. A candidate reference identifies exact original content and its source operation/version/range; a repaired new request has its own identity.

### Edits and validation

The first version should support exact reuse of complete candidate content, pure insertion/append and partial page-map updates. Preserve unchanged body and metadata by default. Merge a local metadata patch into the explicitly named base version, then validate the resulting complete map/structure and conditionally commit against the expected head. A stale base must not silently become today's latest version. Do not require the model to regenerate all prose or resend a full map merely to repair one entry.

A referenced prior candidate is usable even if a later save exists. Adoption in an ancestor records historical use, not proof that every part survives in the current version. Unused candidate material need not all be adopted or explicitly rejected before a task can complete.

Distinguish reusing content from replaying operations. A `block_ops` object can delete/reorder/replace things; copying its prose is different from executing that operation sequence against a changed base. Operations need applicability checks against the intended base. Literal patching must have defined target and match semantics; unique byte matching prevents ambiguous replacement but does not establish semantic correctness.

The agent can choose a larger reconstruction when the source requires it. Local-edit support is an ergonomic capability, not a mandate to use the smallest edit. Logical output blocks do not dictate a token/chunk/storage size or require a complex semantic dependency graph.

### Commit and replay

Recommended body authority: immutable version files. SQLite owns version registration, head/pointers and the unique operation receipt. Stage and validate the file payload before the metadata commit that makes it visible; define cleanup/reconciliation for files without a committed registration. Do not maintain a second independently mutable body as an equal authority.

Operation retries return the original committed receipt and its produced version. A newer head does not invalidate that receipt and must not be rewound. A receipt describes the historical operation; it is not a fresh selection/update of the current document. Validation rejection, successful commit and failure to build/return a model-facing projection are distinguishable outcomes.

No memory-only lock is a durable uniqueness guarantee. The first version uses one active writer per task plus persistent operation identity and short metadata transactions. SQLite ordering does not automatically serialize parallel graph-state `Command` updates; graph policy updates must have a defined single writer.

### Partial-content salvage boundary

Preserving malformed originals is required. Automatically indexing complete subobjects from an incomplete response is a deferred useful option, not a first-version dependency. If added, it must identify closed exact source spans within one attempt/call; handle escapes, duplicate keys and array order; preserve the original hash/span; and create a new valid operation for reuse. Tolerant parsing that closes strings/braces, synthesizes defaults or merges attempts is not proof of a complete original subobject. Extractability is not source correctness.

## 2. Context capacity and handoff

### Two coordinated responsibilities

Evidence management controls what source results, images, OCR and saved content are loaded, kept, released and precisely retrieved. History compaction reorganizes older conversation/work history and continuation state. They share a capacity budget but are not the same operation.

The agent judges relevance and semantic continuation needs. The app observes capacity and requires organization when necessary. It may prioritize releasable content, but does not decide that high OCR confidence, a small text difference, completed page count or storage presence makes evidence semantically unnecessary.

Protect effective user requirements and later amendments, unresolved dependencies and useful work. Save unsaved useful material before removing it from input. Exact originals and references remain retrievable. Latest drafts and unfinished candidates may be partly released; they need not wait for a successor version or stay entirely resident.

### Assembled-request budget

Configure effective capacity and output reserve for the selected route/model. Assess the actual assembled request, including instructions, schemas, native message overhead, images, tool results, draft arguments and continuation state. An estimate is not an exact provider token count. Unknown native/image costs require explicit conservative handling; unknown does not mean zero.

Do not infer the model's nominal window from a local estimate of a rejected request. A provider refusal may reflect endpoint limits, route mismatch, output reserve, image encoding or another error. Only supported diagnosis should trigger context-specific re-preparation; generic HTTP 500/502 alone is not overflow evidence. Transport replay and context-changed re-preparation are distinct request operations, both charged to persistent task budgets.

### Release and rolling compaction

Prefer releasing saved content that is currently unnecessary, then compact older work history when needed. This is an ordering guide, not a mandatory field preset, permanent history-retention rule or unconditional immediate release after saving. Large authored arguments in assistant tool calls can dominate context just as tool results do.

Retain an immutable native journal. Build a separate valid model-input projection, keeping tool-call/result pairing and provider-required native items intact. Do not execute the projection as an original call. The app computes exact covered message/range identities and revision anchors rather than asking the summarizer to reconstruct bookkeeping.

A compaction request may cover only a fitting portion of history. Preserve uncovered history. Its result may be valid progress even if the total context is still above the normal-send threshold. Check reduction on the assembled context, including summary/reference overhead; do not require each partial compaction to reach the final target. No fixed recent `K`, universal percentage, fixed two/three-summary guarantee or claimed 90% saving is selected.

Each compaction request has frozen input, task/step identity, attempt records, budget and cancellation checks through the same Nexus service. It cannot be a hidden untracked model call inside `prepare_step`. Apply a successful result against its intended history revision/coverage boundary. On failure, preserve original records and reassess; do not silently erase input or send the same oversized normal request.

### Continuation content

The recommended first-version handoff is self-sufficient for continuing the task: effective requirements, task/scope, current saved version, unfinished work/dependencies, useful candidate/evidence references and necessary cautions. It need not duplicate complete originals. It does not claim semantic losslessness merely because message IDs or schema validation pass.

Do not adopt delta-only summaries that omit information because it existed in an anchor unless that dependency is explicitly preserved; the first-version recommendation avoids that dependency. Working notes, continuity snapshots, document state and recovery receipts can share references but have different purposes and lifecycles.

### State and caching

Keep small context policy in graph state as the authoritative policy path for the single executor, following the EVT-0878 simplification; an additional external policy-version/activation system is unnecessary. Transient hydration should not be persisted as graph messages. Tools can report intents; one settlement writer applies them at a safe boundary and records the processed accepted batch. Any independent deltas still need explicit conflict rules. `max(policy_rev)` can silently discard parallel changes and is not a merge algorithm. A global journal scan must not resurrect compacted tool history or old policy states. Service-owned request budgets, committed documents and external-effect receipts remain durable outside rollback of that graph state.

A model input view records what was assembled/sent, not what the model understood. Request identity, attempts, accepted tool-batch identity, tool execution, message visibility and semantic source coverage are distinct. Stable IDs must survive retries and resume; using a new recovery checkpoint as the identity for an already accepted batch can cause duplicate dispatch.

Prefer stable instructions, schemas, ordering and appendable prefixes where practical. Updating/removing tail-injected state also changes the prior request prefix; putting dynamic state last is not a cache preservation guarantee. Cache considerations cannot force useless history to remain resident, and smaller input cannot alone establish lower whole-task cost.

## 3. Persistence, recovery and stop behavior

### State ownership

Use one authoritative record for each frozen model request and its attempts, accepted native reply, pending tool batch/progress, operation receipt, document version, export intent and effective compact context policy. Exact record placement remains an implementation choice; a four-module/six-table sketch is not a complete specification. Specify which graph state is authoritative and which can be rebuilt from durable receipts.

Recovery of the same request uses the frozen input. A fresh context policy or newer head can influence a later request, not silently mutate the old request. Persist attempt/budget consumption before dispatch. Reuse a complete accepted saved reply before deciding to call the model again. Do not concatenate partial replies from separate attempts or execute incomplete JSON.

### Recovery boundaries

| Durable boundary | Required behavior on re-entry |
| --- | --- |
| Frozen request exists; accepted reply absent | Reconcile attempt/budget/cancellation state; apply the configured bounded policy before another send of that request |
| Complete reply accepted; tool batch unfinished | Resume the same accepted batch and its outstanding calls; do not regenerate the reply or advance immediately to another model step |
| Tool committed; response/projection/checkpoint missing | Return/reconstruct the historical receipt and its necessary current-batch effects without repeating the local commit |
| Entire batch settled; graph continuation incomplete | Restore the necessary deterministic graph/context effects, then prepare the next request at a safe boundary |
| Local external effect remains unknown | Stop with preserved work and a specific unresolved outcome; do not blindly replay an OCR/script/process operation |

A `ToolMessage` alone may not reproduce a tool's graph `Command`/context-state effect. Conversely, replay must not reapply stale policy over a newer settled state. Reconciliation is scoped to the accepted pending batch and explicit effect identities. A completed call can finish after a higher creation sequence; creation order and `max(event_seq)` are not a completion timeline. Define causal/application progress rather than inferring it from wall-clock timestamps.

Graph checkpoints, SQLite commits and immutable external files do not form one atomic transaction. Define visibility and reconciliation at these limited boundaries. First-version single-writer recovery does not promise arbitrary historical-job migration, exactly-once remote generation or unconditional recovery from every hard crash.

### Shared limits and transport behavior

Normal and compaction sends use one durable budget/cancellation gate, including direct entry and resume paths. Limits survive restart and graph rollback. Distinguish request inactivity from whole-job active time; wait/backoff accounting must be defined. Do not reset attempts, turns or time allowances on resume or hide nested SDK/proxy retries.

When bounded unknown-outcome model replay is enabled, it need not demand routine human proof that the remote generation stopped. Preserve possible duplicate inference, remote overlap and unknown usage/cost. Local abort, timeout or later success does not prove remote cancellation, original-generation continuation or zero cost. Eligibility/limits/default values need configuration; old experiment values are not new defaults.

Streaming and non-streaming share accepted-response/tool/persistence semantics. Preserve native candidate information with safe handling of errors and sensitive fragments. A transport fragment is evidence, not automatically an executable native response. Respect explicit cancellation and user questions; no routine reminder may override them.

### Stop, task completion and export

Execution stop reason, agent content-completion claim and package consistency are separate records. A question for the user can enter a waiting state; a second no-tool answer is not automatically a question. Optional one-shot continuation reminders need explicit bounded behavior and do not count as a first-version requirement.

Saved versions remain exportable by the host without further model use. Partial work retains a draft/partial label. Explicit selection of a version determines Markdown, JSON, HTML, assets and ZIP; a mutable head or newly generated summary must not change that selection during export.

Verify actual intended members and bytes. A manifest identity alone does not establish actual ZIP/file consistency. The export directory and ZIP are separate publication effects; a single rename cannot atomically publish both. Re-entry must preserve unrelated outputs and reconcile known output identities before repeating publication. A finalizer node cannot guarantee packaging after every crash/cancellation/exit.

### Desktop progress and process boundary

Persist important results/receipts; allow coalescing or dropping obsolete progress events. A bounded queue cannot simultaneously promise lossless unlimited events and never block when the consumer stops. Avoid coupling durable tool completion to UI stdout consumption. A reconnecting UI should read committed state.

Protocol output and diagnostics require a deliberate process/channel boundary, but mandatory first-line `os.dup2` was not established as the universal remedy. Native libraries, callbacks, threads and process shutdown need proportionate implementation checks. These considerations do not require a new distributed infrastructure or a separate network research phase before document/context contracts can be written.
