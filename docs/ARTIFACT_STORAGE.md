# Artifact storage and retention

This policy owns project-specific storage, authoritative copies, access and retention. [Project layout](guides/PROJECT_LAYOUT.md) owns maintained code/tests/tools; [INDEX](INDEX.md) owns document navigation. Product source/evidence/version semantics remain with [documents](design/DOCUMENT_MODEL.md), [PDF evidence](design/PDF_EVIDENCE.md) and [runtime/delivery](design/RUNTIME_AND_DELIVERY.md). This policy does not authorize deleting or migrating existing data.

## Ownership and locations

| Class / location | Producer and consumer | Authority, inclusion and recovery |
| --- | --- | --- |
| Maintained `src/`, `tests/`, `tools/`, root manifests and lockfiles | Developers, test/build runners and application | Git sources. Add an adopted asset directly to its owner. Dependency locks reproduce the selected environment; do not silently upgrade. |
| Maintained `docs/`, `README.md`, `AGENTS.md`, `CHANGELOG.md` | Maintainers and repository readers | Git records, with one detailed owner per concern. Keep necessary rules/reasons/results here rather than only in local logs. Captured history and supplied originals retain their status. |
| `docs/sources/` | Source preservation and lookup utilities | Versioned provenance and complete source manifests. Original collection bytes and source hashes are preserved by `.gitattributes`; paths and supplied historical instructions are data. |
| `tests/fixtures/pdf/` | Synthetic evidence regressions | Versioned exact PDF fixtures with a provenance README. Separate from private real PDFs and model/reference answers. |
| `references/`, `private/`, `.env*` | Locally authorized source copies and connection/configuration owners | Ignored private material. Never recover credentials from conversation/authentication logs or include these directories in Git/review packages. `.env.example`, if deliberately supplied, is the ignore exception and must contain no secrets. |
| `workspaces/` or an explicit `-Workspace` | Application task store, engine and user | Ignored durable user data: original sources, SQLite metadata/checkpoints, immutable objects, attempts, candidates, versions and receipts. A task directory is not an OS sandbox. Preserve it independently of test/build cleanup. |
| `outputs/` or the user's selected export destination | Explicit-version exporter and user | Ignored user deliverables. Preserve original destination files and source/version identity; successful ZIP creation does not prove content fidelity. |
| `.local/<round>/` | Bounded development/review executions | Ignored local snapshots, manifests, logs and selected evidence. Record source identity, purpose, results and availability in the appropriate maintained owner. Local-only evidence is not available to an external reviewer by implication. |
| `.local/test-runs/<run>/` | New default desktop-test executions | Ignored synthetic stores/profiles/screenshots plus a separate Playwright `results/` directory. See the execution rules below. |
| `build/`, `out/`, `release/` | PyInstaller, electron-vite and electron-builder | Ignored generated engine/build/package products. Unique retained builds can be evidence; directory names alone do not make them disposable or current. |
| `test-results/`, `playwright-report/` | Earlier or explicitly configured test runners | Ignored results. New desktop defaults use the per-run location; existing results are retained in place. |
| `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.tools/` | Local environment and tool caches | Ignored dependencies/caches. Inspect actual ownership/use before separately authorized cleanup. Do not change global settings to reorganize the checkout. |

An installed Electron app normally uses its own user-data location. `tools/dev/start.ps1` selects ignored `workspaces/default` unless passed `-Workspace`; direct `pnpm dev` uses Electron user-data defaults. `Start Workbench.cmd` selects this checkout's default store for the existing packaged app. These locations are distinct; reorganizing source files neither imports nor migrates a task store.

## Test executions

`playwright.config.ts` creates a unique default `.local/test-runs/<UTC-timestamp>-<process-id>/` and passes its absolute path to workers as `PDFMD_TEST_RUN_ROOT`. Specs resolve their default synthetic evidence below that root. Electron harness profiles use that same identity. Playwright's `results/` child can be cleared by the runner; case stores, screenshots and reports needed beyond that lifecycle belong in sibling locations. A fresh default run does not overwrite the preceding run.

