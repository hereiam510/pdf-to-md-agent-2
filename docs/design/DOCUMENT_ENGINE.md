# Document, evidence, and candidate engineering handoff

This guide explains the document-side responsibilities needed to implement the rebuild without the original chat export. It records the retained behavior, the reasons for it, concrete failure cases, and choices still open under Q1. It is a design handoff, not an implementation claim. Names in code formatting and record examples describe concepts; they do not freeze a public API, schema, table count, or directory layout.

The active contract is [CONTRACTS](../CONTRACTS.md), and its unresolved choices are in [OPEN_QUESTIONS](../OPEN_QUESTIONS.md). [Execution and delivery](EXECUTION_AND_DELIVERY.md) owns durable requests, accepted batches, operation replay, cancellation, and packaging. [Context and evidence](CONTEXT_AND_EVIDENCE.md) owns selection, capacity, and history compaction. [Integration](INTEGRATION_AND_MODEL_BOUNDARY.md) owns protocol and framework wiring. The detailed late-source [reference record](../reference/03-documents-delivery-and-recovery.md) preserves rejected alternatives; [local source material](../reference/sources/INDEX.md) is optional audit evidence.

The central observed problem was concrete: correct `本文件` existed in a retained candidate, a full page-map validation rejected the submission, and later regeneration produced `本文作`. Better storage cannot prove transcription correct, but it can avoid forcing the model to rewrite already-correct prose to repair metadata. The same reasoning applies to a large table with one missing bold span: precise editing should preserve everything outside the selected change.

<a id="identities-and-canonical-data"></a>
## 1. Identities and canonical data

Keep the following objects distinct even when they share a SQLite database and one Python process:

| Object | What it identifies | Important boundary |
|---|---|---|
| Source | The particular PDF bytes and physical page order | Replacing the source changes the meaning of evidence and coordinates. A filename alone is insufficient. |
| Evidence | One saved inspect/OCR/render result and the source/settings that produced it | A later OCR run can create different blocks and coordinates. Evidence identity must survive context release. |
| Received candidate | Original proposed writing content or arguments | It may be invalid or incomplete. Preserve it before deciding whether it is a usable draft. |
| Effective edit submission | A complete proposed operation after exact reference resolution and explicitly defined overrides | Its input is distinct from the retained original candidate and has its own accepted operation identity. |
| Document version | The immutable saved body, mapping, and referenced assets for a particular result | Its content is fixed even if the working head or delivery selection advances. |
| Working head | The selected current working version | Advancing this pointer is an effect with a defined commit boundary. |
| Delivery selection | A chosen version and effective scope belonging to the current task | It may select an older good version while the working head contains a later experiment. A document-wide global selection must not silently replace another task's choice. |
| Task/scope state | User requirements, requested content, progress, issues, and completion claims | A task's `outside_scope` or unresolved issue is not a permanent fact about the PDF. |
| Operation receipt | The historical result of one accepted edit, selection, or other operation | It identifies what committed then, not what every pointer must equal now. |

The preferred body authority is the immutable version file payload. SQLite owns identity/registration, references or manifest hashes, selected pointers, uniqueness, and receipts. Avoid a second independently mutable full body in `blocks_json`: updating that JSON without updating the files, or vice versa, would create two incompatible answers to “what is V12?”. Derived indexes may be rebuilt, but their relationship to the canonical payload must be explicit. Moving the body into SQLite would be a deliberate alternative design, not an incidental copy added for convenience.

An illustrative registration might contain `document_id`, `version_id`, `payload_ref`, `payload_hash`, `parent_version`, and `producing_operation_id`; it is not a required table definition. A content hash checks byte equality. It does not establish the task, source, selected region, intended operation, whether the model saw the content, or whether it remains in a later version.

The discussion called the mutable working pointer `document_head`, `working_version`, `working_version_id`, or `head_version_id` in different sketches. `selected_delivery` and `selected_delivery_version_id` named the separate delivery choice, sometimes carrying `scope_rev` and a draft/completion label. These are vocabulary variants, not several pointers that must all be implemented. The effective distinction is an immutable version versus a task's current work/selection; a pointer copied into a frozen request records what that request saw and cannot become a second live authority.

Logical document blocks support readable structure and stable editing. The requirement to keep a sentence or table readable around page markers does not mean every table must be one indivisible database unit or one model submission. A 4,000-character table can remain a coherent output table while a cell or substring is internally addressable. Conversely, a block ID alone does not locate that content precisely in the source PDF.

