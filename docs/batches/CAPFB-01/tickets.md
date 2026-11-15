# CAPFB-01 tickets

## Planning basis

Selected under the [spec](spec.md#selected-outcome-and-authority). Local tickets; branch `codex/capfb-01` from `codex/gyn-01` at `5fc3a5e`.

| Ticket | Work | Responsible | Depends on | Progress |
| --- | --- | --- | --- | --- |
| T1 | Answer Q1–Q3 with code, test and store evidence | Codex (`gpt-6.1-sol`, `xhigh`) | — | Planned |
| T2 | If supported, correct the feedback note, system guidance and design owner text; add regression tests; run relevant tests | Codex | T1 supports a wording defect | Planned |
| T3 | Review the diff, re-run checks independently, record the verdict, commit locally | Main agent | T1 (and T2 if made) | Planned |

T2 is skipped if T1 finds no wording defect; T3 then records the investigation result.

## Progress

- **T1, T2:** done by Codex CLI 0.169.0 (`gpt-6.1-sol`, `model_reasoning_effort="xhigh"`, Codex's configured sandbox, approval `never`) in one run of assignment `CAPFB-01-IMPL`, session `01a1df07-b014-7513-beaf-ccfa48944e2d`. T1 supported a wording defect, so T2 was carried out. The prompt, event stream, final report, store copies and `investigation.json` are retained under ignored `.local/agent-runs/capfb-01/`.
- **T3:** reviewed and re-tested by the main agent; see [verification](verification.md#combined-verdict).
