> Entry snapshot captured 2026-10-31 01:57 UTC+08:00 (Asia/Singapore), before topic reorganization. Original owner: `docs/PRODUCT_REQUIREMENTS.md`. The filename is capture time, not adoption or execution time. Original text and source times are retained; relative links are adjusted and applicable shared-owner links target this captured edition. Earlier task permissions are historical. Earlier design identities not recorded by the source remain unknown. [Current catalogue](../../INDEX.md).

# Product requirements

Status: rebuild requirements, not implemented behavior. Recorded 2026-10-22, Asia/Hong_Kong. Sources: inherited product intent in EVT-0001, context agreements beginning EVT-0130, the final scope consolidation EVT-1148/1166, and the later repository-scoping decisions in [the source index](../../sources/INDEX.md).

## Outcome and product surface

The user supplies a PDF and an intended scope, which may be a whole document or a complete section crossing page boundaries. The app's own agent produces complete, readable, reusable Markdown and faithful source images with little manual handling. A smaller excerpt is useful only when it matches the requested scope or a declared verification exercise. It must not silently replace a complete requested section.

The destination is an independent Electron/TypeScript/React desktop app with a Python backend. It must run its own agent and use configurable model access through Nexus. It must not require the user to operate Codex or ChatGPT. Independent operation does not require an offline model. Desktop integration and a usable Windows distribution are part of an installable product, rather than evidence supplied by a headless tool demonstration.

Accept native, scanned and mixed PDFs without requiring manual preprocessing in another app. Routine page instructions, repair approvals, intermediate file transfers and manual package assembly should not be needed. An external-chat/local-tool surface remains useful alongside the independent app, through the shared core.

The installed product includes the runtimes it needs. Windows is the first validation environment. The recorded wider targets are Windows x86_64, macOS Apple Silicon and Debian x86_64. Intel Mac, CUDA and Apple Vision were outside that target. These preserved product intentions (SUP-01) do not make a full cross-platform/provider matrix a first-version prerequisite. Specific packaging and permissions remain implementation work.

The user uses Nexus as a connector for monthly subscriptions and may select providers/models such as DeepSeek, GLM or Qwen for cost reasons. Do not substitute a direct pay-as-you-go API as the assumed route. Support the selected route's actual native protocol and capabilities. A model alias or OpenAI-compatible endpoint does not establish all upstream features.

## Content fidelity

Preserve substantive wording, numbers, names, units, punctuation, symbols, meaningful emphasis, typographic distinctions and superscripts/subscripts. Preserve headings, paragraphs, lists, footnotes, substantive sidebars, reading order and cross-page relationships. Layout may be reorganized for reading: columns, physical line breaks, font choice and spacing need not reproduce the PDF exactly. Rewording, guessing or dropping difficult content must not be used to manufacture readability.

Pure decoration, repeated headers/footers and non-content color blocks can normally be omitted. Their omission alone does not require repairs, model calls or acceptance failure. Unique headings, warnings, substantive marginal material and uncertain meaningful content must be retained or explicitly accounted for.

Tables retain values, intentional blanks, headers, grouping, merged spans and their relationships. The representation need not be a simple Markdown pipe table or a predetermined internal schema. Diagrams retain complete relevant panels, captions and important searchable labels. Label transcription supplements the faithful source image.

Small differences such as `mg` versus `μg`, a missing negative, or a changed mathematical symbol can be substantive. Character similarity, geometric agreement, OCR confidence or a numeric mismatch threshold cannot certify semantic equivalence. Font metadata and OCR layers are evidence, not automatic truth about source emphasis or content.

Preserve source characters without blanket NFC normalization or text substitutions. Preserve original raw content when parsing or deriving views. Do not pretty-print/reflow embedded HTML in a way that changes meaning or whitespace. Any canonical serialization choice, including LF line endings, must have a single defined boundary. Do not confuse that choice with preserving original source bytes.

Do not silently fix apparent source errors or normalize Traditional/Simplified forms. Keep suggested corrections separate. Pixels can establish visible form without proving the original Unicode encoding. Use faithful transcription and explicit uncertainty rather than guessing or demanding unavailable encoding proof.

## Images and source coordinates

Keep the source PDF unchanged. When an embedded source image can be faithfully extracted, retain native dimensions and encoding. An existing JPEG is valid. Do not introduce lossy recompression. Faithful lossless crops and renders of vector/composite/scanned content are allowed with source/page/region/render provenance.

Do not white out, cosmetically clean, redraw, silently resize, reduce colors or lower bit depth. A PNG extension alone proves no fidelity. Native-pixel access must remain available. Diagnostic thumbnails and rendered document previews have separate identities and purposes.

Coordinates and bounding boxes need an explicit reference frame, page orientation and render transform. Rounding, tuple packing and abbreviated field names may affect model readability even when software can decode them exactly. Any compact representation must remain discoverable and reversible where it replaces a detailed view.

## Page identity and logical structure

