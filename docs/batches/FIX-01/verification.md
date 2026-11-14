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

## T4 — NET-PM-01

Updated `README.md` only: PDF case/limit claims point to the PDF acceptance table; precise document-access verification and real-model limits point to the Stage B implementation-history section; review scope/limits point to the recorded review. CURRENT_STATE is described only as interaction focus and resume navigation. The build paragraph describes the existing older `release/win-unpacked` folder app and gives `tools/build/build-windows.ps1 -Installer` to create an installer, without claiming an absent installer exists.

Checked each changed destination's section body against its link description. `Get-ChildItem -LiteralPath release -Name` found `win-unpacked` and `builder-debug.yml`, no installer. Read `tools/build/build-windows.ps1`: `-Installer` selects electron-builder NSIS; the default builds a folder app. No packaging, installation or conversion was run.

`pnpm build`: **passed**, TypeScript and all three electron-vite bundles. `.venv/Scripts/python.exe tools/docs/check_docs.py`: **passed**, 147 Markdown files, 8,473 local links/destinations, 503 bundled source files verified, zero errors. `git diff --check`: **passed**. These are targeted implementation checks, not T5 whole-batch acceptance. T5 and the combined verdict remain the coordinator's responsibility.

**Documentation impact.** README's changed links were checked against their actual section content, and current local API behavior is explained in the integration guide. The named spec/tickets and WORK_ITEMS/PHASE_PLAN selection basis were reconciled with this assignment; no work-selection or phase outcome was changed. CURRENT_STATE, ticket integration/review ownership and other T6 records remain for the coordinator. T3's unresolved contract question is retained in its section above; it is not silently described as implemented in any owner.

## T5 — Integration

Pending.

## Combined verdict

Pending.
