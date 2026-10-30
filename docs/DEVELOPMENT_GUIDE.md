# Development handoff

This repository is the development record for the reconstruction. A developer must be able to understand the requirements, mechanisms, rationale, historical corrections and remaining choices from this repository. The original chat export, old checkout and private review files must not be necessary. The source bundle is optional audit material, not a substitute for technical explanation.

The first application increment is implemented. [CONTRACTS](CONTRACTS.md#implemented-first-version-contracts) owns its selected schemas and transitions; [CURRENT_STATE](CURRENT_STATE.md) owns verified scope. Older explanatory examples retain these status meanings:

- The label “Settled” means an agreed outcome or responsibility.
- The label “recommended” means the retained design direction.
- The label “illustrative” means a way to express a discussed mechanism whose exact schema/API is still open.

A historical mechanism is retained for its lesson, not automatically selected. [initial contract decisions](decisions/INITIAL_CONTRACTS.md) records the closure of the three contracts and the limits of that closure.

For **View activity and diagnostics**, read the [API and read lifecycle](design/LOCAL_DIAGNOSTICS.md#task-activity-and-local-diagnostic-api) and [observability implementation/evidence owner](verification/20261031_0157_LOCAL_DIAGNOSTICS.md#f01f02-implementation-method-2026-10-29). Ordinary polling exposes event count/latest identity; pages and selected factual joins reuse temporary catalog copies on demand. CURRENT_STATE records local acceptance independently of conversion readiness.

For the F02 consistency correction, artifact links and both join directions share `artifact_facts`; `record_summary` isolates unsupported list rows without dropping identities/counts. The ordinary task display also isolates request-summary failures so diagnostics remain reachable. Staging-only relationships stay unpublished and independent version commits remain inspectable. Follow the [single correction owner](verification/20261031_0157_LOCAL_DIAGNOSTICS.md#f02-consistency-correction-implementation-and-evidence-2026-10-29) for rationale, discriminating fixtures, exact-source failures, final API/UI/reopen evidence and stops; acceptance/recovery semantics are unchanged.

For [F02-D03](verification/20261031_0157_LOCAL_DIAGNOSTICS.md#f02-d03-implementation-and-evidence-2026-10-30), diagnostic links expose raw observations in `raw_descriptor`; only successful results expose structured `facts`. Apply integrity/provenance and role checks before publishing facts, preserve the earliest failure reason, and gate consumers on success. Independent inline commits retain their own version/file verification. The [API guide](design/LOCAL_DIAGNOSTICS.md#task-activity-and-local-diagnostic-api) explains exact fields and examples; the topic owner records the new synthetic API/Electron/reopen evidence separately from D01/D02.

## Reading by implementation concern

The owner documents state effective requirements and boundaries. The technical guides explain mechanisms, state/data distinctions, sequences, examples, failure handling and alternatives by development concern rather than conversation order.

| Work area | Detailed explanation | Governing owner |
| --- | --- | --- |
| Product behavior, fidelity, user effort and acceptance | [Product requirements](PRODUCT_REQUIREMENTS.md) | Same document |
| Historical reference-input conditions and misleading example outputs | [Reference inputs and known limits](sources/REFERENCE_INPUTS.md) | [Source-led acceptance](PRODUCT_REQUIREMENTS.md#acceptance-and-cost) |
| Framework fit, Nexus subscription routes, native request/response representation, tools and Electron/Python integration | [Integration and model boundary](guides/INTEGRATION_AND_MODEL_BOUNDARY.md) | [Architecture](ARCHITECTURE.md) |
| Installed Nexus/CLIProxyAPI streaming capabilities, primary source links and evidence limits | [Streaming signal evidence](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md) | [Waiting contract](design/STREAMING_RECEIVE.md#streaming-progress-waiting) |
| Evidence access, originals, transient input, policy, budgets, history projection and rolling compaction | [Context and evidence](guides/CONTEXT_AND_EVIDENCE.md) | [Context contract](design/CONTEXT_MANAGEMENT.md#2-context-capacity-and-handoff) |
| Context-coordination policy adoption, integrated design and capacity policy B | [Discussion chronology](discussions/CONTEXT_COORDINATION.md), [consolidated target](design/CONTEXT_UPDATE_COORDINATION.md) | Four adopted policies implemented; [recorded implementation result](history/IMPLEMENTATION_HISTORY.md#complete-context-update-coordination) separates checks and remaining limits |
| Candidate capture, exact reuse, edits, page maps, immutable versions, validation and visibility | [Document engine](guides/DOCUMENT_ENGINE.md) | [Document contract](design/DOCUMENT_MODEL.md#1-document-updates-and-candidate-references) |
| Frozen requests, batches, receipts, recovery, limits, stop/wait behavior, process progress and export | [Execution and delivery](guides/EXECUTION_AND_DELIVERY.md) | [Recovery contract](design/RUNTIME_AND_DELIVERY.md#3-persistence-recovery-and-stop-behavior) |
| Historical accepted-evidence conflict diagnosis, local resolution, graph reentry and paired history | [Recovery target and implementation map](design/ACCEPTED_EVIDENCE_RECOVERY.md), [execution mechanism](guides/EXECUTION_AND_DELIVERY.md#historical-conflict-recovery-implementation), [resolved history](guides/CONTEXT_AND_EVIDENCE.md#resolved-historical-batches), [local API/UI](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#local-saved-acceptance-diagnosis-and-recovery-api) | [Local recovery contract](design/ACCEPTED_EVIDENCE_RECOVERY.md#historical-accepted-evidence-local-recovery); CURRENT_STATE owns checks and limits |
| Why a framework, policy store, summary scheme or recovery rule was revised/rejected | [Decisions](INDEX.md), then the detailed [discussion records](sources/INDEX.md#discussion-records) | The relevant owner above |
| Observability/Langfuse motivation, existing facts and gaps, external-review corrections and candidate integration | [Observability discussion and candidate design](discussions/OBSERVABILITY.md), [finding dispositions](reviews/RUNTIME_FINDINGS.md#observability-review-reconciliation-2026-10-29), [phase placement](history/PHASE_HISTORY.md#observability-placement-after-review-reconciliation-2026-10-29) | No integration selected; existing acceptance/execution/recovery contracts remain authoritative |
| How the three initial contracts were closed, and the limits of that closure | [Three contract closures](decisions/INITIAL_CONTRACTS.md) | [Effective contracts](CONTRACTS.md); historical open questions do not reopen settled work |

Read the guide relevant to the work and its owner. There is no requirement to load every guide, historical alternative or raw message into an agent prompt. Routine conversion needs its task, source, necessary tool guidance and current working state.

If the original technical spelling is easier to remember than a topic heading, use [TECHNICAL_TERMS](TECHNICAL_TERMS.md). It connects names such as `AgentState`, `Pre-Admission Gate`, `BaseTool._parse_input`, `completed_seq` and `token.map` to their explanations and status. The [detail review](reviews/20261031_0157_REBUILD_TECHNICAL_DETAILS.md) distinguishes an adequate paraphrase from a missing mechanism, rather than treating a source-to-topic mapping as proof of preservation.

## Shared vocabulary

| Term | Meaning | Important distinction |
| --- | --- | --- |
| Nexus route | Configured app-to-model path, including the user's monthly-subscription connector | Official pay-as-you-go API features do not prove this route supports them |
| Native journal | Durable original model messages, response items and received tool arguments, with protocol identity | It is not the smaller message list later selected for a request |
| Source | Unchanged user PDF and its identity | OCR, a render and model-authored prose are not the original PDF |
| Evidence | Derived text, layout, OCR, image or crop, with provenance | Saving it does not prove correctness, awareness or complete coverage |
| Evidence view | Selected fields, ranges, regions, resolution or an exact original | A smaller view does not authorize deleting the complete result |
| Candidate | Useful received model-authored content/arguments before execution or document validation | Incomplete or malformed candidates remain non-executable |
| Document version | Committed immutable content and its associated map/assets/version identity | A mutable current pointer and an uncommitted candidate are different |
| Head | Metadata pointer to the currently selected committed version | Replaying an old success must not rewind it |
| Logical operation | Identified tool/document action whose effect must be recognized on retry | An argument hash proves payload equality, not invocation or intent |
| Receipt | Durable operation result, including outcome and produced version | Returning it acknowledges the original operation, not a fresh edit |
| Model request | One frozen, identified model-input operation | An attempt sends that request. Changing context prepares a new request. |
| Accepted reply | Complete response satisfying protocol/execution acceptance rules | Partial transport text and retained malformed candidates are separate states |
| Accepted tool batch | Tool calls from one accepted reply, with stable call identities/progress | Finish or reconcile this batch before the next normal reasoning step |
| Graph checkpoint | Persisted compact orchestration state | It does not atomically commit SQLite, files and remote effects |
| Context policy | Small authoritative selections, pin/release choices, notes/references and compaction progress | Large evidence bodies are hydrated transiently |
| Hydration | Loading selected saved content to assemble a request | It need not mutate persistent graph messages |
| Input projection | Protocol-valid working view assembled for a model request | Attempt records establish dispatch. The projection may shorten retained history. Never replay the projection as an original executable call. |
| Handoff | Task-continuation content: requirements, saved state, unfinished work and references | It is neither a sole original nor proof of semantic losslessness |
| Export | Artifacts from an explicitly chosen committed version | It can proceed without a model. Execution success, content completion and package consistency differ. |

Different names do not require separate servers, databases or classes. They identify lifecycle and ownership differences that implementation must preserve.

## An end-to-end example

This example explains responsibilities. It is not a required OCR/text-first/preview workflow.

1. A user selects a PDF and complete section. The desktop app records source identity, scope, route and constraints. The agent chooses native text, pixels, OCR, scripts or a combination.
2. An inspection returns a large layout result. The complete result and provenance are saved. The model-facing view states what is shown and how to retrieve exact fields/ranges or original pixels. A summary is never the only original.
3. Context preparation resolves selected versions, assembles a protocol-valid request and checks capacity/output reserve. The shared service records frozen input and accounts for an attempt before sending through Nexus.
4. The response proposes an edit. Native content is retained before parsing/schema validation can discard useful text. If only page metadata is invalid, the correct body remains an identifiable candidate.
5. The agent reuses that exact body and repairs metadata against a named base and expected head. The document core validates the complete merged result, prepares immutable content and commits metadata/receipt at the defined visibility boundary. A stale base is not silently replaced with today's latest version.
6. If execution stops after commit but before the graph checkpoint or tool-result projection, recovery identifies the original operation. It returns the original receipt and reconstructs necessary current-batch effects. It does not regenerate prose, duplicate the edit, rewind a newer head or reset spending.
7. If input grows, the app requires context organization when necessary. The agent judges relevance and continuation needs. Saved evidence can leave input while remaining retrievable. Older history may need separate compaction. A fitting partial compaction can make progress without reaching the final normal-send limit in one pass.
8. The host exports a selected saved version. If requested scope remains unfinished, the useful result is exportable with a draft/partial label. Markdown, structured data, HTML and assets must correspond to that version. Making a ZIP does not establish content fidelity.

The technical guides explain each boundary and its open choices. Do not infer that SQLite and files form one transaction. Do not infer that every crash runs a finalizer. Do not infer that an upstream response can be cancelled/retrieved remotely.

## Constraints crossing modules

- **Preserve source meaning and pixels.** Wording, glyphs, meaningful emphasis, tables, page relationships and substantive figures govern acceptance. Dense tuples, Unicode normalization and confidence thresholds cannot decide which distinctions are expendable.
- **Keep originals and useful work.** Evidence/native-response/candidate retention is independent of input selection. Large assistant tool-call arguments can dominate context even after large tool results are released.
- **Use explicit identities.** Source/version/range, operation, request, attempt, accepted batch, checkpoint and actual completion have different meanings. Timestamps, maximum sequence/revision and hashes cannot replace causal ownership.
- **Use one policy settlement path.** Small context policy belongs in Graph State for the single task writer. The earlier external policy-version/activation system is historical. External effects, document commits and request spending still need durable records outside graph rollback.
- **Preserve protocol meaning.** Tool-call pairs, required reasoning items, images and complete-response semantics must survive adapters/projections. A base URL or mature SDK does not establish route compatibility.
- **Keep limits durable.** Ordinary and compaction calls share request/budget/cancellation handling. Retry owners must not multiply. Local abort leaves possible unknown upstream generation and cost.
- **Keep useful work accessible.** Saved-document reading and explicit-version export do not depend on another model request. UI progress transport is not the durable result store.
- **Preserve agent autonomy.** Tools expose discoverable capabilities and full access. They do not impose a fixed extraction order, field preset, summary gate or arbitrary quota.

## Historical observations and examples

The discussion used these concrete observations from the old project:

- Layout with 41 blocks/446 spans still occupied 147,366 characters.
- Regeneration after a page-map rejection changed correct candidate wording.
- Tool-call-only replies sometimes had null assistant prose.
- Earlier context/recovery exercises had scoped successes and limitations.

The guides explain the causal lessons and limits locally.

These are historical observations, not measurements of this repository. The design does not need old run workspaces, job IDs or defaults to express required behavior. Implementable cases include an oversized structured result, correct candidate text with invalid metadata, an accepted tool-only batch, and a commit/checkpoint gap. Old counts are examples, not thresholds or a new experiment queue.

Research/framework mechanisms are retained with status. A paper's compression ratio does not establish equal-quality conversion savings. A framework example does not settle an app schema. A citation does not replace an explanation of why the discussion considered a mechanism.

## Implementation choices and deferred scope

Implementation selected Q1–Q3 without reopening the retained outcomes. The detailed guides preserve their rationale and alternatives; the executable contract section governs exact current names and transitions.

- Q1 uses explicit base/head edits, precise candidate reuse and atomic metadata registration with immutable files.
- Q2 uses complete-input capacity checks, preserved originals, fitting batch compaction and a self-sufficient handoff. The estimator is a heuristic.
- Q3 uses stable request/member identities, a single executor, durable limits and finite receipt reconciliation. It does not promise remote exactly-once generation.

The lockfiles pin selected dependencies. [ARCHITECTURE](ARCHITECTURE.md#implementation-map-and-selected-dependencies) maps the current modules and official guidance. The technical examples are not automatic requirements for additional tables, frameworks or transport mechanisms.

Broader network design remains deferred. The documents record necessary execution boundaries because context work and useful results must survive interruption. This does not reopen general network research.

## Detail and source coverage

[DEVELOPMENT_COVERAGE](sources/DEVELOPMENT_COVERAGE.json) maps every preserved point to its technical explanation, historical rationale or scope note. [POINT_COVERAGE](sources/POINT_COVERAGE.json) retains identities, statuses and source relationships. The reference records preserve narrow findings and rejected mechanisms without making them current requirements.

Optional [bundled sources](sources/rebuild/INDEX.md) provide readable messages, exact records, attachments and substantive forum figures. Source lookup defaults to these versioned files. Historical path strings in quotes identify old evidence, not required checkout locations.

With a working Python 3.9+ interpreter, run:

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166

Checks use repository files only. Counts/hashes do not prove semantic completeness or runtime correctness. Source-aware review and independent repository-only reading supplement them. [CURRENT_STATE](CURRENT_STATE.md) records documentation checks separately from application checks.

## Workbench behavior and implementation overview

This overview was relocated from README on 2026-10-30. Batch numbers and build observations retain their recorded scope; [CURRENT_STATE](CURRENT_STATE.md) identifies the latest source and limits. Contracts remain authoritative for effective behavior.

<!-- relocated-readme-overview:start -->
- An independent Electron/TypeScript/React app with one Python agent controller and shared tools.
- A small LangGraph `StateGraph`, a shared Nexus request service and tool dispatcher, and a document/evidence core. SQLite metadata and immutable external files are the preferred persistence arrangement.
- The agent selects methods. The app enforces capacity, execution and storage contracts. No fixed extraction/OCR/preview recipe applies.
- Provider-portable context handling through Nexus, including monthly-subscription connections. Provider-native compaction, background retrieval and remote cancellation are not baseline dependencies.
- Exact reusable evidence and candidate content, local edits, immutable saved versions and explicit-version export.

The implementation follows these responsibility boundaries. Framework choice is not a measured-superiority claim. Backward compatibility with the original project is unnecessary.

The response-correction increment continues automatically after a text-only reply or an invalid context handoff. Connection settings expose **Automatic response corrections** (default 2, zero disables), applied to new tasks. Corrections retain the original reply and share the task's request/time budget. Continuing an exhausted correction episode does not reset it; new user instructions or an edited document start a new episode. Explicit completion or questions use the agent's `report` tool. See [the execution contract](design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) for boundaries.

Document editing binds a draft to its loaded version and starting head. Historical versions offer **Rebuild from this version**; content added in later versions is excluded from that reconstruction. Failed loads cannot enable editing/export, and a save conflict retains the draft. The agent's `edit_document` uses ordinary edits by default, offers explicit autonomous reconstruction, and can insert/replace exact blocks from retained candidates. Export uses the selected loaded version, excluding unsaved edits. See [the document contract](design/DOCUMENT_MODEL.md#q1-document-schema-and-commit).

After Stop, adding instructions and pressing **Continue** preserves completed tool effects and marks obsolete, unstarted calls as unexecuted before the agent decides again. Continue without an amendment resumes the accepted batch. After an HTTP error or a rejected/truncated reply, Continue can prepare a new request using the latest task state, while retaining the failed record and consumed budgets. Unknown remote outcomes retain their original request and configured replay limit; unknown local effects still need reconciliation. Reopening alone does not send a request.

For a historical saved-acceptance conflict, use **Inspect saved acceptance** in the task panel. The on-demand diagnosis explains retained bytes, original publication, receive-rule compatibility and tool-effect certainty. Eligible finish-boundary cases offer **Preserve work and prepare to re-plan**, a credential-free local action. It preserves original acceptance and consumption, retains completed effects, and pairs unstarted calls with truthful receipts. Review/export saved versions, reopen or add instructions, then use the separate **Continue** to start further model work. Uncommitted candidates, a committed decision awaiting graph projection, and ready local recovery are distinct states. Unknown effects and unsupported evidence remain explicit stopped cases. See [the recovery contract](design/ACCEPTED_EVIDENCE_RECOVERY.md#historical-accepted-evidence-local-recovery), [target and implementation map](design/ACCEPTED_EVIDENCE_RECOVERY.md), and CURRENT_STATE for local verification and limits. This adds no Langfuse integration or external telemetry.

When Stop interrupts context organization and no accepted reply is available, **Resume context organization** offers a separate explicit recovery choice. It preserves the unknown request and usage, permits one replacement, then continues from saved work. The upstream computation may run twice; the app cannot confirm remote cancellation or final cost. Repeated clicks and reopening retain the same committed choice. Ordinary Continue does not enable this recovery automatically. See [the recovery contract](design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery).

The current source includes all three editing/continuation batches, the context-capacity increment and follow-up phase 1. Oversized tool bodies receive explicit deferred receipts with exact read references; complete originals and full/raw/field/range access remain available. Pinned objects survive independently when their original history is compacted. Compaction keeps fitting objects within mixed-size batches and includes later material when a reference-only prefix offers no body reduction. A last-history handoff that still overflows normal input receives bounded correction while the old history remains active; useful partial reductions still apply with uncovered history. Genuinely oversized required pins stop explicitly. See [the context contract](design/CONTEXT_MANAGEMENT.md#q2-context-transitions).

The phase-1 closeout recovers an already applied handoff after an interrupted checkpoint even when new instructions arrive. It preserves the original application receipt and consumed usage, then checks the latest input before continuing. An archived but unapplied candidate still needs validation. See [the closeout evidence](history/IMPLEMENTATION_HISTORY.md#phase-1-closeout-handoff-application-replay).

The Phase 3 closeout distinguishes stencil coverage from page appearance. The agent can inspect the component or select a page occurrence for a correctly painted display asset with original-stream provenance. Context pins now choose index, image, full/selected text or raw bytes explicitly. Admission happens before application; rejection preserves previous pins, releases and notes and lets the agent revise its choice. Full originals and precise reads remain available. See [the closeout evidence](history/IMPLEMENTATION_HISTORY.md#phase-3-closeout-stencil-appearance-and-pin-admission).

Existing Windows folder/installer artifacts still contain the earlier response-correction build; use the development launcher for this revision. [Reviewer handoff](REVIEW_HANDOFF.md) maps the changes and review evidence. The three accepted follow-up phases and the Phase 3 closeout are implemented. [Recorded state](history/IMPLEMENTATION_HISTORY.md#review-follow-up-progress) records checks and limitations separately from plan acceptance and release.

Context updates in one accepted response now form one ordered revision. The complete candidate is admitted at the batch boundary; a structural error prevents partial context application without rolling back other successful tools. History-only pressure retains eligible intent for compaction. Confirmed necessary-content excess records `needs_agent_revision` before diagnostic planning; later capacity increases do not revive it. The agent can explicitly reuse selected fields or operations against the current active base. Original receipts, full access, budgets and frozen requests are preserved. See [the context contract](design/CONTEXT_MANAGEMENT.md#q2-context-transitions) and [recorded evidence](history/IMPLEMENTATION_HISTORY.md#complete-context-update-coordination).

The integrated coordination implementation addresses the reproduced shrinking-update guard, particular-outcome preview and short-reference progress inconsistencies. Actual compaction is checked separately from normal input; a one-way necessary-cost proof never replaces full admission. Committed decisions and policy effects recover before current settings are evaluated. [The design](design/CONTEXT_UPDATE_COORDINATION.md) preserves the rationale and [the handoff](REVIEW_HANDOFF.md) identifies the tested source, evidence and remaining real-model limits.

**View activity and diagnostics** now provides recent/oldest/older/newer activity pages and explicit refresh, plus on-demand request/attempt/context/operation/version records and exact evidence access. Counts are task-filtered; missing historical facts and unchecked graph readiness stay explicit. Use the development launcher for this source revision. [The API/read-lifecycle guide](design/LOCAL_DIAGNOSTICS.md#task-activity-and-local-diagnostic-api) and [recorded state](history/IMPLEMENTATION_HISTORY.md#f01f02-local-implementation-and-acceptance-2026-10-29) explain behavior, checks and limits; this does not establish live conversion or installed-build readiness.

Context updates now distinguish saved pending intent from active policy and from final outcome delivery. Temporary capacity blocks retain valid proposals for Continue; committed outcomes checkpoint before the next input is built. Fitting updates need no compulsory compaction, and large updates cannot gain admission merely by deferring additional unselected evidence. Exact originals remain readable. See [current coordination evidence](history/IMPLEMENTATION_HISTORY.md#proposal-validity-admission-and-outcome-delivery).
<!-- relocated-readme-overview:end -->
