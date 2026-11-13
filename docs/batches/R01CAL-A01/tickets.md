# R01CAL-A01 local tickets

[Spec and authority](spec.md#authority-and-stopping-point) · [Planned acceptance](spec.md#planned-diagnosis-acceptance) · [Verification](verification.md#diagnosis-acceptance) · [Project ticket policy](../../../AGENTS.md#batch-documents-and-ticket-mode)

## Authority, responsibility and shared ownership

The user selected local ticket preparation on 2026-11-07, Asia/Singapore, with an explicit stop after planning and no investigation or implementation. That request established this plan without starting execution. All three tickets are owned by the main agent; no subagents or GitHub Issues are selected. Actual results and combined diagnosis acceptance belong in verification, not this plan.

The subsequent T1-only instruction superseded the earlier planning stop for T1; its [execution evidence](verification.md#t1-historical-evidence-and-visibility-2026-11-07) records safe access and historical observations. The next instruction selected T2 only, preserving the same checkout, inherited work and spec exclusions. The latest instruction selects **T3 only**: integrated assessment, scoped documentary/diagnostic correction and recommendation. The [spec authority](spec.md#authority-and-stopping-point) retains those boundaries; no remedy or follow-up execution is selected.

The [spec's input and execution boundary](spec.md#diagnosis-boundary-and-inputs) applies to every ticket. Product code, tool guidance, Task A/B originals and historical delivery artifacts remain unchanged. Future diagnosis may read the scoped source/evidence and use isolated synthetic checks only within the later execution instruction. Developer helpers and generated evidence use a fresh short ignored run directory under the [storage policy](../../ARTIFACT_STORAGE.md#ownership-and-locations); a maintained regression test requires the applicable later scope and [canonical test location](../../guides/PROJECT_LAYOUT.md#tests-and-fixtures). Ticket planning creates no helpers, fixtures, stores or test results.

The main agent is the single writer for this batch's tickets/verification and necessary topic records. Later work records each observed command/case, source/input identity, outcome, evidence location and limitation in verification as it develops. Preserve failures and partial results. An application defect discovered by a diagnostic check is evidence for this batch, not permission to fix production code or change the spec's guarantees.

## Dependency and execution overview

| Ticket and execution owner | Verifiable contribution | Dependencies |
| --- | --- | --- |
| [R01CAL-A01-T1](#r01cal-a01-t1) | Establish the historical sequence, evidence availability and actual agent-visible inputs. | A later instruction starting diagnosis; current spec and preserved entry state. |
| [R01CAL-A01-T2](#r01cal-a01-t2) | Assess current editing capability and scale through source tracing and synthetic controls. | T1's reconciled source basis and safe access/write boundaries; complete historical artifact availability is not required for independent synthetic work. |
| [R01CAL-A01-T3](#r01cal-a01-t3) | Integrate evidence, assess whole-spec coverage and recommend the next action. | T1/T2 observations or explicit blockers; completed diagnosis cannot be inferred from incomplete required checks. |

Execution is sequential under one owner because the tickets share the evidence basis and verification file. There is no technical need to finish all historical reads before independent T2 checks once the safe baseline is established. Missing inputs affect only the dependent conclusions: retain the limitation, continue independent in-scope work, and carry unresolved required coverage to T3. Material scope changes or actions excluded by the spec need a later decision; this plan introduces no routine per-check approval gate.

## R01CAL-A01-T1

**Contribution:** establish what happened and what information reached the agent, without substituting current descriptions for the recorded input. Addresses [DQ2](spec.md#dq2), the historical portion of [A1](spec.md#a1), [A5](spec.md#a5), and preservation under [A6](spec.md#a6).

**Prerequisites:** diagnosis execution is subsequently selected; reconcile actual Git state and inherited work, then identify the exact Task A references from the [maintained evidence owner](../../verification/20261106_1408_R01CAL_TASK_A.md#identities-and-preserved-conditions). Establish a non-writing original-data access path and isolated output location before using any application helper. Do not infer that a documented private path still exists.

**Work and ownership:**

- Record the applicable spec/source identity, original/copy/synthetic boundaries and which evidence is available. Read only the task-specific non-secret records allowed by the spec. Verify potentially mutating initialization is absent before touching an original store.
- Map the failed complete claim, subsequent saves, rejection/repair information, relevant frozen inputs and final report to request/call/version identities. Distinguish what was retained, returned and included in the agent's next input. Identify scope instructions and schema/feedback visibility with exact evidence locators.
- Record any unavailable artifact or non-exact reconstruction, the conclusions it prevents, and the smallest missing fact. Preserve original evidence and check inspected originals for change. Place necessary, non-secret explanation and the sequence map in verification; private extracts and full logs stay in the isolated run directory.

**Finish and checks:** provide attributable historical observations and an agent-input visibility account against the linked criteria, with availability and access limits. A source-code description alone cannot satisfy a historical visibility claim. If original evidence is unavailable, record T1's affected portion as partial/blocked; this does not prevent T2's independent synthetic capability work. No model-understanding or causal conclusion is required to complete the available evidence mapping.

**Owner:** main agent. **State:** complete under the T1-only instruction; [historical mapping, visibility and preservation evidence](verification.md#t1-historical-evidence-and-visibility-2026-11-07). This does not accept the whole diagnosis or start T2/T3.

## R01CAL-A01-T2

**Contribution:** distinguish an absent or failing mechanism from a supported but difficult representation, and measure only the relevant scale/feedback obstacle. Addresses [DQ1](spec.md#dq1), [DQ3](spec.md#dq3), the current-source portion of [A1](spec.md#a1), [A2](spec.md#a2), [A3](spec.md#a3), [A4](spec.md#a4), and synthetic isolation under [A6](spec.md#a6).

**Prerequisites:** T1 has established the source identity and safe access/write boundaries. Use the existing pinned environment and a fresh isolated synthetic workspace. Resolve the applicable production interface from the source; no assumed range API, new dependency or production change is part of the ticket. Historical evidence gaps remain explicit when comparing current behavior to Task A.

**Work and ownership:**

- Trace only the relevant schema, page-map creation/merge/validation, edit argument exposure, rejection projection and subsequent-input path using the [module/test map](../../guides/PROJECT_LAYOUT.md#engine-module-lookup). Identify material historical/current differences; do not treat current assembly as an exact old payload.
- Use existing production interfaces and synthetic content to run the large-complement/small-control cases and guard cases defined in A2/A3. Capture the actual resulting map, validation outcome, head and candidate retention, and any barrier. The spec owns the case conditions and expected guarantees; do not relax them to obtain a passing result.
- Apply A4 to a successful synthetic metadata-only save, including preservation of exact content/assets and comparison through a fresh reader and synthetic export. Keep unsuccessful paths and state which downstream checks were not exercised.
- If scale or capacity is implicated, record the actual serialized representation and units/limits needed for DQ3, without running a calibration study or inferring tokens or causation from character counts. Record relevant guidance/projection observations for T3 alongside T1's historical visibility evidence.

**Finish and checks:** provide source-linked mechanism findings and reproducible synthetic observations for the linked criteria, including discrepancies and unavailable coverage. A supported mechanism failure is a valid diagnostic result; do not implement a fix, repeat checks without a discriminating reason, or claim synthetic success establishes natural agent completion. Keep original Task A data and delivery unchanged; helpers must not dispatch to a model or controller. If the environment prevents required checks, record the specific prerequisite and partial scope for T3.

**Owner:** main agent. **State:** complete under the T2-only instruction; [source trace, synthetic observations and limits](verification.md#t2-current-mechanism-and-synthetic-controls-2026-11-07). That instruction did not itself authorize T3 or a remedy.

## R01CAL-A01-T3

**Contribution:** integrate the diagnosis and deliver a justified recommendation against the entire spec. Owns [DQ4](spec.md#dq4) and combined review of [DQ1–DQ4](spec.md#questions-and-discriminating-evidence) and [A1–A6](spec.md#planned-diagnosis-acceptance), especially the interpretation in [A5](spec.md#a5) and preservation/recommendation in [A6](spec.md#a6).

**Prerequisites:** T1 and T2 have produced their available observations and recorded blockers. Review may assess a partial result, but required unperformed checks cannot be marked accepted. Do not wait for proof of model causality that the spec deliberately leaves outside offline acceptance.

**Work and ownership:**

- Review evidence against each question and criterion, checking identities, original/current distinctions, scope classification, preservation, missing cases and the actual saved/read/exported synthetic observations. Correct documentary or diagnostic-analysis mistakes within the diagnosis boundary; production fixes remain excluded.
- Classify candidate explanations as supported, contradicted or unresolved. Separate mechanism facts from usability inference and remaining agent-behavior uncertainty. Compare only evidence-relevant next actions and state the acceptance needed for any proposed repair. Recommend no code change if the evidence does not justify one.
- Record the combined diagnosis verdict in [verification](verification.md#diagnosis-acceptance), retaining incomplete/blocked coverage and the smallest needed follow-up. Preserve the prior planning reviews and failed observations. Save consequential remedy options and reasons in REQUEST_CAPACITY; update WORK_ITEMS/PHASE_PLAN only when their distinct selection or phase facts change, then update CURRENT_STATE.

**Finish and checks:** the maintained report is understandable without private logs and traces the conclusions to actual observations, with private availability limits stated. Whole-spec coverage and the [completion/stop rules](spec.md#deliverable-readiness-and-continuation) determine whether diagnosis is complete or partial/blocked. Check affected documentation meaning, links and whitespace. This is main-agent review, not independent review. Stop after the diagnosis report and recommendation; no repair, conversion, provider interval or publication follows by implication.

**Owner:** main agent. **State:** complete under the T3-only instruction; [combined diagnosis, explanation assessment and recommendation](verification.md#diagnosis-acceptance). Stop after this report; proposed follow-ups remain unselected.
