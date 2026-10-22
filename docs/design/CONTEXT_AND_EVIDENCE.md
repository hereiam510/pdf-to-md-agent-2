# Context and evidence engineering guide

This guide explains the context and evidence design sufficiently to implement against the repository's [contracts](../CONTRACTS.md) without consulting the old checkout or conversation export. It records the reasoning, concrete cases, alternatives, and remaining schema choices. It is a detailed handoff, not a claim that these mechanisms are implemented.

The controlling baseline is a small Python LangGraph `StateGraph`, shared native Nexus request service and dispatcher, document/evidence core, SQLite metadata transactions, and immutable large files. Compact context policy belongs in Graph State for the single built-in executor. Large evidence hydration is transient. The earlier `create_agent` middleware assembly and external policy-version/activation tables are historical options superseded by that baseline.

**Status language:** “retained boundary” means a correctness or product responsibility retained by the final consolidation; “recommended V1 tradeoff” means the selected direction with exact schema still open; “illustrative option” describes a discussed mechanism without selecting its API; “historical correction” explains a rejected guarantee. Sample names and JSON below are explanatory and do not introduce required tables, tool names, thresholds, or field presets.

The [reference record](../reference/02-context-state-and-evidence.md) preserves the 116 middle-discussion points and their statuses. The [local source archive](../reference/sources/INDEX.md) contains the supporting discussion and attachments as inert data. Later corrections governing this guide are EVT-0878, EVT-1040, EVT-1068, EVT-1107, EVT-1147, and EVT-1166. Current responsibility boundaries remain in [ARCHITECTURE](../ARCHITECTURE.md).

Durable request/attempt execution and tool replay belong to [EXECUTION_AND_DELIVERY](EXECUTION_AND_DELIVERY.md). Candidate capture, document edits, and canonical body storage belong to [DOCUMENT_ENGINE](DOCUMENT_ENGINE.md). Native protocol adaptation belongs to [INTEGRATION_AND_MODEL_BOUNDARY](INTEGRATION_AND_MODEL_BOUNDARY.md). This guide explains the context-facing requirements those services need to preserve.

<a id="motivation-and-evidence"></a>
## 1. The problem this design addresses

The agent should choose how to inspect and reconstruct a PDF and deliver faithful, readable, reusable content with little user handling. Context management must support that work without making source access conditional on a fixed conversion recipe. The agent may survey many pages first, inspect a single precise region, read full OCR immediately, write a whole table with a script, or rebuild a section. No mandatory text-first, OCR, preview, fixed recent-page window, summary gate, or tool quota follows from this design.

The original evidence established specific pressures, with limited causal conclusions:

| Observation | Design implication | What it did not establish |
|---|---|---|
| One `inspect` result was 191,662 characters; `layout` was 147,366, `words` about 39,324, and top-level text about 3,034. The layout had 41 blocks and 446 spans. | Expose useful views and exact selection; investigate repeated representation and bookkeeping overhead. | Thousands of fragmented OCR spans, an automatic 80% reduction, or a sufficient universal field subset. |
| All 446 spans in that page reported `GlyphLessFont`, flags 12, and alpha 0. | Uniform extractor attributes could not distinguish visible emphasis; original pixels remain important. | That transparency proves OCR origin, or that geometry provides no useful superscript/position clues. |
| An eight-response run accumulated 636,591 input tokens, 537,088 cached input, and 1,587 output tokens; its largest single input was 96,996. The first seven assistant text fields were null. | Account for the actual request, including tool arguments/results; do not assume assistant prose contains all working knowledge. | A 636,591-token single context, a known Nexus bill, or guaranteed savings from a particular compaction policy. |
| A rejected candidate contained correct `本文件`; later regeneration changed it to `本文作`. Rejection concerned page-map validity. | Preserve exact candidate content and repair metadata without forced regeneration. | That context compaction caused the typo. |
| Nine-page natural B/C tasks completed scoped work without using optional evidence-management/checkpoint tools. | Separate mechanism availability, natural adoption, and benefit. | Fear of forgetting, misunderstanding, absence of future need, or a requirement to call every feature. |
| Thirteen-page work had source-fidelity defects; forty-page runs ended in particular network/timeout conditions. | Improve source-to-saved-output comparison and preserve work through execution boundaries. | That large OCR or context-tool friction caused those network endings, or that whole-book work requires subagents. |

Old test counts, R1/R2 injected failures, timing figures, and run IDs are historical evidence, not new defaults, permissions, or acceptance certificates. The reference's [observed evidence](../reference/02-context-state-and-evidence.md#observed-evidence-and-causality) and [original network context](../reference/01-foundations-and-frameworks.md#p1-011) explain them locally. This repository does not need the old runtime to understand the design conclusions.

<a id="objects-and-identities"></a>
## 2. Objects, identities, and the facts each one establishes

The most important distinction is between **content that exists**, **work that occurred**, **content selected for a request**, and **meaning that the agent recorded**. None is a substitute for the others.

| Object/concept | Identity and purpose | Does not by itself establish |
|---|---|---|
| Source | Fixed PDF/image bytes with source identity; the fidelity authority. | A successful extraction or a complete conversion. |
| Evidence result | Immutable output of extraction, OCR, rendering, or another tool, tied to fixed source and settings. | That all requested parts succeeded, or that the model received it. |
| Evidence view | A selected representation, pages, fields, regions, or image form from an evidence result. | That the whole original was shown or that a simplified view is lossless. |
| Candidate | Received proposed content/arguments, including rejected or malformed material. | Executability, source correctness, commitment, or current inclusion. |
| Logical block | A stable editing/reference target such as a table. | Unchanged content; its hash can change after an edit. |
| Document version | Immutable accepted content and its identity. A head selects the current working version. | Completion or source review. |
| Note | A recorded finding, decision, convention, or unresolved question, with a recoverable version/input basis. | Complete coverage of all earlier work or the agent's hidden reasoning. |
| Small context policy | Current selection, pin/release, notes/reference, history-boundary, and processed-batch decisions. | A second authority for committed document/tool effects. |
| Input view | What the app actually assembled for one request, with fixed references and omissions. | What the model understood or what an upstream proxy internally transformed. |
| Frozen request | The concrete request selected for one logical model step and its retries. | A new authorization or fresh budget on each attempt. |
| Accepted response/batch | The complete response accepted locally and its eligible tool calls. | That all effects have completed. |
| Operation receipt | What one identified app operation actually produced or committed. | That its result is still head, should be applied again, or should re-enter compacted history. |
| Handoff | Continuation content replacing a precisely identified history scope. | Semantic losslessness just because its structure and message IDs validate. |

Content hashes establish exact content equality. They do not establish logical block identity, semantic purpose, operation identity, branch selection, whether content was seen, or whether it remains in the current document. Two identical paragraphs may occupy different logical positions; editing a table changes its hash without making it a different table.

The historical example `{block_id: "table_01", content_ref: "sha256:..."}` explains that separation. It does not choose a storage chunk size or require one file per block. A whole table or chapter can remain the agent's unit of work. For document identity and commit details, see [canonical data](DOCUMENT_ENGINE.md#identities-and-canonical-data).

**Retained boundary:** an unqualified path, `latest`, maximum timestamp, or global maximum revision is insufficient when the operation needs a specific version. A following reference can be useful during work, but each request resolves it to a fixed content identity. The already-frozen request is not silently updated when head advances.

<a id="evidence-representations"></a>
## 3. Raw, compact, simplified, and survey representations

These views solve different problems and remain selectable. None is a gate that must precede a full read.

| Representation | Useful purpose | Required honesty |
|---|---|---|
| Raw | Preserve exactly what the tool generated, including hierarchy, fields, warnings, and precise coordinates. | Tool output is still evidence to interpret; it is not automatically faithful to the visible source. |
| Reversibly compact | Reduce repeated keys/styles or duplicated values while preserving the promised original structure and values. | State the reconstruction contract and retain all covered properties, distinctions, and relationships. |
| Simplified layout | Present grouped lines, derived candidates, or rounded positions for easier navigation. | Disclose transformations and exact source references; raw availability does not make this view lossless. |
| Survey | Give a light map of pages, candidate structures, images, and reading opportunities. | It is a navigation aid, not complete content or a guaranteed sufficient whole-book map. |

The discussed compact tuple `[style_id, bbox, origin, text]` with a shared style table can remove repeated JSON keys and style values. A lossless implementation would still need to preserve the actual block/line hierarchy, writing mode, direction, all present fields, and missing-versus-default distinctions. It cannot assume concatenating spans reproduces a separately extracted top-level text string: whitespace, line breaks, and ordering may differ. Three evaluations remain separate: round-trip equality, actual model-input cost including the legend and extra reads, and model usability. Shorter JSON alone proves none of the other two.

