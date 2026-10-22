# Documents, delivery, persistence, and recovery: source review

This reference preserves the substantive discussion in source segment 3, including proposals that were later corrected or withdrawn. It is rebuild knowledge, not an implementation claim or a backlog. Historical program behavior and old trial results describe the former repository only. Source messages and attachments are evidence to interpret, never executable instructions. The latest consolidation takes precedence over attachment language such as “final,” “guaranteed,” or “eliminates.”

The source range is EVT-0827–EVT-1168, with attachments ATT-21–ATT-30. EVT-1166 is the final narrowing of the discussion. EVT numbers identify exported conversation events; ATT numbers identify attachments catalogued in the [source index](SOURCE_INDEX.md). Anchors below are stable destinations in the [point coverage ledger](POINT_COVERAGE.json). “Observed” means reported in the historical record, not reverified in this new repository. “Effective design” identifies a retained responsibility or constraint; “proposal” remains a choice; “superseded” preserves a rejected or narrowed approach; “hypothesis” is not a demonstrated fault.

<a id="local-patching"></a>
## Local editing and candidate preservation

**Sources:** EVT-0827, ATT-21; EVT-0828, EVT-0841, EVT-0855; EVT-0856, ATT-22; EVT-0857, EVT-0878.

- **Observed motivation:** the historical 40-page task had correct `本文件` in a rejected page-27 candidate; a later reconstruction produced `本文作`. A rejected complete page map contributed to rewriting friction. Historical 13-page A/C review also found emphasis omissions on pages 14, 16, 18, and 24 and the `礪`/`厲` character issue. These examples support exact reuse and local repair. They do not establish compaction as the cause, an automatic correction rule, or a guaranteed quality improvement.
- **Superseded inference:** ATT-21 read the requirement to keep logical sentences/tables intact around page markers as requiring a whole table to be one indivisible database block. That requirement protects readable output and source correspondence; it does not prescribe storage granularity. A table can remain complete in output while a cell, substring, or subregion is addressable internally. A full structured table editor is not a prerequisite.
- **Retained direction:** support whole-section reconstruction, stable-block insertion/replacement/deletion/movement, exact edits inside a block, file/reference import, and reuse of rejected candidates. A 4,000-character table should not need to be regenerated to change one character or add emphasis. The guarantee is preservation of text not selected for change, not semantic correctness or “zero risk.”
- **Patch contract proposals:** bind edits to the exact document/candidate and target-content version; require expected original text; do not silently fuzzy-match, normalize glyphs, or convert traditional/simplified Chinese. Validate the complete patch set in a working copy and commit atomically; retain rejected work and reasons. Editing a candidate produces a traceable successor and preserves the original. RFC 6902's `test` and explicit sequence were cited as design inspiration, not an existing string-patch implementation.
- **ATT-21 example caveat:** `<td>厲行節約</td>` → `<td><strong>礪行節約</strong></td>` with `expected_matches: 1` demonstrates mechanics only. A unique match does not prove semantic location or authorize the glyph change. Every textual correction must be supported by the PDF.
- **ATT-22 refinement:** repeated cells (`0`, empty cells, `是`, `12.4`) can make whole-block exact search ambiguous. An optional raw-line range plus expected text, within-range occurrence/position, or a tool-generated location reference can reduce retransmission. Line numbers are not sufficient for repeated items on one line or a one-line HTML table. Visual wrapping differs from raw newlines; JavaScript UTF-16 indexes and backend character indexes need an explicit common convention.
- **Retained batch option:** align all nonoverlapping patches to the same unchanged base snapshot, validate them first, then replace from the greatest offset backward. This prevents one edit shifting another's coordinates. Explicit sequential semantics are an alternative only when clearly defined; accidental anchor creation/destruction must not be implicit. Whole-block replacement and file import remain available.
- **Evidence limit:** ATT-22's claim that this removes all eight historical tool errors is unsupported. The eight included OCR timeout-parameter and post-success result-selection failures, beyond editing and page-map friction.

<a id="source-output-comparison"></a>
## Source, output, and visual comparison

**Sources:** EVT-0827, ATT-21; EVT-0841, EVT-0855; EVT-0856, ATT-22; EVT-0878.

