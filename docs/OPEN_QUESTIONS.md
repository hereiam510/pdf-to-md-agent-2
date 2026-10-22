# First-version open questions

The user explicitly stopped incremental design expansion (EVT-1148). EVT-1166 consolidated three unresolved contracts. Preserve the following distinction: the responsibilities and recommended tradeoffs are known; exact executable schemas and transition semantics still need a coherent specification and implementation. This file does not queue model experiments.

The detailed engineering background is local in [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md) and its linked guides. These open choices are not permission to leave previously discussed mechanisms unexplained or send the next developer back to a conversation archive.

## Q1. Document update and candidate-reference contract

**Observed:** a prior full page-map validation rejection left correct candidate prose available, but later regeneration changed `本文件` to `本文作`. Pure insertion/append and partial-map updates were identified as editing friction. This supports exact reuse and local correction; it does not prove compaction caused the typo or that previous conversions could never complete.

**Hypothesis/deferred:** automatic salvage of partial JSON may save work, but its complete-delivery benefit is unmeasured and it is not needed to settle this contract.

**Recommended tradeoff:** exact reuse of complete candidates; insertion/append and metadata patches; preserve untouched content; validate the complete merged result. Immutable version files own body content; SQLite owns registration/pointers/receipts. Retain malformed originals without requiring automatic salvage.

**Still to specify:** reference identity and applicability, patch/merge semantics, omitted-field behavior, operation success/visibility boundary and the receipt returned on replay.

**Design closure:** the contract can unambiguously express (1) fixing only page metadata, (2) inserting new content, and (3) reusing a rejected candidate without regenerating unchanged prose. For each, identify the original, the changed fields, the unchanged fields and when commit succeeds.

## Q2. Context capacity and handoff contract

**Observed:** large inspect/OCR results consumed substantial input, and a prior checkpoint reduced input while exact evidence retrieval remained possible. Those scoped results do not establish universal cost benefits or lossless continuation.

**Hypotheses:** draft-heavy history may still exceed capacity after evidence release; delta summaries may lose active facts when an anchor changes. These are boundary scenarios, not claimed observed app failures.

**Recommended tradeoff:** configurable effective route capacity/output reserve; complete assembled-request assessment; release saved unnecessary content before older-history compaction where useful; self-sufficient continuation handoff; bounded incremental compaction; failure preserves originals. Latest drafts/unfinished candidates may be partially released. Do not freeze a universal recent-turn count or percentage.

**Still to specify:** capacity/unknown-estimate handling, exact history coverage/revision application, summary replacement and rejection behavior, handoff content contract and the stop path when no fitting request can be assembled within budget.

**Design closure:** sending, releasing, compacting and stopping each have explicit transitions; unprocessed history survives; failure cannot destroy originals; normal requests respect the configured capacity check. A universal optimum threshold and guaranteed compaction count are unnecessary.

## Q3. Persistence, recovery and stop contract

**Observed:** earlier saved-work continuation and scoped injected-fault continuation succeeded. These are rationale for durability, not proof of arbitrary crash/natural-outage recovery in the rebuild.

**Hypotheses:** a tool may commit before a graph checkpoint, and replay may occur after head advances. These need finite reconciliation rules rather than a general distributed system.

**Recommended tradeoff:** one active writer per task; one authority per request/batch/version/receipt; frozen same-request replay; finish the accepted batch before another model step; original receipts without head rollback or budget reset; stop on unreconciled local effects. Export saved versions independently and label partial work.

**Still to specify:** the owners and recovery transitions at frozen-request, accepted-reply, committed-tool and graph-checkpoint boundaries, including complete batch progress, context effects, cancellation, waiting and publication reconciliation.

**Design closure:** each boundary in CONTRACTS has a defined re-entry outcome and state owner. No unconditional arbitrary-old-job migration or universal hard-crash guarantee is required.

## Scope of closure

Design closure requires coherent contracts, not proof that software already implements them. Implementation then needs proportional offline checks and source-led verification of an actual requested PDF/complete section. Desktop UI/backend integration and Windows delivery remain known product implementation work, not a fourth unresolved context-architecture question.

Partial-JSON salvage, delta-only summaries, advanced cache tuning, multi-agent/multi-writer branch systems, automatic reminders, universal all-exit packaging and broad provider/network feature expansion are preserved in the reference discussion. They are not first-version prerequisites or an automatic backlog. Reopen only a relevant contract when a demonstrated implementation/delivery blocker or new human requirement warrants it.
