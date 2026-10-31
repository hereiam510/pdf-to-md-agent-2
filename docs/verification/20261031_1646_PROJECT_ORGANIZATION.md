# Project organization verification

Round recorded 2026-10-31 at 16:46, Asia/Singapore (UTC+08:00). [Decision, scope and acceptance](../decisions/PROJECT_ORGANIZATION.md). This record groups the checks for this organization round; results below distinguish planned work from executed evidence.

## Entry and preservation

Entry HEAD: `15393228205bca350f51decc16eddc9842ac49b1`, branch `master`, with inherited modified/untracked application, test and documentation work. The local entry snapshot contains 750 maintained/unignored files (14,860,948 bytes), an SHA-256 manifest, status and the original tracked diff under `.local/project-organization-20261031_1646/`. It excludes ignored private/runtime/dependency/build material. Existing task data and generated artifacts are not moved or cleaned.

The entry Python and desktop collection commands both exited 0. Python discovery found 1,290 cases in 47 modules; desktop discovery found 58 cases in 20 spec files. A second before/after collection explicitly emitted Python node IDs: applying the [100-file relocation map](20261031_1646_PROJECT_RELOCATIONS.json) leaves zero added or missing case identities, including parameterization. Desktop spec names/cases are unchanged. Collection logs and `discovery-comparison.json` are local to this batch.

## Results

The organization increment is complete. Build, packaging, source/preservation, navigation and affected regression conditions have sufficient local evidence. Python and desktop coverage are composite full-run-plus-correction results, as distinguished below; there is no single fresh all-green whole-suite run or new installed-product certification. Completed checks:

| Check | Executed result and limit |
| --- | --- |
| TypeScript and desktop build | Standalone `tsc --noEmit` and `pnpm build` exit 0. Existing `out/` was copied to the local round's `prior-out/` before rebuilding. Renderer feature imports and compile-only client checks resolve at their new paths. |
| Python discovery/imports | 1,290 exact before/after node identities; zero missing/added cases. Three nested `import test_* as ...` statements initially retained flat names despite successful collection; canonical imports were corrected before their focused final verification. |
| Documentation/source checks | The first check found four link occurrences targeting relocated code/tests: REQUEST_CAPACITY, one captured Stage B discussion and two runtime-review links. Correcting only their locator targets yields exit 0: 503 bundled source hashes, 356 point mappings and 356 development-detail mappings checked. Counts are structural evidence, not a semantic completeness verdict. |
| Source lookup and engine entry | `python tools/docs/source_lookup.py EVT-1166` and `.venv/Scripts/python.exe tools/build/engine-entry.py --help` exit 0. No old export/checkout or provider call is needed. |
| PowerShell discovery | All three moved scripts parse without errors, and the two-parent script-root expression resolves to this repository for development and build scripts. Setup/launch/build commands were not executed merely to inspect their root. |
| Isolated Windows folder packaging | `pnpm exec electron-builder --win --dir --publish never --config.directories.output=.local/project-organization-20261031_1646/package-run1` exits 0. It uses the existing generated frozen engine, not a rebuild of the inherited engine changes. Electron-builder's native-dependency step and Electron runtime preparation ran; dependency manifests/locks remain unchanged. Existing `release/` and `build/engine` are not output destinations. |
| Package input inspection | The isolated app archive has 310 members, with no top-level private/reference/workspace/output/local/test/docs/venv paths. Current renderer and frozen engine are present; the copied `ocr-worker.cjs` is SHA-256-identical to `tools/runtime/ocr-worker.cjs`. This verifies relocated package inputs, not latest-engine or installed-product readiness. |
| Entry preservation | All 26 engine files and 534 `docs/sources/` members are byte-identical to entry. All seven PDF fixtures are exact; their README's test locator is updated. No entry member is missing after relocation. Root/source/test/tool changes receive the scoped comparison below. |
| New owner navigation | Parsed CommonMark links from INDEX reach all four new Markdown owners; every local link in those owners resolves. Reader routes are assessed separately below. |

No live Nexus request, Nursing transition, original-repository change, installer execution or remote publication occurred.

### Python execution corrections

`python-run1` reports 396 passes and 894 setup errors in 30.82 seconds. The supplied `--basetemp` parent did not exist; pytest could not create its child. This is runner setup failure, not an application regression. The original log/XML remain retained. `python-run2` uses a new, explicitly created parent and a separate log/XML destination. Its result and any focused follow-up will be recorded here without replacing run1.

The focused `python-import-run3` executes all eight parameterized cases from the three corrected nested-import functions. All eight pass in 41.35 seconds. This uses the final canonical imports; the longer run2 had already imported its modules before those three statements were corrected, so its result cannot establish their final-source behavior by itself.

The full `python-run2` finishes with **1,282 passes, eight failures, zero errors/skips**, 1,862.08 seconds in stdout (JUnit 1,861.991). JUnit start time is `2026-10-31T16:54:35.045017+08:00`. Every failure is `ModuleNotFoundError` at one of the three old nested imports loaded before correction; no other failure appears. The focused final-source rerun covers exactly those eight identities:

| Pytest selector below `tests/engine/` | Parameterized cases | Final focused result |
| --- | --- | --- |
| `diagnostics/test_recovery_diagnostics.py::test_usage_projection_preserves_known_unknown_zero_and_inconsistency` | `known`, `original_unknown`, `zero`, `different_known` | Four pass |
| `transport/test_stream_item_persistence.py::test_incompatible_old_semantics_preserve_facts_and_stop` | `False`, `True` | Two pass |
| `transport/test_stream_terminal.py::test_suffix_rule_covers_real_compaction_handoff_edit_and_export` | `chat_completions`, `responses` | Two pass |

Together the full run and corrected eight-case rerun cover all 1,290 identities. This is composite regression evidence, not a second single all-green whole-suite run. Engine source and the other Python test bodies do not change afterward; subsequent fixture/storage corrections affect only desktop TypeScript/configuration. The earlier setup and import failures remain in their original logs/XML.

### Desktop execution corrections

The first full desktop run failed the continuation workflow at the 30-second settled-boundary predicate. Its trace identifies `continuation-workflow.spec.ts:71`: the hook never created `settled.txt`. Inspection found the `PYTHONPATH` directory still named `tests/desktop/boundary-hook`, while its file had moved to `tests/desktop/support/boundary-hook/`. The spec and the relocation recipe now select the correct directory. This is an organization defect in test wiring; no product timing/Stop rule is changed. The original run/log/trace remains in `desktop-run1/`; a separate focused rerun will verify Stop, amended Continue, restart and export on the corrected path.

`desktop-hook-run2` still fails that predicate after the path correction. Read-only SQLite inspection of both failed synthetic stores shows exactly one unknown request, `unknown_outcome`, no document head and no operation. The last event says the stream ended without a complete terminal response. The test server returned complete JSON while the new connection requested streaming. The JSON continuation and ordinary workbench fixtures now explicitly choose complete-response waiting; the existing task-settings JSON fixture already makes that choice. No source response is altered or accepted retrospectively. The first run's missing hook path remains a real separate correction, but it was not the first-request failure cause.

The full run's PDF-delivery case reports `electronApplication.firstWindow: Target page, context or browser has been closed` while the focused hook run overlapped it. The default-profile concurrency hypothesis remains unconfirmed pending a serial rerun; no product repair or timeout increase is selected. Later desktop reruns will be serial. The failed trace and all case stores remain available.

The full `desktop-run1` ends with **52 passes and six failures in 33.3 minutes**: both compaction-recovery protocols, continuation, PDF delivery, Chat Completions streaming delivery and ordinary workbench. Its cached workbench code still requests streaming from its JSON fixture; read-only inspection confirms one unknown first request with the original 600/300 wait policy. The later explicit complete-response selection is verified separately. The Responses streaming case, loaded after the storage correction, passes in the same full run; no failed result is replaced by that pass.

Both compaction cases fail on `getJob().events.filter`: the current job API no longer includes that event list. Their corrected test reads the existing activity projection, treats unavailable/malformed views as `-1` while polling, and closes successful captures. The stopped-event expectation and all original recovery/request/version/export checks remain. No product API is changed. A separate serial `desktop-final3` runs the two compaction cases plus continuation, PDF delivery, both streaming protocols and ordinary workbench, covering all six failed identities and the corrected streaming counterpart.

`desktop-final3` reports **five passes and two failures in 3.7 minutes**. Both compaction protocols, PDF delivery and both streamed saved/reopened/exported workflows pass. The original PDF window-close failure does not recur serially; overlapping default-profile use remains a candidate cause, with no product change or general concurrency claim. Streamed exports decode their original image successfully at the shorter new locations. A visual inspection of the exported Chat Completions preview confirms readable `25 mg` text, the final source sentence and the complete green source figure without a broken image; this is one synthetic output, not general PDF fidelity.

The two remaining failures are strict-mode locator ambiguity: both receive progress and the successful export toast have `role=status`. The workflows had completed conversion and reached export. Scope the continuation export and ordinary-workbench export/edit notifications to the existing `.toast.success`, retaining exact message assertions and accessibility roles. The subsequent serial `desktop-final4` reports **two passes in 49.9 seconds**, including Stop/amended Continue, failed-request continuation, source/image preservation, restart, edits and complete/partial explicit-version exports.

All six originally failing identities therefore pass on corrected source; with the 52 original passes, all 58 desktop identities have local coverage. The five- and two-case results are retained alongside the original failures; they are not presented as a new single 58-case all-green run. No unrelated desktop scenario is changed after its pass.

The [163-file implementation identity](20261031_1646_PROJECT_SOURCE.json) includes inherited work. The initial pre-hook-correction local manifest has SHA-256 `94ff17514fe42591d8eec6e8bb04f3b7eff38a860befd858fca819ca89cbec91` and is retained separately. Final checks identify the corrected manifest below; the scoped Git checkpoint alone is not the full tested implementation.

### Windows file-preview path control

The full run's streaming case completed saved/reopened delivery and ZIP extraction, then Edge raised `EncodingError: The source image cannot be decoded` at the exported HTML image check. The unchanged PNG is 7,778 bytes. A control copied the complete exported package byte-for-byte to a shorter batch-owned location and launched installed headless Edge with HTTP(S) requests blocked:

