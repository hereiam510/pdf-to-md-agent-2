# First-version open questions

The user explicitly stopped incremental design expansion (EVT-1148). EVT-1166 consolidated three contracts. Authorized implementation on 2026-10-23 selected their executable schemas and transitions in [CONTRACTS](CONTRACTS.md#implemented-first-version-contracts). Q1–Q3 are now closed as design choices. Implementation, live source fidelity and distribution readiness still require distinct evidence; [CURRENT_STATE](CURRENT_STATE.md) records that evidence. This file does not queue additional model experiments.

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

**Implemented selection:** task-owned immutable candidate references with JSON Pointers; ordinary edits requiring matching base/expected head and explicit autonomous reconstruction from a different base; sequential insert/replace (including local candidate content)/delete/exact code-point patches; supplied-field-only page merges; immutable version files with atomic registration/head/receipt; desktop edit sessions bound to loaded versions. Rejected-candidate reuse, insertion, metadata patches, stale-head rejection, deliberate rebuild and historical receipt replay are covered by offline tests. [Q1](CONTRACTS.md#q1-document-schema-and-commit) owns the exact updated contract.

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

**Implemented selection:**

- A complete-input UTF-8 byte heuristic with explicit output and image allowances; unknown image cost blocks sending.
- Capacity admission defers an individually unfit body through an explicit exact-reference receipt. Individually fitting bodies remain selected under aggregate pressure, which proceeds to compaction. Full originals and unrestricted full/raw/field/range reads remain available.
- Pinned objects hydrate independently of their original history prefix; native images are pinned by image reference. Genuine oversized required pins stop explicitly without silent release.
- Oldest fitting complete history batches, exact request coverage and a revision precondition.
- Six-field self-sufficient handoff, applied only when the entire assembled input decreases; uncovered history survives.
- Original retention on any rejection, and finite `capacity_blocked`/budget stop paths.

These transitions pass offline boundary checks. Those checks do not prove the quality of arbitrary model summaries or equal-quality cost savings.

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

**Implemented selection:** one executor lock, external immutable originals, SQLite request/attempt/effect records, and compact LangGraph checkpoints. Re-entry reconciles accepted-reply and tool-result objects, reuses committed document receipts, and settles the pending batch before another model request. New user amendments preserve completed effects and settle unstarted old calls as unexecuted. Explicit Continue after an HTTP/rejected response records a distinct request transition; unknown remote outcomes retain their frozen ID and replay gate. Limits persist across resume. Unknown OCR/script effects stop. Explicit-version export is independent. [Q3](CONTRACTS.md#q3-execution-recovery-and-delivery) owns exact entry/receipt behavior. Offline fault tests cover the selected gaps; they are not a guarantee for every hard crash or remote outcome.

**Design closure:** each boundary in CONTRACTS has a defined re-entry outcome and state owner. No unconditional arbitrary-old-job migration or universal hard-crash guarantee is required.

## Scope of closure

No unresolved first-version architecture choice currently blocks the implemented path. Desktop/backend integration and Windows folder delivery have been exercised with a local fixture. The user has authorized source-led Nexus verification using copied references and the private credential. Its observed result and any actual blocker belong in CURRENT_STATE; a hypothetical all-provider or whole-book issue does not reopen the design.

The reference discussion preserves these options:

- Partial-JSON salvage.
- Delta-only summaries.
- Advanced cache tuning.
- Multi-agent/multi-writer branch systems.
- Automatic reminders.
- Universal all-exit packaging.
- Broad provider/network feature expansion.

These options are not first-version prerequisites or an automatic backlog. Reopen only a relevant contract when a demonstrated implementation/delivery blocker or new human requirement warrants it.
