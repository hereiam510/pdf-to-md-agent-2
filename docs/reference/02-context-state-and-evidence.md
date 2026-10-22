# Context, state, and evidence: design reasoning and corrections

<a id="scope-and-status"></a>
## Scope, authority, and reading status

This is a **nonnormative reconstruction reference**, not an implementation specification, test backlog, or authorization to run models. It preserves the substantive reasoning in exported conversation events **EVT-0415–EVT-0826**, including the full inline attachments **ATT-07–ATT-20**. All 5,500 lines of the prepared segment were read, together with the later final consolidation. The raw export remains outside this repository. Event and attachment IDs resolve through [SOURCE_INDEX](SOURCE_INDEX.md) and [source-inventory.json](source-inventory.json). The consolidated [POINT_COVERAGE](POINT_COVERAGE.json) maps preserved points to stable anchors; prepared source packets are local review aids.

The segment repeatedly proposed Pi or LangChain `create_agent` with LangGraph persistence. **That is historical.** The later consolidated preference is a **small direct LangGraph `StateGraph`, a shared native Nexus request service/dispatcher, a document/evidence core, and SQLite short transactions with immutable files**. This is a priority design choice, not implemented functionality or proof of superiority. The final consolidation limits unresolved first-version work to three contracts: document editing and candidate references, context capacity and handoff, and persistence/recovery/stopping. Mechanisms below preserve knowledge for implementing those contracts; they do not reopen all the alternatives or make every mechanism mandatory.

Status terms used here distinguish **observed-v1** (facts reported about the original implementation or saved runs), **settled-boundary** (a product or correctness constraint retained through correction), **proposal** (an implementation option), **corrected-proposal** (a useful idea with an explicitly withdrawn guarantee), **superseded** (an older approach displaced by later decisions), and **hypothesis** (an unverified causal explanation or benefit). “Source” references to official APIs below describe what was checked in the conversation, at the stated versions; this review did not perform fresh web research or execute recorded commands.

<a id="p2-001"></a>
<!-- P2-001 | Authority and final consolidation | settled-boundary | EVT-0415,EVT-0826,EVT-1148,EVT-1166 -->
**P2-001 — Preserve the product outcome, not an accumulated mechanism list.** Complete reconstruction was repeatedly allowed. The app should make evidence easy to inspect, correct content easy to save and reuse, and long work possible to continue with little user handling. Existing code structure, a fixed number of modules/tables, framework names, and speculative guarantees are not outcomes. Later consolidation explicitly stops expansion: only an actual implementation or delivery blocker that violates an agreed contract justifies reopening that part of the design.

*Sources: EVT-0415, EVT-0826, EVT-1148, EVT-1166. Status: settled-boundary.*

<a id="source-map"></a>
## Source map

| Attachment | Introducing event | Main review reply | Distinct contribution |
|---|---|---|---|
| ATT-07 | EVT-0415 | EVT-0432 | Layout reduction, pre-admission, pins, CAS, runtime ownership |
| ATT-08 | EVT-0433 | EVT-0459 | Tuple encoding, staged capacity, framework comparison, verification carry-over |
| ATT-09 | EVT-0460 | EVT-0479 | Working Draft, P0–P3, semantic layout, manifest authority |
| ATT-10 | EVT-0480 | EVT-0507 | File import, Survey/Focus Decay, four-store reconciliation, seven-step scenario |
| ATT-11 | EVT-0508 | EVT-0534 | Stable prefix, hash deduplication, SQLite, evidence stubs, asset provenance |
| ATT-12 | EVT-0535 | EVT-0560 | Capacity contract, mechanical eviction, rollup map, timestamps, block identity |
| ATT-13 | EVT-0561 | EVT-0595 | Recovery context, activity ledger, route calibration, lazy acknowledgement |
| ATT-14 | EVT-0596 | EVT-0638 | Supersteps, assistant text, notes watermarks, delayed release, vision delegation |
| ATT-15 | EVT-0639 | EVT-0674 | Delivery tickets, input views, batch barriers, script attempts |
| ATT-16 | EVT-0675 | EVT-0701 | Input-to-response causality, hydration, process markers, complete tool replay |
| ATT-17 | EVT-0702 | EVT-0730 | Monotonic reducers, unhydrated references, frozen attempts, immutable notes |
| ATT-18 | EVT-0731 | EVT-0759 | Policy authority, cache overlap, capacity errors, salvage, framework resume |
| ATT-19 | EVT-0760 | EVT-0789 | Batched intents, computation/storage/selection, activation receipts, Windows sharing |
| ATT-20 | EVT-0790 | EVT-0826 | Product priorities, candidate reuse, visual comparison, episodes, Nexus extraction |

<a id="observed-evidence-and-causality"></a>
## Observed evidence and limits on causal claims

<a id="p2-002"></a>
<!-- P2-002 | Inspect size and span evidence | observed-v1 | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-002 — The measured layout was large, but the original explanation was overstated.** The first `inspect` in run `bdc032cac806419b9612c40927dbcf99` produced 191,662 characters: `layout` alone 147,366, `words` about 39,324, and top-level `text` about 3,034. The page had 41 blocks and 446 spans, not confirmed thousands. Removing `words` alone cannot turn that response into a few thousand characters. Dividing layout length by 446 includes block/line overhead; removing separate top-level `text` cannot shrink the independently measured layout. Adobe OCR fragmentation, an 80% node reduction, half the coordinate characters, or a usual 10–15-style ceiling were hypotheses, not measured explanations or savings.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: observed-v1.*

<a id="p2-003"></a>
<!-- P2-003 | Hidden text layer and emphasis | observed-v1 | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-003 — Extractor attributes did not distinguish visible emphasis in the cited page.** All 446 spans reported `GlyphLessFont`, flags 12, and alpha 0. This supports saying those uniform fields cannot distinguish the original page's visible emphasis. It does not prove every useful superscript clue is absent: size, coordinates, baseline, and direction may still help. Font metadata may be wrong or incomplete. “Transparent” does not independently establish OCR origin, and reported bold flags do not certify visible boldness.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: observed-v1.*

<a id="p2-004"></a>
<!-- P2-004 | Token accounting and missing assistant prose | observed-v1 | EVT-0631,EVT-0638,ATT-14 -->
**P2-004 — The eight-turn run disproved the assumption that assistant prose held most judgments.** The saved run reported 636,591 cumulative input tokens, 537,088 cached input tokens (about 84%), and 1,587 output tokens including 137 reasoning tokens. Peak single-request input was 96,996, so cumulative input is not one context window. The first seven raw `assistant.content` values were `null`; only the eighth contained 508 characters. Judgments could appear in tool parameters, candidates, explicit notes, or not be externalized at all. Reasoning-token counts do not establish accessible, complete, provider-portable working notes.

*Sources: EVT-0631, EVT-0638, ATT-14. Status: observed-v1.*

<a id="p2-005"></a>
<!-- P2-005 | Historical quality and timeout limits | observed-v1 | EVT-0807,EVT-0826,ATT-20 -->
**P2-005 — Quality defects and execution failures were different observations.** The 13-page comparisons had material emphasis and glyph defects; A/full history and C/checkpoint were returned as drafts despite completing without the alleged recovery problems. ATT-20 cited pages 14, 16, 18, and 24 and the `礪`/`厲` confusion. This supports better source inspection, editing, and saved-output comparison. The 40-page setup was 3,600 seconds and 100 rounds, not 1,200 seconds/40 rounds: A2 ended with HTTP 408/incomplete streaming; B2 timed out on request 57. Tool friction and large OCR rereads existed, but their causal role in those network endings was not established.

*Sources: EVT-0807, EVT-0826, ATT-20. Status: observed-v1.*

<a id="p2-006"></a>
<!-- P2-006 | Correct candidate degraded on regeneration | observed-v1 | EVT-0826,ATT-20 -->
**P2-006 — Exact reuse addresses an observed regression after correct content existed.** The rejected 40-page candidate contained correct `本文件`; later reconstruction changed it to `本文作`. Rejection involved full-page mapping validity. This is evidence for preserving original candidates, reusing exact text, and changing metadata without regenerating body content. It is not evidence that compaction itself caused the typo, and more OCR or a boldness detector would not directly cure that particular failure.

*Sources: EVT-0826, ATT-20. Status: observed-v1.*

<a id="p2-007"></a>
<!-- P2-007 | Natural adoption and short-run extrapolation | corrected-proposal | EVT-0534,EVT-0638,EVT-0826,ATT-11,ATT-14,ATT-20 -->
**P2-007 — Non-use and timing do not prove mechanism failure or agent motives.** The nine-page B/C natural tasks did not call `manage_evidence`/`checkpoint`, but completed accepted scoped work without an observed capacity limit. Fear of forgetting, excessive tool friction, misunderstanding, or lack of need were possible explanations, not established motives. The cited 217–228 seconds for nine pages and 392–544 seconds for thirteen pages can inform rough budgets; they do not prove a 173/290-page book requires subagents, that one agent must fail, or that episodes are faster. Prescribed mechanism exercise and natural adoption answer different questions.

*Sources: EVT-0534, EVT-0638, EVT-0826, ATT-11, ATT-14, ATT-20. Status: corrected-proposal.*

<a id="p2-008"></a>
<!-- P2-008 | Test count and fault-injection applicability | observed-v1 | EVT-0459,EVT-0826,ATT-08,ATT-20 -->
**P2-008 — Existing tests are reusable evidence with boundaries.** The 228-test result and R1/R2 injected-failure records apply to a particular v1 code state and exercised behaviors. They support fixture and contract reuse; they do not certify the whole old controller, all hard crashes, natural prolonged outages, arbitrary old-job recovery, or a new framework composition. Saved-work continuation was observed. Installed desktop readiness and complete source-led delivery remain distinct from tests and mechanism use.

*Sources: EVT-0459, EVT-0826, ATT-08, ATT-20. Status: observed-v1.*

<a id="representations-and-layout"></a>
## Evidence representations and readable layout

<a id="p2-009"></a>
<!-- P2-009 | Three evidence representations | settled-boundary | EVT-0432,ATT-07 -->
**P2-009 — Separate raw, reversibly compact, and simplified representations.** Raw results preserve what the tool actually generated. A reversible compact form may extract duplicate styles or avoid duplicate text while retaining its promised original values and relationships. A simplified layout may group spans or approximate coordinates, but must expose the transformation and exact source references. Keeping raw data on disk does not make the simplified view itself lossless. First/full/raw/field/range and native-pixel access remain available; none of these views is a mandatory gate.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-010"></a>
<!-- P2-010 | Span merging and coordinate quantization | corrected-proposal | EVT-0432,ATT-07 -->
**P2-010 — Same style is insufficient evidence for safe merging.** Adjacent same-font spans can represent separate table columns, formulas, labels, deliberate whitespace, or meaningful internal positions. A single union bbox loses internal geometry. At 600 DPI, a 0.5-point quantization interval is about 4.17 pixels and rounding error can be about 2.08 pixels per coordinate. Proposed 0.1/0.5-point rounding is approximation, not universal crop-safe equivalence. Grouped views can be useful, but precise coordinates and source spans must remain directly retrievable.

