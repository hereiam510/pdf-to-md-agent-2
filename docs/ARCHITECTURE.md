# Rebuild architecture

Status: settled responsibility boundaries and preferred implementation baseline; no application is implemented here. EVT-1068, EVT-1107 and EVT-1166 consolidate this direction. The earlier Pi-first and LangChain `create_agent` recommendations remain documented in the reference discussion with their corrections.

For shared terms, an end-to-end example and the module-specific engineering explanations, read [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md). It routes to detailed local guides; source IDs are optional provenance, not prerequisites for understanding this architecture.

## Responsibilities

| Component | Owns | Boundary |
| --- | --- | --- |
| Desktop shell | Task configuration, source/scope selection, progress, saved-document reading, intervention and export access | Electron/TypeScript/React; reconstruct UI from durable state after reconnect |
| Python controller | Agent loop, finite execution policy, task lifecycle and accepted tool-batch sequencing | One controller and shared tools; agent chooses conversion methods |
| Small LangGraph StateGraph | Explicit model/tool/context/recovery transitions and checkpoints of compact orchestration state, including small context policy | Framework is a preferred substrate, not an external-effect transaction manager |
| Nexus request service | Native encoding of the context-selected frozen input, request identity, attempts, complete accepted replies, budgets and cancellation checks | Shared by normal reasoning and compaction; it does not independently reselect evidence |
| Shared tool dispatcher | Tool discovery, raw argument retention, validation, dispatch and durable original receipts | App-internal and external MCP/CLI surfaces use the same core contracts |
| Document/evidence core | Immutable source/evidence/candidate/version content, exact reads, editing, rendering and explicit-version exports | Content fidelity is assessed against the source; storage integrity is a separate guarantee |
| SQLite metadata | Version registration, current pointers, operation uniqueness/receipts and defined execution metadata | Short transactions around durable metadata; large immutable files remain external |

There is no required module count or table count. Boundaries may share a file or be factored into packages as implementation warrants. Do not create a second agent loop merely to adopt a framework.

## Agent loop and autonomy

A graph can express a dynamic model/tool loop. Graph-based execution does not require a fixed business workflow, and autonomy does not remove the need to manage state, budgets, side effects and recovery. The graph represents execution responsibilities; the model still selects methods, tools and continuation based on results.

The model selects source access, OCR, scripts and reconstruction scope. The app checks capacity, maintains identities and accepts complete native replies. The dispatcher executes only validated calls and records every accepted batch member's success, rejection or failure outcome before the next model input is assembled. A complete accepted reply does not imply that every proposed operation passes domain validation. Context work occurs at a defined safe boundary with the same durable request and budget handling as other model calls.

The exact nodes/edges and their schemas are implementation details to settle with [the three contracts](CONTRACTS.md). A simple `prepare -> model -> tools` sketch is not a guarantee that every recovery or cancellation branch is correct.

## Content and context are separate

Keep complete immutable originals outside the model context. Distinguish:

1. Source PDF and derived evidence with source identity and provenance.
2. Received native messages and tool arguments, including rejected or incomplete candidates.
3. Accepted executable messages, tool-batch progress and original receipts.
4. Immutable document versions and explicit delivery versions.
5. The temporary model-input projection and compact continuation state.

Model-facing projections can release or replace large content with accurate references without rewriting the original journal. Replay always uses the original executable call/receipt, never a shortened display of it. Saving data does not automatically decide its relevance or release timing.

Evidence hydration belongs in transient request assembly. Returning large hydrated messages as persistent graph-state updates can refill every checkpoint. The retained simplification keeps small context policy (selections, pin/release choices, notes/references, compaction boundary and settled-batch identity) in graph state, with one settlement writer. An additional external policy-version/activation subsystem is not selected for the single executor (EVT-0872/0878). Transient assembled content stays outside that persistent policy. If a framework hook is used, its actual return/persistence semantics must be verified for the selected version.

## Authority and recovery

Immutable version files are the recommended body authority. SQLite registers their identities and commits metadata/pointers/receipts; avoid a second independently mutable body in `blocks_json`. A staged file plus SQLite commit needs an explicit visibility/reconciliation contract. A database transaction does not also commit the external files or graph checkpoint.

Each request, accepted reply, pending batch, document version and operation receipt has one authoritative record. The graph may keep references and deterministic projections of those facts, but a checkpoint timestamp is not proof that external effects were committed or seen by the model. Preserve local effects when replaying graph work; do not roll back external budgets or publication with a graph branch.

First-version recovery assumes one active writer per task. Multiple independent task workspaces may exist; do not confuse directory isolation with model-context isolation or an OS sandbox. General multi-writer/fork/merge coordination is not a first-version prerequisite.

## Provider portability

Nexus is the intended configurable access layer, including the user's subscription route. Provider-native compaction, response retrieval and remote cancellation may be optional future route capabilities, but the baseline must work without them. Compatibility must cover actual native messages, tool-call IDs/pairs, reasoning items, streaming completion and image content, not only a `base_url` setting.

Do not force every native interaction into a lossy common message shape. Keep a native journal and an explicit, validated projection/adapter where framework messages are needed. Normal inference and history compaction share the same request service, persistent limits and cancellation gate. Framework/SDK/proxy retries must not multiply independently.

## Framework tradeoff retained

Pi offers a lightweight extensible loop and compaction/context hooks, but moving the controller toward TypeScript and integrating the Python source/document core has real coordination costs. LangChain `create_agent` offers a maintained loop and middleware but still needs domain storage/protocol contracts. Deep Agents supplies useful offloading/filesystem/summary mechanisms with stronger built-in assumptions. LangMem supplies memory/summary mechanisms rather than the complete document runtime. OpenAI Agents SDK, Claude Agent SDK and other runtimes require provider/authentication/product-fit checks; SDK maturity alone does not prove Nexus subscription compatibility.

The preferred small StateGraph keeps the Python core and native Nexus service explicit while reusing graph persistence/control primitives. This is a fit judgment, not a benchmark proving lower cost, fewer edits or greater reliability. No new framework bake-off is queued by this choice.

## Implementation boundary

No backward compatibility or old-run migration is required. Useful old code can be reviewed for selective reuse, with the original repository preserved. Dependency versions, exact API/schema names and desktop packaging details are not silently copied from an old environment. Network transport expansion remains deferred; the already-discussed execution boundaries necessary for context and durable work are retained in CONTRACTS.