Keep case subdirectories concise: the run identity already carries the execution context. The streaming case uses `streaming/` rather than repeating a multi-level evidence/delivery/desktop hierarchy. Windows file previews can fail for deep asset paths even when the package bytes are valid; [R14](reviews/RUNTIME_FINDINGS.md#r14--deep-windows-file-url-assets-can-fail-to-display) records the observed limit and remaining destination work. A deliberately deep override is not guaranteed to work in every external viewer.

To retain a named run, choose a new path before starting:

```powershell
$env:PDFMD_TEST_RUN_ROOT = Join-Path $PWD '.local/my-check-run1'
pnpm test:desktop
Remove-Item Env:PDFMD_TEST_RUN_ROOT
```

Do not reuse a named run expecting earlier results to survive Playwright cleanup. The existing specific `PDFMD_*_EVIDENCE` overrides remain available for deliberately selected external/local evidence locations; those overrides take precedence over the default and can reuse paths. Choose them consciously and record their destination. A runner output flag does not move case evidence unless the corresponding root/override also selects it.

Run desktop commands serially unless every participating app launch has an explicitly isolated Electron user-data profile. `workers: 1` serializes one Playwright command, not a second concurrent command. Some ordinary-app fixtures isolate their task store and connection file through `PDFMD_DATA` while retaining Electron's default browser profile; separate task directories do not isolate that profile. The supplied isolated harnesses instead place profiles with their case evidence. The organization round retains one overlapping-run window-close failure and a successful serial control; it does not claim general concurrent-profile support.

Pytest uses its standard temporary-directory fixtures unless a check deliberately selects `--basetemp`. Before selecting one, ensure the destination is a new batch-owned path; pytest may remove/recreate it. Keep XML/log reports outside that disposable directory. Preserve useful earlier failure artifacts on reruns. Local tests use synthetic sources and model/IPC fixtures; live Nexus calls require separately authorized task execution.

## Build and distribution boundaries

Git inclusion, wheel inclusion, desktop packaging and external transmission are separate decisions. `.gitignore` does not define a general packaging boundary.

- Hatch's wheel target packages `src/pdfmd`; tokenizer resources retain their `pdfmd/data` identity. Test packages, fixtures and private inputs are not engine package inputs.
- PyInstaller reads `tools/build/engine-entry.py`, `src/` imports and the explicitly listed engine/data/dependency resources. It writes under `build/engine` and `build/pyinstaller`; its generated spec also belongs to `build/`.
- electron-vite's configured inputs emit `out/main`, `out/preload` and `out/renderer`. A build can replace those generated files. Preserve an earlier meaningful build separately before overwriting it.
- electron-builder selects `out/**` and `package.json`, production dependencies, the generated `build/engine` resource and `tools/runtime/ocr-worker.cjs`. The worker is copied to the resource root as `ocr-worker.cjs`. It must not select repository task stores, private inputs or reference copies.
- `tools/build/build-windows.ps1` writes the Windows folder app/optional installer under `release/`. It can replace existing generated builds. Preparation, packaging, installation and publication are different actions; do not describe an existing binary as containing new source moves or fixes without a matching build/check identity.

Inspect the actual selected inputs when changing a build flow. Do not broaden a package/upload context merely because a needed file was moved. Export ZIP membership remains governed by explicit document-version/asset contracts, not repository packaging.

## Preservation and cleanup

Before a move or overwrite, identify original observations, user edits, authoritative copies, active use and recovery needs. Keep a proportionate recoverable copy and a mapping when necessary. Before recursive filesystem cleanup, resolve and verify the exact absolute target inside the intended workspace; use one shell's native literal-path operations. Ignore status and a successful test do not supply deletion permission.

For each meaningful execution, associate command, source/input identity, conditions, result and retained evidence with its batch. Reruns preserve previous failures and unknown usage rather than relabeling them as success. Store lasting explanations and compact shareable results in the relevant design/decision/verification owner. A local snapshot or hash alone does not explain a mechanism or prove semantic preservation. Historical retention exceptions remain with [their recorded owner](verification/20261031_0342_TEST_ARTIFACT_RETENTION.md); that closed cleanup is not a standing policy to delete more files.

When a new maintained dependency emerges from an experiment, move/adopt the necessary source or permitted evidence into its lasting owner and repair consumers. Do not make ordinary development depend on an undeclared local helper, old conversation export or another checkout. Where originals must remain private or unavailable, record the access/availability limit and which claims cannot be independently rechecked. Retention or garbage collection of runtime user data remains an unselected product capability in [proposed changes](PROPOSED_CHANGES.md).
