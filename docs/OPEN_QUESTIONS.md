# First-version open questions

The user explicitly stopped incremental design expansion (EVT-1148). EVT-1166 consolidated three unresolved contracts. Preserve the following distinction. The responsibilities and recommended tradeoffs are known. Exact executable schemas and transition semantics still need a coherent specification and implementation. This file does not queue model experiments.

The detailed engineering background is local in [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md) and its linked guides. These open choices are not permission to leave previously discussed mechanisms unexplained or send the next developer back to a conversation archive.

## Q1. Document update and candidate-reference contract

**Observed:** a prior full page-map validation rejection left correct candidate prose available, but later regeneration changed `本文件` to `本文作`. The review identified friction in pure insertion/append and partial-map updates. This supports exact reuse and local correction. It does not prove compaction caused the typo or that previous conversions could never complete.

**Hypothesis/deferred:** automatic salvage of partial JSON may save work, but its complete-delivery benefit is unmeasured and it is not needed to settle this contract.

**Recommended tradeoff:**

- Reuse complete candidates exactly.
- Support insertion/append and metadata patches.
- Preserve untouched content.
- Validate the complete merged result.

Immutable version files own body content. SQLite owns registration/pointers/receipts. Retain malformed originals without requiring automatic salvage.

**Still to specify:** reference identity and applicability, patch/merge semantics, omitted-field behavior, operation success/visibility boundary and the receipt returned on replay.

**Design closure:** the contract can express these actions unambiguously:

1. Fix only page metadata.
2. Insert new content.
3. Reuse a rejected candidate without regenerating unchanged prose.

For each action, identify the original, changed fields, unchanged fields and successful commit boundary.

## Q2. Context capacity and handoff contract

**Observed:** large inspect/OCR results consumed substantial input, and a prior checkpoint reduced input while exact evidence retrieval remained possible. Those scoped results do not establish universal cost benefits or lossless continuation.

**Hypotheses:** draft-heavy history may still exceed capacity after evidence release. Delta summaries may lose active facts when an anchor changes. These are boundary scenarios, not claimed observed app failures.

**Recommended tradeoff:**

- Configure effective route capacity/output reserve.
- Assess the complete assembled request.
- Where useful, release saved unnecessary content before compacting older history.
- Use a self-sufficient continuation handoff.
- Use bounded incremental compaction.
- Preserve originals on failure.

Latest drafts/unfinished candidates may be partially released. Do not freeze a universal recent-turn count or percentage.

**Still to specify:**

- Handling of capacity and unknown estimates.
- Exact history coverage and revision application.
- Summary replacement and rejection behavior.
- The handoff content contract.
- The stop path when no fitting request can be assembled within budget.

**Design closure:**

- Sending, releasing, compacting and stopping each have explicit transitions.
- Unprocessed history survives.
- Failure cannot destroy originals.
- Normal requests respect the configured capacity check.

A universal optimum threshold and guaranteed compaction count are unnecessary.

## Q3. Persistence, recovery and stop contract

**Observed:** earlier saved-work continuation and scoped injected-fault continuation succeeded. These are rationale for durability, not proof of arbitrary crash/natural-outage recovery in the rebuild.

**Hypotheses:** a tool may commit before a graph checkpoint, and replay may occur after head advances. These need finite reconciliation rules rather than a general distributed system.

**Recommended tradeoff:**

- Use one active writer per task.
- Use one authority per request/batch/version/receipt.
- Reuse the frozen input when replaying the same request.
- Finish the accepted batch before another model step.
- Return original receipts without head rollback or budget reset.
- Stop on unreconciled local effects.
- Export saved versions independently.
- Label partial work.

**Still to specify:** the owners and recovery transitions at frozen-request, accepted-reply, committed-tool and graph-checkpoint boundaries. These must cover complete batch progress, context effects, cancellation, waiting and publication reconciliation.

**Design closure:** each boundary in CONTRACTS has a defined re-entry outcome and state owner. No unconditional arbitrary-old-job migration or universal hard-crash guarantee is required.

## Scope of closure

Design closure requires coherent contracts, not proof that software already implements them. Implementation then needs proportional offline checks and source-led verification of an actual requested PDF/complete section. Desktop UI/backend integration and Windows delivery remain known product implementation work, not a fourth unresolved context-architecture question.

The reference discussion preserves these options:

- Partial-JSON salvage.
- Delta-only summaries.
- Advanced cache tuning.
- Multi-agent/multi-writer branch systems.
- Automatic reminders.
- Universal all-exit packaging.
- Broad provider/network feature expansion.

These options are not first-version prerequisites or an automatic backlog. Reopen only a relevant contract when a demonstrated implementation/delivery blocker or new human requirement warrants it.