Distinguish one-based physical PDF position from the printed label actually visible in the source. Viewer labels, bookmarks and inferred offsets are not evidence of the printed label. Preserve Roman labels. `none` means visibly absent. `unknown` means unconfirmed or unreadable.

Use English HTML comments for Markdown page markers. Account for every physical source page in the map, including unprocessed and outside-scope pages. Represent the requested section, which can start or end within a page. Markers must not split a coherent sentence, table or logical cross-page block simply to follow physical pagination.

Grouped ranges/lists must not imply that unused intervening pages contributed. Hidden Markdown comments and structured page metadata must agree. Free-text notes remain source-supported.

These retained [syntax examples](../../sources/rebuild/support/SUP-01.txt) illustrate English page comments. They do not define an exclusive grammar or finalize the Q1 serializer contract.

```html
<!-- PDF page: 1 | printed page: none | note: cover spread -->

<!-- PDF pages: 5-6 | printed pages: unknown | section: preface -->

<!-- PDF page: 7 | printed page: iii -->
```

Parse and render the assembled Markdown document as a whole so cross-block definitions and references can resolve. Per-block editing/storage may coexist with whole-document semantics. A parser feature such as footnote support must be checked for the selected renderer, not inferred from the word Markdown.

## Agent autonomy and source access

The agent chooses extraction, OCR, visual reads, scripts, checking and combinations of them, including re-OCR when a text layer exists but is damaged. PyMuPDF is a useful core capability, not the only permissible technique. The agent chooses page/region/DPI/language and how much of a paragraph, table, section or related page sequence to reconstruct.

Retain full first-call access, later full access, raw/field/range reads and actual native image pixels without a summary approval step. There is no universal text-first strategy, compulsory OCR/script/preview stage, fixed field subset, fixed edit size or arbitrary tool-call quota. Capacity constraints still apply to an individual model request. Full access does not promise that an arbitrarily large object fits in one request.

Compact views and indexes expose shape, size, locations, exact retrieval paths, warnings, omissions and coverage. Full underlying results remain available. Stored data is not necessarily seen, understood or remembered by the model. A path or base64 text is not proof that pixels reached a vision-capable request.

Trusted task scripts allow unforeseen legitimate filtering, joining, transformation, validation and reconstruction without adding a product tool for every PDF. They are process-opt-in/off by default, execute with host-user privileges, and are not an OS sandbox. Once enabled, routine per-script permission is unnecessary. Complete originals, intermediate files and logs survive bounded return text. Scripts do not automatically remove existing conversation history. Stronger isolation is a deferred deployment question.

## Durable useful work and delivery

Preserve received evidence and useful candidate content before validation can reject a write. Support exact content reuse and local correction without forcing regeneration of unchanged prose or metadata. Saving a candidate, committing a document version, source acceptance and publication remain separate facts.

Markdown, document JSON, safe HTML, assets and ZIP must refer to the same explicitly selected immutable version. They must use portable relative links. Export only the intended document and its required assets. Keep draft/partial status, unprocessed scope, technical failure and content uncertainty visible. A saved version can be exported independently of another model call or remaining model budget.

The agent must be able to reopen saved content and inspect real saved-output pixels where useful. A script success flag, saved path, manifest or rendered screenshot alone does not prove source fidelity. Known substantive errors or required unread scope must not be described as complete accepted work.

## Acceptance and cost

Check the complete declared scope against the source, including relationships, page identity, image fidelity and the actual saved/reopened/exported version. Use proportional software, offline and source-led checks. No universal review count, compulsory image audit, separate approval receipt or extra model-call ritual is required.

Examples and AI-produced reference Markdown are useful reading examples, not certified answers, a quality ceiling or a prescribed workflow. Source PDFs govern. A formal converter must not receive the matching-range answer, developer transcription or another comparison arm's output. Reviewers may use examples. Previously OCR-processed source files do not establish that the app performed the preprocessing.

The [historical reference-input notes](../../sources/REFERENCE_INPUTS.md) identify the five packages and their known limits. They explain lossy or edited example images, prior OCR, source-spelling corrections and unverified coverage claims. These records create no mandatory benchmark set.

Availability, invocation, execution, actual model input consumption, natural adoption, source quality and net benefit are distinct. Prescribed mechanism exercises do not establish natural adoption. Non-use alone establishes neither no need nor misunderstanding.

Optimize whole-task price-weighted cost while preserving fidelity, autonomy and complete access. Include normal input, cache reads/writes, output, context management, retrieval, re-generation, checking and recovery. Preserve unknown usage and fees. Do not double-count reasoning already included in output or cache categories with overlapping definitions. Only subtract cache reads/writes from input after verifying category semantics. Separate conversion cost from setup/development/review cost and successful-response subtotals from total job cost.

Characters, wire bytes, cumulative job input and per-request context are different quantities. Upstream identity, cache pricing and actual Nexus billing cannot be inferred from a model alias or direct-provider price sheet. Conditional sensitivity analysis is acceptable when assumptions are explicit. No guaranteed savings percentage, universal context waterline, whole-book/provider matrix or indefinite optimization program is an acceptance prerequisite.
