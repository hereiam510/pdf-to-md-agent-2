# CAPFB-01 verification

## Investigation findings

2026-11-15 (Asia/Singapore). Evidence from Codex's T1 report, checked by the main agent against the code. Both task stores were read only through copies under ignored `.local/agent-runs/capfb-01/`; the original catalog hashes were unchanged afterwards.

**Q1 — what happens at capacity.** Normal assembly first tries the complete input, then may replace individually oversized, unpinned bodies with references (`src/pdfmd/context.py`, normal assembly). Several bodies that each fit but overflow together are not evicted. If the normal input still does not fit, `ContextUpdates.continuation` (`src/pdfmd/context_updates.py`) selects a history compaction request, unless:

- the mandatory reservation does not fit (`necessary_estimate_uncertain`) or necessary content provably exceeds capacity (`capacity_blocked` / `feedback_capacity_blocked`); or
- no compaction segment fits, or the configuration is unsupported.

In those cases the run stops with a diagnostic and keeps saved work. Existing coverage includes the oversized-body deferral and pinned/configuration obstruction tests in `tests/engine/context/`.

**Q2 — what the agent was told.** The feedback note ended "nothing is released automatically", and the guidance said only "History pressure retains eligibility for compaction." Neither said that the app compacts automatically when the next input will not fit, nor that low `remaining` is input headroom rather than a task limit. **A wording defect is supported.**

**Q3 — Task A.** Store `workspaces/rc-e7e29aa7/store`, task `c52d328240904cbf99ed7042aa8f5002`:

| Request | Input estimate | `remaining` | Action |
| --- | --- | --- | --- |
| `6:6` | 77,502 | 45,378 | preview saved document |
| `7:7` | 82,278 | 40,602 | edit page metadata |
| `8:8` | 82,975 | 39,905 | `report(partial)` |

Task A received the same note and guidance wording, but its partial stop came with about 40,000 tokens of headroom and no compaction. **The near-zero-capacity lead does not explain R01CAL-A01.** For GYN-01 the store confirms the [GYN-PR-01](../GYN-01/verification.md#gyn-pr-01--the-final-stop-coincides-with-near-zero-reported-capacity) trace (3,280 → 1,141 → 36) and the two automatic compactions (154,307 → 51,940 and 127,334 → 25,799). This remains correlation, not cause.

## Correction

The change is limited to two agent-facing strings and their design text:

- `src/pdfmd/working_context.py`: the feedback note now says `inspect_context` only previews changes, that low `remaining` is estimated input headroom and not a stopping condition or a reason to report partial, that the app compacts automatically when the next input still does not fit (after deferring oversized unpinned bodies) when feasible and otherwise blocks with a diagnostic, and that saved work and requested scope remain.
- `src/pdfmd/context.py` (`SYSTEM`): four lines stating the same, including that `remaining` is not a task budget.
- `docs/design/CONTEXT_MANAGEMENT.md` and `docs/design/DOCUMENT_MODEL.md`: the same behavior, the cases where compaction is unavailable, and that pin/release and report rules are unchanged.
- `tests/engine/context/test_working_context.py`: six new cases. In both protocols, at 32 and 100,000 tokens of headroom, they check the wording, the unchanged numeric fields and the unchanged state. Also in both protocols: automatic compaction is selected when two unpinned 40,000-token reads overflow, and the same reads pinned produce `necessary_estimate_uncertain` with no release, history change or attempt.

An AST comparison by Codex and the main agent's diff review agree that only the note and `SYSTEM` strings changed in product code. Capacity arithmetic, the compaction trigger, admission, budgets, schemas, pin/release semantics and report rules are unchanged. Every request's input estimate grows slightly with the longer wording, which the existing estimator counts.

## Checks

| Run | Command | Result |
| --- | --- | --- |
| Codex | `pytest tests/engine/context/test_working_context.py -q -k capacity_guidance` | 6 passed |
| Codex | `pytest tests/engine -q -k "context or compaction or working"` | 514 passed, 0 failed, 0 skipped |
| Main agent | `pytest tests/engine/context/test_working_context.py -p no:cacheprovider` | 17 passed, 0 failed |
| Main agent | `pytest tests/engine -p no:cacheprovider -k "context or compaction or working or prompt or system"` | 519 passed, 0 failed, 0 skipped (1,345 s) |
| Both | `python tools/docs/check_docs.py`, `git diff --check` | passed |

The full engine and desktop suites were not run: the change is two strings, and the selected tests cover feedback assembly, admission, compaction and the runtime prompt in both protocols. The delegation helper's final JSON print failed on the Windows console encoding (`→` in the report); Codex itself completed with exit code 0 and its artifacts were intact.

## Combined verdict

**CAPFB-01 is accepted offline.** C1–C4 of the [spec](spec.md#acceptance) are met. The capacity feedback and guidance now describe the app's actual behavior at capacity. The investigation narrowed GYN-T3-01's cause without proving it, and showed that Task A's partial stop had a different context.

Limits: there is no live evidence that the new wording changes agent behavior. GYN-01's partial result and R01CAL-A01 stay open at their owners. Confirming the effect needs a separately selected live run. GYN-PR-02 (figure resolution) is untouched. The work is local on `codex/capfb-01`, which is not pushed.