*Sources: EVT-0432, ATT-07. Status: corrected-proposal.*

<a id="p2-011"></a>
<!-- P2-011 | Compact encoding contract | proposal | EVT-0459,ATT-08 -->
**P2-011 — Tuple/style-table encoding needs a complete and useful contract.** The proposed `[style_id, bbox, origin, text]` tuples and style table can reduce repeated JSON keys, but a lossless claim must cover actual hierarchy, line direction, writing mode, properties, missing/default values, and all present fields. Separate PyMuPDF text and dict extraction may differ in whitespace, line breaks, or order; concatenating spans cannot be assumed to recreate top-level text. Round-trip equality, actual input tokens including schema/extra reads, and agent usability are different evaluations. A shorter encoding may impose lookup and interpretation work; it was retained as an option, not established as the default.

*Sources: EVT-0459, ATT-08. Status: proposal.*

<a id="p2-012"></a>
<!-- P2-012 | Reported versus derived layout | settled-boundary | EVT-0479,EVT-0507,EVT-0534,ATT-09,ATT-10,ATT-11 -->
**P2-012 — Label extractor reports and derived hints honestly.** Decoding bitmasks and displaying readable colors are useful. PyMuPDF span flags 12 mean serifed (4) plus monospaced (8), not PDF FontDescriptor “symbolic”; bit 0 is superscript, bit 1 italic, bit 2 serifed, bit 3 monospaced, bit 4 bold. Some extractor values, including superscript detection, are already derived, so “extractor-reported” versus “app-derived” is more accurate than “all physical facts” versus inference. Candidate headings/tables/page numbers/reading order are allowed if provenance and method are clear. A blanket ban on inference was rejected.

*Sources: EVT-0479, EVT-0507, EVT-0534, ATT-09, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-013"></a>
<!-- P2-013 | Geometric hints and simplified groups | corrected-proposal | EVT-0479,EVT-0534,ATT-09,ATT-11 -->
**P2-013 — Geometric hints remain candidates.** Smaller text with a shifted baseline may suggest a superscript/subscript; the proposed example compared 6.5-point text with a 10-point line and a −3.1-point baseline offset. Rotated text requires line direction, not merely `origin[1]`. `confidence: heuristic` names a method, not confidence. `span_count: 6` plus one outer bbox is a traceable simplified group only when exact subspan references remain; it cannot reconstruct six internal boxes by itself. No complete suite of geometry detectors became a prerequisite.

*Sources: EVT-0479, EVT-0534, ATT-09, ATT-11. Status: corrected-proposal.*

<a id="p2-014"></a>
<!-- P2-014 | Survey view and detection limits | proposal | EVT-0507,ATT-10 -->
**P2-014 — Survey is a selectable navigation view.** Proposed page skeletons included dimensions, text-layer availability, transparency statistics, edge/page-number candidates, large-type headings, table/column candidates, and native/vector image counts. Large type may be a diagram label; scanned pages may have no usable text layer. “100–200 characters per page” and “30 pages under 5,000 tokens” were design targets, not sufficiency guarantees for a complete document map. Survey does not replace detailed inspection or force text-first work. Reopening saved evidence avoids repeat extraction, but still has I/O, latency, and model-input costs.

*Sources: EVT-0507, ATT-10. Status: proposal.*

<a id="drafts-candidates-and-content-reuse"></a>
## Drafts, candidates, content references, and document edits

<a id="p2-015"></a>
<!-- P2-015 | Draft versus published and verification | settled-boundary | EVT-0432,EVT-0479,ATT-07,ATT-09 -->
**P2-015 — Work can be saved before it is complete.** Working Draft was the valuable improvement over scattered failed candidates: an identifiable active working version can be read, edited, pinned, and previewed with unknown page metadata or unfinished content. Committed/published versions are immutable references. Candidate/committed state is orthogonal to source-review records and to whether the content is complete. Useful partial results can be honest drafts; no universal whole-book approval gate follows from a version commit.

*Sources: EVT-0432, EVT-0479, ATT-07, ATT-09. Status: settled-boundary.*

<a id="p2-016"></a>
<!-- P2-016 | Draft revision isolation | settled-boundary | EVT-0479,ATT-09,EVT-1166 -->
**P2-016 — Incomplete does not mean structurally unreliable.** A mutation names its expected draft revision; a valid complete operation produces a new revision. An invalid or inapplicable mutation retains its original payload/error without damaging the currently usable draft. Preview reads one fixed revision rather than mixing revisions during rendering. The segment sometimes saved a candidate only after basic parsing; final consolidation strengthens this to preserving received raw parameters before validation. Automatic rescue of truncated JSON is not a first-version prerequisite.

*Sources: EVT-0479, ATT-09, EVT-1166. Status: settled-boundary.*

<a id="p2-017"></a>
<!-- P2-017 | Exact source options for content | settled-boundary | EVT-0507,EVT-0826,ATT-10,ATT-20 -->
**P2-017 — Inline content, saved artifacts/candidates, and workspace files are equal input choices.** A script-prepared four-page, 200-cell table should not have to be echoed through a second long tool-call string to enter the draft. Direct references avoid repeated model generation and reduce opportunities for truncation, escaping errors, and newly introduced typos. This is not literal zero-copy: read/parse/save operations still copy data. Illustrative API output pricing in attachments does not establish Nexus subscription fees or actual savings.

*Sources: EVT-0507, EVT-0826, ATT-10, ATT-20. Status: settled-boundary.*

<a id="p2-018"></a>
<!-- P2-018 | Snapshot validation and short transaction | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-018 — Validate and commit the same fixed content.** Acquire a stable content snapshot, hash/parse/validate it against the immutable expected base outside the lock, then use a short transaction to check current revision and submit the revision/reference/receipt. Long file reads, OCR, rendering, and model inference do not belong inside the document lock. A mutable scratch file must not be re-read after validation as though unchanged. Imported Markdown does not automatically establish source-page coverage, table relationships, or resolved issues.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-019"></a>
<!-- P2-019 | Editing operations and partial page maps | settled-boundary | EVT-0826,ATT-20,EVT-1166 -->
**P2-019 — Remove unnecessary regeneration and mapping friction.** The proposed document core supports insert/append, replace, delete, move, stable targets, candidate/file import, and whole-section reconstruction when useful. Local page-map updates merge into the existing map and validate the resulting whole document; the agent need not resend unchanged body text or the full 173-page map for every edit. Metadata-only fixes, new insertion, and reuse of a rejected candidate are the final contract's three concrete cases. This is method freedom, not a requirement that edits always be small.

*Sources: EVT-0826, ATT-20, EVT-1166. Status: settled-boundary.*

<a id="p2-020"></a>
<!-- P2-020 | Candidate workset selection | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-020 — The active candidate must remain usable, but all candidates need not be loaded.** A correct cross-page table rejected for page metadata may be the best content for continuing its next page. Loading only the old published version or a candidate summary can lose precision and cause redundant reads. The active working candidate may be loaded, pinned, and modified as needed; other candidates can be indexed. Clearly distinguish current working content from committed content, pending corrections, and competing historical candidates.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-021"></a>
<!-- P2-021 | Stable block identity versus content hash | settled-boundary | EVT-0560,ATT-12 -->
**P2-021 — Logical identity and immutable content are different.** A table remains the same table after its text changes, while its hash changes. Identical paragraphs at separate positions may be distinct blocks. `{block_id: table_01, content_ref: sha256:...}` preserves edit/pin/relationship identity while permitting content reuse. A sequence of bare hashes does not. This representation does not force paragraph-sized blocks; the agent may operate on a complete table or chapter.

*Sources: EVT-0560, ATT-12. Status: settled-boundary.*

<a id="p2-022"></a>
<!-- P2-022 | Rebase and conflicts | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-022 — Disjoint block IDs do not establish semantic independence.** A header-unit edit and a numerical-row insertion can conflict despite different targets; so can reordering versus page-map changes or removed images versus added references. Rebase previews may show structural, asset, page-map, and known dependency changes for agent judgment. A stale base must not silently overwrite current work. Preserve the candidate and explain differences. Generic automatic semantic rebase or a large dependency graph is not required.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-023"></a>
<!-- P2-023 | Single content authority | settled-boundary | EVT-0534,EVT-0826,EVT-1166 -->
**P2-023 — Immutable version files are the preferred body authority.** Final consolidation places document body content in immutable files and version registration, pointers, and operation receipts in SQLite; it avoids a second independently mutable body copy. Earlier full-JSON-per-revision and content-addressed block layouts are storage options, not required schemas. Unchanged blocks may be reused. Versioned saving, reopening, preview, and export must select the same intended content identity.

*Sources: EVT-0534, EVT-0826, EVT-1166. Status: settled-boundary.*

<a id="pins-references-and-retention"></a>
## Pins, source references, and evidence retention

<a id="p2-024"></a>
<!-- P2-024 | Pin metadata ownership | settled-boundary | EVT-0432,ATT-07 -->
**P2-024 — Agent intent and system bookkeeping have separate owners.** The agent expresses target, purpose, and possible release condition. The app maintains version/hash, deletion/lineage observations, exact bytes/dimensions, and model-dependent cost estimates. Requiring agents to manually maintain every cost or derived field creates avoidable work. Local byte counts can be exact; token and image-input costs are not universally exact.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-025"></a>
<!-- P2-025 | Fixed and following references | settled-boundary | EVT-0432,EVT-0459,EVT-0479,ATT-07,ATT-08,ATT-09 -->
**P2-025 — Fixed snapshots and following references have different meanings.** Preserve a problematic OCR or old draft for comparison by fixed version. A current header may follow a defined logical identity on a specified working-draft or committed track. One-to-one replacement does not prove unchanged purpose, and “small text edit” does not prove harmlessness: `mg` to `μg`, an added negation, or a one-digit change can transform meaning without structural change. Reveal relevant changes rather than silently declaring compatibility; split/merge/delete may need explicit repinning while the previous snapshot remains accessible.

*Sources: EVT-0432, EVT-0459, EVT-0479, ATT-07, ATT-08, ATT-09. Status: settled-boundary.*

<a id="p2-026"></a>
<!-- P2-026 | Change disclosure and request-fixed references | corrected-proposal | EVT-0479,EVT-0507,EVT-0674,ATT-09,ATT-10,ATT-15 -->
**P2-026 — Do not confuse sent diffs with understood state.** Repeating full before/after diffs every round inflates input. A `last_disclosed_revision` can describe delivery, not model processing or comprehension. Each request resolves following references to fixed versions and records that choice. Ensure needed current content is available after compaction; prior diff delivery is not the only route to current state. Exact full diffs remain retrievable.

*Sources: EVT-0479, EVT-0507, EVT-0674, ATT-09, ATT-10, ATT-15. Status: corrected-proposal.*

