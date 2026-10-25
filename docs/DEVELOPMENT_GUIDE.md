# Development handoff

This repository is the development record for the reconstruction. A developer must be able to understand the requirements, mechanisms, rationale, historical corrections and remaining choices from this repository. The original chat export, old checkout and private review files must not be necessary. The source bundle is optional audit material, not a substitute for technical explanation.

The first application increment is implemented. [CONTRACTS](CONTRACTS.md#implemented-first-version-contracts) owns its selected schemas and transitions; [CURRENT_STATE](CURRENT_STATE.md) owns verified scope. Older explanatory examples retain these status meanings:

- The label “Settled” means an agreed outcome or responsibility.
- The label “recommended” means the retained design direction.
- The label “illustrative” means a way to express a discussed mechanism whose exact schema/API is still open.

A historical mechanism is retained for its lesson, not automatically selected. [OPEN_QUESTIONS](OPEN_QUESTIONS.md) records the closure of the three contracts and the limits of that closure.

## Reading by implementation concern

The owner documents state effective requirements and boundaries. The technical guides explain mechanisms, state/data distinctions, sequences, examples, failure handling and alternatives by development concern rather than conversation order.

| Work area | Detailed explanation | Governing owner |
| --- | --- | --- |
| Product behavior, fidelity, user effort and acceptance | [Product requirements](PRODUCT_REQUIREMENTS.md) | Same document |
| Historical reference-input conditions and misleading example outputs | [Reference inputs and known limits](reference/REFERENCE_INPUTS.md) | [Source-led acceptance](PRODUCT_REQUIREMENTS.md#acceptance-and-cost) |
| Framework fit, Nexus subscription routes, native request/response representation, tools and Electron/Python integration | [Integration and model boundary](design/INTEGRATION_AND_MODEL_BOUNDARY.md) | [Architecture](ARCHITECTURE.md) |
| Evidence access, originals, transient input, policy, budgets, history projection and rolling compaction | [Context and evidence](design/CONTEXT_AND_EVIDENCE.md) | [Context contract](CONTRACTS.md#2-context-capacity-and-handoff) |
| Context-coordination policy adoption, integrated design and capacity policy B | [Discussion chronology](discussions/CONTEXT_COORDINATION.md), [consolidated target](design/CONTEXT_UPDATE_COORDINATION.md) | Four target policies and integrated design adopted, not implemented; [CURRENT_STATE](CURRENT_STATE.md#context-coordination-discussion-and-design-record) separates actual behavior |
| Candidate capture, exact reuse, edits, page maps, immutable versions, validation and visibility | [Document engine](design/DOCUMENT_ENGINE.md) | [Document contract](CONTRACTS.md#1-document-updates-and-candidate-references) |
| Frozen requests, batches, receipts, recovery, limits, stop/wait behavior, process progress and export | [Execution and delivery](design/EXECUTION_AND_DELIVERY.md) | [Recovery contract](CONTRACTS.md#3-persistence-recovery-and-stop-behavior) |
| Why a framework, policy store, summary scheme or recovery rule was revised/rejected | [Decisions](DECISIONS.md), then the detailed [discussion records](reference/SOURCE_INDEX.md#discussion-records) | The relevant owner above |
| What still needs resolution before a coherent first implementation | [Three open contracts](OPEN_QUESTIONS.md) | Same document |

Read the guide relevant to the work and its owner. There is no requirement to load every guide, historical alternative or raw message into an agent prompt. Routine conversion needs its task, source, necessary tool guidance and current working state.

If the original technical spelling is easier to remember than a topic heading, use [TECHNICAL_TERMS](TECHNICAL_TERMS.md). It connects names such as `AgentState`, `Pre-Admission Gate`, `BaseTool._parse_input`, `completed_seq` and `token.map` to their explanations and status. The [detail review](reference/TECHNICAL_DETAIL_REVIEW.md) distinguishes an adequate paraphrase from a missing mechanism, rather than treating a source-to-topic mapping as proof of preservation.

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

[DEVELOPMENT_COVERAGE](reference/DEVELOPMENT_COVERAGE.json) maps every preserved point to its technical explanation, historical rationale or scope note. [POINT_COVERAGE](reference/POINT_COVERAGE.json) retains identities, statuses and source relationships. The reference records preserve narrow findings and rejected mechanisms without making them current requirements.

Optional [bundled sources](reference/sources/INDEX.md) provide readable messages, exact records, attachments and substantive forum figures. Source lookup defaults to these versioned files. Historical path strings in quotes identify old evidence, not required checkout locations.

With a working Python 3.9+ interpreter, run:

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166

Checks use repository files only. Counts/hashes do not prove semantic completeness or runtime correctness. Source-aware review and independent repository-only reading supplement them. [CURRENT_STATE](CURRENT_STATE.md) records documentation checks separately from application checks.
