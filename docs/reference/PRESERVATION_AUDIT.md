# Preservation and self-containment audit

Updated 2026-10-23, Asia/Hong_Kong. This records documentation scope, technical-detail review and local availability. It does not certify an implemented application. The original repository and supplied export were not modified.

## What was preserved

| Check | Result and scope |
| --- | --- |
| Initial supplied-export integrity | All 5,222 listed files matched recorded byte sizes and SHA-256 during the initial 2026-10-22 review |
| Visible conversation | All 207 user/assistant messages accounted for: 47 user, 48 final assistant records, 112 commentary records |
| Local discussion copies | Those 207 messages plus the inherited handoff: 208 exact event JSON records and readable text views |
| Attachments | All 30 exact attachments bundled: 28 pasted-text files and two forum HTML files stored as inert text |
| Forum figures | All 14 ATT-01 research illustrations and all 10 ATT-02 substantive image pages retain original decoded WebP bytes. Offline readers are local. |
| Continuing requirements | Relevant SUP-01/02 verbatim excerpt ranges include source and excerpt hashes. The rebuild does not import old active documents/defaults/permissions. |
| Historical engineering details | SUP-03–07 retain selected facts about reference inputs, tools, export filenames and a source-spelling correction. Maintained explanations distinguish history from requirements. |
| Later requests | LIVE-01 through LIVE-09 preserved locally, including self-containment, technical detail and direct-conversation review |
| Point ledger | 325 entries. These include 102 foundations, 116 context/state and 65 delivery/recovery points. Another 29 map owners/scope, and 13 restore historical details. |
| Source dispositions | 254 sources. Of these, 251 map to retained points. One saved final message is empty, and two messages concern export administration. No classification remains unresolved. |
| Development-detail map | All 325 point IDs mapped: 253 explained, 54 historical references, 18 scope notes |
| Bundled-file integrity | 482 files registered with local hashes and a separate versioned bundle manifest. Verification scope appears below. |

The [point ledger](POINT_COVERAGE.json), [detail map](DEVELOPMENT_COVERAGE.json), [source dispositions](SOURCE_COVERAGE.json) and [source index](SOURCE_INDEX.md) serve different purposes. Counts are not independent feature counts: some owner mappings overlap the detailed records, and a point can contain several connected nuances. A source ID alone is not an adequate technical explanation.

## Technical explanations, not just an archive

The first repository version made original-byte lookup depend on the separate export and summarized some mechanisms too briefly. The user's subsequent clarification required a self-contained development handoff. The revised documents explain the mechanisms directly:

- [Development guide](../DEVELOPMENT_GUIDE.md): shared vocabulary, ownership, an end-to-end example, cross-module constraints and the exact remaining choices.
- [Integration and model boundary](../design/INTEGRATION_AND_MODEL_BOUNDARY.md): Nexus subscription routing, native protocol/adapter/capture boundaries, framework tradeoffs, discovery, configuration and desktop/Python integration.
- [Context and evidence](../design/CONTEXT_AND_EVIDENCE.md): evidence forms and locators, policy settlement, transient hydration, native projections, whole-request capacity, rolling compaction, handoff/notes/restart, caching, scripts and review applicability.
- [Document engine](../design/DOCUMENT_ENGINE.md): source/candidate/version/operation distinctions, retention and validation order, exact reuse, edits/maps, provenance, immutable-file/SQLite visibility and whole-document rendering.
- [Execution and delivery](../design/EXECUTION_AND_DELIVERY.md): request/attempt/batch/receipt identities, complete batch settlement, durable limits, recovery, cancellation/wait/stop, process progress and explicit-version publication.

The three detailed reference records were expanded with definitions, causal examples and historical corrections. Previously discussed alternatives remain available with status. They do not become current requirements. The optional local transcript/attachments support exact-wording audit, while the development explanations stand on their own.

## Source-aware authorship and independent reading

The initial review assigned complete discussion ranges and attachments to three agents: foundations EVT-0002–0414 and ATT-01–06, context/state EVT-0415–0826 and ATT-07–20, delivery/recovery EVT-0827–1168 and ATT-21–30. They also read the controlling final consolidation and cross-reviewed effective owners. The inherited handoff and substantive forum text/images were included.

For the self-contained revision, three continuing reviewers audited all 102/116/65 preserved points against the technical guides and relevant local original sources. They wrote missing explanations and per-point detail maps. Independent reviewers read only repository files. They checked the context guide against document/execution boundaries and the integration guide against execution/document boundaries. They also checked the main entrypoints as a developer without the original export. Root integrated the owners, vocabulary, provenance, source utilities and verification.

Material corrections and additions included:

