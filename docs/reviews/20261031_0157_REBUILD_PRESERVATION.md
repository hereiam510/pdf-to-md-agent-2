> Filing/recording time: 2026-10-31 01:57 UTC+08:00. This relocated record retains the investigation/audit dates and results stated below; its filename does not identify a new research or test run. An original event minute not stated below is unknown.

# Preservation and self-containment audit

Updated 2026-10-23, Asia/Hong_Kong. This records documentation scope, technical-detail review and local availability. It does not certify an implemented application. The original repository and supplied export were not modified.

## What was preserved

| Check | Result and scope |
| --- | --- |
| Initial supplied-export integrity | All 5,222 listed files matched recorded byte sizes and SHA-256 during the initial 2026-10-22 review |
| Visible conversation | All 207 user/assistant messages accounted for: 47 user, 48 final assistant records, 112 commentary records |
| Local discussion copies | Those 207 messages plus the inherited handoff: 208 exact event JSON records and readable text views |
| Attachments | All 30 original attachments retain exact bytes. ATT-31 adds an exact excerpt from a separately supplied document. |
| Forum figures | All 14 ATT-01 research illustrations and all 10 ATT-02 substantive image pages retain original decoded WebP bytes. Offline readers are local. |
| Continuing requirements | Relevant SUP-01/02 verbatim excerpt ranges include source and excerpt hashes. The rebuild does not import old active documents/defaults/permissions. |
| Historical engineering details | SUP-03–27 retain selected input, tool, protocol, export and lifecycle facts. Maintained explanations distinguish history, later corrections and current requirements. |
| Later requests | LIVE-01 through LIVE-09 preserved locally, including self-containment, technical detail and direct-conversation review |
| Point ledger | 356 entries. These include 102 foundations, 116 context/state and 65 delivery/recovery points. Another 29 map owners/scope, and 44 preserve additional details. |
| Source dispositions | 275 sources. Of these, 272 map to retained points. One saved final message is empty, and two messages concern export administration. No classification remains unresolved. |
| Development-detail map | All 356 point IDs mapped: 256 explained, 82 historical references, 18 scope notes |
| Bundled-file integrity | 503 files registered with local hashes and a separate versioned bundle manifest. Verification scope appears below. |

The [point ledger](../sources/POINT_COVERAGE.json), [detail map](../sources/DEVELOPMENT_COVERAGE.json), [source dispositions](../sources/SOURCE_COVERAGE.json) and [source index](../sources/INDEX.md) serve different purposes. Counts are not independent feature counts: some owner mappings overlap the detailed records, and a point can contain several connected nuances. A source ID alone is not an adequate technical explanation.

## Technical explanations, not just an archive

The first repository version made original-byte lookup depend on the separate export and summarized some mechanisms too briefly. The user's subsequent clarification required a self-contained development handoff. The revised documents explain the mechanisms directly:

- [Development guide](../DEVELOPMENT_GUIDE.md): shared vocabulary, ownership, an end-to-end example, cross-module constraints and the exact remaining choices.
- [Integration and model boundary](../guides/INTEGRATION_AND_MODEL_BOUNDARY.md): Nexus subscription routing, native protocol/adapter/capture boundaries, framework tradeoffs, discovery, configuration and desktop/Python integration.
- [Context and evidence](../guides/CONTEXT_AND_EVIDENCE.md): evidence forms and locators, policy settlement, transient hydration, native projections, whole-request capacity, rolling compaction, handoff/notes/restart, caching, scripts and review applicability.
- [Document engine](../guides/DOCUMENT_ENGINE.md): source/candidate/version/operation distinctions, retention and validation order, exact reuse, edits/maps, provenance, immutable-file/SQLite visibility and whole-document rendering.
- [Execution and delivery](../guides/EXECUTION_AND_DELIVERY.md): request/attempt/batch/receipt identities, complete batch settlement, durable limits, recovery, cancellation/wait/stop, process progress and explicit-version publication.

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

