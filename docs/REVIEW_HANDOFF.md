# Context capacity, editing and continuation review handoff

This review target is the working tree based on `2d60c68`, including the three editing/continuation batches and the subsequent context-capacity/pin increment. The new increment is the primary review focus; earlier changes remain part of the actual source and regression boundary. [CURRENT_STATE](CURRENT_STATE.md) owns verification results and evidence locations. [PRODUCT_REQUIREMENTS](PRODUCT_REQUIREMENTS.md) owns intended outcomes. This document maps the review scope and proposed next work; it is not authorization for a new model call, implementation or publication.

## Product and revision scope

The user supplies a PDF and scope. The app runs its own agent through Nexus and supports complete, faithful, readable and reusable Markdown plus source images, with little routine user handling. The agent keeps its choice of methods, tools and reconstruction scope. No fidelity reduction, hidden scope reduction, compulsory extraction recipe or new per-tool approval is part of this revision.

| Batch | Implemented behavior | Main review locations |
| --- | --- | --- |
| Current: capacity and independent pins | Explicit deferral of an individually unfit body with precise read references; no arbitrary eviction of individually fitting evidence; pins hydrate independently of compacted history; original bodies and native pairs retained | `src/pdfmd/context.py:normal/pins/group/compact_request`, tool guidance; `tests/test_context_admission.py`, `test_context.py`, adjusted compaction-pressure fixtures in `test_response_repairs.py` |
| 1. Version-bound editing and reuse | UI draft bound to loaded task/version/head; ordinary edit versus explicit autonomous rebuild; local insert/replace from exact candidate content | `src/renderer/useDocumentSession.ts`, `main.tsx`, `types.ts`; `src/pdfmd/schema.py`, `documents.py`, tool/system guidance; `tests/test_documents.py`, desktop session/workbench tests |
| 2. New instructions before old pending tools | Recover completed receipts and context intents; pair unstarted obsolete calls with unexecuted results; retain candidates; keep unknown effects unknown; old report cannot terminate a new amendment | `src/pdfmd/runtime.py:tools`, `tools.py:reconcile/skip/settle`, `nexus.py:instruction_basis`; `tests/test_continuation.py` |
| 3. Explicit failed-request Continue | New request after HTTP/rejected reply or amended never-sent input; persistent decision before checkpoint update; latest input and failure references; original unknown replay gates and budgets retained | `server.py:Engine.start`, `runtime.py:resume_pending/run`, `nexus.py:reconcile/send`, `context.py:continuation_feedback`; `tests/test_continuation.py` |
| Integration | Local Stop/amend/Continue, version preservation, restart and ZIP delivery; earlier UI edit/rebuild coverage retained | `tests/desktop/continuation-workflow.spec.ts`, `boundary-hook/sitecustomize.py`, `verify_delivery.py`, `workbench.spec.ts` |