- Rolling compaction, handoff content, note-version races, failures/restarts, computation reuse and script boundaries that the interrupted context draft had not yet developed.
- Envelope/schema checks, candidate-reference resolution and full-result validation as distinct stages, with useful content retained first.
- Resolve omitted defaults at their defined sequential operation boundary. Batch acceptance must not accidentally bind a later dependent read to the pre-edit version.
- Task-scoped delivery selection, atomic registration of actual adoption links, and separate export build/verify/directory/ZIP re-entry outcomes.
- Malformed tool-argument JSON may bypass ordinary ToolNode dispatch, while successfully decoded domain/schema-invalid arguments need the common pre-validation capture path. These failures are not the same.
- An accepted complete native reply can contain calls that later fail domain validation. Every batch member still needs a recorded success/rejection/failure outcome before continuation.
- A model-input projection is assembled input, not proof that a send occurred. Attempt records establish dispatch.
- The small Graph State policy, single settlement writer, original receipts and external durable budgets remain consistent across all guides. The superseded external policy-version/activation machinery remains clearly historical.

These reviews found and corrected specific issues. However, the later review of `e243431` found omissions in mechanisms condensed into broad points. These omissions included technical names, field relationships, call ordering and original counterexamples. The earlier absence of a reported gap was not proof that every detail was explained. [TECHNICAL_DETAIL_REVIEW](TECHNICAL_DETAIL_REVIEW.md) records those concrete deficiencies and their repairs. The core architecture and Q1–Q3 did not change.

That later review also used the actual conversation directly: 205 overlapping discussion messages matched the preserved source text exactly. Two administrative export messages were on the export branch rather than the current chat, and EVT-0258 remained empty. Reviewers rotated source ranges and derived candidate details from originals rather than accepting the existing point list as exhaustive. A lexical scan helped locate lost names, but its sample IDs, old paths and aliases were not counted as missing mechanisms. [TECHNICAL_TERMS](../TECHNICAL_TERMS.md) now provides navigation by original terminology.

## Language review and comparison with original meaning

The 2026-10-23 language review used the ASD-STE100 skill, version 0.4.0, against the wording at `ff058bd`. Its scope covered 21 maintained Markdown files, prose fields in four JSON records, two utilities' messages, and one Git-ignore comment. Copied source files were outside the rewrite scope.

The changes split long sentences, named relevant actors, separated conditions and corrected list boundaries. The review covered the 20-word instruction limit, 25-word description limit, paragraph length, active voice and consistent terminology. Technical names, numeric examples, code, quoted wording and requirement status remained protected. These writing rules did not authorize shorter explanations that lost a condition or technical distinction.

After editing, three reviewers compared their assigned technical guides and detailed records with the baseline and relevant original messages/attachments. They also independently checked shared owner documents. Root compared the shared-owner changes with the original agreements, later corrections and final consolidation. Root additionally checked lexical changes, obligations, references, metadata structure and preserved payloads. Matching words, source IDs or hashes supplemented this reading but did not prove equivalent meaning.

The comparison caught and corrected wording risks before completion:

- Same-request replay must reuse already frozen input. Wording about freezing input during replay could imply a new selection.
- Exact candidate reuse must not require retransmitting a long body. It does not prohibit optional retransmission.
- An assembled input view records selected content. Attempt records separately establish dispatch.
- Logit masking suppresses disallowed choices. It does not suppress the choices that remain permitted.
- Recommendations retained their original strength. The review restored affected qualifiers and the repository-wide unimplemented/unverified status.
- Quoted examples retained their original spelling, including punctuation and capitalization. Missing paragraph breaks after lists were corrected.

The unfiltered linter still reports retained quotations and domain-dependent matches. Schema validation, byte verification, human confirmation, context removal and file deletion denote different operations. Process launch, task start and process termination also have different scopes. Passive status descriptions remain where the actor is irrelevant or unspecified. Some apparent verb matches are adjectives or labels, such as fixed input or an HTTP method.

These are reviewed exceptions, not a zero-warning result. The review does not claim official dictionary verification or formal ASD conformity. No architecture decision or Q1–Q3 closure follows from the language edits. No remaining material meaning change was identified in the reviewed passages. The structural and source checks below establish separate, narrower facts.

## Repository-only verification

A clean copy was made from the Git index, containing only intended versioned files: no Git metadata, private scratch, old checkout or external export. A separate Python 3.12.14 runtime outside both repositories ran the checks with isolated mode and bytecode writing disabled. A Python file-open audit hook denied access outside that copy and the interpreter runtime.

The copy passed:

- Documentation and image links, anchors, source IDs, all retained point/detail mappings and source dispositions.
- Hash/size verification of all 482 bundled files, including exact event/attachment identity checks and the 24 figures.
- Local lookup for inherited/empty/final messages, text/forum attachments, all seven supporting excerpts and a later human request.
- Exact event-JSON reading, offline forum-reader routing and local later-request reading.
- A negative check: a modified copied source was refused on hash mismatch, then the test copy was restored.
- Syntax parsing of the two standard-library utilities.

The public checks are repeatable with a working Python 3.9+ interpreter from this repository or an ordinary checkout copy:

    python tools/check_docs.py
    python tools/source_lookup.py EVT-1166 --verify-only
    python tools/source_lookup.py ATT-01
    python tools/source_lookup.py SUP-02
    python tools/source_lookup.py LIVE-07

