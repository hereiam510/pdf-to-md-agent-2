# Proposed changes and reconsideration conditions

This is a retained-options record, not an execution queue. Inclusion establishes neither superiority, adoption nor scheduling. Current rules belong to the [topic designs](INDEX.md#topics); current delivery belongs to [the phase plan](PHASE_PLAN.md). The earlier mixed [options edition](history/discussions/20261031_0157_DESIGN_OPTIONS.md) remains retrievable.

## Find an option

| Unselected direction | Location / trigger |
| --- | --- |
| Langfuse, external export, F03/F04 work | [Observability discussion](discussions/OBSERVABILITY.md); select for a demonstrated missing diagnostic need and settle privacy, deployment and reliability choices first. |
| Diagnostic detail cost and bounds | [Read cost](#diagnostic-detail-read-cost-and-bounds); revisit on measured responsiveness/scale impact. |
| Prepare-only, before-tools gate or multi-dispatch fail-stop controls | [Execution controls](#explicit-request-preparation-and-execution-stop-controls); select only the needed boundary. |
| Evidence retention / pin lifetime | [Retention choices](#evidence-retention-and-pin-lifetime); preserve full source access and explicit agent control. |

Selected streaming method A/SC02, diagnostic typing/DT01, context coordination and bounded accepted-evidence recovery are recorded in their designs and decisions, not left as apparently pending options. This does not select general conflict resolution, broad automatic retry, telemetry integration or live Nursing continuation.

## Diagnostic detail read cost and bounds

The accepted D03 review leaves this performance option deferred. The then-selected [zero-dispatch Nursing preparation](history/discussions/20261031_0157_STAGE_B_CONVERSION.md#baseline-and-zero-dispatch-preparation-selected-2026-10-30) does not select profiling or a read-budget redesign.

**Unselected improvement candidate, 2026-10-29.** The F02 post-implementation review observed that request details scan all task operations and may repeatedly load the same accepted object while matching calls; linked evidence can also be fully read for integrity checks before the user opens its body. `Diagnostics.read` uses a SQLite progress handler, which bounds SQL execution rather than all Python/object I/O while the service lock is held. This is a source-supported cost/boundary concern; no new large-catalog latency, memory or whole-task measurement establishes its magnitude. It is separate from F04's existing stopped-poll graph snapshot behavior.

If a selected detail proves slow/busy or profiling shows repeated work matters, compare filtering candidate identities before reads, reusing provenance/integrity results within one inspection, lazy body access with honest verification labels, and explicit scope-aware read budgets. Preserve full access and do not silently replace full with index or truncate evidence. No persistent cache/schema or arbitrary wall-time threshold is selected. Small reuse naturally needed by the F02-D01 shared checker may be appropriate, but the selected D01/D02 correction does not require a general optimization or benchmark. Revisit on material responsiveness evidence or a separately chosen read-boundary assessment; defer otherwise.


## Explicit request preparation and execution stop controls

On 2026-10-30 the human selected the existing baseline/zero-dispatch preparation stage for a future execution prompt after D03 review. This selects use of existing controls, not implementation of the interface alternatives below; [Stage B](history/discussions/20261031_0157_STAGE_B_CONVERSION.md#baseline-and-zero-dispatch-preparation-selected-2026-10-30) owns current scope and stops.

Recorded 2026-10-29 after the human accepted the Nursing planning review and asked to retain the design consideration. **Disposition:** retain for later selection; no interface or controller implementation selected. The [current decision](decisions/NURSING.md#staged-nursing-continuation-and-control-interface-deferral-2026-10-29) uses existing exact recovery plus the cumulative request guard for one bounded preparation. [Stage B](history/discussions/20261031_0157_STAGE_B_CONVERSION.md#nursing-planning-reviewed-and-staged-direction-agreed-2026-10-29) owns that operational sequence and its unexecuted status.

**Need and evidence.** Start currently prepares and freezes before the send budget check. Setting the total request allowance equal to consumed attempts can prevent dispatch, but still requires the ordinary credential path and writes recovery/settings/graph/time records. It communicates the pause as budget exhaustion, not an explicit prepared-for-review state. A one-dispatch allowance also allows the accepted response's tools, while multi-dispatch allowances permit existing response repairs. Source and existing tests support these distinctions; they do not establish how frequently users need an alternative or prove a live Nursing failure caused by the interface.

| Candidate | Potential benefit and tradeoff | Revisit condition |
| --- | --- | --- |
| Dedicated prepare-only action/API | Make preparation, its writes and an explicit no-dispatch result understandable without using a resource limit as the pause mechanism. Could separate preparation from credential acquisition. Requires a defined durable lifecycle, duplicate/stale handling, graph recovery and a separate send action; it is not a read-only preview. | Repeated request-preview/preparation needs, confusing budget-stop UX, or a selected credential-free preparation requirement. |
| Before-tools gate after complete acceptance | Support explicit inspection before any newly authorized tool effect while retaining the full accepted batch. Adds a resumable execution boundary, stale-instruction/head handling and user friction; it must not turn partial replies into executable calls. | The human selects pre-tool review for a concrete need; current first-live direction instead permits the complete accepted reply's autonomous tools. |
| Scoped multi-dispatch fail-stop policy | Stop at the selected failure/repair boundary before another dispatch, independent of operator polling, while allowing normal autonomous work. Requires precise failure classes, persisted policy/scope, interaction with repairs and clear continuation semantics. | A selected multi-dispatch run requires immediate exits that the existing automatic repair behavior cannot guarantee. No semantic fidelity detector is implied. |

Select only the control needed by the user outcome; these are independent options, not a bundled controller redesign. Prefer reusing current preparation, frozen identity, acceptance, tool receipts and graph responsibilities. A limited gate may be preferable to a general scheduler; continued use of current budgets remains reasonable for occasional bounded checks. Do not make routine per-request approval the product workflow or make these options prerequisites for the current zero-dispatch preparation.

If selected later, derive acceptance from the chosen boundary: no dispatch for prepare-only; no new tool effect for a pre-tools stop; no next dispatch after a selected fail-stop event. Include actual API/UI, stale/duplicate action, interruption/reopen and later authorized continuation. Preserve frozen bytes, source access, accepted evidence, committed effects, useful candidates/versions, user instructions and known/unknown consumption without resets, force acceptance or replay. Current task allowances and frozen route settings must remain distinct. Record whether a successful local boundary test, live request and complete source-led delivery were each achieved; one does not imply the others.


## Evidence retention and pin lifetime

Recorded 2026-10-24, Asia/Hong_Kong, at the user's request following a discussion of raw-stream pins and context capacity. The user wanted these alternatives preserved for later assessment, not implemented in this documentation update.

### Existing basis and evaluation question

The [Phase 3 closeout](history/IMPLEMENTATION_HISTORY.md#phase-3-closeout-stencil-appearance-and-pin-admission) already implements explicit pin representations and capacity admission before policy application. A rejected update preserves the prior working policy. Original evidence remains accessible through full/raw/field/range reads and native images. See [the context contract](design/CONTEXT_MANAGEMENT.md#q2-context-transitions) for exact behavior, replay boundaries and estimator limitations.

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

**Disposition:** Adopted for the 2026-10-25 history-pressure coordination increment after dual-protocol local reproductions. Exact behavior is owned by [Q2](design/CONTEXT_MANAGEMENT.md#q2-context-transitions), the decision by [DECISIONS](decisions/REBUILD.md#consequential-alternatives-and-corrections), and implementation/checks by [CURRENT_STATE](CURRENT_STATE.md). This adoption includes notes and release updates, not only pins. Other options on this page remain unselected.

If a proposed pin could fit after removable history is compacted, the agent could retain the proposal, compact appropriate history, and reassess it against the resulting input. If required instructions plus the selected pins and request overhead already exceed capacity, compacting unrelated history cannot solve the problem. The actual compaction envelope must also fit; a hypothetical small final context does not prove a feasible compaction path.

**Potential value and tradeoff:** A useful pin might become admissible without changing its representation. Compaction adds work and can lose useful semantic detail despite preserving raw history. Coordination must also avoid repeatedly retrying an infeasible proposal or applying a blocked policy before a usable next input exists. Existing atomic rejection and working-policy preservation should remain intact.

**Revisit when:** A concrete task or proportionate local analysis shows rejection caused by reducible history, a feasible compaction path, and a useful evidence selection that existing agent-controlled choices handle awkwardly. Do not infer this need from a raw pin that cannot fit even with minimal history.

**Proportionate evaluation:** Use fitting-after-compaction and irreducibly-oversized controls. Check that the former can progress, the latter receives actionable feedback, and both preserve originals, prior policy on rejection, consumed usage and frozen-request boundaries. Inspect retained instructions and dependencies as well as source-led saved/reopened/exported output. Selected coordination may invoke existing bounded compaction under the active policy; it does not select automatic release, lower fidelity or a narrower conversion scope.

### Current disposition

Keep explicit representations and admission-before-application as the basis. The selected history-pressure coordination is tracked by its contract and current-state record. Ordinary reads remain available, and expiry remains unselected; recording these options does not introduce a more complex pin manager. The agent continues to choose evidence and methods. [CURRENT_STATE](CURRENT_STATE.md) records the next action and existing verification limits; current user instructions authorize work.
