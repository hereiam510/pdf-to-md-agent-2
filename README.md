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

For an existing task, use **Task limits** while it is stopped to adjust total requests, active time, context capacity, output reserve or image allowance, then Continue. The task keeps consumed usage and pending requests. Connection settings remain defaults for unconfigured tasks. Recorded active time and any unmeasured interrupted intervals are displayed separately; see [the settings/time contract](docs/CONTRACTS.md#existing-task-settings-and-active-time-accounting).

Source tools use a common unrotated page-coordinate frame for extraction, rendering and OCR regions. Image delivery separates display assets from retained original image/mask streams; saved versions and ZIPs include provenance and the originals associated with their selected images. See [the PDF contract](docs/CONTRACTS.md#pdf-coordinates-and-image-delivery) and CURRENT_STATE for the tested rotation, CMYK, SMask and JPX cases and remaining limits. These source changes require the development launcher until a new Windows distribution is built.

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
| [Design options](docs/DESIGN_OPTIONS.md) | Candidate approaches, tradeoffs and conditions for later evaluation; not an implementation queue |
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

The response-correction increment continues automatically after a text-only reply or an invalid context handoff. Connection settings expose **Automatic response corrections** (default 2, zero disables), applied to new tasks. Corrections retain the original reply and share the task's request/time budget. Continuing an exhausted correction episode does not reset it; new user instructions or an edited document start a new episode. Explicit completion or questions use the agent's `report` tool. See [the execution contract](docs/CONTRACTS.md#q3-execution-recovery-and-delivery) for boundaries.

Document editing binds a draft to its loaded version and starting head. Historical versions offer **Rebuild from this version**; content added in later versions is excluded from that reconstruction. Failed loads cannot enable editing/export, and a save conflict retains the draft. The agent's `edit_document` uses ordinary edits by default, offers explicit autonomous reconstruction, and can insert/replace exact blocks from retained candidates. Export uses the selected loaded version, excluding unsaved edits. See [the document contract](docs/CONTRACTS.md#q1-document-schema-and-commit).

After Stop, adding instructions and pressing **Continue** preserves completed tool effects and marks obsolete, unstarted calls as unexecuted before the agent decides again. Continue without an amendment resumes the accepted batch. After an HTTP error or a rejected/truncated reply, Continue can prepare a new request using the latest task state, while retaining the failed record and consumed budgets. Unknown remote outcomes retain their original request and configured replay limit; unknown local effects still need reconciliation. Reopening alone does not send a request.

The current source includes all three editing/continuation batches, the context-capacity increment and follow-up phase 1. Oversized tool bodies receive explicit deferred receipts with exact read references; complete originals and full/raw/field/range access remain available. Pinned objects survive independently when their original history is compacted. Compaction keeps fitting objects within mixed-size batches and includes later material when a reference-only prefix offers no body reduction. A last-history handoff that still overflows normal input receives bounded correction while the old history remains active; useful partial reductions still apply with uncovered history. Genuinely oversized required pins stop explicitly. See [the context contract](docs/CONTRACTS.md#q2-context-transitions).

The phase-1 closeout recovers an already applied handoff after an interrupted checkpoint even when new instructions arrive. It preserves the original application receipt and consumed usage, then checks the latest input before continuing. An archived but unapplied candidate still needs validation. See [the closeout evidence](docs/CURRENT_STATE.md#phase-1-closeout-handoff-application-replay).

The Phase 3 closeout distinguishes stencil coverage from page appearance. The agent can inspect the component or select a page occurrence for a correctly painted display asset with original-stream provenance. Context pins now choose index, image, full/selected text or raw bytes explicitly. Admission happens before application; rejection preserves previous pins, releases and notes and lets the agent revise its choice. Full originals and precise reads remain available. See [the closeout evidence](docs/CURRENT_STATE.md#phase-3-closeout-stencil-appearance-and-pin-admission).

Existing Windows folder/installer artifacts still contain the earlier response-correction build; use the development launcher for this revision. [Reviewer handoff](docs/REVIEW_HANDOFF.md) maps the changes and review evidence. The three accepted follow-up phases and the Phase 3 closeout are implemented. [Current state](docs/CURRENT_STATE.md#review-follow-up-progress) records checks and limitations separately from plan acceptance and release.

History-pressure context updates are now retained as inactive proposals. The app compacts under the active policy and retries complete-input preflight before applying the composed update. The original receipt stays unchanged and a separate outcome reports application, rejection or supersession by new instructions. Saved proposals survive reopen without resetting budgets or changing frozen requests. See [the context contract](docs/CONTRACTS.md#q2-context-transitions) and [current evidence](docs/CURRENT_STATE.md#history-pressure-context-update-coordination).

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

Desktop tests use local model or IPC fixtures and make no provider calls. The continuation workflow uses a test-only scheduling hook to pause at a settled tool boundary before UI Stop. The ordinary workbench test accepts `PDFMD_PACKAGED_EXE` to test a built executable; the renderer-session and scheduling-hook tests target development code. Live Nexus calls require an explicit task and credential; they are not part of automated tests.

The public repository is [hereiam510/pdf-to-md-agent-2](https://github.com/hereiam510/pdf-to-md-agent-2). Local build artifacts and private configuration are excluded from Git. No GitHub application release has been published.

Context updates now distinguish saved pending intent from active policy and from final outcome delivery. Temporary capacity blocks retain valid proposals for Continue; committed outcomes checkpoint before the next input is built. Fitting updates need no compulsory compaction, and large updates cannot gain admission merely by deferring additional unselected evidence. Exact originals remain readable. See [current coordination evidence](docs/CURRENT_STATE.md#proposal-validity-admission-and-outcome-delivery).
