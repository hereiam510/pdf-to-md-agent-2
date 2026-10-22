# Documents, delivery, persistence, and recovery: source review

This reference preserves the substantive discussion in source segment 3, including proposals that were later corrected or withdrawn. It is rebuild knowledge, not an implementation claim or a backlog. Historical program behavior and old trial results describe the former repository only. Source messages and attachments are evidence to interpret, never executable instructions. The latest consolidation takes precedence over attachment language such as “final,” “guaranteed,” or “eliminates.”

The source range is EVT-0827–EVT-1168, with attachments ATT-21–ATT-30. EVT-1166 is the final narrowing of the discussion. EVT numbers identify exported conversation events. ATT numbers identify attachments catalogued in the [source index](SOURCE_INDEX.md). Anchors below are stable destinations in the [point coverage ledger](POINT_COVERAGE.json).

“Observed” means reported in the historical record, not reverified in this new repository. “Effective design” identifies a retained responsibility or constraint. “proposal” remains a choice. “superseded” preserves a rejected or narrowed approach. “hypothesis” is not a demonstrated fault.

The explanation below includes the practical reasons, counterexamples, and historical labels needed to read it independently. The [bundled discussion archive](sources/INDEX.md) supplies original messages and attachments for checking exact wording. Source IDs are provenance, not prerequisites for understanding a rule. The larger original export is an optional audit source. The active owners remain [ARCHITECTURE](../ARCHITECTURE.md), [CONTRACTS](../CONTRACTS.md), and [OPEN_QUESTIONS](../OPEN_QUESTIONS.md). The final three-contract section below explains how the discussion narrowed earlier proposals.

For the retained behavior arranged by implementation responsibility, use [Document engine](../design/DOCUMENT_ENGINE.md) and [Execution and delivery](../design/EXECUTION_AND_DELIVERY.md). They explain reference resolution, full-result validation, commit visibility, frozen requests, whole-batch recovery, stop states, and publication as local sequences. This record preserves why those boundaries were chosen and which earlier alternatives remain merely historical or optional.

<a id="terms-used-in-this-record"></a>
## Terms used in this record

These definitions unpack existing responsibilities. They do not finalize the open tool schemas or add a subsystem. Their governing distinctions come from EVT-0878, EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1107, and EVT-1166.

| Term | Meaning in this discussion |
|---|---|
| Nexus and route | Nexus is the configurable model-access layer used by the intended app, including the user's subscription connection. A route identifies the selected model/access/protocol configuration. Another route does not establish its capabilities, input limit, image handling, or failure behavior. Chat Completions and Responses are the two native protocol families discussed. |
| Native reply / journal | The reply in the provider protocol, including message items, tool-call IDs/arguments, images or image references, reasoning items where applicable, and completion/error information. The journal preserves received originals. A framework's display message can be a projection of that record. |
| Candidate | Received proposed document content or writing arguments retained before validation. It can contain correct prose with invalid page metadata, or incomplete raw arguments. Saving it preserves work. It does not make the failed call executable. |
| Draft | A usable working document state that can be read, repaired, previewed, and exported with incomplete or unknown facts identified. A draft can have an immutable saved version. “Draft” describes completion status, while immutability describes how a saved version is addressed. |
| Committed version, working head, delivery selection | A committed version has a durable identity and content. The working head points to the current working version. Delivery selection identifies the version and task scope chosen for export. These can differ: a newer experiment does not replace an earlier selected deliverable automatically. |
| Content reference | An exact address into preserved content, such as candidate identity plus a JSON pointer to one block, or evidence identity plus its internal region. It permits reuse without regenerating the text. Reusing content does not automatically replay the old edit/delete operations around it. |
| Context policy and settlement | Small state describing selected evidence, pin/release choices, useful notes/references, compaction coverage, and processed batches. Settlement applies accepted context-change intents once at a defined sequential boundary. It is state coordination, not proof of source coverage or semantic correctness. |
| Model-input view / hydration | The actual selected content assembled for a particular model call. Hydration resolves references into the requested text, fields, or images. Saving an artifact makes it retrievable. Selection determines whether it enters this input. |
| Frozen request | A prepared request whose selected content, route/model settings, generation parameters, and tool schemas are fixed for recovery of that same decision. Resolving `latest` again or adding a newer image would change it. A later decision may prepare another request. |
| Logical step / physical attempt | A logical step is one intended model judgment. An attempt is an actual send for that step. Recovery retains the prepared step and its consumed budget. New user input or deliberate regeneration creates a new intended decision even if its input happens to be byte-identical. |
| Accepted reply / tool batch | A complete reply accepted by the executor, and the full declared list of tool calls for which it takes responsibility. The batch must retain all call identities, order where required, results, and unfinished work. One successful call does not establish that the rest of the batch is settled. |
| Operation receipt | The durable outcome of one accepted operation, bound to its original identity and input. A receipt can say “created V12” after the current head becomes V13. Replaying the receipt reports that past outcome and must not select V12 again. |
| Graph checkpoint | A saved graph state/progress boundary used by the runtime to continue execution. Restoring it does not undo a sent request, restore spent budget, delete a committed version, or cancel an external process. Domain receipts and request records cover those effects. |
| Compaction / handoff | Compaction reorganizes selected conversation/work history to fit a later input. A handoff carries effective requirements, useful decisions, unfinished work, and exact references needed to continue. It is potentially lossy semantic work and uses the shared model-request accounting when a model generates it. |
| Scope / source mapping / acceptance | Scope states which complete section or other bounded content the user requested. Source mapping relates output to physical pages, printed labels, and regions. Acceptance concerns faithful, usable content for that scope. A complete map or a valid schema does not establish acceptance. |

<a id="historical-case-labels"></a>
## Historical labels and what their observations support

