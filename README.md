# pdf-to-md-agent-2

PDF Markdown Workbench is a local Electron app with a Python agent engine. The agent completes the conversion through Nexus. The app supplies source access, local OCR, document editing, context management, durable execution and explicit-version export.

**The first application increment is implemented.** It includes a Windows folder build and a desktop workflow for importing a PDF, specifying a scope, running an autonomous agent, reviewing or editing saved versions, and exporting a portable ZIP. See [current state](docs/CURRENT_STATE.md) for actual verification and limits. The original project remains unchanged.

## Run locally

Install Python 3.12 through `uv`, Node.js 24 and `pnpm`. From this repository:

```powershell
.\tools\dev\setup.ps1
.\tools\dev\start.ps1
```

The setup script uses the committed Python and JavaScript lockfiles. `-Uv` and `-Pnpm` accept executable paths. The launcher uses ignored `workspaces/default`; `-Workspace` selects a separate task store. Direct `pnpm dev` uses Electron's user-data directory instead.

Open **Nexus connection**, enter the full Chat Completions or Responses endpoint, model alias and credential, and configure the route's capacity and output allowance. Image inputs require a conservative per-image allowance. These are user configuration values, not discovered model specifications. Credentials can be remembered with Windows encryption; they are never stored in task journals. Choose a PDF, describe the whole document or complete section, and start conversion. Trusted host scripts are off by default.