<a id="p2-027"></a>
<!-- P2-027 | No implicit release from page state | settled-boundary | EVT-0459,EVT-0479,EVT-0507,EVT-0560,EVT-0826,ATT-08,ATT-09,ATT-10,ATT-12,ATT-20 -->
**P2-027 — Unpinned, saved, old, or unflagged does not mean irrelevant.** P0–P3, Focus Decay, “saved with no issue,” and default release of evidence omitted from `keep_evidence_ids` were repeatedly rejected as hard semantic rules. A survey of 30 pages may precede reconstruction; keeping all uncommitted evidence resident punishes that valid method. Conversely, writing pages 10–11 does not prove pages 13–15 can leave: an abbreviation or table footnote may be there. Missing issue registration is not proof of no dependency. Pins are strong signals, not a requirement to label every useful item.

*Sources: EVT-0459, EVT-0479, EVT-0507, EVT-0560, EVT-0826, ATT-08, ATT-09, ATT-10, ATT-12, ATT-20. Status: settled-boundary.*

<a id="p2-028"></a>
<!-- P2-028 | Retention signals without fixed workflow | proposal | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-028 — Use signals to help the agent choose, not to dictate scope.** Current requests, explicit pins, unresolved dependencies, recent use, neighboring pages, and drafted status can inform candidates and priorities. Nearby one or two pages are only clues; a dependency may be ten pages away. App observes capacity and offers candidates; agent judges relevance and records needed findings/references; app applies agreed choices. This requires no routine human approval, mandatory pin register, fixed page window, or extra handoff after every edit.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: proposal.*

<a id="p2-029"></a>
<!-- P2-029 | Source link versus residency | settled-boundary | EVT-0789,ATT-19,ATT-20 -->
**P2-029 — Source linkage, unresolved work, and explicit residency are three relationships.** A note or draft citing a page image protects provenance and a precise retrieval path. An open issue protects its question and dependency state. An explicit pin requests designated content in the working input. A table's source reference alone does not require a 4 MB image on every call. Mechanical checks can verify valid references and declared retention; they do not decide semantic necessity.

*Sources: EVT-0789, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-030"></a>
<!-- P2-030 | Evidence release and history compaction | settled-boundary | EVT-0595,EVT-0826,ATT-13,ATT-20 -->
**P2-030 — Releasing evidence and consolidating history are independent actions.** Moving an unnecessary retrievable image out of input need not call another model, rewrite all notes, or create an epoch. Consolidating old conversations must preserve effective requirements, decisions, rationale, unfinished work, and precise retrieval. Evidence management does not replace ordinary history compaction. Optional explicit `context_delta` may accompany a document save; omitting it preserves prior decisions rather than authorizing release.

*Sources: EVT-0595, EVT-0826, ATT-13, ATT-20. Status: settled-boundary.*

<a id="p2-031"></a>
<!-- P2-031 | Immediate and deferred release | proposal | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-031 — Permission to release later differs from an instruction to remove next turn.** `evict_when_needed` can allow batching releases for capacity or cache reuse. `drop_immediately` expresses an agent choice to remove stale, wrong, or distracting evidence in the next input even if capacity is ample. The app must not delay that choice solely to preserve cache. Both remove active exposure while preserving original data and history.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: proposal.*

<a id="navigation-and-work-awareness"></a>
## Navigation, coverage, and work awareness

<a id="p2-032"></a>
<!-- P2-032 | Evidence stubs | corrected-proposal | EVT-0534,ATT-11 -->
**P2-032 — A stub is a retrieval aid, not a guarantee against forgetting.** A short receipt can identify page, candidate table, bottom small-print region, and precise access. Heuristics may miss the important footnote; a 100-character stub cannot guarantee preservation of relationships. Complete indexes persist and can be searched by page/type/text/ID. Active context keeps useful entries and unresolved dependencies; it need not retain one stub for every prior call forever. A handoff must be able to consult originals, not recursively summarize only older stubs.

*Sources: EVT-0534, ATT-11. Status: corrected-proposal.*

<a id="p2-033"></a>
<!-- P2-033 | Rollup maps and bucket indexes | corrected-proposal | EVT-0560,EVT-0595,ATT-12,ATT-13 -->
**P2-033 — Navigation can be compact without a fixed-size guarantee.** Alternating completed/uncompleted pages defeat contiguous rollups: 300 pages can still yield nearly 300 ranges. Twenty-five-page buckets reduce display detail but `O(N/25)` is still `O(N)`, not constant memory. Twelve lines for one 300-page book do not prove all books fit 10–20 lines or 400 tokens. Expandable chapter/range views and selected buckets are useful; one or two active buckets must not restrict cross-range work. Counts do not replace exact coverage records.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-034"></a>
<!-- P2-034 | Coverage versus findings and delivered scope | settled-boundary | EVT-0432,EVT-0560,EVT-0759,ATT-07,ATT-12,ATT-18 -->
**P2-034 — Distinguish extracted, delivered, drafted, and understood.** The app can know results were produced, a particular scope entered a request, and a version cites them; it cannot infer comprehension. “Inspected but unpublished” is a useful reminder, not semantic protection. A compact entry such as “pages 15–20: draft pending; OCR/layout available via manifest” avoids confusing already-extracted pages with unextracted pages. List actual successful ranges and warnings; availability does not prove completeness or correctness. Cross-page meaning such as “page 15 footnote governs pages 12–14” requires an explicit finding, not a mechanical coverage statistic.

*Sources: EVT-0432, EVT-0560, EVT-0759, ATT-07, ATT-12, ATT-18. Status: settled-boundary.*

<a id="p2-035"></a>
<!-- P2-035 | Pending manifests across compaction | settled-boundary | EVT-0730,ATT-17 -->
**P2-035 — Unseen evidence can cross context boundaries through precise range indexes.** Do not invent a content summary of raw text never obtained. But operation facts (“the tool produced pages 15–20”) may be summarized without reading all content. Keep unfinished scope and an immutable manifest entry; do not force every unhydrated evidence directory into every request. Already-written notes may remain useful even if their source is not rehydrated in the compaction call. Unfinished chapters may be compacted; agents may release unrelated or duplicate references even before fully opening them, while originals remain retrievable.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="capacity-and-handoff"></a>
## Capacity accounting, oversized results, and handoff

<a id="p2-036"></a>
<!-- P2-036 | Persistence versus model admission | settled-boundary | EVT-0432,ATT-07 -->
**P2-036 — Saving complete results is separate from admitting them to a model input.** Full evidence, execution outcome, and version receipts can be persisted immediately. Once the tool batch is complete, a shared assembler allocates the next request's total budget. A separate pending buffer can be a reference, not another giant data copy. Checking at request assembly is not inherently too late if every model request passes that boundary. Per-tool wrappers cannot each claim the same remaining capacity.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-037"></a>
<!-- P2-037 | Large-result envelopes | settled-boundary | EVT-0432,EVT-0459,EVT-0560,ATT-07,ATT-08,ATT-12 -->
**P2-037 — Report execution and delivery separately.** A result can be successfully saved yet not fully expanded, or a multi-page operation can partly succeed. Keep per-part outcomes, evidence identity/hash/size, requested representation, actual loaded pages/fields/regions/images, omitted scope, warnings, and exact read methods. Define whether “full” means the requested representation or raw original. A navigation receipt is not proof the full evidence entered the request. Every formal tool call still receives a protocol-valid result before a handoff/model turn; incomplete pairings cannot be hidden in a compaction transition.

*Sources: EVT-0432, EVT-0459, EVT-0560, ATT-07, ATT-08, ATT-12. Status: settled-boundary.*

<a id="p2-038"></a>
<!-- P2-038 | No mandatory stage ladder | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-038 — Capacity actions can be combined according to need.** Representation changes, releasing already-unneeded evidence, exact range reads, and history handoff are options, not a compulsory four-stage conversion process. Crossing a soft watermark alone need not force a handoff. A single result can exceed an otherwise empty window, so neither deferred admission nor compaction guarantees eventual full expansion. The 55% + 35% example usefully motivated preflight, but cannot establish “100% handshake space” for every input.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-039"></a>
<!-- P2-039 | Capacity components and actual requests | settled-boundary | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-039 — Count the complete assembled request and required output reserve.** System instructions, tool schemas, roles/message wrappers, all active historical images, current evidence, working state, previous assistant output/tool calls, and output/handoff allowance affect capacity. JSON characters, bytes, image MB, and pixels are not interchangeable with tokens. Each selected route needs configurable capacity/output reserve; no universal percentage or optimal watermark study is required. “Previous usage + new text” only applies when the actual prior composition remains compatible; compaction, projection changes, route/image changes, and omitted history invalidate that shortcut.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-040"></a>
<!-- P2-040 | Estimation and calibration uncertainty | corrected-proposal | EVT-0560,EVT-0595,EVT-0638,ATT-12,ATT-13,ATT-14 -->
**P2-040 — Calibration remains an estimate, not a proven upper bound.** Bind usage to route/model/protocol/image mode and exact request. Applicable local tokenizers and known image rules help; UTF-8/CJK factors, base64 length, pixel area, recent max ratios times 1.05/1.15, and text/vision split calibration do not mathematically bound the next request. A text-heavy sample can hide badly underestimated image cost. “No new images” may still include old images; subtracting text deltas does not isolate image cost if other inputs/routing changed. A 1,500–2,500-token image allowance is not universal. Preserve uncertainty and recoverable overflow behavior without paid calibration probes as a prerequisite.

*Sources: EVT-0560, EVT-0595, EVT-0638, ATT-12, ATT-13, ATT-14. Status: corrected-proposal.*

<a id="p2-041"></a>
<!-- P2-041 | Handoff allowance and gradual compaction | corrected-proposal | EVT-0560,EVT-0595,ATT-12,ATT-13,EVT-1166 -->
**P2-041 — Plan for the actual sequence of normal output and handoff.** If a normal turn generates content before handoff, `max(normal_output, handoff_output)` alone may omit the new assistant content, tool receipts, and handoff prompt. Predictive margins cannot constrain an as-yet unknown tool batch; re-evaluate afterward. Final consolidation allows consolidation to reduce history progressively: intermediate progress need not already meet the final normal-request budget. It does not promise two or three passes always suffice, retain a fixed recent K turns, or require an old draft to be superseded before it can leave input.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13, EVT-1166. Status: corrected-proposal.*

