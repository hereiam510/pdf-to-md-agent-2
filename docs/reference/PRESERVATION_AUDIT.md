# Preservation and self-containment audit

Updated 2026-10-23, Asia/Hong_Kong. This records documentation scope, technical-detail review and local availability. It does not certify an implemented application. The original repository and supplied export were not modified.

## What was preserved

| Check | Result and scope |
| --- | --- |
| Initial supplied-export integrity | All 5,222 listed files matched recorded byte sizes and SHA-256 during the initial 2026-10-22 review |
| Visible conversation | All 207 user/assistant messages accounted for: 47 user, 48 final assistant records, 112 commentary records |
| Local discussion copies | Those 207 messages plus the inherited handoff: 208 exact event JSON records and readable text views |
| Attachments | All 30 exact attachments bundled: 28 pasted-text files and two forum HTML files stored as inert text |
| Forum figures | All 14 research illustrations in ATT-01 and all 10 substantive image pages in ATT-02 included as original decoded WebP bytes; offline readers are local |
| Continuing requirements | SUP-01/02 relevant verbatim excerpt ranges included, with source and excerpt hashes; old active documents/defaults/permissions are not imported |
| Later requests | LIVE-01 through LIVE-07 preserved locally, including self-containment and detailed technical explanation |
| Point ledger | 310 entries: 102 foundations, 116 context/state, 65 delivery/recovery, 27 effective-owner/scope mappings |
| Source dispositions | 247 sources: 244 mapped to retained points, one empty saved final message, two administrative export messages; no unresolved classification |
| Development-detail map | All 310 point IDs mapped: 247 explained, 47 historical references, 16 scope notes |
| Bundled-file integrity | 477 included files verified against local hashes, with a separate versioned bundle manifest |

The [point ledger](POINT_COVERAGE.json), [detail map](DEVELOPMENT_COVERAGE.json), [source dispositions](SOURCE_COVERAGE.json) and [source index](SOURCE_INDEX.md) serve different purposes. Counts are not independent feature counts: some owner mappings overlap the detailed records, and a point can contain several connected nuances. A source ID alone is not an adequate technical explanation.

## Technical explanations, not just an archive

The first repository version made original-byte lookup depend on the separate export and summarized some mechanisms too briefly. The user's subsequent clarification required a self-contained development handoff. The revised documents explain the mechanisms directly:

- [Development guide](../DEVELOPMENT_GUIDE.md): shared vocabulary, ownership, an end-to-end example, cross-module constraints and the exact remaining choices.
- [Integration and model boundary](../design/INTEGRATION_AND_MODEL_BOUNDARY.md): Nexus subscription routing, native protocol/adapter/capture boundaries, framework tradeoffs, discovery, configuration and desktop/Python integration.
- [Context and evidence](../design/CONTEXT_AND_EVIDENCE.md): evidence forms and locators, policy settlement, transient hydration, native projections, whole-request capacity, rolling compaction, handoff/notes/restart, caching, scripts and review applicability.
- [Document engine](../design/DOCUMENT_ENGINE.md): source/candidate/version/operation distinctions, retention and validation order, exact reuse, edits/maps, provenance, immutable-file/SQLite visibility and whole-document rendering.
- [Execution and delivery](../design/EXECUTION_AND_DELIVERY.md): request/attempt/batch/receipt identities, complete batch settlement, durable limits, recovery, cancellation/wait/stop, process progress and explicit-version publication.

The three detailed reference records were expanded with definitions, causal examples and historical corrections. Previously discussed alternatives remain available with status; they do not become current requirements. The optional local transcript/attachments support exact-wording audit, while the development explanations stand on their own.

## Source-aware authorship and independent reading

The initial review assigned complete discussion ranges and attachments to three agents: foundations EVT-0002–0414 and ATT-01–06, context/state EVT-0415–0826 and ATT-07–20, delivery/recovery EVT-0827–1168 and ATT-21–30. They also read the controlling final consolidation and cross-reviewed effective owners. The inherited handoff and substantive forum text/images were included.

For the self-contained revision, three continuing review roles audited all 102/116/65 preserved points against the technical guides and relevant local original sources. They wrote missing explanations and per-point detail maps. Independent repository-only reads checked the context guide against document/execution, the integration guide against execution/document boundaries, and the main entrypoints as a developer without the original export. Root integrated the owners, vocabulary, provenance, source utilities and verification.

