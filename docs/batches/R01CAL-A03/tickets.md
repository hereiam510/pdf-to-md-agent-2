# R01CAL-A03 local tickets

[Spec and authority](spec.md#status-and-authority) · [Acceptance](spec.md#acceptance-and-context-coverage) · [Verification](verification.md) · [Project ticket policy](../../../AGENTS.md#batch-documents-and-ticket-mode)

## Authority and responsibility

The user's earlier instructions selected this local plan, T1 checks, T2 preparation and the single T3 interval separately. The latest 2026-11-08 instruction selects **A03-T4 only**: source-led review, actual same-version app reopen/export without inference, integrated A1–A8 assessment and records, then stop. The [spec's authority](spec.md#status-and-authority) governs this review; T3's [single interval](spec.md#selected-configuration-and-finite-interval) stays closed. No repair or additional run is selected.

The main agent owns all four tickets and writes their records sequentially. No subagents or GitHub Issues are assigned. This file owns task content, dependencies and progress; [verification](verification.md) owns the transition decision, observed checks and combined verdict. Source/build changes require affected bindings to be checked again, not historical results to be rewritten. Original Task A, prepared Task B and useful artifacts remain preserved.

## Dependency and execution overview

| Ticket | Verifiable contribution | Dependencies |
| --- | --- | --- |
| [R01CAL-A03-T1](#r01cal-a03-t1) | Decide whether the fresh conversion remains valid and useful after A02. | [A02-T3](../R01CAL-A02/tickets.md#r01cal-a02-t3) evidence/review, including explicit blockers or unperformed coverage. |
| [R01CAL-A03-T2](#r01cal-a03-t2) | Bind the source and prepare an isolated fresh task with verified controls. | T1 eligibility at the [reassessed startup/source binding](verification.md#offline-preview-startup-check-and-t1-reassessment-2026-11-07), selected preparation and current source/build assumptions. A completed review alone does not establish eligibility or select preparation. |
| [R01CAL-A03-T3](#r01cal-a03-t3) | Observe the single finite conversion and natural context accumulation. | T2 operational readiness, still-valid T1 decision and actual execution authority. |
| [R01CAL-A03-T4](#r01cal-a03-t4) | Review full source fidelity, actual reopen/export and all acceptance. | T1–T3 records, with actual outputs where available or explicit blockers. |

T1 can finish with an eligible, blocked or deferred decision; only eligibility releases T2's dependency. T4 can account for a blocked/unperformed run without claiming unavailable product checks passed. Planning all contributions now does not require a successful A02 result, authorize execution or assume a future repair. Independent work may continue only within its selected scope.

## R01CAL-A03-T1

**Owner/state:** main agent; original review and the subsequently selected offline prerequisite/reassessment complete, 2026-11-07. [Current decision and tested binding](verification.md#offline-preview-startup-check-and-t1-reassessment-2026-11-07) own eligibility; the [original decision](verification.md#t1-transition-decision-2026-11-07) remains preserved. Reassess this same ticket on a relevant source/build/startup or evidence change. Subsequent preparation is owned by [T2](#r01cal-a03-t2), rather than this transition ticket.

**Contribution:** apply [A1](spec.md#a1) and establish a defensible basis for [A8](spec.md#a8) through the spec's [transition contract](spec.md#transition-from-r01cal-a02).

**Prerequisites:** A02's review accounts for both cases, or identifies missing/invalid evidence and the affected conclusions. Do not replace missing observations with expected outcomes.

**Work and checks:**

- Link the first-stage observations and classify their implications: autonomous correction, trustworthy partial/failed behavior, a concrete invalidating defect, or missing/unknown evidence. An ordinary recovered validation error is not automatically a blocker; an unexplained partial result is not a demonstrated software defect.
- Record eligibility and the unresolved workflow question the fresh conversion would answer. For a blocker or deferral, identify the exact affected guarantee, necessary evidence/remedy and revisit condition. Leave unrelated findings outside the dependency chain.
- Apply [finding and dependency handling](#handling-findings-and-dependency-changes) when a concrete problem changes the plan. Identify any relevant source/build difference and the preparation checks it invalidates. Keep the decision and rationale in A03 verification, linking A02 evidence instead of copying its verdict.

**Finish:** an attributable transition decision, rationale and affected dependencies are recorded. An eligible decision remains subject to T2 readiness and execution scope; a blocked/deferred decision completes the review contribution while holding downstream work. Reassess this same stable ticket's decision after a relevant repair or evidence change, retaining earlier decisions and identities.

## R01CAL-A03-T2

**Owner/state:** main agent; selected offline preparation complete, 2026-11-07, stopped before Start. [Preparation evidence, actual bindings and limits](verification.md#t2-offline-fresh-task-preparation-2026-11-07) own readiness; [T1's decision and tested binding](verification.md#offline-preview-startup-check-and-t1-reassessment-2026-11-07) remain the transition basis. Recheck affected identities/state and activate monitoring before any later selected T3 Start; no live execution is selected here.

**Contribution:** bind [A1](spec.md#a1) and establish the operational prerequisites of [A6](spec.md#a6)/[A7](spec.md#a7), following the spec's [source and fresh-task conditions](spec.md#source-scope-and-fresh-task-conditions).

**Prerequisites:** current eligible transition, selected preparation and no unresolved material source/metering/control conflict. Reconcile [T1's reassessment](verification.md#offline-preview-startup-check-and-t1-reassessment-2026-11-07) with the intended startup/source/build; reuse its verified binding while valid and recheck only relevant changes. Do not infer general preparation readiness from the isolated synthetic preview control or create a conversion task outside the selected scope. A repair that changes relevant behavior requires rebinding and proportionate verification before Start.

**Work and checks:**

- Verify actual source availability/hash and the complete requested section/boundaries against the maintained identity. Prepare a fresh isolated task with no prior requests, attempts, versions, conversion content or delivery state. Preserve originals; keep prior answers, transcripts, stage-one calls and reviewer material outside agent access.
- Bind actual source/build/lockfile/task/configuration identities to the selected baseline and the separate [finite interval](spec.md#selected-configuration-and-finite-interval). Verify effective mapping, limits, normal credential-loading path and metering basis without exposing secrets, reading historical authentication logs or making provider probes.
- Verify supported import/settings/Start/observe/Stop controls and the exact-version read, actual app reopen and export paths offline. Establish unique short runtime/output locations under the [storage policy](../../ARTIFACT_STORAGE.md#ownership-and-locations). Any allowed development build must retain the previous build; this task adds no dependencies, installer or global-setting changes.
- Record readiness and the monitoring/evidence procedure. No offline setup step starts a model request. Resolve a material conflict through the agreed scope before dependent execution; do not silently substitute a source, model, setting or delivery check.

**Finish:** the fresh task and operational controls are attributable and ready, or the exact missing prerequisite is recorded. Availability of a helper/API alone does not verify actual app reopening or delivery. T3 needs current operational readiness, not merely completion of preparation bookkeeping.

## R01CAL-A03-T3

**Owner/state:** main agent; selected single-interval execution and records complete, 2026-11-08. [Execution, terminal claim and preserved evidence](verification.md#t3-single-finite-conversion-2026-11-08) own observations and limits. T3 ended before T4; its interval remains closed, without Continue, rerun or additional allowance.

**Contribution:** observe natural accumulated-context behavior and autonomous finite execution for [A5](spec.md#a5)/[A6](spec.md#a6), preserving evidence for the remaining acceptance.

**Prerequisites:** T1 eligibility and T2 identities remain valid; actual live execution is selected. The spec's single interval and no-replay/no-rerun rules apply without pooled or reset allowances.

**Work and checks:**

- Start the fresh task once with the specified source/outcome and ordinary agent guidance. Let the agent select full/raw/field/range/native-pixel reads and reconstruction methods. Supply no prepared transcription, matching-range answer, prior solution, forced compaction, artificial padding, tool quota or mid-run completion coaching.
- Monitor the agreed send/attempt/time and terminal/Stop conditions. Preserve all native responses, frozen inputs, feedback, candidate/version identities, selected deliverable, usage unknowns, interventions and stop tails. Terminal partial/waiting is an outcome, not an invitation to Continue.
- Capture actual history evolution and any naturally occurring pressure or compaction without forcing a minimum amount of context. Preserve source reads, images, pending-work evidence and retrievable originals. Keep all private/full records outside versioned files.
- Leave the agent result intact for review. Record an invalidating fault and any unperformed coverage; no developer assembly or post-run correction is counted as agent completion.

**Finish:** the declared interval is fully accounted for, including its terminal result or explicit inability to start, with attributable evidence and original partial artifacts. A finite failed attempt can complete this execution contribution without passing conversion acceptance. No extra attempt follows automatically.

## R01CAL-A03-T4

**Owner/state:** main agent; selected review and records complete, 2026-11-08. [T4 source/delivery evidence and A1–A8 assessment](verification.md#t4-source-led-review-and-same-version-delivery-2026-11-08) own observations and the combined verdict. Actual app close/reopen and same-version export were performed without inference. Stop at the [supported next-action boundary](verification.md#t4-combined-verdict-and-supported-next-action); no remedy or another run begins.

**Contribution:** integrate [A1](spec.md#a1), [A2](spec.md#a2), [A3](spec.md#a3), [A4](spec.md#a4), [A5](spec.md#a5), [A6](spec.md#a6), [A7](spec.md#a7) and [A8](spec.md#a8) against the actual source and selected saved version.

**Prerequisites:** available source/run/output identities and the transition/preparation records. If a run or deliverable is absent, assess the available evidence and mark dependent checks unverified; do not create an output to fill the gap.

**Work and checks:**

- Review every scoped source page/region against the agent-selected immutable version for text, numbers, symbols, source language, ordering, meaningful structure and omissions. Check the whole physical-page map, printed/physical boundaries, notes/provenance and final report/claim agreement. Keep reviewer transcriptions separate from the agent task.
- Inspect applicable independent image units, native pixels/retained original bytes, adjacent text and source/page/region provenance. Record absent source categories and uncertainty rather than claiming unsupported figure coverage.
- Actually close/reopen the selected version in the app without Continue or inference, then export that same version to a supported short path. Inspect displayed/rendered text and images, actual ZIP members/bytes, relative links and applicable originals. Record request counts before/after; exact API reads alone cannot satisfy actual reopen. Unavailable downstream checks remain unverified.
- Trace real context evolution, retained/retrievable requirements and pending work, and any compaction that actually occurred. Separate successful conversion with little history from pressure/compaction coverage. Reconcile autonomy, limits, assistance and usage unknowns.
- Write criterion-level and combined verdicts in verification, distinguishing conversion, context coverage and delivery. Compare attributable differences with A02/historical Task A without claiming context causality or general reliability. Record supported findings and scoped next actions; update phase/work selection only if their distinct facts change.

**Finish:** every criterion is assessed against observed evidence or explicitly unavailable coverage, with preserved failures and a supported recommendation. Review completion is separate from product acceptance. The original Task A verdict and the unused prepared Task B remain unchanged; no remediation, calibration or further run begins from this closeout alone.

## Handling findings and dependency changes

This procedure implements the [transition contract](spec.md#transition-from-r01cal-a02) and the [ticket-planning discussion](../../discussions/REQUEST_CAPACITY.md#ticket-planning-and-discovered-fixes-2026-11-07). It allocates no speculative repair ticket or additional execution authority.

1. Record the observed condition, identities, original failure, consumed allowance, useful artifacts and uncertainty in the responsible batch's verification. Distinguish corrected validation feedback, behavioral failure and a demonstrated defect before choosing a remedy.
2. Identify the affected guarantee and downstream ticket. Add a specific dependency only when the finding invalidates that work; record non-blocking findings and revisit conditions without holding unrelated authorized work.
3. Define an evidence-supported investigation/repair and verification contribution when needed. Preserve existing ticket IDs and content. Production repair is excluded by the experiment specs and requires selected repair scope or an explicit amendment; a distinct remedy may use its own small batch linked here. A correction within already-authorized preparation can stay in that ticket if it preserves the agreement. Current ticket creation does not delegate broader repair authority.
4. Verify the selected remedy at its actual source/build identity and reassess T1. Recheck only affected preparation bindings and assumptions before releasing dependent work. Preserve prior decisions/results at their original identities; a fixed build never retroactively passes an earlier run.
5. Keep original budgets and outcomes intact. Additional live confirmation or a repeated case needs its own selected finite allowance; a repair does not reset, transfer or silently enlarge the existing allocation. Record any remaining limitation in the final review.