<a id="p2-042"></a>
<!-- P2-042 | Shared hydration with purpose-specific input | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-042 — Normal inference and handoff share evidence resolution, not necessarily identical contents.** An auxiliary summarizer that sees only ticket IDs can miss the evidence needed for accurate continuation. Both paths should resolve references, fixed versions, and declared projections through the same mechanism and record their actual input. Conversely, requiring all active evidence to be hydrated before compaction recreates the overflow that triggered compaction. Each request receives the relevant content that fits its purpose and capacity; originals stay directly accessible without summary approval.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-043"></a>
<!-- P2-043 | Handoff failure and recovery context | settled-boundary | EVT-0560,EVT-0595,ATT-12,ATT-13 -->
**P2-043 — Failed handoff preserves original records and has a finite outcome.** When old context remains usable, retain it and respond to the actual failure. If it is genuinely unavailable or cannot be made usable through normal capacity handling, a clearly labeled recovery context may carry effective requirements, current artifacts, valid notes, recent activity, candidates, and exact retrieval. It may require renewed source inspection; there is no guarantee of complete internal reasoning or lossless semantic continuation. If even required controls and a workable minimum do not fit, save work and stop with a concrete capacity blocker rather than retry forever. Process restart alone does not justify recovery-context replacement.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-044"></a>
<!-- P2-044 | Mechanical eviction rejection | corrected-proposal | EVT-0560,ATT-12,EVT-1166 -->
**P2-044 — “Save all assistant text, evict saved pages” is not a safe universal fallback.** All assistant text, tool arguments, notes, and drafts may themselves overflow. A saved page with no flagged issue may still supply an unresolved table header/footnote. The app preserves observable records, not hidden mental state. Later consolidation prefers a self-sufficient handoff with effective requirements, unfinished work, and exact references over fragile delta notes. The latest draft and unfinished candidates may partially leave input while their originals remain retrievable; none is permanently pinned merely by being latest.

*Sources: EVT-0560, ATT-12, EVT-1166. Status: corrected-proposal.*

<a id="p2-045"></a>
<!-- P2-045 | Token versus HTTP byte limits | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-045 — HTTP payload size and model context are separate limits.** HTTP 413 says a server/proxy refuses that request size; it does not reveal token capacity. The proposed 15/20 MB and 128k/200k figures were examples, not verified Nexus limits. Track actual request bytes and token estimates separately. A rejection does not authorize the transport to remove evidence. The capacity path must explicitly select a valid view under existing relevance decisions and budgets, record actual requests, and expose omissions.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-046"></a>
<!-- P2-046 | Zero-fit and nonsequential selection | settled-boundary | EVT-0459,EVT-0789,ATT-08,ATT-19 -->
**P2-046 — The next useful evidence may be noncontiguous, and zero items may fit.** Always loading the first K pages can discard the useful last-row/next-header pair or comparison of pages 15 and 19. K is not guaranteed to be at least one: a single native image can exceed the available request size. A lightweight capacity envelope can show dimensions, bytes, ranges, and exact selection options, letting the agent choose regions/fields/representations or revise the working set. Mandatory sequential paging and arbitrary biggest-item eviction were rejected.

*Sources: EVT-0459, EVT-0789, ATT-08, ATT-19. Status: settled-boundary.*

<a id="p2-047"></a>
<!-- P2-047 | Capacity error ownership and budgets | settled-boundary | EVT-0759,EVT-0789,EVT-0826,ATT-18,ATT-19,ATT-20 -->
**P2-047 — Capacity recovery needs its own explicit finite control path.** `before_model` does not automatically catch a downstream capacity exception. A wrapper may make a limited number of handler calls, but “at most two reassemblies” was a policy proposal, not a framework guarantee. Context-limit recovery was not an existing v1 transport retry behavior. Whether separated from transport retry counting or not, all actually sent requests must be recorded and remain under the original round/task/time budgets. A fresh view does not mint attempts or semantic permission to drop needed content.

*Sources: EVT-0759, EVT-0789, EVT-0826, ATT-18, ATT-19, ATT-20. Status: settled-boundary.*

<a id="cache-and-prefix"></a>
## Prompt cache and reusable computation

<a id="p2-048"></a>
<!-- P2-048 | Stable prefix tradeoffs | corrected-proposal | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-048 — Stable prefix is an optimization, not the highest rule.** Put stable instructions/schemas early when practical and use ordinary tool results for normal changes. Supplement current state on recovery, handoff, or a real gap rather than inject a duplicate full snapshot every turn. Replacing a dynamic tail can break the prior prefix; appending every snapshot accumulates duplicates. A fixed epoch baseline plus substantive append-only events and a freshly assembled current view are different legitimate strategies with different cache tradeoffs. They cannot both claim an unchanged prefix and freshly rewritten early state. Update user requirements immediately and explicitly; a revision number alone does not explain what changed.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-049"></a>
<!-- P2-049 | Cache evidence and cost | corrected-proposal | EVT-0534,EVT-0826,ATT-11,ATT-20 -->
**P2-049 — Cache ratios do not establish price-weighted task savings.** The observed roughly 84% cached input is one run, not a promised benefit of epoch/tail design. Prefix identity, cache availability, expiry, routing, repeated outputs, extra reads, and latency all matter. Neither fewer characters nor fewer total tokens alone proves equal-fidelity savings or Nexus billing. A deferred release strategy can preserve reuse, but correctness, current requirements, capacity, and an explicit immediate-removal request take priority.

*Sources: EVT-0534, EVT-0826, ATT-11, ATT-20. Status: corrected-proposal.*

<a id="p2-050"></a>
<!-- P2-050 | Result cache versus operation replay | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-050 — Reuse an existing computation without impersonating its old call.** A repeated logical operation uses its original receipt and identity. A new call may reuse an earlier evidence result but receives a message paired with the new call ID and records the reused provenance. Reuse should preserve requested completeness when capacity allows; recovery does not automatically downgrade full OCR to a bare ID. Missing success receipts do not prove no work happened, especially for scripts.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-051"></a>
<!-- P2-051 | Correct computation signatures | proposal | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-051 — Cache identity follows actual computation.** A useful signature includes fixed source hash, tool/implementation/engine version, resolved defaults, OCR model/language data and their order, DPI, PSM, bbox, annotations, and relevant settings. Tesseract language order can affect output. Whole-call hashes for pages 15–20 and 15–16 differ; overlap reuse needs an index at independently computable units. A later 19–21 request can reuse 19–20 and compute only 21 when semantics permit. Cross-page analyses cannot automatically be reduced to page cache units.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: proposal.*

<a id="p2-052"></a>
<!-- P2-052 | Computation storage and selection granularity | settled-boundary | EVT-0789,ATT-19,ATT-20 -->
**P2-052 — Computation, storage, and selection granularity are independent.** A six-page immutable JSON may store naturally as one blob while an index maps individual pages or JSON Pointers to independent computations. Context may select only pages 19–20 or certain fields/regions without physically splitting the file. Neither partial release nor overlap caching requires one file per page. A selection must record concrete ranges/fields/view version; `partial` alone cannot reconstruct what was delivered.

*Sources: EVT-0789, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-053"></a>
<!-- P2-053 | Explicit recomputation | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-053 — A cache must not trap the agent in a defective old result.** Changed settings or explicit `force_recompute` can generate a new evidence identity, retaining old evidence for comparison and notes. If the default cache index points to the newest result, that is a declared selection policy, not a claim that newest means best. Never silently retarget an existing fixed note/reference. Reuse verifies completeness and source/settings identity rather than trusting only the presence of a cached path.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="input-views-and-hydration"></a>
## Input views, hydration, and causal identity

<a id="p2-054"></a>
<!-- P2-054 | Lightweight persistent references and transient hydration | settled-boundary | EVT-0638,EVT-0674,EVT-0789,ATT-15,ATT-16,ATT-19 -->
**P2-054 — Durable state and model-visible messages need not contain the same large payloads.** Keep large OCR/layout/images in immutable evidence storage; a checkpoint can hold stable references, call pairing, and useful small results. At request time, new transient message objects expand the requested original text/pixels when capacity permits. Small success/error results may stay inline; not every tool needs a blob round-trip. `ToolMessage.artifact` was a plausible structured carrier, rather than guessing that arbitrary body JSON resembles a delivery ticket. Preserve message identity and pairing, and avoid accidentally writing expanded payloads back into graph state.

*Sources: EVT-0638, EVT-0674, EVT-0789, ATT-15, ATT-16, ATT-19. Status: settled-boundary.*

<a id="p2-055"></a>
<!-- P2-055 | Hydration limits and native images | corrected-proposal | EVT-0674,ATT-15 -->
**P2-055 — Reference storage does not guarantee a few-kilobyte checkpoint.** Message counts, notes, assistant arguments, long submitted drafts, and scripts still grow. The design reduces repeated heavy evidence, not all state to a fixed size. “Native image” also does not mean PNG: an original JPEG retains its original format and identity. Successful evidence reuse should fulfill the original requested projection, not require another model turn merely to discover that its result was saved.

*Sources: EVT-0674, ATT-15. Status: corrected-proposal.*

<a id="p2-056"></a>
<!-- P2-056 | Actual input identity replaces sequence maximum | settled-boundary | EVT-0674,ATT-15 -->
**P2-056 — An input view records selection, not just the largest event number.** An input containing event 20's text and event 40's selected fields, while excluding 21–39 and images, cannot be represented as “agent saw everything through 40.” A small immutable `input_view_id`/request manifest identifies requirements, draft and policy versions, included messages/evidence/fields/ranges/image representations, and omitted requested items. It can refer to original files rather than duplicate them. Inclusion in a request proves neither comprehension nor faithful use.

*Sources: EVT-0674, ATT-15. Status: settled-boundary.*

<a id="p2-057"></a>
<!-- P2-057 | Reconstructable app-boundary input | settled-boundary | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-057 — State the reconstruction boundary precisely.** To reconstruct app-assembled input, preserve message order/roles, exact tool parameters, prompt/schema versions, model/route settings, selected notes and resolved pins, projections or immutable projection references, and image representations. Hashes validate content but cannot replace missing bytes. The claim is reconstruction at the defined app boundary; it does not prove the provider/Nexus upstream performed no further transformation or expose what the model internally perceived. Optional safe wire descriptions/digests can check adapter encoding without turning context management into a proxy-chain audit.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: settled-boundary.*

<a id="p2-058"></a>
<!-- P2-058 | Input to accepted response to tool chain | settled-boundary | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-058 — Bind each accepted response and tool call to its real input.** A generated view must travel with the accepted parent response, for example through namespaced app `response_metadata` while preserving provider metadata. A tool binds to that parent response and its call ID, not the latest view in a database. Missing or conflicting linkage is an association error. `additional_kwargs` may contain provider encoding data and is not an arbitrary substitute. Capture after relevant input modifications, preserve the full `ModelResponse`, and account for wrappers that call handlers multiple times or return multiple messages.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: settled-boundary.*

<a id="p2-059"></a>
<!-- P2-059 | View request attempt and batch identities | settled-boundary | EVT-0730,EVT-0789,EVT-0826,ATT-17,ATT-19,ATT-20 -->
**P2-059 — A view is not a round, attempt, accepted batch, or activation event.** Identical frozen input may be retried under multiple attempts; changed pins/schema/messages/model settings require another view. Neither new view nor outer wrapper call resets the stable logical round's attempt/time budget. Usage belongs to each execution attempt, not a single mutable field on a reusable view. The accepted parent response/tool batch establishes which proposals are eligible for activation; querying every operation with the same input view can incorrectly include rejected attempts or other branches.

