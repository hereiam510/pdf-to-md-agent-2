# Context, state, and evidence: design reasoning and corrections

<a id="scope-and-status"></a>
## Scope, authority, and reading status

This is a **nonnormative reconstruction reference**, not an implementation specification, test backlog, or authorization to run models. It preserves the substantive reasoning in exported conversation events **EVT-0415–EVT-0826**, including the full inline attachments **ATT-07–ATT-20**. The review read all 5,500 lines of the prepared segment, together with the later final consolidation. The [repository-local source archive](../../sources/rebuild/INDEX.md) provides discussion bodies and attachments as inert reference material.

The complete external export remains an optional provenance archive. The explanations here do not require the old checkout or its development documents. Event and attachment IDs resolve through [SOURCE_INDEX](../../sources/INDEX.md) and [source-inventory.json](../../sources/source-inventory.json). The consolidated [POINT_COVERAGE](../../sources/POINT_COVERAGE.json) maps preserved points to stable anchors. Prepared source packets are local review aids.

The segment repeatedly proposed Pi or LangChain `create_agent` with LangGraph persistence. **That is historical.** The later consolidated preference includes a **small direct LangGraph `StateGraph`**, a **shared native Nexus request service/dispatcher**, and a **document/evidence core**. It uses **SQLite short transactions with immutable files**. This is a priority design choice, not implemented functionality or proof of superiority.

The final consolidation limits unresolved first-version work to three contracts: document editing and candidate references, context capacity and handoff, and persistence/recovery/stopping. Mechanisms below preserve knowledge for implementing those contracts. They do not reopen all the alternatives or make every mechanism mandatory.

The status terms distinguish these meanings:

* **observed-v1**: facts reported about the original implementation or saved runs.
* **settled-boundary**: a product or correctness constraint retained through correction.
* **proposal**: an implementation option.
* **corrected-proposal**: a useful idea with an explicitly withdrawn guarantee.
* **superseded**: an older approach displaced by later decisions.
* **hypothesis**: an unverified causal explanation or benefit.

“Source” references to official APIs below describe what the conversation checked at the stated versions. This review did not perform fresh web research or execute recorded commands.

The following vocabulary makes the historical discussion readable without its original thread. These are descriptions of the concepts already used below, not additional modules or prescribed data structures.