Material corrections and additions included:

- Rolling compaction, handoff content, note-version races, failures/restarts, computation reuse and script boundaries that the interrupted context draft had not yet developed.
- Envelope/schema checks, candidate-reference resolution and full-result validation as distinct stages, with useful content retained first.
- Resolving omitted defaults at their defined sequential operation boundary; a batch's acceptance must not accidentally bind a later dependent read to the pre-edit version.
- Task-scoped delivery selection, atomic registration of actual adoption links, and separate export build/verify/directory/ZIP re-entry outcomes.
- Malformed tool-argument JSON may bypass ordinary ToolNode dispatch, while successfully decoded domain/schema-invalid arguments need the common pre-validation capture path. These failures are not the same.
- An accepted complete native reply can contain calls that later fail domain validation. Every batch member still needs a recorded success/rejection/failure outcome before continuation.
- A model-input projection is assembled input, not proof that a send occurred. Attempt records establish dispatch.
- The retained small Graph State policy/single settlement writer, original operation receipts and external durable budgets remain consistent across all guides; superseded external policy-version/activation machinery is clearly historical.

These reviews found and corrected specific issues rather than treating matching source counts as proof of semantic completeness. No known material cross-guide contradiction or unexplained development dependency remained in the reviewed scope. This is a bounded review result, not a mathematical guarantee that every interpretation is identical.

## Repository-only verification

A clean copy was made from the Git index, containing only intended versioned files: no Git metadata, private scratch, old checkout or external export. A separate Python 3.12.14 runtime outside both repositories ran the checks with isolated mode and bytecode writing disabled. A Python file-open audit hook denied access outside that copy and the interpreter runtime.

The copy passed:

- Documentation and image links, anchors, source IDs, all 310 point/detail mappings and all 247 source dispositions.
- Hash/size verification of all 477 bundled files, including exact event/attachment identity checks and the 24 figures.
- Local lookup for inherited/empty/final messages, text/forum attachments, both supporting excerpts and a later human request.
- Exact event-JSON reading, offline forum-reader routing and local later-request reading.
- A negative check: a modified copied source was refused on hash mismatch, then the test copy was restored.
- Syntax parsing of the two standard-library utilities.

The public checks are repeatable with a working Python 3.9+ interpreter from this repository or an ordinary checkout copy:

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166 --verify-only
    python tools/source_lookup.py ATT-01
    python tools/source_lookup.py SUP-02
    python tools/source_lookup.py LIVE-07

Default lookup never infers an external export directory. The explicit --export option is optional provenance auditing only. The lookup inventory includes the locally available discussion/design sources; uncited incidental tool-execution records are excluded rather than leaving unresolved external paths in the lookup set.

Whitespace checks cover maintained documentation and utilities. Exact historical source files are intentionally excluded from whitespace cleanup: original CRLF, Markdown hard-break spaces and other source formatting are protected by hashes and Git attributes. The check does not normalize those bytes. No dependency installation, global setting change or live provider request was needed.

## Original-project boundary and remaining limits

The old repository was compared against its initial baseline again: HEAD and porcelain status unchanged, all 103 tracked/nonignored-untracked file hashes unchanged, and no added nonignored file. Its pre-existing uncommitted work remains intact. Ignored runtime trees are outside that hash comparison and were not intentionally modified. The initial review reused an old Python interpreter read-only; the portable verification uses an independent interpreter.

The supplied large export remains untouched. The source copies required here are now local; historical paths inside verbatim messages do not create a development dependency. No old application code, private configuration, run workspace or closed-job ledger became an active owner. No remote publication, app implementation, Nexus generation/probe, PDF conversion, benchmark or installer verification was performed.

EVT-0258's saved final body is empty, some forum screenshots clip text/code, and the original export records missing incidental assets and five unreconstructible old document revisions. These source limits are disclosed, not filled with invented text. They do not represent missing pasted-text attachments or a requirement to consult the original export for the documented design.

[Q1–Q3](../OPEN_QUESTIONS.md) remain intentionally open executable contracts. Unselected schema names, thresholds, dependency versions and implementation choices are distinguished from previously discussed technical detail. The repository preserves and explains the latter without falsely deciding the former.