*Sources: EVT-0730, EVT-0789, EVT-0826, ATT-17, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-060"></a>
<!-- P2-060 | Historical activity is data | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-060 — Compressed historical calls must not masquerade as pending native calls.** Preserve raw exact parameters separately. A compact activity skeleton can list operations, pages, errors, candidate IDs, and retrieval entries as ordinary historical reference text. Truncated arguments inside native `AIMessage.tool_calls` risk malformed examples and invalid pairing. A read-only label alone cannot prevent execution: dispatch must accept only current formally accepted response/framework-pending calls; source text and historical summaries are inert. Ordinary schema validation still applies because a model could imitate a historical format.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="notes-and-coverage"></a>
## Working notes and semantic coverage

<a id="p2-061"></a>
<!-- P2-061 | Activity ledger versus semantic work notes | settled-boundary | EVT-0595,EVT-0638,EVT-0674,ATT-13,ATT-14,ATT-15 -->
**P2-061 — Operations tell what happened, not all the reasoning needed to continue.** “Inspected pages 15–16, changed table_02” omits “page 16's first row continues the prior table; a value remains uncertain and was not adopted.” Likewise a crop bbox gives a selected area, not why it was selected or why an alternative was rejected. A recovery view should draw activity from existing tool/receipt/version records, plus useful explicit notes, messages, errors, and candidates. Avoid a second independent activity ledger. Compact summaries can aid navigation but cannot claim a fixed few-hundred-token size or exact recovery of unexpressed judgment.

*Sources: EVT-0595, EVT-0638, EVT-0674, ATT-13, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-062"></a>
<!-- P2-062 | Notes without compulsory tool conventions | proposal | EVT-0595,EVT-0638,ATT-13,ATT-14 -->
**P2-062 — Preserve important findings during ordinary work without a universal note ritual.** Agents can save discoveries, unresolved dependencies, conventions, and reasons before full compaction; an append-only prefix policy does not prevent tail note updates. The proposed `note_on_previous_step` on every tool may be convenient but adds schema, output, concurrency, and replay obligations; it is not zero cost. A separate note tool can be called alongside a read in one model response, so an additional tool call need not mean an additional model turn. Prior non-use does not prove which interface will be adopted.

*Sources: EVT-0595, EVT-0638, ATT-13, ATT-14. Status: proposal.*

<a id="p2-063"></a>
<!-- P2-063 | Note write time input basis and compaction scope | settled-boundary | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-063 — Separate when a note was saved, what input supported it, and what history was replaced.** In the race example, the model uses input through event 100, emits an OCR and a note, OCR finishes as 101, then the note is saved. Automatically setting `covered_up_to_event_seq=101` excludes unseen OCR from recovery. Even without concurrency, a short note about one unit does not summarize all prior work. Creation/update ordering, exact input-view linkage, and actual compacted message IDs/ranges are separate facts; a normal note never automatically advances a semantic coverage frontier.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-064"></a>
<!-- P2-064 | Operation order is not completion order | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-064 — Mutable operation rows cannot serve as a complete event timeline.** Operation 100 may be registered before 101 and finish later; updating row 100 to succeeded then querying `event_seq > 101` loses that new completion. Keep current operation status separately from framework message/checkpoint order and input/compaction identity. If a completion sequence is needed, allocate it inside the result-commit transaction and define it as receipt-commit order. An append-only state-event record is an option only if useful, not an obligation to construct a general event-sourcing system.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-065"></a>
<!-- P2-065 | Versioned notes and concurrency | settled-boundary | EVT-0638,EVT-0674,EVT-0701,EVT-0730,ATT-14,ATT-15,ATT-16,ATT-17 -->
**P2-065 — Note identity and version checks must preserve both current and historical meaning.** Item-level append/upsert/resolve can avoid whole-note-blob overwrite, but simultaneous edits to the same note still require an expected version or explicit merge rule. Merely storing `note_rev` does not enforce a check. Old input views referencing revision 3 must still resolve revision 3, through immutable note revisions or saved content references. User requirements, source facts, and agent judgments stay distinct; notes cannot quietly rewrite requirements. Independent task databases reduce accidental mixing but still require correct source/workspace identity.

*Sources: EVT-0638, EVT-0674, EVT-0701, EVT-0730, ATT-14, ATT-15, ATT-16, ATT-17. Status: settled-boundary.*

<a id="state-authority-and-policy-activation"></a>
## State authority, policy activation, and conflicts

<a id="p2-066"></a>
<!-- P2-066 | Orthogonal authorities | settled-boundary | EVT-0479,ATT-09 -->
**P2-066 — A context manifest describes one input, not all committed reality.** If document revision 4 and its success receipt commit while a context manifest still references 3, a crash cannot make revision 4 nonexistent. Document/version receipts establish committed edits; evidence storage establishes saved results; session records establish exchanges; context manifests establish versions/content selected for an input. Recovery reconciles these roles. Unreferenced by one context means not included there, not unexecuted, unsaved, or valueless. Atomic replacement of a manifest pointer, including Windows `ReplaceFileW`, cannot create a transaction across independent stores.

*Sources: EVT-0479, ATT-09. Status: settled-boundary.*

<a id="p2-067"></a>
<!-- P2-067 | CAS and self-produced updates | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-067 — A context swap must distinguish external drift from its own new notes.** Capturing notes revision 5, writing handoff notes as 6, then requiring all revisions still equal their original values incorrectly rejects the handoff's own update. Separate read base and staged changes, check competing changes at the real commit point, and commit the appropriate note/policy state coherently. A hook that sequentially writes two independent stores is not a joint transaction. The precise manifest schema was an implementation proposal, not a requirement.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-068"></a>
<!-- P2-068 | Requirement changes during handoff | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-068 — New human instructions govern continuation immediately.** Preserve original requirement revisions and explicit changes; source observations may remain valid while old plans or candidates require reevaluation. If pages 15–20 leave scope, merely appending a high-priority version label does not prove the old plan is harmless. Preserve useful unaffected evidence and candidates; “needs reevaluation” is often more accurate than declaring all affected content invalid. Pause/cancel must not require an additional model handoff first.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-069"></a>
<!-- P2-069 | Why maximum revision loses branches | settled-boundary | EVT-0730,ATT-17 -->
**P2-069 — A larger policy revision does not contain another branch's changes.** From policy 7, A creates 8 to pin a page-12 header, while B creates 9 to release an OCR without A's pin. Choosing `max(8,9)` silently loses the pin. Check expected parent and operation identity where state is actually accepted; “both tools checked 7 before execution” is insufficient. Restore the version associated with the selected checkpoint branch, not the database's global newest number. This rejects timestamp/maximum-number selection as a substitute for ownership and lineage.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-070"></a>
<!-- P2-070 | SQLite serialization does not serialize graph commands | corrected-proposal | EVT-0759,ATT-18,EVT-0878 -->
**P2-070 — Two individually serialized database writes can still race in graph state.** In the historical external-policy proposal, A could commit policy 8 and B policy 9 in SQLite while both returned `Command(active_policy_rev=...)` in one superstep; graph state could reject concurrent updates or accept an unintended order. Adding `current_active_rev` in SQLite while checkpoint state also owned the pointer recreated competing authorities. EVT-0878 subsequently simplified the single built-in executor: keep the small context policy and processed context-change batches in Graph State, settle tool-reported intents at one point, and remove the unnecessary external policy-version/activation tables. Parallel replacement of whole policy values can still overwrite changes; reducers do not infer pin/release meaning. The retained boundary is one state authority and one settlement writer, independent of the final graph node names.

*Sources: EVT-0759, ATT-18, EVT-0878. Status: corrected-proposal.*

<a id="p2-071"></a>
<!-- P2-071 | Activation versus request hydration | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-071 — Durable policy decisions and transient payload expansion belong at different boundaries.** In the historical `create_agent` design, `wrap_tool_call` saved effects/proposals and replayed completion; a sequential `before_model` step settled lightweight state; `wrap_model_call` expanded content, checked capacity, and recorded the input view. Returning huge hydrated messages from `before_model` would persist them into state, undoing reference-based storage. The final architecture may name nodes differently; the separation remains the useful contract.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-072"></a>
<!-- P2-072 | Batched intent resolution | corrected-proposal | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-072 — Same-batch local intents are possible without generic semantic rebase.** Requiring one complete context proposal was a conservative race avoidance suggestion, not proof of semantic correctness. Same accepted tool batch may submit local pin/release intents for one sequential settlement. Validate the merged target state: `pin_remove(ev03)` plus `release(ev03)` can be coherent; conflicting add-pin/release requires an explicit result. Do not always let pins win by iteration order. Different object IDs do not establish independence or spare capacity. The agent owns semantic choices; general automatic linear intent rebasing remained outside first-version necessity.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: corrected-proposal.*

<a id="p2-073"></a>
<!-- P2-073 | Idempotent activation itself | superseded | EVT-0789,EVT-0826,ATT-19,ATT-20,EVT-0878 -->
**P2-073 — The external-policy activation proposal exposed a real replay problem, then was simplified.** Under that historical proposal, SQLite could create policy 8 before graph state persisted its pointer. A stable accepted-batch identity plus its original parent and proposal set was intended to recover the same settlement, instead of creating another policy from all completed database operations. Tool results could carry explicit proposal IDs. `hash(current_parent, sorted_proposals)` alone was insufficient: after 7 became 8, the same proposals would form another key unless the accepted batch was already recorded as settled. Policy-content deduplication and activation-event identity were distinct, and prepared but unactivated policies could exist. EVT-0878 superseded the separate external policy-version/activation machinery with small policy and processed-batch state in Graph State, updated together at one settlement point. Stable batch settlement remains relevant; an external activation receipt store is not a V1 requirement. Receipts for actual document/tool effects and sent model requests still retain their separate purpose.

*Sources: EVT-0789, EVT-0826, ATT-19, ATT-20, EVT-0878. Status: superseded.*

<a id="p2-074"></a>
<!-- P2-074 | Request-pinned policy and references | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16,EVT-0878,EVT-1166 -->
**P2-074 — Reconstruct a real selected state, not independently latest components.** The earlier external-policy design used an immutable policy revision and a branch-selected reference. EVT-0878 replaces that storage mechanism with compact policy in Graph State for the single built-in executor. In either representation, resolve `follow_latest` into fixed versions for each model request. Independently choosing newest checkpoint, policy, notes, draft, and evidence can assemble a state that never existed. Final consolidation requires one owner for each model request, batch progress, document version, and operation receipt, with one active task writer; it does not require an external policy-version table, a particular seven-table schema, or full distributed coordination platform.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16, EVT-0878, EVT-1166. Status: settled-boundary.*

<a id="persistence-and-replay"></a>
## Persistence, operation identity, and replay