| Term | Meaning in this reference |
|---|---|
| Evidence and evidence view | Evidence is a saved source/tool result, such as OCR, layout, an original embedded image, or a render. A view chooses a representation, page/range, fields, or region from that result. Saving the result and including a view in model input are separate events. |
| Active input and retained history | Active input is the particular text, tool messages, and image content sent on one model call. Complete retained records may be much larger. Removing content from active input does not delete its original file or historical record. |
| Context policy, projection, and hydration | Policy records small decisions about selection, pins, release, notes, and history boundaries. Projection applies those decisions to one request. Hydration expands references into actual text/pixels. The later baseline keeps the small policy in Graph State and the large expansion transient. |
| Input view and frozen request | An input view identifies what the app assembled, including fixed versions and omissions. A frozen request preserves that assembled request for attempts of the same logical model call. It does not look up newer draft or pin content midway through a retry. |
| Candidate, working draft, and version | A candidate preserves proposed content, including a rejected or invalid submission. The working draft identifies usable in-progress content. An accepted edit creates a new immutable revision. A current-head pointer selects the working revision. Saved or committed does not by itself mean complete or source-verified. |
| Base, head, and compare-and-swap (CAS) | A base is the explicitly named content an edit was prepared against. Head is the currently selected revision. CAS means that the short commit step checks its expected current state before accepting a change, so another accepted edit is not silently overwritten. |
| Accepted response, tool batch, and receipt | Only an accepted complete model response supplies tool calls eligible for dispatch. Its batch is the set of those calls. An operation receipt records an app effect/result tied to a stable operation identity. It is not a new instruction to execute that operation. |
| Context handoff and framework checkpoint | A context handoff preserves effective requirements and work knowledge while changing active history. A LangGraph checkpoint persists execution state so the same execution can resume. The old app also called a context-reduction tool `checkpoint`. That name did not make it a LangGraph checkpoint. See [the original context gap](20261031_0157_REBUILD_FOUNDATIONS.md#p1-009). |

For a developer tracing one working path, [candidate reuse](#p2-019), [capacity and delivery](#p2-037), [self-sufficient handoff](#p2-044), [request identity](#p2-059), and [commit/replay](#p2-078) supply the concrete examples. The framework API names later in this file explain historical integration arguments. The current small direct graph is not required to retain those hook names.

The [context and evidence engineering guide](../../guides/CONTEXT_AND_EVIDENCE.md) connects these points into a repository-only implementation handoff. It explains exact result/view identities and native pixels, the single Graph State policy writer, transient input assembly, complete-request capacity, and the later rolling-compaction corrections. Read its [coverage and application sequence](../../guides/CONTEXT_AND_EVIDENCE.md#rolling-compaction), [continuation notes](../../guides/CONTEXT_AND_EVIDENCE.md#handoff-and-working-notes), [restart boundary](../../guides/CONTEXT_AND_EVIDENCE.md#failed-handoff-and-restart), and [cache/reuse distinctions](../../guides/CONTEXT_AND_EVIDENCE.md#prompt-cache-and-cost) together when implementing Q2. These are explanatory consolidations. The three open contracts remain open, and historical API sketches below remain version-specific reference material.

<a id="p2-001"></a>
<!-- P2-001 | Authority and final consolidation | settled-boundary | EVT-0415,EVT-0826,EVT-1148,EVT-1166 -->
**P2-001 — Preserve the product outcome, not an accumulated mechanism list.**

Complete reconstruction was repeatedly allowed. The app should make evidence easy to inspect and correct content easy to save and reuse. It should make long work possible to continue with little user handling. Existing code structure, a fixed number of modules/tables, framework names, and speculative guarantees are not outcomes. Later consolidation explicitly stops expansion: only an actual implementation or delivery blocker that violates an agreed contract justifies reopening that part of the design.

*Sources: EVT-0415, EVT-0826, EVT-1148, EVT-1166. Status: settled-boundary.*

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
**P2-002 — The measured layout was large, but the original explanation was overstated.**

The first `inspect` in run `bdc032cac806419b9612c40927dbcf99` produced 191,662 characters: `layout` alone 147,366, `words` about 39,324, and top-level `text` about 3,034. The page had 41 blocks and 446 spans, not confirmed thousands. Removing `words` alone cannot turn that response into a few thousand characters. Dividing layout length by 446 includes block/line overhead. Removing separate top-level `text` cannot shrink the independently measured layout. Adobe OCR fragmentation, an 80% node reduction, half the coordinate characters, or a usual 10–15-style ceiling were hypotheses, not measured explanations or savings.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: observed-v1.*

<a id="p2-003"></a>
<!-- P2-003 | Hidden text layer and emphasis | observed-v1 | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-003 — Extractor attributes did not distinguish visible emphasis in the cited page.**

All 446 spans reported `GlyphLessFont`, flags 12, and alpha 0. This supports saying those uniform fields cannot distinguish the original page's visible emphasis. It does not prove every useful superscript clue is absent: size, coordinates, baseline, and direction may still help. Font metadata may be wrong or incomplete. “Transparent” does not independently establish OCR origin, and reported bold flags do not certify visible boldness.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: observed-v1.*

<a id="p2-004"></a>
<!-- P2-004 | Token accounting and missing assistant prose | observed-v1 | EVT-0631,EVT-0638,ATT-14 -->
**P2-004 — The eight-turn run disproved the assumption that assistant prose held most judgments.**

The saved run reported 636,591 cumulative input tokens, 537,088 cached input tokens (about 84%), and 1,587 output tokens including 137 reasoning tokens. Peak single-request input was 96,996, so cumulative input is not one context window. The first seven raw `assistant.content` values were `null`. Only the eighth contained 508 characters. Judgments could appear in tool parameters, candidates, explicit notes, or not be externalized at all. Reasoning-token counts do not establish accessible, complete, provider-portable working notes.

*Sources: EVT-0631, EVT-0638, ATT-14. Status: observed-v1.*

<a id="p2-005"></a>
<!-- P2-005 | Historical quality and timeout limits | observed-v1 | EVT-0807,EVT-0826,ATT-20 -->
**P2-005 — Quality defects and execution failures were different observations.**

The 13-page comparisons had material emphasis and glyph defects. A/full history and C/checkpoint were returned as drafts despite completing without the alleged recovery problems. ATT-20 cited pages 14, 16, 18, and 24 and the `礪`/`厲` confusion. This supports better source inspection, editing, and saved-output comparison.

The 40-page setup was 3,600 seconds and 100 rounds, not 1,200 seconds/40 rounds: A2 ended with HTTP 408/incomplete streaming. B2 timed out on request 57. Tool friction and large OCR rereads existed, but their causal role in those network endings was not established.

*Sources: EVT-0807, EVT-0826, ATT-20. Status: observed-v1.*

<a id="p2-006"></a>
<!-- P2-006 | Correct candidate degraded on regeneration | observed-v1 | EVT-0826,ATT-20 -->
**P2-006 — Exact reuse addresses an observed regression after correct content existed.**

The rejected 40-page candidate contained correct `本文件`. Later reconstruction changed it to `本文作`. Rejection involved full-page mapping validity. This is evidence for preserving original candidates, reusing exact text, and changing metadata without regenerating body content. It is not evidence that compaction itself caused the typo, and more OCR or a boldness detector would not directly cure that particular failure.

*Sources: EVT-0826, ATT-20. Status: observed-v1.*

<a id="p2-007"></a>
<!-- P2-007 | Natural adoption and short-run extrapolation | corrected-proposal | EVT-0534,EVT-0638,EVT-0826,ATT-11,ATT-14,ATT-20 -->
**P2-007 — Non-use and timing do not prove mechanism failure or agent motives.**

The nine-page B/C natural tasks did not call `manage_evidence`/`checkpoint`, but completed accepted scoped work without an observed capacity limit. Fear of forgetting, excessive tool friction, misunderstanding, or lack of need were possible explanations, not established motives. The cited 217–228 seconds for nine pages and 392–544 seconds for thirteen pages can inform rough budgets. They do not prove a 173/290-page book requires subagents, that one agent must fail, or that episodes are faster. Prescribed mechanism exercise and natural adoption answer different questions.

*Sources: EVT-0534, EVT-0638, EVT-0826, ATT-11, ATT-14, ATT-20. Status: corrected-proposal.*

<a id="p2-008"></a>
<!-- P2-008 | Test count and fault-injection applicability | observed-v1 | EVT-0459,EVT-0826,ATT-08,ATT-20 -->
**P2-008 — Existing tests are reusable evidence with boundaries.**

The 228-test result and R1/R2 injected-failure records apply to a particular v1 code state and exercised behaviors. They support fixture and contract reuse. They do not certify the whole old controller, all hard crashes, natural prolonged outages, arbitrary old-job recovery, or a new framework composition. Saved-work continuation was observed. Installed desktop readiness and complete source-led delivery remain distinct from tests and mechanism use.

Here R1 and R2 are historical test labels, not recovery modes to implement. R1 concerned an injected temporary outage. R2 concerned interruption before a streaming response completed. The [local historical network explanation](20261031_0157_REBUILD_FOUNDATIONS.md#p1-011) records their meaning and limits. Likewise, a run identifier elsewhere in this file identifies the observation behind a number. Rebuilding the product does not depend on finding or rerunning that old job.

*Sources: EVT-0459, EVT-0826, ATT-08, ATT-20. Status: observed-v1.*

<a id="representations-and-layout"></a>
## Evidence representations and readable layout

<a id="p2-009"></a>
<!-- P2-009 | Three evidence representations | settled-boundary | EVT-0432,ATT-07 -->
**P2-009 — Separate raw, reversibly compact, and simplified representations.**

Raw results preserve what the tool actually generated. A reversible compact form may extract duplicate styles or avoid duplicate text while retaining its promised original values and relationships. A simplified layout may group spans or approximate coordinates, but must expose the transformation and exact source references. Keeping raw data on disk does not make the simplified view itself lossless. First/full/raw/field/range and native-pixel access remain available. None of these views is a mandatory gate.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-010"></a>
<!-- P2-010 | Span merging and coordinate quantization | corrected-proposal | EVT-0432,ATT-07 -->
**P2-010 — Same style is insufficient evidence for safe merging.**

Adjacent same-font spans can represent separate table columns, formulas, labels, deliberate whitespace, or meaningful internal positions. A single union bbox loses internal geometry. At 600 DPI, a 0.5-point quantization interval is about 4.17 pixels and rounding error can be about 2.08 pixels per coordinate. Proposed 0.1/0.5-point rounding is approximation, not universal crop-safe equivalence. Grouped views can be useful, but precise coordinates and source spans must remain directly retrievable.

*Sources: EVT-0432, ATT-07. Status: corrected-proposal.*

<a id="p2-011"></a>
<!-- P2-011 | Compact encoding contract | proposal | EVT-0459,ATT-08 -->
**P2-011 — Tuple/style-table encoding needs a complete and useful contract.**

The proposed `[style_id, bbox, origin, text]` tuples and style table can reduce repeated JSON keys. A lossless claim must cover actual hierarchy, line direction, writing mode, properties, missing/default values, and all present fields. Separate PyMuPDF text and dict extraction may differ in whitespace, line breaks, or order. Concatenating spans cannot be assumed to recreate top-level text.

Round-trip equality, actual input tokens including schema/extra reads, and agent usability are different evaluations. A shorter encoding may impose lookup and interpretation work. The review retained it as an option, not an established default.

*Sources: EVT-0459, ATT-08. Status: proposal.*

<a id="p2-012"></a>
<!-- P2-012 | Reported versus derived layout | settled-boundary | EVT-0479,EVT-0507,EVT-0534,ATT-09,ATT-10,ATT-11 -->
**P2-012 — Label extractor reports and derived hints honestly.**

Decoding bitmasks and displaying readable colors are useful. PyMuPDF span flags 12 mean serifed (4) plus monospaced (8), not PDF FontDescriptor “symbolic”. Bit 0 is superscript, bit 1 italic, bit 2 serifed, bit 3 monospaced, bit 4 bold. Some extractor values, including superscript detection, are already derived, so “extractor-reported” versus “app-derived” is more accurate than “all physical facts” versus inference. Candidate headings/tables/page numbers/reading order are allowed if provenance and method are clear. A blanket ban on inference was rejected.

*Sources: EVT-0479, EVT-0507, EVT-0534, ATT-09, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-013"></a>
<!-- P2-013 | Geometric hints and simplified groups | corrected-proposal | EVT-0479,EVT-0534,ATT-09,ATT-11 -->
**P2-013 — Geometric hints remain candidates.**

Smaller text with a shifted baseline may suggest a superscript/subscript. The proposed example compared 6.5-point text with a 10-point line and a −3.1-point baseline offset. Rotated text requires line direction, not merely `origin[1]`. `confidence: heuristic` names a method, not confidence.

`span_count: 6` plus one outer bbox is a traceable simplified group only when exact subspan references remain. It cannot reconstruct six internal boxes by itself. No complete suite of geometry detectors became a prerequisite.

*Sources: EVT-0479, EVT-0534, ATT-09, ATT-11. Status: corrected-proposal.*

<a id="p2-014"></a>
<!-- P2-014 | Survey view and detection limits | proposal | EVT-0507,ATT-10 -->
**P2-014 — Survey is a selectable navigation view.**

Proposed page skeletons included dimensions, text-layer availability, transparency statistics, edge/page-number candidates, large-type headings, table/column candidates, and native/vector image counts. Large type may be a diagram label. Scanned pages may have no usable text layer. “100–200 characters per page” and “30 pages under 5,000 tokens” were design targets, not sufficiency guarantees for a complete document map. Survey does not replace detailed inspection or force text-first work. Reopening saved evidence avoids repeat extraction, but still has I/O, latency, and model-input costs.

*Sources: EVT-0507, ATT-10. Status: proposal.*

<a id="drafts-candidates-and-content-reuse"></a>
## Drafts, candidates, content references, and document edits

<a id="p2-015"></a>
<!-- P2-015 | Draft versus published and verification | settled-boundary | EVT-0432,EVT-0479,ATT-07,ATT-09 -->
**P2-015 — Work can be saved before it is complete.**

Working Draft was the valuable improvement over scattered failed candidates. An identifiable active working version supports reading, editing, pinning, and preview even with unknown page metadata or unfinished content. Committed/published versions are immutable references. Candidate/committed state is orthogonal to source-review records and to whether the content is complete.

Useful partial results can be honest drafts. No universal whole-book approval gate follows from a version commit.

*Sources: EVT-0432, EVT-0479, ATT-07, ATT-09. Status: settled-boundary.*

<a id="p2-016"></a>
<!-- P2-016 | Draft revision isolation | settled-boundary | EVT-0479,ATT-09,EVT-1166 -->
**P2-016 — Incomplete does not mean structurally unreliable.**

A mutation names its expected draft revision. A valid complete operation produces a new revision. An invalid or inapplicable mutation retains its original payload/error without damaging the currently usable draft. Preview reads one fixed revision rather than mixing revisions during rendering.

The segment sometimes saved a candidate only after basic parsing. Final consolidation strengthens this to preserving received raw parameters before validation. Automatic rescue of truncated JSON is not a first-version prerequisite.

*Sources: EVT-0479, ATT-09, EVT-1166. Status: settled-boundary.*

<a id="p2-017"></a>
<!-- P2-017 | Exact source options for content | settled-boundary | EVT-0507,EVT-0826,ATT-10,ATT-20 -->
**P2-017 — Inline content, saved artifacts/candidates, and workspace files are equal input choices.**

A script-prepared four-page, 200-cell table should not need a second long tool-call string to enter the draft. Direct references avoid repeated model generation and reduce opportunities for truncation, escaping errors, and newly introduced typos. This is not literal zero-copy: read/parse/save operations still copy data. Illustrative API output pricing in attachments does not establish Nexus subscription fees or actual savings.

*Sources: EVT-0507, EVT-0826, ATT-10, ATT-20. Status: settled-boundary.*

<a id="p2-018"></a>
<!-- P2-018 | Snapshot validation and short transaction | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-018 — Validate and commit the same fixed content.**

Use this sequence:

1. Acquire a stable content snapshot.
2. Hash/parse/validate it against the immutable expected base outside the lock.
3. Start a short transaction.
4. Check the current revision within that transaction.
5. Submit the revision/reference/receipt within that transaction.
Long file reads, OCR, rendering, and model inference do not belong inside the document lock. A mutable scratch file must not be re-read after validation as though unchanged. Imported Markdown does not automatically establish source-page coverage, table relationships, or resolved issues.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-019"></a>
<!-- P2-019 | Editing operations and partial page maps | settled-boundary | EVT-0826,ATT-20,EVT-1166 -->
**P2-019 — Remove unnecessary regeneration and mapping friction.**

The proposed document core supports insert/append, replace, delete, move, stable targets, candidate/file import, and whole-section reconstruction when useful. Local page-map updates merge into the existing map and validate the resulting whole document. The agent need not resend unchanged body text or the full 173-page map for every edit. Metadata-only fixes, new insertion, and reuse of a rejected candidate are the final contract's three concrete cases. This is method freedom, not a requirement that edits always be small.

The three cases protect different work. In a metadata-only repair, the agent corrects an incorrect or missing source-page association. The table's accepted text and assets stay the same. In a new insertion, the prepared table enters at an identified document location without replacing unrelated blocks. In rejected-candidate reuse, the agent directly references the original candidate text and repairs only the faulty fields. The model does not have to regenerate the table from memory.

A page map associates source pages with their document treatment/content. Changing one association should not require retransmitting every unchanged page entry. The exact patch syntax remains open, but the resulting version must reveal what changed and preserve unspecified content.

*Sources: EVT-0826, ATT-20, EVT-1166. Status: settled-boundary.*

<a id="p2-020"></a>
<!-- P2-020 | Candidate workset selection | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-020 — The active candidate must remain usable, but all candidates need not be loaded.**

A correct cross-page table rejected for page metadata may be the best content for continuing its next page. Loading only the old published version or a candidate summary can lose precision and cause redundant reads. The active working candidate may be loaded, pinned, and modified as needed. Other candidates can be indexed. Clearly distinguish current working content from committed content, pending corrections, and competing historical candidates.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-021"></a>
<!-- P2-021 | Stable block identity versus content hash | settled-boundary | EVT-0560,ATT-12 -->
**P2-021 — Logical identity and immutable content are different.**

A table remains the same table after its text changes, while its hash changes. Identical paragraphs at separate positions may be distinct blocks. `{block_id: table_01, content_ref: sha256:...}` preserves edit/pin/relationship identity while permitting content reuse. A sequence of bare hashes does not. This representation does not force paragraph-sized blocks. The agent may operate on a complete table or chapter.

*Sources: EVT-0560, ATT-12. Status: settled-boundary.*

<a id="p2-022"></a>
<!-- P2-022 | Rebase and conflicts | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-022 — Disjoint block IDs do not establish semantic independence.**

A header-unit edit and a numerical-row insertion can conflict despite different targets. So can reordering versus page-map changes or removed images versus added references. Rebase previews may show structural, asset, page-map, and known dependency changes for agent judgment. A stale base must not silently overwrite current work. Preserve the candidate and explain differences. Generic automatic semantic rebase or a large dependency graph is not required.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-023"></a>
<!-- P2-023 | Single content authority | settled-boundary | EVT-0534,EVT-0826,EVT-1166 -->
**P2-023 — Immutable version files are the preferred body authority.**

Final consolidation places document body content in immutable files and version registration, pointers, and operation receipts in SQLite. It avoids a second independently mutable body copy. Earlier full-JSON-per-revision and content-addressed block layouts are storage options, not required schemas. Unchanged blocks may be reused. Versioned saving, reopening, preview, and export must select the same intended content identity.

*Sources: EVT-0534, EVT-0826, EVT-1166. Status: settled-boundary.*

<a id="pins-references-and-retention"></a>
## Pins, source references, and evidence retention

<a id="p2-024"></a>
<!-- P2-024 | Pin metadata ownership | settled-boundary | EVT-0432,ATT-07 -->
**P2-024 — Agent intent and system bookkeeping have separate owners.**

The agent expresses target, purpose, and possible release condition. The app maintains version/hash, deletion/lineage observations, exact bytes/dimensions, and model-dependent cost estimates. Requiring agents to manually maintain every cost or derived field creates avoidable work. Local byte counts can be exact. Token and image-input costs are not universally exact.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-025"></a>
<!-- P2-025 | Fixed and following references | settled-boundary | EVT-0432,EVT-0459,EVT-0479,ATT-07,ATT-08,ATT-09 -->
**P2-025 — Fixed snapshots and following references have different meanings.**

Preserve a problematic OCR or old draft for comparison by fixed version. A current header may follow a defined logical identity on a specified working-draft or committed track. One-to-one replacement does not prove unchanged purpose. A “small text edit” does not prove harmlessness. Changing `mg` to `μg`, adding a negation, or changing one digit can transform meaning without structural change.

Reveal relevant changes rather than silently declaring compatibility. Split/merge/delete may need explicit repinning while the previous snapshot remains accessible.

*Sources: EVT-0432, EVT-0459, EVT-0479, ATT-07, ATT-08, ATT-09. Status: settled-boundary.*

<a id="p2-026"></a>
<!-- P2-026 | Change disclosure and request-fixed references | corrected-proposal | EVT-0479,EVT-0507,EVT-0674,ATT-09,ATT-10,ATT-15 -->
**P2-026 — Do not confuse sent diffs with understood state.**

Repeating full before/after diffs every round inflates input. A `last_disclosed_revision` can describe delivery, not model processing or comprehension. Each request resolves following references to fixed versions and records that choice. Ensure needed current content is available after compaction. Prior diff delivery is not the only route to current state. Exact full diffs remain retrievable.

*Sources: EVT-0479, EVT-0507, EVT-0674, ATT-09, ATT-10, ATT-15. Status: corrected-proposal.*

<a id="p2-027"></a>
<!-- P2-027 | No implicit release from page state | settled-boundary | EVT-0459,EVT-0479,EVT-0507,EVT-0560,EVT-0826,ATT-08,ATT-09,ATT-10,ATT-12,ATT-20 -->
**P2-027 — Unpinned, saved, old, or unflagged does not mean irrelevant.**

P0–P3, Focus Decay, “saved with no issue,” and default release of evidence omitted from `keep_evidence_ids` were repeatedly rejected as hard semantic rules. A survey of 30 pages may precede reconstruction. Keeping all uncommitted evidence resident punishes that valid method. Conversely, writing pages 10–11 does not prove pages 13–15 can leave: an abbreviation or table footnote may be there. Missing issue registration is not proof of no dependency. Pins are strong signals, not a requirement to label every useful item.

The rejected P0–P3 proposal assigned these categories:

* P0: the current requested focus and explicit pins.
* P1: inspected-but-unwritten pages.
* P2: the most recent one or two neighboring written pages.
* P3: older written pages without a registered issue.
It attempted to make P0/P1 automatically resident and P3 eligible for release. The later “Focus Decay” proposal similarly inferred retention from writing pages 10–11. It would keep only those pages and page 12. It would replace pages 13–15 with small indexes unless they were pinned or linked to a registered issue.

Both used convenient work-state signals as though they established semantic need. The retained idea is to expose those signals as selection help. The rejected inference is that they prove what may disappear from the next input.

*Sources: EVT-0459, EVT-0479, EVT-0507, EVT-0560, EVT-0826, ATT-08, ATT-09, ATT-10, ATT-12, ATT-20. Status: settled-boundary.*

<a id="p2-028"></a>
<!-- P2-028 | Retention signals without fixed workflow | proposal | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-028 — Use signals to help the agent choose, not to dictate scope.**

Current requests, explicit pins, unresolved dependencies, recent use, neighboring pages, and drafted status can inform candidates and priorities. Nearby one or two pages are only clues. A dependency may be ten pages away.

The app observes capacity and offers candidates. The agent judges relevance and records needed findings/references. The app applies agreed choices. This requires no routine human approval, mandatory pin register, fixed page window, or extra handoff after every edit.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: proposal.*

<a id="p2-029"></a>
<!-- P2-029 | Source link versus residency | settled-boundary | EVT-0789,ATT-19,ATT-20 -->
**P2-029 — Source linkage, unresolved work, and explicit residency are three relationships.**

A note or draft citing a page image protects provenance and a precise retrieval path. An open issue protects its question and dependency state. An explicit pin requests designated content in the working input. A table's source reference alone does not require a 4 MB image on every call. Mechanical checks can verify valid references and declared retention. They do not decide semantic necessity.

*Sources: EVT-0789, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-030"></a>
<!-- P2-030 | Evidence release and history compaction | settled-boundary | EVT-0595,EVT-0826,ATT-13,ATT-20 -->
**P2-030 — Releasing evidence and consolidating history are independent actions.**

Moving an unnecessary retrievable image out of input need not call another model, rewrite all notes, or create an epoch. Consolidating old conversations must preserve effective requirements, decisions, rationale, unfinished work, and precise retrieval. Evidence management does not replace ordinary history compaction. Optional explicit `context_delta` may accompany a document save. Omitting it preserves prior decisions rather than authorizing release.

*Sources: EVT-0595, EVT-0826, ATT-13, ATT-20. Status: settled-boundary.*

<a id="p2-031"></a>
<!-- P2-031 | Immediate and deferred release | proposal | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-031 — Permission to release later differs from an instruction to remove next turn.**

`evict_when_needed` can allow batching releases for capacity or cache reuse. `drop_immediately` expresses an agent choice to remove stale, wrong, or distracting evidence in the next input even if capacity is ample. The app must not delay that choice solely to preserve cache. Both remove active exposure while preserving original data and history.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: proposal.*

<a id="navigation-and-work-awareness"></a>
## Navigation, coverage, and work awareness

<a id="p2-032"></a>
<!-- P2-032 | Evidence stubs | corrected-proposal | EVT-0534,ATT-11 -->
**P2-032 — A stub is a retrieval aid, not a guarantee against forgetting.**

A short receipt can identify page, candidate table, bottom small-print region, and precise access. Heuristics may miss the important footnote. A 100-character stub cannot guarantee preservation of relationships. Complete indexes persist and can be searched by page/type/text/ID.

Active context keeps useful entries and unresolved dependencies. It need not retain one stub for every prior call forever. A handoff must be able to consult originals, not recursively summarize only older stubs.

*Sources: EVT-0534, ATT-11. Status: corrected-proposal.*

<a id="p2-033"></a>
<!-- P2-033 | Rollup maps and bucket indexes | corrected-proposal | EVT-0560,EVT-0595,ATT-12,ATT-13 -->
**P2-033 — Navigation can be compact without a fixed-size guarantee.**

Alternating completed/uncompleted pages defeat contiguous rollups: 300 pages can still yield nearly 300 ranges. Twenty-five-page buckets reduce display detail but `O(N/25)` is still `O(N)`, not constant memory. Twelve lines for one 300-page book do not prove all books fit 10–20 lines or 400 tokens. Expandable chapter/range views and selected buckets are useful. One or two active buckets must not restrict cross-range work. Counts do not replace exact coverage records.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-034"></a>
<!-- P2-034 | Coverage versus findings and delivered scope | settled-boundary | EVT-0432,EVT-0560,EVT-0759,ATT-07,ATT-12,ATT-18 -->
**P2-034 — Distinguish extracted, delivered, drafted, and understood.**

The app can know results were produced, a particular scope entered a request, and a version cites them. It cannot infer comprehension. “Inspected but unpublished” is a useful reminder, not semantic protection. A compact entry such as “pages 15–20: draft pending; OCR/layout available via manifest” avoids confusing already-extracted pages with unextracted pages.

List actual successful ranges and warnings. Availability does not prove completeness or correctness. Cross-page meaning such as “page 15 footnote governs pages 12–14” requires an explicit finding, not a mechanical coverage statistic.

*Sources: EVT-0432, EVT-0560, EVT-0759, ATT-07, ATT-12, ATT-18. Status: settled-boundary.*

<a id="p2-035"></a>
<!-- P2-035 | Pending manifests across compaction | settled-boundary | EVT-0730,ATT-17 -->
**P2-035 — Unseen evidence can cross context boundaries through precise range indexes.**

Do not invent a content summary of raw text never obtained. But operation facts (“the tool produced pages 15–20”) may be summarized without reading all content. Keep unfinished scope and an immutable manifest entry. Do not force every unhydrated evidence directory into every request.

Already-written notes may remain useful even if their source is not rehydrated in the compaction call. Unfinished chapters may be compacted. Agents may release unrelated or duplicate references even before fully opening them, while originals remain retrievable.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="capacity-and-handoff"></a>
## Capacity accounting, oversized results, and handoff

<a id="p2-036"></a>
<!-- P2-036 | Persistence versus model admission | settled-boundary | EVT-0432,ATT-07 -->
**P2-036 — Saving complete results is separate from admitting them to a model input.**

Full evidence, execution outcome, and version receipts can be persisted immediately. Once the tool batch is complete, a shared assembler allocates the next request's total budget. A separate pending buffer can be a reference, not another giant data copy. Checking at request assembly is not inherently too late if every model request passes that boundary. Per-tool wrappers cannot each claim the same remaining capacity.

*Sources: EVT-0432, ATT-07. Status: settled-boundary.*

<a id="p2-037"></a>
<!-- P2-037 | Large-result envelopes | settled-boundary | EVT-0432,EVT-0459,EVT-0560,ATT-07,ATT-08,ATT-12 -->
**P2-037 — Report execution and delivery separately.**

A result can be successfully saved yet not fully expanded, or a multi-page operation can partly succeed. Keep per-part outcomes, evidence identity/hash/size, requested representation, actual loaded pages/fields/regions/images, omitted scope, warnings, and exact read methods. Define whether “full” means the requested representation or raw original. A navigation receipt is not proof the full evidence entered the request. Every formal tool call still receives a protocol-valid result before a handoff/model turn. Incomplete pairings cannot be hidden in a compaction transition.

For example, an OCR request for pages 15–20 can finish and persist all six pages. The next model input may select only pages 19–20. The tool outcome is successful for 15–20. The input view says that 19–20 were delivered and that 15–18 remain saved but unexpanded.

If page 18 actually failed extraction, that is a separate execution failure. Do not describe it as merely an omitted view. A useful result envelope makes these facts visible together and provides an exact way to retrieve the saved pages. This is an explanation of the required distinctions, not a fixed envelope schema or a rule that only two pages may be loaded.

*Sources: EVT-0432, EVT-0459, EVT-0560, ATT-07, ATT-08, ATT-12. Status: settled-boundary.*

<a id="p2-038"></a>
<!-- P2-038 | No mandatory stage ladder | corrected-proposal | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-038 — Capacity actions can be combined according to need.**

Representation changes, releasing already-unneeded evidence, exact range reads, and history handoff are options, not a compulsory four-stage conversion process. Crossing a soft watermark alone need not force a handoff. A single result can exceed an otherwise empty window, so neither deferred admission nor compaction guarantees eventual full expansion. The 55% + 35% example usefully motivated preflight, but cannot establish “100% handshake space” for every input.

In that example, a proposed early-handoff watermark was 65% of the window. Existing input used 55%. One batch of four pages' images/layout added another 35%. This took the next input to 90% before allowing for a handoff request and output. The useful lesson was to save the whole batch and check its assembled contribution before exposing it to another model call.

The proposal's guarantee was too strong. Deferring the batch does not prove that old history plus control messages and handoff allowance fit. Nor does it prove that the deferred batch will fit a fresh context. A receipt/reference avoids an uncontrolled expansion. It does not create capacity.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: corrected-proposal.*

<a id="p2-039"></a>
<!-- P2-039 | Capacity components and actual requests | settled-boundary | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-039 — Count the complete assembled request and required output reserve.**

System instructions, tool schemas, roles/message wrappers, all active historical images, current evidence, working state, previous assistant output/tool calls, and output/handoff allowance affect capacity. JSON characters, bytes, image MB, and pixels are not interchangeable with tokens. Each selected route needs configurable capacity/output reserve. No universal percentage or optimal watermark study is required. “Previous usage + new text” only applies when the actual prior composition remains compatible. Compaction, projection changes, route/image changes, and omitted history invalidate that shortcut.

Three quantities answer different questions:

* Stored evidence size says how much original material exists.
* Active-input contribution says how much material the request selects, including any repeated appearances.
* Estimated remaining room subtracts the whole assembled input and required output allowance from the chosen route's available capacity.

Thus a large saved OCR file can contribute nothing when unselected. A small passage repeated in several messages contributes repeatedly. A request also has a byte size independently of its token estimate. Unknown route limits or uncertain image accounting remain visibly unknown/estimated. They must not appear as an exact “safe remaining” count.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-040"></a>
<!-- P2-040 | Estimation and calibration uncertainty | corrected-proposal | EVT-0560,EVT-0595,EVT-0638,ATT-12,ATT-13,ATT-14 -->
**P2-040 — Calibration remains an estimate, not a proven upper bound.**

Bind usage to route/model/protocol/image mode and exact request. Applicable local tokenizers and known image rules help. UTF-8/CJK factors, base64 length, pixel area, recent max ratios times 1.05/1.15, and text/vision split calibration do not mathematically bound the next request. A text-heavy sample can hide badly underestimated image cost.

“No new images” may still include old images. Subtracting text deltas does not isolate image cost if other inputs/routing changed. A 1,500–2,500-token image allowance is not universal. Preserve uncertainty and recoverable overflow behavior without paid calibration probes as a prerequisite.

*Sources: EVT-0560, EVT-0595, EVT-0638, ATT-12, ATT-13, ATT-14. Status: corrected-proposal.*

<a id="p2-041"></a>
<!-- P2-041 | Handoff allowance and gradual compaction | corrected-proposal | EVT-0560,EVT-0595,ATT-12,ATT-13,EVT-1166 -->
**P2-041 — Plan for the actual sequence of normal output and handoff.**

If a normal turn generates content before handoff, `max(normal_output, handoff_output)` alone may omit the new assistant content, tool receipts, and handoff prompt. Predictive margins cannot constrain an as-yet unknown tool batch. Re-evaluate afterward. Final consolidation allows consolidation to reduce history progressively: intermediate progress need not already meet the final normal-request budget.

It does not promise that two or three passes always suffice. It does not require retaining a fixed recent K turns. It does not require superseding an old draft before it can leave input.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13, EVT-1166. Status: corrected-proposal.*

<a id="p2-042"></a>
<!-- P2-042 | Shared hydration with purpose-specific input | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-042 — Normal inference and handoff share evidence resolution, not necessarily identical contents.**

An auxiliary summarizer that sees only ticket IDs can miss the evidence needed for accurate continuation. Both paths should resolve references, fixed versions, and declared projections through the same mechanism and record their actual input. Conversely, requiring all active evidence to be hydrated before compaction recreates the overflow that triggered compaction. Each request receives the relevant content that fits its purpose and capacity. Originals stay directly accessible without summary approval.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-043"></a>
<!-- P2-043 | Handoff failure and recovery context | settled-boundary | EVT-0560,EVT-0595,ATT-12,ATT-13 -->
**P2-043 — Failed handoff preserves original records and has a finite outcome.**

When old context remains usable, retain it and respond to the actual failure. If old context is genuinely unavailable or normal capacity handling cannot make it usable, the app may create a clearly labeled recovery context. This context may carry effective requirements, current artifacts, valid notes, recent activity, candidates, and exact retrieval. It may require renewed source inspection. There is no guarantee of complete internal reasoning or lossless semantic continuation.

If even required controls and a workable minimum do not fit, save work. Stop with a concrete capacity blocker rather than retry forever. Process restart alone does not justify recovery-context replacement.

The intended restart order is:

1. Load the original supported session/checkpoint.
2. Reconcile known document/tool effects.
3. Resume from the original position if that state remains usable.
A new recovery summary is a fallback for a specific unavailable/invalid context, not the default restart mechanism. Otherwise a normal process restart would itself discard recent useful details that the mature runtime already preserved. A failed compaction also needs capacity reassessment before the next normal send. Preserving the originals and immediately resending their unchanged oversized projection does not solve the failure.

*Sources: EVT-0560, EVT-0595, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-044"></a>
<!-- P2-044 | Mechanical eviction rejection | corrected-proposal | EVT-0560,ATT-12,EVT-1166 -->
**P2-044 — “Save all assistant text, evict saved pages” is not a safe universal fallback.**

All assistant text, tool arguments, notes, and drafts may themselves overflow. A saved page with no flagged issue may still supply an unresolved table header/footnote. The app preserves observable records, not hidden mental state. Later consolidation prefers a self-sufficient handoff with effective requirements, unfinished work, and exact references over fragile delta notes. The latest draft and unfinished candidates may partially leave input while their originals remain retrievable. None is permanently pinned merely by being latest.

A self-sufficient handoff:

* States the current requested scope and fidelity constraints.
* Identifies the selected draft/version and useful candidates.
* Records decisions needed to interpret them.
* Names remaining work with exact retrieval references.
The cross-page-table example needs two findings. Page 16's first row continues the preceding table. A particular value remains uncertain and was not adopted. “continued table_02; see previous notes” is insufficient if those notes leave active history.

The handoff can reference the complete table and source pixels instead of copying them all. It preserves the known relationship and retrieval path without claiming to preserve an unexpressed thought or to fit every handoff into one fixed-size summary.

*Sources: EVT-0560, ATT-12, EVT-1166. Status: corrected-proposal.*

<a id="p2-045"></a>
<!-- P2-045 | Token versus HTTP byte limits | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-045 — HTTP payload size and model context are separate limits.**

HTTP 413 says a server/proxy refuses that request size. It does not reveal token capacity. The proposed 15/20 MB and 128k/200k figures were examples, not verified Nexus limits. Track actual request bytes and token estimates separately. A rejection does not authorize the transport to remove evidence.

The capacity path must explicitly select a valid view under existing relevance decisions and budgets. It must record actual requests and expose omissions.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-046"></a>
<!-- P2-046 | Zero-fit and nonsequential selection | settled-boundary | EVT-0459,EVT-0789,ATT-08,ATT-19 -->
**P2-046 — The next useful evidence may be noncontiguous, and zero items may fit.**

Always loading the first K pages can discard the useful last-row/next-header pair or comparison of pages 15 and 19. K is not guaranteed to be at least one: a single native image can exceed the available request size. A lightweight capacity envelope can show dimensions, bytes, ranges, and exact selection options, letting the agent choose regions/fields/representations or revise the working set. Mandatory sequential paging and arbitrary biggest-item eviction were rejected.

*Sources: EVT-0459, EVT-0789, ATT-08, ATT-19. Status: settled-boundary.*

<a id="p2-047"></a>
<!-- P2-047 | Capacity error ownership and budgets | settled-boundary | EVT-0759,EVT-0789,EVT-0826,ATT-18,ATT-19,ATT-20 -->
**P2-047 — Capacity recovery needs its own explicit finite control path.**

`before_model` does not automatically catch a downstream capacity exception. A wrapper may make a limited number of handler calls, but “at most two reassemblies” was a policy proposal, not a framework guarantee. Context-limit recovery was not an existing v1 transport retry behavior. Capacity recovery may have separate counting from transport retries. Either way, record every actual send and retain the original round/task/time budgets. A fresh view does not mint attempts or semantic permission to drop needed content.

*Sources: EVT-0759, EVT-0789, EVT-0826, ATT-18, ATT-19, ATT-20. Status: settled-boundary.*

<a id="cache-and-prefix"></a>
## Prompt cache and reusable computation

<a id="p2-048"></a>
<!-- P2-048 | Stable prefix tradeoffs | corrected-proposal | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-048 — Stable prefix is an optimization, not the highest rule.**

Put stable instructions/schemas early when practical and use ordinary tool results for normal changes. Supplement current state on recovery, handoff, or a real gap rather than inject a duplicate full snapshot every turn. Replacing a dynamic tail can break the prior prefix. Appending every snapshot accumulates duplicates.

A fixed epoch baseline plus substantive append-only events and a freshly assembled current view are different legitimate strategies with different cache tradeoffs. They cannot both claim an unchanged prefix and freshly rewritten early state. Update user requirements immediately and explicitly. A revision number alone does not explain what changed.

“Epoch” in the earlier proposal meant a period of work after one context consolidation, beginning with a fixed continuation baseline and then appending later events. It was proposed to preserve a reusable prompt prefix. A “dynamic tail” instead rebuilds current-state content near the end of each request.

Moving or rewriting old prefix content can reduce prefix reuse. Keeping every old snapshot can consume input with stale duplicates. Neither strategy changes the complete retained records. The product choice concerns the actual request projection and whole-task cost, not whether history must be permanently append-only everywhere.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-049"></a>
<!-- P2-049 | Cache evidence and cost | corrected-proposal | EVT-0534,EVT-0826,ATT-11,ATT-20 -->
**P2-049 — Cache ratios do not establish price-weighted task savings.**

The observed roughly 84% cached input is one run, not a promised benefit of epoch/tail design. Prefix identity, cache availability, expiry, routing, repeated outputs, extra reads, and latency all matter. Neither fewer characters nor fewer total tokens alone proves equal-fidelity savings or Nexus billing. A deferred release strategy can preserve reuse, but correctness, current requirements, capacity, and an explicit immediate-removal request take priority.

*Sources: EVT-0534, EVT-0826, ATT-11, ATT-20. Status: corrected-proposal.*

<a id="p2-050"></a>
<!-- P2-050 | Result cache versus operation replay | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-050 — Reuse an existing computation without impersonating its old call.**

A repeated logical operation uses its original receipt and identity. A new call may reuse an earlier evidence result but receives a message paired with the new call ID and records the reused provenance. Reuse should preserve requested completeness when capacity allows. Recovery does not automatically downgrade full OCR to a bare ID. Missing success receipts do not prove no work happened, especially for scripts.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-051"></a>
<!-- P2-051 | Correct computation signatures | proposal | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-051 — Cache identity follows actual computation.**

A useful signature includes fixed source hash, tool/implementation/engine version, resolved defaults, OCR model/language data and their order, DPI, PSM, bbox, annotations, and relevant settings. Tesseract language order can affect output. Whole-call hashes for pages 15–20 and 15–16 differ. Overlap reuse needs an index at independently computable units. A later 19–21 request can reuse 19–20 and compute only 21 when semantics permit. Cross-page analyses cannot automatically be reduced to page cache units.

Source hash plus raw user arguments can therefore be insufficient. Omitted defaults may resolve differently after an engine/configuration change, while the visible arguments stay identical. The signature represents the effective computation, including versions/settings that affect it. It is a computation identity, separate from the new call's operation identity and from the subset eventually selected into model input.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: proposal.*

<a id="p2-052"></a>
<!-- P2-052 | Computation storage and selection granularity | settled-boundary | EVT-0789,ATT-19,ATT-20 -->
**P2-052 — Computation, storage, and selection granularity are independent.**

A six-page immutable JSON may store naturally as one blob while an index maps individual pages or JSON Pointers to independent computations. Context may select only pages 19–20 or certain fields/regions without physically splitting the file. Neither partial release nor overlap caching requires one file per page. A selection must record concrete ranges/fields/view version. `partial` alone cannot reconstruct what was delivered.

*Sources: EVT-0789, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-053"></a>
<!-- P2-053 | Explicit recomputation | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-053 — A cache must not trap the agent in a defective old result.**

Changed settings or explicit `force_recompute` can generate a new evidence identity, retaining old evidence for comparison and notes. If the default cache index points to the newest result, that is a declared selection policy, not a claim that newest means best. Never silently retarget an existing fixed note/reference. Reuse verifies completeness and source/settings identity rather than trusting only the presence of a cached path.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="input-views-and-hydration"></a>
## Input views, hydration, and causal identity

<a id="p2-054"></a>
<!-- P2-054 | Lightweight persistent references and transient hydration | settled-boundary | EVT-0638,EVT-0674,EVT-0789,ATT-15,ATT-16,ATT-19 -->
**P2-054 — Durable state and model-visible messages need not contain the same large payloads.**

Keep large OCR/layout/images in immutable evidence storage. A checkpoint can hold stable references, call pairing, and useful small results. At request time, new transient message objects expand the requested original text/pixels when capacity permits. Small success/error results may stay inline. Not every tool needs a blob round-trip.

`ToolMessage.artifact` was a plausible structured carrier, rather than guessing that arbitrary body JSON resembles a delivery ticket. Preserve message identity and pairing, and avoid accidentally writing expanded payloads back into graph state.

*Sources: EVT-0638, EVT-0674, EVT-0789, ATT-15, ATT-16, ATT-19. Status: settled-boundary.*

<a id="p2-055"></a>
<!-- P2-055 | Hydration limits and native images | corrected-proposal | EVT-0674,ATT-15 -->
**P2-055 — Reference storage does not guarantee a few-kilobyte checkpoint.**

Message counts, notes, assistant arguments, long submitted drafts, and scripts still grow. The design reduces repeated heavy evidence, not all state to a fixed size. “Native image” also does not mean PNG: an original JPEG retains its original format and identity. Successful evidence reuse should fulfill the original requested projection. It should not require another model turn merely to discover that its result was saved.

*Sources: EVT-0674, ATT-15. Status: corrected-proposal.*

<a id="p2-056"></a>
<!-- P2-056 | Actual input identity replaces sequence maximum | settled-boundary | EVT-0674,ATT-15 -->
**P2-056 — An input view records selection, not just the largest event number.**

An input containing event 20's text and event 40's selected fields, while excluding 21–39 and images, cannot be represented as “agent saw everything through 40.” A small immutable `input_view_id`/request manifest identifies requirements, draft and policy versions, included messages/evidence/fields/ranges/image representations, and omitted requested items. It can refer to original files rather than duplicate them. Inclusion in a request proves neither comprehension nor faithful use.

*Sources: EVT-0674, ATT-15. Status: settled-boundary.*

<a id="p2-057"></a>
<!-- P2-057 | Reconstructable app-boundary input | settled-boundary | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-057 — State the reconstruction boundary precisely.**

To reconstruct app-assembled input, preserve:

* Message order/roles.
* Exact tool parameters.
* Prompt/schema versions.
* Model/route settings.
* Selected notes and resolved pins.
* Projections or immutable projection references.
* Image representations.
Hashes validate content but cannot replace missing bytes. The claim is reconstruction at the defined app boundary. It does not prove the provider/Nexus upstream performed no further transformation or expose what the model internally perceived. Optional safe wire descriptions/digests can check adapter encoding without turning context management into a proxy-chain audit.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: settled-boundary.*

<a id="p2-058"></a>
<!-- P2-058 | Input to accepted response to tool chain | settled-boundary | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-058 — Bind each accepted response and tool call to its real input.**

A generated view must travel with the accepted parent response, for example through namespaced app `response_metadata` while preserving provider metadata. A tool binds to that parent response and its call ID, not the latest view in a database. Missing or conflicting linkage is an association error. `additional_kwargs` may contain provider encoding data and is not an arbitrary substitute.

Capture after relevant input modifications. Preserve the full `ModelResponse`. Account for wrappers that call handlers multiple times or return multiple messages.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: settled-boundary.*

<a id="p2-059"></a>
<!-- P2-059 | View request attempt and batch identities | settled-boundary | EVT-0730,EVT-0789,EVT-0826,ATT-17,ATT-19,ATT-20 -->
**P2-059 — A view is not a round, attempt, accepted batch, or activation event.**

Identical frozen input may be retried under multiple attempts. Changed pins/schema/messages/model settings require another view. Neither new view nor outer wrapper call resets the stable logical round's attempt/time budget. Usage belongs to each execution attempt, not a single mutable field on a reusable view. The accepted parent response/tool batch establishes which proposals are eligible for activation. Querying every operation with the same input view can incorrectly include rejected attempts or other branches.

An illustrative chain makes the identities concrete:

1. Logical request Q uses fixed input view V.
2. Transport attempt A fails or has an unknown outcome.
3. An authorized bounded attempt B sends the same frozen Q/V.
4. B yields the complete response R that is accepted locally.
5. R contains tool calls T1 and T2, which form the accepted batch.

Their operations and context-change intents belong to R and its call identities. V describes their input basis. However, V alone does not distinguish attempt A's unaccepted response from R or identify which tools are eligible. Recording a new view to handle capacity still does not erase Q's existing attempts or the task's elapsed budget. These letters illustrate relationships, not a required identifier format or additional database tables.

*Sources: EVT-0730, EVT-0789, EVT-0826, ATT-17, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-060"></a>
<!-- P2-060 | Historical activity is data | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-060 — Compressed historical calls must not masquerade as pending native calls.**

Preserve raw exact parameters separately. A compact activity skeleton can list operations, pages, errors, candidate IDs, and retrieval entries as ordinary historical reference text. Truncated arguments inside native `AIMessage.tool_calls` risk malformed examples and invalid pairing. A read-only label alone cannot prevent execution: dispatch must accept only current formally accepted response/framework-pending calls. Source text and historical summaries are inert. Ordinary schema validation still applies because a model could imitate a historical format.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="notes-and-coverage"></a>
## Working notes and semantic coverage

<a id="p2-061"></a>
<!-- P2-061 | Activity ledger versus semantic work notes | settled-boundary | EVT-0595,EVT-0638,EVT-0674,ATT-13,ATT-14,ATT-15 -->
**P2-061 — Operations tell what happened, not all the reasoning needed to continue.**

“Inspected pages 15–16, changed table_02” omits “page 16's first row continues the prior table; a value remains uncertain and was not adopted.” Likewise a crop bbox gives a selected area, not why it was selected or why an alternative was rejected. A recovery view should draw activity from existing tool/receipt/version records, plus useful explicit notes, messages, errors, and candidates. Avoid a second independent activity ledger. Compact summaries can aid navigation but cannot claim a fixed few-hundred-token size or exact recovery of unexpressed judgment.

*Sources: EVT-0595, EVT-0638, EVT-0674, ATT-13, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-062"></a>
<!-- P2-062 | Notes without compulsory tool conventions | proposal | EVT-0595,EVT-0638,ATT-13,ATT-14 -->
**P2-062 — Preserve important findings during ordinary work without a universal note ritual.**

Agents can save discoveries, unresolved dependencies, conventions, and reasons before full compaction. An append-only prefix policy does not prevent tail note updates. The proposed `note_on_previous_step` on every tool may be convenient but adds schema, output, concurrency, and replay obligations. It is not zero cost.

A separate note tool can accompany a read in one model response. Thus an additional tool call need not mean an additional model turn. Prior non-use does not prove which interface will be adopted.

*Sources: EVT-0595, EVT-0638, ATT-13, ATT-14. Status: proposal.*

<a id="p2-063"></a>
<!-- P2-063 | Note write time input basis and compaction scope | settled-boundary | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-063 — Separate when a note was saved, what input supported it, and what history was replaced.**

In the race example, the model uses input through event 100 and emits an OCR and a note. OCR finishes as 101 before the app saves the note. Automatically setting `covered_up_to_event_seq=101` excludes unseen OCR from recovery. Even without concurrency, a short note about one unit does not summarize all prior work.

Creation/update ordering, exact input-view linkage, and actual compacted message IDs/ranges are separate facts. A normal note never automatically advances a semantic coverage frontier.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-064"></a>
<!-- P2-064 | Operation order is not completion order | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-064 — Mutable operation rows cannot serve as a complete event timeline.**

Operation 100 may be registered before 101 and finish later. Updating row 100 to succeeded then querying `event_seq > 101` loses that new completion. Keep current operation status separately from framework message/checkpoint order and input/compaction identity. If a completion sequence is needed, allocate it inside the result-commit transaction and define it as receipt-commit order. An append-only state-event record is an option only if useful, not an obligation to construct a general event-sourcing system.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-065"></a>
<!-- P2-065 | Versioned notes and concurrency | settled-boundary | EVT-0638,EVT-0674,EVT-0701,EVT-0730,ATT-14,ATT-15,ATT-16,ATT-17 -->
**P2-065 — Note identity and version checks must preserve both current and historical meaning.**

Item-level append/upsert/resolve can avoid whole-note-blob overwrite. However, simultaneous edits to the same note still require an expected version or explicit merge rule. Merely storing `note_rev` does not enforce a check. Old input views referencing revision 3 must still resolve revision 3, through immutable note revisions or saved content references.

User requirements, source facts, and agent judgments stay distinct. Notes cannot quietly rewrite requirements. Independent task databases reduce accidental mixing but still require correct source/workspace identity.

*Sources: EVT-0638, EVT-0674, EVT-0701, EVT-0730, ATT-14, ATT-15, ATT-16, ATT-17. Status: settled-boundary.*

<a id="state-authority-and-policy-activation"></a>
## State authority, policy activation, and conflicts

<a id="p2-066"></a>
<!-- P2-066 | Orthogonal authorities | settled-boundary | EVT-0479,ATT-09 -->
**P2-066 — A context manifest describes one input, not all committed reality.**

If document revision 4 and its success receipt commit while a context manifest still references 3, a crash cannot make revision 4 nonexistent. Document/version receipts establish committed edits. Evidence storage establishes saved results. Session records establish exchanges. Context manifests establish versions/content selected for an input.

Recovery reconciles these roles. Unreferenced by one context means not included there, not unexecuted, unsaved, or valueless. Atomic replacement of a manifest pointer, including Windows `ReplaceFileW`, cannot create a transaction across independent stores.

The historical “four-store reconciliation” phrase referred to four logical questions:

* What did the model/session exchange?
* What did the document service commit?
* What evidence was saved?
* What did the context select?
They can share physical storage where useful. The failed “single manifest authority” proposal would have treated writes absent from the active manifest as ineffective. That would discard knowledge of a real document commit merely because a later context update did not finish. The corrected design gives each fact one owner and reconciles references between them. An input snapshot can select an older version for comparison while the document service correctly reports a newer head.

*Sources: EVT-0479, ATT-09. Status: settled-boundary.*

<a id="p2-067"></a>
<!-- P2-067 | CAS and self-produced updates | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-067 — A context swap must distinguish external drift from its own new notes.**

Capturing notes revision 5, writing handoff notes as 6, then requiring all revisions still equal their original values incorrectly rejects the handoff's own update. Separate read base and staged changes. Check competing changes at the real commit point. Commit the appropriate note/policy state coherently. A hook that sequentially writes two independent stores is not a joint transaction. The precise manifest schema was an implementation proposal, not a requirement.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-068"></a>
<!-- P2-068 | Requirement changes during handoff | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-068 — New human instructions govern continuation immediately.**

Preserve original requirement revisions and explicit changes. Source observations may remain valid while old plans or candidates require reevaluation. If pages 15–20 leave scope, merely appending a high-priority version label does not prove the old plan is harmless. Preserve useful unaffected evidence and candidates. “needs reevaluation” is often more accurate than declaring all affected content invalid. Pause/cancel must not require an additional model handoff first.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-069"></a>
<!-- P2-069 | Why maximum revision loses branches | settled-boundary | EVT-0730,ATT-17 -->
**P2-069 — A larger policy revision does not contain another branch's changes.**

From policy 7, A creates 8 to pin a page-12 header, while B creates 9 to release an OCR without A's pin. Choosing `max(8,9)` silently loses the pin. Check expected parent and operation identity where state is actually accepted. “both tools checked 7 before execution” is insufficient. Restore the version associated with the selected checkpoint branch, not the database's global newest number. This rejects timestamp/maximum-number selection as a substitute for ownership and lineage.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-070"></a>
<!-- P2-070 | SQLite serialization does not serialize graph commands | corrected-proposal | EVT-0759,ATT-18,EVT-0878 -->
**P2-070 — Two individually serialized database writes can still race in graph state.**

In the historical external-policy proposal, A could commit policy 8 and B policy 9 in SQLite. Both could return `Command(active_policy_rev=...)` in the same superstep. Graph state could reject concurrent updates or accept an unintended order. Adding `current_active_rev` in SQLite while checkpoint state also owned the pointer recreated competing authorities.

EVT-0878 subsequently simplified the single built-in executor. The design places the small context policy and processed context-change batches in Graph State. It settles tool-reported intents at one point and excludes the unnecessary external policy-version/activation tables.

Parallel replacement of whole policy values can still overwrite changes. Reducers do not infer pin/release meaning. The retained boundary is one state authority and one settlement writer, independent of the final graph node names.

*Sources: EVT-0759, ATT-18, EVT-0878. Status: corrected-proposal.*

<a id="p2-071"></a>
<!-- P2-071 | Activation versus request hydration | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-071 — Durable policy decisions and transient payload expansion belong at different boundaries.**

In the historical `create_agent` design, `wrap_tool_call` saved effects/proposals and replayed completion. A sequential `before_model` step settled lightweight state. `wrap_model_call` expanded content, checked capacity, and recorded the input view. Returning huge hydrated messages from `before_model` would persist them into state, undoing reference-based storage. The final architecture may name nodes differently. The separation remains the useful contract.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="p2-072"></a>
<!-- P2-072 | Batched intent resolution | corrected-proposal | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-072 — Same-batch local intents are possible without generic semantic rebase.**

Requiring one complete context proposal was a conservative race avoidance suggestion, not proof of semantic correctness. Same accepted tool batch may submit local pin/release intents for one sequential settlement. Validate the merged target state: `pin_remove(ev03)` plus `release(ev03)` can be coherent. Conflicting add-pin/release requires an explicit result. Do not always let pins win by iteration order.

Different object IDs do not establish independence or spare capacity. The agent owns semantic choices. General automatic linear intent rebasing remained outside first-version necessity.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: corrected-proposal.*

<a id="p2-073"></a>
<!-- P2-073 | Idempotent activation itself | superseded | EVT-0789,EVT-0826,ATT-19,ATT-20,EVT-0878 -->
**P2-073 — The external-policy activation proposal exposed a real replay problem, then was simplified.**

Under that historical proposal, SQLite could create policy 8 before graph state persisted its pointer. The proposal intended a stable accepted-batch identity, original parent, and proposal set to recover the same settlement. It would avoid creating another policy from all completed database operations. Tool results could carry explicit proposal IDs. `hash(current_parent, sorted_proposals)` alone was insufficient: after 7 became 8, the same proposals would form another key unless the accepted batch was already recorded as settled.

Policy-content deduplication and activation-event identity were distinct, and prepared but unactivated policies could exist. EVT-0878 superseded the separate external policy-version/activation machinery with small policy and processed-batch state in Graph State, updated together at one settlement point.

Stable batch settlement remains relevant. An external activation receipt store is not a V1 requirement. Receipts for actual document/tool effects and sent model requests still retain their separate purpose.

*Sources: EVT-0789, EVT-0826, ATT-19, ATT-20, EVT-0878. Status: superseded.*

<a id="p2-074"></a>
<!-- P2-074 | Request-pinned policy and references | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16,EVT-0878,EVT-1166 -->
**P2-074 — Reconstruct a real selected state, not independently latest components.**

The earlier external-policy design used an immutable policy revision and a branch-selected reference. EVT-0878 replaces that storage mechanism with compact policy in Graph State for the single built-in executor. In either representation, resolve `follow_latest` into fixed versions for each model request. Independently choosing newest checkpoint, policy, notes, draft, and evidence can assemble a state that never existed.

Final consolidation requires one owner for each model request, batch progress, document version, and operation receipt. It also requires one active task writer. It does not require an external policy-version table, a particular seven-table schema, or full distributed coordination platform.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16, EVT-0878, EVT-1166. Status: settled-boundary.*

<a id="persistence-and-replay"></a>
## Persistence, operation identity, and replay

<a id="p2-075"></a>
<!-- P2-075 | SQLite short transactions and immutable files | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-075 — Four logical responsibilities do not require four independent stores.**

SQLite can hold version registration, artifact references, receipts, notes, and metadata, while large bodies/evidence remain immutable files. Shared transactions cover database records only, not external blobs or framework sessions/checkpoints. WAL is a useful option, still with one writer. Synchronization/checkpoint settings affect latency and durability. “Under one millisecond” was unmeasured. Table count and all-JSON-row layouts were provisional proposals, not architecture proof.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-076"></a>
<!-- P2-076 | Prepare files before references and protect prepared work | settled-boundary | EVT-0534,EVT-0560,EVT-0595,EVT-0638,EVT-0730,ATT-11,ATT-12,ATT-13,ATT-14,ATT-17 -->
**P2-076 — Finish immutable files before committing references to them.**

Blob-first preparation/verification followed by the database transaction reduces dangling committed references. Framework acknowledgement can occur later. It is not a universal two-phase distributed transaction or absolute filesystem durability guarantee. Unreferenced prepared files may still belong to an in-progress or recoverable operation.

TTL leases need renewal for long operations. A simpler early implementation can avoid background deletion. No active process does not mean no useful prepared work: startup must identify recoverable tasks before cleanup. These are preservation principles, not a new cleanup project.

*Sources: EVT-0534, EVT-0560, EVT-0595, EVT-0638, EVT-0730, ATT-11, ATT-12, ATT-13, ATT-14, ATT-17. Status: settled-boundary.*

<a id="p2-077"></a>
<!-- P2-077 | Stable logical operation identity | settled-boundary | EVT-0507,EVT-0534,EVT-0638,EVT-0674,EVT-0730,ATT-10,ATT-11,ATT-14,ATT-15,ATT-17 -->
**P2-077 — An app operation is more than a provider tool-call string.**

Persist exact accepted call parameters and a scoped stable operation identity before executing effects. Link parent accepted response, task/thread, namespace, framework call, and input view consistently. Include the parent response unless call-ID uniqueness across the entire scope is guaranteed.

Retrying the same operation preserves identity. A changing run/attempt ID must not turn it into a new operation. The app rejects the same identity with different tool/parameters/fixed inputs. Summary arguments alone cannot prove equality.

*Sources: EVT-0507, EVT-0534, EVT-0638, EVT-0674, EVT-0730, ATT-10, ATT-11, ATT-14, ATT-15, ATT-17. Status: settled-boundary.*

<a id="p2-078"></a>
<!-- P2-078 | Idempotent receipts and current head | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-078 — Replay returns what happened then without rolling current state backward.**

Commit a document version and its receipt coherently. An identical replay returns the original result rather than inserting twice. A receipt saying “produced revision 4” may coexist with current head 5. Report both as distinct facts. A new call with `expected_rev=3` after 4 exists is blocked by version checking, so it is a usability/reconciliation problem rather than proof of duplicate writing. Historical completion must not reset current pointers.

Consider an accepted append operation prepared from revision 3. The document service saves revision 4 and its operation receipt, then the process stops before the graph records the tool completion. On resume, the framework may invoke the pending operation again. Matching its stable identity and exact parameters returns the receipt for revision 4 instead of appending twice. If later valid work has already advanced head to revision 5, returning that historical receipt still does not set head back to 4.

If the model creates a different call after restart, it is a new operation. Its stale expected head can be rejected and its content retained for reconciliation. Neither receipt replay nor content-hash equality authorizes treating that new call as the old operation. This example explains the boundary, not a requirement to manually scan and reinject every past receipt.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-079"></a>
<!-- P2-079 | Content hash deduplication boundaries | corrected-proposal | EVT-0534,ATT-11 -->
**P2-079 — Content hashes identify exact payload equality, not semantic intent or operation identity.**

Optional `(base_revision, payload_hash)` deduplication must be scoped by document, operation kind, target, complete change, fixed referenced contents/assets, and base. Stable logical operation identity is separately scoped to its accepted response and batch. A content hash does not supply it.

Identical table text inserted at different positions can be two valid operations. “Nearly identical” regeneration will not hash equally. Prefer preserving accepted calls and reconciling saved effects before asking the model to reconstruct an action. Optional exact deduplication does not establish a general intent recognizer.

*Sources: EVT-0534, ATT-11. Status: corrected-proposal.*

<a id="p2-080"></a>
<!-- P2-080 | Full completion replay including graph updates | corrected-proposal | EVT-0701,EVT-0730,ATT-16,ATT-17,EVT-0878 -->
**P2-080 — A tool's completion may contain more than its visible receipt.**

The historical external-policy example replayed only `ToolMessage` after app policy 8 was saved but `Command(update={active_policy_rev:8})` was not checkpointed, leaving graph policy 7 active. That particular external policy/command mechanism was superseded by EVT-0878's compact Graph State policy and centralized settlement. The underlying completion lesson remains: preserve the committed domain result and any necessary supported state-update semantics. Reconstruct an equivalent completion without regressing newer state.

Stable message identities and expected versions help avoid duplicates/regression. A design that persists only `Command.update` must explicitly limit supported forms. `goto`/`graph` cannot silently disappear. The final direct graph can concentrate state writes and reduce this machinery, while retaining the completion effects it actually supports.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17, EVT-0878. Status: corrected-proposal.*

<a id="p2-081"></a>
<!-- P2-081 | Stable message IDs do not resurrect safely | settled-boundary | EVT-0730,ATT-17 -->
**P2-081 — Stable message IDs only deduplicate messages still present.**

`add_messages` replaces an existing same-ID entry. If compaction removed it, replay adds it again. Do not scan every successful receipt and re-inject historical messages, potentially orphaning ToolMessages. Let the runtime determine actual pending work, then reuse the corresponding receipt/completion when that work is invoked. Message identity is one aid, not a universal exactly-once or safe-history-replay guarantee.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-082"></a>
<!-- P2-082 | Framework resume and pending writes | settled-boundary | EVT-0595,EVT-0638,EVT-0759,ATT-13,ATT-14,ATT-18 -->
**P2-082 — Use supported framework recovery rather than rebuild its scheduler.**

Load session/checkpoint, reconcile effects, and continue the original state if usable. LangGraph has public state/history access and pending writes. The checked `create_agent` dispatched separate tools with `Send("tools", [tool_call])`. An unfinished superstep therefore does not prove every completed OCR must rerun.

`StateSnapshot.tasks` contains `PregelTask` descriptions, not a guaranteed executable tool-call array. Use the runtime resume entry. When it actually invokes a tool, the wrapper checks its receipt. State snapshots serve diagnostics/status/checkpoint selection rather than a second scheduler.

*Sources: EVT-0595, EVT-0638, EVT-0759, ATT-13, ATT-14, ATT-18. Status: settled-boundary.*

<a id="p2-083"></a>
<!-- P2-083 | Expensive tool result reuse | proposal | EVT-0638,ATT-14 -->
**P2-083 — Saved OCR/render outputs can bridge the remaining effect/checkpoint gap.**

The design prefers framework completion records. App results can cover the interval after an expensive tool finished but before its completion was durably recorded. Reuse checks source version, exact settings, and result completeness. This is useful even though “all tools always replay after a superstep crash” was false. It need not force every tiny operation through the same subprocess or blob machinery.

*Sources: EVT-0638, ATT-14. Status: proposal.*

<a id="p2-084"></a>
<!-- P2-084 | Acknowledgement timestamps and lazy observation | corrected-proposal | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-084 — Returned, observed, persisted, sent, and understood are distinct.**

`returned_to_session_at` can be empty after the framework saved a result but before app timestamp update, or filled before framework persistence if ordered the other way. A hook seeing a result is not itself proof it survives a crash. Lack of a result in compacted active input is not evidence it was never delivered. Lazy acknowledgement can optimize common cases, backed by stable session/checkpoint identities and supported public-state reconciliation. Timestamps are observations, not joint transactions or proof of comprehension.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: corrected-proposal.*

<a id="p2-085"></a>
<!-- P2-085 | Persistence modes and original budgets | settled-boundary | EVT-0560,EVT-0638,EVT-0730,ATT-12,ATT-14,ATT-17,EVT-1166 -->
**P2-085 — State the persistence and budget boundaries explicitly.**

A named SQLite checkpointer does not determine durability: `sync`, `async`, and `exit` have different crash protection. A complete accepted response, each tool effect, and graph progress may be durable at different times. Recovery retains original persistent attempts/time budgets and does not re-publish a saved version. Final consolidation asks for explicit behavior at four boundaries: request saved, response accepted, tool committed, and graph recorded. Arbitrary hard-crash or all-old-job recovery is not assumed.

These boundaries describe what is known at interruption. A saved request can supply frozen input and its existing budget, but does not by itself prove whether a remote attempt ran. An accepted response supplies the complete tool-call batch eligible for dispatch. A committed tool effect supplies its own durable result/receipt even if graph acknowledgement is missing. Recorded graph progress supplies the framework's continuation state, while earlier external effects remain facts that checkpoint rollback cannot undo.

Synchronous, asynchronous, and exit-time checkpoint saving determine when that last record becomes durable. Merely naming SQLite does not select the mode. The unresolved contract is finite behavior at these transitions, not a requirement to build a distributed transaction across the provider, database, and files.

*Sources: EVT-0560, EVT-0638, EVT-0730, ATT-12, ATT-14, ATT-17, EVT-1166. Status: settled-boundary.*

<a id="subprocesses-and-salvage"></a>
## Subprocesses, unknown outcomes, and useful partial work

<a id="p2-086"></a>
<!-- P2-086 | Working directories are not OS sandboxes | settled-boundary | EVT-0674,ATT-15 -->
**P2-086 — Per-attempt directories provide organization and provenance.**

Pointing cwd/environment at `script_runs/<operation_id>/out` does not prevent absolute-path or parent-directory writes. Trusted scripts execute with host-user permissions. Directory separation is not an OS sandbox or automatic read-only enforcement. Full reconstruction does not silently change that security model. Any genuine restricted execution boundary needs a separately chosen mechanism, not a relabeled working folder.

*Sources: EVT-0674, ATT-15. Status: settled-boundary.*

<a id="p2-087"></a>
<!-- P2-087 | In-flight unknown states | settled-boundary | EVT-0674,EVT-0701,ATT-15,ATT-16 -->
**P2-087 — A missing completion marker does not prove nonexecution.**

`in_flight`/`spawning` can mean registered-before-launch, running, completed-before-receipt, or interrupted with partial output. The controller can crash after launch but before recording running, or after completion but before writing `_exit_status.json`. Nonzero exit can be an ordinary failure with reusable output. Even a zero exit and matching hashes do not prove scope/contract completion. Keep unknown states honest. Logical operations and physical attempts are distinct, and each real subprocess attempt can retain process identity, working directory, logs, and outputs.

*Sources: EVT-0674, EVT-0701, ATT-15, ATT-16. Status: settled-boundary.*

<a id="p2-088"></a>
<!-- P2-088 | Job objects and launch gaps | corrected-proposal | EVT-0701,EVT-0730,ATT-16,ATT-17 -->
**P2-088 — Process supervision improves control but does not undo file effects.**

Windows `KILL_ON_JOB_CLOSE` acts when the last job handle closes, for processes actually assigned to that job. Handle inheritance, breakaway, assignment, and termination confirmation matter. `CREATE_SUSPENDED` then assignment has a crash gap. Supported Windows can use `PROC_THREAD_ATTRIBUTE_JOB_LIST` at process creation.

A job may be destroyed before restart can query it. PID plus creation time helps identity but does not alone prove all descendants stopped. Other platforms require their own real lifecycle guarantees, not an assertion that process groups are equivalent. Apply this machinery only to actual subprocesses, not database note updates.

*Sources: EVT-0701, EVT-0730, ATT-16, ATT-17. Status: corrected-proposal.*

<a id="p2-089"></a>
<!-- P2-089 | Retry by effects not tool label | settled-boundary | EVT-0730,ATT-17 -->
**P2-089 — Safe retry follows an actual side-effect contract.**

Built-in OCR/rendering can be retryable when these conditions hold:

* It reads fixed inputs.
* It writes only attempt-specific candidates.
* It leaves formal versions unchanged.
* Old execution cannot continue modifying the same output.
Being “built-in” does not prove those conditions. A host script without a final receipt is not blindly rerun, but evidence can still establish reusable completion or partial results. The agent may reconcile saved script, process state, outputs, and identifiable effects. Only unresolved effects remain unknown or blocked. No routine human intervention is required for effects that can be safely reconciled within authorization.

*Sources: EVT-0730, ATT-17. Status: settled-boundary.*

<a id="p2-090"></a>
<!-- P2-090 | Separate inspect terminate and adopt intent | settled-boundary | EVT-0759,EVT-0789,EVT-0826,ATT-18,ATT-19,ATT-20 -->
**P2-090 — Diagnostic reading must not quietly kill or adopt.**

Agents may inspect partial logs, malformed JSON, and damaged files to diagnose or repair. The whole directory need not validate first. Termination targets an identified attempt and is explicit, even if an interface combines steps. Salvaging one stable file does not imply stopping the entire attempt. Adoption selects a fixed consistent copy and validates that exact content. These internal responsibilities do not force a four-tool ritual on the agent.

*Sources: EVT-0759, EVT-0789, EVT-0826, ATT-18, ATT-19, ATT-20. Status: settled-boundary.*

<a id="p2-091"></a>
<!-- P2-091 | Snapshot and Windows sharing semantics | corrected-proposal | EVT-0789,ATT-19 -->
**P2-091 — A consistent copy needs evidence of stability, not just an existing filename.**

A live writer can yield a torn copy. Holding a compatible read handle during snapshot acquisition is a possible Windows implementation. `GENERIC_WRITE` requests write access. `FILE_SHARE_WRITE` permits others' write access and does not mean that handle is writing. `ERROR_SHARING_VIOLATION` means incompatible access/share modes, possibly an exclusive reader, not proof of an unknown descendant writing. Report snapshot unavailability and the observed error without inventing its cause.

*Sources: EVT-0789, ATT-19. Status: corrected-proposal.*

<a id="p2-092"></a>
<!-- P2-092 | Decode versus completeness and independent salvage receipts | settled-boundary | EVT-0759,EVT-0789,ATT-18,ATT-19 -->
**P2-092 — Valid bytes, valid format, and complete requested work are separate.**

Use mature full parsers/decoders. PNG endings/CRC or JPEG EOI alone do not replace decoding, and Pillow `verify()` differs from loading pixels. A syntactically valid JSON holding pages 1–30 is not successful completion of requested 1–100. Verify selected source/scope/content, record useful rescued ranges, and preserve the original failed/uncertain operation history. A separate salvage receipt can succeed while the original operation remains incomplete. A single `salvaged_resolved` flag should not erase that distinction.

*Sources: EVT-0759, EVT-0789, ATT-18, ATT-19. Status: settled-boundary.*

<a id="images-previews-and-source-review"></a>
## Images, previews, and source-led review

<a id="p2-093"></a>
<!-- P2-093 | Asset registration without restricting methods | settled-boundary | EVT-0534,ATT-11,ATT-12 -->
**P2-093 — Registered assets can come from legitimate scripts as well as built-in tools.**

An import path should record source and processing for native embedded images, page/region renders, raster crops, and script-produced derivatives. Native images preserve original encoding/dimensions, including JPEG. Crops concern parent pixels and lossless output. Vector/composite PDF renders concern page/region/render parameters/readability.

One mandatory page/bbox/DPI field set does not fit all types. Management/provenance records do not prove a crop retained the right panel, legend, or labels. Preserve source-led quality checks without imposing a new per-image approval ritual.

*Sources: EVT-0534, ATT-11, ATT-12. Status: settled-boundary.*

<a id="p2-094"></a>
<!-- P2-094 | Preview generation versus review | settled-boundary | EVT-0507,EVT-0534,ATT-10,ATT-11 -->
**P2-094 — Producing a PNG is not passing a quality check.**

A preview record identifies generated pixels for a fixed target revision. A review record identifies what was actually inspected, its source, scope, aspect, and unresolved issues. Do not auto-create a passing layout review because Chromium produced an image. Candidate/draft previews remain useful before final mapping or full document completion.

For example, missing bold emphasis has at least three places to investigate:

* Whether the source's emphasis was noticed.
* Whether the saved Markdown encoded it.
* Whether the rendered preview displays it.
A preview alone exposes only the rendering result. Comparing the exact saved markup with the source region locates the failure. This explains why source, saved revision, and preview need compatible identities, while leaving the agent free to choose the necessary inspection method.

*Sources: EVT-0507, EVT-0534, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-095"></a>
<!-- P2-095 | Review history and aspect carry-over | settled-boundary | EVT-0459,EVT-0479,EVT-0507,ATT-08,ATT-09,ATT-10 -->
**P2-095 — A v1 review remains a historical fact. Applicability to v2 is a separate judgment.**

Avoid marking an entire page and all dependencies invalid after any edit. Distinguish characters/numbers, meaningful styles, reading/cross-page relations, crop content, and rendered layout. Unchanged characters do not prove full text fidelity when superscripts, footnote placement, or emphasis changes. Adding table rows may alter shared header/unit/footnote scope. Preserve unaffected checks where justified and guide targeted reevaluation without a universal quality engine or compulsory review gate.

For example, a check of a figure's labels can remain relevant after an unrelated paragraph edit. An earlier review of a table's units may need reconsideration when a new row extends the same header's scope. Keep the original review attached to the version/aspect it actually examined and make any carry-over explicit. A global “reviewed” bit or automatic invalidation of every neighboring page loses those distinctions.

*Sources: EVT-0459, EVT-0479, EVT-0507, ATT-08, ATT-09, ATT-10. Status: settled-boundary.*

<a id="p2-096"></a>
<!-- P2-096 | Version dependencies for previews and exports | settled-boundary | EVT-0638,EVT-0674,ATT-14,ATT-15 -->
**P2-096 — A dependent preview must identify the committed version it actually used.**

Running `update_draft` and an implicit-latest preview concurrently can inspect old content while the agent believes it saw the new revision. Return `produced_revision`, then let the agent choose that version for readback/preview/export. An optional document-level commit-plus-preview operation may reduce a round, but reports commit and preview outcomes separately. Preview failure is not edit failure. A generic `after_batch_mutation` scheduler brings ambiguity with multiple edits, failed edits, stale bases, and recovery, and was not made first-version necessary. Explicitly viewing old content or a rejected candidate remains useful.

*Sources: EVT-0638, EVT-0674, ATT-14, ATT-15. Status: settled-boundary.*

<a id="p2-097"></a>
<!-- P2-097 | Source to saved-output comparison | proposal | EVT-0826,ATT-20 -->
**P2-097 — Make the original region and corresponding saved block easy to compare.**

Missing emphasis can originate in source interpretation, Markdown markup, or rendering. Access to both source pixels and the exact saved revision helps locate the failure. A `render_regions([{page,bbox,label},...])` capability can inspect confusable glyphs, headings, superscripts, or neighboring emphasis. Return independent images or a contact sheet at the agent's choice. Keep labels outside source pixels, sufficient context, per-region provenance, originals, and exact rereads.

*Sources: EVT-0826, ATT-20. Status: proposal.*

<a id="p2-098"></a>
<!-- P2-098 | Contact sheets and ink-density hypotheses | hypothesis | EVT-0826,ATT-20 -->
**P2-098 — Visual assistance is not certified optical interpretation.**

One contact sheet may be cheaper/clearer than several images, or worse if it makes each glyph too small. Bytes alone do not decide. Proposed ink/stroke ratio hints are reproducible measurements but not reliable bold labels without evidence. Chinese characters naturally differ in density. Size, bbox alignment, background, bleed, binarization, or hidden OCR misalignment also affect values.

Keep such output as optional “visual difference worth checking” hints, not per-span mandatory numeric noise or a first-version prerequisite. Exact local original-pixel comparison has the more direct value.

*Sources: EVT-0826, ATT-20. Status: hypothesis.*

<a id="runtime-and-framework-alternatives"></a>
## Runtime and framework alternatives, with corrected comparisons

<a id="p2-099"></a>
<!-- P2-099 | App responsibility does not mean custom mechanism | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-099 — Defining product policy does not require reimplementing every mechanism.**

The app decides what must be preserved, accepted, and displayed. A framework may implement messages, persistence, turn boundaries, summaries, cancellation, or middleware that calls a centralized policy. Declaring all session/provider/context/lifecycle work app-owned and then saying the runtime is only a while-loop prejudges the comparison. Conversely, if integration really replaces most features, a thinner runtime can be sensible. Compare reusable mechanisms, state/exception paths to maintain, public-interface stability, diagnostics, and upgrade cost. Do not compare only low interference or adapter line count.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-100"></a>
<!-- P2-100 | Single policy without one giant hook | settled-boundary | EVT-0432,EVT-0459,ATT-07,ATT-08 -->
**P2-100 — One decision authority can be implemented through cooperating components.**

Avoid independent app and framework compressors maintaining competing active contexts. It does not follow that all logic must sit in one hook. Similarly, converting through framework message types does not inherently destroy images or encrypted reasoning. Verify required information survives and the final native request is correct. Hook names alone do not establish Nexus compatibility or crash safety.

*Sources: EVT-0432, EVT-0459, ATT-07, ATT-08. Status: settled-boundary.*

<a id="p2-101"></a>
<!-- P2-101 | Deep Agents corrections | corrected-proposal | EVT-0459,EVT-0479,ATT-08,ATT-09 -->
**P2-101 — Deep Agents was not eliminated by the attachment's claims.**

In the checked 0.7.29 version, size offloading was in `FilesystemMiddleware`, with public `tool_token_limit_before_evict=None` and same-name replacement mechanisms. Configuration is not rewriting the entire middleware. Summarization offered prompt/counting/custom-summarizer options. Pi also has automatic compaction policy to coordinate.

Deep Agents has TypeScript as well as Python variants, requiring version-specific checks. Since v0.7 task planning/`write_todos` was optional, the claimed mandatory Todo removal cost was wrong. No measured “context advantages become zero” conclusion followed.

*Sources: EVT-0459, EVT-0479, ATT-08, ATT-09. Status: corrected-proposal.*

<a id="p2-102"></a>
<!-- P2-102 | Generic workspace tools and formal artifacts | settled-boundary | EVT-0479,ATT-09 -->
**P2-102 — Workspace file tools need not bypass document validation.**

They can prepare long drafts, notes, scripts, and intermediate outputs. Workspace Markdown is working material. Formal versions come through the document service. Do not point generic tools directly at internal version storage or automatically treat any file as a published artifact. Retain agent script/file freedom rather than remove it to simplify a framework comparison. `create_agent` was attractive for opting into only needed tools, not because generic file tools are intrinsically incompatible.

*Sources: EVT-0479, ATT-09. Status: settled-boundary.*

<a id="p2-103"></a>
<!-- P2-103 | Public interfaces and inaccurate recovery APIs | corrected-proposal | EVT-0432,EVT-0507,EVT-0534,EVT-0595,ATT-07,ATT-10,ATT-11,ATT-13 -->
**P2-103 — The named framework hooks had narrower meanings than the proposals claimed.**

Deep Agents `_get_effective_messages` was internal, not a stable extension contract. The review preferred public model/tool middleware.

Pi's request `context`/`context_with_system`, compaction hooks, and `context_edit` do not themselves create an app transaction. Pi v1.3.0 examples used `SessionManager.open()` and `createAgentSession()`, not `Session.load()`. Persisted tool results were message entries with role `toolResult`. Tool `execute()` returns `AgentToolResult {content, details}`, not a session-entry object. `getEntry/getEntries/getBranch` provide public reads. The review rejected direct JSONL surgery.

*Sources: EVT-0432, EVT-0507, EVT-0534, EVT-0595, ATT-07, ATT-10, ATT-11, ATT-13. Status: corrected-proposal.*

<a id="p2-104"></a>
<!-- P2-104 | LangGraph and Pi resume scope | corrected-proposal | EVT-0507,EVT-0595,EVT-0638,ATT-10,ATT-13,ATT-14 -->
**P2-104 — Framework recovery must be assessed at its actual public boundary.**

LangGraph `update_state()` creates a new checkpoint, applies reducers, and `as_node` affects subsequent execution. It is not merely appending a ToolMessage, so hiding repair side effects in `get_tuple()` was rejected. Public `get_state/get_state_history` can inspect without parsing private storage. Pi's low-level `Agent.continue()` can reject when the last message is assistant and no queued message exists. That refutes an automatic-pending-tool-resume assumption, not Pi's overall suitability. A hook mapping alone cannot establish equal integration cost.

*Sources: EVT-0507, EVT-0595, EVT-0638, ATT-10, ATT-13, ATT-14. Status: corrected-proposal.*

<a id="p2-105"></a>
<!-- P2-105 | Historical framework preference and supersession | superseded | EVT-0595,EVT-0638,EVT-0826,EVT-1166 -->
**P2-105 — The `create_agent` preference was provisional and later narrowed.**

This segment moved from Pi versus Deep Agents to Pi versus selective `create_agent`. It then prioritized `create_agent` with persistent LangGraph checkpoints to reduce custom recovery responsibilities. Plain `create_agent` does not include `FilesystemMiddleware` by default. These were design priorities, not app-level compatibility or performance results. The later final consolidation chooses a small direct `StateGraph` plus native Nexus service and document/evidence core. This supersedes the middleware-centered assembly while retaining useful state and projection boundaries.

*Sources: EVT-0595, EVT-0638, EVT-0826, EVT-1166. Status: superseded.*

<a id="nexus-models-and-long-work"></a>
## Nexus integration, model capability, and long work

<a id="p2-106"></a>
<!-- P2-106 | Native Nexus behavior without a second retry owner | settled-boundary | EVT-0730,EVT-0826,ATT-17,ATT-20,EVT-1166 -->
**P2-106 — Preserve behavioral contracts when extracting the Nexus service.**

The conversation valued:

* Native Chat Completions/Responses encoding.
* Tool-image pairing.
* Encrypted reasoning where used.
* Complete-response validation.
* Safe diagnostics.
* Persistent attempts.
* Attempt-local SSE assembly without partial JSON execution or cross-attempt concatenation.
Context is app-controlled and does not require upstream native compaction. The final design uses the shared service for ordinary inference and consolidation with the same budget/cancellation rules. It does not assume remote cancellation, background result retrieval, or known cost after unknown outcomes.

*Sources: EVT-0730, EVT-0826, ATT-17, ATT-20, EVT-1166. Status: settled-boundary.*

<a id="p2-107"></a>
<!-- P2-107 | Old transport cannot be wrapped as an automatic guarantee | corrected-proposal | EVT-0819,EVT-0826,ATT-20 -->
**P2-107 — Extract capabilities before adapting them to a new lifecycle.**

The v1 retry ledger lived in `Agent.model_round`, while Chat image pairing depended on `Provider.pending_images`/`flush_images`. They were not all in one HTTP function. A `NexusWireChatModel` wrapper could be a useful historical adapter option, but would not inherit 228 tests or every old guarantee automatically. Isolate request/batch state, preserve native-response/framework mappings, and use one retry owner. Generic `ChatOpenAI` retries are configurable and it supports images/Responses. The specific risk is unpreserved third-party fields and actual route behavior, not an established claim it breaks everything.

*Sources: EVT-0819, EVT-0826, ATT-20. Status: corrected-proposal.*

<a id="p2-108"></a>
<!-- P2-108 | Frozen input and bounded unknown outcomes | settled-boundary | EVT-0730,EVT-0759,ATT-17,ATT-18 -->
**P2-108 — Transport replay and capacity redesign are different actions.**

For an eligible transient transport failure, reuse the frozen logical request rather than re-resolve live pins or change the prefix. Keep each attempt, diagnostics, response candidate, usage if known, and unknown fees/settlement when appropriate. Permanent configuration/authentication errors and user cancellation do not gain blind retries. Capacity correction needs the explicit context path. Earlier examples of automatic retries 2/three attempts described optional configurations, not a new default or renewed authorization for model calls.

*Sources: EVT-0730, EVT-0759, ATT-17, ATT-18. Status: settled-boundary.*

<a id="p2-109"></a>
<!-- P2-109 | Model switching preserves unresolved modality needs | settled-boundary | EVT-0534,EVT-0560,EVT-0595,ATT-11,ATT-12,ATT-13 -->
**P2-109 — Capability checks address the work, not merely API acceptance.**

Check target context, image/tool/protocol capabilities, prepare the transferable state, validate the actual request, then activate. Removing images can make a text model's request valid while losing evidence for emphasis, legends, or superscripts. OCR is not universally equivalent. Retain unresolved visual requirements and block only unsupported operations, allowing useful text/script work or an available vision route. A font name alone must not impose mandatory page-by-page visual gates. Model rules and calibration do not silently carry across routes.

*Sources: EVT-0534, EVT-0560, EVT-0595, ATT-11, ATT-12, ATT-13. Status: settled-boundary.*

<a id="p2-110"></a>
<!-- P2-110 | Optional visual delegation | proposal | EVT-0638,ATT-14 -->
**P2-110 — A vision tool is an optional way to support a text-focused agent.**

`query_visual_evidence` can use a configured vision route and retain question, exact images/regions, model, response, and uncertainty as derived evidence. Allow crop, whole page, or multiple related pages so a forced crop does not remove a header/legend. Raw pixels remain source evidence. Such a tool does not automatically certify its model's interpretation, create a required workflow, or authorize additional paid model calls during this reconstruction.

*Sources: EVT-0638, ATT-14. Status: proposal.*

<a id="p2-111"></a>
<!-- P2-111 | Sections and episodes | proposal | EVT-0826,ATT-20 -->
**P2-111 — Long work needs continuity, not a fixed two-level agent design.**

One agent switching sections or optional sequential episodes/subagents can carry effective requirements, current versions/candidates, unfinished scopes, unresolved cross-section relations, and the same task budget/records. No page threshold mandates episodes. Sharing a budget does not enlarge its time/round allowance. Separate budgets change policy.

Subgraphs can provide execution-local persistence, but do not choose handoff content, merge documents, or judge completion automatically. Heavy OCR/images remain in evidence storage. Child checkpoints store state/references, and the parent receives exact outputs and remaining issues rather than an unverifiable completion summary.

*Sources: EVT-0826, ATT-20. Status: proposal.*

<a id="verification-and-convergence"></a>
## Verification, adoption, and final convergence

<a id="p2-112"></a>
<!-- P2-112 | Seven-step scenario is a fixture not workflow | settled-boundary | EVT-0479,EVT-0507,ATT-09,ATT-10 -->
**P2-112 — The seven-step path was an example for integration checks.**

The useful scenario has seven steps:

1. Survey across pages.
2. Save an unfinished table.
3. Fix metadata/header.
4. Preview the same revision.
5. Compact.
6. Continue editing.
7. Interrupt after a commit.
They do not prescribe how every PDF is converted. A scripted mock model may finish without reading the new context at all. Thus a successful sequence alone does not establish correct handoff, source fidelity, or agent autonomy.

The scenario joins the contracts through these relationships:

* The unfinished table survives its metadata repair without regeneration.
* The preview reads the revision actually produced.
* The handoff retains the relationship needed to continue the table.
* The app reconciles a commit followed by interruption without a duplicate append.

These relationships connect the contracts rather than test seven unrelated buttons. A fixture can assert those identities, unchanged content, references, and receipts directly. To establish actual conversion quality, compare the saved/reopened/exported output with the relevant source. Thus the historical suggestion was useful as a bounded integration fixture. It was insufficient as a framework winner or universal conversion recipe.

*Sources: EVT-0479, EVT-0507, ATT-09, ATT-10. Status: settled-boundary.*

<a id="p2-113"></a>
<!-- P2-113 | What offline checks can establish | settled-boundary | EVT-0459,EVT-0507,EVT-0534,ATT-08,ATT-10,ATT-11 -->
**P2-113 — Check the actual contract rather than only the path completing.**

Useful checks include:

* Exact compact-encoding round trips.
* Final assembled requirements/current state/unresolved references.
* Precise evidence and pixel retrieval.
* Original receipts without duplicate edits.
* Complete tool pairing.
* Expected activation behavior at interruption boundaries.

An exception can run `finally`/flush and is not a hard process kill. Broken IPC may leave a subprocess working. Fixture tests establish scoped mechanisms, not live model reasoning, comprehensive Nexus behavior, lower equal-quality cost, or the best framework. “Two hours to prove the winner” and adapter line count were not reliable acceptance criteria.

*Sources: EVT-0459, EVT-0507, EVT-0534, ATT-08, ATT-10, ATT-11. Status: settled-boundary.*

<a id="p2-114"></a>
<!-- P2-114 | Proportionate source-led acceptance | settled-boundary | EVT-0507,EVT-0534,EVT-0826,EVT-1166 -->
**P2-114 — Delivered reading and software mechanics remain separate.**

A source-led saved/reopened/exported check concerns the intended PDF or complete section, image fidelity, meaningful formatting, correct content, and reusable output. Natural autonomy does not require the agent to exercise import, release, visual delegation, or preview correction merely to demonstrate features. Final design acceptance is consistent contracts and clear ownership. Later implementation needs suitable offline checks and actual source comparison. These retrospective suggested experiments are not current standing permission or a queued benchmark matrix.

*Sources: EVT-0507, EVT-0534, EVT-0826, EVT-1166. Status: settled-boundary.*

<a id="p2-115"></a>
<!-- P2-115 | Three final contracts and bounded scope | settled-boundary | EVT-1148,EVT-1166 -->
**P2-115 — The final consolidation leaves three decision areas, not endless prerequisites.**

Document edits must define exact references, changed fields, preservation of unspecified content, and commit success. Capacity/handoff must define sendable, release-needed, consolidation-needed, and still-too-large states without losing unprocessed history or destroying originals. Persistence/recovery must name owners and behavior at saved request, accepted response, committed tool, and recorded graph boundaries. Reconcile frozen requests and historical receipts without budget reset or head rollback.

Unknown local effects preserve work and stop when unreconcilable. Explicit user questions wait. Speculative hard-crash universality, automatic truncated-call salvage, universal reminders, and automatic packaging on every exit are not necessary additions.

*Sources: EVT-1148, EVT-1166. Status: settled-boundary.*

<a id="p2-116"></a>
<!-- P2-116 | Delivery and product readiness | settled-boundary | EVT-1166 -->
**P2-116 — Saved results and delivery status have independent meaning.**

Markdown, JSON, HTML, images, and ZIP should correspond to one selected version. Stopped execution, an agent's completion statement, and export consistency are separate records. Existing saved versions can export without another model request, with incomplete work clearly marked as draft. If delivery means an installable desktop product, interface/backend integration and Windows packaging remain real delivery work, not reasons to reopen context architecture. The preferred architecture is still unimplemented. This reference preserves design knowledge without importing closed v1 job allowances or treating old test logs as new acceptance.

*Sources: EVT-1166. Status: settled-boundary.*

<a id="rejected-guarantees-index"></a>
## Compact index of claims not to revive as requirements

The detailed points above preserve each claim's useful part and correction. The following index is deliberately nonnormative:

| Rejected or narrowed claim | Corrected reference |
|---|---|
| Layout size proves thousands of fragmented OCR spans. 80% reduction is guaranteed | P2-002, P2-010, P2-011 |
| Span grouping/coordinate rounding is lossless because raw data remains on disk | P2-009–P2-013 |
| Transparent text or flags certify source meaning or absence of all geometry clues | P2-003, P2-012, P2-013 |
| Saved/unpinned/old/no-error pages are automatically safe to evict | P2-027–P2-031, P2-044 |
| Every source link requires permanent model residency | P2-029, P2-035 |
| A rollup/stub/ledger guarantees constant context size or no forgetting | P2-032–P2-035, P2-061 |
| All latest draft/candidate content must stay resident until superseded | P2-041, P2-044 |
| Every release requires a handoff or fixed K recent rounds | P2-030, P2-041 |
| Token estimation/calibration supplies a universal upper bound | P2-039–P2-041 |
| Full hydration is necessary before summarizing. All references must stay in each request | P2-035, P2-042 |
| Compaction/deferred admission always fits all results or at least one item | P2-038, P2-043, P2-046 |
| Largest/newest result can be dropped automatically after 413 | P2-045–P2-047 |
| `input_view_id`, max event sequence, or one timestamp proves all execution/semantic states | P2-056–P2-065, P2-084 |
| Context manifest overrides committed document/evidence facts | P2-066 |
| Maximum revision or serialized SQLite transactions resolve graph branches | P2-069–P2-074 |
| Replaying every successful receipt with stable message IDs is safe | P2-080–P2-082 |
| Missing marker means not started. Directory isolation is a sandbox | P2-086–P2-092 |
| Saved preview, valid image/JSON, registered asset, or larger test count certifies content | P2-008, P2-092–P2-098 |
| `create_agent` or a thin old-HTTP wrapper automatically inherits v1 guarantees | P2-099–P2-108 |
| Context-tool non-use, short-run extrapolation, or subagents establish a whole-book conclusion | P2-007, P2-111–P2-114 |

This review executed no recorded command from the export. It edited no old-project file and made no model call. This document introduced no new runtime implementation or schema.

<a id="historical-technical-vocabulary"></a>
## Historical technical vocabulary and schema evolution

The discussion proposed concrete encodings, fields, SQL tables, hooks, and status labels before repeatedly correcting their semantics. This section preserves those names together with what they meant and why they changed. It is not an approved SQL schema or an additional implementation backlog. The final consolidation in [EVT-1166](../../sources/rebuild/text/EVT-1166.txt) still controls: a small StateGraph and shared services, with Q1–Q3 open. In particular, later simplification removed the external context-policy/activation store. Discovering its old table name below is not a reason to recreate it.

<a id="historical-representation-vocabulary"></a>
### Representation proposals: what was compressed, grouped, or inferred

**Style Lookup Table** and **Lossless Compact Representation** proposed moving repeated span style into a `style_table`. A style entry held `(font, size, flags, color, alpha, ascender, descender)` and a span held `[style_id, [x0,y0,x1,y1], [ox,oy], text]`. This removes repeated keys/values. By itself, it does not encode the block/line hierarchy, line `wmode`/`dir`, or every optional property. Nor does it distinguish a missing field from an explicit default.

A decoder needs those relationships too. Separately extracted top-level text cannot be replaced by concatenated spans without checking whitespace, line breaks and order.

The proposed style-count estimate and the 80% reduction claim were not established measurements. The relevant comparisons remain exact reconstruction, actual request cost including the legend, and model usability.

**Homogeneous Span Coalescing** joined apparently similar adjacent text. **Coordinate Quantization** rounded coordinates to 0.1/0.5 points. Both can simplify a view, but same font/style does not establish prose continuity across a table column, formula or large gap.

`model_layout` therefore became a clearly described model-oriented view rather than a lossless substitute. `view_type: "simplified_coalesced_lines"` and `source_span_range: [12,17]` explained what had been grouped and how to reread the six original spans. `span_count: 6` and one union box alone cannot reconstruct six boxes. `raw_dict`, `words`, and `chars` remain possible exact-read representations. The guide explains the 600-DPI rounding counterexample in [representations](../../guides/CONTEXT_AND_EVIDENCE.md#evidence-representations).

The proposed `observed_properties` / `derived_hints` split evolved into `extractor_reported` / `app_derived_hints`, because extractor flags can themselves embody inference. `geometry_sub_sup_candidates` used size/baseline differences. `layout_role_candidates` described possible headings, tables or page labels. A candidate's `bbox` and `span_ids` locate the supporting values.

`confidence: "heuristic"` identifies a method, not a calibrated likelihood. The rejected `flags:12 -> [serif,symbolic]` mapping confused PDF FontDescriptor flags with PyMuPDF's span flags: the latter value was `serifed + monospaced`. Neither `layer:"transparent_ocr"` nor a `bold` label may be inferred as visible source truth solely from uniform transparent extraction attributes.

Sources: [ATT-07](../../sources/rebuild/attachments/ATT-07.txt), [ATT-08](../../sources/rebuild/attachments/ATT-08.txt), [ATT-09](../../sources/rebuild/attachments/ATT-09.txt), [ATT-10](../../sources/rebuild/attachments/ATT-10.txt), [ATT-11](../../sources/rebuild/attachments/ATT-11.txt), corrections [EVT-0432](../../sources/rebuild/text/EVT-0432.txt), [EVT-0459](../../sources/rebuild/text/EVT-0459.txt), [EVT-0479](../../sources/rebuild/text/EVT-0479.txt), [EVT-0507](../../sources/rebuild/text/EVT-0507.txt), [EVT-0534](../../sources/rebuild/text/EVT-0534.txt).

<a id="historical-admission-envelopes"></a>
### Admission names and result-status fields

**Pre-Admission Gate → Pending Buffer → Deferred Intake Receipt** described saving complete tool output before deciding what the next model request could accommodate. The Pending Buffer could be a reference to immutable output, not another full copy. The proposed 55% current context plus 35% new batch against a 65% soft watermark motivated checking before expansion. It did not prove handoff would fit or that deferred content would fit afterward. A single item can exceed the fresh request's usable capacity.

| Original label/field | Intended meaning and correction |
|---|---|
| `saved_partially_loaded`, `loaded_scope`, `omitted_scope_manifest` | First attempt to describe saved-but-unexpanded output. The combined status obscured whether the tool partly failed or merely delivered a partial view. |
| `operation_status: succeeded | failed`, `evidence_ref` | Execution outcome and saved-original identity. Mixed per-page outcomes need finer detail than one whole-call success flag. |
| `delivery_scope: full | range_loaded | deferred_for_compaction`, `omitted_ranges` | Which requested view entered a particular request. `full` needs a defined representation. Deferred does not mean failed, and does not promise a compulsory compaction. |
| `tool_execution_status`, `delivered_projection`, `undelivered_scope` | Later names explicitly separated tool production from selected pages/fields/images and saved content still outside the request. |
| **Capacity-Gated Envelope**, **Capacity-Blocked Envelope** | Navigation/status for a saved result that cannot fully enter the current input, with size, scope, warnings and exact access choices. These are not substitutes for full access when it fits. |
| **Batch Paging Gate / Windowed Batch Delivery**, `staged_in_batch` | A proposal to load the first K items and mark the rest pending. The correction allowed K=0 and noncontiguous choices such as pages 15 and 19, rather than imposing reading order. |
| **4-Stage Capacity Escalation** | Proposed release/representation/range/handoff actions were narrowed to options that can be combined, not a mandatory four-step workflow. |

For example, a saved OCR result for pages 15–20 may supply pages 19–20 now and expose exact retrieval for 15–18. That is successful execution with limited presentation. If page 18 never produced valid output, it is an extraction failure and must remain distinguishable. These responsibilities survive. None of the historical enums was finalized. See [precise-read semantics](../../guides/CONTEXT_AND_EVIDENCE.md#precise-read-semantics) and [capacity states](../../guides/CONTEXT_AND_EVIDENCE.md#oversized-results).

Sources: [ATT-07](../../sources/rebuild/attachments/ATT-07.txt), [ATT-08](../../sources/rebuild/attachments/ATT-08.txt), [ATT-12](../../sources/rebuild/attachments/ATT-12.txt), [ATT-13](../../sources/rebuild/attachments/ATT-13.txt), [ATT-19](../../sources/rebuild/attachments/ATT-19.txt), [ATT-20](../../sources/rebuild/attachments/ATT-20.txt), corrections [EVT-0432](../../sources/rebuild/text/EVT-0432.txt), [EVT-0459](../../sources/rebuild/text/EVT-0459.txt), [EVT-0560](../../sources/rebuild/text/EVT-0560.txt), [EVT-0789](../../sources/rebuild/text/EVT-0789.txt).

<a id="historical-manifest-and-staged-updates"></a>
### Pin lineage, manifest fields, and staged note changes

The pin proposal separated agent intent (`target_ref`, `reason_and_unpin_hint`) from app-derived hash/version/size/lineage metadata. `pin_mode` could be `fixed_snapshot` or `follow_latest`. `target_track` selected `working_draft` or `published`. The attachment's proposed default did not become a selected product default. Fixed snapshots preserve an old OCR/table for comparison. Following references select the current instance of a logical object, then resolve to a fixed version for each request.

**Automatic Lineage Forwarding** attempted to retarget pins after a one-to-one or continuous replacement. That can preserve structural identity while losing the reason for the pin: `mg` versus `μg`, a negation, or one digit can change meaning. `target_deleted_needs_review` described a missing target. `stale_requires_repin` described ambiguous continuation. `pin_updated_verify_compatibility` described changed content whose relevance needed reconsideration.

These notices do not constitute automatic semantic validation. **Unconditional Change Disclosure** later proposed a full before/after diff every time. `last_disclosed_revision` then tried to suppress repetition. A sent diff is a delivery observation, not comprehension, and needed current content must still survive compaction.

The **Optimistic Concurrency Manifest** grouped `requirements_revision`, `artifact_version`, `notes_revision`, and `evidence_refs`. The later **Active Context Manifest** example contained `manifest_id`, `framework_session_cursor`, `requirements_rev`, `working_draft_rev`, `published_version_id`, `notes_rev`, and `pinned_refs`, selected by `active_manifest_pointer` in `context_manifest.json`. The cursor referred to a framework entry/checkpoint. The remaining fields selected app state. Replacing that pointer with `ReplaceFileW` could atomically select one manifest, but could not make unrelated stores one transaction or invalidate a document revision already committed. “Four-store reconciliation” named logical session/document/evidence/context responsibilities, not four required databases.

The notes self-conflict used a base with `notes_rev:5`: the handoff produced notes 6, then an unchanged-base comparison wrongly rejected its own result. ATT-08 proposed:

```text
expected_external = (req_rev:R1, published_ver:V1,
                     candidate_head:C1, pre_handshake_notes_rev:N1)
staged_notes_delta = notes generated by this handoff
```

The tuple is the read basis for competing changes. The delta is the pending change to apply. Check external drift at the actual conditional commit boundary, then publish the new note/context state coherently. Do not compare a handoff's own new notes against its old note revision. `candidate_head` identified the selected candidate state in that proposal, not a declaration that every candidate had already committed. This compare-and-swap use of **CAS** differs from content-addressed storage, also called CAS in later attachment prose.

`invalidated_by_requirement_change` was similarly too broad: a changed instruction can require reevaluating a plan while leaving source facts and useful content valid. `rebase_review_required` signaled that page maps, asset references or pin dependencies needed review. Disjoint edited block IDs did not prove semantic independence. `stale_needs_recheck` for every affected page/downstream page was narrowed to aspect/scope applicability, preserving the truth of an old check. These were proposed notices, not mandatory state enums. The final context/persistence contracts still have to define their precise transition behavior.

Sources: [ATT-07](../../sources/rebuild/attachments/ATT-07.txt), [ATT-08](../../sources/rebuild/attachments/ATT-08.txt), [ATT-09](../../sources/rebuild/attachments/ATT-09.txt), [ATT-10](../../sources/rebuild/attachments/ATT-10.txt), corrections [EVT-0432](../../sources/rebuild/text/EVT-0432.txt), [EVT-0459](../../sources/rebuild/text/EVT-0459.txt), [EVT-0479](../../sources/rebuild/text/EVT-0479.txt), [EVT-0507](../../sources/rebuild/text/EVT-0507.txt).

<a id="historical-input-and-observation-fields"></a>
### Delivery tickets, input manifests, and per-attempt observations

**Delivery Ticket** was a compact stored result reference with `operation_id`, `status`, `evidence_id`, `content_sha256`, and `requested_projection`. The example projection requested `mode:full_ocr`, pages 15–16 and images. **Just-in-Time Hydration** / `InputViewAssembler` described expanding that reference to actual text/images for a request, while keeping large payloads outside persisted graph messages. `ToolMessage.artifact` was the proposed programmatic carrier. Scanning arbitrary message text for ticket-like JSON was rejected.

Small success/error results could remain in `ToolMessage.content`. The design retained original image format, including JPEG. The design did not guarantee a few-KB checkpoint or require every small result to take an external-file round trip.

The table name `model_input_views` belonged to a proposed immutable app-boundary input manifest. Its field groups answer distinct reconstruction questions:

| Historical fields/aliases | Meaning |
|---|---|
| `input_view_id`, `policy_rev`, `effective_req_rev`, `effective_draft_rev` | Identify the view and the requirement/document/context basis selected for it. Later Graph-State policy ownership supersedes the separate policy table, not the need for a fixed input basis. |
| `resolved_pins_json`, `resolved_notes_json` | Fixed content and note revisions used after resolving following references. Reading each independently as “latest” can assemble a combination that never existed. |
| `included_messages_and_projections_json`, later `included_messages_manifest_json` | Message order, roles, original call parameters and actual evidence/field/range/image selections or immutable references. `projection_mode:partial` alone cannot reconstruct them. |
| `capacity_omitted_items_json`, later `capacity_omitted_manifest_json` | Requested content not admitted, with exact retrieval and the reason, not proof of extraction failure. |
| `system_prompt_blob_sha256`, `tool_schemas_blob_sha256`, `route_and_model_config_json` | The actual prompt/schema/configuration used. Hashes require retained referent bytes. They are not the content itself. |
| `estimated_tokens`, `estimated_tokens_range_json` | Pre-send estimates tied to the manifest and method, not provider usage or a proven upper bound. |
| `observed_input_tokens` | An early mutable field on the view, corrected because several attempts can use one immutable view and have different observations. |
| `model_request_attempts`, `model_attempt_id`, `observed_usage_json`, `safe_diagnostics_json` | Per-send outcome, actual reported usage and safe diagnostics. Unknown usage/fees stay unknown. |
| `round_id`, `attempt_no`, `request_wire_digest_sha256` | Stable logical request/round accounting, attempt position, and optional safe encoded-request comparison. A new input view cannot reset the original budget. |

The causal association was proposed as `AIMessage.response_metadata["pdf_md_app"] = {input_view_id, accepted_attempt_id, message_id}`. `app_input_view_id` was another example spelling. Preserve existing provider metadata. `additional_kwargs` was not an interchangeable bag because it can carry provider-specific encoding fields. `triggered_by_view_id`, `parent_input_view_id`, and `based_on_view_id` then expressed operation or note provenance. A missing/mismatched accepted parent cannot be repaired by querying the database's latest view.

Capture after all relevant app-layer input modifications. A wrapper may invoke its handler several times, and a `ModelResponse` may include more than one message. Do not map one outer call blindly to one request or keep only its first response object. The promise is reconstruction at a specified app boundary, not access to transformations inside Nexus or proof of model understanding. The lifecycle guide owns frozen-request/attempt behavior. These field spellings remain illustrative.

Sources: [ATT-15](../../sources/rebuild/attachments/ATT-15.txt), [ATT-16](../../sources/rebuild/attachments/ATT-16.txt), [ATT-17](../../sources/rebuild/attachments/ATT-17.txt), [ATT-18](../../sources/rebuild/attachments/ATT-18.txt), [ATT-20](../../sources/rebuild/attachments/ATT-20.txt), corrections [EVT-0674](../../sources/rebuild/text/EVT-0674.txt), [EVT-0701](../../sources/rebuild/text/EVT-0701.txt), [EVT-0730](../../sources/rebuild/text/EVT-0730.txt).

<a id="historical-note-and-order-fields"></a>
### Notes, coverage frontiers, and completion order

`working_state` originally collected `requirements_json`, `agent_notes_json`, `pinned_refs_json` and `active_epoch_id`. Splitting `user_requirements_log` from `agent_working_notes` clarified human versus model authority. An agent's interpretation must not silently edit the effective user requirement. Similarly, `evidence_records.retention_state` incorrectly attached a context-dependent selection to immutable evidence. `context_epoch_items(epoch_id, evidence_id, projection_mode)` moved the selection to a particular context, but `partial` still needed exact ranges/fields to be reproducible. None of these names selects a final table layout.

`active_notes_json`, `open_dependencies_json`, and `pinned_items_json` were whole-state fields. Two parallel note writers could replace each other's changes. `note_id` / `note_key` with `upsert`, `append_observation`, and `resolve_issue` offered independent-item updates. Two writers touching the same item still needed `expected_note_rev` or an explicit merge rule. `working_note_revisions(note_id, note_rev, ...)` preserved old note content for old views. A stored `working_notes.note_rev` without an expected-version check did not prevent overwrite.

The **three-anchor note coverage** proposal used `created_at_seq`, `based_on_input_seq`, and `compacted_up_to_seq` for save time, input basis and replaced history. It corrected automatically advancing `covered_up_to_event_seq` / `notes_watermark_seq` to a concurrently completed OCR result. However, the maximum `based_on_input_seq` still failed selective input. Event 20's text and event 40's fields did not mean events 21–39 or any images were supplied. `based_on_view_id` described the exact selection. Actual replaced message IDs/ranges described compaction.

A routine note about one uncertain value cannot stand for all preceding history.

`operations.event_seq` was assigned on registration and later reused when updating the row to `succeeded`. With operation 100 completing after 101, a query `event_seq > 101` missed the late completion. `created_seq` was narrowed to registration order, and optional `completed_seq` was allocated with the completion receipt transaction. `sequence_counters` was an illustrative implementation for that order, not a new required event-sourcing service. Conversation order still belongs to framework message/checkpoint identity.

**Mechanical Delta Log**, **Unconsolidated Turn Ledger**, and **Compact Turn Skeleton** could derive actions from existing receipts, errors, candidate references and exact history. They do not preserve an unrecorded interpretation. In the cited eight-response run, the first seven `AIMessage.content` values were null. 1,587 cumulative output tokens included 137 reasoning tokens and the final visible text had 508 characters.

Neither those tokens nor selected `crop_bbox`/`_select` arguments disclose all semantic decisions. Explicit working notes remain useful. `record_work_note` / `record_notes` can accompany a read in the same model response. The `note_on_previous_step` field on every tool was optional and carried schema/replay/conflict costs.

Sources: [ATT-11](../../sources/rebuild/attachments/ATT-11.txt), [ATT-12](../../sources/rebuild/attachments/ATT-12.txt), [ATT-13](../../sources/rebuild/attachments/ATT-13.txt), [ATT-14](../../sources/rebuild/attachments/ATT-14.txt), [ATT-15](../../sources/rebuild/attachments/ATT-15.txt), [ATT-16](../../sources/rebuild/attachments/ATT-16.txt), [ATT-17](../../sources/rebuild/attachments/ATT-17.txt), corrections [EVT-0534](../../sources/rebuild/text/EVT-0534.txt), [EVT-0560](../../sources/rebuild/text/EVT-0560.txt), [EVT-0595](../../sources/rebuild/text/EVT-0595.txt), [EVT-0638](../../sources/rebuild/text/EVT-0638.txt), [EVT-0674](../../sources/rebuild/text/EVT-0674.txt), [EVT-0701](../../sources/rebuild/text/EVT-0701.txt).

<a id="historical-replay-and-policy-fields"></a>
### Replay and policy proposals: names that do not confer guarantees

`operation_receipts` / `operations` represented domain effects. `operation_id` and `framework_call_ref` identified an operation. Successive proposed uniqueness keys moved from `tool_call_id` alone to session/thread/namespace and the accepted `parent_ai_message_id`. The reason was scope, not enthusiasm for longer keys. A call ID is not assumed globally unique. An attempt's `run_id` must not destroy the identity of a resumed operation.

`canonical_input_sha256` covered the tool name, complete normalized arguments and fixed referenced inputs. `args_summary_json` could assist display but could not establish exact equality. The proposed `(base_revision, payload_sha256)` shortcut was exact-operation recognition only, not fuzzy semantic intent deduplication.

The historical `operation_outcome: {produced_rev:4}` versus `current_document_state: {latest_draft_rev:5}` example prevented a replayed receipt from moving the current head backward. `result_envelope_json`, `tool_message_payload`, `tool_message_content_json`, `tool_message_artifact_json`, and `tool_message_id` described presentation of the committed result. They were not another mutable document authority.

The **Universal Tool-Call Receipt Short-Circuiting** proposal extended reuse to expensive reads/OCR, but its motivation overstated whole-superstep replay. The discussed `create_agent` implementation sent calls with `Send("tools", [tool_call])`, and saved `pending_writes` could preserve completed task results. App receipts bridged the separate gap between an app effect and framework persistence.

Do not independently schedule `StateSnapshot.tasks`: they are `PregelTask` descriptions that may include nodes, subgraphs or interrupts. Use the selected version's supported resume behavior. When it redispatches a tool, the wrapper can reconcile its exact receipt. Framework API names here are recorded version-specific considerations, not current pins or a new framework comparison.

A result can include `Command(update=...)` as well as `ToolMessage`. If app policy 8 committed but the graph update was not recorded, replaying only the success text left the graph on policy 7. `state_update_json`, `framework_state_update_json`, and later `state_update_patch_json` named the supported state effects to preserve.

They did not encode every `Command` field, including `goto` and `graph`. Unsupported semantics could not be silently dropped. `ToolMessage.id` / `add_messages` could replace an existing same-ID message but would append if compaction had removed it. Therefore a stable ID is not permission to reinsert every historical success.

The proposed policy fields were `active_policy_rev`, `parent_policy_rev`, `current_active_rev`, `delta_intents`, `proposal_ids`, and `last_settled_key`. **Monotonic Guard** / `max(policy_rev)` lost a sibling branch's pin. **Linear Intent Rebasing** based only on disjoint IDs ignored cross-object dependencies and shared capacity. Serialized SQLite writes did not serialize competing graph `Command` updates.

**Net-State Resolution** instead examined the merged intent set: `pin_remove(ev03)` plus `release(ev03)` can be coherent, while contradictory add-pin/release needs an explicit result. `linked_refs` preserved provenance/retrieval. `pinned_refs` expressed residency. A source citation alone could not require a multi-MB image in every request.

`policy_proposals`, `proposal_saved_pending_activation`, `policy_activations`, and `settlement_key=hash(parent_policy_rev, sorted(proposal_ids))` belonged to the later external-policy scheme. The policy-created/graph-not-updated gap needed stable accepted-batch reconciliation. Calculating a new key from the advanced current parent could settle the same batch again. The later small-Graph-State design superseded those tables, retaining one settlement writer and processed-batch identity. It did not turn SQLite and graph records into a distributed atomic transaction.

Finally, `acknowledged_in_turn`, `dispatched_at`, `committed_at`, `returned_to_session_at`, and `observed_in_session_at` attempted to describe lifecycle observations. “Returned” could precede durable graph storage. A crash could also leave the app marker empty after the graph stored the result. **Lazy Ack** could observe/reconcile known entries, not establish exactly-once delivery or comprehension. Choosing a checkpointer also did not choose `durability="sync"`, `async`, or `exit` automatically.

Sources: [ATT-10](../../sources/rebuild/attachments/ATT-10.txt) through [ATT-20](../../sources/rebuild/attachments/ATT-20.txt), corrections [EVT-0507](../../sources/rebuild/text/EVT-0507.txt), [EVT-0534](../../sources/rebuild/text/EVT-0534.txt), [EVT-0560](../../sources/rebuild/text/EVT-0560.txt), [EVT-0595](../../sources/rebuild/text/EVT-0595.txt), [EVT-0638](../../sources/rebuild/text/EVT-0638.txt), [EVT-0701](../../sources/rebuild/text/EVT-0701.txt), [EVT-0730](../../sources/rebuild/text/EVT-0730.txt), [EVT-0759](../../sources/rebuild/text/EVT-0759.txt), [EVT-0789](../../sources/rebuild/text/EVT-0789.txt), [EVT-0826](../../sources/rebuild/text/EVT-0826.txt), simplification [EVT-0878](../../sources/rebuild/text/EVT-0878.txt).

<a id="historical-capacity-estimator-vocabulary"></a>
### Capacity formulas and the counterexamples that limit them

**Dual-Anchor Capacity Accounting** combined the previous API Reported Anchor (`usage.input_tokens` / `prompt_tokens`) with a Conservative Delta Estimator. That anchor was observed usage for its actual request. Adding only new text after compaction, changed images or a route change did not yield the next request's count. UTF-8 bytes and CJK counts times a coefficient did not prove a bound. Nor did assumed 512×512/768×768 image tile formulas establish a Nexus route's actual image accounting.

**Component-Level Estimation with Route Calibration Factor** proposed a local component baseline `B(x)`, an observation `r_k = U_actual,k / sum(B(x_i))`, and a factor such as `alpha = max(recent ratios, 1.15) * 1.05` for the `(nexus_route, model_id, protocol, image_mode)` combination. Recomputing the selected component set was an improvement over blindly reusing an old total. The review rejected the claim of a guaranteed conservative upper bound. Text-heavy observations can conceal large image underestimation, and future composition need not resemble calibration samples.

**Split-Modality Accounting** separated text/schema counting from image observations. A local tokenizer such as `tiktoken` could supply a baseline, but not every native wrapper/provider overhead was known exactly. “No new images” did not mean image-free history. A residual increase after subtracting text deltas could still reflect other request changes, so it was not automatically the true image charge.

The suggested 1,500–2,500 tokens per high-resolution image was not a universal maximum. The discussion included a roughly 3,000-token counterexample. Image pixels, bytes, dimensions and base64 size remained distinct measurements.

The reserve formula also evolved:

```text
proposed intake room = window - current input - max(normal output, handoff output)
later planning check = current input + normal output margin
                     + expected tool receipt margin + handoff turn budget <= window
```

The first formula omitted the normal output/tool results that might remain present before a later handoff. The second acknowledged those stages, but **Expected Tool Receipt Margin** was still only a prediction. An unknown tool batch could exceed it. Inspect the actual saved results before the next model request. **Uncertainty-Aware Estimator**, `[estimated_tokens, high_water_estimate]`, and later `estimated_tokens_range_json` expressed estimates with uncertainty rather than a proof. New estimate names do not eliminate finite capacity-rejection handling.

`rejection_kind: http_payload_too_large | model_context_exceeded` and `CapacityRejectedError(kind="http_413" | "context_exceeded")` were illustrative error interfaces. `request_bytes` describes request size, while `estimated_tokens` describes a model-context estimate. A 413 does not reveal a token limit. The 15/20-MB and 128k/200k figures, “at most two” reassemblies, and mandatory first-K delivery were proposals, not measured route limits or defaults. Capacity correction required an explicit finite context path, while transient transport replay reused the frozen input. Every actual send remained accountable under the original budget.

Sources: [ATT-12](../../sources/rebuild/attachments/ATT-12.txt), [ATT-13](../../sources/rebuild/attachments/ATT-13.txt), [ATT-14](../../sources/rebuild/attachments/ATT-14.txt), [ATT-15](../../sources/rebuild/attachments/ATT-15.txt), [ATT-18](../../sources/rebuild/attachments/ATT-18.txt), [ATT-19](../../sources/rebuild/attachments/ATT-19.txt), [ATT-20](../../sources/rebuild/attachments/ATT-20.txt), corrections [EVT-0560](../../sources/rebuild/text/EVT-0560.txt), [EVT-0595](../../sources/rebuild/text/EVT-0595.txt), [EVT-0638](../../sources/rebuild/text/EVT-0638.txt), [EVT-0759](../../sources/rebuild/text/EVT-0759.txt), [EVT-0789](../../sources/rebuild/text/EVT-0789.txt), [EVT-0826](../../sources/rebuild/text/EVT-0826.txt).

<a id="historical-computation-and-visual-options"></a>
### Computation units, visual helpers, and section options

**Deterministic Extraction Cache** initially used `(source_pdf_sha256, tool_name, canonical_params_sha256)`. That exact-call identity did not match `pages=15–20` to `pages=15–16`. **Unit-Level Cache** and `computation_signature` added the actual independently reusable unit and effective tool/engine/OCR data versions. `dpi`, `psm`, crop/annotation options and resolved defaults could change results. `langs=["chi_tra","eng"]` preserved meaningful language order. A matching path or output hash alone did not prove equivalent inputs, successful full scope or source correctness.

`computed_page_units(source_hash, tool_name, engine_and_model_ver, resolved_params_hash, pdf_page, crop_bbox) -> (evidence_id, json_pointer_or_slice, created_at)` was the proposed logical index. It allowed pages 19–20 from an earlier 15–20 result to satisfy part of a new 19–22 call, computing only 21–22 where pages were independent. `computed_pages`, `reused_cached_pages`, and `evidence_ids` made the reuse visible. **Computation Unit**, **Storage Unit**, and **Selection Unit** remained separate: a six-page JSON need not become six physical files for partial retrieval/release. A cross-page analysis or section script may not be decomposable into page-independent computations.

`force_recompute` produced new evidence while preserving old IDs for comparison. Selecting the newest cache result was a policy, not a quality ranking. A new call reusing old evidence received a result paired to its own call identity. Replaying the same old operation instead returned its historical receipt. Neither required forcing the model through an opaque reference-only response when the requested full view fit.

Optional `query_visual_evidence(evidence_id, crop_bbox, question)` recorded the selected original images, question, model/route, answer and uncertainty as derived evidence. It allowed broader/multiple-page context instead of compulsory cropping. `render_regions([{page,bbox,label}, ...])`, the `render_pdf` regions variant and **Multi-Crop Contact Sheet** helped compare glyphs or source/output regions. Labels stayed outside original pixels and separate originals stayed accessible. `pixel_ink_ratio` / **Ink-Weight Hints** measured differences affected by character shape, size, background, bleed and bbox alignment, not certified boldness.

The related `registered_assets` / `register_asset` proposal used `source_kind: native_embedded | page_or_region_render | raster_crop | script_produced`. Those values distinguished original encoded images, PDF rendering, crops of existing raster pixels, and traceable script processing. They require different provenance: an embedded JPEG need not invent a render DPI. A raster crop needs its parent pixel identity. A render needs the source page/region/settings.

`unverified_asset_provenance` was a proposed diagnostic for missing provenance, not a reason to ban script-produced assets or require a human approval for every image. **Provenance Recorded** and **Content Verified** were separate facts: knowing the source does not prove a crop retained the legend. These names remain illustrative, and the selected asset contract belongs with document evidence access.

The optional **Episode / Scoped Sub-Agent** example `run_section_episode(page_range, section_goal, inherited_pins)` described scoped continuation, not a fixed page-count threshold or selected public tool. One agent could also change scope. Effective requirements, exact saved outputs/candidates, unfinished relations and the same task budget had to carry across. Child checkpoints retained state/references. Full OCR/images belonged in evidence storage.

Old per-page timings did not prove a whole-book failure or a subagent speedup. The 40-page runs used 3,600 seconds/100 rounds and ended in recorded network conditions, rather than proving a 1,200-second physical limit. `keep_evidence_ids` omission did not authorize release. The corrected optional `context_delta: {release_when_needed:[...], pin:[...]}` explicitly expressed the change while omission preserved previous decisions.

Sources: [ATT-11](../../sources/rebuild/attachments/ATT-11.txt), [ATT-12](../../sources/rebuild/attachments/ATT-12.txt), [ATT-14](../../sources/rebuild/attachments/ATT-14.txt), [ATT-18](../../sources/rebuild/attachments/ATT-18.txt), [ATT-19](../../sources/rebuild/attachments/ATT-19.txt), [ATT-20](../../sources/rebuild/attachments/ATT-20.txt), corrections [EVT-0534](../../sources/rebuild/text/EVT-0534.txt), [EVT-0638](../../sources/rebuild/text/EVT-0638.txt), [EVT-0759](../../sources/rebuild/text/EVT-0759.txt), [EVT-0789](../../sources/rebuild/text/EVT-0789.txt), [EVT-0826](../../sources/rebuild/text/EVT-0826.txt).
