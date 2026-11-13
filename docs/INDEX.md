# Project document catalogue

Use the current request to select a route. This file supplies navigation and the complete inventory; substantive rules, work decisions and evidence stay at the linked owners. [README](../README.md) explains setup/use and [AGENTS](../AGENTS.md) the working agreement.

## Start by task

| Request or question | Read first | Expand when relevant |
| --- | --- | --- |
| Continue without a named topic | [CURRENT_STATE](CURRENT_STATE.md#focus-and-resume-route), then its exact resume section and instruction basis | Actual task/source/evidence state before relying on readiness; ask only if consequential ambiguity remains. |
| Discuss or prepare a spec | The topic's discussion/open question and governing design from [Find by topic](#find-by-topic) | Applicable requirements, decisions, constraints and relevant phase conditions; no batch is required for an unfinished discussion. |
| Work on a named batch | Its spec, tasks and applicable verification in [Batch documents](#batch-documents) | Governing sections and their exceptions, affected code/usage consumers and source identities. A known task does not require reading the whole register/archive. |
| Choose the next work | [PHASE_PLAN](PHASE_PLAN.md#delivery-route), [WORK_ITEMS](WORK_ITEMS.md#selection-now), and current interaction context | Evidence and dependencies for consequential competing candidates; item ordering belongs in WORK_ITEMS. |
| Review or update documentation | The scoped task/topic owner and actual current basis | Related consumers found by names, concepts, paths and links, including files absent from the diff; [daily routine](../AGENTS.md#daily-development-and-document-maintenance). |
| Find a prior decision or result | Topic evidence/decision links, then the [catalogue](#complete-maintained-document-catalogue) if needed | Exact historical entry/version only when the question requires it. Source manifests are provenance, not a default reading queue. |

Read complete applicable sections, including exceptions and dependent rules. Headings/search hits locate content; they are not completed reading. Retrieve missing bodies after truncation. Follow a dependency when it can change scope, expected behavior, authority or acceptance; a navigation/backlink does not restart the reading route. A named task overrides an unrelated saved focus, while a ready spec alone grants no new authority.

## Batch documents

[Project ticket policy](../AGENTS.md#batch-documents-and-ticket-mode). These are stable destinations, not duplicate progress or verdict summaries. Create each file when its stage has content; completed batches retain their paths.

| Batch | Scope and planned acceptance | Execution owner | Actual evidence and verdict |
| --- | --- | --- | --- |
| NET-01 | [spec.md](batches/NET-01/spec.md) | [tickets.md](batches/NET-01/tickets.md) | [verification.md](batches/NET-01/verification.md) |
| R01CAL-A03-DELIVERY-01 | [spec.md](batches/R01CAL-A03-DELIVERY-01/spec.md) | [tickets.md](batches/R01CAL-A03-DELIVERY-01/tickets.md) | [verification.md](batches/R01CAL-A03-DELIVERY-01/verification.md) |
| R01CAL-A03 | [spec.md](batches/R01CAL-A03/spec.md) | [tickets.md](batches/R01CAL-A03/tickets.md) | [verification.md](batches/R01CAL-A03/verification.md) |
| R01CAL-A02 | [spec.md](batches/R01CAL-A02/spec.md) | [tickets.md](batches/R01CAL-A02/tickets.md) | [verification.md](batches/R01CAL-A02/verification.md) |
| R01CAL-A01 | [spec.md](batches/R01CAL-A01/spec.md) | [tickets.md](batches/R01CAL-A01/tickets.md) | [verification.md](batches/R01CAL-A01/verification.md) |
| DOC-FLOW-01 | [spec.md](batches/DOC-FLOW-01/spec.md) | [tickets.md](batches/DOC-FLOW-01/tickets.md) | [verification.md](batches/DOC-FLOW-01/verification.md) |
| CRED-03-04 | [spec.md](batches/CRED-03-04/spec.md) | [tickets.md](batches/CRED-03-04/tickets.md) | [verification.md](batches/CRED-03-04/verification.md) |
| DOC-ORG-R1 | [spec.md](batches/DOC-ORG-R1/spec.md) | [tickets.md](batches/DOC-ORG-R1/tickets.md) | [verification.md](batches/DOC-ORG-R1/verification.md) |
| DOC-LAYOUT-01 | [spec.md](batches/DOC-LAYOUT-01/spec.md) | [tickets.md](batches/DOC-LAYOUT-01/tickets.md) | [verification.md](batches/DOC-LAYOUT-01/verification.md) |

## Find by topic

| Topic / search terms | Governing or discussion entry | Conditional detail and evidence |
| --- | --- | --- |
| Development credentials, file discovery/read failure, Remember/Clear | [DEVELOPMENT_CREDENTIALS](design/DEVELOPMENT_CREDENTIALS.md#basis-and-reading-route) | [Implementation guide](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#credential-implementation-and-checks), [CRED-03-04](batches/CRED-03-04/spec.md), [selection](discussions/REQUEST_CAPACITY.md#credential-follow-up-repair-selection-and-handoff-2026-11-06), [counterexamples](reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06). Read original and follow-up matrices for changes to this owner. |
| Documents, candidates, exact saved versions, field/range reads | [DOCUMENT_MODEL](design/DOCUMENT_MODEL.md) | [DOCUMENT_ENGINE](guides/DOCUMENT_ENGINE.md), [Q1 decision](decisions/INITIAL_CONTRACTS.md#q1-document-update-and-candidate-reference-contract), [implementation evidence](history/IMPLEMENTATION_HISTORY.md#document-editing-increment). |
| Asset references, readable filenames, embedded provenance and synchronized delivery | [Adopted asset design](design/ASSET_REFERENCES.md#design-basis-and-ownership), [discussion and investigation](discussions/ASSET_REFERENCES.md#current-question-and-authority), [repair specification](batches/R01CAL-A03-DELIVERY-01/spec.md) | [Document rules](design/DOCUMENT_MODEL.md#q1-document-schema-and-commit), [image/original preservation](design/PDF_EVIDENCE.md#pdf-coordinates-and-image-delivery), [A03 finding](batches/R01CAL-A03/verification.md#r01cal-a03-delivery-01--linked-page-renders-are-absent-from-the-saved-version-and-zip), [work selection](WORK_ITEMS.md#context-capability-and-delivery-work). |
| Context capacity, pins, handoff and coordinated updates | [CONTEXT_MANAGEMENT](design/CONTEXT_MANAGEMENT.md), [CONTEXT_UPDATE_COORDINATION](design/CONTEXT_UPDATE_COORDINATION.md) | [Discussion](discussions/CONTEXT_COORDINATION.md#current-view-and-authority), [decisions](decisions/CONTEXT_MANAGEMENT.md), [engineering](guides/CONTEXT_AND_EVIDENCE.md), [coordination evidence](history/IMPLEMENTATION_HISTORY.md#complete-context-update-coordination). |
| R01 calibration, route limits and complete-section delivery | [REQUEST_CAPACITY](discussions/REQUEST_CAPACITY.md#current-question-and-discussion-status), [work selection](WORK_ITEMS.md#production-estimation-residuals) | [R01CAL-A01 diagnosis scope](batches/R01CAL-A01/spec.md), [R01CAL-A02 metadata-only exercise](batches/R01CAL-A02/spec.md), [R01CAL-A03 fresh-conversion scope and transition](batches/R01CAL-A03/spec.md), [Task A evidence](verification/20261106_1408_R01CAL_TASK_A.md), [runtime finding index](reviews/RUNTIME_FINDINGS.md#finding-index). Follow the specific study/selection entries from those owners rather than every earlier exchange. |
| Usage observer, anchoring trial and coordinator | [Usage-anchoring design](design/CONTEXT_MANAGEMENT.md#usage-anchoring-v1-first-bounded-trial-2026-11-05) | [Observer evidence](verification/20261105_0220_USAGE_OBSERVATION.md), [UA-01 evidence](reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06), [work/revisit decisions](WORK_ITEMS.md#observer-findings). |
| Durable effects, Continue/Stop, task settings, export | [RUNTIME_AND_DELIVERY](design/RUNTIME_AND_DELIVERY.md) | [EXECUTION_AND_DELIVERY](guides/EXECUTION_AND_DELIVERY.md), [Q3 decision](decisions/INITIAL_CONTRACTS.md#q3-persistence-recovery-and-stop-contract), [publication evidence](verification/20261031_2220_VERSION_PUBLICATION.md). |
| Network failures, HTTP errors, transport retry and replay of model requests | [Runtime transport rules](design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior), [network discussion](discussions/NETWORK_RECOVERY.md#current-question-and-authority), [NET-01 spec](batches/NET-01/spec.md) and [tickets](batches/NET-01/tickets.md) | [R04 evidence](reviews/RUNTIME_FINDINGS.md#r04--http-errors-lose-diagnostic-body-and-have-no-automatic-retry), [offline verification](batches/NET-01/verification.md), [Stage C conditions](PHASE_PLAN.md#c-continue-through-ordinary-interruptions). |
| R03 local OCR/scripts interrupted with unknown effects | [Runtime rules](design/RUNTIME_AND_DELIVERY.md#3-persistence-recovery-and-stop-behavior), [R03 evidence](reviews/RUNTIME_FINDINGS.md#r03--local-process-stop-can-leave-no-supported-continuation) | [Work disposition](WORK_ITEMS.md#runtime-and-engineering-inventory), [Stage C conditions](PHASE_PLAN.md#c-continue-through-ordinary-interruptions). Do not infer a selected recovery batch from a discussion example. |
| Accepted-evidence diagnosis and bounded recovery | [ACCEPTED_EVIDENCE_RECOVERY](design/ACCEPTED_EVIDENCE_RECOVERY.md) | [Discussion](discussions/ACCEPTED_EVIDENCE_RECOVERY.md#current-position), [decisions](decisions/ACCEPTED_EVIDENCE_RECOVERY.md), [checks](verification/20261031_1917_RECOVERY_ACCEPTANCE.md). Eligibility does not grant permission to replay a task. |
| Streaming waiting, completion and accepted reply settlement | [STREAMING_RECEIVE](design/STREAMING_RECEIVE.md) | [Discussion](discussions/STREAMING_RECEIVE.md#current-position-and-discussion-status), [decisions](decisions/STREAMING_RECEIVE.md), [route research](research/20261031_0157_NEXUS_STREAMING_SIGNALS.md), [recorded checks](verification/20261031_1917_STREAMING_ACCEPTANCE.md). |
| PDF coordinates, faithful images and figure delivery | [PDF_EVIDENCE](design/PDF_EVIDENCE.md), [FIGURE_DELIVERY](design/FIGURE_DELIVERY.md) | [Engineering](guides/CONTEXT_AND_EVIDENCE.md#implemented-pdf-coordinates-and-image-delivery), [local figure checks](verification/20261101_0033_FD01_LOCAL.md), [two-page evidence](verification/20261101_0103_FD01_TWO_PAGE_LIVE.md), [source limits](sources/REFERENCE_INPUTS.md). |
| Nursing task and source-led conversion acceptance | [Discussion](discussions/NURSING.md#current-question-and-boundary), [Stage B conditions](PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) | [Historical closeout](decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01), [full-run evidence/correction](verification/20261031_2242_NURSING_LIVE.md), [earlier dispatch](verification/20261031_0157_NURSING_BASELINE_AND_DISPATCH.md). |
| Local diagnostics, activity and typed client | [LOCAL_DIAGNOSTICS](design/LOCAL_DIAGNOSTICS.md) | [Discussion](discussions/OBSERVABILITY.md#current-position), [decisions](decisions/LOCAL_DIAGNOSTICS.md), [recorded checks](verification/20261031_0157_LOCAL_DIAGNOSTICS.md), [F/DT findings](reviews/RUNTIME_FINDINGS.md#issue-navigation). |
| Framework, native protocols and integration | [ARCHITECTURE](ARCHITECTURE.md), [PRODUCT_REQUIREMENTS](PRODUCT_REQUIREMENTS.md) | [INTEGRATION_AND_MODEL_BOUNDARY](guides/INTEGRATION_AND_MODEL_BOUNDARY.md#read-by-integration-question), [rebuild decisions](decisions/REBUILD.md). |
| Unselected options, telemetry, retention and lifecycle | [PROPOSED_CHANGES](PROPOSED_CHANGES.md#find-an-option) | [Work/revisit conditions](WORK_ITEMS.md#diagnostics-and-retained-options), relevant discussion/decision owners. Inclusion is not adoption. |
| Documentation and continuation | [Ownership and update rules](#maintaining-this-catalogue) | [Adoption](decisions/DOCUMENTATION.md#progressive-disclosure-and-interaction-continuation-2026-11-07), [DOC-FLOW-01](batches/DOC-FLOW-01/spec.md), [earlier qualifying review](reviews/20261106_2307_ORGANIZATION_REVIEW.md#assessment). |
| Source/test/tool layout, generated outputs and retention | [PROJECT_LAYOUT](guides/PROJECT_LAYOUT.md), [ARTIFACT_STORAGE](ARTIFACT_STORAGE.md) | [Organization decision](decisions/PROJECT_ORGANIZATION.md), [recorded checks](verification/20261031_1646_PROJECT_ORGANIZATION.md), [ORG-01 review](reviews/20261031_1907_PROJECT_ORGANIZATION.md). |

## Initial contract basis

The first-version Q1/Q2/Q3 forms refine, rather than replace, their original responsibility boundaries: [DOCUMENT_MODEL](design/DOCUMENT_MODEL.md), [CONTEXT_MANAGEMENT](design/CONTEXT_MANAGEMENT.md) and [RUNTIME_AND_DELIVERY](design/RUNTIME_AND_DELIVERY.md) own their substantive rules. [INITIAL_CONTRACTS](decisions/INITIAL_CONTRACTS.md) preserves closure reasoning. Adopted design, implementation, local checks, route behavior and full-source acceptance are distinct. The [preceding contract navigator](history/20261107_1358_CONTRACTS.md) and [older contract edition](history/contracts/20261031_0157_CONTRACTS.md) retain historical context; they are not competing live rules.

## Maintaining this catalogue

| Owner | Maintains | Update trigger |
| --- | --- | --- |
| CURRENT_STATE | Interaction focus, exact resume route, next activity/instruction basis, parked-work links | Activity/focus/authority changes; save substantive content before updating the pointer. |
| WORK_ITEMS | Problem/event identities and evidence links; work selection, priority/deferral reasons, residual scope and revisit conditions | A missing identity/link or reached revisit condition needs recording, or these planning facts change; do not copy a task or batch verdict as a second disposition. |
| PHASE_PLAN | Phase outcomes, ordering and phase-level acceptance | Outcome, dependency, scope or acceptance basis changes; no per-ticket status update. |
| Topic design / discussion / decision | Effective rules / unresolved positions / adopted choices and reasons | Meaningful evidence or choice changes; preserve the distinction between proposed and adopted. |
| Batch spec / tickets / verification | Agreement and criteria / execution / observed evidence and verdict | Their own facts change; prior evidence keeps its tested identity and limits. |
| Guides and README | Procedures, explanations and user-facing examples | A governing behavior/interface changes their meaning, even when they are absent from the code diff. |
| INDEX | Reading routes and complete catalogue | Add/move/retire an owner or change a reading dependency; no mutable result values in link labels. |

Maintain directed references to substantive owners and find affected consumers by topic/concept/identifier/path searches. A stable link alone does not keep surrounding examples correct. Use the [daily routine](../AGENTS.md#daily-development-and-document-maintenance); record actual documentation impact in the selected verification/review owner. No separate read log or mirrored status ledger is required. Keep current topic filenames stable; add files only when they have distinct substantive content. A new conversation or a long file alone does not require splitting.

Preserve exact applicable design/source versions before material replacement. Git retains ordinary edits; historical captures identify original scope, recording time/timezone and locator adjustments. Original source collections, failed checks, counterexamples and unselected alternatives retain meaning. Catalogue history for discovery but load it only for the current question. Useful return links are navigation, not instructions to reread the whole route.

## Complete maintained-document catalogue

Batch specifications, local tickets and verification owners are catalogued once in [Batch documents](#batch-documents). The categories below list the other maintained documents, root guidance, fixture documentation and preserved editions. Original source collections are represented by their entry points and complete manifests; the hundreds of verbatim messages/attachments/images are not duplicated as catalogue rows. The original [rebuild bundle manifest](sources/rebuild/bundle-manifest.json), [source inventory](sources/source-inventory.json) and [context-evidence manifest](sources/context-coordination/manifest.json) enumerate them.

### Project entry and current owners

| Document | Purpose / role |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Rebuild working agreement |
| [CHANGELOG.md](../CHANGELOG.md) | Changelog |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Rebuild architecture |
| [docs/ARTIFACT_STORAGE.md](ARTIFACT_STORAGE.md) | Maintained, private, runtime, test and build storage; retention and packaging boundaries. |
| [docs/CURRENT_STATE.md](CURRENT_STATE.md) | Interaction focus, exact resume point and instruction basis. |
| [docs/DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Development handoff |
| [docs/INDEX.md](INDEX.md) | Task/topic routes and complete document inventory. |
| [docs/PHASE_PLAN.md](PHASE_PLAN.md) | Phase outcomes, ordering and phase-level acceptance. |
| [docs/PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) | Product requirements |
| [docs/PROPOSED_CHANGES.md](PROPOSED_CHANGES.md) | Unselected changes, tradeoffs and reconsideration conditions. |
| [docs/TECHNICAL_TERMS.md](TECHNICAL_TERMS.md) | Technical terminology and mechanism navigator |
| [README.md](../README.md) | pdf-to-md-agent-2 |
| [docs/WORK_ITEMS.md](WORK_ITEMS.md) | Work selection, comparative priority, residual scope and revisit decisions. |

### Current topic designs

| Document | Purpose / role |
| --- | --- |
| [docs/design/ACCEPTED_EVIDENCE_RECOVERY.md](design/ACCEPTED_EVIDENCE_RECOVERY.md) | Accepted-evidence conflict diagnosis and recovery |
| [docs/design/ASSET_REFERENCES.md](design/ASSET_REFERENCES.md) | Adopted portable asset naming/provenance, schema/API, reference/save/view/export and dependency design, with rationale and implementation/evidence routes; [design versions](design/ASSET_REFERENCES.md#design-versions) locate preserved editions. |
| [docs/design/CONTEXT_MANAGEMENT.md](design/CONTEXT_MANAGEMENT.md) | Context management and capacity contract |
| [docs/design/CONTEXT_UPDATE_COORDINATION.md](design/CONTEXT_UPDATE_COORDINATION.md) | Context update coordination: consolidated target design |
| [docs/design/DEVELOPMENT_CREDENTIALS.md](design/DEVELOPMENT_CREDENTIALS.md) | Credential-file policy, state ownership and acceptance matrices |
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
| [tools/qualification/README.md](../tools/qualification/README.md) | Acceptance-only Windows metadata harness, isolated reader build and reproduction instructions; qualification results stay in the batch verification. |

### Discussions

| Document | Purpose / role |
| --- | --- |
| [docs/discussions/ACCEPTED_EVIDENCE_RECOVERY.md](discussions/ACCEPTED_EVIDENCE_RECOVERY.md#current-position) | Accepted-evidence recovery: discussion and alternatives |
| [docs/discussions/ASSET_REFERENCES.md](discussions/ASSET_REFERENCES.md#current-question-and-authority) | Portable asset references: offline investigation, alternatives and specification basis |
| [docs/discussions/CONTEXT_COORDINATION.md](discussions/CONTEXT_COORDINATION.md#current-view-and-authority) | Context management: discussion and design convergence |
| [docs/discussions/NETWORK_RECOVERY.md](discussions/NETWORK_RECOVERY.md#current-question-and-authority) | Network failure handling: discussion |
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
| [docs/reviews/20261106_2307_ORGANIZATION_REVIEW.md](reviews/20261106_2307_ORGANIZATION_REVIEW.md) | Updated-skill reorganization review: preservation comparisons, reader checks and remaining active duplication |
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
| [Asset-reference design and acceptance editions](design/ASSET_REFERENCES.md#design-versions) | Topic-owned version list locates the paired pre-protocol and pre-primary-XMP captures and their preserved rule/acceptance basis. |
| [AR-S4.2 before design filing](batches/R01CAL-A03-DELIVERY-01/20261108_1652_spec_AR_S4_2.md) | Preserved complete pre-filing layout; adopted rule bodies subsequently live in the design owner with batch acceptance retained in the spec. |
| [AR-S4.1 before dependency applicability audit](batches/R01CAL-A03-DELIVERY-01/20261108_1634_spec_AR_S4_1.md) | Inactive production-pin edition before the wider release-channel and later-fix assessment; original body preserved. |
| [AR-S4 before production-release correction](batches/R01CAL-A03-DELIVERY-01/20261108_1616_spec_AR_S4.md) | Inactive technical specification before reconsidering the ExifTool development-release pin; original body preserved. |
| [AR-S3 before technical completion](batches/R01CAL-A03-DELIVERY-01/20261108_1555_spec_AR_S3.md) | Inactive edition before concrete schema/API/dependency selection; original body and relative-link base preserved. |
| [AR-S2 before technical-choice adoption](batches/R01CAL-A03-DELIVERY-01/20261108_1536_spec_AR_S2.md) | Inactive product-spec edition before selection of the four approaches and ampersand locator correction; original body preserved. |
| [AR-S1 draft and naming-discussion amendments](batches/R01CAL-A03-DELIVERY-01/20261108_1152_spec_AR_S1.md) | Captured before AR-S2 consolidation; original body preserved in the same relative-link directory. Inactive specification history, not a competing current target. |
| [docs/history/20261107_BATCH_LAYOUT_REVIEW_HANDOFF.md](history/20261107_BATCH_LAYOUT_REVIEW_HANDOFF.md) | Captured assignment before fixed batch-file migration |
| [docs/history/20261107_BATCH_LAYOUT_WORK_ITEMS.md](history/20261107_BATCH_LAYOUT_WORK_ITEMS.md) | Captured register before fixed batch-file migration |
| [docs/history/20261107_1358_CURRENT_STATE.md](history/20261107_1358_CURRENT_STATE.md) | Captured preceding docs/CURRENT_STATE.md; original scope retained with locator adjustments |
| [docs/history/20261107_1358_PHASE_PLAN.md](history/20261107_1358_PHASE_PLAN.md) | Captured preceding docs/PHASE_PLAN.md; original scope retained with locator adjustments |
| [docs/history/20261107_1358_WORK_ITEMS.md](history/20261107_1358_WORK_ITEMS.md) | Captured preceding docs/WORK_ITEMS.md; original scope retained with locator adjustments |
| [docs/history/20261107_1358_CONTRACTS.md](history/20261107_1358_CONTRACTS.md) | Captured preceding docs/CONTRACTS.md; original scope retained with locator adjustments |
| [docs/history/20261107_1358_REVIEW_HANDOFF.md](history/20261107_1358_REVIEW_HANDOFF.md) | Captured preceding docs/REVIEW_HANDOFF.md; original scope retained with locator adjustments |
| [docs/history/design/20261107_1358_DEVELOPMENT_CREDENTIALS.md](history/design/20261107_1358_DEVELOPMENT_CREDENTIALS.md) | Captured credential rule/acceptance body before owner relocation |
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
