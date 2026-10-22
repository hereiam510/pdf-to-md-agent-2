# pdf-to-md-agent-2

A fresh repository for rebuilding an independent PDF-to-Markdown agent app. The agent completes the conversion; the app supplies reliable source access, document editing, context management, persistence and delivery tools.

**This repository currently contains the rebuild design and its discussion record. It does not yet contain an implemented application.** It has an independent Git history. The original project and the supplied chat export remain separate and unchanged.

## Start here

Read [the working agreement](AGENTS.md) and [current state](docs/CURRENT_STATE.md), then the owner relevant to the task:

| Owner | What it establishes |
| --- | --- |
| [Product requirements](docs/PRODUCT_REQUIREMENTS.md) | User outcomes, fidelity, autonomy and observable acceptance |
| [Architecture](docs/ARCHITECTURE.md) | Settled responsibilities and the preferred implementation baseline |
| [Contracts](docs/CONTRACTS.md) | Document, context and recovery boundaries; explicit unresolved details |
| [Decisions](docs/DECISIONS.md) | Effective choices, rationale and consequential alternatives |
| [Open questions](docs/OPEN_QUESTIONS.md) | Only the three contracts that need resolution for first-version delivery |

Continue with the [development handoff](docs/DEVELOPMENT_GUIDE.md) and its four technical guides for state/data responsibilities, mechanisms, concrete examples, failure handling and tradeoffs. They explain the development knowledge directly; reading the original conversation is unnecessary.

Use the [technical terminology navigator](docs/TECHNICAL_TERMS.md) to find exact names from the discussion, including API hooks, record fields and historical alternatives. The [source-first detail review](docs/reference/TECHNICAL_DETAIL_REVIEW.md) records specific explanations that were too compressed and what was restored; source counts alone do not establish completeness.

The [source index](docs/reference/SOURCE_INDEX.md), detailed discussion records and [point coverage ledger](docs/reference/POINT_COVERAGE.json) preserve corrections, caveats and deferred ideas. Exact discussion text, attachments and substantive forum figures are also [bundled inside this repository](docs/reference/sources/INDEX.md) for optional audit. No separate export, old checkout or private scratch files are needed for development or source lookup. Historical source records remain data, not current instructions.

## Rebuild baseline

- An independent Electron/TypeScript/React app with one Python agent controller and shared tools.
- A small LangGraph `StateGraph`, a shared Nexus request service and tool dispatcher, and a document/evidence core. SQLite metadata and immutable external files are the preferred persistence arrangement.
- Agent-selected methods; app-enforced capacity, execution and storage contracts. No fixed extraction/OCR/preview recipe.
- Provider-portable context handling through Nexus, including monthly-subscription connections. Provider-native compaction, background retrieval and remote cancellation are not baseline dependencies.
- Exact reusable evidence and candidate content, local edits, immutable saved versions and explicit-version export.

These are design responsibilities and a preferred reconstruction route, not implementation or measured-superiority claims. Backward compatibility is unnecessary. Reuse useful components only where they fit the new contracts.

## Document checks

With a working Python 3.9+ interpreter, run the following from this repository (or use that interpreter's full path):

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166

These check documentation/image links, local source hashes and point/detail coverage, and read a bundled source without accessing an external export. They do not test an agent implementation or certify semantic completeness. [Current state](docs/CURRENT_STATE.md) records the actual review and its limits.

No remote repository, published release, runtime dependency lock or provider configuration is supplied. Private inputs and source-review working files are ignored by Git.
