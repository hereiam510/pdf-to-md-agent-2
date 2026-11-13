# pdf-to-md-agent-2

PDF Markdown Workbench is a local Electron app with a Python agent engine. The agent completes the conversion through Nexus. The app supplies source access, local OCR, document editing, context management, durable execution and explicit-version export.

**[Start development](docs/INDEX.md#start-by-task):** choose a reading route for the requested task. [CURRENT_STATE](docs/CURRENT_STATE.md) locates unfinished discussion or work; [PHASE_PLAN](docs/PHASE_PLAN.md#readiness-and-evidence) assesses product-stage readiness. Use the linked verification owners before treating a development build or installer as verified delivery.

For day-to-day work, follow the [development routine](AGENTS.md#daily-development-and-document-maintenance) and [batch catalogue](docs/INDEX.md#batch-documents). Each batch separates scope, local tickets and verification; affected documentation is maintained as part of delivery.

## Run locally

Install Python 3.12 through `uv`, Node.js 24 and `pnpm`. From this repository:

```powershell
.\tools\dev\setup.ps1
.\tools\dev\start.ps1
```

The setup script uses the committed Python and JavaScript lockfiles. `-Uv` and `-Pnpm` accept executable paths. The launcher uses ignored `workspaces/default`; `-Workspace` selects a separate task store. Direct `pnpm dev` uses Electron's user-data directory instead.

Development launches automatically read the ignored `private/api-key.txt` when present. The file contains one UTF-8 credential; its value stays in app memory unless you explicitly choose to remember it in Connection settings. This applies across development workspaces and tasks. Use `tools/dev/start.ps1 -CredentialFile <path>` for another file, or `-NoCredentialFile` for manual entry. Packaged apps do not load development credential files. See [credential loading](docs/design/DEVELOPMENT_CREDENTIALS.md#development-credential-file-loading) for precedence, errors and controls.

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

The saved-version view reports asset-reference incompleteness separately from the agent's content claim and ZIP byte verification. Historical omissions remain inspectable and exactly exportable. **Return to document** restores the loaded snapshot after image viewing or a blocked navigation. The [reference and preview implementation](docs/guides/DOCUMENT_ENGINE.md#shared-asset-reference-interpretation-and-selected-version-view) explains snapshot-scoped resources and selection guards. The [preview contract](docs/design/ASSET_REFERENCES.md#preview-binding-and-return-behavior) preserves full selected bytes and sandbox isolation. The [Windows verification](docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t5-r-windows-rerun-after-the-windows-naming-repair) records the tested builds and the [shared-original repair](docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t5-offline-repair-for-ar-t5-16).

## Start here

Read [the working agreement](AGENTS.md), then **[the document catalogue](docs/INDEX.md)**. It provides topic routes and a complete categorized inventory. Use [CURRENT_STATE](docs/CURRENT_STATE.md) for actual implementation/verification and the next decision, [the phase plan](docs/PHASE_PLAN.md#delivery-route) for product outcomes, and [the handoff](docs/CURRENT_STATE.md#focus-and-resume-route) for source/check boundaries. Historical run permissions are not present execution authority.

The catalogue leads directly to current streaming receive, document editing, context coordination, recovery and diagnostic designs, their reasons and original decision/discussion entries, applicable verification and preserved editions. [CONTRACTS](docs/INDEX.md#initial-contract-basis) is the shared-rule navigator; [DEVELOPMENT_GUIDE](docs/DEVELOPMENT_GUIDE.md) routes deeper engineering explanations.

## Repository map

[Project layout](docs/guides/PROJECT_LAYOUT.md) maps engine modules, renderer features, test groups and utility entry points. [Artifact storage](docs/ARTIFACT_STORAGE.md) defines authoritative/private copies, per-run results, packaging boundaries and retention.

Keep maintained source, private task data and generated evidence in their declared locations. The layout and storage owners above define the paths, consumers and retention boundaries; [INDEX](docs/INDEX.md) supplies the document catalogue.

## Rebuild baseline

The detailed [workbench behavior and implementation overview](docs/DEVELOPMENT_GUIDE.md#workbench-behavior-and-implementation-overview) preserves the former README explanations, recovery distinctions and supporting links. Use it with current contracts and recorded validation; [PHASE_PLAN](docs/PHASE_PLAN.md#readiness-and-evidence) owns phase readiness. The original `pdf-to-md-agent` repository remains unchanged.

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