Default lookup never infers an external export directory. The explicit --export option is optional provenance auditing only. The lookup inventory includes locally available discussion/design sources. It excludes uncited incidental tool-execution records, which would leave unresolved external paths in the lookup set.

Whitespace checks cover maintained documentation and utilities. Whitespace cleanup excludes exact historical source files. Hashes and Git attributes protect original CRLF, Markdown hard-break spaces and other source formatting. The check does not normalize those bytes. The checks required no dependency installation, global setting change or live provider request.

<a id="verified-historical-detail-gaps"></a>
## Verified historical-detail gaps

The later attachment review compared four claimed omission areas with the repository at `8f5e7e6`. The user authorized filling confirmed gaps. Three reviewers checked distinct source areas, wrote scoped additions and cross-reviewed another area. Root integrated navigation, selected source excerpts, coverage records and wording.

The review found real omissions in maintained explanations. Some underlying facts already existed in local sources. The page-comment examples, for example, were already in SUP-01. The review did not establish the critique's claim of complete core coverage or its proposed “100%” completeness conclusion.

| Area | Restored explanation and evidence boundary |
| --- | --- |
| Page comments and package layout | Preserve the three syntax examples and historical export filenames. Exact grammar and final names remain Q1/Q3 choices. Assets mean referenced files, without a mandatory empty ZIP directory. |
| Five reference packages | Preserve identities, input conditions, example defects, absent linked artwork and the repeated-glyph correction. The actual PDFs and example outputs are not bundled or newly validated. |
| OCR and image handling | Explain local language identity, initialization diagnostics, per-page timeout and completed-page retention. Preserve RGB/JPEG pitfalls without pinning old versions or imposing OCR. |
| Preview resources | Separate saved Markdown/comments from sanitized display. Explain historical local-byte routing and external-resource blocking. Electron behavior remains unverified. |
| Desktop packaging | Preserve Forge and PyInstaller rationale as historical directions. The earlier Vite status is not a current status claim. |
| Credentials and scripts | Explain optional plaintext files, ignored configuration, process-environment and hidden-input routes. Environment filtering does not encrypt files or create a sandbox. |

The review corrected two overgeneralizations about the medical inputs. Adobe OCR preprocessing is user-confirmed for both supplied medical PDFs. The 446-span `GlyphLessFont` observation concerns Nursing physical page 12 only. It does not describe every page of both inputs.

SUP-03–07 contain selected verbatim evidence with full-source and excerpt hashes. Their source snapshots match the supplied export and old commit `182ea39b31829edf6491a72472004b1cd1068897`. SUP-06 is inert code text for filenames and ZIP membership. SUP-07 selects only the correction sentences within one evidence paragraph. This review imported no complete old development document, executable module or work ledger.

The additions use the same ASD-STE100 clarity rules as the earlier language review. Reviewers compared new statements with original source wording after editing. They preserved historical qualifiers, example status, source scope and open contracts. These checks do not claim official dictionary certification or semantic completeness.

The per-file language scan reported four vocabulary overlaps and two passive descriptions in added text. These describe different operations or leave an irrelevant actor unnamed. No new sentence-length violation remained.

After integration, the repository-only copy passed 19 checks. These included all five new source lookups with outside file access denied. The documentation check covered 25 Markdown files, 482 bundled files and all 325 point/detail mappings. All 476 prior source payloads remained byte-identical. Only their navigation index changed.

A fresh comparison preserved the old repository's HEAD, status and all 103 tracked or nonignored file hashes. The user's untracked `docs_bundle.txt` also remained unchanged and outside the commit. These checks did not inspect ignored runtime trees or prove application behavior.

No new PDF inspection, OCR run, provider call, dependency installation or current upstream compatibility survey occurred. The work restores documented lessons and their limits. The [reference-input note](REFERENCE_INPUTS.md) and technical guides explain those lessons without requiring the old checkout or conversation export.

## Original-project boundary and remaining limits

The comparison against the old repository's initial baseline found these results:

- HEAD and porcelain status remained unchanged.
- All 103 tracked/nonignored-untracked file hashes remained unchanged.
- No nonignored file was added.

Its pre-existing uncommitted work remains intact. Ignored runtime trees are outside that hash comparison and were not intentionally modified. The initial review reused an old Python interpreter read-only. The portable verification uses an independent interpreter.

The supplied large export remains untouched. The source copies required here are now local. Historical paths inside verbatim messages do not create a development dependency. No old application code, private configuration, run workspace or closed-job ledger became an active owner. This gap review made no remote publication, app implementation, Nexus generation/probe, PDF conversion, benchmark or installer verification.

EVT-0258's saved final body is empty, some forum screenshots clip text/code, and the original export records missing incidental assets and five unreconstructible old document revisions. These source limits are disclosed, not filled with invented text. They do not represent missing pasted-text attachments or a requirement to consult the original export for the documented design.

[Q1–Q3](../OPEN_QUESTIONS.md) remain intentionally open executable contracts. Unselected schema names, thresholds, dependency versions and implementation choices are distinguished from previously discussed technical detail. The repository preserves and explains the latter without falsely deciding the former.
