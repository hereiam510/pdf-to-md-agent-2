# Project layout and development routes

This guide owns maintained code, test and utility locations. [Architecture](../ARCHITECTURE.md) owns application responsibilities; [artifact storage](../ARTIFACT_STORAGE.md) owns private/generated data and retention; [INDEX](../INDEX.md) is the complete document catalogue. The [organization decision](../decisions/PROJECT_ORGANIZATION.md) explains the selected layout and preservation boundary. Do not infer implementation readiness from directory structure.

## Application sources

| Location | Responsibility and constraints |
| --- | --- |
| `src/pdfmd/` | Installed Python package, exposed through `pdf-md-engine` / `pdfmd.server:main`. Keep one engine and shared tools. No backend package migration is needed to use this layout. |
| `src/desktop/main.ts`, `preload.ts` | Electron process lifecycle, authenticated local engine, explicit IPC and isolated renderer bridge. Their explicit electron-vite inputs remain in the root configuration. |
| `src/renderer/main.tsx`, `index.html` | Application composition and renderer entry. Root `types.ts` defines shared desktop/renderer contracts; `style.css` owns the existing global styles. |
| `src/renderer/features/documents/` | Saved-document edit-session hook and obsolete-read/session guards. |
| `src/renderer/features/settings/` | Task-limit and response-waiting editors. Connection composition reuses the same waiting component. |
| `src/renderer/features/receive/` | Receive/progress facts shown from durable observations. |
| `src/renderer/features/recovery/` | Accepted-evidence diagnosis/recovery UI; inspection is separate from execution authority. |
| `src/renderer/features/diagnostics/` | Read-only activity UI and the typed diagnostic-record client. Shared result types remain in `types.ts`. |
| `src/pdfmd/data/` | Compressed tokenizer resource and its license. Keep its package-resource identity and frozen-build destination. |

Do not create a feature directory solely for a future idea. Keep feature-specific UI together and shared contracts with their actual consumers. A directory move must update relative imports, compile-time type checks and any fixture that loads the module directly. There is no second API client, service layer or agent loop implied by these folders.

### Engine module lookup

The engine remains a small flat package so its existing imports, lifecycle and package-data lookup stay stable. Read the relevant module with its technical guide; the following is a responsibility map, not a requirement to create more packages.

