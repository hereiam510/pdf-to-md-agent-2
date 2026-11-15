# FIX-01 tickets

[Spec](spec.md) · [Verification](verification.md)

## Planning basis and authority

The [spec](spec.md#selected-outcome-and-authority) owns scope, authority and acceptance. Ticket mode is local. The user asked for implementation to be delegated to Codex CLI with model `gpt-6.1-sol` at reasoning effort `xhigh`, in a `workspace-write` sandbox with no interactive approvals, working directly in this checkout on `codex/fix-01`. The main agent owns the assignment, review, integration, the whole-batch checks and the records. The implementer leaves its changes uncommitted for review; the main agent commits them on `codex/fix-01`. The implementer may not push, open a PR, merge, change global settings, read `private/` or call a provider.

## Sequence and dependencies

| Ticket | Depends on | Implementer | Files (single writer) |
| --- | --- | --- | --- |
| [T1](#t1--h02-mojibake-in-agent-facing-text) | — | Codex | `src/pdfmd/tools.py`, any other file with the same mojibake, a test |
| [T2](#t2--h03-local-api-input-validation) | — | Codex | `src/pdfmd/server.py`, new or existing server tests |
| [T3](#t3--r01-surrogate-trace-and-rejection-boundary) | — | Codex | The trace result decides; expected `src/pdfmd/` extraction, reply-validation or storage code and their tests |
| [T4](#t4--net-pm-01-readme-routes) | — | Codex | `README.md` |
| [T5](#t5--integration-and-whole-batch-checks) | T1–T4 | Main agent (Codex runs the targeted tests for T1–T4 and `pnpm build`) | Records only |
| [T6](#t6--review-and-records) | T5 | Main agent | `docs/` owners |

T1–T4 are independent. One implementer does them in order, so no file has two writers.

## T1 — H02: mojibake in agent-facing text

Correct the preview argument error in `Tools.preview` (`src/pdfmd/tools.py`) to use a real en dash or a plain hyphen. Search `src/`, `tests/` and `tools/` for other mojibake sequences (`â€`, `Ã`) and fix any in maintained text. Add or extend a test that checks the message.

**Done when** the [H02 acceptance](spec.md#acceptance) holds.

## T2 — H03: local API input validation

For each route in `src/pdfmd/server.py` that takes `body: dict` (currently `import_source`, `start`, `task_settings`, `edit`, `export`, and the `resolve_conflict` engine path), declare the expected body with Pydantic models or FastAPI's native parameter validation, so missing or wrongly typed fields produce FastAPI's request-validation 4xx naming the field. Check the installed FastAPI/Pydantic versions and their documented validation behavior first. Keep optional fields optional with their current defaults, and keep every field the desktop currently sends (search `desktop/` or the renderer for the calls). Where a route's engine method also reads required keys from a nested dict, validate those too or map the failure to a 400 with the field name. Keep the authorization dependency and the existing `ValueError` handler.

**Done when** the [H03 acceptance](spec.md#acceptance) holds.

## T3 — R01-SURROGATE: trace and rejection boundary

Follow the [agreed rule](spec.md#r01-surrogate-rule-agreed-2026-11-14). First trace the producers and write the findings, with file and function references, into the [verification](verification.md) T3 section. Then implement the rejection at each reachable boundary, with tests through the real path. Use existing helpers where they fit (`asset_catalog.record_json` already rejects lone surrogates with `encode("utf-8", "strict")`).

**Stop and report** instead of deciding alone if meeting the rule needs a change to stored formats, to how source text is represented, or to the rejected-reply contract.

**Done when** the [R01-SURROGATE acceptance](spec.md#acceptance) holds.

Implementation under decision A is delivered uncommitted for main-agent review; [T3 verification](verification.md#implementation-under-decision-a) owns producer boundaries, targeted checks, failures/reruns and limits. T5/T6 remain with the main agent.

## T4 — NET-PM-01: README routes

Apply the [NET-PM-01 finding](../NET-01/verification.md#post-merge-review-and-orientation). In `README.md`, replace each pointer to CURRENT_STATE for implementation facts (PDF rotation/CMYK/SMask/JPX cases, document-access verification limits, review limits) with a link to the section that actually holds the fact. Find it by searching `docs/design/`, `docs/guides/` and `docs/history/IMPLEMENTATION_HISTORY.md`. Correct the build paragraph: `release/` currently holds only the folder build `win-unpacked`, and no installer has been built since the source changes; say how to build one instead of naming a missing file. Keep the README short. Do not change other owners except to fix a link that README needs.

**Done when** the [NET-PM-01 acceptance](spec.md#acceptance) holds.

## T5 — Integration and whole-batch checks

On the final revision, run:

```powershell
.venv\Scripts\python.exe -m pytest tests/engine --junitxml=build/fix-01-engine-<rev>.xml
pnpm build
pnpm test:desktop <specs that exercise the changed routes>
.venv\Scripts\python.exe tools/docs/check_docs.py
git diff --check
```

The full engine suite took about 33 minutes at NET-01. Record the revision, counts, failures and reruns in [verification](verification.md#t5--integration). A failure caused by this batch is fixed within scope; an unrelated pre-existing failure is recorded, not fixed.

## Progress

T1–T4 implemented by Codex and committed as `2d833b5` and `0103aa1`; T5 run on `0103aa1`; T6 completed with the [combined verdict](verification.md#combined-verdict). All tickets are accepted. On 2026-11-15, at the user's request ("Push and open PR"), `codex/fix-01` was pushed and [PR #3](https://github.com/hereiam510/pdf-to-md-agent-2/pull/3) opened against `master`. It is open and mergeable, with no CI checks configured. Merging needs the user's request.

## T6 — Review and records

The main agent reviews the diff against the spec, reruns checks where needed, and records the verdict in [verification](verification.md). It updates the H02, H03 and R01-SURROGATE rows in [WORK_ITEMS](../../WORK_ITEMS.md), the NET-PM-01 status, [CURRENT_STATE](../../CURRENT_STATE.md), the [batch catalogue](../../INDEX.md#batch-documents) and any guide or design text whose behavior changed (for example the local API or input-validity rules).