<a id="p2-075"></a>
<!-- P2-075 | SQLite short transactions and immutable files | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-075 — Four logical responsibilities do not require four independent stores.** SQLite can hold version registration, artifact references, receipts, notes, and metadata, while large bodies/evidence remain immutable files. Shared transactions cover database records only, not external blobs or framework sessions/checkpoints. WAL is a useful option, still with one writer; synchronization/checkpoint settings affect latency and durability. “Under one millisecond” was unmeasured. Table count and all-JSON-row layouts were provisional proposals, not architecture proof.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-076"></a>
<!-- P2-076 | Prepare files before references and protect prepared work | settled-boundary | EVT-0534,EVT-0560,EVT-0595,EVT-0638,EVT-0730,ATT-11,ATT-12,ATT-13,ATT-14,ATT-17 -->
**P2-076 — Finish immutable files before committing references to them.** Blob-first preparation/verification followed by the database transaction reduces dangling committed references; framework acknowledgement can occur later. It is not a universal two-phase distributed transaction or absolute filesystem durability guarantee. Unreferenced prepared files may still belong to an in-progress or recoverable operation. TTL leases need renewal for long operations; a simpler early implementation can avoid background deletion. No active process does not mean no useful prepared work: startup must identify recoverable tasks before cleanup. These are preservation principles, not a new cleanup project.

*Sources: EVT-0534, EVT-0560, EVT-0595, EVT-0638, EVT-0730, ATT-11, ATT-12, ATT-13, ATT-14, ATT-17. Status: settled-boundary.*

<a id="p2-077"></a>
<!-- P2-077 | Stable logical operation identity | settled-boundary | EVT-0507,EVT-0534,EVT-0638,EVT-0674,EVT-0730,ATT-10,ATT-11,ATT-14,ATT-15,ATT-17 -->
**P2-077 — An app operation is more than a provider tool-call string.** Persist exact accepted call parameters and a scoped stable operation identity before executing effects. Link parent accepted response, task/thread, namespace, framework call, and input view consistently; include the parent response unless call-ID uniqueness across the entire scope is guaranteed. Retrying the same operation preserves identity; a changing run/attempt ID must not turn it into a new operation. Same identity with different tool/parameters/fixed inputs is rejected. Summary arguments alone cannot prove equality.

*Sources: EVT-0507, EVT-0534, EVT-0638, EVT-0674, EVT-0730, ATT-10, ATT-11, ATT-14, ATT-15, ATT-17. Status: settled-boundary.*

<a id="p2-078"></a>
<!-- P2-078 | Idempotent receipts and current head | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-078 — Replay returns what happened then without rolling current state backward.** Commit a document version and its receipt coherently. An identical replay returns the original result rather than inserting twice. A receipt saying “produced revision 4” may coexist with current head 5; report both as distinct facts. A new call with `expected_rev=3` after 4 exists is blocked by version checking, so it is a usability/reconciliation problem rather than proof of duplicate writing. Historical completion must not reset current pointers.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-079"></a>
<!-- P2-079 | Content hash deduplication boundaries | corrected-proposal | EVT-0534,ATT-11 -->
**P2-079 — Content hashes identify exact payload equality, not semantic intent or operation identity.** Optional `(base_revision, payload_hash)` deduplication must be scoped by document, operation kind, target, complete change, fixed referenced contents/assets, and base. Stable logical operation identity is separately scoped to its accepted response and batch; a content hash does not supply it. Identical table text inserted at different positions can be two valid operations. “Nearly identical” regeneration will not hash equally. Prefer preserving accepted calls and reconciling saved effects before asking the model to reconstruct an action. Optional exact deduplication does not establish a general intent recognizer.

*Sources: EVT-0534, ATT-11. Status: corrected-proposal.*

<a id="p2-080"></a>
<!-- P2-080 | Full completion replay including graph updates | corrected-proposal | EVT-0701,EVT-0730,ATT-16,ATT-17,EVT-0878 -->
**P2-080 — A tool's completion may contain more than its visible receipt.** The historical external-policy example replayed only `ToolMessage` after app policy 8 was saved but `Command(update={active_policy_rev:8})` was not checkpointed, leaving graph policy 7 active. That particular external policy/command mechanism was superseded by EVT-0878's compact Graph State policy and centralized settlement. The underlying completion lesson remains: preserve the committed domain result and any necessary supported state-update semantics, and reconstruct an equivalent completion without regressing newer state. Stable message identities and expected versions help avoid duplicates/regression. A design that persists only `Command.update` must explicitly limit supported forms; `goto`/`graph` cannot silently disappear. The final direct graph can concentrate state writes and reduce this machinery, while retaining the completion effects it actually supports.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17, EVT-0878. Status: corrected-proposal.*

<a id="p2-081"></a>
<!-- P2-081 | Stable message IDs do not resurrect safely | settled-boundary | EVT-0730,ATT-17 -->
**P2-081 — Stable message IDs only deduplicate messages still present.** `add_messages` replaces an existing same-ID entry; if compaction removed it, replay adds it again. Do not scan every successful receipt and re-inject historical messages, potentially orphaning ToolMessages. Let the runtime determine actual pending work, then reuse the corresponding receipt/completion when that work is invoked. Message identity is one aid, not a universal exactly-once or safe-history-replay guarantee.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-082"></a>
<!-- P2-082 | Framework resume and pending writes | settled-boundary | EVT-0595,EVT-0638,EVT-0759,ATT-13,ATT-14,ATT-18 -->
**P2-082 — Use supported framework recovery rather than rebuild its scheduler.** Load session/checkpoint, reconcile effects, and continue the original state if usable. LangGraph has public state/history access and pending writes; the checked `create_agent` dispatched separate tools with `Send("tools", [tool_call])`. An unfinished superstep therefore does not prove every completed OCR must rerun. `StateSnapshot.tasks` contains `PregelTask` descriptions, not a guaranteed executable tool-call array. Use the runtime resume entry; when it actually invokes a tool, the wrapper checks its receipt. State snapshots serve diagnostics/status/checkpoint selection rather than a second scheduler.

*Sources: EVT-0595, EVT-0638, EVT-0759, ATT-13, ATT-14, ATT-18. Status: settled-boundary.*

<a id="p2-083"></a>
<!-- P2-083 | Expensive tool result reuse | proposal | EVT-0638,ATT-14 -->
**P2-083 — Saved OCR/render outputs can bridge the remaining effect/checkpoint gap.** Framework completion records are preferred; app results can cover the interval after an expensive tool finished but before its completion was durably recorded. Reuse checks source version, exact settings, and result completeness. This is useful even though “all tools always replay after a superstep crash” was false. It need not force every tiny operation through the same subprocess or blob machinery.

*Sources: EVT-0638, ATT-14. Status: proposal.*

<a id="p2-084"></a>
<!-- P2-084 | Acknowledgement timestamps and lazy observation | corrected-proposal | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-084 — Returned, observed, persisted, sent, and understood are distinct.** `returned_to_session_at` can be empty after the framework saved a result but before app timestamp update, or filled before framework persistence if ordered the other way. A hook seeing a result is not itself proof it survives a crash. Lack of a result in compacted active input is not evidence it was never delivered. Lazy acknowledgement can optimize common cases, backed by stable session/checkpoint identities and supported public-state reconciliation. Timestamps are observations, not joint transactions or proof of comprehension.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-085"></a>
<!-- P2-085 | Persistence modes and original budgets | settled-boundary | EVT-0560,EVT-0638,EVT-0730,ATT-12,ATT-14,ATT-17,EVT-1166 -->
**P2-085 — State the persistence and budget boundaries explicitly.** A named SQLite checkpointer does not determine durability: `sync`, `async`, and `exit` have different crash protection. A complete accepted response, each tool effect, and graph progress may be durable at different times. Recovery retains original persistent attempts/time budgets and does not re-publish a saved version. Final consolidation asks for explicit behavior at four boundaries: request saved, response accepted, tool committed, and graph recorded; arbitrary hard-crash or all-old-job recovery is not assumed.

*Sources: EVT-0560, EVT-0638, EVT-0730, ATT-12, ATT-14, ATT-17, EVT-1166. Status: settled-boundary.*

<a id="subprocesses-and-salvage"></a>
## Subprocesses, unknown outcomes, and useful partial work

<a id="p2-086"></a>
<!-- P2-086 | Working directories are not OS sandboxes | settled-boundary | EVT-0674,ATT-15 -->
**P2-086 — Per-attempt directories provide organization and provenance.** Pointing cwd/environment at `script_runs/<operation_id>/out` does not prevent absolute-path or parent-directory writes. Trusted scripts execute with host-user permissions; directory separation is not an OS sandbox or automatic read-only enforcement. Full reconstruction does not silently change that security model. Any genuine restricted execution boundary needs a separately chosen mechanism, not a relabeled working folder.

*Sources: EVT-0674, ATT-15. Status: settled-boundary.*

<a id="p2-087"></a>
<!-- P2-087 | In-flight unknown states | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-087 — A missing completion marker does not prove nonexecution.** `in_flight`/`spawning` can mean registered-before-launch, running, completed-before-receipt, or interrupted with partial output. The controller can crash after launch but before recording running, or after completion but before writing `_exit_status.json`. Nonzero exit can be an ordinary failure with reusable output. Even a zero exit and matching hashes do not prove scope/contract completion. Keep unknown states honest; logical operations and physical attempts are distinct, and each real subprocess attempt can retain process identity, working directory, logs, and outputs.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-088"></a>
<!-- P2-088 | Job objects and launch gaps | corrected-proposal | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-088 — Process supervision improves control but does not undo file effects.** Windows `KILL_ON_JOB_CLOSE` acts when the last job handle closes, for processes actually assigned to that job; handle inheritance, breakaway, assignment, and termination confirmation matter. `CREATE_SUSPENDED` then assignment has a crash gap; supported Windows can use `PROC_THREAD_ATTRIBUTE_JOB_LIST` at process creation. A job may be destroyed before restart can query it. PID plus creation time helps identity but does not alone prove all descendants stopped. Other platforms require their own real lifecycle guarantees, not an assertion that process groups are equivalent. Apply this machinery only to actual subprocesses, not database note updates.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: corrected-proposal.*

<a id="p2-089"></a>
<!-- P2-089 | Retry by effects not tool label | settled-boundary | EVT-0730,ATT-17 -->
**P2-089 — Safe retry follows an actual side-effect contract.** Built-in OCR/rendering can be retryable when reading fixed inputs, writing only attempt-specific candidates, leaving formal versions unchanged, and ensuring old execution cannot continue modifying the same output. Being “built-in” does not prove those conditions. A host script without a final receipt is not blindly rerun, but evidence can still establish reusable completion or partial results. The agent may reconcile saved script, process state, outputs, and identifiable effects; only unresolved effects remain unknown or blocked. No routine human intervention is required for effects that can be safely reconciled within authorization.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-090"></a>
<!-- P2-090 | Separate inspect terminate and adopt intent | settled-boundary | EVT-0759,EVT-0789,EVT-0826,ATT-18,ATT-19,ATT-20 -->
**P2-090 — Diagnostic reading must not quietly kill or adopt.** Agents may inspect partial logs, malformed JSON, and damaged files to diagnose or repair; the whole directory need not validate first. Termination targets an identified attempt and is explicit, even if an interface combines steps. Salvaging one stable file does not imply stopping the entire attempt. Adoption selects a fixed consistent copy and validates that exact content. These internal responsibilities do not force a four-tool ritual on the agent.