These reviews found and corrected specific issues. However, the later review of `e243431` found omissions in mechanisms condensed into broad points. These omissions included technical names, field relationships, call ordering and original counterexamples. The earlier absence of a reported gap was not proof that every detail was explained. [TECHNICAL_DETAIL_REVIEW](20261031_0157_REBUILD_TECHNICAL_DETAILS.md) records those concrete deficiencies and their repairs. The core architecture and Q1–Q3 did not change.

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
- Hash/size verification of all 503 bundled files, including exact event/attachment identity checks and the 24 figures.
- Local lookup for inherited/empty/final messages, text/forum attachments, all 27 supporting excerpts and a later human request.
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

No new PDF inspection, OCR run, provider call, dependency installation or current upstream compatibility survey occurred. The work restores documented lessons and their limits. The [reference-input note](../sources/REFERENCE_INPUTS.md) and technical guides explain those lessons without requiring the old checkout or conversation export.

<a id="seven-detail-review"></a>
## Seven-detail review and corrected interpretations

The next review checked seven suggested omissions against `4125332`, original discussion and selected historical file snapshots. Three reviewers divided the source areas. The first six topics needed more concrete engineering explanations. The seventh already had a corrected contract elsewhere, but needed its example and correction beside rolling compaction.

| Suggested detail | Disposition |
| --- | --- |
| Stateless encrypted reasoning | Preserve the old `include` default and `store=False`. Current official Responses guidance does not require explicit inclusion. No official API statement verifies Nexus compatibility. |
| Safe error metadata | Explain allowlisted labels, decoded credential filtering and withheld-fragment metadata. Do not discard valid native frames merely because another frame contains an error. |
| Wire quirks | Preserve the actual `auto` to `default` metadata correction and scoped proxy conditions. These are not proof of a current SDK defect or remote settlement. |
| Windows replacement errors | Preserve the old retry allowlist. Error 1176 depends on the backup argument. Error 1175 does not guarantee full rollback or eventual success. |
| Playwright cancellation | Preserve worker ownership and waiting for active browser work and cleanup. Async support does not imply supported cancellation during an active API call. No browser-pipe diagnosis was established here. |
| Retry hierarchy | Preserve positive-automatic, queue-only and explicit-resume branches. Old numerical allowances are examples, not rebuild defaults. Resume never manufactures another allowance. |
| Unseen evidence | Preserve pending scope and immutable-manifest access. Reject invented summaries without requiring all originals or every evidence ID in every request. |

The review also checked two claimed supersessions. Fixed SQL drafts remain historical, while the selected responsibility boundaries remain intact. `produced_revision` and `preview_on_commit` clarify explicit version dependencies. Separate `commit_status` and `preview_status` do not make commit and preview one atomic effect.

The early attachment described a two-stage handshake, not necessarily two model turns. Later corrections rejected compulsory handoffs for every threshold crossing or evidence release. Rolling compaction and self-sufficient handoffs address related but distinct problems. The history does not prohibit every future handshake or dependency scheduler.

Some suggested event IDs did not identify the claimed supporting text in the supplied export. The review used actual file snapshots and exact source ranges instead. SUP-08–12 preserve those selected facts locally, including inert request-setting code and the `3301bf0` correction identity. Existing conversation and attachment bytes remain unchanged.

The official API and platform checks are dated 2026-10-23. The guides cite the OpenAI reasoning/streaming references, Microsoft `ReplaceFileW` reference and Playwright lifecycle guidance. These checks establish the stated documentation boundaries, not measured behavior of a Nexus route or the rebuilt app.

Three reviewers cross-checked the additions against other guides and relevant sources. The review corrected wording that could imply a global browser-lifecycle timeout. Source-aware reading preserved historical qualifiers, later corrections and open contracts. The changed-line language scan retained two passive descriptions with irrelevant actors. It found no new sentence-length violation. This does not establish formal ASD certification.

The repository-only copy passed 24 checks with outside source reads denied. It verified 25 Markdown files, 487 bundled files and all 333 point/detail mappings. All 481 prior source payloads remained byte-identical. Only their navigation index changed.