**Source basis:** EVT-0855, EVT-0878, EVT-0942, EVT-1005, EVT-1040, EVT-1068, EVT-1147, EVT-1166; ATT-21–ATT-30 with the later corrections controlling.

<a id="evidence-and-exact-access"></a>
## 2. Evidence, precise access, and computation reuse

Preserve complete evidence and expose exact first/full/raw/field/range/native-image access. A caller may request a useful field directly on its first call, or request the full result. A compact receipt or inventory can describe a result that did not fit into the current input; it is not an obligatory summary gate. State what was actually returned, what was omitted, warnings, exact reread methods, and the underlying saved identity. Keeping the original on disk does not prove the model received or understood it.

An evidence reference should resolve to an immutable result and an internal location. For example, the concept “evidence E, block `p14_b03`” can carry source PDF identity, page, coordinate system, and render/OCR parameters through E. Bare `p14_b03` is ambiguous after an engine change, crop, or recomputation. `bbox_pixels` describes positions in a particular rendered image; `bbox_pdf` describes positions in PDF coordinates. A crop needs the correct transform and rendering context. Do not demand a manually entered box for every word or cell: a page reference or agent-selected region is valid when only coarse location exists, and one output block can have several source regions.

The illustrative `source_refs` item `{"evidence_id":"ev_004","item_pointer":"/pages/14/blocks/3"}` makes both parts visible: `evidence_id` fixes the retained result, while `item_pointer` selects a location within its actual structure. A JSON pointer's array position is not itself a physical PDF page number; the referenced record supplies that meaning. A previous `{page, from_inspect_block}` sketch lacked this durable evidence binding. Updating an observation or choosing a newer OCR result produces a new reference/observation; it does not rewrite the immutable result behind an existing reference.

The document core makes the same preserved evidence available to the built-in runtime, external MCP clients, and CLI. Only the built-in input assembler knows its complete model-input footprint. An MCP server can report its result's size and available projections, but cannot remove already-returned content from an external host's conversation or infer that host's remaining capacity. The external host can perform its own compaction; content is not necessarily permanent merely because the server cannot alter it.

Text, words, layout, and font/position fields may overlap while carrying different evidence. Deduplicate avoidable serialization without declaring one fixed field set sufficient for every task. Full access remains available, and the agent chooses which representation is relevant. An OCR confidence score or a small text difference cannot establish that an image is dispensable.

An optional computation index can reuse independently computed page/region results. The historical key proposal included source hash, tool/engine version, language-data hash, normalized parameters, and page/region. Overlapping requests could retrieve existing units; an explicit `force_recompute` could obtain a fresh result. This does not require a separate file for every page, force cached results into model context, or prove cost savings. Suitability includes how the result was produced, not merely whether its bytes still hash correctly. Computation reuse remains a performance option, not a V1 prerequisite.

**Source basis:** EVT-0855, EVT-0878, EVT-0968, EVT-1005, EVT-1068, EVT-1107; ATT-21/22/28/29. The [context guide](CONTEXT_AND_EVIDENCE.md) explains the global input-capacity boundary.

<a id="candidate-capture"></a>
## 3. Retention precedes validation

Use the following responsibility order, without assuming a single framework callback covers every stage:

1. The Nexus receiving layer preserves the native response and writing fragments actually received, including raw arguments that cannot be decoded into a valid tool call.
2. The common dispatch boundary preserves app-received, decoded writing arguments before the domain schema can reject them.
3. Check the decoded call's tool/envelope and reference-input shape. A schema that supports references must admit those references; it must not require their full resolved body to have been retransmitted. Captured invalid arguments remain a candidate record with precise errors.
4. Resolve the exact candidate/content references and explicitly defined overrides against the named base. Preserve the received call separately from this complete effective submission; a repair is a new operation, not a mutation of the rejected original.
5. Apply the declared operations to a working copy and validate the resulting complete document, page map, references, and assets under the draft contract. Checking only the patch or the reference envelope is insufficient. Unknown or incomplete task metadata must be represented honestly rather than confused with invalid structural relationships.
6. Prepare immutable content and conditionally commit according to the [visibility boundary](#commit-visibility). Only this step establishes the promised saved-version/pointer effects.
7. Return the operation outcome and model-facing projection. A projection failure after commit is not an unperformed write.

Saving only inside `DocumentService.save()` is too late if a framework rejects required metadata before entering that function. A wrapper's `args` may already be a parsed dictionary: it can preserve schema-invalid calls it receives, but not necessarily malformed raw JSON. LangChain's `invalid_tool_calls` can bypass ordinary ToolNode dispatch. Native capture and pre-schema dispatch capture protect different rejection boundaries; best-effort indexing is a later convenience, not the only retained copy.

<a id="framework-capture-order"></a>
### The framework rejection that motivated the capture boundary

In the reviewed LangChain path, `BaseTool._parse_input` applies the Pydantic `args_schema` before invoking the Python tool function. A missing required field or wrong metadata type can raise `ValidationError` before `DocumentService.save()` runs. The proposed outer `wrap_tool_call` hook can first retain the received `tool_call["args"]` dictionary, then let ordinary tool validation proceed. That dictionary is already a decoded representation: an earlier JSON decoding failure can instead enter `AIMessage.invalid_tool_calls`, while normal ToolNode dispatch reads `AIMessage.tool_calls`. Those failed raw arguments therefore need the Nexus receiving path, independently of the wrapper. This describes the reviewed integration sequence, not a requirement to adopt the prebuilt agent or an assumption that private framework methods remain unchanged.

The proposed error fields were `error_code`, `field_errors`, `saved_candidate_ref`, and `recovery_hint`. Their useful division is a machine-readable rejection category, exact invalid locations, the content actually retained, and an actionable repair explanation. For example, a page-12 map error should identify that field and say that the saved body can be referenced in a new repair; it should not ask for the body again or imply that page 13's rejected metadata was committed. The names remain examples. If retention fails, omit any claim of a usable saved reference and report that distinct failure.

The same issue applies to MCP. The reviewed SDK validated registered-tool arguments before invoking the function. A permissive transport schema alone was not a complete remedy: the request could still have a wrong container or be rejected earlier, and weakening tool schemas removes useful guidance. The historical SDK 2.3.0 review found an `Extension.intercept_tool_call` hook before tool validation for an accepted `tools/call` request. The retained requirement is to find the supported interception boundary in the actually selected version, not to assume that hook exists unchanged. A server cannot preserve arguments that the external client rejected before transmitting them, and no local callback can guarantee storage of bytes never received or a failed disk write.

Return a stable reuse reference with validation errors. Explain whether body, metadata, assets, or target/base applicability failed, so the next action can repair that part. Truly optional draft metadata should be optional in the draft contract. Body and page changes may still be accepted in one atomic edit; different validation responsibilities do not require two model calls.

This sequence distinguishes early call validation from validation of the resolved result. It does not prescribe one parser, a second permissive tool schema, or the final reference syntax. If a reference cannot be resolved or a raw candidate cannot be indexed, report that limit while retaining what was actually saved. A `candidate_ref` can honestly be returned only after its backing content was durably retained; “capture attempted” cannot be advertised as successful preservation when storage failed.

**Source basis:** EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1107, EVT-1147; ATT-23–ATT-30.

<a id="candidate-reuse-and-lineage"></a>
## 4. Exact reuse, candidate lineage, and malformed originals

A candidate reference can conceptually be an immutable `candidate_id` plus JSON pointer, selected block list, or another exact location accepted by the chosen tool surface. The reference must identify the retained bytes/content, not a mutable “latest candidate.” Proposed forms such as `reuse_candidate_ref`, `block_ops_from_candidate`, `from_candidate`, `block_indices`, and `override_meta` are alternatives from the discussion, not jointly mandatory fields.

The later names `content_from_candidate` and `replay_ops_from_candidate` were meant to expose different intentions. An illustrative content item was `{"from_candidate":"cand_04","select":"/blocks/2","override_meta":{}}`; another selected several items with `block_indices`. These forms retrieve content without regenerating it, with any metadata overrides governed by the eventual merge contract. In contrast, `replay_ops_from_candidate="cand_05"` proposed reusing a whole operation sequence. The earlier `block_ops_from_candidate` spelling obscured that distinction because a list of edits is not merely a list of prose blocks. None of these spellings selects the final reference schema.

Separate two intentions:

| Intention | Meaning |
|---|---|
| Reuse content | Copy the exact selected prose/table/block into a new operation, with explicitly supplied applicable metadata. |
| Reuse an operation | Ask to perform the earlier append/delete/reorder/replace/patch sequence against an identified base after checking its current intent and applicability. |

A failed `save_draft` can contain a `blocks` array and no `block_ops`. A candidate's `block_ops` may delete or reorder unrelated content. Reusing a correct paragraph must not require executing those old effects. Replacing the base version also requires rechecking targets and expected text; byte-identical operation arguments do not imply applicability to a different document state.

For nested repairs, define omission and replacement explicitly. If C contains page-12 and page-13 updates, a correction for page 12 must not silently erase page 13. Choose and document per-page upsert, whole-array replacement, and nested-field semantics. Preserve C, then save the new effective-argument snapshot and its parentage with a new operation identity. Changing the input of an existing accepted operation ID is an inconsistency, not an update.

Candidate usefulness cannot be inferred from creation time. Candidate A for the first section may still be needed after an unrelated second section commits. `active_unresolved`, `adopted`, `superseded`, and `abandoned` were proposed labels, but one global flag is insufficient for partial adoption or different task scopes. Adopting two of three blocks does not dispose of the third; a later candidate on the same page may cover different content. A small active-work reference set can represent current work without implementing a general lifecycle engine.

In particular, the proposed query `WHERE task_id = ? AND lifecycle_status = 'active_unresolved'` cannot describe which subitems a branch used. The later `version_candidate_links` sketch records `(candidate_id, item_pointer)` against the produced version instead. Its advantage is precise historical adoption, not automatic inference of current completion; the next paragraph's deletion example is why an ancestry query cannot replace current version content or active work state.

Version-to-candidate links record historical use. V10 may adopt a paragraph and V11 delete it; V10's ancestry link remains true while V11 no longer contains the paragraph. Current content is read from the specified version; necessary unfinished work belongs to task state. Do not require an explicit disposition report for every unused header/decorative fragment, and do not make all unadopted candidates a completion gate. General branching and a lineage UI are deferred options.

When a commit records adoption links, include the actual candidate/content locations used in that commit's metadata transaction. Otherwise a crash can register a version without its claimed provenance, or mark a candidate adopted when the version never committed. This requirement concerns the recorded relationship, not a compulsory lifecycle table or an instruction to adopt every available fragment.

<a id="candidate-repair-sequence"></a>
### Worked example: rejected body reused with a page-only repair

Suppose candidate C contains two paragraphs and page-map changes for physical pages 12 and 13. The prose includes correct `本文件`, but page 12's metadata is invalid. C's rejection has not committed those changes to base V10.

1. Retain C's original arguments and the page-12 validation error. The existing document remains V10. Do not claim C is a valid version merely because its body is readable.
2. The repair names V10, C, and the exact content to import. A reference into C's `blocks` selects prose; it does not implicitly execute a `delete` or `reorder` from another candidate field.
3. The repair supplies the page-12 correction and expresses the intended treatment of C's page-13 proposal. A content-only import does not silently inherit all rejected metadata. If it should retain page 13, it must explicitly import that metadata or use a declared whole-candidate merge contract that preserves it. Metadata already in V10 follows the ordinary omitted-field preservation rule.
4. Resolve C's selected content exactly, assemble the effective submission, and keep C and the repair separately identifiable. Do not ask the model to regenerate the paragraphs; no automatic malformed-JSON extraction is involved in this complete-candidate case.
5. Apply the body import and metadata changes to a working copy of V10. Validate the whole resulting map and structure, including relationships involving unchanged content. Validation succeeds for a coherent draft even when explicitly permitted facts remain unknown; it does not establish source fidelity or full-scope completion.
6. At commit, check the expected base/head again. If compatible, register the new version, the promised pointer changes, operation result, and actual adoption relations coherently. If stale or invalid, preserve C and the prepared repair and report the conflict/error; do not silently apply it to a newer head.
7. Return the new version's receipt. A retry of the same accepted operation returns that receipt. A later correction changes the effective input and receives a new operation identity.

This distinguishes two forms that the final Q1 schema still needs to make unambiguous: importing selected candidate content with explicit new metadata, and reusing a broader candidate submission with declared merge/override rules. Both can protect page 13; an undocumented mixture can erase it.

### Optional extraction from an incomplete call

Raw malformed arguments are retained regardless of whether automatic extraction exists. If exact extraction is added, it must operate within one attempt and one call, preserve raw identity and span, understand strings/escapes/structural closure, handle duplicate-key and array-order semantics, and independently parse only fully closed original subobjects. Do not add closure characters, synthesize fields, merge attempts, or execute the failed original operation.

For the received text:

```text
{"blocks":[{"id":"b1","text":"A"},{"id":"b2","text":"B","page":
```

The original b1 object is closed; b2 is not. A tolerant parser may return b2 while dropping its unfinished `page`, or insert braces. That is a repaired interpretation, not evidence that b2 was received complete. Exact extraction can expose b1 for a new validated operation; it still cannot establish correct source transcription. Report “complete subobjects extracted; remainder uncertain,” not “all early blocks are correct” or “only the last block needs regeneration.” Later ungenerated content may also be missing.

The reviewed examples were Pydantic's `allow_partial=True`, which returned b2's already-read fields, and LangChain's `parse_partial_json`, which can repair closure characters. These behaviors suit tolerant decoding; they are insufficient as the test for an exact original span. `salvaged_blocks` and `status: "salvaged_from_malformed_call"` were proposed index labels, not evidence that the original call became valid or a requirement to implement extraction in V1.

The historical 8,419-character incomplete-argument record arose during a streaming/service failure. It does not prove output-token truncation is the usual cause. Smaller saves/append/insert are available to the agent without a mandatory page/block cadence. Automatic malformed-call extraction is not a prerequisite for exact reuse of already-complete candidates.

**Source basis:** EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166; ATT-27–ATT-30.

<a id="edit-semantics"></a>
## 5. Edit semantics, locators, and character fidelity

The first contract must express exact reuse, insertion/append, and metadata-only repair without body regeneration. Useful operations discussed include:

| Operation | Required meaning to specify |
|---|---|
| Append / insert before or after | Insert new content at an explicit position without requiring a nonempty removal range. |
| Replace / delete | Identify the target blocks/content and the expected base. |
| Move / reorder | Define the destination and ordering effect within the working copy. |
| Exact patch | Identify stored content, expected old text, match/location semantics, and replacement. |
| Whole-section / whole-block replacement or import | Retain a practical route for larger reconstructions when the agent judges them necessary. |
| Page/provenance update | Change selected metadata while preserving omitted body and other metadata under the declared merge contract. |

A proposed `edit_document(base_version, reuse_candidate_ref, block_ops, page_map_updates, provenance_updates, delivery_selection)` illustrated grouping these responsibilities. Another proposal separated `save_draft`, `edit_document`, and `select_delivery`. Tool count alone neither establishes a small schema nor reduces cognitive load; choose the surface after specifying the behavior.

For an operation sequence, create one working copy, apply the declared sequence, validate the final merged result, and commit one version. Define whether later block locators refer to the initial base or earlier operation results. Do not accidentally mix sequential block operations with simultaneous string-patch coordinates.

For a set of patches aligned to one unchanged base, a retained option is: resolve and verify all expected spans, reject overlaps/ambiguity, then apply replacements from the greatest offset backward. This prevents an earlier replacement changing a later span's coordinates. Explicit sequential patches are another possible contract, but later anchors must intentionally refer to the intermediate state; accidental creation/destruction of matches cannot choose semantics for the caller.

<a id="patch-preconditions-and-locator-fields"></a>
### Expected text and location are separate checks

RFC 6902's `test` was cited because it checks an expected value at a JSON location before a later change proceeds. It does not define searching and replacing a substring inside Markdown. Our analogous precondition is to check `expected_old_text` against the selected stored span at the named base; if it differs, reject the proposed patch instead of searching a newer version for something similar. The original `find_exact` / `replace_with` / `expected_matches` form makes a text search and count explicit, but `expected_matches: 1` is neither a source-correctness check nor a solution for deliberately repeated cells.

The locator proposals refined that search as follows. These are alternatives to specify under Q1, not a combined mandatory object:

| Discussed field or reference | Mechanical purpose and unresolved convention |
|---|---|
| `line_range: [start_line, end_line]` | Limit searching to raw stored lines; define the line base, endpoint inclusivity, and newline convention. This edit-range proposal is separate from the parser's half-open source ranges described below. |
| `context_before`, `expected_old_text`, `context_after` | Match the target with surrounding stored text when the target value alone repeats. Context anchors still need explicit matching and ambiguity rules. |
| `occurrence_in_range` or a returned range reference | Select a particular verified match within the chosen range. A caller's explicit choice differs from silently defaulting to the first occurrence. |
| `replacement_text`, `new_text`, or `replace_with` | Alternative names for the proposed replacement; they do not change the precondition or location semantics. |
| `table_cell_locator` or `cell_ref` | A table-aware convenience that resolves to an exact version-bound span. A read-only grid may expose `visual_row_span` / `visual_col_span` and raw HTML locations; row/column coordinates must distinguish visual cells from stored elements. |

For example, a returned range for the second `12.4` on a raw HTML line can select that cell while `expected_old_text` guards against a stale read. Check every selected base span before applying a same-base patch set; then descending-offset replacement preserves the remaining coordinates. If surrounding context matches twice or an earlier sequential edit changes the intended cell, the contract must reject or deliberately resolve that condition rather than silently choose a match.

Repeated cells make naïve matching unsafe. A table can contain many `0`, empty cells, `是`, or `12.4` values, including several on one raw line. `occurrence=1` must not silently select the first unless the caller deliberately chose that location. A returned cell/range reference, raw-line range plus expected text, or within-range position can provide precision. Display wrapping is not stored newlines; a one-line HTML table defeats line number alone. Row 5/column 3 also needs a declared distinction between visual grid coordinates and stored cells when `rowspan`/`colspan` exist. A cell reference can be a convenience over generic patches without requiring a separate mandatory table AST.

Preserve source characters. JavaScript string positions use UTF-16 units while Python commonly exposes code-point positions; an interface needs an explicit counting convention and programmatic conversion. It must not require a model to hand-count an entire table. The historical normalization check showed `U+2F800` becoming `U+4E3D` under NFC. That proves NFC is not universally lossless for source distinctions. Do not silently normalize glyphs, convert traditional/simplified Chinese, or fuzzy-match a correction. An explicit LF version-storage rule remains possible; preserve received originals and define the mapping. Pretty-printed HTML and normalized search can be mapped read/edit views instead of rewriting canonical content.

Adding HTML whitespace can create text nodes and affect copying or parsing. A format-only change is therefore not automatically byte/behavior neutral. Likewise, the illustrative patch `<td>厲行節約</td>` to `<td><strong>礪行節約</strong></td>` changes both emphasis and a character. One exact match proves a unique target under that locator, not that the change agrees with the PDF. The app guarantees untouched content is not regenerated; source-led judgment determines whether the selected edit is correct.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-1040, EVT-1068, EVT-1166; ATT-21–ATT-30.

<a id="page-maps-and-provenance"></a>
## 6. Page maps, provenance, scope, and claims

Keep four responsibilities separate:

| Responsibility | Examples | Why it is separate |
|---|---|---|
| Source inventory and observations | Source identity, physical page order, observed printed label, blank-page observation, region evidence | The PDF can remain unchanged while a prior label reading is corrected. |
| Task scope | Requested pages, complete section, figure/table, explicit exclusions, scope revision | A partial-page task cannot be fully described by `target_pages=[12]`. |
| Output provenance | Which output blocks derive from which source pages/regions/evidence | Having one paragraph from a page does not account for its footnotes and tables. |
| Work/review claims | Drafting, known gaps, completed requested section, review tied to a version/scope | A complete structural map is not semantic acceptance. |

The Nursing example requested “Breasts and Figure 4–13,” physical page 12 / printed page 68, excluding adjacent content. That is a complete useful scope within one page. Completing it under task A does not complete task B's later full-page request. Retain useful prior content and identify added/uncertain scope; no universal rereview of every unchanged part follows.

Sparse updates and complete correspondence are compatible. A change for one page can merge into the named base; the service can construct the complete output map from source page count, task scope, and existing facts. Do not force resubmission of 173 entries for one correction. Validate the complete merged map rather than validating only the patch or silently treating absent entries as outside scope.

The exact per-page key and nested merge semantics remain open. A proposed `pdf_page` key expresses physical page identity. Keep `unknown` printed label distinct from `none`: unknown means not determined; none means no printed label is present. Stable physical order remains available in both cases. Source visibly blank, deliberately omitted decoration, unprocessed content, and outside this task are different observations/decisions. A copyright page can contain requested author, edition, ISBN, or other content and must not be automatically omitted.

The proposal names `source_page_inventory`, `block_provenance`, and `task_scope_and_claims` express those responsibilities. `printed_page` is an observation alongside physical `pdf_page`; `source_scope_note` describes a block's source boundary; `scope_id` / `scope_rev` and `page_coverage_claims` relate task claims to the selected `version_id`. A changed scope or corrected printed-label reading must not alter an earlier immutable version's evidence. These names aid interpretation of the discussion and leave the final record layout open.

Output page markers and structured mapping must express the same source relation. Physical pages are one-based positions in the particular PDF; Roman or other printed labels are observations from visible source content, not inferred viewer labels. If a block uses pages 12 and 14, a grouped marker must not imply that page 13 contributed. English HTML-comment labels can preserve correspondence without interrupting a sentence or table at an artificial page boundary. Exact marker serialization is governed by the product requirement and the eventual document contract, not by a mandatory storage-block size.

Names such as `converted_full_page`, `converted_partial_scope`, `source_visibly_blank`, `omitted_non_content`, and `unprocessed/drafting` were proposed to improve expression, not to make the app an automatic semantic judge. “Every target page has a block or is marked blank/omitted” is too weak: a page can have a converted paragraph and a missing table. Completion binds effective scope and document version, with known material omissions/errors made explicit.

A draft may be saved, previewed, snapshotted, and exported with incomplete facts. A later `publish_version` or completion gate must not make useful drafts inaccessible. Export consistency, completion claim, and source review remain distinct records. Page mapping covers correspondence; it does not require body text on every input page.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-1040, EVT-1068, EVT-1166; ATT-21–ATT-30.

<a id="commit-visibility"></a>
## 7. File preparation, SQLite commit, and visibility

The recommended sequence is a staged immutable payload followed by a short conditional metadata transaction. It avoids claiming that SQLite also commits the filesystem or graph checkpoint.

1. Resolve the intended document, base, effective parameters, source/reference identities, and operation identity. Preserve resolved defaults for recovery.
2. Construct and validate a working result without mutating the committed base. Prepare the immutable body/assets and verify the required files are present and correspond to that result.
3. At the actual metadata commit boundary, check operation uniqueness and the expected base/head conditions. A prior check before parallel work is insufficient.
4. Commit version registration, the promised pointer changes, the producing operation's identity/outcome, and any actual adoption/provenance links coherently. A same-ID/different-input submission is rejected.
5. Return the receipt and a model-facing projection. If projection fails, the commit remains a success that can be reconciled and returned again.
6. The graph records completion separately. Recovery reuses the committed result rather than repeating the edit.

This is a responsibility sequence, not a guarantee of universal power-loss durability. The selected filesystem/database settings and visibility rules still need implementation decisions. “Atomically replace one file” does not atomically publish a directory's assets, update another file, and checkpoint graph state.

The commit-as-receipt proposal usefully embeds an operation identity in a version or metadata record. It does not make folder existence equal to successful save. The old order moved a version folder and then updated `current.json`; a crash could leave useful prepared content without the working head advancing. If save promises registration and head advance together, the metadata transaction must define that effect, or the API must explicitly expose separate operations.

For example, A prepares V11 from V10, then another legitimate operation advances the head to V12. Recovery of A follows its recorded state:

- If A already committed, return its historical receipt and keep V12 current.
- If A has only a complete prepared result and its expected base/target still holds, finish the originally defined conditional commit.
- If that base/target no longer holds, preserve the prepared V11 content and report conflict. Do not silently overwrite V12 or reinterpret A as an edit against V12.

The same rule applies with one active writer after restart: durable later facts can outlive an old graph checkpoint. An in-memory lock is not a durable uniqueness guarantee. Two individually serialized SQLite writes also do not resolve concurrent graph policy updates; each authority needs its own defined writer.

Do not delete unreferenced attempt/version files simply because they are not registered or no process currently runs. They may be the only recoverable correct work. A first version can avoid background cleanup; a generalized lease/garbage-collection system is not required. Started/unknown/completed execution facts for scripts or model calls cannot be replaced by successful document-version metadata alone.

**Source basis:** EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166; ATT-25–ATT-30.

<a id="rendering-and-preview"></a>
## 8. Rendering, reading, and precise comparison

Source rendering and output preview use different identities. Source render needs PDF identity, physical page, region, DPI, and related parameters and must work before a draft exists. Output preview uses a saved document version and view parameters; rendering a candidate may be a separate convenience. Requiring a document version for source rendering would obstruct the agent's first source read.

Comparison can provide independent native images, separate crops, or an explicitly chosen montage. Keep source pixels unmodified, with labels/dividers outside them and enough surrounding context to interpret the crop. Two native images may still be resized by a route's processor; neither 300–400 DPI nor a 900×350 crop guarantees model-side resolution. More DPI cannot recover detail missing from a scan. The historical proposal that 24×24 glyphs became 12×12 after joining pages was a possible scaling mechanism, not a diagnosed cause of old emphasis errors.

Render the complete Markdown document with its supported CommonMark/extensions before locating output regions. Separate block rendering changes semantics. For example:

```markdown
See [source][r].

[r]: https://example.com
```

The reference link resolves when the definition is in the same parsed document. Rendering the first content block alone can lose the definition. Parsing together still does not enable a footnote extension absent from configuration.

Parser token/source-line information may help produce app-owned DOM anchors. It is not automatically a one-block/one-element map: tokens can span content-block boundaries and one block can produce several DOM regions. Raw HTML needs explicit handling; the historical parser returned an `html_block`'s raw `token.content`, ignoring attributes attached only to the parser token. A `data-block-id` wrapper/attribute proposal therefore was not a complete 15-line mapping engine. Sanitization and allowed app-generated markers must preserve the intended rendering and security boundary without rewriting source content casually.

<a id="parser-source-map-mechanics"></a>
### How the proposed source-line map would locate output

The `markdown-it-py` proposal first assembles the exact whole Markdown version, recording each source block's half-open `[start_line, end_line)` interval, including the effects of separators inserted during assembly. It then parses that whole string once. A core rule can compare each top-level token's `token.map` source interval with the recorded block intervals and associate eligible rendered regions with `data-block-id`. Multiple output elements may share one block ID; a token crossing block boundaries needs a many-to-many mapping rather than an arbitrary single owner. The mapping is to this assembled version's source lines, not PDF coordinates or editor visual wrapping.

For ordinary rendered tokens, adding an attribute may be sufficient for an appropriate renderer. In the reviewed raw-HTML path, `token.attrSet("data-block-id", "blk_01")` does not change the emitted `<table>` because the `html_block` renderer returns `token.content` directly. Explicit handling during serialization or carefully chosen containers is therefore needed for raw HTML. The `nh3` sanitization proposal would allow the intended app-generated marker on the relevant elements; merely adding a token attribute or widening the allowlist cannot solve the missing raw-HTML mapping. The exact handling still must preserve whole-document semantics and supported extensions.

This explains why the approach was retained as a useful implementation basis while its “15 lines” and “100% exact” guarantees were rejected. It is an optional precise-preview technique, not a fixed dependency version, mandatory table AST, or prerequisite for saving/exporting a useful first version.

A DOM locator screenshot can be occluded or contain only the visible portion of a scrolling region. Report saved version, actual captured extent, dimensions, and location precision. Disjoint regions can be more useful than one large union rectangle. Whole-document semantics and crop completeness are separate concerns.

Keep normal reading conditions distinct from an expanded diagnostic view. Removing fixed heights, overflow, and sticky behavior or widening to `scrollWidth` can expose hidden content for diagnosis; it can also conceal a real defect in the ordinary user viewport. Record which conditions were changed. Desktop synchronized navigation means jumping to related source/output content, not promising row-for-row coordinate alignment between PDF layout and reflowed Markdown.

A review observation belongs to the version and source/scope actually examined. After an edit, determine whether the observation still applies to the changed content; do not automatically present an old review as a check of the current version. This traceability does not impose a universal preview count, visual gate, or extra model-call ritual.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1068, EVT-1107; ATT-21–ATT-29.

<a id="q1-closure-and-scenarios"></a>
## 9. Q1 closure and concrete contract scenarios

The following scenarios explain the decisions needed before implementation. They are not a newly queued benchmark matrix.

| Scenario | Required observable behavior |
|---|---|
| Correct body, invalid page-12 metadata | Preserve the original candidate and error. Repair page 12 against a named base while retaining page 13 and unchanged prose under explicit merge rules. Validate the complete result and return a version/receipt. |
| Insert a new complete paragraph | Express an insertion/append without inventing a removal target or regenerating the surrounding section. Larger reconstruction remains available when useful. |
| Save succeeded, result-field selection failed | Distinguish the successful commit from projection failure. Return/reconstruct its original receipt on recovery; do not make the model repeat the body. |
| Old candidate remains useful after a later save | Reuse the specified content. Do not reject it solely because another section committed more recently or because an ancestor once adopted another part. |
| Prepared version conflicts with a newer head | Preserve useful prepared files and return conflict/current facts. Do not silently rebase or roll the head backward. |
| Draft is stopped before full scope completion | Allow specified-version reading/preview/export with honest draft/gap labeling. Export consistency does not upgrade its content-completion claim. |

Q1 remains open until reference identity/applicability, insertion/edit ordering, omitted-field and nested merge behavior, target-match rules, base/head checking, commit visibility, and receipt/projection outcomes are unambiguous. A specific string-patch schema, table AST, lifecycle engine, malformed-JSON salvage system, or generalized branching facility is not needed to settle those boundaries. The preferred immutable-file/SQLite arrangement is a baseline to specify and implement; old outputs and the 228-check result are not acceptance of this new engine.

**Controlling scope:** EVT-1148 and EVT-1166. Historical mechanisms and examples remain explained locally so a developer can understand the tradeoff without reopening every proposal.
