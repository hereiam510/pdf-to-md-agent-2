# Shared contract navigator

## Reading this contract

The agreed document, context and execution boundaries and their implemented Q1–Q3 forms are now owned together by topic below. This is a relocation, not a new behavior or schema selection. Detailed engineering explanations remain in the guides; historical examples retain their original status. Start with [the document catalogue](INDEX.md) or [current readiness](CURRENT_STATE.md).

| Responsibility | Effective owner |
| --- | --- |
| Q1 documents, candidates, precise reads and working-evidence feedback | [Document model](design/DOCUMENT_MODEL.md) |
| Q2 context capacity, handoff, pins and admission | [Context management](design/CONTEXT_MANAGEMENT.md), [coordination mechanism](design/CONTEXT_UPDATE_COORDINATION.md) |
| Q3 persistence, Continue, Stop, budgets, settings and export | [Runtime and delivery](design/RUNTIME_AND_DELIVERY.md) |
| Historical accepted-evidence recovery | [Recovery design](design/ACCEPTED_EVIDENCE_RECOVERY.md#historical-accepted-evidence-local-recovery) |
| PDF coordinates, image display and preserved originals | [PDF evidence](design/PDF_EVIDENCE.md) |
| Streaming waits, response completion, storage and acceptance | [Streaming receive](design/STREAMING_RECEIVE.md) |
| Read-only activity/diagnostics and raw versus validated facts | [Local diagnostics](design/LOCAL_DIAGNOSTICS.md) |

## Implemented first-version contracts

The earlier responsibility sections and later implemented forms are complementary, not competing contracts. The implemented Q1–Q3 schemas/transitions refine those boundaries; scope remains [the product requirements](PRODUCT_REQUIREMENTS.md), and [initial contract decisions](decisions/INITIAL_CONTRACTS.md) retain closure reasoning. Adopted design, implemented code, local checks, actual route behavior and full PDF acceptance remain distinct.

The [pre-reorganization contract edition](history/contracts/20261031_0157_CONTRACTS.md) preserves the complete preceding view. Later changes must preserve affected historical rules and their referenced requirements/architecture/acceptance before replacement; a live current-owner link is not a historical version identifier.
