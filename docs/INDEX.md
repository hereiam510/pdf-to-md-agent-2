# Project document catalogue

Start with the question or capability below. [CURRENT_STATE](CURRENT_STATE.md) owns actual readiness and the next decision; [PHASE_PLAN](PHASE_PLAN.md) owns product outcomes/acceptance. This catalogue owns retrieval and the full maintained-document inventory. [README](../README.md) explains setup/usage, [AGENTS](../AGENTS.md) the working agreement. Read relevant owners rather than every file.

## Start development

| Question | Owner |
| --- | --- |
| What works and what is active? | [CURRENT_STATE](CURRENT_STATE.md#find-current-work) |
| What remains across the project? | [WORK_ITEMS](WORK_ITEMS.md): current item dispositions, impact and next checks |
| How do I continue the selected assignment? | [REVIEW_HANDOFF](REVIEW_HANDOFF.md#credential-follow-up-implementation-handoff-2026-11-06), linked to its acceptance and evidence owners |
| Why this next increment and what must the phase deliver? | [PHASE_PLAN](PHASE_PLAN.md#next-increment-selection), the single roadmap |

Read these together before recommending next work, then follow relevant detailed owners. README/INDEX supply navigation; WORK_ITEMS owns current item dispositions, PHASE_PLAN sequencing and CURRENT_STATE readiness. Recorded items do not authorize execution.

## Topics

| Topic | Current design / contract | Discussion and decisions | Evidence / next choice |
| --- | --- | --- | --- |
| Streaming receive, progress waiting, completion and acceptance | [STREAMING_RECEIVE](design/STREAMING_RECEIVE.md#basis-for-this-revision) ([versions](design/STREAMING_RECEIVE.md#design-versions)) | [Discussion](discussions/STREAMING_RECEIVE.md), [decisions](decisions/STREAMING_RECEIVE.md) | [Route signal research](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md), [SC findings](reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30), [A/SC02 recorded checks](CURRENT_STATE.md#verification-basis) |
| Documents, candidates, precise reads and evidence feedback | [DOCUMENT_MODEL](design/DOCUMENT_MODEL.md) ([versions](design/DOCUMENT_MODEL.md#design-versions)) | [Initial Q1 decision](decisions/INITIAL_CONTRACTS.md#q1-document-update-and-candidate-reference-contract), [rebuild choices](decisions/REBUILD.md#established-rebuild-decisions) | [Engineering guide](guides/DOCUMENT_ENGINE.md), [implementation history](history/IMPLEMENTATION_HISTORY.md) |
| Context, capacity, handoff and complete update coordination | [CONTEXT_MANAGEMENT](design/CONTEXT_MANAGEMENT.md) ([usage-anchoring trial v1](design/CONTEXT_MANAGEMENT.md#usage-anchoring-v1-first-bounded-trial-2026-11-05), [versions](design/CONTEXT_MANAGEMENT.md#design-versions)), [coordination](design/CONTEXT_UPDATE_COORDINATION.md) ([versions](design/CONTEXT_UPDATE_COORDINATION.md#design-versions)) | [Policy discussion](discussions/CONTEXT_COORDINATION.md), [request capacity](discussions/REQUEST_CAPACITY.md), [R01-CAL study discussion and real-PDF clarification](discussions/REQUEST_CAPACITY.md#r01-cal-study-discussion-and-real-pdf-validation-2026-11-06), [small real-PDF trial plan and selected sources](discussions/REQUEST_CAPACITY.md#r01-cal-small-real-pdf-trial-plan-and-source-selection-2026-11-06), [offline route/billing/readiness bindings](discussions/REQUEST_CAPACITY.md#offline-route-billing-and-operational-readiness-2026-11-06), [prepared tasks and offline operational checks](discussions/REQUEST_CAPACITY.md#offline-operational-preparation-and-verification-2026-11-06), [Task A execution approval and handoff](discussions/REQUEST_CAPACITY.md#task-a-execution-approval-and-handoff-2026-11-06), [decisions](decisions/CONTEXT_MANAGEMENT.md) | [34-send assessment](discussions/REQUEST_CAPACITY.md#current-estimator-offline-calibration-2026-11-01), [component proposal](discussions/REQUEST_CAPACITY.md#recommendation-correction-and-component-calibration-proposal-2026-11-01), [method discussion/review reconciliation](discussions/REQUEST_CAPACITY.md#estimation-method-discussion-and-review-reconciliation-2026-11-01), [Task A execution/review and R01CAL-A01](verification/20261106_1408_R01CAL_TASK_A.md), [R01/R02 findings](reviews/RUNTIME_FINDINGS.md#finding-index), [production modality repair](reviews/RUNTIME_FINDINGS.md#r01-mod-production-classification-increment-2026-11-06), [counter recovery](reviews/RUNTIME_FINDINGS.md#r01-count-automatic-recovery-increment-2026-11-06), [offline calibration evaluator](reviews/RUNTIME_FINDINGS.md#r01-cal-offline-evaluator-increment-2026-11-06), [offline coordinator](reviews/RUNTIME_FINDINGS.md#ua-01-offline-usage-anchoring-coordinator-increment-2026-11-06), [independent review and UA-01-R1/R2](reviews/RUNTIME_FINDINGS.md#ua-01-independent-contract-and-implementation-review-2026-11-06), [offline repairs/results and deferred defaults boundary](reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06), [observer verification](verification/20261105_0220_USAGE_OBSERVATION.md), [engineering detail](guides/CONTEXT_AND_EVIDENCE.md) |
| Durable effects, Continue/Stop, settings and delivery | [RUNTIME_AND_DELIVERY](design/RUNTIME_AND_DELIVERY.md) ([versions](design/RUNTIME_AND_DELIVERY.md#design-versions)) | [Q3 closure](decisions/INITIAL_CONTRACTS.md#q3-persistence-recovery-and-stop-contract), [reopening decision](decisions/REBUILD.md#reopening-policy) | [Engineering guide](guides/EXECUTION_AND_DELIVERY.md), [remaining interruption/export work](PHASE_PLAN.md) |
| Accepted-evidence conflict diagnosis and bounded local recovery | [ACCEPTED_EVIDENCE_RECOVERY](design/ACCEPTED_EVIDENCE_RECOVERY.md) ([versions](design/ACCEPTED_EVIDENCE_RECOVERY.md#design-versions)) | [Discussion](discussions/ACCEPTED_EVIDENCE_RECOVERY.md), [decisions](decisions/ACCEPTED_EVIDENCE_RECOVERY.md) | [R13 findings](reviews/RUNTIME_FINDINGS.md#r13--accepted-result-settlement-consistency-selected-2026-10-28); current eligibility is not permission to recover a task |
| Autonomous independent figures and adjacent searchable text | [FD-01: adopted target and local implementation](design/FIGURE_DELIVERY.md) | [Decision](decisions/NURSING.md#figure-delivery-requirements-selected-2026-11-01), [discussion](discussions/NURSING.md#figure-delivery-correction-and-selected-direction-2026-11-01) | [Acceptance correction](verification/20261031_2242_NURSING_LIVE.md#acceptance-correction-2026-11-01), [Local checks/proposal](verification/20261101_0033_FD01_LOCAL.md), [completed two-page acceptance](verification/20261101_0103_FD01_TWO_PAGE_LIVE.md); interval closed; full fourteen-page FD-01/captionless validation deferred by [task closeout](decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01) |
| PDF coordinates and faithful images | [PDF_EVIDENCE](design/PDF_EVIDENCE.md) ([versions](design/PDF_EVIDENCE.md#design-versions)) | [Selected Phase 3 choices](decisions/REBUILD.md#established-rebuild-decisions) | [Image/evidence guide](guides/CONTEXT_AND_EVIDENCE.md#implemented-pdf-coordinates-and-image-delivery), [historical input limits](sources/REFERENCE_INPUTS.md) |
| Read-only local diagnostics and typed client | [LOCAL_DIAGNOSTICS](design/LOCAL_DIAGNOSTICS.md#basis-for-this-revision) ([versions](design/LOCAL_DIAGNOSTICS.md#design-versions)) | [Observability discussion](discussions/OBSERVABILITY.md), [decisions](decisions/LOCAL_DIAGNOSTICS.md) | [Recorded API/UI/reopen checks](verification/20261031_0157_LOCAL_DIAGNOSTICS.md), [F/DT findings](reviews/RUNTIME_FINDINGS.md#issue-navigation) |
| Nursing complete fourteen-page conversion | [Task closeout with known figure limitation](decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01); [Stage B](PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) | [Product direction and review basis](discussions/NURSING.md#product-direction-correction-and-review-basis-2026-10-31), [current direction and earlier decisions](decisions/NURSING.md#product-outcome-direction-2026-10-31) | [Historical delivery evidence and preserved acceptance correction](verification/20261031_2242_NURSING_LIVE.md), [earlier dispatch](verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md), [current readiness/next selection](CURRENT_STATE.md#nursing-boundary-and-next-product-decision) |
| Langfuse, control APIs, retention and other unselected changes | [PROPOSED_CHANGES](PROPOSED_CHANGES.md#find-an-option) | [Observability alternatives](discussions/OBSERVABILITY.md), relevant topic decisions | Inclusion is not adoption or a prerequisite; use each recorded reconsideration condition. |
| Framework, architecture and integration | [ARCHITECTURE](ARCHITECTURE.md), [requirements](PRODUCT_REQUIREMENTS.md) | [Rebuild decisions](decisions/REBUILD.md), [original foundation discussion](history/discussions/20261031_0157_REBUILD_FOUNDATIONS.md) | [Integration guide](guides/INTEGRATION_AND_MODEL_BOUNDARY.md), [source inventory](sources/INDEX.md) |
| Development credential loading and startup | [Implemented mechanism](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#development-credential-file-loading), [selected follow-up and acceptance](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#selected-credential-follow-up-target-2026-11-06), [original matrix](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#credential-repair-acceptance) | [Whole-development selection](discussions/REQUEST_CAPACITY.md#development-credential-loading-selected-and-verified-2026-11-06), [original repair rationale](discussions/REQUEST_CAPACITY.md#credential-startup-repair-selection-and-handoff-2026-11-06), [follow-up selection](discussions/REQUEST_CAPACITY.md#credential-follow-up-repair-selection-and-handoff-2026-11-06) | [CRED-01/02 review](reviews/RUNTIME_FINDINGS.md#development-credential-startup-review-2026-11-06), [original execution](reviews/RUNTIME_FINDINGS.md#credential-startup-repair-implementation-and-offline-acceptance-2026-11-06), [CRED-03/04 review](reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06), [dispositions](WORK_ITEMS.md#development-credential-startup), [active handoff](REVIEW_HANDOFF.md#credential-follow-up-implementation-handoff-2026-11-06) |
| Documentation organization and historical correspondence | [Filing rules below](#maintaining-this-catalogue) | [Ownership decision](decisions/DOCUMENTATION.md#updated-skill-organization-2026-11-06) | [Organization verification](verification/20261106_2300_PROJECT_ORGANIZATION.md), [DOC-09–13](reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md), [DOC-14–19 conformance review](reviews/20261031_1917_DOCUMENTATION_CONFORMANCE.md), [conformance checks](verification/20261031_1917_DOCUMENTATION_CONFORMANCE.md) |
| Repository layout, tests, utilities and artifact ownership | [Project layout](guides/PROJECT_LAYOUT.md), [artifact storage](ARTIFACT_STORAGE.md) | [Organization decision](decisions/PROJECT_ORGANIZATION.md) | [Organization checks](verification/20261031_1646_PROJECT_ORGANIZATION.md), [follow-up review and ORG-01](reviews/20261031_1907_PROJECT_ORGANIZATION.md); product phase/readiness remain with their existing owners. |

## Decisions

Decisions are organized by the topic rows above and the decision category below. Designs identify applicable entries, including carried-forward choices; an old decision can still be effective. To inspect an older edition, follow the design's preserved-source/version route and that edition's own basis. Do not match dates or assume the newest decision replaces every older choice. Earlier permission statements apply to their recorded tasks.

## Maintaining this catalogue

Keep stable undated active state/design/discussion/decision paths. Use `YYYYMMDD_HHMM_` for new standalone event/round documents or historical captures, with timezone and timestamp meaning stated inside. Related checks can share one verification document while retaining distinguishable run identities, results and original evidence. Existing legacy history/aggregate finding filenames remain deliberate category owners, not fabricated event timestamps.

Before substantively changing a design or a shared rule/source it relies on, preserve the necessary prior version and exact basis. Use stable retained entries where sufficient; do not copy the whole project or create one file per rule/turn. Current shared-owner links are useful lookup, but do not substitute for historical rule versions. Update changed facts in their owners, replace redundant restatements with descriptive links, and verify affected old routes. A move changes locator metadata, not original evidence bytes or adoption status.

Record findings, reasons, dispositions and unselected options in their topic owners. Update catalogue rows when a maintained document is added/moved/retired; do not put detailed status or another backlog here. The whole-project inventory is below; local contents/source manifests are subordinate navigation, not competing catalogues. Private/local evidence is explicitly limited to its availability. Technical names, source language, counterexamples and consequential rationale remain preserved.

## Complete maintained-document catalogue

The following lists maintained documents, root guidance, fixture documentation and preserved editions. Original source collections are represented by their entry points and complete manifests; the hundreds of verbatim messages/attachments/images are not duplicated as catalogue rows. The original [rebuild bundle manifest](sources/rebuild/bundle-manifest.json), [source inventory](sources/source-inventory.json) and [context-evidence manifest](sources/context-coordination/manifest.json) enumerate them.

### Project entry and current owners

| Document | Purpose / role |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Rebuild working agreement |
| [CHANGELOG.md](../CHANGELOG.md) | Changelog |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Rebuild architecture |
| [docs/ARTIFACT_STORAGE.md](ARTIFACT_STORAGE.md) | Maintained, private, runtime, test and build storage; retention and packaging boundaries. |
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
| [docs/WORK_ITEMS.md](WORK_ITEMS.md) | Project-wide work register and current item dispositions. |

### Current topic designs

| Document | Purpose / role |
| --- | --- |
| [docs/design/ACCEPTED_EVIDENCE_RECOVERY.md](design/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted-evidence conflict diagnosis and recovery |
| [docs/design/CONTEXT_MANAGEMENT.md](design/CONTEXT_MANAGEMENT.md) | Context management and capacity contract |
| [docs/design/CONTEXT_UPDATE_COORDINATION.md](design/CONTEXT_UPDATE_COORDINATION.md) | Context update coordination: consolidated target design |
| [docs/design/DOCUMENT_MODEL.md](design/DOCUMENT_MODEL.md) | Document model, editing and precise evidence access |
| [docs/design/LOCAL_DIAGNOSTICS.md](design/LOCAL_DIAGNOSTICS.md) | Local activity and diagnostic projection |
| [docs/design/FIGURE_DELIVERY.md](design/FIGURE_DELIVERY.md) | Complete independent figures with adjacent source-grounded text; adopted requirements and proposed implementation/checks |
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
| [docs/guides/PROJECT_LAYOUT.md](guides/PROJECT_LAYOUT.md) | Code/test/tool ownership, development routes and earlier-location lookup. |

### Discussions

| Document | Purpose / role |
| --- | --- |
| [docs/discussions/ACCEPTED_EVIDENCE_RECOVERY.md](discussions/ACCEPTED_EVIDENCE_RECOVERY.md#current-position) | Accepted-evidence recovery: discussion and alternatives |
| [docs/discussions/CONTEXT_COORDINATION.md](discussions/CONTEXT_COORDINATION.md#current-view-and-authority) | Context management: discussion and design convergence |
| [docs/discussions/NURSING.md](discussions/NURSING.md#current-question-and-boundary) | Nursing conversion: current discussion |
| [docs/discussions/OBSERVABILITY.md](discussions/OBSERVABILITY.md#current-position) | Observability and Langfuse: discussion |
| [docs/discussions/REQUEST_CAPACITY.md](discussions/REQUEST_CAPACITY.md#current-question-and-discussion-status) | Request capacity and usable context: discussion |
| [docs/discussions/STREAMING_RECEIVE.md](discussions/STREAMING_RECEIVE.md#current-position-and-discussion-status) | Streaming receive: discussion and evolution |

### Decisions

| Document | Purpose / role |
| --- | --- |
| [docs/decisions/ACCEPTED_EVIDENCE_RECOVERY.md](decisions/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted Evidence Recovery: decisions and rationale |
| [docs/decisions/CONTEXT_MANAGEMENT.md](decisions/CONTEXT_MANAGEMENT.md) | Context Management: decisions and rationale |
| [docs/decisions/DOCUMENTATION.md](decisions/DOCUMENTATION.md) | Documentation organization decisions |
| [docs/decisions/INITIAL_CONTRACTS.md](decisions/INITIAL_CONTRACTS.md) | Closed first-version contract choices and their original questions |
| [docs/decisions/LOCAL_DIAGNOSTICS.md](decisions/LOCAL_DIAGNOSTICS.md) | Local Diagnostics: decisions and rationale |
| [docs/decisions/NURSING.md](decisions/NURSING.md) | Nursing: decisions and rationale |
| [docs/decisions/PROJECT_ORGANIZATION.md](decisions/PROJECT_ORGANIZATION.md) | Repository organization, preserved guarantees, findings and acceptance. |
| [docs/decisions/REBUILD.md](decisions/REBUILD.md) | Rebuild: decisions and rationale |
| [docs/decisions/STREAMING_RECEIVE.md](decisions/STREAMING_RECEIVE.md) | Streaming Receive: decisions and rationale |

### Research

| Document | Purpose / role |
| --- | --- |
| [docs/research/20261031_0157_NEXUS_STREAMING_SIGNALS.md](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md) | Nexus and CLIProxyAPI streaming signal evidence |

### Verification

| Document | Purpose / role |
| --- | --- |
| [docs/verification/20261106_2300_PROJECT_ORGANIZATION.md](verification/20261106_2300_PROJECT_ORGANIZATION.md) | Updated-skill organization, entry preservation, owner mapping and navigation checks |
| [docs/verification/20261105_0220_USAGE_OBSERVATION.md](verification/20261105_0220_USAGE_OBSERVATION.md) | Observation-only usage anchoring: specification/source identity, offline equivalence and faults, work/storage measurements and readiness limits. |
| [docs/verification/20261031_2242_NURSING_LIVE.md](verification/20261031_2242_NURSING_LIVE.md) | Authorized finite fourteen-page Nursing execution, observed consumption/exits and source-led acceptance. |
| [docs/verification/20261031_2220_VERSION_PUBLICATION.md](verification/20261031_2220_VERSION_PUBLICATION.md) | Selected new-version publication increment, checks and concrete Nursing validation preparation. |
| [docs/verification/20261031_2019_R07_INTEGRATION.md](verification/20261031_2019_R07_INTEGRATION.md) | Selected baseline integration, bounded R07 settlement/reopen acceptance and fresh execution evidence. |
| [docs/verification/20261031_0157_DOCUMENTATION_STRUCTURE.md](verification/20261031_0157_DOCUMENTATION_STRUCTURE.md) | Documentation reorganization verification |
| [docs/verification/20261101_0033_FD01_LOCAL.md](verification/20261101_0033_FD01_LOCAL.md) | FD-01 local implementation, offline evidence and finite two-page proposal; no provider calls |
| [docs/verification/20261101_0103_FD01_TWO_PAGE_LIVE.md](verification/20261101_0103_FD01_TWO_PAGE_LIVE.md) | Approved two-page interval, refreshed preparation, consumption and actual source/package acceptance |
| [docs/verification/20261031_0157_LOCAL_DIAGNOSTICS.md](verification/20261031_0157_LOCAL_DIAGNOSTICS.md) | Local diagnostic implementation and verification record |
| [docs/verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md](verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md) | Nursing baseline and single-dispatch evidence |
| [docs/verification/20261031_0342_TEST_ARTIFACT_RETENTION.md](verification/20261031_0342_TEST_ARTIFACT_RETENTION.md) | Authorized test-product cleanup, exact retained exceptions and historical evidence availability |
| [docs/verification/20261031_1646_PROJECT_ORGANIZATION.md](verification/20261031_1646_PROJECT_ORGANIZATION.md) | Repository relocation, test discovery, preservation and execution checks, with [path map](verification/20261031_1646_PROJECT_RELOCATIONS.json) and [implementation identity](verification/20261031_1646_PROJECT_SOURCE.json). |
| [docs/verification/20261031_1917_DOCUMENTATION_CONFORMANCE.md](verification/20261031_1917_DOCUMENTATION_CONFORMANCE.md) | Applicable documentation-rule coverage, semantic/navigation checks and preservation. |
| [docs/verification/20261031_1917_RECOVERY_ACCEPTANCE.md](verification/20261031_1917_RECOVERY_ACCEPTANCE.md) | Relocated 2026-10-29 recovery and diagnostic execution evidence; no new product run. |
| [docs/verification/20261031_1917_STREAMING_ACCEPTANCE.md](verification/20261031_1917_STREAMING_ACCEPTANCE.md) | Relocated SC02 source identity, failures/reruns and acceptance evidence from 2026-10-30. |

| [docs/verification/20261106_0112_WORK_REGISTER.md](verification/20261106_0112_WORK_REGISTER.md) | Development-entry/register reconciliation and checks. |

| [docs/verification/20261106_1408_R01CAL_TASK_A.md](verification/20261106_1408_R01CAL_TASK_A.md) | Task A baseline execution, source-led partial acceptance, native usage, credential-loading checks and A-to-B recommendation. |

### Findings and reviews

| Document | Purpose / role |
| --- | --- |
| [docs/reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md](reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md) | Documentation structure review and disposition |
| [docs/reviews/20261031_1907_PROJECT_ORGANIZATION.md](reviews/20261031_1907_PROJECT_ORGANIZATION.md) | Whole-project organization review, canonical fixture-import correction and scoped verification. |
| [docs/reviews/20261031_1917_DOCUMENTATION_CONFORMANCE.md](reviews/20261031_1917_DOCUMENTATION_CONFORMANCE.md) | DOC-14–19: documentation conformity gaps, impact and disposition. |
| [docs/reviews/20261031_0157_REBUILD_PRESERVATION.md](reviews/20261031_0157_REBUILD_PRESERVATION.md) | Preservation and self-containment audit |
| [docs/reviews/20261031_0157_REBUILD_TECHNICAL_DETAILS.md](reviews/20261031_0157_REBUILD_TECHNICAL_DETAILS.md) | Source-first technical-detail review |
| [docs/reviews/DOCUMENTATION_REORGANIZATION_2026-10.md](reviews/DOCUMENTATION_REORGANIZATION_2026-10.md) | Documentation reorganization review — October 2026 |
| [docs/reviews/RUNTIME_FINDINGS.md](reviews/RUNTIME_FINDINGS.md) | Runtime findings, dispositions and review reconciliation |

### Historical editions and stage records

| Document | Purpose / role |
| --- | --- |
| [docs/history/20261106_2300_README.md](history/20261106_2300_README.md) | Historical working-tree entry before updated-skill organization; original owner `README.md` |
| [docs/history/20261106_2300_CURRENT_STATE.md](history/20261106_2300_CURRENT_STATE.md) | Historical working-tree entry before updated-skill organization; original owner `docs/CURRENT_STATE.md` |
| [docs/history/20261106_2300_PHASE_PLAN.md](history/20261106_2300_PHASE_PLAN.md) | Historical working-tree entry before updated-skill organization; original owner `docs/PHASE_PLAN.md` |
| [docs/history/20261106_2300_REVIEW_HANDOFF.md](history/20261106_2300_REVIEW_HANDOFF.md) | Historical working-tree entry before updated-skill organization; original owner `docs/REVIEW_HANDOFF.md` |
| [docs/history/contracts/20261031_0157_ARCHITECTURE.md](history/contracts/20261031_0157_ARCHITECTURE.md) | Preserved edition / historical reasoning: Rebuild architecture |
| [docs/history/contracts/20261031_0157_CONTRACTS.md](history/contracts/20261031_0157_CONTRACTS.md) | Preserved edition / historical reasoning: Rebuild contracts |
| [docs/history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md](history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md) | Preserved edition / historical reasoning: Product requirements |
| [docs/history/decisions/20261031_0157_DECISIONS.md](history/decisions/20261031_0157_DECISIONS.md) | Preserved edition / historical reasoning: Decisions and rationale |
| [docs/history/design/20261031_0157_EXECUTION_AND_DELIVERY.md](history/design/20261031_0157_EXECUTION_AND_DELIVERY.md) | Preserved edition / historical reasoning: Execution, recovery, and delivery engineering handoff |
| [docs/history/design/20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md](history/design/20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md) | Preserved edition / historical reasoning: Integration and model-boundary engineering guide |
| [docs/history/design/20261031_1917_ACCEPTED_EVIDENCE_RECOVERY.md](history/design/20261031_1917_ACCEPTED_EVIDENCE_RECOVERY.md) | Pre-conformance recovery design capture with original reasoning and scope. |
| [docs/history/design/20261031_1917_CONTEXT_UPDATE_COORDINATION.md](history/design/20261031_1917_CONTEXT_UPDATE_COORDINATION.md) | Pre-conformance coordination design capture with its shared-rule and adoption basis. |
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