| Identical package location | Image URL pathname length | Decode result |
| --- | --- | --- |
| Original deep streaming case | 264 characters | `EncodingError`, natural dimensions 0 by 0 |
| Short control location | 192 characters | Success, natural dimensions 420 by 300 |

`path-control-inputs.json` retains the per-file hashes and `path-control-results.json` the two observed results; originals remain under `desktop-run1/`. This is a path/location-dependent viewer failure, not evidence of image-byte corruption. It does not measure a universal threshold. [R14](../reviews/RUNTIME_FINDINGS.md#r14--deep-windows-file-url-assets-can-fail-to-display) records the affected delivery risk and Stage D revisit condition.

The new test run timestamp now uses compact UTC digits, and the default streaming case uses `streaming/` instead of repeating `stream-progress-evidence/delivery/desktop/` below the run root. Explicit evidence overrides retain their authority. Shorter new paths must pass the original image decoding and saved/reopened/exported assertions; no assertion, image or package format is weakened. The same final source manifest records these fixture/configuration corrections.

Two subsequent default-root runs of `diagnostic-client.spec.ts` each pass both cases. They create distinct compact directories `20261031092226334-100712` and `20261031092228890-98636`, each with its own `results/`; the earlier run remains. These are UTC execution identifiers, not Asia/Singapore event timestamps. The post-path-correction local manifest has SHA-256 `07fd9fc0d0f85b86e3296cd33b104078897f112543e967697b019ae82980616f` and is retained before the activity-fixture correction; `8bec41fde8600e632a2bad3bc042c64bd1dea24df2e5e6ae756dd079836a1270` identifies the pre-toast-correction edition. The final 163-file local implementation manifest has SHA-256 `a3a2c9fcad2df628f71d52b3bb684fd90077fa90720df2f237bde7fcdac419d8`; its versioned form adds the stated scope envelope. Every current implementation member matches its recorded hash.

## Scoped Git and preservation boundary

The organization checkpoint stages tracked application/test files from HEAD plus the recorded relocation/import/test-storage/fixture-mode/API-consumer changes. Thirty-seven inherited source/test members remain modified or untracked at their mapped locations. The staged tree has no engine-file changes and no canonical test-import gaps. The shared retention record and its two inherited documentation navigation updates are included because the new storage policy cites that record; they do not authorize another cleanup.

All 144 existing implementation/tool/manifest members affected by the preservation comparison match the declared transformations, with zero unexpected changes or missing originals. Engine/source/PDF originals remain exact as described above. Dependency locks, workspace manifest, electron-vite inputs, TypeScript config, Git ignore rules and source-preservation attributes remain unchanged. The [versioned implementation manifest](20261031_1646_PROJECT_SOURCE.json) identifies the larger checked worktree, including local-only inherited members; it does not claim that every member is in the scoped commit or available remotely.

The local scoped commit containing this record is an organization checkpoint on `codex/project-organization`, not a clean release of the inherited implementation. No push, release, installer execution or user-data cleanup is included. Existing ignored evidence and all new failed/successful run products remain retained. Final source identity and staged/working boundaries are also recorded under the local round for continuation.

## Repository-only reading routes

- README's setup/start/build/document commands name existing `tools/dev`, `tools/build` and `tools/docs` entries. The architecture still explains the original component responsibilities; the layout guide locates the engine modules and renderer features without inventing another backend layer.
- INDEX's layout/storage topic reaches the selected structure and reasons, the artifact policy, this verification and the path map. The catalogue includes each new Markdown owner. CURRENT_STATE keeps readiness and the phase plan retains full fourteen-page Stage B acceptance.
- A context-test reader can follow the layout command to the context group, root conftest and canonical cross-group builders. A desktop reader finds specs separately from module-launched Python fixtures and harness/type checks. The original case names/parameters remain discoverable.
- A storage reader can identify which copy is authoritative, where private/runtime inputs belong, which runner can clear results, which package allowlists govern inclusion, and why ignored data is not automatically disposable. Earlier cleanup permissions remain historical.
- The moved settings link in the captured Stage B discussion reaches the same component at its current locator; its prose, constraints, recorded evidence and old commands retain their status. The prior Git edition and exact entry snapshot retain the old locator spelling. Source collections and shared historical design/rule editions are not rewritten.
- H05 is deferred until a justified responsibility/failure-boundary change; R03, broader R07, R01/CTX and residual R02 have their current impact and revisit conditions with the finding owners. Neither a path change nor passing local tests resolves those independent concerns.

These checks assess meaning and navigation for affected routes. No headings or fragment grammar changed, so a new rendered-browser audit was unnecessary. This is not a new source-first audit of every historical technical detail.

## Evidence limits

Local logs and snapshots are available in this checkout, not automatically to a remote reader. Maintained rules, methods, results and limitations belong in this repository; rerunning the declared synthetic tests requires the documented dependencies, not an old private workspace. Software checks do not certify full real-source conversion or installed-product readiness.
