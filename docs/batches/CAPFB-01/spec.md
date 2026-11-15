# CAPFB-01 specification

## Selected outcome and authority

2026-11-15 (Asia/Singapore). After the [GYN-01 post-run review](../GYN-01/verification.md#post-run-review), the user answered "ok, use gpt-6.1-sol-xhigh to implement" to the proposed offline investigation of [GYN-T3-01](../GYN-01/verification.md#gyn-t3-01--unfinished-final-self-check). This selects:

1. the offline investigation of [GYN-PR-01](../GYN-01/verification.md#gyn-pr-01--the-final-stop-coincides-with-near-zero-reported-capacity)'s three targets, and
2. if the evidence supports it, a bounded correction of the agent-facing capacity feedback and context guidance, with offline tests.

Implementation is delegated to Codex (`gpt-6.1-sol`, reasoning effort `xhigh`) as the user instructed; Codex tests and fixes first, then the main agent reviews, re-tests, records and commits locally. Not selected: any model/provider call, live conversion, Continue of the GYN-01 task, change to compaction policy or capacity calculation, GYN-PR-02's figure-resolution remedy, push, PR or merge.

## Problem

In GYN-01's final three requests the `Working context feedback` reported `remaining` 3,280 → 1,141 → 36 tokens. The agent saved a partial version, read one block, then reported partial with its final self-check "still pending", with 23 sends and about 27 minutes of active allowance unused. The feedback note ends "nothing is released automatically", and the guidance in `src/pdfmd/context.py` says only "History pressure retains eligibility for compaction." Neither states what the app does when the next request would exceed capacity. Earlier in the same run the agent continued at 7,518 and 5,708 remaining and the app compacted automatically, so low capacity alone did not stop it. The cause is unproven.

## Investigation questions

- **Q1 — mechanism.** When a normal request's input would exceed capacity, what does the current code do (automatic history compaction, a deferral, a diagnostic, a wait)? Under which conditions is compaction not available (for example, pinned or confirmed-necessary content)? Cite the code paths and existing tests.
- **Q2 — what the agent is told.** Does the agent-facing feedback and system guidance let an agent tell that a low or near-zero `remaining` is not by itself a reason to stop, when Q1 shows the app will compact? Identify the exact misleading or missing statements.
- **Q3 — Task A.** Does historical Task A (R01CAL-A01, [identity](../../verification/20261106_1408_R01CAL_TASK_A.md#identities-and-preserved-conditions)) show the same pattern in its final requests (low `remaining` before a voluntary partial report)? Its task predates parts of the current feedback, so record what feedback it actually received. Read its retained store read-only.

## Correction rule (conditional)

Proceed only if Q1 establishes the app's actual behavior at capacity and Q2 finds that the agent-facing text omits or misstates it. Then:

- State the actual behavior accurately and briefly in the feedback note and the system guidance: what happens when the next request would not fit, and that low `remaining` is a capacity measure, not a stopping condition or a reason to report partial, while saved work and the requested scope remain. Keep every statement true for the cases where compaction is not available.
- Keep the change to wording. Do not change capacity arithmetic, the compaction trigger, admission, budgets, tool schemas, pins/release semantics or report rules. Do not add a stop-prevention rule, a forced continuation or coaching about this source.
- Update the owning design text where it states this behavior (for example `docs/design/CONTEXT_MANAGEMENT.md`, `docs/design/CONTEXT_UPDATE_COORDINATION.md` or the guide that documents the feedback) so the contract and the prompt agree.

If Q1/Q2 do not support a wording defect, make no product change and report the evidence and the remaining hypotheses.

## Acceptance

- **C1:** Q1–Q3 answered with code references, test references and store evidence; uncertainty stated.
- **C2 (if a correction is made):** regression tests assert the corrected feedback note and guidance statements, and that the feedback's numeric fields and the compaction/admission behavior are unchanged (existing tests still pass).
- **C3:** relevant engine tests pass in Codex's run and again in the main agent's independent run on the final tree. The full engine and desktop suites are not required unless the change reaches shared request assembly beyond text.
- **C4:** documentation owners agree with the code; `tools/docs/check_docs.py` passes.
- **Limit:** no live evidence. Whether the wording changes agent behavior needs a separately selected live check.