*Sources: EVT-0759, EVT-0789, EVT-0826, ATT-18, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-091"></a>
<!-- P2-091 | Snapshot and Windows sharing semantics | corrected-proposal | EVT-0789,ATT-19 -->
**P2-091 — A consistent copy needs evidence of stability, not just an existing filename.** A live writer can yield a torn copy. Holding a compatible read handle during snapshot acquisition is a possible Windows implementation. `GENERIC_WRITE` requests write access; `FILE_SHARE_WRITE` permits others' write access and does not mean that handle is writing. `ERROR_SHARING_VIOLATION` means incompatible access/share modes, possibly an exclusive reader, not proof of an unknown descendant writing. Report snapshot unavailability and the observed error without inventing its cause.

*Sources: EVT-0789, ATT-19. Status: corrected-proposal.*

<a id="p2-092"></a>
<!-- P2-092 | Decode versus completeness and independent salvage receipts | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-092 — Valid bytes, valid format, and complete requested work are separate.** Use mature full parsers/decoders; PNG endings/CRC or JPEG EOI alone do not replace decoding, and Pillow `verify()` differs from loading pixels. A syntactically valid JSON holding pages 1–30 is not successful completion of requested 1–100. Verify selected source/scope/content, record useful rescued ranges, and preserve the original failed/uncertain operation history. A separate salvage receipt can succeed while the original operation remains incomplete; a single `salvaged_resolved` flag should not erase that distinction.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="images-previews-and-source-review"></a>
## Images, previews, and source-led review

<a id="p2-093"></a>
<!-- P2-093 | Asset registration without restricting methods | settled-boundary | EVT-0534,ATT-11,ATT-12 -->
**P2-093 — Registered assets can come from legitimate scripts as well as built-in tools.** An import path should record source and processing for native embedded images, page/region renders, raster crops, and script-produced derivatives. Native images preserve original encoding/dimensions, including JPEG; crops concern parent pixels and lossless output; vector/composite PDF renders concern page/region/render parameters/readability. One mandatory page/bbox/DPI field set does not fit all types. Management/provenance records do not prove a crop retained the right panel, legend, or labels; preserve source-led quality checks without imposing a new per-image approval ritual.

*Sources: EVT-0534, ATT-11, ATT-12. Status: settled-boundary.*

<a id="p2-094"></a>
<!-- P2-094 | Preview generation versus review | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-094 — Producing a PNG is not passing a quality check.** A preview record identifies generated pixels for a fixed target revision. A review record identifies what was actually inspected, its source, scope, aspect, and unresolved issues. Do not auto-create a passing layout review because Chromium produced an image. Candidate/draft previews remain useful before final mapping or full document completion.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-095"></a>
<!-- P2-095 | Review history and aspect carry-over | settled-boundary | EVT-0459,EVT-0479,EVT-0507,ATT-08,ATT-09,ATT-10 -->
**P2-095 — A v1 review remains a historical fact; applicability to v2 is a separate judgment.** Avoid marking an entire page and all dependencies invalid after any edit. Distinguish characters/numbers, meaningful styles, reading/cross-page relations, crop content, and rendered layout. Unchanged characters do not prove full text fidelity when superscripts, footnote placement, or emphasis changes. Adding table rows may alter shared header/unit/footnote scope. Preserve unaffected checks where justified and guide targeted reevaluation without a universal quality engine or compulsory review gate.

*Sources: EVT-0459, EVT-0479, EVT-0507, ATT-08, ATT-09, ATT-10. Status: settled-boundary.*

<a id="p2-096"></a>
<!-- P2-096 | Version dependencies for previews and exports | settled-boundary | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-096 — A dependent preview must identify the committed version it actually used.** Running `update_draft` and an implicit-latest preview concurrently can inspect old content while the agent believes it saw the new revision. Return `produced_revision`, then let the agent choose that version for readback/preview/export. An optional document-level commit-plus-preview operation may reduce a round, but reports commit and preview outcomes separately; preview failure is not edit failure. A generic `after_batch_mutation` scheduler brings ambiguity with multiple edits, failed edits, stale bases, and recovery, and was not made first-version necessary. Explicitly viewing old content or a rejected candidate remains useful.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-097"></a>
<!-- P2-097 | Source to saved-output comparison | proposal | EVT-0826,ATT-20 -->
**P2-097 — Make the original region and corresponding saved block easy to compare.** Missing emphasis can originate in source interpretation, Markdown markup, or rendering. Access to both source pixels and the exact saved revision helps locate the failure. A `render_regions([{page,bbox,label},...])` capability can inspect confusable glyphs, headings, superscripts, or neighboring emphasis. Return independent images or a contact sheet at the agent's choice; keep labels outside source pixels, sufficient context, per-region provenance, originals, and exact rereads.

*Sources: EVT-0826, ATT-20. Status: proposal.*

<a id="p2-098"></a>
<!-- P2-098 | Contact sheets and ink-density hypotheses | hypothesis | EVT-0826,ATT-20 -->
**P2-098 — Visual assistance is not certified optical interpretation.** One contact sheet may be cheaper/clearer than several images, or worse if it makes each glyph too small; bytes alone do not decide. Proposed ink/stroke ratio hints are reproducible measurements but not reliable bold labels without evidence: Chinese characters naturally differ in density, and size, bbox alignment, background, bleed, binarization, or hidden OCR misalignment affect values. Keep such output as optional “visual difference worth checking” hints, not per-span mandatory numeric noise or a first-version prerequisite. Exact local original-pixel comparison has the more direct value.

*Sources: EVT-0826, ATT-20. Status: hypothesis.*

<a id="runtime-and-framework-alternatives"></a>
## Runtime and framework alternatives, with corrected comparisons

<a id="p2-099"></a>
<!-- P2-099 | App responsibility does not mean custom mechanism | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-099 — Defining product policy does not require reimplementing every mechanism.** The app decides what must be preserved, accepted, and displayed; a framework may implement messages, persistence, turn boundaries, summaries, cancellation, or middleware that calls a centralized policy. Declaring all session/provider/context/lifecycle work app-owned and then saying the runtime is only a while-loop prejudges the comparison. Conversely, if integration really replaces most features, a thinner runtime can be sensible. Compare reusable mechanisms, state/exception paths to maintain, public-interface stability, diagnostics, and upgrade cost, not only low interference or adapter line count.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-100"></a>
<!-- P2-100 | Single policy without one giant hook | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-100 — One decision authority can be implemented through cooperating components.** Avoid independent app and framework compressors maintaining competing active contexts. It does not follow that all logic must sit in one hook. Similarly, converting through framework message types does not inherently destroy images or encrypted reasoning: verify required information survives and the final native request is correct. Hook names alone do not establish Nexus compatibility or crash safety.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-101"></a>
<!-- P2-101 | Deep Agents corrections | corrected-proposal | EVT-0459,EVT-0479,ATT-08,ATT-09 -->
**P2-101 — Deep Agents was not eliminated by the attachment's claims.** In the checked 0.7.29 version, size offloading was in `FilesystemMiddleware`, with public `tool_token_limit_before_evict=None` and same-name replacement mechanisms; configuration is not rewriting the entire middleware. Summarization offered prompt/counting/custom-summarizer options. Pi also has automatic compaction policy to coordinate. Deep Agents has TypeScript as well as Python variants, requiring version-specific checks. Since v0.7 task planning/`write_todos` was optional, the claimed mandatory Todo removal cost was wrong. No measured “context advantages become zero” conclusion followed.

*Sources: EVT-0459, EVT-0479, ATT-08, ATT-09. Status: corrected-proposal.*

<a id="p2-102"></a>
<!-- P2-102 | Generic workspace tools and formal artifacts | settled-boundary | EVT-0479,ATT-09 -->
**P2-102 — Workspace file tools need not bypass document validation.** They can prepare long drafts, notes, scripts, and intermediate outputs. Workspace Markdown is working material; formal versions come through the document service. Do not point generic tools directly at internal version storage or automatically treat any file as a published artifact. Retain agent script/file freedom rather than remove it to simplify a framework comparison. `create_agent` was attractive for opting into only needed tools, not because generic file tools are intrinsically incompatible.

*Sources: EVT-0479, ATT-09. Status: settled-boundary.*

<a id="p2-103"></a>
<!-- P2-103 | Public interfaces and inaccurate recovery APIs | corrected-proposal | EVT-0432,EVT-0507,EVT-0534,EVT-0595,ATT-07,ATT-10,ATT-11,ATT-13 -->
**P2-103 — The named framework hooks had narrower meanings than the proposals claimed.** Deep Agents `_get_effective_messages` was internal, not a stable extension contract; public model/tool middleware was preferred. Pi's request `context`/`context_with_system`, compaction hooks, and `context_edit` do not themselves create an app transaction. Pi v1.3.0 examples used `SessionManager.open()` and `createAgentSession()`, not `Session.load()`; persisted tool results were message entries with role `toolResult`. Tool `execute()` returns `AgentToolResult {content, details}`, not a session-entry object. `getEntry/getEntries/getBranch` provide public reads. Direct JSONL surgery was rejected.

*Sources: EVT-0432, EVT-0507, EVT-0534, EVT-0595, ATT-07, ATT-10, ATT-11, ATT-13. Status: corrected-proposal.*

<a id="p2-104"></a>
<!-- P2-104 | LangGraph and Pi resume scope | corrected-proposal | EVT-0507,EVT-0595,EVT-0638,ATT-10,ATT-13,ATT-14 -->
**P2-104 — Framework recovery must be assessed at its actual public boundary.** LangGraph `update_state()` creates a new checkpoint, applies reducers, and `as_node` affects subsequent execution; it is not merely appending a ToolMessage, so hiding repair side effects in `get_tuple()` was rejected. Public `get_state/get_state_history` can inspect without parsing private storage. Pi's low-level `Agent.continue()` can reject when the last message is assistant and no queued message exists; that refutes an automatic-pending-tool-resume assumption, not Pi's overall suitability. A hook mapping alone cannot establish equal integration cost.

*Sources: EVT-0507, EVT-0595, EVT-0638, ATT-10, ATT-13, ATT-14. Status: corrected-proposal.*

<a id="p2-105"></a>
<!-- P2-105 | Historical framework preference and supersession | superseded | EVT-0595,EVT-0638,EVT-0826,EVT-1166 -->
**P2-105 — The `create_agent` preference was provisional and later narrowed.** This segment moved from Pi versus Deep Agents to Pi versus selective `create_agent`, then prioritized `create_agent` with persistent LangGraph checkpoints to reduce custom recovery responsibilities. Plain `create_agent` does not include `FilesystemMiddleware` by default. These were design priorities, not app-level compatibility or performance results. The later final consolidation chooses a small direct `StateGraph` plus native Nexus service and document/evidence core, superseding the middleware-centered assembly while retaining useful state and projection boundaries.