Same-style span merging was explicitly narrowed. Adjacent spans may be separate table columns, labels, formulas, or meaningful whitespace. One union bounding box cannot reconstruct their internal positions. A group carrying `span_count: 6` and one outer box needs exact subspan references to remain a traceable simplified view. It is not an exact substitute for six boxes.

Coordinate rounding is approximation. At 600 DPI, a 0.5-point step corresponds to about 4.17 pixels, with up to about 2.08 pixels rounding error per coordinate. The proposed 0.1/0.5-point rounding was not proved safe for every crop or glyph distinction. Preserve precise original values for exact reads and native-pixel work.

Survey candidates discussed in ATT-10 included page dimensions, text-layer availability, transparency statistics, possible page labels/headers/footers, large-type lines, possible tables/columns, and native/vector image counts. Large type may be a diagram label; a scan may lack usable text extraction. Targets of 100–200 characters per page or 30 pages under 5,000 tokens were proposals, not completeness guarantees. Reopening saved evidence avoids repeating the extraction computation but still uses storage I/O, latency, and request capacity.

Sources and detailed corrections: [P2-002–003](../reference/02-context-state-and-evidence.md#p2-002), [P2-009–014](../reference/02-context-state-and-evidence.md#p2-009).

<a id="layout-and-visual-evidence"></a>
## 4. Extractor reports, derived hints, and original pixels

Label what the extractor reported separately from what the app inferred. A blanket prohibition on inference would remove useful navigation. Conversely, an inferred heading/table/boldness label must not masquerade as a source fact.

The conversation corrected a specific bitmask error: PyMuPDF span flags 12 mean serifed (4) plus monospaced (8), not PDF FontDescriptor “symbolic.” The discussed flag mapping was bit 0 superscript, bit 1 italic, bit 2 serifed, bit 3 monospaced, and bit 4 bold. Even an extractor's superscript indication can be derived. The accurate distinction is “extractor-reported” versus “app-derived,” not “all physical facts” versus inference.

A smaller span shifted relative to a line can be a useful superscript/subscript hint. The example used 6.5-point text against a 10-point line with a −3.1-point baseline offset. Rotation requires the line direction rather than comparing only `origin[1]`. `confidence: heuristic` describes a method, not a calibrated confidence value. Optional hints can identify where to inspect without becoming certification or a mandatory detector suite.

Image provenance depends on the operation:

| Image kind | Content to preserve or describe |
|---|---|
| Native embedded image | Original encoding, dimensions, identity, and source relation; an original JPEG remains JPEG. |
| Raster crop | Parent pixels, exact selected region, and lossless output appropriate to the source. |
| PDF page/region render | Fixed source/page/region, render settings, and enough detail for the intended reading; vector/composite content may require rendering. |
| Script-derived image | Original parent/source identities and the actual processing performed. |
| Contact sheet | Per-region identities, labels outside source pixels, selected layout/scaling, and access to independent originals. |

One mandatory page/bbox/DPI field set does not describe all those objects. Registered provenance does not prove that a crop retained the right panel, legend, or label. A contact sheet may improve comparison, or may shrink each glyph too much. Bytes alone do not decide.

The ink/stroke-density proposal was retained only as an optional measurement or “difference worth checking” hint. Character shape, size, alignment, background, bleed, binarization, and OCR misregistration can change density without a boldness change. It is not a reliable bold label, per-span required field, or V1 prerequisite. Exact original-pixel access remains the more direct capability.

For a missing emphasis mark, distinguish source interpretation, saved markup, and rendered display. A rendered preview cannot alone locate the cause. Compare the original region and the exact saved version when needed. Generating a PNG is not a review pass; review applies to an actual inspected aspect and version. Detailed preview identities belong to [rendering and preview](DOCUMENT_ENGINE.md#rendering-and-preview).

Sources: [P2-012–013](../reference/02-context-state-and-evidence.md#p2-012), [P2-093–098](../reference/02-context-state-and-evidence.md#p2-093).

<a id="precise-read-semantics"></a>
## 5. Precise read and result-envelope semantics

The supported capability is direct access to full/raw material and exact fields, ranges, pages, regions, or native images on the first useful call and on later retrieval. The final public signatures remain open. Names such as `inspect`, `ocr`, `render`, and `read_evidence` identify capability families in the discussion, not an obligation to recreate every old function verbatim.

A caller needs to distinguish requesting computation from reading a saved result. A saved evidence reference can provide exact bytes or selected views without rerunning OCR. A different requested setting or explicit recomputation may create new evidence. The tool must make this distinction visible; a read is not “zero cost” simply because it avoids extraction.

The evidence identity and selection together should determine what was returned. Selection can include pages, JSON Pointers/fields, text ranges, image regions, representation/version, and rendering parameters where relevant. A mutable path or the word `partial` alone cannot reconstruct it. Exact selection syntax, indexing conventions, and inclusive/exclusive ranges are API decisions to define consistently, not settled by the examples here.

A locator such as `p14_b03` identifies only an internal block until it is bound to immutable evidence E. Recomputing OCR with a different crop, engine, or language order can produce another page-14 block 3. The usable reference is E plus its internal location; source PDF identity, physical page, coordinate system, and settings can then be recovered from E. Pixel coordinates belong to one particular raster, while PDF coordinates belong to the page space. A crop must use their recorded transform, including relevant scale/rotation/region origin. This avoids asking the agent to copy bookkeeping fields already known to the tool, without pretending an ambiguous short ID is exact provenance.

Native-pixel access means the original pixels remain retrievable. It does not guarantee that a model route internally processes the image at that resolution: its image processor may resize it. Keep the original and the selected transmitted representation distinguishable. Independent images, a crop, and a contact sheet remain agent choices; none is a universal resolution guarantee.

The following is an **illustrative result description**, not a selected schema:

```json
{
  "operation": "ocr of source S, pages 15–20",
  "execution": "all requested pages saved successfully",
  "evidence_ref": "fixed evidence E with immutable original",
  "requested_view": "full OCR for pages 15–20",
  "actual_input_view": "OCR for pages 19–20",
  "saved_but_not_expanded": "pages 15–18",
  "retrieval": "exact saved-result access by E and page/field selection",
  "warnings": []
}
```

This example preserves six-page execution success while admitting only two pages to a particular input. If page 18 failed extraction, report that failure separately; it cannot be described merely as saved-but-unexpanded. Per-part status matters for mixed results. A result receipt should distinguish at least execution outcome, persisted original identity, requested representation, actual delivered scope, omissions, warnings, and exact retrieval. “Full” must say whether it means the requested representation or raw original.

An oversized result remains a valid completed tool result with accurate references and coverage. It is not hidden by dropping the formal ToolMessage. Every call in the accepted batch needs its protocol-valid result before the next model request or handoff. Pairing alone does not prove all payload content was delivered.

Source pages extracted, selected into input, cited in a draft, and understood are different facts. The app can record the first three at defined boundaries; comprehension cannot be inferred. Neither successful parser output nor the existence of a saved file proves complete source coverage or correct interpretation.

These precise-read capabilities belong in the common document/evidence service used by the built-in executor, CLI, and MCP clients. Only an assembler that knows the whole request can assess its remaining model capacity. An MCP server can describe its return size and selectable views, but cannot remove earlier results from an external host's history. The host may compact that history itself. This boundary does not justify a fixed concise-first return or removal of first-call full access.

Sources: [P2-034–037](../reference/02-context-state-and-evidence.md#p2-034), [P2-046](../reference/02-context-state-and-evidence.md#p2-046), [P2-052](../reference/02-context-state-and-evidence.md#p2-052), EVT-0878, EVT-1107.

<a id="indexes-and-unfinished-evidence"></a>
## 6. Indexes, stubs, and unfinished evidence

Complete evidence indexes remain available by source/page/type/text/ID where supported. The active request needs useful navigation, not necessarily one permanently resident stub per previous call.

A stub may say that a page has a possible table, a bottom small-print region, and an exact retrieval route. It helps the agent find the original. A 100-character stub cannot guarantee that an important footnote or relationship was preserved; heuristics can miss it. A handoff should be able to consult originals, rather than recursively summarizing only older stubs.

Range rollups are useful when work is contiguous. They do not guarantee constant size: alternating complete/incomplete pages can produce almost one range per page. Twenty-five-page buckets reduce displayed detail but remain proportional to document length. Twelve lines for one 300-page document do not establish a 10–20-line or 400-token universal index. Expandable chapter/range views and selected buckets are options; limiting activity to one or two buckets must not block cross-range work.

Unopened results also need continuity. It is legitimate to record “OCR produced pages 15–20; draft pending; originals at E” without pretending to summarize their unseen content. Preserve unfinished scope and an immutable manifest/retrieval entry. An unfinished chapter can cross a compaction boundary; no rule requires every unhydrated directory to be listed in every request. Existing notes can remain useful even if their cited source is not rehydrated in the summarization call.

Mechanical coverage cannot encode all semantic findings. “Page 15 footnote governs pages 12–14” is a recorded relationship. “Pages 12–15 extracted” is an operation fact. Both may be useful, and neither replaces the other.

Sources: [P2-032–035](../reference/02-context-state-and-evidence.md#p2-032), [P2-061](../reference/02-context-state-and-evidence.md#p2-061).

<a id="drafts-and-content-references"></a>
## 7. Drafts and candidates in the working input

Working Draft was proposed to make useful unfinished content directly readable, editable, previewable, and pinnable, rather than leaving it scattered among failed submissions. Candidate/committed status, completeness, and source-review status are independent. A valid saved revision can honestly be a partial draft. Unknown page metadata must not require discarding otherwise useful received content.

The candidate itself is preserved before validation at the native receiving and dispatch boundaries described in [candidate capture](DOCUMENT_ENGINE.md#candidate-capture). The context layer selects exact saved content; it must not require the agent to regenerate a correct table solely because a mapping field failed validation.

Inline text, saved candidate/artifact references, and workspace-file content are legitimate input choices. In the discussed four-page, 200-cell table example, a script can prepare the table once and the document service can import a fixed snapshot. Reading, parsing, and saving still copy bytes; “zero-copy” was an ergonomic claim about avoiding another model-generated tool string, not a literal memory guarantee.

The active candidate may be more useful than the latest committed document. For example, it can contain the correct preceding portion of a cross-page table despite rejected page metadata. A candidate index or one-line summary is not always enough to continue its next row faithfully. At the same time, all candidate bodies need not be loaded, and the latest draft is not permanently resident until a successor exists. Select the block, necessary neighboring content, unresolved relationships, and exact references appropriate to the current work.

Candidate A can remain useful after an unrelated section B saves successfully; “created before the last save” does not make A obsolete. Likewise, an ancestor version's adoption of A records historical use, while a later version may have removed that content. The working continuation should describe necessary unfinished work and useful exact candidate references. It need not demand a disposition for every unused candidate fragment or treat all unadopted material as a completion blocker.

Source references and version identity make selective retention possible. They do not decide relevance. Releasing large old authored tool arguments must preserve the original executable journal and exact content reference; a shortened presentation cannot become the argument used for replay.

The document service owns edit applicability and short conditional commits. The ordinary example validates a fixed candidate against an explicitly named base outside the lock, then checks expected head and records version/receipt in a short transaction. A mutable scratch file must not be reread after validation as if unchanged. Disjoint block IDs do not prove semantic independence: changing a table's header units can conflict with adding a numeric row elsewhere. See [edit semantics](DOCUMENT_ENGINE.md#edit-semantics) and [commit visibility](DOCUMENT_ENGINE.md#commit-visibility).

Sources: [P2-015–023](../reference/02-context-state-and-evidence.md#p2-015), [P2-044](../reference/02-context-state-and-evidence.md#p2-044), EVT-1107, EVT-1147, EVT-1166.

<a id="pins-links-and-release"></a>
## 8. Pins, links, and release intent

Three relationships need separate meaning:

| Relationship | Meaning | Example |
|---|---|---|
| Source linkage | Where a claim/block came from and how to retrieve its source. | A table cites a page image without requiring that entire 4 MB image on every call. |
| Unresolved dependency | A question or relationship still relevant to unfinished work. | A later footnote may define the current table's units. |
| Explicit residency/pin | An agent choice that specified content should be included in the working view, subject to explicit capacity handling. | Keep a cross-page header or comparison crop available while continuing the table. |

A pin expresses target, purpose, and a possible release condition. The app maintains derived version/hash, lineage observations, dimensions/bytes, and applicable cost estimates. The agent should not manually update bookkeeping the app can observe. Byte counts may be exact; token/image cost estimates may not be.

Fixed references and following references solve different tasks. Preserve a defective OCR or old draft by fixed version for comparison. Follow a logical table/header on a specified draft or committed track when current content is wanted. Resolve following references to fixed content for each request, and disclose changes relevant to their purpose. A one-to-one edit does not establish semantic compatibility: `mg` to `μg`, an added negation, or one changed digit may matter greatly. Split/merge/delete can require explicit repinning while the old snapshot remains retrievable.

A last-disclosed revision means a change was included at a defined delivery boundary, not that the model understood it. Repeating full before/after diffs on every request can inflate history. Exact diffs remain retrievable, and current needed content must still be available after compaction even if an earlier diff was once sent.

Release means removing active exposure while preserving originals/history. The discussed `evict_when_needed` option authorizes later removal when useful for capacity or batching. `drop_immediately` requests removing stale/wrong/distracting content from the next view even when capacity is ample. Cache reuse is not a reason to override the latter. These names are illustrative option semantics, not selected public API spellings.

Omitting an item from a new `keep_evidence_ids` list was not accepted as blanket release authorization. An optional `context_delta` accompanying a save can express explicit changes; omitting the delta preserves prior decisions. Releasing one unnecessary image does not require another model call, a rewritten note set, or a new epoch.

Sources: [P2-024–031](../reference/02-context-state-and-evidence.md#p2-024), [P2-053](../reference/02-context-state-and-evidence.md#p2-053).

<a id="retention-signals"></a>
## 9. Retention signals and rejected automatic rules

Current focus, explicit pins, unresolved dependencies, recent use, neighboring pages, and drafted status can help rank candidate selections. They are evidence for agent judgment, not semantic proofs.

The historical P0–P3 proposal assigned P0 to current focus/pins, P1 to inspected-but-unwritten pages, P2 to the last one or two neighboring written pages, and P3 to older written pages without registered issues. It attempted automatic protection/release from those categories. Focus Decay later proposed that writing pages 10–11 would keep those pages and page 12 while reducing unpinned pages 13–15 to indexes.

The counterexamples explain why these did not become hard rules:

* An agent may inspect 30 pages before organizing them. Keeping every inspected-but-unwritten page fully resident penalizes that reasonable method.
* The newest requested result may exceed the whole available window. Calling it P0 cannot make it fit.
* A dependency may be ten pages away. One or two neighboring pages are clues, not a safe boundary.
* Saved pages can still contain needed abbreviations, header units, or footnotes. “No issue registered” does not prove no dependency.
* An unpinned item can still be useful; requiring a manual pin for every useful object adds a fragile note-taking obligation.

The retained division is straightforward: the app observes capacity and supplies useful candidates/metadata; the agent decides semantic relevance and records findings/references; the app applies agreed changes at the next safe assembly boundary. This needs no routine human approval and imposes no fixed page window or mandatory handoff after each edit.

Sources: [P2-027–028](../reference/02-context-state-and-evidence.md#p2-027), [P2-044–046](../reference/02-context-state-and-evidence.md#p2-044).

<a id="compact-policy-authority"></a>
## 10. Compact policy has one authority

**Recommended V1 tradeoff:** keep small context policy in Graph State for the single built-in executor. EVT-0878 explicitly removed the earlier external context-policy version table and activation-receipt subsystem as unnecessary complexity for that scope. Retain one settlement writer and processed accepted-batch tracking. This does not move committed documents, sent requests, consumed budgets, or external-effect receipts into rollbackable graph policy.

The discussed policy content includes evidence selection/release/pin decisions, notes or note references, history-compaction boundaries, and already-processed context-change batches. An illustrative conceptual shape is:

```json
{
  "selections": ["fixed evidence identity plus requested view/selection"],
  "pins": ["target, fixed/following mode, purpose, release condition"],
  "release_choices": ["explicit immediate or when-needed intent"],
  "working_notes": ["small content or recoverable note-version references"],
  "history_state": "selected handoff, exact replaced coverage, and remaining history",
  "processed_context_batches": ["accepted batch identities already settled"]
}
```

This lists meanings, not a schema. Large evidence, repeated base64 images, and full hydrated OCR are absent because they belong in immutable storage and transient requests. Reference storage still does not guarantee a few-kilobyte checkpoint: messages, long authored arguments, notes, scripts, and identifiers can grow. A checkpoint's actual serialization behavior must be understood.

The historical policy 7/8/9 example explains why one authority matters. Two tools start from policy 7. A creates 8 containing a page-12 header pin; B creates 9 containing an OCR release but not A's pin. Selecting `max(8,9)` loses the pin. Timestamps and monotonic numbers establish ordering, not inclusion of all changes. The same problem can occur in one physical database. Two serialized SQLite transactions can still return competing graph `Command` values in a superstep.

Putting the policy in Graph State simplifies ownership, but parallel whole-policy replacement can still overwrite changes. A reducer combines data according to its rule; it does not infer whether pin/release intents conflict. The retained simplification is one accepted-state writer, not a claim that Graph State removes all conflicts.

A graph rollback does not undo a sent model request, refund its budget, delete a committed version, or cancel an external script. Their services retain the durable facts. Graph policy can select an old document for comparison while the document service reports a newer current head. See [recovery transitions](EXECUTION_AND_DELIVERY.md#recovery-transitions).

Sources: [P2-066–075](../reference/02-context-state-and-evidence.md#p2-066), EVT-0878, EVT-1166.

<a id="intent-settlement"></a>
## 11. Tool intents and one settlement boundary

Tools may report context-change intents instead of each writing a complete policy. The discussed historical flow was `wrap_tool_call` for tool outcomes/intents, sequential `before_model` for small-state settlement, and `wrap_model_call` for actual input construction. In the direct graph these are responsibilities; retaining those exact middleware hooks is unnecessary.

The context-facing sequence is:

1. Dispatch the calls of one accepted complete response through the shared dispatcher.
2. Save each actual tool outcome and any context intent with its operation/accepted-batch identity.
3. Finish or reconcile the entire accepted batch; every formal call has a valid result before a new model request is prepared.
4. At one settlement point, interpret the eligible intents against the selected small state, handle conflicts, and record which accepted batch was processed.
5. Build a new transient request projection from that settled policy.

This describes a safe sequencing boundary, not a custom replacement for the framework scheduler. The durable batch execution rules are in [accepted-batch execution](EXECUTION_AND_DELIVERY.md#accepted-batch-execution). A partially unfinished batch does not authorize a new model response that regenerates its calls.

Two same-batch intents `pin_remove(ev03)` and `release(ev03)` can be coherent. An add-pin and release of the same target need an explicit outcome. Always letting pins win by iteration order is not semantic conflict resolution. Different target IDs do not establish independence: a released image can support another object's unresolved relationship, and multiple selections share one capacity budget.

When order matters, use the trusted accepted-parent declaration order and the chosen conflict rule, not whichever I/O finishes first. That orders settlement decisions only; it does not by itself sequence a document edit before a dependent preview. The executor must preserve actual effect dependencies separately.

Requiring one full proposal was a conservative historical race-avoidance suggestion, not a proof that the proposal is semantically correct. Local intents with one settlement point are possible. General automatic rebasing of independent semantic intents, a dependency graph, or multi-writer branch reconciliation is not a V1 prerequisite.

Idempotence is scoped to the accepted batch and its real state transition. Re-entering an already-settled batch must not apply it again or regress newer policy. Looking up every completed operation with a particular input view is wrong: the set can include rejected model attempts, unrelated calls, or historical work. The earlier external-policy scheme illustrated this with a policy-creation/activation gap and `hash(current_parent, sorted_proposals)`; that key changes after the parent advances, so it could accidentally create another activation. The separate activation-table mechanism was superseded, while stable batch identity and once-only settlement remain useful responsibilities.

User requirements can change while a handoff or tool batch is in progress. Preserve the new effective instruction and reevaluate the continuation it affects. A staged handoff's own new notes are not external drift: capturing note revision 5, producing revision 6, then checking that notes are still 5 would reject its own update. Distinguish the read basis, staged changes, and genuinely competing updates. Exact transition mechanics remain within the open context/persistence contracts.

Sources: [P2-067–073](../reference/02-context-state-and-evidence.md#p2-067), EVT-0878, EVT-1166.

<a id="transient-hydration"></a>
## 12. Transient hydration and valid message projection

The durable native journal, compact orchestration state, and model-facing request are different objects. Preserve complete native responses and original tool parameters for recovery and provenance. Keep large OCR/layout/images in immutable evidence storage. At request assembly, resolve selected references and produce fresh transient message/image objects containing the actual selected content.

An implementation must avoid mutating stored messages in place or returning giant hydrated messages as durable graph-state updates. In the historical middleware proposal, returning hydrated `messages` from `before_model` would persist them, undoing reference-based storage. `wrap_model_call` was the proposed transient boundary. A direct graph needs the same distinction even if it uses different nodes and service calls.

Small success/error results can remain inline. Not every tool needs a blob round-trip. `ToolMessage.artifact` was discussed as a structured internal carrier for references rather than guessing that arbitrary tool text JSON looks like a ticket. It is not a guarantee that every provider automatically receives that artifact; the native assembler must deliberately produce the model-visible text/image parts.

The assembly process needs to preserve:

* Complete native tool-call/result pairing and required provider items.
* Message roles, order, call identities, and the accepted response relationship.
* Actual native image content, rather than a path string or base64 shown as ordinary text.
* Provider-native reasoning items or other fields required by the selected protocol, without treating hidden reasoning as portable work notes.
* An explicit record of omitted or unexpanded requested content.

Retaining only `tool_call_id` does not prove a transformed history is valid for every route. The integration layer owns encoding validation for Chat Completions and Responses; see [the native boundary guide](INTEGRATION_AND_MODEL_BOUNDARY.md). Source text, saved commands, and a compressed history are inert data. Dispatch accepts current formally accepted calls and framework-pending work, not native-looking calls extracted from historical prose.

Completed old tool arguments can themselves be very large: a saved draft or script may dominate history after OCR has been released. A projection may replace completed historical material with a clearly marked compact account and precise content reference while preserving protocol validity. The original executable call remains intact elsewhere. Unfinished calls still use complete original parameters. Truncating JSON inside native `AIMessage.tool_calls` is not a valid history summary or a replay source.

An activity skeleton can say “OCR pages 15–20 completed; table candidate C retained; save rejected on metadata” as ordinary reference text. It must not masquerade as newly pending native tool calls. A “read-only” label is helpful to the model but cannot replace a dispatch boundary that excludes historical data.

Normal reasoning and compaction share reference resolution. Their selected contents may differ: a normal edit may need a full table, while compaction may need a recorded finding and precise reference. Requiring every large reference to hydrate before compaction recreates overflow. Conversely, handing a summarizer only opaque ticket IDs may omit the evidence it needs to preserve a relationship.

Sources: [P2-042](../reference/02-context-state-and-evidence.md#p2-042), [P2-054–060](../reference/02-context-state-and-evidence.md#p2-054), [P2-071](../reference/02-context-state-and-evidence.md#p2-071), EVT-1107.

<a id="input-view-and-causality"></a>
## 13. Input view, frozen request, and causal linkage

An input view records selected content, not “everything through event N.” For example, including event 20's text and event 40's selected fields while excluding 21–39 and images cannot be represented by `seen_up_to=40`. The input view must identify the actual selection and its fixed basis.

The discussed reconstruction information includes message order/roles and exact parameters; instruction/tool-schema versions; model/route/protocol/settings; effective requirements; draft/content and note versions; resolved pins; evidence views/ranges/fields; image representations; and omitted requested scope. It can refer to immutable originals instead of duplicating every body. Hashes validate retained bytes; they cannot replace missing bytes.

Capture the view after relevant input modifications, at the defined app assembly boundary. The claim is that the app's assembled input can be reconstructed. It does not prove Nexus or a provider made no later transformation, nor reveal what the model internally perceived. Optional safe wire descriptions/digests can inspect encoding without making context management a proxy-chain audit project.

The accepted response must retain the input association. In the historical LangChain adapter, a namespaced application entry in `response_metadata` was proposed while preserving provider metadata and the full `ModelResponse`. `additional_kwargs` may contain provider encoding data and is not an arbitrary interchangeable carrier. Middleware can invoke a handler multiple times or return multiple messages; using whichever view was most recently written globally can associate a tool with the wrong input.

The relationship is better understood as:

```text
logical model request Q with fixed input view V
  -> attempt A, with its own status/usage/diagnostics
  -> authorized retry attempt B of the same frozen request
  -> complete accepted response R
  -> accepted batch of R's tool calls T1 and T2
  -> identified effects/receipts and small-state intents
  -> settled next working state
  -> newly assembled request, when the batch is complete
```

The diagram illustrates identity relationships, not selected node names. Usage belongs to each actual attempt; an input view is not a mutable usage account. A new view does not reset task/step limits. The accepted response distinguishes eligible tools from an unaccepted attempt generated from the same V. Tools bind to R and their call identities, not the database's latest V.

A frozen request is resolved once for attempts of that request. A live `follow_latest` pin or a newly committed draft affects a later request, not transport replay of Q. Deliberate new judgment can use identical content without being the same logical operation. Those durable identity details are owned by [request and attempt identity](EXECUTION_AND_DELIVERY.md#request-and-attempt-identity).

Sources: [P2-056–059](../reference/02-context-state-and-evidence.md#p2-056), [P2-074](../reference/02-context-state-and-evidence.md#p2-074), [P2-108](../reference/02-context-state-and-evidence.md#p2-108).

<a id="capacity-accounting"></a>
## 14. Complete-request capacity accounting

**Retained boundary:** assess the actual assembled request for the selected route and its required output allowance. System instructions, tools/schemas, native wrappers, prior assistant text and tool arguments, tool results, notes/handoff, selected draft content, current evidence, and all still-active historical images contribute. Counting only the latest tool result or newest text misses substantial input.

Keep three quantities distinct:

| Quantity | What it answers |
|---|---|
| Original evidence size | How much material was generated/saved, with exact bytes/dimensions where known. |
| Selected active contribution | What the current request includes, including repeated appearances and actual representations. |
| Estimated remaining room | The selected route's configured capacity minus the assembled input estimate and appropriate output/control allowance, with uncertainty shown. |

A large saved OCR file contributes nothing when unselected. A smaller passage repeated across arguments and results can contribute multiple times. JSON characters, UTF-8 bytes, image megabytes, pixels, base64 length, and model tokens are different measures. Request bytes should be measured independently of token estimates.

Capacity and output reserve are configurable per selected route/model. Unknown costs/limits remain unknown or estimated, not zero. Known applicable tokenizers and documented image rules help, but local text counting may not include all native/provider overhead. Prior observed usage is a calibration observation tied to the actual route/protocol/image mode and input composition.

Rejected shortcuts include:

* Treating UTF-8/CJK factors or pixel area as universal token counts.
* Multiplying recent worst ratios by 1.05 or 1.15 and calling the result a proven upper bound.
* Assuming “no new images” means no images remain in history.
* Inferring new image cost by subtracting only text deltas when other messages, projections, routing, or representation changed.
* Treating 1,500–2,500 tokens as a universal image allowance.
* Adding new text to previous usage after compaction, route changes, or projection changes and calling it the current request count.

A text-heavy calibration sample can conceal severe image underestimation. Separate text/image observations are useful but do not eliminate uncertainty. No paid calibration probe or research into one optimal percentage is a V1 prerequisite.

Output and handoff timing also matter. If a normal turn first produces a large draft/tool call and only afterward needs handoff, reserving merely `max(normal_output, handoff_output)` can omit the newly created messages and the handoff prompt. Unknown future tool batches cannot be bounded by a pre-turn prediction alone. Re-evaluate their actual saved results before the next request.

Sources: [P2-036–041](../reference/02-context-state-and-evidence.md#p2-036), [P2-045](../reference/02-context-state-and-evidence.md#p2-045), EVT-1040, EVT-1166.

<a id="oversized-results"></a>
## 15. Oversized results and capacity states

Saving complete results and admitting them to model input are separate actions. Tools can finish and preserve all output while returning references/status suitable for a valid request projection. Once the accepted tool batch is complete, one assembler assesses its aggregate contribution. Independent wrappers must not each assume they own the entire remaining budget.

The early example used a 65% soft watermark. Existing input was 55%; a batch of high-resolution images/layout added 35%, reaching 90% before handoff overhead/output. The useful correction was to persist complete results and check assembly before uncontrolled expansion. A pending buffer can be only a reference to the saved content. The historical promise that this always leaves “100% safe handshake space” was false: old history or a single new item can already exceed the usable window.

The final contract needs behavior for four conceptual states. The labels below explain them without selecting implementation enums:

| State | Context behavior |
|---|---|
| Sendable | Assemble the chosen valid projection, record/freeze it, then use the shared request service. |
| Release needed | Apply permitted release/representation choices to saved content not needed in the next input; preserve originals and describe omissions. |
| Compaction needed | Arrange a sendable, tracked request that reorganizes appropriate history and continuation knowledge. |
| Still cannot fit | Preserve work and explain the concrete capacity obstruction; use remaining authorized choices/budget, then stop finitely if no workable request can be formed. |

These are not a compulsory four-stage ladder. A request may need an exact range read, another representation, a release and partial compaction together, or no handoff at all. A soft watermark alone need not force consolidation. The final recommended ordering is to release saved currently unnecessary content before organizing older history when useful, not to evict every saved item automatically.

Zero evidence objects may fit. A single native image can exceed the request size even when other history is light. Always loading the first K pages can exclude the useful last-row/next-header pair or a comparison of pages 15 and 19. A light capacity envelope can describe dimensions, size, ranges, and exact view options so the agent can select noncontiguous pages, fields, or regions. It does not authorize automatic eviction of the largest or newest requested item.

HTTP 413 and model context overflow are different. A server/proxy byte limit does not reveal the model's token window. The 15/20 MB and 128k/200k figures in proposals were examples, not verified Nexus specifications. Record the actual upstream diagnosis, local estimate/method, route, model, protocol, and settings separately. A rejected request locally estimated at 80,000 tokens proves that request was rejected under those conditions, not that the model's nominal limit is 80,000. A temporary route-specific safety budget may be adjusted without promoting that estimate to a model specification. Generic 500/502 alone is not evidence of context overflow.

Transport must not silently remove evidence. A capacity correction prepares a new selected view under existing relevance decisions and persistent task limits; a transient transport replay reuses the frozen request. Historical suggestions of one/two reassemblies were finite-policy options, not framework guarantees or new defaults. Every actual send still consumes the recorded applicable attempts/time/usage budget. `before_model` does not automatically catch and recover a later provider exception; the controller needs an explicit finite path.

Sources: [P2-036–047](../reference/02-context-state-and-evidence.md#p2-036), EVT-1040, EVT-1068, EVT-1166.

<a id="rolling-compaction"></a>
## 16. Rolling compaction and exact replacement coverage

Evidence release changes selected payloads. Semantic history compaction asks a model to preserve the work knowledge needed after some history leaves active input. The latter is a real request with a purpose, frozen input, attempt records, accepted response, budget, and cancellation checks through the same Nexus service. A function named `prepare_step` cannot hide that model call as a free local transformation. An extra graph node or another request purpose can express it; no node count is prescribed.

An already oversized history cannot simply be resent in full with “please summarize.” Removing OCR/images may help, but long human requirements, authored drafts, scripts, and tool exchanges can still exceed capacity. Select a fitting portion with the effective requirements, current work anchors, relevant exact evidence, and control/output allowance appropriate to that request. Each actual compaction request must itself fit its selected route's request limits. The total outstanding working history can remain too large for normal inference while several such requests make progress.

For each compaction, the app records the actual supplied message IDs/ranges, the previous handoff and its coverage if used, the still-unprocessed history, the input's context revision, and fixed document/note anchors. These are app-known identities, not fields the model should reconstruct from prose. Selection and replacement must preserve complete native tool-call/result units and any other required native items. “Messages through 200” is inadequate if the selected portion omitted messages or delivered only fields from some results.

The application path has separate responsibilities:

1. Prepare a fitting, fixed compaction request and record its intended coverage and anchors.
2. Obtain and preserve a complete accepted reply through the shared request service.
3. Check nonblank/format/refusal status, intended replacement scope, compatible base revision and anchor references, and the actual resulting request size.
4. Apply a valid continuation to only its covered history; retain all uncovered history and exact originals.
5. Reassess the full working view. Continue normal inference if it fits, arrange useful additional release/compaction within remaining allowance, or take the finite stop path.

This is an explanatory responsibility sequence, not a finalized state machine. A compaction reply without ordinary tool calls is still a compaction result; it must not accidentally take the normal “no tools means assess delivery” branch. Empty, refused, malformed, stale, or unusable output does not authorize discarding the previous context. Structural validation establishes the replacement boundary, not semantic losslessness, and does not require a hidden second reviewer model.

Consider a normal-send target of 80k in an illustrative configuration. A fitting compaction request reduces the assembled outstanding view from 140k to 100k. That can be valid progress even though normal work cannot yet resume. Requiring every accepted partial compaction to meet 80k would reject the intended rolling behavior. Conversely, a 5k summary replacing a 10k segment may fail to reduce the assembled view if it also adds more than 5k of duplicated anchors and references. Measure net change on the entire replacement view, including all new overhead.

Compacting the oldest prefix is a reasonable initial strategy, but not the correctness rule. Summarizing another valid segment can also reduce total size. Correctness depends on exact coverage, preserving unprocessed content, retaining effective requirements/useful work, and applying to the intended revision. A partial pass must not mark the rest of history compacted. Repeatedly summarizing the same material without useful net progress is a reason to reconsider or stop within original limits; no fixed two/three-pass sufficiency guarantee or 90% reduction is established.

Q2 still needs the precise revision-application, replacement, rejection, progress, capacity-estimate, and finite-stop semantics. These mechanics explain the choices already discussed rather than resolving them by inventing an API. See [the execution boundary](EXECUTION_AND_DELIVERY.md#context-work-and-frozen-input).

Sources: [P2-041–044](../reference/02-context-state-and-evidence.md#p2-041), EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="handoff-and-working-notes"></a>
## 17. Self-sufficient handoff and working notes

The recommended first-version handoff contains enough explicit knowledge to continue: effective user requirements and amendments, current scope, the selected saved version, useful candidates/evidence, unfinished work, dependencies, decisions needed to interpret that work, and material cautions. It can reference large original content precisely instead of copying it all. “Self-sufficient” concerns continuation knowledge, not embedding an entire PDF or promising every summary has one fixed maximum length.

For a cross-page table, “read pages 15–16; changed table_02” gives an activity record. The useful continuation may instead need: “page 16's first row continues table_02 under the prior header; one value remains visually uncertain and was not adopted; candidate C contains the correct completed portion; E identifies the source crop.” The first statement cannot recover the second merely from operation counts. Source pixels and table content can be retrieved from E/C, but the unresolved relationship should not disappear when the old conversation leaves input.

The delta-only proposal illustrates a hidden dependency. A note anchor says that next-page rows use the preceding header, so the summarizer omits that finding. Later, the notes are replaced by “currently on page 18.” If the next request contains only the new notes and the delta summary, the header relationship has vanished. Storing an old `anchor_version_id` somewhere does not mean its content is assembled into future input. Delta summaries would require exact anchor inclusion or deliberate consolidation before replacing it. The first-version recommendation avoids that fragile dependency; it does not add a second competing memory service.

Keep historical narrative distinct from current anchors. A current draft may already contain work completed after the history segment being summarized. Pin anchors to exact versions and make clear which statements describe past events and which describe the current work state. Clear prompt sections help; they cannot guarantee that a model never mixes chronology or omits meaning.

Working notes can preserve findings during ordinary work, before a full handoff is needed. Notes may record a source fact, an interpretation, an unresolved dependency, a convention, or why an alternative was rejected. Label those meanings so an agent note does not quietly rewrite a user requirement. Explicit human amendments govern continuation immediately; unaffected source facts and useful content may remain valid while plans need reevaluation.

No compulsory note on every tool call was selected. The proposed `note_on_previous_step` field adds schema/output, conflict, failure, and replay work. A separate note tool can appear alongside a source read in one accepted model response, so a second tool does not necessarily require another model turn. Stable-prefix strategies also allow substantive note updates; they do not justify delaying an important finding for an arbitrary number of turns. Preserve what was actually externalized without claiming to recover hidden reasoning from token counts or assistant prose.

Small current notes or note references can live with the compact Graph State policy. Historical input reconstruction still needs the exact note content used then: an immutable note revision or retained content reference can provide it without becoming another mutable current-policy authority. Item-level append/upsert/resolve is an option for avoiding whole-blob replacement, but two edits to the same note still need an expected-version or explicit merge rule. Merely storing `note_rev` does not enforce such a check.

Sources: [P2-030](../reference/02-context-state-and-evidence.md#p2-030), [P2-044](../reference/02-context-state-and-evidence.md#p2-044), [P2-061–065](../reference/02-context-state-and-evidence.md#p2-061), [P2-068](../reference/02-context-state-and-evidence.md#p2-068), EVT-1107, EVT-1147, EVT-1166.

<a id="notes-coverage-and-order"></a>
## 18. Note timing, source coverage, and completion order

Three coordinates answer different questions: when a note was written, which input supported it, and which history a compaction replaced. A normal note update never automatically advances the history-compaction boundary.

The discussion's race example starts with a model input through event 100. The accepted response requests OCR and saves a note. OCR finishes first as event 101; the note is written afterward. If the app marks that note “covered through 101” because 101 is the database's newest number, recovery can omit the new OCR even though the model had not received it. Even without concurrency, a short note about one uncertain unit does not summarize all earlier work. Bind the note to its actual input view and record compaction's actual coverage separately.

Operation registration sequence is also not completion order. Operation 100 may be registered before 101 but finish after 101. Updating row 100 to succeeded and later querying only `event_seq > 101` misses that completion. Operation status records describe current operation facts; framework message/checkpoint identity describes conversation progress; input views describe supplied content; compaction records describe replaced history. If a completion sequence is useful, allocate it with the result commit and define it as receipt-commit order. An append-only event history is an option, not a required general event-sourcing architecture.

A recovery activity view should derive known actions from existing tool records, receipts, and document versions rather than maintain a second independent activity ledger. Useful notes, errors, candidates, and exact message/evidence access complement that view. A crop bbox tells where the crop was made, not why that region was chosen or an alternative rejected. Mechanical coverage and explicit findings work together; neither proves comprehension or source fidelity.

Sources: [P2-034–035](../reference/02-context-state-and-evidence.md#p2-034), [P2-056](../reference/02-context-state-and-evidence.md#p2-056), [P2-061–065](../reference/02-context-state-and-evidence.md#p2-061).

<a id="failed-handoff-and-restart"></a>
## 19. Failed handoff, restart, and context-facing recovery

Failure preserves the old native records, candidate handoff, coverage description, and useful evidence. If the old state is usable, continue from it after responding to the actual failure. Reassess capacity before a new normal request; sending the same oversized view immediately after failed application simply repeats the known problem. A changed requirement or revision can make a prepared continuation stale without making every underlying source observation worthless.

Restart alone is not a reason to construct a new recovery summary. Load the selected framework state/session through supported interfaces, reconcile durable request/batch/document effects, and continue original pending work when usable. Only missing/invalid history or capacity that cannot be handled through the normal path justifies a clearly labeled recovery context. Such a context can contain effective requirements, saved artifacts, valid notes, recent activity, candidates, outstanding scope, and exact retrieval. It may require renewed source inspection; it does not recreate unexpressed reasoning or promise lossless continuation.

The context-facing distinctions at interruption are:

| Durable fact | Consequence for context continuation |
|---|---|
| Frozen request exists | Attempts of that request reuse its exact selected input; later policy/head changes do not rewrite it. |
| Complete response accepted | Its complete tool batch, not a regenerated answer, defines pending work. |
| Tool committed before graph acknowledgement | Its original receipt and supported current-batch effects can be reconstructed without repeating the commit. |
| Batch settled before graph continuation | Recover necessary deterministic continuation effects without reapplying old policy over a newer settled state. |
| Local effect remains unreconciled | Preserve work and report the specific unknown outcome; a new summary is not evidence that the effect is safe to repeat. |

A tool's completion can include more than visible `ToolMessage` text. Historical middleware examples could lose a `Command` update when only the text was replayed. The direct graph may centralize writes, but still needs to recover the supported effects of its accepted pending batch. Conversely, stable message IDs do not justify injecting every historical receipt: if compaction removed a message, a same-ID insertion may add it anew and orphan a tool result. Recover actual pending runtime/batch work, not an unbounded scan of all successful history.

“Returned,” “observed by a hook,” “persisted by a framework,” “included in model input,” and “understood” are separate states. An app acknowledgement timestamp can be empty after framework persistence or set before it, depending on ordering. Lazy acknowledgement is a possible fast path backed by supported state reconciliation; it is not a transaction across the stores. Likewise, naming a SQLite checkpointer does not select synchronous, asynchronous, or exit-time durability. The chosen framework version's actual persistence mode determines the checkpoint boundary.

Model requests, budgets, and committed document/effect facts remain service-owned across graph rollback. A historical receipt for producing V4 may coexist with current head V5; returning it must not select V4 again. A prepared but uncommitted file remains useful work, not automatically committed or abandoned. Stage/verify files before publishing metadata references, preserve recoverable prepared data, and use the document service's conditional commit rules. No process running and no active-context reference do not prove a file is disposable. A first version can avoid background deletion without introducing leases or a garbage-collection project.

Every actual normal or compaction send passes the shared gate, including after successful handoff and on resume paths. Already accepted results can be read without another generation; retrieving them does not refresh exhausted model allowances. Cancellation or a genuine user question must not require one more model handoff. If necessary controls and a workable minimum cannot fit within remaining authorized choices and budget, stop finitely with saved work and a concrete capacity obstruction. Exact re-entry/stop rules remain Q2/Q3 work, owned with [recovery transitions](EXECUTION_AND_DELIVERY.md#recovery-transitions).

Sources: [P2-043](../reference/02-context-state-and-evidence.md#p2-043), [P2-066](../reference/02-context-state-and-evidence.md#p2-066), [P2-075–085](../reference/02-context-state-and-evidence.md#p2-075), EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="prompt-cache-and-cost"></a>
## 20. Prompt-cache tradeoffs and whole-task cost

Stable instructions, tool schemas, ordering, and appendable prefixes can help practical cache reuse. Current requirements, correctness, capacity, and explicit release choices still govern the actual request. Cached tokens are not necessarily free, and the roughly 84% cached-input observation in one old run did not establish a bill or the best policy for another route.

Two historical projection strategies illustrate the tradeoff:

| Strategy | Benefit sought | Cost or limitation |
|---|---|---|
| Fixed continuation baseline for an epoch, then substantive append-only events | Keep the existing input prefix stable while work proceeds. | Old events and duplicated snapshots accumulate until another view is organized. An epoch is a projection period, not a new execution budget. |
| Fresh current-state view near the request tail | Present selected current facts without all stale snapshots. | Replacing the previous tail changes part of the prior request's prefix; tail placement alone is no cache guarantee. |

Ordinary tool results can convey normal changes without injecting a duplicate full state snapshot each turn. A current-state supplement is useful on recovery, handoff, or a real information gap. Whatever strategy is selected, an effective user amendment must be communicated explicitly; a new requirements revision number alone does not say what changed.

Recently generated tool arguments have a distinct timing fact: they were output from the last request and were not yet part of that request's input. Projecting them before their first return therefore need not invalidate the prefix of the last input. Rewriting older already-sent history is a different change. Frozen request snapshots preserve same-request replay; permanent verbatim retention of recent history is unnecessary for that purpose. A moving hard recent-K window can itself rewrite history every turn.

Deferred release can preserve a reusable prefix when consistent with the agent's intent, while an immediate-release instruction removes stale or distracting material from the next view. Neither cache policy decides semantic relevance. Compare whole-task price-weighted input/output, additional reads or compaction, latency and achieved fidelity, preserving unknown fees/usage. Shorter JSON, fewer characters, lower total tokens, or a higher hit percentage alone cannot establish equal-quality savings. This task selects no cache experiment or new billing assumption.

Sources: [P2-048–049](../reference/02-context-state-and-evidence.md#p2-048), EVT-1107, EVT-1147, EVT-1166.

<a id="computation-reuse"></a>
## 21. Computation reuse, exact reads, and operation replay

These three actions are distinct: reading an immutable saved result; repeating the same identified operation after interruption; and performing a new call that reuses an earlier computation. The first avoids computation but still costs I/O and possibly model input. The second returns the original operation receipt under its stable identity. The third has a new accepted call/result identity, with explicit reused-evidence provenance. Reusing a former call's native message ID for the new call can break pairing.

An optional computation cache must describe the computation actually performed: fixed source, tool/implementation/engine version, resolved defaults, relevant OCR model/language data and language order, DPI, page segmentation mode, region, annotation settings, and other effective parameters. Tesseract language order was a concrete example of an input that can affect the result. These are illustrative signature dimensions to derive from the chosen operation, not a universal field preset for every tool.

A whole-call hash for pages 15–20 will differ from one for 15–16, so exact whole-call deduplication alone does not resolve overlap. An index can reuse independently computed pages 19–20 when a later call asks for 19–21 and compute only 21, where the computation really is page-independent. A cross-page table analysis or section-wide script may depend on the whole range and cannot automatically use page cache units.

Computation units, physical storage, and context selection are independent. One immutable six-page JSON file may hold several independent results, an index may map each page or JSON Pointer, and a request may load only fields on pages 19–20. Neither partial release nor overlap reuse requires one file per page. Selection records exact ranges, fields, regions and view identity; `partial` cannot reconstruct the content sent.

Verify fixed inputs and result completeness before reuse, not merely an existing path or matching output hash. A successful reuse should satisfy the requested view when capacity permits, with actual omissions disclosed when it does not. Recovery must not silently replace a full OCR request with an opaque ID and force an extra model turn just to learn that the result exists.

An explicit recomputation option or changed settings produces a new evidence identity while retaining the old result. If a default cache index prefers the newest result, make that a declared selection rule. Newest does not mean better. Existing notes/fixed references remain bound to the earlier evidence so an agent can compare a suspected bad OCR with the recomputation. Computation caching remains an option rather than a first-version dependency.

Sources: [P2-050–055](../reference/02-context-state-and-evidence.md#p2-050), [P2-077–079](../reference/02-context-state-and-evidence.md#p2-077), [P2-083](../reference/02-context-state-and-evidence.md#p2-083).

<a id="scripts-and-partial-work"></a>
## 22. Scripts, partial outputs, and the evidence boundary

Trusted scripts remain process-opt-in and off by default. Once enabled for the task, autonomous own-task scripts do not need routine per-script approval. They run with the host user's permissions. A task or attempt directory organizes files and provenance; it does not prohibit absolute-path writes, isolate model context, or provide an OS sandbox. Generic workspace tools can prepare long drafts, notes and scripts, while formal document versions still pass through the document service. Do not expose internal version storage as arbitrary mutable workspace files.

Preserve complete scripts, logs and outputs despite response-size limits. Diagnostic reading may inspect partial logs, malformed JSON, or a damaged image without first validating the entire directory. It must not silently terminate a process or adopt its files as committed content. Termination identifies an actual attempt; adoption selects and validates a fixed consistent copy. These are distinct intentions even if a convenient interface combines explicitly requested steps, and they do not require a four-tool ritual.

Missing `_exit_status.json` or a success receipt does not prove nonexecution. The controller can stop after launch but before recording “running,” or after the process finished but before recording its result. An attempt can remain running, be incomplete, or have useful complete files. Nonzero exit can still leave reusable output; zero exit alone does not prove scope completion. Physical attempts retain their own identity and output locations under a stable logical operation.

The relevant evidence tests differ:

| Question | What addresses it |
|---|---|
| Did these exact bytes remain unchanged? | A fixed copy/hash and its recorded identity. |
| Is the selected file decodable? | A complete parser/decoder appropriate to its format. PNG endings/CRC or JPEG EOI alone are insufficient; image verification and pixel loading differ. |
| Was the copy consistent while acquired? | The actual writer/snapshot contract; an existing filename or a failed share-mode open does not establish it. |
| Does it cover the requested work? | Source/settings/scope checks. Valid JSON for pages 1–30 does not complete a 1–100 request. |
| Can the operation safely run again? | Its actual side-effect and supervision contract, reconciled outcomes, and remaining authorization/limits. |

A separate successful salvage receipt can record useful recovered ranges while the original attempt stays failed/incomplete/unknown. Do not erase the original uncertainty with one `salvaged_resolved` flag. Reuse full stable results when their source/settings/completeness are established; preserve useful partial work for further inspection. A built-in OCR/render is not automatically pure because it leaves the PDF unchanged—it can create files/processes. A host script is not automatically unrecoverable merely because its marker is missing. Stop only on the effects that remain unreconciled under the execution contract.

Historical Windows supervision and file-sharing details remain in [P2-088](../reference/02-context-state-and-evidence.md#p2-088) and [P2-091](../reference/02-context-state-and-evidence.md#p2-091): Job Object handle/assignment/descendant limits, the suspended-launch gap, and share-mode errors must not be turned into universal guarantees. They are implementation options to consult for a relevant process need, not prerequisites for context work. The current lifecycle owner is [execution and delivery](EXECUTION_AND_DELIVERY.md#process-and-progress).

Sources: [P2-086–092](../reference/02-context-state-and-evidence.md#p2-086), [P2-102](../reference/02-context-state-and-evidence.md#p2-102).

<a id="review-and-version-dependencies"></a>
## 23. Review applicability and version-dependent reading

A preview or review names the actual source, output version, scope and aspect inspected. Generating a PNG is an output operation; it is not automatically a passing review. An old review remains a true historical observation after an edit, while applicability to the new version needs a separate judgment.

Different aspects can change independently: characters/numbers, meaningful emphasis, superscripts, reading order, cross-page relations, crop content and rendered layout. Unchanged characters do not prove all text fidelity if superscript positioning or emphasis changed. Appending a table row can change shared-header/unit/footnote interpretation. Preserve unaffected checks where justified and support targeted reconsideration; do not invalidate an entire page after every edit or install a universal approval gate.

An edit and an implicit-latest preview issued together can race: the preview may read the old version while the agent believes it saw the edit. The edit should return its produced version; readback/preview/export can then select that exact version. An optional commit-plus-preview convenience must report both outcomes separately, since preview failure does not undo a committed edit. A general `after_batch_mutation` scheduler was not made necessary: multiple edits, failed edits, stale bases and resume create dependencies that a generic hook name does not resolve. Explicit old-version or rejected-candidate preview remains useful.

Source/output comparison can use independent regions or a contact sheet with labels outside source pixels and adequate surrounding context. The agent decides the needed comparison. Contact sheets, ink ratios, registered assets and successful image decoding do not certify interpretation. Precise local originals and exact saved-version readback are the underlying capabilities; preview rendering mechanics belong in [the document guide](DOCUMENT_ENGINE.md#rendering-and-preview).

Sources: [P2-093–098](../reference/02-context-state-and-evidence.md#p2-093).

<a id="framework-and-native-boundary"></a>
## 24. Framework and native-protocol lessons retained

An app-owned policy does not require a custom mechanism for everything. Framework messages, persistence, summaries, middleware and lifecycle hooks can implement parts of that policy. Evaluate reusable mechanisms, maintained exception/state paths, public interfaces, diagnostics and upgrade burden. Comparing only adapter line count or low interference prejudges the choice. If an integration replaces most framework services, a smaller direct runtime can be the simpler fit.

One context authority can be implemented through cooperating components. It does not require one giant hook, nor independent app/framework compressors with competing active contexts. Framework message conversion is not inherently lossy; the actual adapter must preserve the required native fields, images, reasoning items and call/result relationships. A list of hook names or a matching `base_url` alone cannot establish compatibility or crash recovery.

The current baseline uses the small direct StateGraph and shared native Nexus request service. Historical `create_agent`/Pi/Deep Agents recommendations and API corrections remain self-contained in [P2-101–105](../reference/02-context-state-and-evidence.md#p2-101). They are version-specific review facts, not current dependency pins: Deep Agents' configurable filesystem offloading/optional planning, public rather than internal hooks, Pi's real session/result APIs, LangGraph state updates and Pi's narrower pending-tool continuation behavior all mattered to that comparison. No fresh framework contest follows.

Extract Nexus behavior before assuming a thin HTTP wrapper inherits it. The old retry ledger was in the controller and Chat image pairing involved provider-held pending images; they were not all one HTTP function. The retained contracts include native Chat/Responses encoding, actual tool-image pairing, needed reasoning items, complete-response validation, attempt-local streaming assembly, safe diagnostics, persistent attempts and one retry owner. A generic SDK's configurable retries or image support does not prove either total incompatibility or exact preservation of third-party native fields.

Normal reasoning and compaction share those native and durable boundaries. Attempt fragments remain evidence; no partial JSON execution or cross-attempt concatenation follows. Transport replay uses the frozen logical request and preserves each attempt's observed status/usage and unknown cost. A capacity redesign prepares another selected view through its explicit control path. Neither a new view nor an old example of two retries creates new allowance. Upstream native compaction, background response retrieval and remote cancellation are optional route capabilities, not baseline dependencies. Detailed encoding belongs in [the integration guide](INTEGRATION_AND_MODEL_BOUNDARY.md).

Sources: [P2-099–108](../reference/02-context-state-and-evidence.md#p2-099), EVT-0878, EVT-1166.

<a id="model-switching-and-long-work"></a>
## 25. Model changes and long-work continuity

A target model/route needs the context, tool, modality and native-protocol capabilities for the intended work. Prepare transferable state and validate the actual request before activating a change. Rules, token calibration and image assumptions from one route do not silently carry to another. Removing images can make a text-only request syntactically valid while discarding needed evidence for a legend, emphasis or superscript.

Retain unresolved visual requirements explicitly. Useful text/script work can continue where supported, or a configured vision route can address the visual question. Do not turn a font name such as `GlyphLessFont` into a compulsory page-by-page visual gate. OCR is useful evidence but is not universally equivalent to original pixels for layout and emphasis.

The optional `query_visual_evidence` proposal gives a text-focused agent a way to ask about exact images/regions using a configured vision route. Its derived evidence would retain the question, actual selected images/regions, route/model, response and uncertainty. Crop, whole-page and multi-page inputs remain options so a forced crop does not exclude a relevant header or legend. The answer is a model interpretation; raw pixels remain source evidence. This mechanism is not required for V1 and does not authorize an additional model call in the present documentation task.

Long work can remain one agent changing sections or use optional sequential episodes/subagents. The handoff must preserve effective requirements, current saved versions/candidates, unfinished scopes, cross-section dependencies and exact outputs. Heavy evidence remains in evidence storage; child/episode checkpoints need state and references rather than copied image/OCR bodies. The parent needs exact outputs and outstanding issues, not only “section complete.” A subgraph supplies execution-local persistence; it does not merge documents or judge semantic completion automatically.

Sharing one task budget across episodes does not enlarge it; assigning separate budgets changes policy. Nine-/thirteen-page timings and forty-page transport failures did not prove one agent must fail on a whole book or that subagents save time. No page count selects a two-level architecture or makes delegation a conversion prerequisite.

Sources: [P2-007](../reference/02-context-state-and-evidence.md#p2-007), [P2-109–111](../reference/02-context-state-and-evidence.md#p2-109).

<a id="verification-and-open-contracts"></a>
## 26. Verification meaning and the three remaining contracts

The historical seven-step integration example joined useful boundaries: survey pages, save an unfinished table, repair its metadata/header, preview the produced revision, compact, continue the table, and interrupt after a commit. Its value is in checking the same content/identities through the sequence. It is not a fixed conversion workflow. A scripted mock can follow seven tool calls while ignoring the supplied context; sequence completion alone therefore does not establish useful handoff, source fidelity or autonomy.

Appropriate mechanism checks inspect the actual claims: exact compact-encoding round trips; fixed source/field/range/native-pixel retrieval; what the assembled request contains and omits; complete native pairing; covered versus retained history; required current-batch effects; and original receipts without repeated edits or pointer regression. A failure caught by `finally` is not a hard-kill test, and disconnected UI/IPC does not prove a child stopped. Old test counts and bounded injected faults are scoped evidence, not acceptance of this rebuild.

Source-led acceptance compares the actual requested PDF or complete section with saved, reopened and exported reading. Meaningful formatting, characters, source images, table relations and usable output matter. A model's completion claim, consistent package bytes, accepted tool execution, and installed desktop readiness are distinct. Optional mechanism non-use does not establish misunderstanding or poor quality, and a prescribed exercise does not establish natural adoption or equal-quality cost savings.

This guide explains prior development detail while preserving the final scope:

| Open contract | What still needs a precise choice | What is already retained |
|---|---|---|
| Q1: document updates and references | Exact reference/applicability, patch/merge/omission behavior, commit success and replay result. | Preserve complete candidates, support insertion and local metadata repair, keep untouched content, use immutable body files with defined metadata ownership. |
| Q2: capacity and handoff | Unknown-estimate policy, send/release/compaction/stop transitions, exact coverage/revision application, replacement/rejection and continuation content. | Assess complete requests, preserve originals/unprocessed history, allow partial rolling progress, use self-sufficient continuation, keep relevance with the agent. |
| Q3: persistence/recovery/stop | Authoritative record placement, boundary re-entry, batch/context effects, original-budget/cancellation/waiting behavior and publication reconciliation. | One active task writer, frozen same-request replay, historical receipts, complete accepted-batch handling, preserved useful work and explicit-version export. |

These are the same three questions in [OPEN_QUESTIONS](../OPEN_QUESTIONS.md), not additional prerequisites. Exact field names, table/module counts, universal percentages, a fixed recent-turn count, automatic truncated-call salvage, general multi-writer branches, universal reminders, all-exit packaging and advanced cache tuning remain unselected or deferred. Reopen a design only for a relevant demonstrated contract-breaking implementation/delivery issue or changed human requirement.

Saved versions remain accessible and exportable without further model generation, with draft/partial status when appropriate. Markdown, JSON, HTML, assets and ZIP must correspond to the selected immutable version; execution stop, content claim and package consistency remain distinct. Desktop/backend integration and Windows delivery are known implementation work for an installable product, not a fourth unresolved context-architecture question. No app implementation, provider run or new benchmark is established by these documents.

Sources: [P2-001](../reference/02-context-state-and-evidence.md#p2-001), [P2-008](../reference/02-context-state-and-evidence.md#p2-008), [P2-112–116](../reference/02-context-state-and-evidence.md#p2-112), EVT-1148, EVT-1166.
