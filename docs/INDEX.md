# Project document catalogue

Start with the question or capability below. [CURRENT_STATE](CURRENT_STATE.md) owns actual readiness and the next decision; [PHASE_PLAN](PHASE_PLAN.md) owns product outcomes/acceptance. This catalogue owns retrieval and the full maintained-document inventory. [README](../README.md) explains setup/usage, [AGENTS](../AGENTS.md) the working agreement. Read relevant owners rather than every file.

## Topics

| Topic | Current design / contract | Discussion and decisions | Evidence / next choice |
| --- | --- | --- | --- |
| Streaming receive, progress waiting, completion and acceptance | [STREAMING_RECEIVE](design/STREAMING_RECEIVE.md#basis-for-this-revision) | [Discussion](discussions/STREAMING_RECEIVE.md), [decisions](decisions/STREAMING_RECEIVE.md) | [Route signal research](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md), [SC findings](reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30), [A/SC02 recorded checks](CURRENT_STATE.md#verification-basis) |
| Documents, candidates, precise reads and evidence feedback | [DOCUMENT_MODEL](design/DOCUMENT_MODEL.md) | [Initial Q1 decision](decisions/INITIAL_CONTRACTS.md#q1-document-update-and-candidate-reference-contract), [rebuild choices](decisions/REBUILD.md#established-rebuild-decisions) | [Engineering guide](guides/DOCUMENT_ENGINE.md), [implementation history](history/IMPLEMENTATION_HISTORY.md) |
| Context, capacity, handoff and complete update coordination | [CONTEXT_MANAGEMENT](design/CONTEXT_MANAGEMENT.md), [coordination](design/CONTEXT_UPDATE_COORDINATION.md) | [Policy discussion](discussions/CONTEXT_COORDINATION.md), [request capacity](discussions/REQUEST_CAPACITY.md), [decisions](decisions/CONTEXT_MANAGEMENT.md) | [R01/R02 findings](reviews/RUNTIME_FINDINGS.md#finding-index), [engineering detail](guides/CONTEXT_AND_EVIDENCE.md) |
| Durable effects, Continue/Stop, settings and delivery | [RUNTIME_AND_DELIVERY](design/RUNTIME_AND_DELIVERY.md) | [Q3 closure](decisions/INITIAL_CONTRACTS.md#q3-persistence-recovery-and-stop-contract), [reopening decision](decisions/REBUILD.md#reopening-policy) | [Engineering guide](guides/EXECUTION_AND_DELIVERY.md), [remaining interruption/export work](PHASE_PLAN.md) |
| Accepted-evidence conflict diagnosis and bounded local recovery | [ACCEPTED_EVIDENCE_RECOVERY](design/ACCEPTED_EVIDENCE_RECOVERY.md) | [Discussion](discussions/ACCEPTED_EVIDENCE_RECOVERY.md), [decisions](decisions/ACCEPTED_EVIDENCE_RECOVERY.md) | [R13 findings](reviews/RUNTIME_FINDINGS.md#r13--accepted-result-settlement-consistency-selected-2026-10-28); current eligibility is not permission to recover a task |
| PDF coordinates and faithful images | [PDF_EVIDENCE](design/PDF_EVIDENCE.md) | [Selected Phase 3 choices](decisions/REBUILD.md#established-rebuild-decisions) | [Image/evidence guide](guides/CONTEXT_AND_EVIDENCE.md#implemented-pdf-coordinates-and-image-delivery), [historical input limits](sources/REFERENCE_INPUTS.md) |
| Read-only local diagnostics and typed client | [LOCAL_DIAGNOSTICS](design/LOCAL_DIAGNOSTICS.md#basis-for-this-revision) | [Observability discussion](discussions/OBSERVABILITY.md), [decisions](decisions/LOCAL_DIAGNOSTICS.md) | [Recorded API/UI/reopen checks](verification/20261031_0157_LOCAL_DIAGNOSTICS.md), [F/DT findings](reviews/RUNTIME_FINDINGS.md#issue-navigation) |
| Nursing complete fourteen-page conversion | [Stage B acceptance](PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) | [Current discussion](discussions/NURSING.md), [historical decisions](decisions/NURSING.md) | [Baseline/dispatch observations](verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md), [actual next decision](CURRENT_STATE.md#nursing-boundary-and-next-product-decision) |
| Langfuse, control APIs, retention and other unselected changes | [PROPOSED_CHANGES](PROPOSED_CHANGES.md#find-an-option) | [Observability alternatives](discussions/OBSERVABILITY.md), relevant topic decisions | Inclusion is not adoption or a prerequisite; use each recorded reconsideration condition. |
| Framework, architecture and integration | [ARCHITECTURE](ARCHITECTURE.md), [requirements](PRODUCT_REQUIREMENTS.md) | [Rebuild decisions](decisions/REBUILD.md), [original foundation discussion](history/discussions/20261031_0157_REBUILD_FOUNDATIONS.md) | [Integration guide](guides/INTEGRATION_AND_MODEL_BOUNDARY.md), [source inventory](sources/INDEX.md) |
| Documentation organization and historical correspondence | [Filing rules below](#maintaining-this-catalogue) | [Decision](decisions/DOCUMENTATION.md#topic-ownership-and-version-correspondence-2026-10-31) | [DOC-09–13](reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md), [batch verification](verification/20261031_0157_DOCUMENTATION_STRUCTURE.md) |

## Decisions

Decisions are organized by the topic rows above and the decision category below. Designs identify applicable entries, including carried-forward choices; an old decision can still be effective. To inspect an older edition, follow the design's preserved-source/version route and that edition's own basis. Do not match dates or assume the newest decision replaces every older choice. Earlier permission statements apply to their recorded tasks.

## Maintaining this catalogue

Keep stable undated active state/design/discussion/decision paths. Use `YYYYMMDD_HHMM_` for new standalone event/round documents or historical captures, with timezone and timestamp meaning stated inside. Related checks can share one verification document while retaining distinguishable run identities, results and original evidence. Existing legacy history/aggregate finding filenames remain deliberate category owners, not fabricated event timestamps.

Before substantively changing a design or a shared rule/source it relies on, preserve the necessary prior version and exact basis. Use stable retained entries where sufficient; do not copy the whole project or create one file per rule/turn. Current shared-owner links are useful lookup, but do not substitute for historical rule versions. Correct current restatements together and verify affected old routes. A move changes locator metadata, not original evidence bytes or adoption status.

Record findings, reasons, dispositions and unselected options in their topic owners. Update catalogue rows when a maintained document is added/moved/retired; do not put detailed status or another backlog here. The whole-project inventory is below; local contents/source manifests are subordinate navigation, not competing catalogues. Private/local evidence is explicitly limited to its availability. Technical names, source language, counterexamples and consequential rationale remain preserved.

## Complete maintained-document catalogue

The following lists maintained documents, root guidance, fixture documentation and preserved editions. Original source collections are represented by their entry points and complete manifests; the hundreds of verbatim messages/attachments/images are not duplicated as catalogue rows. The original [rebuild bundle manifest](sources/rebuild/bundle-manifest.json), [source inventory](sources/source-inventory.json) and [context-evidence manifest](sources/context-coordination/manifest.json) enumerate them.

### Project entry and current owners

| Document | Purpose / role |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Rebuild working agreement |
| [CHANGELOG.md](../CHANGELOG.md) | Changelog |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Rebuild architecture |
| [docs/CONTRACTS.md](CONTRACTS.md) | Routes each shared contract to its detailed topic owner. |
| [docs/CURRENT_STATE.md](CURRENT_STATE.md) | Actual readiness, limits and next decision. |
| [docs/DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Development handoff |
| [docs/INDEX.md](INDEX.md) | Central topic routes and complete document inventory. |
| [docs/PHASE_PLAN.md](PHASE_PLAN.md) | Product outcomes, accepted scope and completion conditions. |
| [docs/PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) | Product requirements |
| [docs/PROPOSED_CHANGES.md](PROPOSED_CHANGES.md) | Unselected changes, tradeoffs and reconsideration conditions. |
| [docs/REVIEW_HANDOFF.md](REVIEW_HANDOFF.md) | Current source/evidence/authority boundaries for review and continuation. |
| [docs/TECHNICAL_TERMS.md](TECHNICAL_TERMS.md) | Technical terminology and mechanism navigator |
| [README.md](../README.md) | pdf-to-md-agent-2 |

### Current topic designs

| Document | Purpose / role |
| --- | --- |
| [docs/design/ACCEPTED_EVIDENCE_RECOVERY.md](design/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted-evidence conflict diagnosis and recovery |
| [docs/design/CONTEXT_MANAGEMENT.md](design/CONTEXT_MANAGEMENT.md) | Context management and capacity contract |
| [docs/design/CONTEXT_UPDATE_COORDINATION.md](design/CONTEXT_UPDATE_COORDINATION.md) | Context update coordination: consolidated target design |
| [docs/design/DOCUMENT_MODEL.md](design/DOCUMENT_MODEL.md) | Document model, editing and precise evidence access |
| [docs/design/LOCAL_DIAGNOSTICS.md](design/LOCAL_DIAGNOSTICS.md) | Local activity and diagnostic projection |
| [docs/design/PDF_EVIDENCE.md](design/PDF_EVIDENCE.md) | PDF coordinates and image evidence contract |
| [docs/design/RUNTIME_AND_DELIVERY.md](design/RUNTIME_AND_DELIVERY.md) | Durable runtime, continuation and delivery contract |
| [docs/design/STREAMING_RECEIVE.md](design/STREAMING_RECEIVE.md) | Streaming receive, completion and accepted-result settlement |

### Engineering guides

| Document | Purpose / role |
| --- | --- |
| [docs/guides/CONTEXT_AND_EVIDENCE.md](guides/CONTEXT_AND_EVIDENCE.md) | Context and evidence engineering guide |
| [docs/guides/DOCUMENT_ENGINE.md](guides/DOCUMENT_ENGINE.md) | Document, evidence, and candidate engineering handoff |
| [docs/guides/EXECUTION_AND_DELIVERY.md](guides/EXECUTION_AND_DELIVERY.md) | Execution, recovery, and delivery engineering handoff |
| [docs/guides/INTEGRATION_AND_MODEL_BOUNDARY.md](guides/INTEGRATION_AND_MODEL_BOUNDARY.md) | Integration and model-boundary engineering guide |

### Discussions

| Document | Purpose / role |
| --- | --- |
| [docs/discussions/ACCEPTED_EVIDENCE_RECOVERY.md](discussions/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted-evidence recovery: discussion and alternatives |
| [docs/discussions/CONTEXT_COORDINATION.md](discussions/CONTEXT_COORDINATION.md) | Context management: discussion and design convergence |
| [docs/discussions/NURSING.md](discussions/NURSING.md) | Nursing conversion: current discussion |
| [docs/discussions/OBSERVABILITY.md](discussions/OBSERVABILITY.md) | Observability and Langfuse: discussion |
| [docs/discussions/REQUEST_CAPACITY.md](discussions/REQUEST_CAPACITY.md) | Request capacity and usable context: discussion |
| [docs/discussions/STREAMING_RECEIVE.md](discussions/STREAMING_RECEIVE.md) | Streaming receive: discussion and evolution |

### Decisions

| Document | Purpose / role |
| --- | --- |
| [docs/decisions/ACCEPTED_EVIDENCE_RECOVERY.md](decisions/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted Evidence Recovery: decisions and rationale |
| [docs/decisions/CONTEXT_MANAGEMENT.md](decisions/CONTEXT_MANAGEMENT.md) | Context Management: decisions and rationale |
| [docs/decisions/DOCUMENTATION.md](decisions/DOCUMENTATION.md) | Documentation organization decisions |
| [docs/decisions/INITIAL_CONTRACTS.md](decisions/INITIAL_CONTRACTS.md) | Closed first-version contract choices and their original questions |
| [docs/decisions/LOCAL_DIAGNOSTICS.md](decisions/LOCAL_DIAGNOSTICS.md) | Local Diagnostics: decisions and rationale |
| [docs/decisions/NURSING.md](decisions/NURSING.md) | Nursing: decisions and rationale |
| [docs/decisions/REBUILD.md](decisions/REBUILD.md) | Rebuild: decisions and rationale |
| [docs/decisions/STREAMING_RECEIVE.md](decisions/STREAMING_RECEIVE.md) | Streaming Receive: decisions and rationale |

### Research

| Document | Purpose / role |
| --- | --- |
| [docs/research/20261031_0157_NEXUS_STREAMING_SIGNALS.md](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md) | Nexus and CLIProxyAPI streaming signal evidence |

### Verification

| Document | Purpose / role |
| --- | --- |
| [docs/verification/20261031_0157_DOCUMENTATION_STRUCTURE.md](verification/20261031_0157_DOCUMENTATION_STRUCTURE.md) | Documentation reorganization verification |
| [docs/verification/20261031_0157_LOCAL_DIAGNOSTICS.md](verification/20261031_0157_LOCAL_DIAGNOSTICS.md) | Local diagnostic implementation and verification record |
| [docs/verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md](verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md) | Nursing baseline and single-dispatch evidence |

### Findings and reviews

| Document | Purpose / role |
| --- | --- |
| [docs/reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md](reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md) | Documentation structure review and disposition |
| [docs/reviews/20261031_0157_REBUILD_PRESERVATION.md](reviews/20261031_0157_REBUILD_PRESERVATION.md) | Preservation and self-containment audit |
| [docs/reviews/20261031_0157_REBUILD_TECHNICAL_DETAILS.md](reviews/20261031_0157_REBUILD_TECHNICAL_DETAILS.md) | Source-first technical-detail review |
| [docs/reviews/DOCUMENTATION_REORGANIZATION_2026-10.md](reviews/DOCUMENTATION_REORGANIZATION_2026-10.md) | Documentation reorganization review — October 2026 |
| [docs/reviews/RUNTIME_FINDINGS.md](reviews/RUNTIME_FINDINGS.md) | Runtime findings, dispositions and review reconciliation |

### Historical editions and stage records

| Document | Purpose / role |
| --- | --- |
| [docs/history/contracts/20261031_0157_ARCHITECTURE.md](history/contracts/20261031_0157_ARCHITECTURE.md) | Preserved edition / historical reasoning: Rebuild architecture |
| [docs/history/contracts/20261031_0157_CONTRACTS.md](history/contracts/20261031_0157_CONTRACTS.md) | Preserved edition / historical reasoning: Rebuild contracts |
| [docs/history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md](history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md) | Preserved edition / historical reasoning: Product requirements |
| [docs/history/decisions/20261031_0157_DECISIONS.md](history/decisions/20261031_0157_DECISIONS.md) | Preserved edition / historical reasoning: Decisions and rationale |
| [docs/history/design/20261031_0157_EXECUTION_AND_DELIVERY.md](history/design/20261031_0157_EXECUTION_AND_DELIVERY.md) | Preserved edition / historical reasoning: Execution, recovery, and delivery engineering handoff |
| [docs/history/design/20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md](history/design/20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md) | Preserved edition / historical reasoning: Integration and model-boundary engineering guide |
| [docs/history/discussions/20261031_0157_DESIGN_OPTIONS.md](history/discussions/20261031_0157_DESIGN_OPTIONS.md) | Preserved edition / historical reasoning: Design options |
| [docs/history/discussions/20261031_0157_OBSERVABILITY_AND_LANGFUSE.md](history/discussions/20261031_0157_OBSERVABILITY_AND_LANGFUSE.md) | Preserved edition / historical reasoning: Observability and Langfuse: discussion and candidate design |
| [docs/history/discussions/20261031_0157_REBUILD_CONTEXT.md](history/discussions/20261031_0157_REBUILD_CONTEXT.md) | Preserved edition / historical reasoning: Context, state, and evidence: design reasoning and corrections |
| [docs/history/discussions/20261031_0157_REBUILD_DELIVERY.md](history/discussions/20261031_0157_REBUILD_DELIVERY.md) | Preserved edition / historical reasoning: Documents, delivery, persistence, and recovery: source review |
| [docs/history/discussions/20261031_0157_REBUILD_FOUNDATIONS.md](history/discussions/20261031_0157_REBUILD_FOUNDATIONS.md) | Preserved edition / historical reasoning: Foundations, research, and framework decisions |
| [docs/history/discussions/20261031_0157_STAGE_B_CONVERSION.md](history/discussions/20261031_0157_STAGE_B_CONVERSION.md) | Preserved edition / historical reasoning: Stage B conversion progress and interruption discussion |
| [docs/history/IMPLEMENTATION_HISTORY.md](history/IMPLEMENTATION_HISTORY.md) | Preserved edition / historical reasoning: Implementation and validation history |
| [docs/history/PHASE_HISTORY.md](history/PHASE_HISTORY.md) | Preserved edition / historical reasoning: Phase selection and revision history |
| [docs/history/REVIEW_HISTORY.md](history/REVIEW_HISTORY.md) | Preserved edition / historical reasoning: Review and execution handoff history |

### Sources and provenance

| Document | Purpose / role |
| --- | --- |
| [docs/sources/context-coordination/INDEX.md](sources/context-coordination/INDEX.md) | Context coordination discussion sources |
| [docs/sources/INDEX.md](sources/INDEX.md) | Source index and preservation scope |
| [docs/sources/LATER_DECISIONS.md](sources/LATER_DECISIONS.md) | Later repository-scoping decisions |
| [docs/sources/rebuild/INDEX.md](sources/rebuild/INDEX.md) | Bundled discussion sources |
| [docs/sources/REFERENCE_INPUTS.md](sources/REFERENCE_INPUTS.md) | Historical reference inputs and known limits |

### Fixture documentation

| Document | Purpose / role |
| --- | --- |
| [tests/fixtures/pdf/README.md](../tests/fixtures/pdf/README.md) | Synthetic image regression sources |