*Sources: EVT-0595, EVT-0638, EVT-0826, EVT-1166. Status: superseded.*

<a id="nexus-models-and-long-work"></a>
## Nexus integration, model capability, and long work

<a id="p2-106"></a>
<!-- P2-106 | Native Nexus behavior without a second retry owner | settled-boundary | EVT-0730,EVT-0826,ATT-17,ATT-20,EVT-1166 -->
**P2-106 — Preserve behavioral contracts when extracting the Nexus service.** The conversation valued native Chat Completions/Responses encoding, tool-image pairing, encrypted reasoning where used, complete-response validation, safe diagnostics, persistent attempts, and attempt-local SSE assembly without partial JSON execution or cross-attempt concatenation. Context is app-controlled and does not require upstream native compaction. The final shared service is used for ordinary inference and consolidation with the same budget/cancellation rules; it does not assume remote cancellation, background result retrieval, or known cost after unknown outcomes.

*Sources: EVT-0730, EVT-0826, ATT-17, ATT-20, EVT-1166. Status: settled-boundary.*

<a id="p2-107"></a>
<!-- P2-107 | Old transport cannot be wrapped as an automatic guarantee | corrected-proposal | EVT-0819,EVT-0826,ATT-20 -->
**P2-107 — Extract capabilities before adapting them to a new lifecycle.** The v1 retry ledger lived in `Agent.model_round`, while Chat image pairing depended on `Provider.pending_images`/`flush_images`; they were not all in one HTTP function. A `NexusWireChatModel` wrapper could be a useful historical adapter option, but would not inherit 228 tests or every old guarantee automatically. Isolate request/batch state, preserve native-response/framework mappings, and use one retry owner. Generic `ChatOpenAI` retries are configurable and it supports images/Responses; the specific risk is unpreserved third-party fields and actual route behavior, not an established claim it breaks everything.

*Sources: EVT-0819, EVT-0826, ATT-20. Status: corrected-proposal.*

<a id="p2-108"></a>
<!-- P2-108 | Frozen input and bounded unknown outcomes | settled-boundary | EVT-0730,EVT-0759,ATT-17,ATT-18 -->
**P2-108 — Transport replay and capacity redesign are different actions.** For an eligible transient transport failure, reuse the frozen logical request rather than re-resolve live pins or change the prefix. Keep each attempt, diagnostics, response candidate, usage if known, and unknown fees/settlement when appropriate. Permanent configuration/authentication errors and user cancellation do not gain blind retries. Capacity correction needs the explicit context path. Earlier examples of automatic retries 2/three attempts described optional configurations, not a new default or renewed authorization for model calls.

*Sources: EVT-0730, EVT-0759, ATT-17, ATT-18. Status: settled-boundary.*

<a id="p2-109"></a>
<!-- P2-109 | Model switching preserves unresolved modality needs | settled-boundary | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-109 — Capability checks address the work, not merely API acceptance.** Check target context, image/tool/protocol capabilities, prepare the transferable state, validate the actual request, then activate. Removing images can make a text model's request valid while losing evidence for emphasis, legends, or superscripts; OCR is not universally equivalent. Retain unresolved visual requirements and block only unsupported operations, allowing useful text/script work or an available vision route. A font name alone must not impose mandatory page-by-page visual gates. Model rules and calibration do not silently carry across routes.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-110"></a>
<!-- P2-110 | Optional visual delegation | proposal | EVT-0638,ATT-14 -->
**P2-110 — A vision tool is an optional way to support a text-focused agent.** `query_visual_evidence` can use a configured vision route and retain question, exact images/regions, model, response, and uncertainty as derived evidence. Allow crop, whole page, or multiple related pages so a forced crop does not remove a header/legend. Raw pixels remain source evidence. Such a tool does not automatically certify its model's interpretation, create a required workflow, or authorize additional paid model calls during this reconstruction.

*Sources: EVT-0638, ATT-14. Status: proposal.*

<a id="p2-111"></a>
<!-- P2-111 | Sections and episodes | proposal | EVT-0826,ATT-20 -->
**P2-111 — Long work needs continuity, not a fixed two-level agent design.** One agent switching sections or optional sequential episodes/subagents can carry effective requirements, current versions/candidates, unfinished scopes, unresolved cross-section relations, and the same task budget/records. No page threshold mandates episodes. Sharing a budget does not enlarge its time/round allowance; separate budgets change policy. Subgraphs can provide execution-local persistence, but do not choose handoff content, merge documents, or judge completion automatically. Heavy OCR/images remain in evidence storage; child checkpoints store state/references, and the parent receives exact outputs and remaining issues rather than an unverifiable completion summary.

*Sources: EVT-0826, ATT-20. Status: proposal.*

<a id="verification-and-convergence"></a>
## Verification, adoption, and final convergence

<a id="p2-112"></a>
<!-- P2-112 | Seven-step scenario is a fixture not workflow | settled-boundary | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-112 — The seven-step path was an example for integration checks.** Survey across pages, save an unfinished table, fix metadata/header, preview the same revision, compact, continue editing, and interrupt after a commit form a useful scenario. They do not prescribe how every PDF is converted. A scripted mock model may finish without reading the new context at all, so a successful sequence alone does not establish correct handoff, source fidelity, or agent autonomy.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: settled-boundary.*

<a id="p2-113"></a>
<!-- P2-113 | What offline checks can establish | settled-boundary | EVT-0459,EVT-0507,EVT-0534,ATT-08,ATT-10,ATT-11 -->
**P2-113 — Check the actual contract rather than only the path completing.** Useful checks include exact compact-encoding round trips; final assembled requirements/current state/unresolved references; precise evidence and pixel retrieval; original receipts without duplicate edits; complete tool pairing; and expected activation behavior at interruption boundaries. An exception can run `finally`/flush and is not a hard process kill; broken IPC may leave a subprocess working. Fixture tests establish scoped mechanisms, not live model reasoning, comprehensive Nexus behavior, lower equal-quality cost, or the best framework. “Two hours to prove the winner” and adapter line count were not reliable acceptance criteria.

*Sources: EVT-0459, EVT-0507, EVT-0534, ATT-08, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-114"></a>
<!-- P2-114 | Proportionate source-led acceptance | settled-boundary | EVT-0507,EVT-0534,EVT-0826,EVT-1166 -->
**P2-114 — Delivered reading and software mechanics remain separate.** A source-led saved/reopened/exported check concerns the intended PDF or complete section, image fidelity, meaningful formatting, correct content, and reusable output. Natural autonomy does not require the agent to exercise import, release, visual delegation, or preview correction merely to demonstrate features. Final design acceptance is consistent contracts and clear ownership; later implementation needs suitable offline checks and actual source comparison. These retrospective suggested experiments are not current standing permission or a queued benchmark matrix.

*Sources: EVT-0507, EVT-0534, EVT-0826, EVT-1166. Status: settled-boundary.*

<a id="p2-115"></a>
<!-- P2-115 | Three final contracts and bounded scope | settled-boundary | EVT-1148,EVT-1166 -->
**P2-115 — The final consolidation leaves three decision areas, not endless prerequisites.** Document edits must define exact references, changed fields, preservation of unspecified content, and commit success. Capacity/handoff must define sendable, release-needed, consolidation-needed, and still-too-large states without losing unprocessed history or destroying originals. Persistence/recovery must name owners and behavior at saved request, accepted response, committed tool, and recorded graph boundaries; reconcile frozen requests and historical receipts without budget reset or head rollback. Unknown local effects preserve work and stop when unreconcilable; explicit user questions wait. Speculative hard-crash universality, automatic truncated-call salvage, universal reminders, and automatic packaging on every exit are not necessary additions.

*Sources: EVT-1148, EVT-1166. Status: settled-boundary.*

<a id="p2-116"></a>
<!-- P2-116 | Delivery and product readiness | settled-boundary | EVT-1166 -->
**P2-116 — Saved results and delivery status have independent meaning.** Markdown, JSON, HTML, images, and ZIP should correspond to one selected version; stopped execution, an agent's completion statement, and export consistency are separate records. Existing saved versions can export without another model request, with incomplete work clearly marked as draft. If delivery means an installable desktop product, interface/backend integration and Windows packaging remain real delivery work, not reasons to reopen context architecture. The preferred architecture is still unimplemented; this reference preserves design knowledge without importing closed v1 job allowances or treating old test logs as new acceptance.

*Sources: EVT-1166. Status: settled-boundary.*

<a id="rejected-guarantees-index"></a>
## Compact index of claims not to revive as requirements

The detailed points above preserve each claim's useful part and correction. The following index is deliberately nonnormative:

| Rejected or narrowed claim | Corrected reference |
|---|---|
| Layout size proves thousands of fragmented OCR spans; 80% reduction is guaranteed | P2-002, P2-010, P2-011 |
| Span grouping/coordinate rounding is lossless because raw data remains on disk | P2-009–P2-013 |
| Transparent text or flags certify source meaning or absence of all geometry clues | P2-003, P2-012, P2-013 |
| Saved/unpinned/old/no-error pages are automatically safe to evict | P2-027–P2-031, P2-044 |
| Every source link requires permanent model residency | P2-029, P2-035 |
| A rollup/stub/ledger guarantees constant context size or no forgetting | P2-032–P2-035, P2-061 |
| All latest draft/candidate content must stay resident until superseded | P2-041, P2-044 |
| Every release requires a handoff or fixed K recent rounds | P2-030, P2-041 |
| Token estimation/calibration supplies a universal upper bound | P2-039–P2-041 |
| Full hydration is necessary before summarizing; all references must stay in each request | P2-035, P2-042 |
| Compaction/deferred admission always fits all results or at least one item | P2-038, P2-043, P2-046 |
| Largest/newest result can be dropped automatically after 413 | P2-045–P2-047 |
| `input_view_id`, max event sequence, or one timestamp proves all execution/semantic states | P2-056–P2-065, P2-084 |
| Context manifest overrides committed document/evidence facts | P2-066 |
| Maximum revision or serialized SQLite transactions resolve graph branches | P2-069–P2-074 |
| Replaying every successful receipt with stable message IDs is safe | P2-080–P2-082 |
| Missing marker means not started; directory isolation is a sandbox | P2-086–P2-092 |
| Saved preview, valid image/JSON, registered asset, or larger test count certifies content | P2-008, P2-092–P2-098 |
| `create_agent` or a thin old-HTTP wrapper automatically inherits v1 guarantees | P2-099–P2-108 |
| Context-tool non-use, short-run extrapolation, or subagents establish a whole-book conclusion | P2-007, P2-111–P2-114 |

No recorded command in the export was executed for this reference. No old-project file was edited, no model call was made, and no new runtime implementation or schema was introduced by this document.
