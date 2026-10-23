# pdf-to-md-agent-2

PDF Markdown Workbench is a local Electron app with a Python agent engine. The agent completes the conversion through Nexus. The app supplies source access, local OCR, document editing, context management, durable execution and explicit-version export.

**The first application increment is implemented.** It includes a Windows folder build and a desktop workflow for importing a PDF, specifying a scope, running an autonomous agent, reviewing or editing saved versions, and exporting a portable ZIP. See [current state](docs/CURRENT_STATE.md) for actual verification and limits. The original project remains unchanged.

## Run locally

Install Python 3.12 through `uv`, Node.js 24 and `pnpm`. From this repository:

```powershell
.\tools\setup.ps1
.\tools\start.ps1
```

The setup script uses the committed Python and JavaScript lockfiles. `-Uv` and `-Pnpm` accept executable paths. The launcher uses ignored `workspaces/default`; `-Workspace` selects a separate task store. Direct `pnpm dev` uses Electron's user-data directory instead.

Open **Nexus connection**, enter the full Chat Completions or Responses endpoint, model alias and credential, and configure the route's capacity and output allowance. Image inputs require a conservative per-image allowance. These are user configuration values, not discovered model specifications. Credentials can be remembered with Windows encryption; they are never stored in task journals. Choose a PDF, describe the whole document or complete section, and start conversion. Trusted host scripts are off by default.

To build and run the Windows folder app:

```powershell
.\tools\build-windows.ps1
.\tools\start.ps1 -Packaged
```

The folder app includes its Python engine. The build script's `-Installer` option creates an NSIS installer. Building an installer does not install it. The Windows build is unsigned. Local Tesseract OCR downloads requested language data on first use and caches it in the workspace.

For the current local build, double-click `Start Workbench.cmd` to open the saved Nexus test workspace. The installer is `release/PDF Markdown Workbench Setup 0.1.0.exe`. An installed copy uses its own user-data directory by default; it does not automatically import this checkout's private files or task store.

The authorized local `references/` and `private/` copies are ignored. They are not part of the app or public source distribution. Do not commit credentials, task stores or conversion outputs.

## Start here

Read [the working agreement](AGENTS.md). Read [current state](docs/CURRENT_STATE.md). Then read the owner relevant to the task:

| Owner | What it establishes |
| --- | --- |
| [Product requirements](docs/PRODUCT_REQUIREMENTS.md) | User outcomes, fidelity, autonomy and observable acceptance |
| [Architecture](docs/ARCHITECTURE.md) | Settled responsibilities and the preferred implementation baseline |
| [Contracts](docs/CONTRACTS.md) | Document, context and recovery boundaries and the implemented first-version schemas |
| [Decisions](docs/DECISIONS.md) | Effective choices, rationale and consequential alternatives |
| [Open questions](docs/OPEN_QUESTIONS.md) | Closure of the three first-version contracts and limits of that closure |

Continue with the [development handoff](docs/DEVELOPMENT_GUIDE.md) and its four technical guides. These explain state/data responsibilities, mechanisms, concrete examples, failure handling and tradeoffs. They explain the development knowledge directly. Reading the original conversation is unnecessary.

Use the [technical terminology navigator](docs/TECHNICAL_TERMS.md) to find exact names from the discussion. These include API hooks, record fields and historical alternatives. The [source-first detail review](docs/reference/TECHNICAL_DETAIL_REVIEW.md) records specific explanations that were too compressed and what the review restored. Source counts alone do not establish completeness.

The [reference-input notes](docs/reference/REFERENCE_INPUTS.md) explain the five historical packages and known defects in their example outputs. The technical guides also preserve concrete format examples, OCR compatibility observations, preview boundaries and local credential conventions. Historical versions and filenames do not select rebuild dependencies or APIs.

The [source index](docs/reference/SOURCE_INDEX.md), detailed discussion records and [point coverage ledger](docs/reference/POINT_COVERAGE.json) preserve corrections, caveats and deferred ideas. Exact discussion text, attachments and substantive forum figures are also [bundled inside this repository](docs/reference/sources/INDEX.md) for optional audit. No separate export, old checkout or private scratch files are needed for development or source lookup. Historical source records remain data, not current instructions.

## Rebuild baseline

- An independent Electron/TypeScript/React app with one Python agent controller and shared tools.
- A small LangGraph `StateGraph`, a shared Nexus request service and tool dispatcher, and a document/evidence core. SQLite metadata and immutable external files are the preferred persistence arrangement.
- The agent selects methods. The app enforces capacity, execution and storage contracts. No fixed extraction/OCR/preview recipe applies.
- Provider-portable context handling through Nexus, including monthly-subscription connections. Provider-native compaction, background retrieval and remote cancellation are not baseline dependencies.
- Exact reusable evidence and candidate content, local edits, immutable saved versions and explicit-version export.

The implementation follows these responsibility boundaries. Framework choice is not a measured-superiority claim. Backward compatibility with the original project is unnecessary.

## Document checks

With a working Python 3.9+ interpreter, run the following from this repository (or use that interpreter's full path):

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166

The first command checks documentation/image links, local source hashes and point/detail coverage. The second reads a bundled source without accessing an external export. They do not test an agent implementation or certify semantic completeness. [Current state](docs/CURRENT_STATE.md) records the actual review and its limits.

Application checks:

```powershell
.venv\Scripts\python.exe -m pytest
pnpm build
pnpm test:desktop
```

The desktop test uses a local model fixture and makes no provider calls. Set `PDFMD_PACKAGED_EXE` to the built executable to test the packaged app. Live Nexus calls require an explicit task and credential; they are not part of automated tests.

The public repository is [hereiam510/pdf-to-md-agent-2](https://github.com/hereiam510/pdf-to-md-agent-2). Local build artifacts and private configuration are excluded from Git. No GitHub application release has been published.