- **Retained direction:** make the saved output and relevant original pixels easy to inspect together, with previews bound to a specific document version. Optional paired images, independent crops, or an explicitly chosen montage can reduce navigation. Labels and dividers belong outside source pixels; retain originals, coordinates, and surrounding context. This can help distinguish source interpretation, Markdown emphasis, and rendered-output errors.
- **Hypotheses, not diagnoses:** ATT-21 attributed old emphasis errors to cross-turn visual memory; ATT-22 substituted visual downsampling as the true bottleneck and illustrated 24×24 glyphs becoming 12×12 after joining pages. Neither causal claim was established by the recorded task. Comparison does not make every mistake immediately visible, and two native image items do not guarantee full model-side resolution; route preprocessing can still resize them. The cited Qwen processor illustrates that qualification, not a fresh benchmark.
- **Source precision:** the old `Block` had `id`, `pages`, and `markdown`, with no bbox. A block ID plus page is not a precise crop. Use a known region when available, a page or agent-selected region when only coarse location exists, and multiple references for multi-page/multi-region content. Do not require a bbox for every word or cell. Desktop synchronized navigation means jumping to related source content, not aligning PDF coordinates row-by-row with reflowed Markdown.
- **Reference proposal:** optional `source_refs` can reuse inspect/OCR positions without hand-entered coordinates. A bare `p14_b03` is not durable: another OCR engine, crop, or recomputation may produce a different block with that name. Bind the reference to immutable evidence plus its internal block/field location; derive PDF identity, page, coordinate system, and render parameters from that evidence. Historical OCR already distinguished `bbox_pixels` and `bbox_pdf`.
- **Review scope:** a review belongs to its exact output version. A later edit cannot inherit the statement that the current version has been checked without considering the changed content. This is traceability, not a mandatory review ritual.
- **Computation-cache proposal:** ATT-21 also proposed an index by source hash, tool/engine version, language-data hash, normalized parameters, and page/region for independent page render/OCR work. Overlapping requests could reuse already computed units, while `force_recompute` allows a fresh result. Computation indexing does not require storing every page as a separate file. This is a reusable performance idea, not a prerequisite or proof of savings; [the earlier cache discussion](02-context-state-and-evidence.md#cache-and-prefix) retains its broader qualifications.

<a id="capacity-visibility-and-access"></a>
## Capacity visibility and unrestricted evidence access

**Sources:** EVT-0827, ATT-21; EVT-0853, EVT-0855; EVT-0856, ATT-22; EVT-0878.

- **Historical figures:** the 40-page record carried 1,865,411 OCR characters from eight full page objects; the 13-page C request read nine objects totaling 1,976,466 characters and the next input reached 796,420 tokens. The 40-page run was configured for 3,600 seconds/100 rounds and ended after HTTP 408 and the 57th request timing out. These observations do not prove OCR weight, rereading, or tool friction caused the timeout.
- **Corrected evidence misuse:** P ran with selective/checkpoint disabled. Its non-use cannot establish failure of natural adoption, lack of capacity awareness, or need for a particular mechanism. Small 9-page B/C jobs' non-use likewise does not by itself explain the cause. ATT-21's claim that agents did not release evidence because they could not see capacity is a hypothesis.
- **Retained capacity information:** distinguish original evidence size, selected content's actual contribution to this assembled input (including duplicates), and remaining capacity under the configured route and output reserve. An OCR original may be huge while a selected `text` field is small; repeated images must count as repeated input. Include system content, tool definitions, ordinary dialogue, work state, and images. Track request bytes separately from tokens; unknown limits remain unknown and estimates are labeled.
- **Placement:** compute the global footprint at the built-in input-assembly boundary, tied to `input_view_id`. Individual tools can expose their own sizes. A permanent heavy-item leaderboard in every tool result is optional and can itself add history. ATT-21's 60–70% thresholds and 200,000-token denominator were illustrative/configurable, not universal limits or quality boundaries. `drafted` does not imply evidence is dispensable.
- **Explicit intent:** a save/update may optionally carry `context_delta` such as `release_when_needed` and `pin`; omitted fields do not silently release unpinned evidence. Ordinary user revisions, unsaved reasoning, rationale, and unresolved questions need context protection alongside structured evidence. The app handles capacity; the agent judges relevance.
- **MCP boundary:** the server can report its own results and offer first-call field/range/image selection, exact rereading, and complete originals. It cannot remove content already in an external host's dialogue or infer that host's global capacity without host information. Conversely, the host can manage its own history; content is not necessarily “welded forever.” A shared `DocumentService` cannot promise the built-in runtime's global footprint for every interface.
- **Superseded restriction:** ATT-22 proposed a compulsory compact/default initial result and described it as MCP's only defense. Preserve the caller's ability to request full/raw/field/range/native-image content on the first call, without a summary gate or fixed text-first preset. Changing defaults is a separate product choice. `text`, layout, words, and font/position data may overlap but are not interchangeable; deduplication must not presume one representation always suffices.

<a id="scope-map-and-completeness"></a>
## Task scope, page facts, and actual completeness

**Sources:** EVT-0827, ATT-21; EVT-0855; EVT-0856, ATT-22; EVT-0872, EVT-0878.

- **Retained separation:** document/evidence services own sources, versions, assets, candidates, and precise modification; task state owns effective requirements, scope, progress, issues, and their associated versions; execution state owns dialogue, pending actions, context policy, operation/request records. These responsibilities may share SQLite and one process.
- **Historical scope example:** converting pages 1–10 today does not make pages 11–173 permanently outside all future tasks. A historical version's `outside_scope` designation can correctly describe that task; the error is blindly inheriting it into a later full-book task.
- **Retained update direction:** accept partial/sparse page changes and merge them against the base. Internal sparse storage and full output mapping are compatible: derive the complete mapping from source page count, task scope, and known facts. Do not force the model to retransmit 173 entries to correct one page, but do not remove the full source-correspondence outcome.
- **Superseded completion test:** ATT-22 proposed only `converted`, `source_blank_or_omitted`, and `drafting`, then completion when every target page is converted or blank/omitted. One paragraph on a page does not account for its tables, footnotes, or captions. The Breasts case requested one complete portion of page 12 and excluded adjacent content, so `target_pages=[12]` alone cannot express the scope. A section, figure, table, or other bounded content may define the task.
- **Required distinctions:** source facts (physical and printed pages, regions, evidence), task scope, output-to-source relationships, and progress/review status remain separate. `converted` can report a relation but cannot certify quality. Confirmed blank source and a decision to omit decoration are different facts. Keep `none` and `unknown` printed-page states distinct. Complete source mapping does not imply every page must have body content.

<a id="continuity-and-state-ownership"></a>
## Continuity, state ownership, and replay identity

**Sources:** EVT-0827, ATT-21; EVT-0828, EVT-0841, EVT-0853, EVT-0855; EVT-0856, ATT-22; EVT-0857, EVT-0872, EVT-0878.

- **Retained continuity view:** common saved document/candidate/evidence/work data can support context handoff, optional chapter delegation, and reopening tomorrow. A “Document Continuity Snapshot” is a selected, auditable handoff view, not one mechanism that replaces all three lifecycles.
- **Different lifecycles:** same-run context transition needs active requirements, progress, issues, and input selection; a child/new task needs explicit scope, inherited information, outputs, and edit authority; restoring the same execution additionally needs checkpoint, pending steps, receipts, original budgets, and reconciliation of outside changes. New tasks must not inherit old pending tool calls; recovery must not overlook unprocessed results. Task-specific notes/issues do not all belong to document-global state.
- **Superseded settlement design:** ATT-21 proposed a SQLite settlement key from accepted tool-batch identity instead of `hash(current_policy_rev, proposal_ids)`, which would turn policy 7→8 into a second 8→9 settlement on replay. The stable batch idea fixes that identity problem, but its instruction to force `active_policy_rev` back to the receipt's policy 8 would undo a legitimate later policy 9. Replayed prior effects retain the advanced state; an incomplete original transition can use its receipt only under compatible parent state; incompatible branches/modifications require a conflict.
- **Later simplification:** small context policy belongs in Graph State: selections, release/pin policy, notes or references, compaction boundary, and settled batches. Remove an unnecessarily external policy-version/activation mechanism for the single built-in executor. Tools report intents; one `before_model` settlement updates policy and processed batch once; request assembly applies it. Reducers do not automatically resolve conflicting `pin`/`release` intents or two parallel whole-policy replacements.
- **Corrected causal claim:** two physical databases did not cause the policy rollback; interpreting an old result as present state did. The same mistake can happen in one database. Conversely, Graph/checkpoint rollback cannot undo sent requests, spent budget, committed document versions, or completed external effects. Durable service-owned request records and operation receipts remain necessary, even if physically colocated.
- **ID distinctions:** `(thread_id, checkpoint_ns, tool_call_id)` plus argument hash can collide across accepted parent replies. ATT-22's proposed `parent_model_request_id == input_view_id` also conflated roles: a view can be resent, a turn can use several views, and only an accepted response generates executable calls. Use stable application operation identity with accepted parent response and branch relationship; separately relate logical request, physical attempt, and input view. Same operation recovery reuses identity; a new accepted batch gets new identity.

<a id="transport-salvage-and-slices"></a>
## Transport, process inspection, and delivery increments

**Sources:** EVT-0827, ATT-21; EVT-0855; EVT-0856, ATT-22; EVT-0878.

- **Observed legacy coupling:** `Provider.pending_images`/`flush_images` and `Agent.model_round` carried mutable request state. Merely wrapping the old instance as a stateless model is unsafe. The proposal is request-local encoding: Chat Completions pairs tool-result images with the corresponding following native image message; Responses encodes them in the corresponding function output and preserves native reasoning behavior. Attempt-local SSE assembly and diagnostic filtering remain relevant knowledge. Exact framework hooks and model class names are proposals, not implemented interfaces.
- **Budget distinction:** one durable request ledger is useful, but does not make transport retries, local preflight reconstruction, and sent capacity-recovery attempts the same policy. With `automatic_retries=0`, defining all sends as `1 + automatic_retries` leaves no post-rejection repack send. Local preflight has no HTTP attempt but uses time; every actual send counts against common totals. ATT-22's one immediate overflow resend is a proposal, not an adopted default. Only recognized capacity errors and a view that improves that specific limit justify repacking; valid requirements/work must survive. HTTP 413 may carry `Retry-After`, so “always immediately/no wait” was corrected.
- **Historical retry illustration:** ATT-22 contrasted default zero retries with a trial value of two and 60–120-second backoff, separating listed 500/502/503/504, timeout, and interrupted-stream cases from recognized capacity rejection. These values/classifications describe that proposal and earlier environment; they are not inherited new-repository defaults or a newly authorized trial.
- **Process inspection proposal:** distinguish read-only `inspect_attempt`, explicit `terminate_attempt`, and bounded `salvage_attempt`; inspecting/salvaging must not silently kill a running child. Windows Job Objects, `FILE_SHARE_READ` snapshots, explicit `terminate_running_process=True`, and complete decoding were proposed mechanics. Read/write stability and conflicts must be reported; rescued partial output is not whole-task completion. These ideas do not create a required V1 salvage subsystem.
- **Construction priority:** ATT-21's P0 document editing/visual comparison, P1 context continuity, P2 transport/process services, and optional P3 optical hints/chapter episodes describe product value, not a rigid layer-by-layer build order. Waiting for every lower layer before connecting Nexus postpones integration discoveries.
- **Retained increment principle:** connect a small useful source→save→reopen→export flow using shared tools and the actually used Nexus route, preserve candidates from the first increment, then add precision and context continuity where needed. ATT-22's first slice bundled new framework, both protocols, persistent retries, sparse document model, full chapter, and interruption recovery and was judged too large. Other product protocols remain capabilities to integrate, not grounds to expand the first slice. Candidate loss on first validation failure must not be deferred to a second slice.
- **No automatic work authorization:** these reviews explicitly described read-only analysis, with no project edits, tests, or Nexus model calls. Vertical slices are retained reasoning about implementation order, not a queued execution request in this reference.

<a id="unaltered-text-and-locators"></a>
## Raw text fidelity and edit views

**Sources:** EVT-0880, ATT-23; EVT-0881, EVT-0894, EVT-0914; EVT-0915, ATT-24; EVT-0942.

ATT-23 proposed banning bare offsets and normalizing every ingested block to LF plus NFC, with deterministic HTML table pretty-printing around rows/cells. Its rationale was legitimate: supplementary-plane characters count differently in Python code points and JavaScript UTF-16 units; CRLF/LF and a one-line HTML table complicate line-based addressing. Its remedy was rejected. The historical local Python check showed `U+2F800 → NFC → U+4E3D`; that proves NFC is not universally lossless for source character distinctions, not that every normalization visibly changes text or that the PDF used that code point. Inserting HTML newlines creates text nodes and may alter whitespace, copying, or parsing.

Preserve the original candidate; an explicit LF version-storage contract remains possible. Pretty-printed lines, table grids, normalized search, and line numbers should be read/edit views with mappings back to actual stored content. Offsets may be used if their counting convention and programmatic conversion are defined; the model need not hand-count them. A version-bound `cell_ref` can be a convenience over the same patch mechanism. `row=5,col=3` alone is ambiguous with rowspan/colspan: distinguish visual grid positions from stored cells. Neither a mandatory table AST nor permanent removal of cell references follows.

ATT-24 proposed only `patch_block(..., expected_old_text, new_text, occurrence=1)` plus a read-only cell grid, alleging cell references require a separate byte-splicing AST engine. The correction retained generic patches first and optional cell locators, while rejecting silent first-occurrence selection: require uniqueness unless the caller explicitly selects a returned location. The proposed “95% of errors” coverage has no measured support. Larger or multiple patches can handle structural changes; a cell convenience need not express every edit.

<a id="preserve-before-validation"></a>
## Preserve received content before validation

**Sources:** EVT-0880, ATT-23; EVT-0894, EVT-0914; EVT-0915, ATT-24; EVT-0916, EVT-0942.

Saving candidates only inside `DocumentService.save()` misses input rejected earlier by a framework's schema validation. The historical `AgentTools.call()` already saved full tool arguments before validation/execution. Retain that protection across built-in, MCP, and CLI entry points: preserve fully received writing arguments, validate, create/update a usable draft, then commit a document version. Return a stable reuse reference and precise errors so metadata can be corrected without rewriting body text. Raw records can hold invalid arguments; valid drafts and published versions still satisfy their own contracts.

The reviewed `wrap_tool_call` position ran before tool validation, but its `args` were an already-parsed dictionary, not raw response bytes. The adapter separately preserves the complete native reply. A truncated reply may be diagnostic evidence; it does not authorize executing a partial tool call. If a write committed and later response-field selection failed, retain the successful receipt and distinguish that from an unperformed write.

ATT-24 proposed `write_blocks` with optional page maps and a later `publish_version` gate. Saving incomplete metadata is useful, but export cannot be gated on completion: a draft must be previewable, snapshotted, and exportable with gaps explicitly identified. A single edit can atomically include body plus optional page changes; separating validation responsibilities does not force two model calls.

<a id="draft-export-and-claims"></a>
## Draft usability, completion claims, and revisable observations

**Sources:** EVT-0880, ATT-23; EVT-0910, EVT-0914; EVT-0915, ATT-24; EVT-0931, EVT-0942.

Saving a draft preserves changes and coherent version/block relationships, with missing facts marked. Export guarantees one-version artifacts and honest draft/gap labels. Declaring completion concerns the user's full requested scope and absence of known material omissions/errors. Technical validation of structure/assets/references cannot establish semantic completeness.

ATT-23 proposed `converted_full_page`, `converted_partial_scope`, `source_visibly_blank`, `omitted_non_content`, `unprocessed/drafting`, plus scope-derived `outside_task_scope`. These can represent claims and observations, not wholly objective completion facts. A natural-language subpage boundary helps express “Breasts and Figure 4-13, physical page 12/printed page 68”; it cannot prove all figure labels or content are present. Completion must bind both scope revision and document version. Completing that subsection under task A does not complete task B's expanded full page. Keep useful prior work and identify added/uncertain scope without automatically requiring every old part to be rereviewed.

ATT-24's separation into `source_page_inventory`, `block_provenance`, and `task_scope_and_claims` was retained as a responsibility model, not a prescribed three-table schema. Stable source identity/physical order differs from revisable observations such as a read printed label or inferred provenance. “Printed page 68 never becomes invalid” was corrected: the PDF may be unchanged while the observation was wrong. Preserve earlier observations in their historical versions and retain immutable evidence references alongside page numbers/notes. `none` and `unknown` remain distinct. A copyright page may contain author, edition, ISBN, or other requested content; do not classify it as omittable by default.

The historical 191,662-character first inspect belonged to a task that passed source acceptance: it proves input weight, not task failure. The final 13-page A emphasis defects were pages 16/18/24; C also included page 14 and `礪→厲`. ATT-24's broad attribution of failures to interface friction overstated the evidence.

<a id="batch-order-and-recovery"></a>
## Deterministic intent settlement and actual tool order

**Sources:** EVT-0880, ATT-23; EVT-0914; EVT-0915, ATT-24; EVT-0916, EVT-0931, EVT-0942.

Settlement must use trusted accepted-parent tool-call declaration order, not completion timing. Concurrent I/O can finish in a different order after replay. `before_model` can persist compact policy/processed-batch changes, while request assembly hydrates selected content without copying giant evidence back into checkpoints. Deterministic intent order does not order actual file effects: parallel revise/export or two edits based on V still need version/dependency handling.

The reviewed `create_agent` implementation dispatched calls through parallel `Send("tools", ...)`; substituting it for the former controller's sequential loop does not preserve order automatically. ATT-24's “30-line declaration-order lock” was rejected as a recovery guarantee. If A completed before a crash and the framework restores its pending write without reexecuting A, B may wait forever for an in-memory signal. A read of `latest` before a write can also race a later write even when each writer waits for earlier writers.

Use explicit versions for reopen/preview/export, base revisions and atomic service commits for edits, and durable receipts for recovery. When a batch needs ordering, the executor that owns the complete batch should order it. A small sequential LangGraph tool node is acceptable and does not impose a PDF conversion recipe. Independent reads may parallelize under their actual resource contract; OCR/render can create files, assets, and child processes and are not universally side-effect-free. Do not build a hidden general scheduler merely to keep `create_agent`'s form.

<a id="preview-semantics"></a>
## Whole-document rendering and honest preview locations

**Sources:** EVT-0880, ATT-23; EVT-0914; EVT-0915, ATT-24; EVT-0931, EVT-0942.

ATT-23 proposed `inspect_block_pair` rendering 300–400 DPI source crops and an output `#tbl_02` crop; its guarantee that a 900×350 image avoids all route resizing was withdrawn. Higher DPI cannot recreate missing scan detail. One output block can derive from several source regions, and reflowed output has different geometry. Historical preview rendering had no established block→DOM mapping.

ATT-24 then proposed independently rendering each Markdown block into `<div data-block-id=...>`, allowing the attribute through sanitization, and using Playwright locators for “100% exact” screenshots. The historical in-memory parser example refuted independence: block A `See [source][r].` plus block B `[r]: https://example.com` resolves when parsed together but not when separately rendered. Preserve whole-document CommonMark semantics. Parser source-line/token locations may support app-generated DOM anchors and one-block-to-many-DOM-region mappings; they are a basis for implementation, not a finished mapping engine.

Locator screenshots can include occlusion or only currently visible contents of a scroll container. Report actual crop coverage, dimensions, location precision, and version; do not equate a locator with complete capture. Independent native images are useful; optional montages remain valid. No fixed crop/DPI/visual-check stage is imposed.

<a id="adapter-integration-boundaries"></a>
## Model integration and the accepted-reply gap

**Sources:** EVT-0880, ATT-23; EVT-0910, EVT-0914; EVT-0915, ATT-24; EVT-0940, EVT-0942.

ATT-23's proposed under-150-line `NexusHttpChatModel` supposedly inheriting 100% of 228 historical checks and R1/R2 protection was explicitly retracted. The retry ledger lived in the old controller; image pairing lived in mutable provider state; those tests were against specific old modules, not a new adapter. Tool binding, async calls, message conversion, and durable identities still need integration. `create_agent` needs executable `AIMessage.tool_calls`; arbitrarily replacing all current messages with references breaks dispatch unless explicitly resolved.

Retain the actual Chat Completions sequence: complete all paired tool results, then append that batch's paired native-image user message. Responses uses its corresponding function outputs. A model instance may keep configuration, pools, and service references; avoiding request-residual mutable image queues is the meaningful requirement, not literal 100% statelessness.

The selection boundary is `complete artifact → current context selection → selected image resolution → protocol encoding`. Scanning every historical artifact to recreate images would undo release decisions. Artifacts do not automatically become model input.

If a complete accepted reply is durable but its Graph checkpoint is not, recovery must first look up that reply by a durable logical step identity before sending another request. Merely storing `accepted_reply_id` in message metadata covers only the already-checkpointed case. `(run_id, step_index)` is a possible app-owned identity with explicitly defined recovery/branch semantics, not an assumption about a framework invocation ID.

<a id="useful-slice-acceptance"></a>
## Useful delivery increments and their limits

**Sources:** EVT-0880, ATT-23; EVT-0881, EVT-0914; EVT-0915, ATT-24; EVT-0942.

The proposed first-slice checks concerned observable work: native text/tools/images round-trip through Nexus; correct body survives an invalid-metadata save; save/reopen/read/export identify one version; resume recognizes committed effects and unfinished work. Use a complete useful subsection, not an arbitrary 1–2-page cut that severs a figure/table. These were future verification directions and did not authorize new Nexus trials.

ATT-24's first slice again accumulated full editing, both streaming protocols, three data categories, DOM mapping, and concurrency coordination; the review narrowed it to content that can be saved, repaired, taken away, and resumed. Fine visual conveniences and context continuation remain distinct capabilities. Lightweight references plus pin/release alone do not finish context management: ordinary dialogue, later user corrections, unresolved dependencies, and a single oversize evidence selection still need explicit behavior. Framework names and feature counts cannot substitute for that outcome.

<a id="small-graph-and-step-identity"></a>
## A small graph, durable step identity, and frozen requests

**Sources:** EVT-0943, ATT-25; EVT-0944, EVT-0957, EVT-0968; EVT-0969, ATT-26; EVT-0970, EVT-0982, EVT-1005.

ATT-25 proposed three nodes (`model_step`, `tool_batch_step`, `settle_step`) plus a common dispatcher. The retained reason to prefer a small `StateGraph` is direct ownership of complete tool batches, ordering, recovery, and input assembly. Pre-validation capture and reply reconciliation are needed under any runtime. `create_agent` also supplies middleware, tools, and structured-output behavior; declining it does not make all integration work disappear. A full `BaseChatModel` wrapper is optional if the model node can call the extracted Nexus request service directly. Node counts are not an architectural requirement; a prepare boundary can be useful without adding a model call.

ATT-25's stable key `(job_id, checkpoint_ns, model_turn_seq)` handles one straight-line restart but not all new decisions. `checkpoint_ns` is not branch identity. A branch can retain the same tuple; a no-tool answer can reach END without incrementing the counter, then collide with later user input. Each new intended model judgment needs a durably saved new `model_step_id`; restoring an already-prepared decision retains its ID/input. New input, deliberate regeneration, and branch rejudgment use a new ID even when their prompts/fingerprints are identical. Same ID with changed input is inconsistency, not license to overwrite the request.

ATT-26 proposed four nodes: `prepare_step → model_step → tool_batch_step → prepare_step`, with `delivery_check_step` for a no-tool reply. It assumed every recovery/branch passes through prepare and every new branch's fingerprint differs. Both assumptions were corrected: checkpoint successors and `update_state(as_node=...)` can resume after prepare, and regeneration can reuse identical content with different intent. Define application entry rules explicitly. Graph `durability="sync"` can ensure the prior checkpoint is written before the next step; it cannot guarantee exactly-once remote generation.

Prepare freezes route/model configuration, generation parameters, tool schemas, and actually selected content, not merely text messages or evidence filenames. Save the full request in immutable files and small IDs/references/fingerprint plus policy in Graph state. Do not resolve `latest` or swap images after prepare. Before sending, durable attempt consumption must already be recorded. No accepted reply does not mean no request was sent; inspect attempt status and original remaining budgets before bounded recovery. Only a complete durable reply for the same logical request is directly reusable.

<a id="commit-and-receipt-boundary"></a>
## A committed version and its operation receipt

**Sources:** EVT-0943, ATT-25; EVT-0968; EVT-0969, ATT-26; EVT-0982, EVT-1005.

Writing a success receipt only after a file change leaves a crash gap: committed document → crash → no receipt → duplicate operation. Bind operation ID and input fingerprint atomically to the commit, or embed enough identity in the committed result to recover it. The historical `publication_operation` field demonstrates that principle; it is not proof of the new architecture.

ATT-26's “commit-as-receipt” proposed embedding identity in `document.json` and evidence metadata, using atomic replacement/short transactions, and eliminating a separate receipt/event store. The useful simplification does not make folder existence equivalent to save completion. The former code first moved the version folder, then updated `current.json`; a crash can leave prepared files without an advanced working head. If save promises both version registration and head advance, stage immutable files first, then atomically commit registration, pointer, and operation identity in a short transaction. Alternatively expose those two operations separately. Retain useful prepared results.

Successful version metadata does not replace “started, outcome unknown” records for scripts, OCR, or model requests. No receipt is not proof an effect never happened. Recovered tools must restore results and required state/context intents, not just display text. These responsibilities need finite execution records, not a general event-sourcing system. Batch-level graph nodes also do not automatically checkpoint each nested tool.

<a id="cross-interface-capture"></a>
## The cross-interface capture boundary

**Sources:** EVT-0943, ATT-25; EVT-0968; EVT-0969, ATT-26; EVT-0999, EVT-1005.

A common dispatcher is a good ownership boundary but does not prove every interface reaches it before validation. The historical installed MCP SDK validated registered-tool arguments before invoking the function, so placing capture inside that function remained too late. ATT-26 proposed a permissive transport schema plus strict domain schema, claiming this guarantees entry. Wrong container types/missing required values can still fail, and weakening schemas removes useful guidance.

The historical review then found installed MCP SDK 2.3.0's `Extension.intercept_tool_call`, preceding tool validation for an accepted `tools/call` request. It offered a way to retain clear tool schemas and perform shared capture first. Preserve the principle, not an unverified assumption about another SDK version: each entry must save app-received, successfully decoded tool-call arguments before domain validation. Draft metadata that is truly optional should be optional in its schema. A server cannot save content rejected by an external client before transmission. No 100% capture guarantee extends to bytes never received or undecodable protocol messages.

<a id="reading-versus-diagnostic-view"></a>
## Actual reading and expanded diagnostic views

**Sources:** EVT-0943, ATT-25; EVT-0957, EVT-0968; EVT-0969, ATT-26; EVT-1005.

ATT-25 proposed a roughly 15-line parser rule assigning `data-block-id` from `token.map`, claiming complete cross-block links/footnotes and raw HTML support. Historical parser checks showed default `html_block` rendering returns raw `token.content` and ignores `token.attrSet`; HTML needs explicit handling. Token ranges may cross content-block boundaries, requiring many-to-many correspondence. Whole-document parsing preserves supported cross-block semantics but does not enable a footnote extension absent from the parser configuration. The line-count and 100% claims were withdrawn.

ATT-25 also proposed no fixed heights/overflow/sticky elements, a viewport widened to `scrollWidth`, and union-bound screenshots or segmentation. These can support an expanded diagnostic view but may hide real reading defects under normal CSS/viewport. Keep actual-reading and expanded/zoomed views explicit and version-bound; record changed conditions. Disjoint DOM regions may be clearer than a large union box full of whitespace. This remains a convenience direction, not proof it fixes old glyph/emphasis errors.

<a id="capacity-in-first-usable-runtime"></a>
## Capacity belongs in the first usable runtime

**Sources:** EVT-0943, ATT-25; EVT-0968; EVT-0969, ATT-26; EVT-0970, EVT-1005.

ATT-25 postponed context management until a third stage for 40-page-plus documents. The review corrected the page-count premise: a single-page inspect can contain 191,662 characters. Basic capacity behavior belongs with useful runtime work: save full evidence separately, state what is selected/not sent, estimate actual input, retain native/full/precise access, and preserve results on overflow instead of silently truncating.

ATT-26 moved this earlier, proposing a loaded/unloaded-range inventory on oversize results. That helps a large new result but not history already too full to fit the inventory or another answer. Reserve room before exhaustion for tool schemas, image estimates, normal output, and compaction itself. Distinguish large-result handling from accumulated-history handling. Capacity estimates across routes remain fallible; a “never overflows” guarantee was rejected. Basic history compaction/recovery belongs in the first usable long-task version, without waiting for advanced screenshot/table helpers. Full first-call results remain available within capacity; inventories are not universal gates.

The adapter may stream selected image bytes from disk; a categorical disk-access prohibition is unnecessary. Context policy chooses evidence, the input assembler resolves that choice, and encoding must obey the frozen selection without resurrecting released artifacts. The Nexus service can be an in-process module in one Python backend.

<a id="selected-version-delivery"></a>
## Select a delivery version and distinguish stopping from delivery

**Sources:** EVT-0943, ATT-25; EVT-0968; EVT-0969, ATT-26; EVT-0999, EVT-1005.

A no-tool model answer can be a question, blocker report, or early stop, not completed delivery. Check the selected saved version, corresponding export, declared scope, and draft/completion state. Structural validity, agent completion claim, and source-review outcome remain different information; `complete_accepted` cannot be inferred from a valid schema and does not mandate routine human approval.

ATT-26's automatic export of the newest version was narrowed to explicit delivery intent `(version_id, scope_rev)`. Example: V10 is good, V11 is a trial table edit, and the agent chooses V10. Automatically shipping latest V11 overrides that choice. A known selected version can be packaged by the app without spending another model turn or routinely asking the user. Preserve consistent Markdown/JSON/HTML/assets/ZIP for that selected version.

An exported version and abandoned experimental candidate can coexist. Only candidates still belonging to unfinished current work merit follow-up; their mere existence must not trigger rewriting. A real request for user clarification enters waiting-input state rather than looping through prepare without new information. Practical first-version editing includes append/insert/delete/reorder, local page/provenance updates, and candidate-body reuse with repaired metadata; substring patching alone is insufficient.

<a id="incremental-edit-and-reference-contract"></a>
## Incremental editing and exact candidate references

**Sources:** EVT-1006, ATT-27; EVT-1007, EVT-1040; EVT-1041, ATT-28; EVT-1042, EVT-1060, EVT-1068; EVT-1069, ATT-29; EVT-1107; EVT-1108, ATT-30; EVT-1147, EVT-1166.

ATT-27 proposed `edit_document(base_version, reuse_candidate_ref, block_ops, page_map_updates, provenance_updates, delivery_selection)` to avoid resending unchanged body or the full page map. Its operations were append, before/after insert, replace, delete, reorder/move, and exact patch. Multiple block operations should act in a defined sequence on one working copy, then commit one version only after the merged result validates. Define whether later locators refer to earlier operation results; inner patches sharing a base snapshot retain their explicit separate semantics. Tool count alone neither minimizes schema tokens nor cognitive load.

Candidate repair cannot silently inherit/replace nested fields or arrays. Example: a candidate contains updates for pages 12 and 13; correcting page 12 must not silently erase page 13. Define omitted-field preservation, replacement, per-page upsert, and nested-field handling. Editing a candidate produces a new effective-argument snapshot and operation ID with parentage, leaving the original intact. Reusing an old operation ID with changed input violates replay identity. Replacing the base version also requires rechecking delete/replace/patch applicability.

ATT-28 proposed avoiding implicit parameter inheritance by importing `block_ops_from_candidate`, explicitly resubmitting small page changes, and exposing `save_draft`, `edit_document`, and `select_delivery`. This is a possible clearer tool surface, not a mandatory count. Per-page upsert needs a defined `pdf_page` key; unknown printed label, uncertain scope, and unprocessed work remain distinct. Missing information must not automatically become `outside_scope`.

The correction separated **content reuse** from **operation reuse**. `block_ops` can include deletion, reordering, or context-sensitive patches; adopting a correct paragraph must not force those old effects. A failed `save_draft` may contain `blocks` rather than `block_ops`. Support references such as immutable `candidate_id + JSON pointer` or a selected block list wherever content is accepted; separately allow whole-operation reuse only after validation of its current intent and base. ATT-29's `from_candidate`, `select`, `block_indices`, and `override_meta` were illustrative shapes, not finalized JSON schemas. Raw capture precedes best-effort indexing; an indexing failure must not erase the saved raw candidate.

The final narrowing keeps complete-candidate exact reuse, insertion/append, and partial page updates in the first contract. It requires clear answers to which original is referenced, which fields change, what omitted fields preserve, and when commit succeeds. It does not require malformed-JSON salvage first.

<a id="candidate-relationships"></a>
## Useful candidates, partial adoption, and lineage

**Sources:** EVT-1006, ATT-27; EVT-1023, EVT-1040; EVT-1041, ATT-28; EVT-1060, EVT-1068; EVT-1069, ATT-29; EVT-1107; EVT-1162, EVT-1166.

ATT-27 proposed considering only candidates created after the latest successful commit and not superseded/abandoned. That rule was withdrawn: first-section candidate A can still contain necessary correct content when unrelated second-section B commits later. Use actual adoption/repair/replacement/abandonment relationships, not timestamps. A small active-work reference set can be enough.

ATT-28's statuses `active_unresolved`, `adopted`, `superseded`, and `abandoned` improved explicitness but a global candidate or task-only flag was still too coarse. One branch adopting two of three blocks does not resolve the third or another branch. A new candidate touching the same page does not prove complete replacement. Keep immutable originals separately from scoped adoption/discard relations; record version commit and actual adoption links atomically when applicable. Do not require a disposition report for every unused decorative/header fragment or make every unadopted candidate a completion gate.

ATT-29 proposed immutable candidate records plus `version_candidate_links` along version ancestry instead of a separate lifecycle state machine. This accurately records historical usage, but cannot alone prove current content or unfinished work: V10 can adopt a paragraph and V11 delete it while the ancestor link remains. Current content comes from the specified version; necessary unfinished work comes from task state. Branch management and a complete lineage UI are reference options, not V1 prerequisites under the final narrowing.

<a id="reconcile-without-pointer-regression"></a>
## Reconcile prepared work and replay historical receipts

**Sources:** EVT-1006, ATT-27; EVT-1023, EVT-1040; EVT-1041, ATT-28; EVT-1068; EVT-1069, ATT-29; EVT-1104, EVT-1107; EVT-1108, ATT-30; EVT-1147, EVT-1166.

ATT-27 proposed immutable version folders plus one atomically replaced `document_manifest.json` containing committed versions, working head, and selected delivery. It claimed a matching prepared folder could simply complete the manifest update after a crash. Counterexample: A prepares V11 from V10, another legitimate operation advances to V12, and replaying A would roll the head back. Correct recovery is: return the historical result if A already committed; finish a complete prepared result only if its expected base/target still holds; otherwise retain the useful prepared result and report conflict. Atomic file replacement still requires serialized conditional updates to avoid lost writers, and `ReplaceFileW` does not guarantee durability of a whole version's assets or universal power-loss recovery.

The preferred simplification became SQLite metadata for version registration, uniqueness, pointers, and operation facts, with staged immutable content files. Checkpoint and metadata are separate commit boundaries reconciled through identity. ATT-28's document-version DAG plus per-task/branch heads and delivery choices illustrates ownership; it is not a requirement to implement generalized branching. Final V1 preference is one active writer per task. Explicit regen/new-input entry rules remain useful; a display `branch_seq` need not become a second correctness key.

Persist resolved defaults when an operation starts: a missing version resolved to V10, selected parameters, and its output/attempt directory remain V10 on recovery. Dynamic defaults are still dynamic until resolved. Operation keys need app task/accepted-reply or step identity, not provider `tool_call_id` alone. An old Graph snapshot can describe what an earlier request saw but must not overwrite SQLite's later committed head.

**Historical receipt rule:** A produced V12 and B later produced V13; replay A returns the original V12 receipt while retaining V13. C selected V10 and a later selection chose V11; replay C returns its historical selection result without resetting delivery to V10. Receipts are facts at commit time, not assertions that today's pointer still equals that result. Recovering a frozen model request still uses its original input rather than silently inserting today's head.

Operation-specific reconciliation is necessary: save/edit checks original commit and expected base; select-delivery checks the historical selection and valid target/scope; export checks the specified version and destination package independently of current head; render/preview checks existing artifacts and parameters and can create a new independent attempt. Export V10 while editing V12 is valid. Incomplete draft export must not acquire a hidden “full scope complete” precondition from selection validation.

The accepted model reply may contain A (edit to V12) and B (preview still unfinished). Finding A's receipt is insufficient to start the next model round. Reconcile the **entire accepted tool-call list**, restoring completed results/intents and handling remaining calls or their stop reason. Only after whole-batch completion can the next new request be assembled from current committed work. The former controller's `next_call`/pending-operation state was evidence for this responsibility, not proof that a new graph already provides it.

<a id="operation-attempts-and-concurrency"></a>
## Operation attempts, concurrency, and useful partial files

**Sources:** EVT-1006, ATT-27; EVT-1023, EVT-1040; EVT-1041, ATT-28; EVT-1068; EVT-1069, ATT-29; EVT-1107.

Do not classify OCR/render as pure solely because the PDF is unchanged. They can allocate outputs and child processes; safe parallelism requires separate locations, resource limits, and started/completed records. Parallel eligibility and safe replay are different questions. A fixed-version `reopen` need not be banned from parallel execution merely by name. A first version can execute sequentially and expand concurrency only for real independence.

ATT-28's replay matrix proposed automatic read/render retry, CPU/WASM-bounded OCR with reconciliation, serialized edits/export, and stopping uncertain host-user scripts. These are operation-specific proposals, not a universal replay guarantee. Its instruction to clear incomplete `attempt_dir` before rerendering was rejected. Preserve complete useful images and diagnostics, verify identity/parameters, reuse suitable output, and create a new attempt for necessary reruns. A hash proves unchanged file bytes, not that they were rendered from the required source, region, DPI, or engine parameters.

Source render uses PDF identity/page/region/DPI and must work before any draft exists. Output preview uses the selected saved version and view parameters, with renderable candidates supported separately if useful. ATT-29's single version/candidate input requirement for both would obstruct source reading and was corrected.

<a id="overflow-and-accounted-compaction"></a>
## Overflow observations and accounted semantic compaction

**Sources:** EVT-1006, ATT-27; EVT-1034, EVT-1040; EVT-1041, ATT-28; EVT-1060, EVT-1068; EVT-1069, ATT-29; EVT-1083, EVT-1107; EVT-1108, ATT-30; EVT-1147, EVT-1166.

ATT-27 proposed returning from a rejected normal request to prepare, avoiding identical-input transport retry, allowing one or two reduced resends, and lowering route capacity using the rejected local token estimate. Rejection of an estimated 80k input proves that request failed under that configuration; it does not prove an 80k model context window. Record upstream error/count/limit, local estimate/method, and route/model/protocol separately. A provisional safety budget may change for that configuration without changing other routes or inventing a model specification. Automatic tuning is not a prerequisite.

A new step ID does not reset attempts, elapsed time, known usage, overall limits, or the bounded overflow-recovery event. Local evidence projection is deterministic; semantic handoff production is a real model call. It needs durable identity, frozen input, pre-send accounting, accepted-response capture, and the shared Nexus recovery/cancellation contract. It can be a distinct purpose or node without a second communications stack; it must not be hidden in a supposedly free prepare function.

Every actual send, including compaction and any reminder/repack, passes the shared service's final budget, cancellation, and capacity checks. A graph-top gate can be bypassed by restored successors, compaction-success edges, or unfinished-delivery loops. First reuse an already durable accepted result where applicable; zero remaining budget does not prohibit reading that result. An actual fresh request still requires remaining authority/budget. No success edge may skip a newly received cancellation.

Removing giant evidence alone may leave long user instructions, authoring tool arguments, and ordinary dialogue too large. That is a **hypothetical boundary**, not a proven historical failure. Preserve complete operations, effective requirements, unresolved work, and exact references; choose a compaction request that itself fits available capacity. Returning an inventory of unloaded content does not by itself solve accumulated history.

<a id="compaction-coverage-and-handoff"></a>
## Compaction coverage, incremental progress, and usable handoff

**Sources:** EVT-1041, ATT-28; EVT-1042, EVT-1060, EVT-1068; EVT-1069, ATT-29; EVT-1070, EVT-1104, EVT-1107; EVT-1108, ATT-30; EVT-1142, EVT-1147; EVT-1148, EVT-1149, EVT-1166.

Each compaction attempt must identify actual supplied message IDs/ranges, the prior handoff and its coverage, unprocessed history, and base context revision. Only processed ranges may be replaced; preserve complete tool-call/result pair boundaries. A cited LangMem summary implementation tracks summarized IDs but may select a tail on oversize input; that is reference behavior, not a complete-handoff guarantee. After model output, explicitly check format/nonblank/refusal, exact replacement scope, revision validity, and capacity effects before application, then return to normal-work assessment. Invalid or stale handoff leaves originals intact and is not routed as “no tool calls, therefore deliver.” Structural coverage checks cannot certify preserved meaning; the agent supplies semantic judgment, without a hidden review-model gate.

ATT-29's rolling oldest-prefix summary with a fixed current-head/notes anchor is a reasonable simple option, not the only correct selection. Summarizing a tail can reduce capacity while retaining the earlier prefix. Exact coverage and preservation of unprocessed messages provide the correctness boundary. Distinguish historical events from the current work state in the anchor; program-known message IDs, revisions, and anchor versions need not be regenerated by a model.

Separate **can apply this compaction** from **can resume normal inference**. Reducing 140k→100k toward an 80k target is useful and can be applied while further compaction remains. Evaluate the entire resulting model view including added anchors/references, not just summary length. A normal request must fit fully assembled input plus output reserve; an intermediate compaction step need not meet that final target. Original persistent budgets and a no-progress stop bound the process; two/three rounds are configurable proposals, not universal sufficiency. If application fails and capacity is still excessive, reconsider cause/selection rather than immediately resending the same oversized normal request.

ATT-30 proposed differential handoff containing only old information absent from the current anchor, limited to residual observations, rejected hypotheses, and cross-page clues. It risks loss if the old note says “next-page rows use the prior header,” the handoff omits that because it is in the anchor, and a later note replaces the anchor with “processing page 18.” An anchor reference on disk is not proof the information is assembled into future input. Such differential summaries require persistent exact-anchor inclusion or consolidation on anchor change. The final V1 preference is a self-contained handoff sufficient to continue work, protecting effective user requirements, unfinished tasks, saved-result references, important choices, and dependencies; do not adopt differential summary as a prerequisite.

<a id="authoring-history-and-cache"></a>
## Authoring history projection and cache claims

**Sources:** EVT-1069, ATT-29; EVT-1107; EVT-1108, ATT-30; EVT-1142, EVT-1147, EVT-1166.

Large body text can be present in old `AIMessage.tool_calls` arguments as well as OCR/tool results. Retain original replies, arguments, and results for execution/replay; project completed historical operations only in the next model's explicitly constructed view. Current pending calls still execute original complete arguments. Preserving a call ID alone does not establish protocol validity for rewritten history on every Nexus route. The proposed “90% reduction” was unmeasured and remains withdrawn.

Saving content does not automatically make immediate withdrawal useful: a just-saved paragraph may be needed to repair two characters next round. Conversely, ATT-30's fixed recent-K verbatim window and requirement that a draft be superseded before withdrawal are too restrictive. A large newest version or unresolved candidate can be represented by precise references for irrelevant portions while current text/context stays active. Use reliable preservation, exact retrieval, relevance, and capacity—not version age or a rigid K—as the decision basis. Batched work-view changes may preserve a stable prefix without per-turn sliding rewrites.

The cache claim also needed correction: a tool call just generated was not in the prior input, so projecting it before first return does not necessarily invalidate that prior prefix. Rewriting previously sent history is a different case. Route-specific cache benefit and equal-quality cost savings remain unproven. Frozen request snapshots, rather than permanent verbatim windows, guarantee same-request replay consistency. Cache optimization is not a V1 prerequisite.

<a id="malformed-candidate-boundary"></a>
## Malformed calls: raw preservation and optional exact extraction

**Sources:** EVT-1069, ATT-29; EVT-1099, EVT-1107; EVT-1108, ATT-30; EVT-1109, EVT-1127, EVT-1147; EVT-1162, EVT-1166.

There are at least two earlier rejection boundaries: raw JSON decoding and tool-schema validation. A wrapper can preserve decoded but schema-invalid calls delivered to it, while LangChain's `invalid_tool_calls` may bypass ordinary ToolNode dispatch entirely. Nexus reception owns native response/candidate preservation; the common dispatcher owns pre-schema argument preservation; indexing is a separate success condition. A callback or local storage layer cannot guarantee capture of bytes never received or a write that failed.

ATT-30 proposed “best-effort salvage” of 13 closed blocks before a truncated 14th/15th, calling the early blocks correct and implying only one needs rewriting. The correction accepts an **optional exact extraction** concept: use the same attempt and same tool call, retain raw identity and exact positions, recognize strings/escapes/structural boundaries, and independently parse only fully closed original subobjects. Do not add missing quotes/brackets/fields, combine attempts, or treat recovery as authorization to execute the failed original call. A new complete valid operation may reference extracted content after normal validation.

The historical offline example was `{"blocks":[{"id":"b1","text":"A"},{"id":"b2","text":"B","page":`. Pydantic `allow_partial=True` returned b2 without its unfinished field, despite b2 never closing; LangChain's partial parser can add closure characters. Neither output proves exact original completeness. Say “13 syntactically complete subobjects saved; remainder uncertain,” not “13 correct blocks” or “only rewrite block 14”; later ungenerated blocks may be missing too.

A historical record saved 8,419 characters of incomplete arguments during a streaming/service failure. It does not establish output-token truncation as the usual cause. Autonomous smaller saves/append/insert can also reduce giant-submission risk without a fixed page/block cadence. Final scope explicitly removes automatic malformed-block extraction from the V1 prerequisites; preserve the raw data and establish complete-candidate references first.

<a id="stop-state-and-independent-export"></a>
## Stop states, finite reminders, and independent export

**Sources:** EVT-1041, ATT-28; EVT-1068; EVT-1069, ATT-29; EVT-1083, EVT-1107; EVT-1108, ATT-30; EVT-1147; EVT-1162, EVT-1166.

ATT-28's five terminal labels mixed execution, content, and package verification. Keep those dimensions separate: a canceled run can still have a saved/exported useful draft; “verified” package consistency does not certify source fidelity. Known necessary scope gaps matter for completion claims, while optional unresolved candidates do not create a universal delivery gate. Resume retains original exhausted budgets and cancellation; explicit continuation can clear cancellation as defined, but it creates no new allowance by itself.

Unknown remote outcome and unreconciled local effects remain different. When enabled and still within the authorized original bounds, unknown-outcome model replay can continue under the existing limited policy; do not silently turn it back into mandatory settlement confirmation. Unreconciled local script/OCR effects stop with useful work retained. A genuine specific user question enters waiting; technical failure/budget/cancellation uses its own stop reason. The cited 180-second settlement-guard timeout and R1's 188.24-second delay were historical observations, not universal recovery thresholds.

ATT-30 proposed one reminder after a no-tool incomplete reply to handle narration (“next I will OCR”) or premature completion, then stop after a second stall. It remains optional. Explicit cancellation, a concrete question, or an explicit stop reason wins before a reminder. If used, persist reminder identity so restart cannot repeat it indefinitely, account for its model request, and report `stopped_incomplete` rather than pretending every stall requires the user to answer. A recognizable control field/tool can clarify intent, but no new control API is mandated. A reminder reduces one source of false stopping; it cannot guarantee next-turn action. Final scope excludes automatic reminders as a V1 requirement.

Host/CLI/UI-callable specified-version export independent of model quota is retained. Historical `Workspace.export(document, version)` and direct CLI dispatch already supplied a foundation; “zero quota means saved work can never be exported” was false. Export uses time/disk even with zero model tokens. The app may persist export intent/results so normal completion or a later host action can package an existing result.

ATT-29's all-exit deterministic finalizer guarantee was withdrawn: hard termination, shutdown, or cancellation may prevent any graph finalizer running. Cancel first stops new model/tool work; continuing a large package operation depends on the task policy. An automatically exported newest draft stays explicitly draft and must not replace the selected delivery. Actual files and ZIP members must match the selected version; a manifest hash alone is insufficient. Directory and ZIP publication are not one universal atomic replacement, and unrelated existing output must not be overwritten. “Every exit automatically packages” is not a V1 prerequisite.

<a id="progress-and-ipc-limits"></a>
## Structured progress and IPC limits

**Sources:** EVT-1041, ATT-28; EVT-1068; EVT-1069, ATT-29; EVT-1083, EVT-1107; EVT-1108, ATT-30.

A structured progress stream was proposed for the eventual Electron/React desktop: capacity/preparation, request/attempt/backoff, streamed-character progress, OCR pages, candidate preservation, and committed versions. Historical asynchronous stdio JSON was a chosen direction with message framing still open and no desktop integration yet. Durable state is authoritative; events are notifications after commit. Reconnection starts from a snapshot with sequence/revision; high-frequency updates can coalesce. An OCR page completion means evidence extraction, not page conversion or source acceptance. Version diffs read explicit immutable versions rather than reconstructing body from progress events.

ATT-29 proposed first-line `os.dup2` OS-level stdout redirection plus a ring buffer/watermark to preserve control replies and never block even if UI reading stops. That was narrowed: bounded memory, arbitrary non-droppable controls, producers that never wait, and unlimited new requests cannot all hold during indefinite receiver failure. Keep ordinary progress off the conversion core's critical path, persist important results for request-ID lookup, coalesce notifications, recover via snapshots, and reject/limit new work at declared queue/storage limits. Both protocol and diagnostics pipes need draining. Separate diagnostics from protocol, but mandatory first-line `dup2` is withdrawn; exact Windows/MCP/packaging wiring requires the selected implementation context, not a universal recipe.

<a id="canonical-storage-and-schema-counts"></a>
## Canonical storage and nonbinding schema sketches

**Sources:** EVT-1108, ATT-30; EVT-1109, EVT-1147; EVT-1148, EVT-1149, EVT-1162, EVT-1166.

ATT-30 warned of a second-system effect and proposed “four core modules plus six SQLite tables”: branches, document_versions, candidates, version_candidate_links, operations, context_revisions. This remains an illustration, not a complete/final storage specification. It did not settle owners for model steps/frozen requests/accepted replies/attempt totals, live context policy versus historical snapshots, canonical body versus indexes/manifests, or export intents and the three state dimensions. Those responsibilities can use an existing journal/checkpointer/record; no table count is intrinsically sufficient or necessary.

The proposal put full `blocks_json`/`page_map_json` in SQLite while retaining immutable version files. Two independently mutable body authorities would be a conflict. The final preference is immutable version files as canonical body, with SQLite owning identity, registration, manifest hashes, pointers, and operation receipts. Moving the body into SQLite would require a deliberate unified redesign rather than silent duplication. Likewise Nexus communications and export keep clear interfaces even if a chart groups them in one box.

The historical 228-check result supports retaining useful earlier behavior; it is scoped to its old version/affected test set. Old Nursing/Gynecology/JRE/News Writing accepted outputs, R1/R2 injected recovery, and preview verification do not certify new storage, graph recovery, arbitrary crashes, natural long outages, or installed-product readiness. Reuse capabilities and knowledge selectively; do not import old statuses, closed validation jobs, or test totals as this repository's requirements or results.

<a id="final-three-contracts"></a>
## Final narrowing: three open V1 contracts

**Controlling sources:** EVT-1148 (user explicitly stopped per-round design expansion), EVT-1149, EVT-1162, EVT-1166. This final scope supersedes earlier attachments describing proposed schemas/diagrams as settled or complete.

The architecture is sufficiently clear as **design responsibilities**, not implementation: one Python control layer with agent-chosen reading/OCR/inspection/edit methods; a small preferred LangGraph StateGraph; shared Nexus request service for ordinary and compaction calls with persistent budgets/cancellation/frozen native requests; document/evidence services retaining complete sources, candidates, immutable versions, exact reads and edits; separate evidence selection and history compaction; preserved pre-validation arguments and historical operation receipts; consistent specified-version Markdown, JSON, HTML, images, and ZIP with independent export. It does not depend on provider-native compaction, background retrieval, or remote cancellation. Framework, module, and table counts are no longer research questions.

| Open contract | Observed evidence and limits | Recommended tradeoff | Design-finalization condition |
|---|---|---|---|
| Document updates and candidate references | Full-page-map rejection and `本文件→本文作` rewriting regression; missing direct append/insert/local-map interfaces. This does not prove compaction caused the typo, or malformed-call salvage improves completed delivery. | Exact references to complete candidates; append/insert/local maps; merge then validate the whole result without retransmitting unchanged content; immutable canonical files plus SQLite metadata. Preserve malformed raw data; optional extraction later. | Specify original identity, updated fields, omitted-field preservation, and commit success. Express page-only correction, insertion, and rejected-candidate reuse without body regeneration. |
| Capacity and handoff | Large inspect/OCR input; prior checkpoint reduced input and recovered earlier evidence. No general cost or lossless-continuation proof. Draft-history overflow after release and anchor-dependent summary loss are hypothetical boundary cases. | Configurable route capacity/output reserve; assess all assembled content; release saved currently irrelevant content, then older history; partial projection may include latest and unresolved candidates; self-contained continuation handoff; gradual compaction, original preservation on failure, explicit stop on exhausted allowance. No fixed K, supersession prerequisite, differential-summary prerequisite, or promised 2–3-pass sufficiency. | Define send/release/compact/still-too-large behavior, protect unprocessed history and originals, and use configurable thresholds without universal-percentage research. |
| Persistence, recovery, and stop | Save-and-continue and R1/R2 injected delivery evidence. Tool commit before Graph checkpoint and replay after head advancement are hypotheses requiring bounded rules, not observed universal failures. | One active task writer; explicit sole owners for requests, batch progress, versions, and receipts; frozen same-request recovery; complete whole tool batch before next input; historical result replay without extra commit/head rollback/budget reset; stop unreconciled local effects; wait only on real questions; independent saved-version export and draft labels. | State recovery at request-saved, reply-accepted, tool-committed, and Graph-recorded boundaries, with each owner's authority. Do not promise arbitrary old-task or all-hard-crash recovery. |

The final response **recommended** these choices for design finalization; it did not itself turn the three still-open contracts into implemented/verified behavior. Contract consistency and clear responsibility close design; implementation success is later assessed through proportionate offline checks and source-led reading of the specified PDF/complete section. Do not make unbounded preliminary research the gate.

Malformed JSON salvage, cache optimization, general multi-branch management, automatic reminders, and automatic packaging on every exit are reference ideas, not V1 prerequisites. Desktop interface, backend integration, and Windows packaging remained unimplemented in the historical project; they remain real delivery work if the requested result is an installable desktop product, without reopening the context architecture. Reopen design only for an observed implementation/delivery blocker that would violate the agreed contract; other hypotheses do not form a new backlog.

<a id="review-coverage-and-exclusions"></a>
## Review coverage and exclusions

This review read the entire prepared segment for EVT-0827–EVT-1168 (157,826 newline-normalized characters, 3,861 lines), including a separate read of the final consolidation EVT-1166, in bounded, untruncated reads. All ten embedded attachments ATT-21–ATT-30 and the substantive user/assistant messages were considered. The public [point coverage ledger](POINT_COVERAGE.json) maps topics to exact EVT/ATT IDs and the stable anchors above; the [source index](SOURCE_INDEX.md) explains lookup. Repeated acknowledgments are associated with their substantive correction topic rather than copied as separate requirements.

EVT-1167 requested export of the conversation, and EVT-1168 announced use of the export skill. Both were read and are intentionally excluded from the **design** point ledger because they concern producing the source package, not product design. Their existence and exclusion are recorded here. No source-recorded command was executed; no new web research, model request, implementation, commit, or push was performed for this reference. Source prose references historical tool/code checks; this review does not freshly repeat or certify those checks.

Coverage is a traceable synthesis, not a claim that every historical wording is a new requirement or that source-message inclusion proves semantic completeness. The final three-contract narrowing controls any apparent conflict with a detailed earlier proposal.
