# Design options

This document retains candidate approaches for later evaluation. Inclusion does not establish a defect, prove an improvement, select work, or authorize implementation or experiments. These options are not delivery prerequisites or an implementation queue. Effective behavior belongs to [CONTRACTS](CONTRACTS.md); implementation and verification status belong to [CURRENT_STATE](CURRENT_STATE.md); adopted consequential choices belong to [DECISIONS](DECISIONS.md).

Record evidence status separately from adoption status. An adopted option is not thereby implemented or verified. Revisit an option when its stated conditions become relevant, rather than automatically scheduling every entry. If an option is selected, superseded or rejected, update its disposition and link to the applicable decision and contract instead of maintaining a second progress ledger here.

## Context coordination policy and responsibility choices

Updated 2026-10-26, Asia/Hong_Kong (UTC+08:00). The [discussion record](discussions/CONTEXT_COORDINATION.md#alternatives-and-current-disposition) owns the comparisons and revisions. The user selected whole-batch admission, no automatic partial context application, explicit agent reselection of uncommitted intent after new instructions, and B for confirmed necessary-content excess; [DECISIONS](DECISIONS.md#context-coordination-design-recording-boundary) records adoption. The [target design](design/CONTEXT_UPDATE_COORDINATION.md) integrates these policies, request/decision responsibilities and planned acceptance. It is now implemented; CURRENT_STATE owns the local checks and remaining real-model limits. This options record does not authorize another increment.

The former immediate/deferred route remains a meaningful unselected alternative, particularly for early commitment before cancellation. It could defer intermediate X+Y and compose release X; this alone does not provide the selected whole-revision promise when earlier changes already fit. Neither moving admission nor extracting a helper fixes the three retained estimation/projection controls automatically. The user rejected automatic partial application for this target; a generic rule to borrow every shorter pending pin/note remains unselected. Whole-old-policy snapshot import and a user keep-pending switch are not required by explicit agent content reuse. The former C recommendation would retain automatic eligibility for an already feasible candidate after a settings reduction when the active diagnostic route was blocked. That is a coherent alternative tradeoff, not an established logical contradiction, but it is not the selected policy. B favors a durable disposition independent of notification availability; restoration after that disposition requires explicit agent reselection. Unknown estimates and pure history pressure retain their separate treatment. Existing pin-lifetime options below retain their separate status.

## Evidence retention and pin lifetime

Recorded 2026-10-24, Asia/Hong_Kong, at the user's request following a discussion of raw-stream pins and context capacity. The user wanted these alternatives preserved for later assessment, not implemented in this documentation update.

### Existing basis and evaluation question

The [Phase 3 closeout](CURRENT_STATE.md#phase-3-closeout-stencil-appearance-and-pin-admission) already implements explicit pin representations and capacity admission before policy application. A rejected update preserves the prior working policy. Original evidence remains accessible through full/raw/field/range reads and native images. See [the context contract](CONTRACTS.md#q2-context-transitions) for exact behavior, replay boundaries and estimator limitations.

Retaining an original reference, repeatedly presenting native pixels, and injecting raw Base64 bytes have different purposes and context costs. Original retention does not itself require repeated injection. Existing ordinary reads, explicit release, pin representations and history compaction may already meet a task's needs.

The unresolved question is which further usage guidance or lifecycle choices would help agents complete faithful conversions with less unnecessary intervention. The later local reproductions and explicit authorization selected history-pressure coordination below. They do not establish live-model frequency, natural adoption, conversion-quality gains or measured cost savings. No model trial or other implementation is selected by this options record.

### Read without creating a long-lived pin

**Disposition:** An available usage strategy to assess when relevant; not a new feature request or compulsory workflow.

An agent that needs evidence for one decision can read it without adding a persistent pin, then save useful conclusions with precise source references. Ordinary read results can remain in history; absence of a pin does not mean immediate eviction or a smaller next request. Saved conclusions do not replace the full original or establish coverage by themselves.

**Potential value and tradeoff:** Avoid retaining evidence beyond its useful working period, while allowing later retrieval. Repeated reads may instead increase cost or omit a dependency from the immediate working context. The agent must remain free to pin evidence it needs repeatedly.

**Revisit when:** Task analysis or observed runs suggest that long-lived pins are used for one-off inspections and existing read/release choices are poorly understood or inconvenient. Check existing tool guidance before proposing a new mechanism.

**Proportionate evaluation:** Inspect actual assembled inputs and retrieval behavior rather than assuming reads disappear. On a relevant conversion, compare source-led saved, reopened and exported results, preservation of unresolved dependencies, and any additional retrieval or user intervention. Check that originals and precise access remain available. Cost claims require whole-task usage and applicable pricing, not just shorter input text.

### Agent-selected lifetime or release condition

**Disposition:** Unselected mechanism; automatic expiry is not part of the current pin contract.

An agent could explicitly request a retention period or release condition, such as presenting evidence to the next model invocation only. This could reduce forgotten pins. It must not silently impose expiry on existing pins or decide which evidence is semantically expendable.

**Potential value and tradeoff:** Less manual release bookkeeping, balanced against premature removal, repeated retrieval and additional durable state. A phrase such as "next invocation" is incomplete without specifying whether a failed send, retry, frozen-request replay or successful response consumes the lifetime. Those semantics would need definition if this option is selected; no particular implementation is prescribed here.

**Revisit when:** Repeated unnecessary retention remains a meaningful obstacle after explicit representations, ordinary reads and explicit release have been assessed, or a concrete task demonstrates a useful bounded lifetime.

**Proportionate evaluation:** First define observable expiry behavior. Then exercise successful and failed calls, retries, replay and reopening under that definition. Verify that recorded pin choices and complete originals survive correctly, that required evidence is available when needed, and that source-led delivery and agent choice are preserved. Fewer active pins alone is not evidence of better conversion.

### Compact other history before admitting a pin

**Disposition:** Adopted for the 2026-10-25 history-pressure coordination increment after dual-protocol local reproductions. Exact behavior is owned by [Q2](CONTRACTS.md#q2-context-transitions), the decision by [DECISIONS](DECISIONS.md#consequential-alternatives-and-corrections), and implementation/checks by [CURRENT_STATE](CURRENT_STATE.md). This adoption includes notes and release updates, not only pins. Other options on this page remain unselected.

If a proposed pin could fit after removable history is compacted, the agent could retain the proposal, compact appropriate history, and reassess it against the resulting input. If required instructions plus the selected pins and request overhead already exceed capacity, compacting unrelated history cannot solve the problem. The actual compaction envelope must also fit; a hypothetical small final context does not prove a feasible compaction path.

**Potential value and tradeoff:** A useful pin might become admissible without changing its representation. Compaction adds work and can lose useful semantic detail despite preserving raw history. Coordination must also avoid repeatedly retrying an infeasible proposal or applying a blocked policy before a usable next input exists. Existing atomic rejection and working-policy preservation should remain intact.

**Revisit when:** A concrete task or proportionate local analysis shows rejection caused by reducible history, a feasible compaction path, and a useful evidence selection that existing agent-controlled choices handle awkwardly. Do not infer this need from a raw pin that cannot fit even with minimal history.

**Proportionate evaluation:** Use fitting-after-compaction and irreducibly-oversized controls. Check that the former can progress, the latter receives actionable feedback, and both preserve originals, prior policy on rejection, consumed usage and frozen-request boundaries. Inspect retained instructions and dependencies as well as source-led saved/reopened/exported output. Selected coordination may invoke existing bounded compaction under the active policy; it does not select automatic release, lower fidelity or a narrower conversion scope.

### Current disposition

Keep explicit representations and admission-before-application as the basis. The selected history-pressure coordination is tracked by its contract and current-state record. Ordinary reads remain available, and expiry remains unselected; recording these options does not introduce a more complex pin manager. The agent continues to choose evidence and methods. [CURRENT_STATE](CURRENT_STATE.md) records the next action and existing verification limits; current user instructions authorize work.