The five new support files contain 18 verified excerpt ranges or sentence spans. The old repository's HEAD, status and 103 tracked or nonignored file hashes remained unchanged. The user's untracked `docs_bundle.txt` remained unchanged and outside the commit.

No new provider request, conversion, dependency installation, benchmark or app implementation followed from this review. Q1–Q3 remain open. The work adds technical explanations and corrects overstrong wording within the existing architecture.

<a id="subsystem-detail-review"></a>
## Subsystem details and separately recovered source

The next review started at `ed13c4e`. The user identified two packaging concerns and twenty detail groups across five subsystems. Three reviewers inspected separate areas, wrote explanations and cross-reviewed another area. Root checked source identity, integrated provenance and compared changed wording with original records. Q1–Q3 and the architecture owners remain unchanged.

### Repository state and source identity

The user reported an older uploaded ZIP alongside a newer text bundle. At review start, local HEAD and remote `master` both identified `ed13c4e444075934b390a6584dc6f7ee644605c9`. That remote already included the 333-point review and SUP-08–12. No local `docs_bundle.txt` was present at that time. These observations establish repository state, not the identity of the user's earlier uploaded archive.

The separate `conversation 2.md` was available in the user-identified document collection. Lines 109–309 contain the missing first external response, including 8,631 characters. The review retained that exact excerpt as ATT-31 with the full-document and excerpt hashes. ATT-04 instead matches EVT-0349 after surrounding whitespace removal. This demonstrates duplicate exported content, without proving the clipboard's cause or reconstructing unseen chat events.