The labels below identify earlier exercises. They are not active presets, queued jobs, or evidence that the rebuild already works. The local [earlier evidence account](02-context-state-and-evidence.md#p2-005) preserves the comparison qualifications. EVT-0855, EVT-0878, EVT-0942, and EVT-1166 supply the late corrections used here.

| Label used below | Context and useful inference |
|---|---|
| 13-page A/C | A used full history and C used the checkpoint variant in a historical comparison. Their delivered drafts still contained emphasis/glyph defects. A's final emphasis issues were on pages 16/18/24. C also included page 14 and the `礪`/`厲` distinction. This motivates source inspection and exact editing, without proving one context strategy caused those defects. |
| 40-page comparison | Larger historical attempts used a 3,600-second/100-round configuration. Their recorded endings included HTTP 408/incomplete streaming and a separate timeout on request 57. A page-27 candidate had correct `本文件` before rejection, while later regeneration produced `本文作`. Candidate reuse addresses that observed regression. OCR volume alone does not diagnose the network endings. |
| 9-page B/C and P | Earlier natural-use exercises were cited when discussing whether agents spontaneously use optional mechanisms. P had selective/checkpoint features disabled. Its non-use therefore cannot show that enabled context tools would be ignored. These labels provide no universal natural-adoption rate. |
| Breasts / Figure 4–13 / Core Delivery | A source-accepted Nursing subsection at physical page 12, printed page 68, excluded adjacent content. It demonstrates why a task can cover only part of a page. Its first inspect produced 191,662 characters, so a heavy input can coexist with successful scoped delivery. |
| R1/R2 | Bounded injected-failure recovery exercises. R1 included an injected outage and roughly 188 seconds before forwarding. R2 interrupted a streaming response before completion. Their completed deliveries support those tested boundaries, not arbitrary process-crash or natural prolonged-outage recovery. |
| Nursing, Gynecology, JRE, News Writing | Names of earlier source/example packages with particular accepted outputs. The names are historical evidence labels, not a requirement to rerun those packages or reproduce old APIs and storage formats. |
| 228 checks | A historical offline test result against particular old modules. It can guide selective reuse of behavior and fixtures. Transferring a module into a new graph does not transfer that verification result. |

Read these cases as motivation for the corresponding contract. The examples using V10/V11, policy 7/8/9, page 12/13, or an 80k capacity target are explanatory boundary scenarios. They do not claim those exact events occurred in a production run.

<a id="local-patching"></a>
## Local editing and candidate preservation

**Sources:** EVT-0827, ATT-21. EVT-0828, EVT-0841, EVT-0855. EVT-0856, ATT-22. EVT-0857, EVT-0878.

- **Observed motivation:** the historical 40-page task had correct `本文件` in a rejected page-27 candidate. A later reconstruction produced `本文作`. A rejected complete page map contributed to rewriting friction. Historical 13-page A/C review also found emphasis omissions on pages 14, 16, 18, and 24 and the `礪`/`厲` character issue. These examples support exact reuse and local repair. They do not establish compaction as the cause, an automatic correction rule, or a guaranteed quality improvement.
- **Superseded inference:** ATT-21 read the requirement to keep logical sentences/tables intact around page markers as requiring a whole table to be one indivisible database block. That requirement protects readable output and source correspondence. It does not prescribe storage granularity. A table can remain complete in output while a cell, substring, or subregion is addressable internally. A full structured table editor is not a prerequisite.
- **Retained direction:** support whole-section reconstruction, stable-block insertion/replacement/deletion/movement, exact edits inside a block, file/reference import, and reuse of rejected candidates. Changing one character or adding emphasis should not require regeneration of a 4,000-character table. The guarantee is preservation of text not selected for change, not semantic correctness or “zero risk.”
- **Patch contract proposals:** bind edits to the exact document/candidate and target-content version. Require expected original text. Do not silently fuzzy-match, normalize glyphs, or convert traditional/simplified Chinese. Validate the complete patch set in a working copy. Commit atomically.

  Retain rejected work and reasons. Editing a candidate produces a traceable successor and preserves the original. RFC 6902's `test` and explicit sequence were cited as design inspiration, not an existing string-patch implementation.
- **ATT-21 example caveat:** `<td>厲行節約</td>` → `<td><strong>礪行節約</strong></td>` with `expected_matches: 1` demonstrates mechanics only. A unique match does not prove semantic location or authorize the glyph change. The PDF must support every textual correction.
- **ATT-22 refinement:** repeated cells (`0`, empty cells, `是`, `12.4`) can make whole-block exact search ambiguous. An optional raw-line range plus expected text, within-range occurrence/position, or a tool-generated location reference can reduce retransmission. Line numbers are not sufficient for repeated items on one line or a one-line HTML table. Visual wrapping differs from raw newlines. JavaScript UTF-16 indexes and backend character indexes need an explicit common convention.
- **Retained batch option:** align all nonoverlapping patches to the same unchanged base snapshot. Validate them first. Then replace from the greatest offset backward. This prevents one edit shifting another's coordinates.

  Explicit sequential semantics are an alternative only when clearly defined. Accidental anchor creation/destruction must not be implicit. Whole-block replacement and file import remain available.
- **Evidence limit:** ATT-22's claim that this removes all eight historical tool errors is unsupported. The eight included OCR timeout-parameter and post-success result-selection failures, beyond editing and page-map friction. ATT-23/ATT-24 described the breakdown as six underlying rejections and two post-success projection errors. That source-record classification illustrates why a returned error does not establish that an operation failed to commit.

  It is not a new verification of the old runs. ATT-24 also cited R2's rejection of an empty `remove_ids` list as concrete insertion friction. This supports a pure insertion/append capability without requiring a dummy deletion.

For example, suppose the saved table contains the same `12.4` in three cells and only one source cell is bold. A replacement of the first matching `12.4` is ambiguous even though it leaves every other character untouched. The usable edit describes the fixed table version, a returned cell/range location or sufficiently precise surrounding text, the expected old content, and the intended markup. The app can reject a stale or ambiguous target before publishing a version.

The agent must still inspect the source to decide whether that particular cell is bold. This is the practical difference between preserving untouched bytes and proving a correction right. The locator and operation schema remain open choices.

RFC 6902's `test` compares an expected JSON value at a location before a later operation proceeds. It does not supply string search/replacement semantics. The source used it as an analogy for checking the stored target's `expected_old_text` before applying `replacement_text`.

ATT-21's `find_exact`, `replace_with`, and `expected_matches` were one proposed surface. ATT-22 narrowed search with `line_range: [start_line, end_line]` and `occurrence_in_range`. A unique match still does not establish the correct source cell. The [precondition and locator explanation](../design/DOCUMENT_ENGINE.md#patch-preconditions-and-locator-fields) separates expected content, explicit location, count, and patch order without selecting a final schema.

<a id="source-output-comparison"></a>
## Source, output, and visual comparison

**Sources:** EVT-0827, ATT-21. EVT-0841, EVT-0855. EVT-0856, ATT-22. EVT-0878.

- **Retained direction:** make the saved output and relevant original pixels easy to inspect together. Bind previews to a specific document version. Optional paired images, independent crops, or an explicitly chosen montage can reduce navigation. Labels and dividers belong outside source pixels. Retain originals, coordinates, and surrounding context. This can help distinguish source interpretation, Markdown emphasis, and rendered-output errors.
- **Hypotheses, not diagnoses:** ATT-21 attributed old emphasis errors to cross-turn visual memory. ATT-22 substituted visual downsampling as the true bottleneck and illustrated 24×24 glyphs becoming 12×12 after joining pages. The recorded task established neither causal claim.

  Comparison does not make every mistake immediately visible. Two native image items do not guarantee full model-side resolution. Route preprocessing can still resize them. The cited Qwen processor illustrates that qualification, not a fresh benchmark.
- **Source precision:** the old `Block` had `id`, `pages`, and `markdown`, with no bbox. A block ID plus page is not a precise crop. Use a known region when available. Use a page or agent-selected region when only coarse location exists. Use multiple references for multi-page/multi-region content. Do not require a bbox for every word or cell.

  Desktop synchronized navigation means jumping to related source content, not aligning PDF coordinates row-by-row with reflowed Markdown.
- **Reference proposal:** optional `source_refs` can reuse inspect/OCR positions without hand-entered coordinates. A bare `p14_b03` is not durable: another OCR engine, crop, or recomputation may produce a different block with that name. Bind the reference to immutable evidence plus its internal block/field location. Derive PDF identity, page, coordinate system, and render parameters from that evidence. Historical OCR already distinguished `bbox_pixels` and `bbox_pdf`.
- **Review scope:** a review belongs to its exact output version. A later edit cannot inherit a current-version review statement without considering the changed content. This is traceability, not a mandatory review ritual.
- **Computation-cache proposal:** ATT-21 also proposed an index by source hash, tool/engine version, language-data hash, normalized parameters, and page/region for independent page render/OCR work. Overlapping requests could reuse already computed units, while `force_recompute` allows a fresh result. Computation indexing does not require storing every page as a separate file. This is a reusable performance idea, not a prerequisite or proof of savings. [The earlier cache discussion](02-context-state-and-evidence.md#cache-and-prefix) retains its broader qualifications.

<a id="capacity-visibility-and-access"></a>
## Capacity visibility and unrestricted evidence access

**Sources:** EVT-0827, ATT-21. EVT-0853, EVT-0855. EVT-0856, ATT-22. EVT-0878.

- **Historical figures:** the 40-page record carried 1,865,411 OCR characters from eight full page objects. The 13-page C request read nine objects totaling 1,976,466 characters. The next input reached 796,420 tokens. The 40-page comparisons used a 3,600-second/100-round configuration. Their separate endings included HTTP 408/incomplete streaming and a timeout on request 57. These observations do not prove OCR weight, rereading, or tool friction caused the timeout.
- **Corrected evidence misuse:** P ran with selective/checkpoint disabled. Its non-use cannot establish failure of natural adoption, lack of capacity awareness, or need for a particular mechanism. Small 9-page B/C jobs' non-use likewise does not by itself explain the cause. ATT-21's claim that agents did not release evidence because they could not see capacity is a hypothesis.
- **Retained capacity information:** distinguish original evidence size from selected content's actual contribution to this assembled input, including duplicates. Also distinguish remaining capacity under the configured route and output reserve. An OCR original may be huge while a selected `text` field is small. Repeated images must count as repeated input.

  Include system content, tool definitions, ordinary dialogue, work state, and images. Track request bytes separately from tokens. Keep unknown limits unknown. Label estimates.
- **Placement:** compute the global footprint at the built-in input-assembly boundary, tied to `input_view_id`. Individual tools can expose their own sizes. A permanent heavy-item leaderboard in every tool result is optional and can itself add history. ATT-21's 60–70% thresholds and 200,000-token denominator were illustrative/configurable, not universal limits or quality boundaries. `drafted` does not imply evidence is dispensable.
- **Explicit intent:** a save/update may optionally carry `context_delta` such as `release_when_needed` and `pin`. Omitted fields do not silently release unpinned evidence. Ordinary user revisions, unsaved reasoning, rationale, and unresolved questions need context protection alongside structured evidence. The app handles capacity. The agent judges relevance.
- **MCP boundary:** the server can report its own results and offer first-call field/range/image selection, exact rereading, and complete originals. It cannot remove content already in an external host's dialogue or infer that host's global capacity without host information. Conversely, the host can manage its own history. Content is not necessarily “welded forever.” A shared `DocumentService` cannot promise the built-in runtime's global footprint for every interface.
- **Superseded restriction:** ATT-22 proposed a compulsory compact/default initial result and described it as MCP's only defense. Preserve the caller's ability to request full/raw/field/range/native-image content on the first call, without a summary gate or fixed text-first preset. Changing defaults is a separate product choice. `text`, layout, words, and font/position data may overlap but are not interchangeable. Deduplication must not presume one representation always suffices.

<a id="scope-map-and-completeness"></a>
## Task scope, page facts, and actual completeness

**Sources:** EVT-0827, ATT-21. EVT-0855. EVT-0856, ATT-22. EVT-0872, EVT-0878.

- **Retained separation:** document/evidence services own sources, versions, assets, candidates, and precise modification. Task state owns effective requirements, scope, progress, issues, and their associated versions. Execution state owns dialogue, pending actions, context policy, operation/request records. These responsibilities may share SQLite and one process.
- **Historical scope example:** converting pages 1–10 today does not make pages 11–173 permanently outside all future tasks. A historical version's `outside_scope` designation can correctly describe that task. The error is blindly inheriting it into a later full-book task.
- **Retained update direction:** accept partial/sparse page changes and merge them against the base. Internal sparse storage and full output mapping are compatible. Derive the complete mapping from source page count, task scope, and known facts. Do not force the model to retransmit 173 entries to correct one page. Retain the full source-correspondence outcome.
- **Superseded completion test:** ATT-22 proposed only `converted`, `source_blank_or_omitted`, and `drafting`, then completion when every target page is converted or blank/omitted. One paragraph on a page does not account for its tables, footnotes, or captions. The Breasts case requested one complete portion of page 12 and excluded adjacent content, so `target_pages=[12]` alone cannot express the scope. A section, figure, table, or other bounded content may define the task.
- **Required distinctions:** source facts (physical and printed pages, regions, evidence), task scope, output-to-source relationships, and progress/review status remain separate. `converted` can report a relation but cannot certify quality. Confirmed blank source and a decision to omit decoration are different facts.

  Keep `none` and `unknown` printed-page states distinct. `none` records that no printed label is present. `unknown` means the printed label remains undetermined. Physical page order still identifies the page. Complete source mapping does not imply every page must have body content.

<a id="continuity-and-state-ownership"></a>
## Continuity, state ownership, and replay identity

**Sources:** EVT-0827, ATT-21. EVT-0828, EVT-0841, EVT-0853, EVT-0855. EVT-0856, ATT-22. EVT-0857, EVT-0872, EVT-0878.

- **Retained continuity view:** common saved document/candidate/evidence/work data can support context handoff, optional chapter delegation, and reopening tomorrow. A “Document Continuity Snapshot” is a selected, auditable handoff view, not one mechanism that replaces all three lifecycles.
- **Different lifecycles:** same-run context transition needs active requirements, progress, issues, and input selection. A child/new task needs explicit scope, inherited information, outputs, and edit authority. Restoring the same execution additionally needs checkpoint, pending steps, receipts, original budgets, and reconciliation of outside changes. New tasks must not inherit old pending tool calls. Recovery must not overlook unprocessed results. Task-specific notes/issues do not all belong to document-global state.
- **Superseded settlement design:** ATT-21 proposed a SQLite settlement key from accepted tool-batch identity instead of `hash(current_policy_rev, proposal_ids)`. That hash would turn policy 7→8 into a second 8→9 settlement on replay. The stable batch idea fixes that identity problem. But the proposal also instructed recovery to force `active_policy_rev` back to the receipt's policy 8. That would undo a legitimate later policy 9.

  Replayed prior effects retain the advanced state. An incomplete original transition can use its receipt only under compatible parent state. Incompatible branches/modifications require a conflict.
- **Later simplification:** small context policy belongs in Graph State: selections, release/pin policy, notes or references, compaction boundary, and settled batches. Remove an unnecessarily external policy-version/activation mechanism for the single built-in executor. Tools report intents. One `before_model` settlement updates policy and processed batch once. Request assembly applies it. Reducers do not automatically resolve conflicting `pin`/`release` intents or two parallel whole-policy replacements.
- **Corrected causal claim:** two physical databases did not cause the policy rollback. Interpreting an old result as present state caused it. The same mistake can happen in one database. Conversely, Graph/checkpoint rollback cannot undo sent requests, spent budget, committed document versions, or completed external effects. Durable service-owned request records and operation receipts remain necessary, even if physically colocated.
- **ID distinctions:** `(thread_id, checkpoint_ns, tool_call_id)` plus argument hash can collide across accepted parent replies. ATT-22's proposed `parent_model_request_id == input_view_id` also conflated roles. A service can resend a view. A turn can use several views. Only an accepted response generates executable calls.

  Use stable application operation identity with accepted parent response and branch relationship. Separately relate logical request, physical attempt, and input view. Same operation recovery reuses identity. A new accepted batch gets new identity.

<a id="transport-salvage-and-slices"></a>
## Transport, process inspection, and delivery increments

**Sources:** EVT-0827, ATT-21. EVT-0855. EVT-0856, ATT-22. EVT-0878.

- **Observed legacy coupling:** `Provider.pending_images`/`flush_images` and `Agent.model_round` carried mutable request state. Merely wrapping the old instance as a stateless model is unsafe. The proposal is request-local encoding.

  Chat Completions pairs tool-result images with the corresponding following native image message. Responses encodes them in the corresponding function output and preserves native reasoning behavior. Attempt-local SSE assembly and diagnostic filtering remain relevant knowledge. Exact framework hooks and model class names are proposals, not implemented interfaces.
- **Budget distinction:** one durable request ledger is useful, but does not make transport retries, local preflight reconstruction, and sent capacity-recovery attempts the same policy. With `automatic_retries=0`, defining all sends as `1 + automatic_retries` leaves no post-rejection repack send. Local preflight has no HTTP attempt but uses time. Every actual send counts against common totals.

  ATT-22's one immediate overflow resend is a proposal, not an adopted default. Only recognized capacity errors and a view that improves that specific limit justify repacking. Valid requirements/work must survive. HTTP 413 may carry `Retry-After`, so “always immediately/no wait” was corrected.
- **Historical retry illustration:** ATT-22 contrasted default zero retries with a trial value of two and 60–120-second backoff. It separated listed 500/502/503/504, timeout, and interrupted-stream cases from recognized capacity rejection. These values/classifications describe that proposal and earlier environment. They are not inherited new-repository defaults or a newly authorized trial.
- **Process inspection proposal:** distinguish read-only `inspect_attempt`, explicit `terminate_attempt`, and bounded `salvage_attempt`. Inspecting/salvaging must not silently kill a running child. Windows Job Objects, `FILE_SHARE_READ` snapshots, explicit `terminate_running_process=True`, and complete decoding were proposed mechanics. The process tools must report read/write stability and conflicts. Rescued partial output is not whole-task completion. These ideas do not create a required V1 salvage subsystem.
- **Construction priority:** ATT-21 listed P0 document editing/visual comparison, P1 context continuity, P2 transport/process services, and optional P3 optical hints/chapter episodes. These describe product value, not a rigid layer-by-layer build order. Waiting for every lower layer before connecting Nexus postpones integration discoveries.
- **Retained increment principle:** connect a small useful source→save→reopen→export flow using shared tools and the actually used Nexus route. Preserve candidates from the first increment. Then add precision and context continuity where needed. ATT-22's first slice bundled new framework, both protocols, persistent retries, sparse document model, full chapter, and interruption recovery and was judged too large. Other product protocols remain capabilities to integrate, not grounds to expand the first slice. Candidate loss on first validation failure must not be deferred to a second slice.
- **No automatic work authorization:** these reviews explicitly described read-only analysis, with no project edits, tests, or Nexus model calls. Vertical slices are retained reasoning about implementation order, not a queued execution request in this reference.

Here a **vertical slice** connects enough of the actual path to deliver a bounded useful result. The example path selects a source/scope, obtains needed evidence, saves correct candidate content, and repairs a rejected metadata field. It then reopens the saved version and exports that version. It does not prescribe those as mandatory model steps on every conversion. It was preferred over finishing every editing feature, then every context feature, then all transport machinery before testing whether the parts work together.

SSE means the streamed server-sent-event fragments assembled by the request service. A fragment must not be mistaken for a complete accepted tool call.

<a id="unaltered-text-and-locators"></a>
## Raw text fidelity and edit views

**Sources:** EVT-0880, ATT-23. EVT-0881, EVT-0894, EVT-0914. EVT-0915, ATT-24. EVT-0942.

ATT-23 proposed banning bare offsets and normalizing every ingested block to LF plus NFC, with deterministic HTML table pretty-printing around rows/cells. Its rationale was legitimate. Supplementary-plane characters count differently in Python code points and JavaScript UTF-16 units. CRLF/LF and a one-line HTML table complicate line-based addressing. The review rejected its remedy.

The historical local Python check showed `U+2F800 → NFC → U+4E3D`. That proves NFC is not universally lossless for source character distinctions. It does not prove that every normalization visibly changes text or that the PDF used that code point. Inserting HTML newlines creates text nodes and may alter whitespace, copying, or parsing.

Preserve the original candidate. An explicit LF version-storage contract remains possible. Pretty-printed lines, table grids, normalized search, and line numbers should be read/edit views with mappings back to actual stored content. Offsets remain usable with a defined counting convention and programmatic conversion. The model need not hand-count them.

A version-bound `cell_ref` can be a convenience over the same patch mechanism. `row=5,col=3` alone is ambiguous with rowspan/colspan: distinguish visual grid positions from stored cells. Neither a mandatory table AST nor permanent removal of cell references follows.

ATT-24 proposed only `patch_block(..., expected_old_text, new_text, occurrence=1)` plus a read-only cell grid, alleging cell references require a separate byte-splicing AST engine. The correction retained generic patches first and optional cell locators, while rejecting silent first-occurrence selection. Require uniqueness unless the caller explicitly selects a returned location. The proposed “95% of errors” coverage has no measured support. Larger or multiple patches can handle structural changes. A cell convenience need not express every edit.

ATT-23's concrete locator names were `line_range`, `context_before`, `expected_old_text`, and `context_after`, with optional explicit occurrence selection. Its `table_cell_locator` proposed row/column addressing. ATT-24's grid added `visual_row_span` and `visual_col_span`. These are ways to resolve a version-bound target, not a rule to normalize stored HTML into that grid. Define raw newline/index conventions and visual-grid versus stored-cell meaning before using them. Neither line numbers nor `row=5,col=3` is self-explanatory in a table with repeated values and merged cells.

<a id="preserve-before-validation"></a>
## Preserve received content before validation

**Sources:** EVT-0880, ATT-23. EVT-0894, EVT-0914. EVT-0915, ATT-24. EVT-0916, EVT-0942.

Saving candidates only inside `DocumentService.save()` misses input rejected earlier by a framework's schema validation. The historical `AgentTools.call()` already saved full tool arguments before validation/execution. Retain that protection across built-in, MCP, and CLI entry points.

First preserve fully received writing arguments. Then validate them. Create/update a usable draft. Finally, commit a document version.

Return a stable reuse reference and precise errors so metadata can be corrected without rewriting body text. Raw records can hold invalid arguments. Valid drafts and published versions still satisfy their own contracts.

The reviewed `wrap_tool_call` position ran before tool validation, but its `args` were an already-parsed dictionary, not raw response bytes. The adapter separately preserves the complete native reply. A truncated reply may be diagnostic evidence. It does not authorize executing a partial tool call. If a write committed and later response-field selection failed, retain the successful receipt and distinguish that from an unperformed write.

The concrete validation path was `BaseTool._parse_input` applying Pydantic `args_schema` before the tool function. A `ValidationError` can therefore prevent `DocumentService.save()` from running at all. An outer `wrap_tool_call` can capture the received `tool_call["args"]` first. Raw decoding failures that become `AIMessage.invalid_tool_calls` need the separate Nexus reception path. The [capture sequence](../design/DOCUMENT_ENGINE.md#framework-capture-order) explains these two rejection boundaries and the illustrative `error_code`, `field_errors`, `saved_candidate_ref`, and `recovery_hint` error fields. Capturing a dictionary is not capture of original native JSON bytes, and a saved-reference claim still depends on a successful write.

ATT-24 proposed `write_blocks` with optional page maps and a later `publish_version` gate. Saving incomplete metadata is useful, but export cannot be gated on completion: a draft must be previewable, snapshotted, and exportable with gaps explicitly identified. A single edit can atomically include body plus optional page changes. Separating validation responsibilities does not force two model calls.

With candidate references, “validate” has more than one boundary:

1. Check the received tool/reference form after capture.
2. Resolve the referenced content and explicit changes.
3. Validate the complete merged draft/map before conditional commit. A reference envelope cannot establish the resulting document's validity, and requiring inline body text before reference resolution would defeat exact reuse. The [worked repair](../design/DOCUMENT_ENGINE.md#candidate-repair-sequence) makes that distinction without choosing a final tool schema.

<a id="draft-export-and-claims"></a>
## Draft usability, completion claims, and revisable observations

**Sources:** EVT-0880, ATT-23. EVT-0910, EVT-0914. EVT-0915, ATT-24. EVT-0931, EVT-0942.

Saving a draft preserves changes and coherent version/block relationships, with missing facts marked. Export guarantees one-version artifacts and honest draft/gap labels. Declaring completion concerns the user's full requested scope and absence of known material omissions/errors. Technical validation of structure/assets/references cannot establish semantic completeness.

ATT-23 proposed `converted_full_page`, `converted_partial_scope`, `source_visibly_blank`, `omitted_non_content`, `unprocessed/drafting`, plus scope-derived `outside_task_scope`. These can represent claims and observations, not wholly objective completion facts. A natural-language subpage boundary helps express “Breasts and Figure 4-13, physical page 12/printed page 68”. It cannot prove all figure labels or content are present.

Completion must bind both scope revision and document version. Completing that subsection under task A does not complete task B's expanded full page. Keep useful prior work and identify added/uncertain scope without automatically requiring every old part to be rereviewed.

ATT-24's separation into `source_page_inventory`, `block_provenance`, and `task_scope_and_claims` was retained as a responsibility model, not a prescribed three-table schema. Stable source identity/physical order differs from revisable observations such as a read printed label or inferred provenance. “Printed page 68 never becomes invalid” was corrected: the PDF may be unchanged while the observation was wrong. Preserve earlier observations in their historical versions and retain immutable evidence references alongside page numbers/notes.

`none` and `unknown` remain distinct. A copyright page may contain author, edition, ISBN, or other requested content. Do not classify it as omittable by default.

The historical 191,662-character first inspect belonged to a task that passed source acceptance: it proves input weight, not task failure. The final 13-page A emphasis defects were pages 16/18/24. C also included page 14 and `礪→厲`. ATT-24's broad attribution of failures to interface friction overstated the evidence.

<a id="batch-order-and-recovery"></a>
## Deterministic intent settlement and actual tool order

**Sources:** EVT-0880, ATT-23. EVT-0914. EVT-0915, ATT-24. EVT-0916, EVT-0931, EVT-0942.

Settlement must use trusted accepted-parent tool-call declaration order, not completion timing. Concurrent I/O can finish in a different order after replay. `before_model` can persist compact policy/processed-batch changes, while request assembly hydrates selected content without copying giant evidence back into checkpoints. Deterministic intent order does not order actual file effects: parallel revise/export or two edits based on V still need version/dependency handling.

The reviewed `create_agent` implementation dispatched calls through parallel `Send("tools", ...)`. Substituting it for the former controller's sequential loop does not preserve order automatically. The review rejected ATT-24's “30-line declaration-order lock” as a recovery guarantee. If A completed before a crash and the framework restores its pending write without reexecuting A, B may wait forever for an in-memory signal. A read of `latest` before a write can also race a later write even when each writer waits for earlier writers.

Use explicit versions for reopen/preview/export, base revisions and atomic service commits for edits, and durable receipts for recovery. When a batch needs ordering, the executor that owns the complete batch should order it. A small sequential LangGraph tool node is acceptable and does not impose a PDF conversion recipe. Independent reads may parallelize under their actual resource contract. OCR/render can create files, assets, and child processes and are not universally side-effect-free. Do not build a hidden general scheduler merely to keep `create_agent`'s form.

<a id="preview-semantics"></a>
## Whole-document rendering and honest preview locations

**Sources:** EVT-0880, ATT-23. EVT-0914. EVT-0915, ATT-24. EVT-0931, EVT-0942.

ATT-23 proposed `inspect_block_pair` rendering 300–400 DPI source crops and an output `#tbl_02` crop. The discussion withdrew its guarantee that a 900×350 image avoids all route resizing. Higher DPI cannot recreate missing scan detail. One output block can derive from several source regions, and reflowed output has different geometry. Historical preview rendering had no established block→DOM mapping.

ATT-24 then proposed independently rendering each Markdown block into `<div data-block-id=...>`, allowing the attribute through sanitization, and using Playwright locators for “100% exact” screenshots. The historical in-memory parser example refuted independence: block A `See [source][r].` plus block B `[r]: https://example.com` resolves when parsed together but not when separately rendered. Preserve whole-document CommonMark semantics. Parser source-line/token locations may support app-generated DOM anchors and one-block-to-many-DOM-region mappings. They are a basis for implementation, not a finished mapping engine.

Locator screenshots can include occlusion or only currently visible contents of a scroll container. Report actual crop coverage, dimensions, location precision, and version. Do not equate a locator with complete capture. Independent native images are useful. Optional montages remain valid. No fixed crop/DPI/visual-check stage is imposed.

<a id="adapter-integration-boundaries"></a>
## Model integration and the accepted-reply gap

**Sources:** EVT-0880, ATT-23. EVT-0910, EVT-0914. EVT-0915, ATT-24. EVT-0940, EVT-0942.

ATT-23's proposed under-150-line `NexusHttpChatModel` supposedly inheriting 100% of 228 historical checks and R1/R2 protection was explicitly retracted. The retry ledger lived in the old controller. Image pairing lived in mutable provider state. Those tests were against specific old modules, not a new adapter.

Tool binding, async calls, message conversion, and durable identities still need integration. `create_agent` needs executable `AIMessage.tool_calls`. Arbitrarily replacing all current messages with references breaks dispatch unless the dispatcher explicitly resolves them.

Retain the actual Chat Completions sequence: complete all paired tool results, then append that batch's paired native-image user message. Responses uses its corresponding function outputs. A model instance may keep configuration, pools, and service references. Avoiding request-residual mutable image queues is the meaningful requirement, not literal 100% statelessness.

The selection boundary is `complete artifact → current context selection → selected image resolution → protocol encoding`. Scanning every historical artifact to recreate images would undo release decisions. Artifacts do not automatically become model input.

A complete accepted reply may be durable while its Graph checkpoint is not. In that case, recovery must retrieve the reply by durable logical step identity before sending another request. Merely storing `accepted_reply_id` in message metadata covers only the already-checkpointed case. `(run_id, step_index)` is a possible app-owned identity with explicitly defined recovery/branch semantics, not an assumption about a framework invocation ID.

<a id="useful-slice-acceptance"></a>
## Useful delivery increments and their limits

**Sources:** EVT-0880, ATT-23. EVT-0881, EVT-0914. EVT-0915, ATT-24. EVT-0942.

The proposed first-slice checks concerned observable work:

- Native text/tools/images round-trip through Nexus.
- Correct body survives an invalid-metadata save.
- Save/reopen/read/export identify one version.
- Resume recognizes committed effects and unfinished work. Use a complete useful subsection, not an arbitrary 1–2-page cut that severs a figure/table. These were future verification directions and did not authorize new Nexus trials.

ATT-24's first slice again accumulated full editing, both streaming protocols, three data categories, DOM mapping, and concurrency coordination. The review narrowed it to content that can be saved, repaired, taken away, and resumed. Fine visual conveniences and context continuation remain distinct capabilities. Lightweight references plus pin/release alone do not finish context management. Ordinary dialogue, later user corrections, unresolved dependencies, and a single oversize evidence selection still need explicit behavior. Framework names and feature counts cannot substitute for that outcome.

<a id="small-graph-and-step-identity"></a>
## A small graph, durable step identity, and frozen requests

**Sources:** EVT-0943, ATT-25. EVT-0944, EVT-0957, EVT-0968. EVT-0969, ATT-26. EVT-0970, EVT-0982, EVT-1005.

ATT-25 proposed three nodes (`model_step`, `tool_batch_step`, `settle_step`) plus a common dispatcher. The retained reason to prefer a small `StateGraph` is direct ownership of complete tool batches, ordering, recovery, and input assembly. Pre-validation capture and reply reconciliation are needed under any runtime. `create_agent` also supplies middleware, tools, and structured-output behavior. Declining it does not make all integration work disappear.

A full `BaseChatModel` wrapper is optional if the model node can call the extracted Nexus request service directly. Node counts are not an architectural requirement. A prepare boundary can be useful without adding a model call.

ATT-25's stable key `(job_id, checkpoint_ns, model_turn_seq)` handles one straight-line restart but not all new decisions. `checkpoint_ns` is not branch identity. A branch can retain the same tuple. A no-tool answer can reach END without incrementing the counter, then collide with later user input.

Each new intended model judgment needs a durably saved new `model_step_id`. Restoring an already-prepared decision retains its ID/input. New input, deliberate regeneration, and branch rejudgment use a new ID even when their prompts/fingerprints are identical. Same ID with changed input is inconsistency, not license to overwrite the request.

ATT-26 proposed four nodes: `prepare_step → model_step → tool_batch_step → prepare_step`, with `delivery_check_step` for a no-tool reply. It assumed every recovery/branch passes through prepare and every new branch's fingerprint differs. The review corrected both assumptions. Checkpoint successors and `update_state(as_node=...)` can resume after prepare. Regeneration can reuse identical content with different intent.

Define application entry rules explicitly. Graph `durability="sync"` can ensure the prior checkpoint is written before the next step. It cannot guarantee exactly-once remote generation.

Prepare freezes route/model configuration, generation parameters, tool schemas, and actually selected content, not merely text messages or evidence filenames. Save the full request in immutable files and small IDs/references/fingerprint plus policy in Graph state. Do not resolve `latest` or swap images after prepare. Before sending, the service must record attempt consumption durably.

No accepted reply does not mean no request was sent. Inspect attempt status and original remaining budgets before bounded recovery. Only a complete durable reply for the same logical request is directly reusable.

Consider a prepared request Q that selected document V10 and a particular OCR image. While Q's response is uncertain, another legitimate action makes V11 the current head. A permitted retry of Q must retain V10, the same image, settings, and schemas. It must consume another attempt under the original budget. Replacing V10 with V11 changes the decision input and requires a new logical request.

Q's complete accepted reply may already be saved. In that case, recovery reads that reply and settles its whole tool batch before considering the next model request. This separates a historical input snapshot from the current document pointer without requiring generalized branch management.

<a id="commit-and-receipt-boundary"></a>
## A committed version and its operation receipt

**Sources:** EVT-0943, ATT-25. EVT-0968. EVT-0969, ATT-26. EVT-0982, EVT-1005.

Writing a success receipt only after a file change leaves a crash gap: committed document → crash → no receipt → duplicate operation. Bind operation ID and input fingerprint atomically to the commit. Alternatively, embed enough identity in the committed result to recover it. The historical `publication_operation` field demonstrates that principle. It is not proof of the new architecture.

ATT-26's “commit-as-receipt” proposed embedding identity in `document.json` and evidence metadata, using atomic replacement/short transactions, and eliminating a separate receipt/event store. The useful simplification does not make folder existence equivalent to save completion. The former code first moved the version folder, then updated `current.json`. A crash can leave prepared files without an advanced working head.

If save promises both version registration and head advance, stage immutable files first. Then atomically commit registration, pointer, and operation identity in a short transaction. Alternatively expose those two operations separately. Retain useful prepared results.

Successful version metadata does not replace “started, outcome unknown” records for scripts, OCR, or model requests. No receipt is not proof an effect never happened. Recovered tools must restore results and required state/context intents, not just display text. These responsibilities need finite execution records, not a general event-sourcing system. Batch-level graph nodes also do not automatically checkpoint each nested tool.

<a id="cross-interface-capture"></a>
## The cross-interface capture boundary

**Sources:** EVT-0943, ATT-25. EVT-0968. EVT-0969, ATT-26. EVT-0999, EVT-1005.

A common dispatcher is a good ownership boundary but does not prove every interface reaches it before validation. The historical installed MCP SDK validated registered-tool arguments before invoking the function, so placing capture inside that function remained too late. ATT-26 proposed a permissive transport schema plus strict domain schema, claiming this guarantees entry. Wrong container types/missing required values can still fail, and weakening schemas removes useful guidance.

The historical review then found installed MCP SDK 2.3.0's `Extension.intercept_tool_call`, preceding tool validation for an accepted `tools/call` request. It offered a way to retain clear tool schemas and perform shared capture first. Preserve the principle, not an unverified assumption about another SDK version. Each entry must save app-received, successfully decoded tool-call arguments before domain validation.

Draft metadata that is truly optional should be optional in its schema. A server cannot save content rejected by an external client before transmission. No 100% capture guarantee extends to bytes never received or undecodable protocol messages.

<a id="reading-versus-diagnostic-view"></a>
## Actual reading and expanded diagnostic views

**Sources:** EVT-0943, ATT-25. EVT-0957, EVT-0968. EVT-0969, ATT-26. EVT-1005.

ATT-25 proposed a roughly 15-line parser rule assigning `data-block-id` from `token.map`, claiming complete cross-block links/footnotes and raw HTML support. Historical parser checks showed default `html_block` rendering returns raw `token.content` and ignores `token.attrSet`. HTML needs explicit handling. Token ranges may cross content-block boundaries, requiring many-to-many correspondence. Whole-document parsing preserves supported cross-block semantics but does not enable a footnote extension absent from the parser configuration. The line-count and 100% claims were withdrawn.

The mechanism first concatenated the complete Markdown and recorded each block's half-open `[start_line, end_line)` range. It then parsed once with `markdown-it-py` and compared each top-level `token.map` with those ranges. Multiple resulting DOM elements could carry the same `data-block-id`. Simple containment alone cannot assign cross-boundary tokens correctly.

`token.attrSet("data-block-id", "blk_01")` affected the token but did not annotate the raw `<table>` returned by the reviewed `html_block` renderer. `nh3` allowing the attribute is a later sanitization concern, not a fix for an attribute never emitted. The [source-map walkthrough](../design/DOCUMENT_ENGINE.md#parser-source-map-mechanics) explains the retained basis and raw-HTML limitation independently of the source attachment.

ATT-25 also proposed no fixed heights/overflow/sticky elements, a viewport widened to `scrollWidth`, and union-bound screenshots or segmentation. These can support an expanded diagnostic view but may hide real reading defects under normal CSS/viewport. Keep actual-reading and expanded/zoomed views explicit and version-bound. Record changed conditions. Disjoint DOM regions may be clearer than a large union box full of whitespace. This remains a convenience direction, not proof it fixes old glyph/emphasis errors.

<a id="capacity-in-first-usable-runtime"></a>
## Capacity belongs in the first usable runtime

**Sources:** EVT-0943, ATT-25. EVT-0968. EVT-0969, ATT-26. EVT-0970, EVT-1005.

ATT-25 postponed context management until a third stage for 40-page-plus documents. The review corrected the page-count premise: a single-page inspect can contain 191,662 characters. Basic capacity behavior belongs with useful runtime work:

- Save full evidence separately.
- State what is selected/not sent.
- Estimate actual input.
- Retain native/full/precise access.
- Preserve results on overflow instead of silently truncating.

ATT-26 moved this earlier, proposing a loaded/unloaded-range inventory on oversize results. That helps a large new result but not history already too full to fit the inventory or another answer. Reserve room before exhaustion for tool schemas, image estimates, normal output, and compaction itself. Distinguish large-result handling from accumulated-history handling.

Capacity estimates across routes remain fallible. The review rejected a “never overflows” guarantee. Basic history compaction/recovery belongs in the first usable long-task version, without waiting for advanced screenshot/table helpers. Full first-call results remain available within capacity. Inventories are not universal gates.

The adapter may stream selected image bytes from disk. A categorical disk-access prohibition is unnecessary. Context policy chooses evidence, the input assembler resolves that choice, and encoding must obey the frozen selection without resurrecting released artifacts. The Nexus service can be an in-process module in one Python backend.

<a id="selected-version-delivery"></a>
## Select a delivery version and distinguish stopping from delivery

**Sources:** EVT-0943, ATT-25. EVT-0968. EVT-0969, ATT-26. EVT-0999, EVT-1005.

A no-tool model answer can be a question, blocker report, or early stop, not completed delivery. Check the selected saved version, corresponding export, declared scope, and draft/completion state. Structural validity, agent completion claim, and source-review outcome remain different information. A valid schema cannot establish `complete_accepted`. That label does not mandate routine human approval.

ATT-26's automatic export of the newest version was narrowed to explicit delivery intent `(version_id, scope_rev)`. Example: V10 is good, V11 is a trial table edit, and the agent chooses V10. Automatically shipping latest V11 overrides that choice. A known selected version can be packaged by the app without spending another model turn or routinely asking the user. Preserve consistent Markdown/JSON/HTML/assets/ZIP for that selected version.

EVT-1040 further places that intent with the current task, not one global document manifest entry that other tasks could overwrite. Committed versions/provenance remain document facts. Direct selection of existing V10 must be possible without manufacturing an edited successor merely to select it. Selecting a newly committed version can remain a convenience. This ownership rule does not require general branch management.

An exported version and abandoned experimental candidate can coexist. Only candidates still belonging to unfinished current work merit follow-up. Their mere existence must not trigger rewriting. A real request for user clarification enters waiting-input state rather than looping through prepare without new information. Practical first-version editing includes append/insert/delete/reorder, local page/provenance updates, and candidate-body reuse with repaired metadata. Substring patching alone is insufficient.

<a id="incremental-edit-and-reference-contract"></a>
## Incremental editing and exact candidate references

**Sources:** EVT-1006, ATT-27. EVT-1007, EVT-1040. EVT-1041, ATT-28. EVT-1042, EVT-1060, EVT-1068. EVT-1069, ATT-29. EVT-1107. EVT-1108, ATT-30. EVT-1147, EVT-1166.

ATT-27 proposed `edit_document(base_version, reuse_candidate_ref, block_ops, page_map_updates, provenance_updates, delivery_selection)` to avoid resending unchanged body or the full page map. Its operations were append, before/after insert, replace, delete, reorder/move, and exact patch. Multiple block operations should act in a defined sequence on one working copy, then commit one version only after the merged result validates. Define whether later locators refer to earlier operation results. Inner patches sharing a base snapshot retain their explicit separate semantics. Tool count alone neither minimizes schema tokens nor cognitive load.

Candidate repair cannot silently inherit/replace nested fields or arrays. For example, a candidate contains updates for pages 12 and 13. Correcting page 12 must not silently erase page 13. Define omitted-field preservation, replacement, per-page upsert, and nested-field handling.

Editing a candidate produces a new effective-argument snapshot and operation ID with parentage, leaving the original intact. Reusing an old operation ID with changed input violates replay identity. Replacing the base version also requires rechecking delete/replace/patch applicability.

ATT-28 proposed avoiding implicit parameter inheritance by importing `block_ops_from_candidate`, explicitly resubmitting small page changes, and exposing `save_draft`, `edit_document`, and `select_delivery`. This is a possible clearer tool surface, not a mandatory count. Per-page upsert needs a defined `pdf_page` key. Unknown printed label, uncertain scope, and unprocessed work remain distinct. Missing information must not automatically become `outside_scope`.

The correction separated **content reuse** from **operation reuse**. `block_ops` can include deletion, reordering, or context-sensitive patches. Adopting a correct paragraph must not force those old effects. A failed `save_draft` may contain `blocks` rather than `block_ops`.

Support immutable `candidate_id + JSON pointer` references or a selected block list wherever content is accepted. Separately allow whole-operation reuse only after validation of its current intent and base. ATT-29's `from_candidate`, `select`, `block_indices`, and `override_meta` were illustrative shapes, not finalized JSON schemas. Raw capture precedes best-effort indexing. An indexing failure must not erase the saved raw candidate.

ATT-29 called those capabilities `content_from_candidate` and `replay_ops_from_candidate`. Its example `{"from_candidate":"cand_04","select":"/blocks/2","override_meta":{}}` names selected content and explicit metadata handling. `replay_ops_from_candidate="cand_05"` names an operation sequence requiring renewed applicability checks. Those names explain why the earlier `block_ops_from_candidate` proposal could not serve both uses, and remain alternatives to specify rather than an agreed input schema.

The final narrowing keeps complete-candidate exact reuse, insertion/append, and partial page updates in the first contract. It requires clear answers to which original is referenced, which fields change, what omitted fields preserve, and when commit succeeds. It does not require malformed-JSON salvage first.

The page-12/page-13 example can be read as a concrete contract exercise, rather than a finalized API:

| Stage | Preserved information and required decision |
|---|---|
| Receive candidate C | Retain C's complete body and the proposed page-12 and page-13 metadata even if page 12 is invalid. Report the actual metadata rejection. Do not discard the body. |
| Prepare repair | Identify C and the exact body fields to reuse. Supply the correction for page 12. For a broader candidate merge, define that omitted page-13/body fields remain unchanged unless explicitly replaced. For content-only import, explicitly carry any desired page-13 candidate metadata. The rejected call did not commit that metadata into the base. The implementation must not guess between these intentions. |
| Validate and commit | Build a complete effective submission against the named base. Validate the merged structure. Commit only when the expected base/head condition still holds. Preserve C and the repair's parentage if validation or concurrency checks fail. |
| Return or replay | Return the new version and its operation receipt. Repeating that same accepted operation returns its original outcome. Changing the repair's input creates a new operation identity. |

Likewise, reusing a paragraph from C's `blocks` array means retrieving that paragraph. Reusing C's `block_ops` means asking to run a sequence that might delete or move other blocks. Keeping those two intentions separate is what lets a later task use good prose without inheriting a stale edit plan.

<a id="candidate-relationships"></a>
## Useful candidates, partial adoption, and lineage

**Sources:** EVT-1006, ATT-27. EVT-1023, EVT-1040. EVT-1041, ATT-28. EVT-1060, EVT-1068. EVT-1069, ATT-29. EVT-1107. EVT-1162, EVT-1166.

ATT-27 proposed considering only candidates created after the latest successful commit and not superseded/abandoned. That rule was withdrawn: first-section candidate A can still contain necessary correct content when unrelated second-section B commits later. Use actual adoption/repair/replacement/abandonment relationships, not timestamps. A small active-work reference set can be enough.

ATT-28's statuses `active_unresolved`, `adopted`, `superseded`, and `abandoned` improved explicitness but a global candidate or task-only flag was still too coarse. One branch adopting two of three blocks does not resolve the third or another branch. A new candidate touching the same page does not prove complete replacement. Keep immutable originals separately from scoped adoption/discard relations. Record version commit and actual adoption links atomically when applicable. Do not require a disposition report for every unused decorative/header fragment or make every unadopted candidate a completion gate.

ATT-29 proposed immutable candidate records plus `version_candidate_links` along version ancestry instead of a separate lifecycle state machine. This accurately records historical usage, but cannot alone prove current content or unfinished work. V10 can adopt a paragraph and V11 delete it while the ancestor link remains. Current content comes from the specified version. Necessary unfinished work comes from task state. Branch management and a complete lineage UI are reference options, not V1 prerequisites under the final narrowing.

<a id="reconcile-without-pointer-regression"></a>
## Reconcile prepared work and replay historical receipts

**Sources:** EVT-1006, ATT-27. EVT-1023, EVT-1040. EVT-1041, ATT-28. EVT-1068. EVT-1069, ATT-29. EVT-1104, EVT-1107. EVT-1108, ATT-30. EVT-1147, EVT-1166.

ATT-27 proposed immutable version folders plus one atomically replaced `document_manifest.json` containing committed versions, working head, and selected delivery. It claimed a matching prepared folder could simply complete the manifest update after a crash. Counterexample: A prepares V11 from V10, another legitimate operation advances to V12, and replaying A would roll the head back. Correct recovery follows these conditions:

- If A already committed, return its historical result.
- Finish a complete prepared result only if its expected base/target still holds.
- Otherwise, retain the useful prepared result and report conflict. Atomic file replacement still requires serialized conditional updates to avoid lost writers. `ReplaceFileW` does not guarantee durability of a whole version's assets or universal power-loss recovery.

The preferred simplification became SQLite metadata for version registration, uniqueness, pointers, and operation facts, with staged immutable content files. Checkpoint and metadata are separate commit boundaries reconciled through identity. ATT-28's document-version DAG plus per-task/branch heads and delivery choices illustrates ownership. It is not a requirement to implement generalized branching.

Final V1 preference is one active writer per task. Explicit regen/new-input entry rules remain useful. A display `branch_seq` need not become a second correctness key.

Persist resolved defaults when an operation starts. A missing version that resolved to V10 retains V10 on recovery. Selected parameters and its output/attempt directory also retain their resolved values. Dynamic defaults are still dynamic until resolved. Operation keys need app task/accepted-reply or step identity, not provider `tool_call_id` alone. An old Graph snapshot can describe what an earlier request saw but must not overwrite SQLite's later committed head.

The start boundary matters for a sequential batch containing `save`, then `preview` with no version. Under that declared ordering contract, preview should resolve its default after its required earlier save. Resolving every omitted version at batch acceptance could bind preview to the old head instead. Retain the accepted arguments and the later effective values as related records. Recovery checks the recorded values rather than resolving “current” again. [Hash and identity distinctions](../design/EXECUTION_AND_DELIVERY.md#hashes-and-identity) explain why equal content, one accepted operation, and present applicability are separate facts.

**Historical receipt rule:** A produced V12 and B later produced V13. Replay A returns the original V12 receipt while retaining V13. C selected V10 and a later selection chose V11. Replay C returns its historical selection result without resetting delivery to V10. Receipts are facts at commit time, not assertions that today's pointer still equals that result. Recovering a frozen model request still uses its original input rather than silently inserting today's head.

Operation-specific reconciliation is necessary:

- Save/edit checks the original commit and expected base.
- Select-delivery checks the historical selection and valid target/scope.
- Export checks the specified version and destination package independently of current head.
- Render/preview checks existing artifacts and parameters and can create a new independent attempt. Export V10 while editing V12 is valid. Incomplete draft export must not acquire a hidden “full scope complete” precondition from selection validation.

The accepted model reply may contain A (edit to V12) and B (preview still unfinished). Finding A's receipt is insufficient to start the next model round. Reconcile the **entire accepted tool-call list**, restoring completed results/intents and handling remaining calls or their stop reason. Only after whole-batch completion can the next new request be assembled from current committed work. The former controller's `next_call`/pending-operation state was evidence for this responsibility, not proof that a new graph already provides it.

This example has four different recovery boundaries:

| Last known durable fact | What remains to decide or recover |
|---|---|
| Request saved, complete reply absent | Check whether an attempt was sent, its consumed allowance, cancellation, and the configured bounded replay policy. Missing reply is not proof of an unsent request. |
| Reply accepted with A and B | Resume responsibility for those same two calls. Generating a new reply would risk replacing accepted intent or duplicating A. |
| A committed, but B is unfinished | Reuse A's original receipt, preserve any necessary current-batch context effect, and reconcile B. A later V13 head stays V13. An unknown local effect of B cannot be treated as permission for a blind rerun. |
| Whole batch settled, but graph continuation is absent | Restore the supported deterministic continuation effects and then assemble a new request. That later request may see the current committed version. |

The table explains the already-selected ownership problem. Exact records and transitions remain the third open V1 contract. A crash gap is a boundary to specify, not evidence that every historical run lost work.

<a id="operation-attempts-and-concurrency"></a>
## Operation attempts, concurrency, and useful partial files

**Sources:** EVT-1006, ATT-27. EVT-1023, EVT-1040. EVT-1041, ATT-28. EVT-1068. EVT-1069, ATT-29. EVT-1107.

Do not classify OCR/render as pure solely because the PDF is unchanged. They can allocate outputs and child processes. Safe parallelism requires separate locations, resource limits, and started/completed records. Parallel eligibility and safe replay are different questions. A fixed-version `reopen` need not be banned from parallel execution merely by name. A first version can execute sequentially and expand concurrency only for real independence.

ATT-28's replay matrix proposed automatic read/render retry, CPU/WASM-bounded OCR with reconciliation, serialized edits/export, and stopping uncertain host-user scripts. These are operation-specific proposals, not a universal replay guarantee. The review rejected its instruction to clear incomplete `attempt_dir` before rerendering. Preserve complete useful images and diagnostics, verify identity/parameters, reuse suitable output, and create a new attempt for necessary reruns. A hash proves unchanged file bytes, not that they were rendered from the required source, region, DPI, or engine parameters.

Source render uses PDF identity/page/region/DPI and must work before any draft exists. Output preview uses the selected saved version and view parameters, with renderable candidates supported separately if useful. ATT-29's single version/candidate input requirement for both would obstruct source reading. The review corrected that requirement.

<a id="overflow-and-accounted-compaction"></a>
## Overflow observations and accounted semantic compaction

**Sources:** EVT-1006, ATT-27. EVT-1034, EVT-1040. EVT-1041, ATT-28. EVT-1060, EVT-1068. EVT-1069, ATT-29. EVT-1083, EVT-1107. EVT-1108, ATT-30. EVT-1147, EVT-1166.

ATT-27 proposed returning from a rejected normal request to prepare and avoiding identical-input transport retry. It allowed one or two reduced resends and lowered route capacity using the rejected local token estimate. Rejection of an estimated 80k input proves that request failed under that configuration. It does not prove an 80k model context window.

Record upstream error/count/limit, local estimate/method, and route/model/protocol separately. A provisional safety budget may change for that configuration without changing other routes or inventing a model specification. Automatic tuning is not a prerequisite.

A new step ID does not reset attempts, elapsed time, known usage, overall limits, or the bounded overflow-recovery event. Local evidence projection is deterministic. Semantic handoff production is a real model call. It needs durable identity, frozen input, pre-send accounting, accepted-response capture, and the shared Nexus recovery/cancellation contract. It can be a distinct purpose or node without a second communications stack. The implementation must not hide it in a supposedly free prepare function.

Every actual send, including compaction and any reminder/repack, passes the shared service's final budget, cancellation, and capacity checks. A graph-top gate can be bypassed by restored successors, compaction-success edges, or unfinished-delivery loops. First reuse an already durable accepted result where applicable. Zero remaining budget does not prohibit reading that result. An actual fresh request still requires remaining authority/budget. No success edge may skip a newly received cancellation.

Removing giant evidence alone may leave long user instructions, authoring tool arguments, and ordinary dialogue too large. That is a **hypothetical boundary**, not a proven historical failure. Preserve complete operations, effective requirements, unresolved work, and exact references. Choose a compaction request that itself fits available capacity. Returning an inventory of unloaded content does not by itself solve accumulated history.

<a id="compaction-coverage-and-handoff"></a>
## Compaction coverage, incremental progress, and usable handoff

**Sources:** EVT-1041, ATT-28. EVT-1042, EVT-1060, EVT-1068. EVT-1069, ATT-29. EVT-1070, EVT-1104, EVT-1107. EVT-1108, ATT-30. EVT-1142, EVT-1147. EVT-1148, EVT-1149, EVT-1166.

Each compaction attempt must identify the message IDs/ranges actually supplied. It must also identify the prior handoff/coverage, unprocessed history, and base context revision. Replace only processed ranges. Preserve complete tool-call/result pair boundaries. A cited LangMem summary implementation tracks summarized IDs but may select a tail on oversize input. That is reference behavior, not a complete-handoff guarantee.

After model output, explicitly check format/nonblank/refusal, exact replacement scope, revision validity, and capacity effects before application. Then return to normal-work assessment. Invalid or stale handoff leaves originals intact and is not routed as “no tool calls, therefore deliver.” Structural coverage checks cannot certify preserved meaning. The agent supplies semantic judgment, without a hidden review-model gate.

ATT-29's rolling oldest-prefix summary with a fixed current-head/notes anchor is a reasonable simple option, not the only correct selection. Summarizing a tail can reduce capacity while retaining the earlier prefix. Exact coverage and preservation of unprocessed messages provide the correctness boundary. Distinguish historical events from the current work state in the anchor. The model need not regenerate program-known message IDs, revisions, and anchor versions.

Separate **can apply this compaction** from **can resume normal inference**. Reducing 140k→100k toward an 80k target is useful and can be applied while further compaction remains. Evaluate the entire resulting model view including added anchors/references, not just summary length. A normal request must fit fully assembled input plus output reserve. An intermediate compaction step need not meet that final target.

Original persistent budgets and a no-progress stop bound the process. Two/three rounds are configurable proposals, not universal sufficiency. If application fails and capacity is still excessive, reconsider cause/selection rather than immediately resending the same oversized normal request.

ATT-30 proposed differential handoff containing only old information absent from the current anchor, limited to residual observations, rejected hypotheses, and cross-page clues. It risks loss in this example. The old note says “next-page rows use the prior header,” and the handoff omits that because it is in the anchor. A later note replaces the anchor with “processing page 18.” An anchor reference on disk does not prove that future input assembly includes the information. Such differential summaries require persistent exact-anchor inclusion or consolidation on anchor change.

The final V1 preference is a self-contained handoff sufficient to continue work. It protects effective user requirements, unfinished tasks, saved-result references, important choices, and dependencies. Do not adopt differential summary as a prerequisite.

<a id="authoring-history-and-cache"></a>
## Authoring history projection and cache claims

**Sources:** EVT-1069, ATT-29. EVT-1107. EVT-1108, ATT-30. EVT-1142, EVT-1147, EVT-1166.

Large body text can be present in old `AIMessage.tool_calls` arguments as well as OCR/tool results. Retain original replies, arguments, and results for execution/replay. Project completed historical operations only in the next model's explicitly constructed view. Current pending calls still execute original complete arguments. Preserving a call ID alone does not establish protocol validity for rewritten history on every Nexus route. The proposed “90% reduction” was unmeasured and remains withdrawn.

Saving content does not automatically make immediate withdrawal useful: a just-saved paragraph may be needed to repair two characters next round. Conversely, ATT-30's fixed recent-K verbatim window and requirement that a draft be superseded before withdrawal are too restrictive. A large newest version or unresolved candidate can be represented by precise references for irrelevant portions while current text/context stays active. Use reliable preservation, exact retrieval, relevance, and capacity—not version age or a rigid K—as the decision basis. Batched work-view changes may preserve a stable prefix without per-turn sliding rewrites.

The cache claim also needed correction. A tool call just generated was not in the prior input. Projecting it before first return therefore does not necessarily invalidate that prior prefix. Rewriting previously sent history is a different case.

Route-specific cache benefit and equal-quality cost savings remain unproven. Frozen request snapshots, rather than permanent verbatim windows, guarantee same-request replay consistency. Cache optimization is not a V1 prerequisite.

<a id="malformed-candidate-boundary"></a>
## Malformed calls: raw preservation and optional exact extraction

**Sources:** EVT-1069, ATT-29. EVT-1099, EVT-1107. EVT-1108, ATT-30. EVT-1109, EVT-1127, EVT-1147. EVT-1162, EVT-1166.

There are at least two earlier rejection boundaries: raw JSON decoding and tool-schema validation. A wrapper can preserve decoded but schema-invalid calls delivered to it, while LangChain's `invalid_tool_calls` may bypass ordinary ToolNode dispatch entirely. Nexus reception owns native response/candidate preservation. The common dispatcher owns pre-schema argument preservation. Indexing is a separate success condition. A callback or local storage layer cannot guarantee capture of bytes never received or a write that failed.

ATT-30 proposed “best-effort salvage” of 13 closed blocks before a truncated 14th/15th, calling the early blocks correct and implying only one needs rewriting. The correction accepts an **optional exact extraction** concept:

- Use the same attempt and same tool call.
- Retain raw identity and exact positions.
- Recognize strings/escapes/structural boundaries.
- Independently parse only fully closed original subobjects. Do not add missing quotes/brackets/fields, combine attempts, or treat recovery as authorization to execute the failed original call. A new complete valid operation may reference extracted content after normal validation.

The historical offline example was `{"blocks":[{"id":"b1","text":"A"},{"id":"b2","text":"B","page":`. Pydantic `allow_partial=True` returned b2 without its unfinished field, despite b2 never closing. LangChain's partial parser can add closure characters. Neither output proves exact original completeness. Say “13 syntactically complete subobjects saved; remainder uncertain,” not “13 correct blocks” or “only rewrite block 14”. Later ungenerated blocks may be missing too.

In that example, `{"id":"b1","text":"A"}` is an original closed object. The b2 object has an unfinished `page` value and no closing brace. Returning `{"id":"b2","text":"B"}` would silently drop received but unfinished structure. Optional extraction may retain b1 as an exact addressed fragment, while the complete failed call remains inert.

Even b1 still needs the normal domain and source checks before adoption. Syntactic closure proves neither required metadata nor correct PDF transcription. No extraction feature is needed to reference a candidate whose original arguments were already complete.

A historical record saved 8,419 characters of incomplete arguments during a streaming/service failure. It does not establish output-token truncation as the usual cause. Autonomous smaller saves/append/insert can also reduce giant-submission risk without a fixed page/block cadence. Final scope explicitly removes automatic malformed-block extraction from the V1 prerequisites. Preserve the raw data and establish complete-candidate references first.

<a id="stop-state-and-independent-export"></a>
## Stop states, finite reminders, and independent export

**Sources:** EVT-1041, ATT-28. EVT-1068. EVT-1069, ATT-29. EVT-1083, EVT-1107. EVT-1108, ATT-30. EVT-1147. EVT-1162, EVT-1166.

ATT-28's five terminal labels mixed execution, content, and package verification. Keep those dimensions separate. A canceled run can still have a saved/exported useful draft. “verified” package consistency does not certify source fidelity.

Known necessary scope gaps matter for completion claims, while optional unresolved candidates do not create a universal delivery gate. Resume retains original exhausted budgets and cancellation. Explicit continuation can clear cancellation as defined, but it creates no new allowance by itself.

The exact historical labels were `completed_verified_delivery`, `exported_honest_draft`, `waiting_for_user_clarification`, `stopped_operational_limit`, and `stopped_unreconciled_effect`. Later sketches separated `execution_status`, `content_status`, and `delivery_status`. They did not finalize their enums. `awaiting_user` needs an actual question, potentially retained as `clarification_prompt`. `stopped_incomplete` describes a stall without inventing one. [Stop-label meanings](../design/EXECUTION_AND_DELIVERY.md#stop-label-meanings) explains why package verification, cancellation, remote uncertainty, and local unknown effects cannot be collapsed into the original five mutually exclusive labels.

Unknown remote outcome and unreconciled local effects remain different. When enabled and still within the authorized original bounds, unknown-outcome model replay can continue under the existing limited policy. Do not silently turn it back into mandatory settlement confirmation. Unreconciled local script/OCR effects stop with useful work retained.

A genuine specific user question enters waiting. Technical failure/budget/cancellation uses its own stop reason. The cited 180-second settlement-guard timeout and R1's 188.24-second delay were historical observations, not universal recovery thresholds.

ATT-30 proposed one reminder after a no-tool incomplete reply to handle narration (“next I will OCR”) or premature completion. The proposal stops after a second stall. It remains optional. Explicit cancellation, a concrete question, or an explicit stop reason wins before a reminder.

If used, persist reminder identity so restart cannot repeat it indefinitely. Account for its model request. Report `stopped_incomplete` rather than pretending every stall requires the user to answer.

A recognizable control field/tool can clarify intent, but no new control API is mandated. A reminder reduces one source of false stopping. It cannot guarantee next-turn action. Final scope excludes automatic reminders as a V1 requirement.

Host/CLI/UI-callable specified-version export independent of model quota is retained. Historical `Workspace.export(document, version)` and direct CLI dispatch already supplied a foundation. “zero quota means saved work can never be exported” was false. Export uses time/disk even with zero model tokens. The app may persist export intent/results so normal completion or a later host action can package an existing result.

ATT-29's all-exit deterministic finalizer guarantee was withdrawn: hard termination, shutdown, or cancellation may prevent any graph finalizer running. Cancel first stops new model/tool work. Continuing a large package operation depends on the task policy. An automatically exported newest draft stays explicitly draft and must not replace the selected delivery.

Actual files and ZIP members must match the selected version. A manifest hash alone is insufficient. Directory and ZIP publication are not one universal atomic replacement, and unrelated existing output must not be overwritten. “Every exit automatically packages” is not a V1 prerequisite.

For example, an export published its directory before interruption but did not publish its ZIP. Re-entry first checks that directory's identity and bytes. It preserves the matching useful output and handles the remaining archive effect. It does not erase the directory or claim that both outputs already succeeded. The [publication sequence](../design/EXECUTION_AND_DELIVERY.md#export-publication-sequence) explains the build/member-check/publication boundaries. Final path naming and replay rules remain Q3 choices.

<a id="progress-and-ipc-limits"></a>
## Structured progress and IPC limits

**Sources:** EVT-1041, ATT-28. EVT-1068. EVT-1069, ATT-29. EVT-1083, EVT-1107. EVT-1108, ATT-30.

A structured progress stream was proposed for the eventual Electron/React desktop: capacity/preparation, request/attempt/backoff, streamed-character progress, OCR pages, candidate preservation, and committed versions. Historical asynchronous stdio JSON was a chosen direction with message framing still open and no desktop integration yet. Durable state is authoritative. Events are notifications after commit.

Reconnection starts from a snapshot with sequence/revision. High-frequency updates can coalesce. An OCR page completion means evidence extraction, not page conversion or source acceptance. Version diffs read explicit immutable versions rather than reconstructing body from progress events.

IPC means communication between the desktop process and Python backend. In the stdio proposal, standard input/output pipes carry framed JSON messages. Diagnostics need a distinct channel so a library's printed text cannot corrupt a protocol message. A pipe has finite buffering: if the receiver stops reading, an unbounded producer eventually blocks or needs another declared limit.

Coalescing “OCR reached page 5, then page 6” into the latest progress notification can be safe because committed results remain queryable. Dropping the only durable success receipt is different. These distinctions explain the queue warning without prescribing a transport implementation.

ATT-29 proposed first-line `os.dup2` OS-level stdout redirection plus a ring buffer/watermark to preserve control replies and never block even if UI reading stops. That was narrowed: bounded memory, arbitrary non-droppable controls, producers that never wait, and unlimited new requests cannot all hold during indefinite receiver failure. Keep ordinary progress off the conversion core's critical path.

- Persist important results for request-ID lookup.
- Coalesce notifications.
- Recover via snapshots.
- Reject/limit new work at declared queue/storage limits.

Both protocol and diagnostics pipes need draining. Separate diagnostics from protocol. The discussion withdrew mandatory first-line `dup2`. Exact Windows/MCP/packaging wiring requires the selected implementation context, not a universal recipe.

<a id="canonical-storage-and-schema-counts"></a>
## Canonical storage and nonbinding schema sketches

**Sources:** EVT-1108, ATT-30. EVT-1109, EVT-1147. EVT-1148, EVT-1149, EVT-1162, EVT-1166.

ATT-30 warned of a second-system effect and proposed “four core modules plus six SQLite tables”: branches, document_versions, candidates, version_candidate_links, operations, context_revisions. This remains an illustration, not a complete/final storage specification. It did not settle owners for model steps/frozen requests/accepted replies/attempt totals. Ownership also remained open for live context policy versus historical snapshots, canonical body versus indexes/manifests, export intents, and the three state dimensions. Those responsibilities can use an existing journal/checkpointer/record. No table count is intrinsically sufficient or necessary.

The proposal put full `blocks_json`/`page_map_json` in SQLite while retaining immutable version files. Two independently mutable body authorities would be a conflict. The final preference is immutable version files as canonical body, with SQLite owning identity, registration, manifest hashes, pointers, and operation receipts. Moving the body into SQLite would require a deliberate unified redesign rather than silent duplication. Likewise Nexus communications and export keep clear interfaces even if a chart groups them in one box.

The historical 228-check result supports retaining useful earlier behavior. It is scoped to its old version/affected test set. Old Nursing/Gynecology/JRE/News Writing accepted outputs, R1/R2 injected recovery, and preview verification have limited scope. They do not certify new storage, graph recovery, arbitrary crashes, natural long outages, or installed-product readiness. Reuse capabilities and knowledge selectively. Do not import old statuses, closed validation jobs, or test totals as this repository's requirements or results.

<a id="final-three-contracts"></a>
## Final narrowing: three open V1 contracts

**Controlling sources:** EVT-1148 (user explicitly stopped per-round design expansion), EVT-1149, EVT-1162, EVT-1166. This final scope supersedes earlier attachments describing proposed schemas/diagrams as settled or complete.

The architecture is sufficiently clear as **design responsibilities**, not implementation:

- One Python control layer with agent-chosen reading/OCR/inspection/edit methods.
- A small preferred LangGraph StateGraph.
- A shared Nexus request service for ordinary and compaction calls with persistent budgets/cancellation/frozen native requests.
- Document/evidence services retaining complete sources, candidates, immutable versions, exact reads and edits.
- Separate evidence selection and history compaction.
- Preserved pre-validation arguments and historical operation receipts.
- Consistent specified-version Markdown, JSON, HTML, images, and ZIP with independent export. It does not depend on provider-native compaction, background retrieval, or remote cancellation. Framework, module, and table counts are no longer research questions.

| Open contract | Observed evidence and limits | Recommended tradeoff | Design-finalization condition |
|---|---|---|---|
| Document updates and candidate references | Full-page-map rejection, `本文件→本文作` rewriting regression, and missing direct append/insert/local-map interfaces. This does not prove compaction caused the typo, or malformed-call salvage improves completed delivery. | Use exact references to complete candidates and append/insert/local maps. Merge, then validate the whole result without retransmitting unchanged content. Use immutable canonical files plus SQLite metadata. Preserve malformed raw data. Extraction remains optional for later work. | Specify original identity, updated fields, omitted-field preservation, and commit success. Express page-only correction, insertion, and rejected-candidate reuse without body regeneration. |
| Capacity and handoff | Large inspect/OCR input. Prior checkpoint reduced input and recovered earlier evidence. No general cost or lossless-continuation proof. Draft-history overflow after release and anchor-dependent summary loss are hypothetical boundary cases. | Use configurable route capacity/output reserve. Assess all assembled content. Release saved currently irrelevant content, then older history. Partial projection may include latest and unresolved candidates. Use a self-contained continuation handoff and gradual compaction, preserving originals on failure and stopping explicitly on exhausted allowance. No fixed K, supersession prerequisite, differential-summary prerequisite, or promised 2–3-pass sufficiency. | Define send/release/compact/still-too-large behavior, protect unprocessed history and originals, and use configurable thresholds without universal-percentage research. |
| Persistence, recovery, and stop | Save-and-continue and R1/R2 injected delivery evidence. Tool commit before Graph checkpoint and replay after head advancement are hypotheses requiring bounded rules, not observed universal failures. | Use one active task writer and explicit sole owners for requests, batch progress, versions, and receipts. Freeze same-request recovery input. Complete the whole tool batch before the next input. Replay historical results without extra commit/head rollback/budget reset. Stop unreconciled local effects and wait only on real questions. Support independent saved-version export and draft labels. | State recovery at request-saved, reply-accepted, tool-committed, and Graph-recorded boundaries, with each owner's authority. Do not promise arbitrary old-task or all-hard-crash recovery. |

The final response **recommended** these choices for design finalization. It did not itself turn the three still-open contracts into implemented/verified behavior. Contract consistency and clear responsibility close design. Later implementation assessment uses proportionate offline checks and source-led reading of the specified PDF/complete section. Do not make unbounded preliminary research the gate.

Malformed JSON salvage, cache optimization, general multi-branch management, automatic reminders, and automatic packaging on every exit are reference ideas, not V1 prerequisites. Desktop interface, backend integration, and Windows packaging remained unimplemented in the historical project. They remain real delivery work if the requested result is an installable desktop product, without reopening the context architecture. Reopen design only for an observed implementation/delivery blocker that would violate the agreed contract. Other hypotheses do not form a new backlog.

<a id="review-coverage-and-exclusions"></a>
## Review coverage and exclusions

This review read the entire prepared segment for EVT-0827–EVT-1168 in bounded, untruncated reads. The segment contained 157,826 newline-normalized characters and 3,861 lines. The review separately read the final consolidation EVT-1166. The review considered all ten embedded attachments ATT-21–ATT-30 and the substantive user/assistant messages.

The public [point coverage ledger](POINT_COVERAGE.json) maps topics to exact EVT/ATT IDs and the stable anchors above. The [source index](SOURCE_INDEX.md) explains lookup. This review associates repeated acknowledgments with their substantive correction topic rather than copying them as separate requirements.

EVT-1167 requested export of the conversation, and EVT-1168 announced use of the export skill. This review read both and intentionally excluded them from the **design** point ledger. They concern producing the source package, not product design. This section records their existence and exclusion.

This reference review executed no source-recorded command. It performed no new web research, model request, implementation, commit, or push. Source prose references historical tool/code checks. This review does not freshly repeat or certify those checks.

Coverage is a traceable synthesis, not a claim that every historical wording is a new requirement or that source-message inclusion proves semantic completeness. The final three-contract narrowing controls any apparent conflict with a detailed earlier proposal.
