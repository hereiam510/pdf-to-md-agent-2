# FIX-01 verification

[Spec and acceptance](spec.md#acceptance) · [Tickets](tickets.md#sequence-and-dependencies)

## T1 — H02

Implemented in `src/pdfmd/tools.py`: the preview argument error now uses en dashes. Added `tests/engine/documents/test_preview_validation.py` (three invalid viewport cases through `Dispatcher.execute`, after saving a real version). `rg -n 'â€|Ã' src tests tools` found only the corrected source string before the change; the final search found no matches (expected rg exit 1).

Checks on the uncommitted tree based on `756a434`:

- `.venv/Scripts/python.exe -m pytest tests/engine/documents/test_preview_validation.py tests/engine/documents/test_documents.py -q`: 27 setup errors; Windows denied pytest's default temporary directory. No application assertion ran.
- The same selection with `--basetemp=.local/fix-01-t1-a -o cache_dir=.local/fix-01-pytest-cache --tb=short`: 27 setup errors and session cleanup failed with `WinError 5`. Python's Windows `mkdir(mode=0700)` creates directories inaccessible to this sandbox.
- Process-local runner below, with temporary path `.local/fix-01-t1-c`: 24 passed, 3 failed because the new test read `error` instead of the dispatch envelope's `data.error`. Corrected that assertion.
- Same runner and selection, path `.local/fix-01-t1-d`: **27 passed, 0 failed**.

The process-local runner used for targeted pytest runs in this assignment is:

```powershell
.venv/Scripts/python.exe -c "import os,pytest; mkdir=os.mkdir; os.mkdir=lambda path,mode=0o777,*,dir_fd=None: mkdir(path,0o777,dir_fd=dir_fd); raise SystemExit(pytest.main([<test files>,'-q','--basetemp=<unique path>','-o','cache_dir=.local/fix-01-pytest-cache-c','--tb=short']))"
```

This changes test-process directory creation only, without changing application source, installed dependencies, ACLs or user/global settings. The first successful run exposed the assertion defect above. Generated data stays in ignored `.local/`. No guide describes the old garbled message, so no behavior documentation change is needed for T1.

## T2 — H03

Implemented typed local bodies in `src/pdfmd/server.py` for import, start, settings and export. Optional fields retain their defaults; settings remain patches and merged nested values use the existing Route/Limits validation and 400 handler. Manual edits retain the original candidate before native `Edit` validation produces a 422 with body/field locations. Direct `Engine.resolve_conflict` calls now validate `ConflictResolutionSelection`, matching the already typed HTTP route. Authorization and the existing ValueError/Conflict handler remain in place.

Installed/locked versions checked offline: FastAPI **0.161.1**, Pydantic **2.14.1**. Inspected their shipped documentation/source: `pydantic/main.py:BaseModel.model_validate` describes strict validation and location-bearing ValidationError; `fastapi/exception_handlers.py:request_validation_exception_handler` returns 422 with `detail`. No network access or dependency change. Desktop call fields were checked in `src/desktop/main.ts` (import, start including recovery identities, settings, edit, export and conflict resolution).

Added `tests/engine/execution/test_api_validation.py`: 30 cases for missing/wrongly typed fields on all six routes, nested settings/import errors, candidate retention and unchanged head on rejected edits, direct conflict validation, and valid desktop-shaped import/settings/edit/export/start requests using MockTransport. Updated the local API explanation in `docs/guides/INTEGRATION_AND_MODEL_BOUNDARY.md#local-api-input-validation`.

The first process-local runner selected `test_api_validation.py`, `test_security.py`, `test_task_settings.py`, and `test_accepted_evidence_recovery.py`, using `.local/fix-01-t2-a`, `-q -rA` and the T1 runner options: **132 passed, 3 failed**. All 30 new API cases passed. The three existing child-process crash-recovery cases failed before their injected exit because children did not inherit the directory workaround. No application workaround was added for this environment issue.

The rerun inherited the same mkdir workaround through ignored `.local/fix-01-test-support/sitecustomize.py`, using process-local `PYTHONPATH`. Its only effect is to use normal directory creation when a test asks for mode 0700; children inherit it. Exact command:

```powershell
$env:PYTHONPATH = (Resolve-Path .local/fix-01-test-support).Path
.venv/Scripts/python.exe -m pytest tests/engine/execution/test_api_validation.py tests/engine/execution/test_security.py tests/engine/execution/test_task_settings.py tests/engine/execution/test_accepted_evidence_recovery.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t2-b -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**135 passed, 0 failed in 155.28 s.** This tested the final T2 implementation; the temporary T3 changes described below were subsequently removed in full.

`pnpm test:desktop workbench.spec.ts`, with process-local `PYTHONPATH` as above and `PDFMD_SKIP_CREDENTIAL_FILE=1`: **could not execute**. Playwright selected one test, then failed to spawn its worker with `EPERM` (exit 1); zero test bodies ran. No credential loading, model call or fixture conversion occurred. This sandbox has no escalation path. Desktop validation remains with the coordinator, including settings and accepted-recovery coverage. No full engine or full desktop suite was run.

## T3 — R01-SURROGATE

### Producer trace (before T3 implementation)

Trace performed offline on the T1/T2 working tree based on `756a434`. These are reachability conclusions, not claims about observed user incidence.

| Producer | Reachability and evidence | Earliest rejection boundary |
| --- | --- | --- |
| PDF text extraction | **Reachable.** `evidence.py:Evidence.inspect` calls `page.get_text(mode)` then stores JSON. The installed `pymupdf/__init__.py:JM_make_spanlist` uses `chr(ch.m_internal.c)` in raw character dictionaries; `make_escape` substitutes U+FFFD in other text representations. An in-memory synthetic PDF with ToUnicode `<42> <D800>` yielded `A`, U+D800, `C` in `rawdict`, and `A`, U+FFFD, `C` in text/blocks/words/dict. Source bytes were not changed. | Inspect raw page characters within `Evidence.inspect`, before requesting a representation that can normalize them. Report physical page and zero-based extracted character offset; retain the original PDF. Image metadata and other strings also need validation before persistence. |
| OCR output | **Reachable.** `tools/runtime/ocr-worker.cjs` writes `JSON.stringify(data)`; JavaScript JSON can escape lone UTF-16 units. `tools.py:Dispatcher.ocr` decodes `result.json` with `json.loads` and immediately stores the result object. JSON escapes bypass UTF-8 byte validation. | Validate decoded OCR fields before storing derived evidence; report page, field and zero-based character offset. Keep result.json and complete logs available. |
| Trusted scripts and other tool output | **Reachable through decoded JSON.** `tools.py:Dispatcher.script` retains outputs/logs as bytes. Its stdout preview decodes with `errors='replace'` (cannot produce a Python surrogate); strict UTF-8 plain text cannot contain one either. However `evidence.py:Evidence.read` first calls `Store.json`, so a retained JSON output containing an ASCII `\ud800` escape becomes a lone surrogate and reaches `returned_bytes`/tool-result persistence. Tool arguments can also carry a nested JSON escape after `Dispatcher.execute` decodes them. | Validate decoded evidence and decoded tool arguments before use/settlement. Original output/candidate bytes stay immutable and raw-accessible. No change is needed to binary output storage or the preview's existing byte-decoding behavior. |
| Native model replies | **Reachable in both protocols, streaming and non-streaming.** `nexus.py:_parse_reply` decodes native JSON, then separately decodes each call's argument string. A surrogate can be in text, identifiers, keys, reasoning, or doubly escaped tool JSON. Non-streaming raw bytes are saved before parsing. `streaming.py:StreamDecoder._dispatch` decodes JSON events; `nexus.py:Nexus.send` stores the assembled value before `parse_reply`, so streaming events need an earlier guard too. | Reject decoded native strings and decoded argument values before acceptance, preserving raw native bytes or SSE chunks without executing a rejected call. Valid pairs within JSON decode to scalar non-BMP text. **The investigation below found that the existing rejected-reply path does not enter automatic repair; this is the stop point.** |
| User-entered text/configuration | **Reachable.** The local API decodes JSON into Python strings; import scope, start amendments, manual edits and arbitrary route parameters can carry escaped surrogates. Direct `Evidence.create_job`/`Engine.start`/`Engine._configure` calls also bypass HTTP validation. | Reject API JSON before schema/domain handling, plus validate direct entry points before writes. Existing ValueError client errors remain actionable and leave the task reusable. |
| File names/paths | **Reachable.** Windows wide paths can contain unpaired UTF-16 units, and local JSON paths can explicitly carry one. `Evidence.create_job` places `Path(path).name/stem` in blob/job records; `Dispatcher.script` places discovered output filenames in metadata. Export destinations also enter OS operations and delivery records. | Validate supplied paths before file operations and discovered filename metadata before registration. Retain any original script files/logs; no rename or character substitution. |
| Request preparation and metadata persistence fallback | **Reachable for direct/native callers.** `request_estimation.py:estimate` and `nexus.py:Nexus.freeze` use `storage.py:encode`; `Store.put_tx` and `Store.stage_blob` share it. Existing `asset_catalog.py:record_json` already uses strict UTF-8 and does not normalize characters. | Convert strict UTF-8 failure into a clear ValueError with field/offset context, before request freezing or metadata publication. Binary source bytes remain allowed. |

No listed producer can be declared wholly unreachable. Plain strict UTF-8 text and the script stdout preview are unreachable **subpaths**, but decoded JSON from those tools is reachable. The preliminary expectation was that boundary checks would suffice without changing record formats, source representation, or the rejected-reply contract. The real-path check contradicted the last part, as follows.

### Stopped: rejected native replies do not enter automatic repair

**T3 is not implemented.** Temporary boundary guards and three test files were used to exercise the trace, then removed from the delivered working-tree diff once the required contract change became clear. No stored format, source representation or rejected-reply behavior was changed. The remaining T3 change is this trace and stop report.

`nexus.py:Nexus._settle_failure` maps `rejected_reply` to `response_rejected`; `Nexus._check_reentry` raises `StopRun` for a rejected request. `runtime.py:Runtime.model` calls `Nexus.send` without catching that stop, and `Runtime.run` marks the task blocked. `Runtime.repair` instead references an **accepted** reply (`accepted_ref`) and is invoked only for an accepted no-tool normal reply, unexpected compaction tools or an invalid handoff. The [runtime contract](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) likewise gives rejected replies explicit user Start/Continue, while [automatic correction](../../design/RUNTIME_AND_DELIVERY.md#continuation-feedback-and-delivery-settlement) bounds text-only replies and invalid handoffs. A rejected native reply has no accepted-ref basis for that existing repair record.

The temporary end-to-end controls fed ASCII JSON escapes for lone U+D800/U+DFFF through both native protocols, with and without SSE, and observed **blocked / response_rejected after one attempt**, with the original native/SSE evidence retained and no tool execution. All sixteen controls expecting automatic repair failed at that final-state assertion. Extending that behavior is a material rejected-reply contract change, so the ticket stopped as instructed.

Attempted command (same process-local PYTHONPATH as T2):

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/documents/test_unicode_sources.py tests/engine/execution/test_unicode_inputs.py tests/engine/transport/test_unicode_replies.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-a -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**18 passed, 19 failed in 9.87 s; three test regex escape warnings.** The other three failures were test-fixture issues: the filename assertion also counted stdout/stderr `.txt` logs, the raw-body valid-pair API request omitted Content-Type, and the estimation fixture omitted the required model identity. Their fixture corrections were saved but not rerun after the contract stop. Passing controls exercised all five real PDF extraction modes with a synthetic ToUnicode mapping, OCR JSON with a mocked process result, an actual opted-in script emitting escaped JSON, API/direct-input guards, atomic persistence rejection and request-freeze rejection. These temporary checks establish investigation evidence only, not final R01-SURROGATE acceptance. An in-memory PyMuPDF extraction probe independently reproduced the rawdict-versus-normalized-text distinction before the temporary guard implementation.

Useful attempted code/test copies are retained in ignored `.local/fix-01-t3-investigation/`; the attempted patch includes the then-current T1/T2 diff as context and must not be applied blindly. Temporary test artifacts remain under `.local/fix-01-t3-a/`. The repository alone contains the substantive findings above; scratch is optional supporting material.

**Question for the coordinator/user:** may FIX-01 extend the rejected-native-reply contract to bounded automatic repair using retained native/SSE evidence when `accepted_ref` is absent, or should the surrogate rule retain the existing blocked/explicit-Continue behavior? No such choice was made here. Source/guide behavior owners remain unchanged for T3 because no T3 implementation is delivered.

### Implementation under decision A

Continued offline on the clean `codex/fix-01` tree at `896886d`, under the user's decision A and T3-only assignment. The producer trace and stop report above retain their original investigation status; this implementation answers that historical stop. No automatic repair of rejected replies was added. No stored format or source representation changed; no dependency, global setting, provider call, reads of `private/`, `references/` or `workspaces/`, branch, commit or publication was involved. Checks use synthetic stores in ignored `.local/`. Changes remain uncommitted for coordinator review.

The saved investigation's T3 hunks were reused after inspection, excluding its old T1/T2/server-route changes. The first selective `git apply` failed on the scratch patch's CRLF line endings and changed no source; a local LF copy applied the selected hunks, with current server/tool guards adapted separately. The three saved test files were reused with all three known fixture corrections: discovered filenames exclude stdout/stderr logs, raw JSON requests declare Content-Type, and estimation includes the model identity. The sixteen reply controls now assert decision A.

| Reachable producer | Implemented boundary and preserved result |
| --- | --- |
| PDF extraction | `evidence.py:Evidence.inspect` checks raw page characters before any alternate PyMuPDF representation can substitute U+FFFD, then checks selected fields/metadata. Error names the one-based physical page and zero-based extracted-character offset; source PDF bytes stay unchanged and rendering remains usable. |
| OCR JSON | `tools.py:Dispatcher.ocr` checks decoded result fields before derived-evidence publication. Error names page, field and offset. Original result.json and complete process logs remain retained. Recognition itself is mocked in the new control. |
| Decoded script/tool JSON | `storage.py:Store.json` checks immediately after decoding, including later candidate reuse. `Evidence.read` propagates invalid-Unicode rejection instead of treating the escaped JSON as plain text. Exact full/range raw byte access remains available; scripts still require explicit process opt-in. |
| Decoded tool arguments | `tools.py:Dispatcher.execute` retains the argument-string candidate, then checks decoded keys/values before dispatch and settles a failed receipt. Reusing that rejected candidate cannot bypass the check. Direct script code and document edits are also checked before writes. |
| Native model replies | `nexus.py:parse_reply` checks decoded native fields and separately decoded tool JSON; `streaming.py:StreamDecoder` checks each decoded event before assembly. Both protocols, streaming and non-streaming: reject with native/SSE bytes preserved, no accepted reply or tool execution, `response_rejected` and blocked task; reopening alone sends nothing. Existing `Engine.start` explicit Continue succeeds, preserves the failed request/evidence and consumed attempts, and saves/reopens/exports exact emoji/CJK text. Streaming failures retain the existing generic safe message and fixed `unicode` diagnostic field. |
| User/API and direct inputs | `server.py` checks authenticated decoded POST bodies before schema/domain handling; lone-surrogate bodies return the existing 400 envelope with field/offset. Direct import, settings/start, conflict resolution and document-edit entry points check before writes. Rejected API mutations leave the existing job/objects unchanged and a subsequent valid settings action succeeds. |
| Filenames/paths | Source/import, export, Store root/file-registration and discovered script paths are checked without renaming. The Windows wide-filename control keeps the original lone-surrogate filename and bytes plus complete logs while rejecting metadata publication. |
| Request/persistence fallback | `storage.py:encode` turns strict UTF-8 encoding failure into `InvalidUnicode` (`ValueError`) with field/offset. Request-freeze metadata, record/event identities and blob metadata are checked before publication/staging. `asset_catalog.py:record_json` shares the same canonical encoder, retaining its exact format and existing XML-forbidden-scalar escapes. Valid non-BMP values persist and reopen exactly. |

Changed source files: `src/pdfmd/{storage,evidence,tools,nexus,streaming,server,documents,asset_catalog}.py`. Added tests: `tests/engine/documents/test_unicode_sources.py`, `tests/engine/execution/test_unicode_inputs.py`, and `tests/engine/transport/test_unicode_replies.py`. The tests cover all traced producers, atomic rejection, raw/candidate/log preservation, candidate reuse, the real opted-in script/Windows filename paths, valid JSON surrogate pairs, and explicit Continue with saved/reopened/exported output.

**Commands and observed results.** All pytest invocations below set process-local `$env:PYTHONPATH = (Resolve-Path .local/fix-01-test-support).Path` first, reusing the supplied mode-0700 workaround, inherited by test child processes. Each basetemp is a new ignored local run. No full engine or desktop suite was run.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/documents/test_unicode_sources.py tests/engine/execution/test_unicode_inputs.py tests/engine/transport/test_unicode_replies.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-b -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**33 passed, 4 failed in 23.01 s.** The four streaming-text controls incorrectly expected a field/offset in the existing generic stream-failure message. They already observed rejection. Corrected them to assert the retained fixed `unicode` diagnostic; the non-streaming/nested-argument cases still check the detailed message. No stream-error disclosure contract was changed.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/documents/test_unicode_sources.py tests/engine/execution/test_unicode_inputs.py tests/engine/transport/test_unicode_replies.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-c -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**43 passed, 0 failed in 28.28 s**, after adding direct persistence/key/path controls. Review then identified retained-candidate decoding as another route; validation moved into `Store.json`, with an explicit no-fallback rule in `Evidence.read` and one additional candidate-reuse control. Final-code reruns follow.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/documents/test_documents.py tests/engine/documents/test_pdf_delivery.py tests/engine/documents/test_document_access.py tests/engine/documents/test_version_publication.py tests/engine/documents/test_enriched_save.py tests/engine/execution/test_security.py tests/engine/execution/test_api_validation.py tests/engine/execution/test_task_settings.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-d -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**150 passed, 0 failed in 108.55 s**, before the final retained-JSON guard; this selection is included again in the final-code run below.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/execution/test_runtime.py tests/engine/execution/test_continuation.py tests/engine/execution/test_malformed_settlement.py tests/engine/execution/test_acceptance_settlement.py tests/engine/execution/test_accepted_evidence_recovery.py tests/engine/transport/test_request_estimation.py tests/engine/transport/test_response_repairs.py tests/engine/transport/test_streaming_parser.py tests/engine/transport/test_stream_contract.py tests/engine/transport/test_streaming_delivery.py tests/engine/transport/test_stream_storage.py tests/engine/transport/test_stream_acceptance_storage.py tests/engine/transport/test_stream_item_semantics.py tests/engine/transport/test_stream_item_persistence.py tests/engine/transport/test_stream_terminal.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-e -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**792 passed, 0 failed in 791.73 s (13:11)**. This process imported modules before the final retained-JSON guard; run `h` repeats the selection on final code.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/documents/test_unicode_sources.py tests/engine/execution/test_unicode_inputs.py tests/engine/transport/test_unicode_replies.py tests/engine/documents/test_documents.py tests/engine/documents/test_pdf_delivery.py tests/engine/documents/test_document_access.py tests/engine/documents/test_version_publication.py tests/engine/documents/test_enriched_save.py tests/engine/execution/test_security.py tests/engine/execution/test_api_validation.py tests/engine/execution/test_task_settings.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-f -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**194 passed, 0 failed in 194.36 s**, including all **44** T3 controls and the earlier 150-case regression selection. A final direct-settings guard was then moved ahead of task-lock file creation and its no-lock-write assertion added; the affected input/API/settings checks are rerun below.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/execution/test_unicode_inputs.py tests/engine/execution/test_api_validation.py tests/engine/execution/test_task_settings.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-g -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**73 passed, 0 failed in 52.28 s**, including the direct-settings no-lock-write assertion.

```powershell
.venv/Scripts/python.exe -m pytest tests/engine/execution/test_runtime.py tests/engine/execution/test_continuation.py tests/engine/execution/test_malformed_settlement.py tests/engine/execution/test_acceptance_settlement.py tests/engine/execution/test_accepted_evidence_recovery.py tests/engine/transport/test_request_estimation.py tests/engine/transport/test_response_repairs.py tests/engine/transport/test_streaming_parser.py tests/engine/transport/test_stream_contract.py tests/engine/transport/test_streaming_delivery.py tests/engine/transport/test_stream_storage.py tests/engine/transport/test_stream_acceptance_storage.py tests/engine/transport/test_stream_item_semantics.py tests/engine/transport/test_stream_item_persistence.py tests/engine/transport/test_stream_terminal.py -q -o addopts=--import-mode=importlib --basetemp=.local/fix-01-t3-h -o cache_dir=.local/fix-01-pytest-cache-c --tb=short
```

**792 passed, 0 failed in 705.39 s (11:45)** on final code. Across runs `f` and `h`, **986 distinct targeted cases** passed, including all 44 new T3 controls; run `g` repeats the 73 cases affected by the final direct-settings placement/assertion. No failing application assertion remains in these selections.

`pnpm build`: **passed**, TypeScript and all three electron-vite bundles. `.venv/Scripts/python.exe tools/docs/check_docs.py`: **passed** before the final ticket/continuation pointers (147 Markdown files, 8,484 local links/destinations, 503 bundled source files, zero errors), and **passed again** after those updates (147 files, **8,485** links/destinations, 503 bundled sources, **zero errors**). `git diff --check`: **passed** during implementation and after the final records/navigation updates. A repository-only Python comparison (`.venv/Scripts/python.exe -`, using `git show HEAD:docs/batches/FIX-01/verification.md` and the current file) also **passed**: the complete T5/combined-verdict tail is identical after newline normalization.

**Documentation impact and limits.** Updated the declared PDF/runtime design owners and the integration guide with the validity boundary, offset meaning, preservation rules and decision-A behavior. Checked affected current explanations by producer/contract names; no other owner needs an in-scope behavior correction. T3's ticket and CURRENT_STATE route to coordinator review. Work selection and phase outcomes have not changed, so WORK_ITEMS/PHASE_PLAN remain unchanged. The guard rejects malformed source-derived text; it does not certify extraction/OCR quality or source fidelity. Synthetic local transport fixtures establish mechanics without provider calls; real-route behavior, whole-engine/desktop integration and combined acceptance remain for the coordinator. T5 and the combined verdict are unchanged. T3 implementation and targeted verification are ready for review, uncommitted.

## T4 — NET-PM-01

Updated `README.md` only: PDF case/limit claims point to the PDF acceptance table; precise document-access verification and real-model limits point to the Stage B implementation-history section; review scope/limits point to the recorded review. CURRENT_STATE is described only as interaction focus and resume navigation. The build paragraph describes the existing older `release/win-unpacked` folder app and gives `tools/build/build-windows.ps1 -Installer` to create an installer, without claiming an absent installer exists.

Checked each changed destination's section body against its link description. `Get-ChildItem -LiteralPath release -Name` found `win-unpacked` and `builder-debug.yml`, no installer. Read `tools/build/build-windows.ps1`: `-Installer` selects electron-builder NSIS; the default builds a folder app. No packaging, installation or conversion was run.

`pnpm build`: **passed**, TypeScript and all three electron-vite bundles. `.venv/Scripts/python.exe tools/docs/check_docs.py`: **passed**, 147 Markdown files, 8,473 local links/destinations, 503 bundled source files verified, zero errors. `git diff --check`: **passed**. These are targeted implementation checks, not T5 whole-batch acceptance. T5 and the combined verdict remain the coordinator's responsibility.

**Documentation impact.** README's changed links were checked against their actual section content, and current local API behavior is explained in the integration guide. The named spec/tickets and WORK_ITEMS/PHASE_PLAN selection basis were reconciled with this assignment; no work-selection or phase outcome was changed. CURRENT_STATE, ticket integration/review ownership and other T6 records remain for the coordinator. T3's unresolved contract question is retained in its section above; it is not silently described as implemented in any owner.

## Review of the delegated implementation

2026-11-15, main agent. Codex CLI 0.169.0 ran with model `gpt-6.1-sol`, `model_reasoning_effort="xhigh"`, the `workspace-write` sandbox and `approval_policy="never"`, in two assignments: T1–T4 (stopping at T3's contract question), then T3 under decision A. Prompts, event streams and final messages are retained under ignored `.local/agent-runs/fix-01-*`. The main agent read both diffs and committed them as `2d833b5` (T1, T2, T4 and the T3 trace) and `0103aa1` (T3).

- **T2 against the desktop.** The typed bodies forbid extra fields. `src/desktop/main.ts` sends exactly `path`/`scope` on import, `version_id`/`destination` on export, `route`/`limits` on settings, and `key`, `route`, `limits`, `amendment`, `scripts`, `recover_compaction_request`, `retry_request` on start (undefined values are dropped by JSON serialization). These match the declared fields.
- **T3 against the rule.** Model replies use the existing rejected-reply path, no character is replaced or dropped, and the boundaries match the trace. The rejected-reply contract text in the runtime design now states the surrogate case.
- **T3 cost.** `Evidence.inspect` now also runs PyMuPDF `rawdict` extraction, because other modes replace a lone surrogate with U+FFFD before it can be seen. On a synthetic 100-page text PDF (55 lines of about 95 characters per page), extraction per page rose from about 2.1 to 8.2 ms for `text`, 2.2 to 8.5 ms for `blocks` and 2.7 to 9.1 ms for `dict` (best of three). About 6 ms per page, or about 2 s for a 290-page whole inspection, is accepted against model latency. Revisit if inspection latency is observed in a real task.
- **Sandbox limits.** Inside Codex's sandbox, pytest's mode-0700 temporary directories were inaccessible and Playwright could not spawn workers (`EPERM`). The implementer's targeted runs used a test-process-only `mkdir` workaround; no application code depends on it. T5 below runs without the workaround, outside the sandbox.

## T5 — Integration

Run by the main agent on clean commit `0103aa1`, outside the Codex sandbox, with no test workarounds. No provider was called.

- `.venv\Scripts\python.exe -m pytest tests/engine -q -p no:cacheprovider --junitxml=build/fix-01-engine-0103aa1.xml`: **1,956 passed**, 0 failed, 0 errors, 0 skipped in 2,153 s. NET-01's final run had 1,879 cases; the difference is FIX-01's new tests. Log: `build/fix-01-engine-0103aa1.log`.
- `pnpm build`: passed (TypeScript and all electron-vite bundles). Log: `build/fix-01-build-0103aa1.log`.
- `pnpm test:desktop` (complete suite, one worker, the configured 120 s timeout): **118 passed** in 27.0 min, with no failures or reruns. This includes import, start, settings, edit, export, conflict resolution, continuation and the workbench delivery chain through the new typed API bodies and the Unicode checks. Log: `build/fix-01-desktop-0103aa1.log`.
- `.venv\Scripts\python.exe tools/docs/check_docs.py` and `git diff --check`: passed after these records.

An earlier full engine run at `2d833b5` was stopped before completion, because T3 was about to change the same modules; it supplies no result.

## Combined verdict

**FIX-01 is accepted offline.** Each item meets its [acceptance](spec.md#acceptance):

- **H02:** corrected message, test added, no remaining mojibake ([T1](#t1--h02)).
- **H03:** missing or wrongly typed fields return a field-naming 4xx on every changed route; valid desktop requests pass end to end ([T2](#t2--h03), T5 desktop run).
- **R01-SURROGATE:** every traced producer rejects at its earliest boundary without altering characters. Model replies follow decision A (blocked, explicit Continue recovers), proven in both protocols with and without streaming. Valid non-BMP text passes through save, reopen and export ([T3](#implementation-under-decision-a)).
- **NET-PM-01:** README pointers lead to the owners that hold the facts, and the build paragraph is accurate ([T4](#t4--net-pm-01)).

Limits: no real source PDF with a lone surrogate was available; the controls use synthetic ToUnicode maps, OCR JSON and replies. PDF inspection costs about 6 ms more per page ([review](#review-of-the-delegated-implementation)). Automatic repair of rejected replies is out of scope as [REPLY-AUTO-01](../../WORK_ITEMS.md#runtime-and-engineering-inventory). Delivery through [PR #3](https://github.com/hereiam510/pdf-to-md-agent-2/pull/3) is recorded in the [ticket progress](tickets.md#progress).

## Post-merge review and orientation

2026-11-15 (Asia/Singapore). Standalone review requested by the user ("review and suggest next steps") on `codex/fix-01-closeout` at `0417061`. No product code, build or provider interval was run.

**Merge result.** `master` equals `origin/master` at merge commit `b722341`. `git diff --name-only 0103aa1 0417061` lists only files under `docs/`, so the [T5 suites](#t5--integration) on `0103aa1` apply to the merged tree. A repeat engine run was started and stopped before completion, because it would only repeat T5 on the same code. It supplies no result. `tools/docs/check_docs.py` passed with no errors (147 Markdown files). Every local batch branch, including `codex/net-01-closeout` and `codex/fix-01`, is an ancestor of `master`.

**Findings.**

- **FIX-PM-01 — the combined verdict still said merging was pending.** P3 records. The closeout commit updated the ticket progress, CURRENT_STATE and WORK_ITEMS but not the last sentence of the [combined verdict](#combined-verdict). Corrected here with a link to the ticket progress.
- **FIX-PM-02 — closeout records are local only.** As with NET-PM-02, `0417061` and this review are not pushed. Until they are, GitHub's `master` shows PR #3 as "not merged" in CURRENT_STATE and the ticket progress.
- **NET-PM-03 still applies and is growing.** CURRENT_STATE now has about 70 return-route bullets. The same accumulation affects the [WORK_ITEMS selection paragraph](../../WORK_ITEMS.md#selection-now), which now retells NET-01 and FIX-01 history in one paragraph of about 400 words and contains the phrase "NET-PM-03 (unselected) (growing return-route list)". Still unselected.

**Residuals carried forward.** [REPLY-AUTO-01](../../WORK_ITEMS.md#runtime-and-engineering-inventory) (rejected replies block until Continue) revisits on a Stage B run that blocks on one. The 6 ms per page inspection cost revisits if latency shows in a real task. `release/win-unpacked` (2026-11-13) predates NET-01 and FIX-01, so any packaged check starts with a fresh build (DIST-01). UA-01-DEFAULTS remains the only small open defect, and it sits on a path that is disabled by default.

**Next step.** The [recommendation after NET-01](../../discussions/NETWORK_RECOVERY.md#next-step-recommendation-after-net-01) still holds. FIX-01 completed the user's "fix known bugs first" precondition. Recommended: discuss and specify one fresh, bounded Stage B source-led task, offline first. Its four decisions are unchanged: source and class, scope, a fresh task, and route and budget. Facts that inform the source choice, from a local read of `references/` (page text length and image count sampled with PyMuPDF; no content claims):

- `gynecology/source.pdf`: 21 pages, native text layer, figures on some pages. The prepared [Task B](../../discussions/REQUEST_CAPACITY.md) covered printed pages 1–3 with Figures 1.1–1.3, frozen on a 2026-11-06 build.
- `news-writing/source.pdf`: 290 pages, one image per page and a thin text layer (Task A's source, JBIG2 page images).
- `nursing/source.pdf`: 14 pages, native text with two images per page (historical Nursing closeout).

A fresh task on the gynecology section, extended to a complete section long enough to reach R01CAL-A01's outside-scope classification point, covers native text, figures (FD-01) and attribution text (AR-T5-14) in one run. A mixed or scanned class (CTX-08) would need a news-writing section as a separate choice. Nothing is selected.