Exact contracts are in [Q1–Q3](CONTRACTS.md#implemented-first-version-contracts). The [context guide](design/CONTEXT_AND_EVIDENCE.md#implemented-capacity-admission-and-independent-pins), [document guide](design/DOCUMENT_ENGINE.md#implemented-editing-and-reuse-behavior) and [execution guide](design/EXECUTION_AND_DELIVERY.md#implemented-continuation-boundaries) explain mechanisms and rationale. The existing single-writer graph and native Nexus services fit these boundaries; dependency pins are unchanged. No general recovery rewrite was needed.

## Evidence and independent reproduction

Use the supplied source snapshot rather than HEAD alone. `manifest.json` in the local review package lists every packaged source byte hash and identifies additions that ordinary `git diff` does not display. `changes.patch` includes tracked and new files relative to HEAD; `context-increment.patch` isolates the current batch against the preserved preceding source snapshot. Existing root review scratch, credentials, private PDF packages and real Nexus workspaces are excluded. The optional historical design sources in the source ZIP remain reference data, not current instructions.

From the extracted source with the locked development environment installed:

```powershell
.venv\Scripts\python.exe -m pytest -o addopts= -q
pnpm build
pnpm test:desktop
.venv\Scripts\python.exe tools/check_docs.py
```

These commands do not require Nexus credentials. Python tests use mock HTTP; desktop conversion tests use a loopback server with scripted responses. The three renderer-session tests use controlled IPC replies. The continuation desktop test uses the real backend with a test-only delay after a real settled context-tool receipt, allowing UI Stop at a deterministic boundary. Normal app startup does not load that hook. This is not a test of safely terminating arbitrary running scripts.

The current final run passed **80 Python tests in 66.67 seconds**, **five desktop tests in 1.3 minutes**, the TypeScript/desktop build and documentation checks. The earlier 68-test editing/continuation baseline remains preserved separately. Relevant evidence is bundled under `evidence/`:

- Full test/build/document-check logs and focused continuation logs.
- Current capacity fixtures for both native protocols: image-heavy synthetic PDF, exact saved version, original/fixture payloads, exported ZIP, source/output screenshots and hash verification. They use only mock HTTP and retain complete dictionary evidence. They prove the exercised continuation and content preservation, not natural model adoption of precise reads.
- Synthetic two-page source, reopened screenshot, exact exported ZIP, verification JSON and fixture payloads from the continuation workflow.
- The previous editing/rebuild workflow's source, reopened screenshot, delivery ZIP and verification JSON.
- The initial desktop failure log and explanation: interrupting a running script produced the existing `local_outcome_unknown` result, so the test was corrected to target a settled boundary. Its failure was not concealed by changing the product's unknown-effect behavior.

The retained checks compare all exported members with the reopened saved version, compare source image bytes and retain the original PDF unchanged. The scripted text fixtures preserve source strings but are not evidence of natural agent strategy, full conversion quality or universal formatting fidelity. The normal/compaction failure tests cover the selected re-entry paths, not every possible crash.

## Review questions and remaining limits

Review the implementation independently; the following questions help locate consequential boundaries, not prescribe findings:

- Does a fitting full selection remain full? Can a giant first result be reached by arbitrary precise/full/raw reads after an explicit deferral, with original warnings/coverage intact? Does aggregate history pressure still exercise compaction rather than silently evicting evidence?
- After removing covered history, do exact pins still hydrate from immutable originals, including candidate syntax and image pixels? Do mandatory oversized pins stop explicitly? Does a pin protect only its selected object rather than freezing an entire batch or recursively claiming referenced content was read?
- Are native call/result pairs and reasoning items preserved? Are capacity decisions visible in frozen inputs/metadata without putting hydrated bodies into graph checkpoints? Do correction and Continue tests still exercise actual compaction after the fixture changes?
- Can a stale/asynchronous renderer read change draft identity or exported version? Can an explicit rebuild or local candidate reuse change unrelated content without declaring it?
- Does amendment handling preserve actual completed work, exact native pairing and context intents while stopping unstarted obsolete work? Is every unknown effect reported honestly?
- Does Continue retain old evidence and consumption, recover its own persistence gaps, and prevent a new-ID bypass of unknown-outcome replay limits?
- Do retained originals, reopened versions and ZIP bytes agree? Distinguish structural completeness from source-led content acceptance.

No new Nexus/model call, external change, dependency upgrade, old-repository modification or Windows repackaging occurred. `Start Workbench.cmd` and existing `release/` artifacts still use the earlier response-correction build. Use the development launcher to exercise this source. No migration of pending requests created by older builds is provided; use isolated development test workspaces. Older completed saved versions remain readable/exportable.

Known remaining areas, outside this revision:

- **Source-supported defects:** `Engine.start` applies new limits only before a job has requests; changed connection limits do not amend an existing job. `Runtime.run` charges a persisted open active interval through restart, including downtime after an abrupt death. These can obstruct continuation despite saved work.
- **Observed conservative boundary:** stopping an active script can leave `local_outcome_unknown`. The files survive, but the app has no general mechanism to inspect/settle that effect and resume autonomously. The failed integration attempt confirms this boundary for the synthetic script; it does not justify assuming all interrupted scripts are safe to repeat.
- **Current capacity limits:** huge mandatory instructions/pins, non-projectable native items or an oversized metadata scaffold can still block. The estimator is conservative configuration-based accounting, not measured provider usage. Full/raw access does not guarantee a full object fits one inference. Repeated model choices to request the same oversized full view are not classified as semantic no-progress by this increment.
- **Previously identified but not repaired here:** PDF rotation/region and CMYK/soft-mask evidence issues. They remain separate delivery concerns; this capacity increment supplies no new live frequency, fidelity or cost measurements for them.
- **Unverified:** natural use of local candidate reuse by live models, real-provider failed-request recovery on this revision, arbitrary crash guarantees, current Windows distribution and clean-machine installation.

## Suggested upcoming plan

These are proposed bounded batches. Their order can change if independent review finds a more direct delivery blocker. They are not started by this handoff.

1. **Address review-confirmed delivery blockers.** Reproduce findings against this snapshot; distinguish regressions, pre-existing defects and hypotheses. Fix the smallest coherent set at the responsible boundary, preserving agent autonomy. Completion: targeted reproductions pass, affected workflow still saves/reopens/exports correctly, and evidence/owners agree.
2. **Make existing-job limits and active time understandable and effective.** Address the two source-supported continuation defects together: explicit job-limit updates must retain already consumed usage, and restart must not silently charge offline time as active execution. Keep unknown outcome replay separate. Completion: local clock/fault tests, effective-limit UI/API checks, no reset of consumed attempts and no loss of saved delivery. Exact accounting policy should be stated before implementation.
3. **Correct a source-evidence defect when selected for work.** Reproduce the retained rotation/region-coordinate or CMYK/soft-mask issue with a minimal source and fix the responsible evidence boundary. Completion: coordinate/native-pixel expectations are explicit, the resulting saved/reopened/exported image matches the source, and unrestricted extraction/render choices remain available. Avoid combining this with unrelated framework or provider expansion.

The capacity increment is implemented and locally verified; it is no longer a queued proposal. Natural agent use on a user-selected complete section remains unverified and needs separate authorization before any new Nexus/model call. That validation is not a reason to erase the limits of scripted tests or reopen closed experiments.

Broader local-effect recovery, provider expansion, packaging and framework replacement are not hidden prerequisites for those batches. A concrete delivery blocker can change priorities without reopening every historical design option.