| Concern | Modules under `src/pdfmd/` | Detailed owner |
| --- | --- | --- |
| Task service, orchestration and dispatch | `server.py`, `runtime.py`, `tools.py`, `active_time.py` | [Execution and delivery](EXECUTION_AND_DELIVERY.md), [runtime contract](../design/RUNTIME_AND_DELIVERY.md) |
| Native requests, receive and accounting | `nexus.py`, `streaming.py`, `waiting.py`, `usage.py`, `request_estimation.py` | [Streaming contract](../design/STREAMING_RECEIVE.md), [integration](INTEGRATION_AND_MODEL_BOUNDARY.md) |
| Offline fixed-payload calibration evaluation | `calibration.py` | [Study/corpus commands and semantics](CONTEXT_AND_EVIDENCE.md#offline-calibration-evaluator); developer-only explicit invocation, no runtime profile activation |
| Offline bounded usage-anchoring coordinator | `usage_trial.py`, shared `anchor_basis.py` | [Coordinator mechanism](CONTEXT_AND_EVIDENCE.md#offline-usage-anchoring-coordinator); explicit mock-only injection, no application enrollment entry point |
| Opt-in usage observation and shadow pricing | `usage_observation.py`, `usage_anchoring.py` | [Observer mechanism](CONTEXT_AND_EVIDENCE.md#observation-only-usage-anchoring); no admission or trial authority |
| Context assembly and commitment | `context.py`, `context_revisions.py`, `context_updates.py`, `context_outcomes.py`, `working_context.py` | [Context engineering](CONTEXT_AND_EVIDENCE.md), [coordination design](../design/CONTEXT_UPDATE_COORDINATION.md) |
| Immutable content and PDF evidence | `storage.py`, `schema.py`, `documents.py`, `evidence.py` | [Document engine](DOCUMENT_ENGINE.md), [PDF contract](../design/PDF_EVIDENCE.md) |
| Acceptance, history and recovery | `acceptance.py`, `history.py`, `recovery.py` | [Recovery design](../design/ACCEPTED_EVIDENCE_RECOVERY.md) |
| Read-only diagnostic projection | `diagnostics.py`, `receive_diagnostics.py` | [Diagnostic design](../design/LOCAL_DIAGNOSTICS.md) |

## Tests and fixtures

| Location | Use |
| --- | --- |
| `tests/conftest.py` | Shared synthetic PDF, route and temporary Store fixtures. |
| `tests/engine/context/` | Admission, coordination, pins, compaction, handoffs and working context. |
| `tests/engine/documents/` | Editing, exact reads, PDF coordinates/images and saved/reopened/exported delivery. |
| `tests/engine/execution/` | Runtime, acceptance settlement, continuation/recovery, time/settings and security boundaries. |
| `tests/engine/transport/` | Native requests, estimation, deadlines, streaming persistence/semantics and reply repairs. |
| `tests/engine/diagnostics/` | Read-only diagnostic facts, attribution and failed-result behavior. |
| `tests/desktop/specs/` | Playwright specs, including actual Electron workflows and focused client tests. |
| `tests/desktop/fixtures/` | Python offline fixture builders. Launch with `python -m tests.desktop.fixtures.<name>` from the repository root. |
| `tests/desktop/support/` | Isolated Electron harnesses, delivery verification, test-boundary hook and result-location helper. |
| `tests/desktop/types/` | Compile-only diagnostic client/type checks; included by the root TypeScript configuration. |
| `tests/fixtures/pdf/` | Seven versioned synthetic color/mask/JPX PDFs; [fixture provenance](../../tests/fixtures/pdf/README.md). |

Tests use canonical `tests.engine.<concern>.test_<name>` imports where they share an existing builder. Shared desktop fixture modules use `tests.desktop.fixtures.<name>` imports, including when consumed by engine tests. Do not reload these modules under ad hoc names through file-path loaders: that creates a second module identity and bypasses the package layout. Root `tests/__init__.py` and the group package files make those identities explicit. Pytest uses `--import-mode=importlib`; a flat test directory is no longer inserted as an implicit import root. Desktop fixture builders use those same identities through module launch. They do not modify `sys.path`. The selected wheel packages only `src/pdfmd`, so the test packages are not application modules.

From the repository root:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pytest tests/engine/transport/test_stream_contract.py
pnpm build
pnpm test:desktop
pnpm exec playwright test streaming-delivery.spec.ts
python tools/docs/check_docs.py
python tools/docs/source_lookup.py EVT-1166
```

Desktop checks use synthetic local model/IPC fixtures. They do not make provider calls. Their generated profiles, stores, screenshots and reports use a unique run directory selected by `playwright.config.ts`; [storage policy](../ARTIFACT_STORAGE.md#test-executions) explains overrides and runner cleanup. A compile-only test is not an executed UI check. Build and desktop evidence do not establish installed-product readiness.

## Tools and build inputs

| Location | Entry points and consumers |
| --- | --- |
| `tools/dev/` | `setup.ps1` installs from existing frozen lockfiles; `start.ps1` launches development or the existing packaged app, with development-only credential-file selection/opt-out; `make-smoke-pdf.py` generates a synthetic test source at the supplied destination. |
| `tools/build/` | `build-windows.ps1` freezes the Python engine, runs its smoke checks and packages Electron; `engine-entry.py` is the frozen entry and explicit trusted-script child entry; `check-frozen-engine.py` validates the existing frozen runtime without a network call. |
| `tools/docs/` | `check_docs.py` validates documentation/source references; `source_lookup.py` reads the bundled provenance. Both find the repository two parents above their own file, independently of caller working directory. |
| `tools/runtime/ocr-worker.cjs` | Tesseract worker launched by Electron in development and copied to the packaged resource root by electron-builder. Its packaged name stays `ocr-worker.cjs`. |

PowerShell entry scripts derive the repository from their script directory and run there. Python fixture module commands and `pnpm` commands are invoked from the repository root. `Start Workbench.cmd` still launches the local existing Windows folder app and selects `workspaces/default`; it is not a setup script or proof that the old distribution contains current source.

Root `pyproject.toml`, `uv.lock`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `tsconfig.json`, `electron.vite.config.ts` and `playwright.config.ts` retain their supported discovery locations. Package-data collection, the frozen entry path, development OCR path and packaged OCR input must be updated together when moving a tool. Package/build allowlists are separate from Git ignore rules; see [storage and distribution boundaries](../ARTIFACT_STORAGE.md#build-and-distribution-boundaries).

## Earlier locations

Before this round, renderer feature files lived directly under `src/renderer/`, Python tests directly under `tests/`, desktop builders/specs/harnesses together under `tests/desktop/`, and utilities directly under `tools/`. Engine test filenames and desktop spec filenames are unchanged; their concern directories identify their current owner. A former `tests/desktop/<topic>-fixture.py` is now `tests/desktop/fixtures/<topic_with_underscores>.py`. [The round's exact relocation map](../verification/20261031_1646_PROJECT_RELOCATIONS.json) also includes inherited untracked files. Historical commands and manifests describe the tree actually used then. They are not rewritten into claims about this tree; use current commands above for new work.