ATT-31 is not retroactively assigned to EVT-0350. It remains a separately recovered proposal. The [foundation reference](../history/discussions/20261031_0157_REBUILD_FOUNDATIONS.md#supplemental-first-response) explains its Node/Python ownership diagram, working-ledger sketch and five PoC cases. It also preserves later qualifications. The actual sketch uses `continued_table`, `from_pdf_page`, `header_columns` and `evidence_ref`. The field names quoted in the new audit differed from that passage.

### Restored mechanics and corrected claims

| Area | Preserved detail and important correction |
| --- | --- |
| Evidence selection | Separate roots for first-call structured values, raw MCP wrappers and preserved arguments. `arguments:true` addresses `/arguments`, not raw content blocks. |
| Native image restoration | `coverage.images[].raw_pointer` selects an individual image block for native input. Whole-record base64 text and descriptions provide no pixels. |
| Shape and ranges | `describe:true`, exact types/sizes, index paging and exclusive range ends. String offsets count Unicode code points, not UTF-8 bytes. |
| Released diagnostics | Recursive named-field copying and RFC 6901 escaping preserve selected diagnostics. Fields omitted before projection cannot reappear through this helper. |
| Coordinates | Unrotated top-left page points require crop, scale and rotation information. `bbox_pixels` and `bbox_pdf` belong to OCR word records. |
| Embedded images | Displayed xrefs, zero/unextractable references, mask checks and registered renders have distinct meanings. Mask rejection was app policy, not a universal library limitation. |
| OCR | Historical PSM choices, missing OSD data and one Node process per selected page. The below-80 warning counts individual low-confidence words. |
| Preview | Viewport/scroll settings and natural/display image sizes support reading checks. The 15-second setting does not bound every operation or cleanup. |
| CommonMark and language | CJK delimiter boundaries motivate optional safe `strong` elements. Document `language` affects HTML `lang`, without translating content or selecting OCR languages. |
| Historical schema | Content, page, block and saved-envelope fields retain their ownership. `metrics` is inside `content`. `unmapped_disposition` is a save argument. |
| Complete status | Nonempty uncertainties or unprocessed pages fail the historical structural check. Limitations and unknown printed labels do not independently trigger that check. |
| Recent draft arguments | Sliding Verbatim Window can avoid an immediate reread for a small edit. Fixed K and unconditional retention/cache guarantees remain rejected prescriptions. |
| Windows publication | Temporary-file flush/fsync precedes replacement. Separate read/write allowlists include different errors, with seven sleeps across at most eight attempts. |
| Scripts | Exact environment names, interpreter flags and timeout boundaries. Inline stdout and stderr each contain at most 16,000 bytes, with complete files retained separately. |
| Supervision and decoding | Job Object creation/handle limits and Pillow verification versus pixel loading remain distinct. Neither certifies complete, faithful requested work. |
| Provider configuration | Exact reserved keys and parsed URL guards prevent particular local overrides. They do not establish route compatibility. |
| Usage | Absent-key fallback differs from explicit null. Detail objects do not merge. Failed-attempt numeric filtering differs from the normalizer's raw usage object. |
| Backoff | Double-capped positive jitter, queue-only delay and Retry-After precedence retain original durable budgets. Waiting does not create more allowed attempts. |
| Error labels | HTTP-derived `stream_incomplete` and local `incomplete_stream` have different origins. Similar labels do not prove one cause or retry eligibility. |
| Fault relay | R1 rejects locally before upstream connection. R2 cuts after a qualifying complete frame and 64 accumulated Unicode alphanumeric characters. These are closed experiment mechanics. |

Current official checks qualified the historical Playwright launch note. The old code passed no launch timeout, while its guidance described 30 seconds. The checked current launch reference states 180000 milliseconds. The guide preserves both identities without inferring which historical dependency produced that default. It also distinguishes CommonMark syntax rules and PyMuPDF capabilities from old app policies.

SUP-13–27 preserve selected code and tool-contract ranges with full-source and excerpt hashes. They match the original repository's recorded Git commit. Available export workspace copies match those files byte-for-byte. Some files were absent from that export workspace subset. Their records identify the original Git snapshot as the source instead. No executable old module or closed-job permission becomes an active owner.

The source and point ledgers now contain 275 sources and 356 points. The 23 added points include three supplemental-proposal groups and twenty subsystem groups. These are navigation records, not independent features or proof that every possible detail is preserved.

The repository-only copy passed 40 checks with external source reads denied. The documentation check covered 25 Markdown files, 503 bundled files and all 356 point/detail mappings. It included local lookup of ATT-31 and every supporting excerpt. Source verification preserved all 486 prior source payloads byte-for-byte, apart from the separate navigation index. The 56 new supporting ranges match their recorded source and excerpt hashes.

Fourteen new supporting files match both the export workspace and the original Git snapshot. SUP-20 uses the original Git snapshot because the export workspace lacks `ocr/worker.cjs`. ATT-31's source-document and exact-range hashes also match. The old repository's HEAD, existing status and all 103 tracked or nonignored files remain unchanged. No provider call, conversion or runtime implementation occurred.

The wording review used ASD-STE100 clarity rules and source-aware cross-reading. It retained API-specific vocabulary and status descriptions where the actor was irrelevant. Counts and mechanical scans supplement semantic review rather than proving complete preservation. Fresh delivery archives and text bundles identify their source commit, so separately generated snapshots can be compared explicitly.

## Original-project boundary and remaining limits

The comparison against the old repository's initial baseline found these results:

- HEAD and porcelain status remained unchanged.
- All 103 tracked/nonignored-untracked file hashes remained unchanged.
- No nonignored file was added.

Its pre-existing uncommitted work remains intact. Ignored runtime trees are outside that hash comparison and were not intentionally modified. The initial review reused an old Python interpreter read-only. The portable verification uses an independent interpreter.

The supplied large export remains untouched. The source copies required here are now local. Historical paths inside verbatim messages do not create a development dependency. No old application code, private configuration, run workspace or closed-job ledger became an active owner. This gap review made no remote publication, app implementation, Nexus generation/probe, PDF conversion, benchmark or installer verification.

EVT-0258's saved final body is empty, some forum screenshots clip text/code, and the original export records missing incidental assets and five unreconstructible old document revisions. These source limits are disclosed, not filled with invented text. They do not represent missing pasted-text attachments or a requirement to consult the original export for the documented design.

[Q1–Q3](../decisions/INITIAL_CONTRACTS.md) remain intentionally open executable contracts. Unselected schema names, thresholds, dependency versions and implementation choices are distinguished from previously discussed technical detail. The repository preserves and explains the latter without falsely deciding the former.