New connections default to streaming progress waiting: up to **600 seconds before first generation progress**, then **300 seconds without further progress**, with **no total request cutoff** by default. These are adjustable starting points, not demonstrated sufficient values. Heartbeats and status events do not reset progress waiting. Complete replies are validated before tools execute. A total cutoff is available only as an explicit choice; legacy saved connections retain their previous non-streaming deadline until changed. See [the waiting contract](docs/design/STREAMING_RECEIVE.md#streaming-progress-waiting) and [route capability evidence](docs/research/20261031_0157_NEXUS_STREAMING_SIGNALS.md).

For an existing task, use **Task limits** while it is stopped to adjust total requests, active time, context capacity, output reserve, image allowance or response waiting, then Continue. Changes apply to future newly prepared normal and compaction requests, not an existing frozen request. Saving settings sends nothing and does not authorize replay of an unknown result. The task keeps consumed usage and pending requests. Connection settings remain defaults for unconfigured tasks. Recorded active time and any unmeasured interrupted intervals are displayed separately; see [the settings/time contract](docs/design/RUNTIME_AND_DELIVERY.md#existing-task-settings-and-active-time-accounting).

Source tools use a common unrotated page-coordinate frame for extraction, rendering and OCR regions. Image delivery separates display assets from retained original image/mask streams; saved versions and ZIPs include provenance and the originals associated with their selected images. See [the PDF contract](docs/design/PDF_EVIDENCE.md#pdf-coordinates-and-image-delivery) and CURRENT_STATE for the tested rotation, CMYK, SMask and JPX cases and remaining limits. These source changes require the development launcher until a new Windows distribution is built.

To build and run the Windows folder app:

```powershell
.\tools\build\build-windows.ps1
.\tools\dev\start.ps1 -Packaged
```

The folder app includes its Python engine. The build script's `-Installer` option creates an NSIS installer. Building an installer does not install it. The Windows build is unsigned. Local Tesseract OCR downloads requested language data on first use and caches it in the workspace.

For the current local build, double-click `Start Workbench.cmd` to open the saved Nexus test workspace. The installer is `release/PDF Markdown Workbench Setup 0.1.0.exe`. An installed copy uses its own user-data directory by default; it does not automatically import this checkout's private files or task store.

The authorized local `references/` and `private/` copies are ignored. They are not part of the app or public source distribution. Do not commit credentials, task stores or conversion outputs.

The development engine supports exact-version document indexes and field/range reads. Normal agent inputs include working-evidence/capacity feedback; optional `inspect_context` lists the frozen input and previews explicitly chosen policy changes. Smaller reads do not automatically remove earlier full content. See [the access and feedback contract](docs/design/DOCUMENT_MODEL.md#exact-saved-document-and-evidence-access) and CURRENT_STATE for local verification and real-model limits.

## Start here

Read [the working agreement](AGENTS.md), then **[the document catalogue](docs/INDEX.md)**. It provides topic routes and a complete categorized inventory. Use [CURRENT_STATE](docs/CURRENT_STATE.md) for actual implementation/verification and the next decision, [the phase plan](docs/PHASE_PLAN.md#delivery-route) for product outcomes, and [the handoff](docs/REVIEW_HANDOFF.md) for source/check boundaries. Historical run permissions are not present execution authority.

The catalogue leads directly to current streaming receive, document editing, context coordination, recovery and diagnostic designs, their reasons and original decision/discussion entries, applicable verification and preserved editions. [CONTRACTS](docs/CONTRACTS.md) is the shared-rule navigator; [DEVELOPMENT_GUIDE](docs/DEVELOPMENT_GUIDE.md) routes deeper engineering explanations.

The application includes the Windows publication repair and FD-01 guidance. The user [accepts the historical fourteen-page Nursing task as complete with its known figure-delivery limitation](docs/decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01). Original package/source-pixel/usage evidence and the [acceptance correction](docs/verification/20261031_2242_NURSING_LIVE.md#acceptance-correction-2026-11-01) remain intact; closeout does not certify the old output under full FD-01. The separate [two-page agent run](docs/verification/20261101_0103_FD01_TWO_PAGE_LIVE.md) passes bounded independent-figure/text and save/reopen/export acceptance in seven sends. Full fourteen-page FD-01 and captionless validation are deferred; neither closed interval authorizes continuation.

The [latest offline estimator assessment](docs/discussions/REQUEST_CAPACITY.md#current-estimator-offline-calibration-2026-11-01) is complete for those 34 sends. Original estimates equal exact-frozen-payload recomputation; all are high relative to corresponding reported input usage. **The current estimator and settings are retained.** Route-wide calibration, actual limits and whole-task benefit remain unproved; no numeric profile, implementation, compaction policy, provider call or Stage D phase is selected. [CURRENT_STATE](docs/CURRENT_STATE.md) retains other source-class and installed-readiness limits. No Langfuse integration is selected.

## Repository map

[Project layout](docs/guides/PROJECT_LAYOUT.md) maps engine modules, renderer features, test groups and utility entry points. [Artifact storage](docs/ARTIFACT_STORAGE.md) defines authoritative/private copies, per-run results, packaging boundaries and retention.

| Path | Role and handling |
| --- | --- |
| `src/pdfmd/`, `src/desktop/`, `src/renderer/` | Python engine, Electron host and renderer. [Architecture](docs/ARCHITECTURE.md#implementation-map-and-selected-dependencies) maps responsibilities. |
| `src/renderer/features/` | Document sessions, settings, receive progress, recovery and diagnostics, grouped by UI responsibility. |
| `tests/engine/`, `tests/desktop/`, `tests/fixtures/` | Engine tests by concern; separate desktop specs, Python fixtures, support harnesses and type checks; exact synthetic source PDFs. |
| `tools/dev/`, `tools/build/`, `tools/docs/`, `tools/runtime/` | Development launch/setup, Windows builds, documentation/source checks and the runtime OCR worker. Root manifests/lockfiles keep their tool-discovery locations. |
| `docs/` | Central INDEX, requirements, architecture, current state, phase plan and contract/development routes. |
| `docs/design/`, `docs/guides/` | Adopted topic rules/mechanisms and deeper engineering explanations. The guides label retained historical alternatives. |
| `docs/discussions/`, `docs/decisions/`, `docs/PROPOSED_CHANGES.md` | Attributed evolving positions, consequential choices/reasons, and unselected options with revisit conditions. |
| `docs/research/`, `docs/verification/`, `docs/reviews/` | Source-backed investigations, actual run/check records, and assessed findings/dispositions. A recorded result is not a new run. |
| `docs/history/` | Preserved editions and earlier stage records, with original scope, basis and historical authority explicit. |
| `docs/sources/` | Source inventories/coverage and original collections. A complete manifest indexes raw members; supplied instructions remain data. |
| `references/` | Ignored test PDF/example copies, separate from maintained documentation and not needed to understand development guidance. |
| `.local/`, `private/` | Ignored local analysis/evidence and private material. Local evidence may be important and is not disposable solely because it is ignored. |
| `workspaces/`, `outputs/` | Ignored task stores and user outputs. Preserve original inputs, drafts, images, consumption and task history. |
| `build/`, `out/`, `release/`, `test-results/` | Ignored generated artifacts/results. Inspect actual contents and provenance before any separately scoped cleanup; directory names do not prove disposability or current readiness. |
| `.venv/`, `node_modules/`, caches | Local environment/build dependencies; not source documentation and not moved by the documentation batch. |
| `.local/test-runs/<run>/` | New desktop-test evidence, profiles and screenshots; a separate `results/` child is owned by Playwright. Choose a new `PDFMD_TEST_RUN_ROOT` for a named run. |

The [documentation decision](docs/decisions/DOCUMENTATION.md#topic-ownership-and-version-correspondence-2026-10-31) explains ownership and maintenance. Keep current entries concise, place detailed checks once with their owner, and preserve links/status when facts change. No fixed file count or per-conversation document is required.

## Rebuild baseline

The detailed [workbench behavior and implementation overview](docs/DEVELOPMENT_GUIDE.md#workbench-behavior-and-implementation-overview) preserves the former README explanations, recovery distinctions and supporting links. Use it with current contracts and recorded validation; [CURRENT_STATE](docs/CURRENT_STATE.md) owns current readiness. The original `pdf-to-md-agent` repository remains unchanged.

## Document checks

With a working Python 3.9+ interpreter, run the following from this repository (or use that interpreter's full path):

    python tools/docs/check_docs.py
    python tools/docs/source_lookup.py EVT-1166

The first command checks documentation/image links, local source hashes and point/detail coverage. The second reads a bundled source without accessing an external export. They do not test an agent implementation or certify semantic completeness. [Current state](docs/CURRENT_STATE.md) records the actual review and its limits.

Application checks:

```powershell
.venv\Scripts\python.exe -m pytest
pnpm build
pnpm test:desktop
```

Desktop tests use local model or IPC fixtures and make no provider calls. Playwright gives each run a unique local result/evidence directory; [the storage policy](docs/ARTIFACT_STORAGE.md#test-executions) explains overrides and cleanup behavior. The continuation workflow uses a test-only scheduling hook to pause at a settled tool boundary before UI Stop. The ordinary workbench test accepts `PDFMD_PACKAGED_EXE` to test a built executable; the renderer-session and scheduling-hook tests target development code. Live Nexus calls require an explicit task and credential; they are not part of automated tests.

The public repository is [hereiam510/pdf-to-md-agent-2](https://github.com/hereiam510/pdf-to-md-agent-2). Local build artifacts and private configuration are excluded from Git. No GitHub application release has been published.
