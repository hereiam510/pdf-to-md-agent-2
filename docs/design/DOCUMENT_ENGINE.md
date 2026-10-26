# Document, evidence, and candidate engineering handoff

This guide explains document-side responsibilities, rationale, failure cases and considered Q1 options without the original chat export. [The implemented contracts](../CONTRACTS.md#implemented-first-version-contracts) now select Q1's schema and transitions; they supersede statements below that those choices remain open. Other example names and historical mechanisms retain their original status. [CURRENT_STATE](../CURRENT_STATE.md) records verification.

The active contract is [CONTRACTS](../CONTRACTS.md), and its unresolved choices are in [OPEN_QUESTIONS](../OPEN_QUESTIONS.md). [Execution and delivery](EXECUTION_AND_DELIVERY.md) owns durable requests, accepted batches, operation replay, cancellation, and packaging. [Context and evidence](CONTEXT_AND_EVIDENCE.md) owns selection, capacity, and history compaction. [Integration](INTEGRATION_AND_MODEL_BOUNDARY.md) owns protocol and framework wiring. The detailed late-source [reference record](../reference/03-documents-delivery-and-recovery.md) preserves rejected alternatives. [Local source material](../reference/sources/INDEX.md) is optional audit evidence.

The central observed problem involved a retained candidate containing correct `本文件`. Full page-map validation rejected the submission. Later regeneration produced `本文作`. Better storage cannot prove transcription correct. However, it can avoid forcing the model to rewrite already-correct prose to repair metadata. The same reasoning applies to a large table with one missing bold span: precise editing should preserve everything outside the selected change.

## Implemented editing and reuse behavior

The 2026-10-24 Q1 increment resolves two observed loss paths: an ordinary request could combine an older content base with the current expected head, and the desktop could combine a newly selected version ID with a draft copied from previously loaded content. These require different protections. A backend equality check cannot detect a frontend that labels old text with two matching new IDs.

The backend uses `mode="edit"` by default, requiring `base_version == expected_head`. `mode="rebuild"` explicitly permits a different saved or empty base while retaining the current-head commit check. The agent chooses either mode without a human approval gate; large replacements remain available. A conflict preserves the received candidate rather than choosing a new base automatically. Immutable prior versions remain readable and exportable.

The desktop groups the base version, expected head, mode and draft blocks in an edit session. Loaded content is separately identified by task and version, with loading/error/ready states. Switching selections hides an obsolete preview immediately; effect cleanup ignores late replies. A failed load cannot enable editing/export. Opening an editor freezes its version even if background polling later reports a newer head. A failed save retains the draft. Export uses the loaded immutable version and explicitly excludes unsaved edits. Historical editing is labeled as rebuilding; no automatic old-version-to-current-head substitution occurs.

For a local repair, suppose candidate `candidate:old-request:0` contains a correct second-page paragraph in `/operations/0/blocks`, followed by an unwanted delete. After a newer version `V2` is saved, the agent can submit:

```json
{
  "base_version": "V2",
  "expected_head": "V2",
  "operations": [{
    "kind": "insert",
    "after_id": "existing-section",
    "reuse_candidate": {"ref": "candidate:old-request:0", "pointer": "/operations/0/blocks"}
  }],
  "page_updates": {"2": {"printed": "none", "disposition": "included"}}
}
```

Only the referenced block content is copied. The old delete and rejected page metadata are not replayed. A `replace` operation accepts the same content reference with an explicit target `id`; either operation also accepts a pointer to a single Block. Ownership, candidate kind, pointer syntax and Block shape are checked before the normal merged-document validation and conditional commit. Literal `blocks` and `reuse_candidate` are mutually exclusive at that operation. Top-level reuse remains a whole-list replacement, so it should not be used for inserting a paragraph. Source strings are preserved without Unicode normalization or HTML reflow.

The document tests cover rejected metadata, retained candidates, later commits, local insert/replace, deliberate reconstruction, source images, reopen and byte-checked export. Controlled IPC tests cover delayed/failed/out-of-order reads and head advancement while editing; the full desktop fixture also rebuilds an older version and exports after restarting. These checks establish software/artifact behavior, not natural model adoption or universal source fidelity. [CONTRACTS Q1](../CONTRACTS.md#q1-document-schema-and-commit) is the exact current contract; the historical alternatives below retain their stated status.

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
| Task/scope state | User requirements, requested content, progress, issues, and completion claims | A task's `outside_scope` designation is not a permanent PDF fact. An unresolved task issue is not a permanent PDF fact either. |
| Operation receipt | The historical result of one accepted edit, selection, or other operation | It identifies what committed then, not what every pointer must equal now. |

The preferred body authority is the immutable version file payload. SQLite owns identity/registration, references or manifest hashes, selected pointers, uniqueness, and receipts. Avoid a second independently mutable full body in `blocks_json`. Updating that JSON without updating the files would create two incompatible answers to “what is V12?”. Updating only the files would cause the same conflict.

The app may rebuild derived indexes, but their relationship to the canonical payload must be explicit. Moving the body into SQLite would be a deliberate alternative design, not an incidental copy added for convenience.

An illustrative registration might contain `document_id`, `version_id`, `payload_ref`, `payload_hash`, `parent_version`, and `producing_operation_id`. This example is not a required table definition. A content hash checks byte equality. It does not establish the task, source, selected region, or intended operation. It also does not establish whether the model saw the content or whether a later version retains it.

The discussion called the mutable working pointer `document_head`, `working_version`, `working_version_id`, or `head_version_id` in different sketches. `selected_delivery` and `selected_delivery_version_id` named the separate delivery choice, sometimes carrying `scope_rev` and a draft/completion label. These are vocabulary variants, not several pointers that must all be implemented. The effective distinction is an immutable version versus a task's current work or selection. A pointer copied into a frozen request records what that request saw. That copy cannot become a second live authority.

Logical document blocks support readable structure and stable editing. Page markers must leave sentences and tables readable. This requirement does not make each table one indivisible database unit or one model submission. A 4,000-character table can remain a coherent output table while a cell or substring is internally addressable. Conversely, a block ID alone does not locate that content precisely in the source PDF.

**Source basis:** EVT-0855, EVT-0878, EVT-0942, EVT-1005, EVT-1040, EVT-1068, EVT-1147, EVT-1166. ATT-21–ATT-30 with the later corrections controlling.

<a id="evidence-and-exact-access"></a>
## 2. Evidence, precise access, and computation reuse

The implemented `read_document` full view is the immutable version envelope, not the `Edit` input schema. Its blocks are at `/content/blocks`; an optional exact-version index lists block and Markdown pointers, page associations and character/byte counts. Both direct first reads and full/raw access remain valid. Range endpoints select the chosen string/array; they do not slice an arbitrary root object. [The access contract](../CONTRACTS.md#exact-saved-document-and-evidence-access) defines root, pointer-target and requested-selection completeness separately. Returning every item in `/content/blocks` does not return the entire envelope, while returning the requested last block is still a fulfilled selection. These are storage/access facts, not conversion-quality claims.

Reading a narrower selection does not cancel an older full read or erase authored draft arguments. The [working-evidence contract](../CONTRACTS.md#working-evidence-feedback-and-optional-preview) exposes their actual input representations and exact release references. The agent may keep both, select another range, or submit an explicit context revision; the app does not infer relevance from size or a successful save.

Preserve complete evidence and expose exact first/full/raw/field/range/native-image access. A caller may request a useful field directly on its first call, or request the full result. A compact receipt or inventory can describe a result that did not fit into the current input. It is not an obligatory summary gate. State the actual returned content, omitted content, warnings, exact reread methods, and underlying saved identity. Keeping the original on disk does not prove the model received or understood it.

An evidence reference should resolve to an immutable result and an internal location. For example, the concept “evidence E, block `p14_b03`” can carry source PDF identity, page, coordinate system, and render/OCR parameters through E. Bare `p14_b03` is ambiguous after an engine change, crop, or recomputation.

`bbox_pixels` describes positions in a particular rendered image. `bbox_pdf` describes positions in PDF coordinates. A crop needs the correct transform and rendering context.

Do not demand a manually entered box for every word or cell. A page reference or agent-selected region is valid when only coarse location exists. One output block can have several source regions.

The illustrative `source_refs` item `{"evidence_id":"ev_004","item_pointer":"/pages/14/blocks/3"}` makes both parts visible. `evidence_id` fixes the retained result. `item_pointer` selects a location within its actual structure. A JSON pointer's array position is not itself a physical PDF page number. The referenced record supplies that meaning.

A previous `{page, from_inspect_block}` sketch lacked this durable evidence binding. Updating an observation or choosing a newer OCR result produces a new reference or observation. It does not rewrite the immutable result behind an existing reference.

The document core makes the same preserved evidence available to the built-in runtime, external MCP clients, and CLI. Only the built-in input assembler knows its complete model-input footprint. An MCP server can report its result's size and available projections. It cannot remove already-returned content from an external host's conversation or infer that host's remaining capacity. The external host can compact its own history. Content is not necessarily permanent merely because the server cannot alter it.

Text, words, layout, and font/position fields may overlap while carrying different evidence. Deduplicate avoidable serialization without declaring one fixed field set sufficient for every task. Full access remains available, and the agent chooses which representation is relevant. An OCR confidence score or a small text difference cannot establish that an image is dispensable.

<a id="historical-pdf-coordinates"></a>
### Historical PDF coordinates and OCR boxes

The old public tools numbered physical pages from one. A `region` was `[x0,y0,x1,y1]` in unrotated page points, with a top-left origin. One point represents 1/72 inch. This was the tool's MuPDF-style coordinate convention. Native PDF coordinates use a different origin, so the label “PDF points” alone is insufficient.

The region helper computed unrotated bounds as `page.rect * page.derotation_matrix`. It rejected nonfinite, empty or out-of-bounds rectangles. Rendering passed `region * page.rotation_matrix` as the clip to `get_pixmap`. The render receipt recorded the original region, DPI, pixel dimensions and source hash. It did not return OCR word boxes.

The OCR reader returned two rectangles for each recognized word:

| Field | Historical meaning |
|---|---|
| `bbox_pixels` | `[x,y,x+width,y+height]` within the cropped rendered image, using OCR TSV pixel positions. |
| `bbox_pdf` | The corresponding rectangle in the tool's unrotated page-point coordinate system. |

For that conversion, the reader transformed the crop into rotated page coordinates. It scaled by `dpi / 72` and used `.irect.tl` as the integer rectangle's top-left pixel origin. It added that origin to each OCR rectangle, scaled by `72 / dpi`, and applied `page.derotation_matrix`. Keeping crop origin, scale and rotation together prevents a crop-relative pixel box from pointing elsewhere on the PDF.

These are historical transforms, not a final rebuild coordinate schema. The evidence reference must retain the source, region and settings that make its coordinates interpretable.

**Source basis:** SUP-15, SUP-19 and EVT-0878. See PyMuPDF's [page-coordinate rules](https://pymupdf.readthedocs.io/en/latest/page.html) and [coordinate-system explanation](https://pymupdf.readthedocs.io/en/latest/app3.html#coordinates), checked 2026-10-23.

<a id="image-mode-and-encoding"></a>
### Image mode and encoding

The historical Pillow warning concerns retained pixels, color, transparency and bit depth. A blanket `convert("RGB")` can discard alpha or change a grayscale or one-bit representation. Do not silently apply this conversion to every crop. Choose a supported representation that preserves the relevant source properties. Report any format limitation instead of silently lowering fidelity.

New JPEG encoding can introduce lossy changes, even when the crop dimensions stay unchanged. Copying an existing native JPEG stream differs from decoding and recompressing it. A PNG extension alone does not prove native resolution or unchanged pixels. The [reference-input notes](../reference/REFERENCE_INPUTS.md) explain the historical crop and image-edit defects that motivate these checks. Pillow was a proposed component in that record, not a verified rebuild implementation. See SUP-04 for the retained warning.

<a id="historical-image-xrefs-and-masks"></a>
### Historical image references and masks

The old `inspect` returned displayed-image metadata from `get_image_info(xrefs=True)`. Its image list covered the page, even when a region clipped text, layout and words. An `xref` identifies a PDF object. Inline or unresolved images can have `xref=0`, so an image listing does not guarantee direct extraction.

`extract_image(document, page, xref)` first checked that the requested page displayed that reference. It then stored the encoded bytes returned by `Document.extract_image`, with encoding, dimensions and source provenance. Native JPEG bytes remained available where supported. Other encodings could require PyMuPDF's lossless reconstruction. This was not a promise that every visible figure occupied one image object.

The old extractor rejected an image when any of these mask checks matched:

- The extraction result contained a nonzero `smask` reference.
- A displayed occurrence reported `has-mask`.
- The PDF object's `ImageMask` entry was `true`, indicating a stencil mask.

A bare image stream can omit the transparency or composition needed for the page's appearance. The old fallback was a faithful page-region render. For delivery, `render_page(..., asset=True)` registered that render as artwork with `kind: "page_render"`. Its provenance distinguished rendered pixels from native extraction. This was the old application's policy. PyMuPDF also documents image-plus-mask composition, so region rendering is not the only technically possible implementation.

**Source basis:** SUP-15 and SUP-26. See PyMuPDF's [displayed-image metadata](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_image_info) and [mask composition](https://pymupdf.readthedocs.io/en/latest/recipes-images.html#how-to-handle-image-masks), checked 2026-10-23.

An optional computation index can reuse independently computed page/region results. The historical key proposal included source hash, tool/engine version, language-data hash, normalized parameters, and page/region. Overlapping requests could retrieve existing units. An explicit `force_recompute` could obtain a fresh result.

This does not require a separate file for every page, force cached results into model context, or prove cost savings. Suitability includes the method that produced the result, not merely whether its bytes still hash correctly. Computation reuse remains a performance option, not a V1 prerequisite.

**Source basis:** EVT-0855, EVT-0878, EVT-0968, EVT-1005, EVT-1068, EVT-1107. ATT-21/22/28/29. The [context guide](CONTEXT_AND_EVIDENCE.md) explains the global input-capacity boundary.

<a id="candidate-capture"></a>
## 3. Retention precedes validation

Use the following responsibility order, without assuming a single framework callback covers every stage:

1. The Nexus receiving layer preserves the native response and writing fragments that it actually receives. These include raw arguments that cannot form a valid decoded tool call.
2. The common dispatch boundary preserves app-received, decoded writing arguments before the domain schema can reject them.
3. Check the decoded call's tool/envelope and reference-input shape. A schema that supports references must admit those references. It must not require the caller to retransmit their full resolved body. Captured invalid arguments remain a candidate record with precise errors.
4. Resolve the exact candidate/content references and explicitly defined overrides against the named base. Preserve the received call separately from this complete effective submission. A repair is a new operation, not a mutation of the rejected original.
5. Apply the declared operations to a working copy. Validate the resulting complete document, page map, references, and assets under the draft contract. Checking only the patch or the reference envelope is insufficient. Represent unknown or incomplete task metadata honestly. Do not confuse it with invalid structural relationships.
6. Prepare immutable content. Conditionally commit according to the [visibility boundary](#commit-visibility). Only this step establishes the promised saved-version/pointer effects.
7. Return the operation outcome and model-facing projection. A projection failure after commit is not an unperformed write.

Saving only inside `DocumentService.save()` is too late if a framework rejects required metadata before entering that function. A wrapper's `args` may already be a parsed dictionary. It can preserve schema-invalid calls that it receives, but not necessarily malformed raw JSON. LangChain's `invalid_tool_calls` can bypass ordinary ToolNode dispatch. Native capture and pre-schema dispatch capture protect different rejection boundaries. Best-effort indexing is a later convenience, not the only retained copy.

<a id="framework-capture-order"></a>
### The framework rejection that motivated the capture boundary

In the reviewed LangChain path, `BaseTool._parse_input` applies the Pydantic `args_schema` before invoking the Python tool function. A missing required field or wrong metadata type can raise `ValidationError` before `DocumentService.save()` runs. The proposed outer `wrap_tool_call` hook can first retain the received `tool_call["args"]` dictionary. It can then let ordinary tool validation proceed.

That dictionary is already a decoded representation. An earlier JSON decoding failure can instead enter `AIMessage.invalid_tool_calls`. Normal ToolNode dispatch reads `AIMessage.tool_calls`. Those failed raw arguments therefore need the Nexus receiving path, independently of the wrapper. This describes the reviewed integration sequence. It neither requires the prebuilt agent nor assumes that private framework methods remain unchanged.

The proposed error fields were `error_code`, `field_errors`, `saved_candidate_ref`, and `recovery_hint`. Their useful division is a machine-readable rejection category, exact invalid locations, the content actually retained, and an actionable repair explanation. For example, a page-12 map error should identify that field. It should explain that a new repair can reference the saved body. It should not request the body again or imply that the service committed page 13's rejected metadata.

The names remain examples. If retention fails, report that distinct failure. Do not claim that a usable saved reference exists.

The same issue applies to MCP. The reviewed SDK validated registered-tool arguments before invoking the function. A permissive transport schema alone was not a complete remedy. The request could still have a wrong container or encounter rejection earlier. Weakening tool schemas also removes useful guidance.

The historical SDK 2.3.0 review found an `Extension.intercept_tool_call` hook before tool validation for an accepted `tools/call` request. Find the supported interception boundary in the actually selected version. Do not assume that the historical hook exists unchanged. A server cannot preserve arguments that the external client rejected before transmission. No local callback can guarantee storage of bytes never received. A callback also cannot guarantee storage when the disk write fails.

Return a stable reuse reference with validation errors. Explain whether body, metadata, assets, or target/base applicability failed. This lets the next action repair that part. Truly optional draft metadata should be optional in the draft contract. The service may still accept body and page changes in one atomic edit. Different validation responsibilities do not require two model calls.

This sequence distinguishes early call validation from validation of the resolved result. It does not prescribe one parser, a second permissive tool schema, or the final reference syntax. If reference resolution or raw-candidate indexing fails, report that limit. Retain the content that the app actually saved. Return a `candidate_ref` only after the app durably retains its backing content. Do not advertise “capture attempted” as successful preservation when storage failed.

**Source basis:** EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1107, EVT-1147. ATT-23–ATT-30.

<a id="candidate-reuse-and-lineage"></a>
## 4. Exact reuse, candidate lineage, and malformed originals

A candidate reference can conceptually be an immutable `candidate_id` plus JSON pointer, selected block list, or another exact location accepted by the chosen tool surface. The reference must identify the retained bytes/content, not a mutable “latest candidate.” Proposed forms such as `reuse_candidate_ref`, `block_ops_from_candidate`, `from_candidate`, `block_indices`, and `override_meta` are alternatives from the discussion, not jointly mandatory fields.

The later names `content_from_candidate` and `replay_ops_from_candidate` were meant to expose different intentions. An illustrative content item was `{"from_candidate":"cand_04","select":"/blocks/2","override_meta":{}}`. Another selected several items with `block_indices`. These forms retrieve content without regenerating it, with any metadata overrides governed by the eventual merge contract.

In contrast, `replay_ops_from_candidate="cand_05"` proposed reusing a whole operation sequence. The earlier `block_ops_from_candidate` spelling obscured that distinction because a list of edits is not merely a list of prose blocks. None of these spellings selects the final reference schema.

Separate two intentions:

| Intention | Meaning |
|---|---|
| Reuse content | Copy the exact selected prose/table/block into a new operation, with explicitly supplied applicable metadata. |
| Reuse an operation | Ask to perform the earlier append/delete/reorder/replace/patch sequence against an identified base after checking its current intent and applicability. |

A failed `save_draft` can contain a `blocks` array and no `block_ops`. A candidate's `block_ops` may delete or reorder unrelated content. Reusing a correct paragraph must not require executing those old effects. Replacing the base version also requires rechecking targets and expected text. Byte-identical operation arguments do not imply applicability to a different document state.

For nested repairs, define omission and replacement explicitly. If C contains page-12 and page-13 updates, a correction for page 12 must not silently erase page 13. Choose and document per-page upsert, whole-array replacement, and nested-field semantics. Preserve C, then save the new effective-argument snapshot and its parentage with a new operation identity. Changing the input of an existing accepted operation ID is an inconsistency, not an update.

Candidate usefulness cannot be inferred from creation time. Candidate A for the first section may still be needed after an unrelated second section commits. `active_unresolved`, `adopted`, `superseded`, and `abandoned` were proposed labels, but one global flag is insufficient for partial adoption or different task scopes. Adopting two of three blocks does not dispose of the third. A later candidate on the same page may cover different content. A small active-work reference set can represent current work without implementing a general lifecycle engine.

In particular, the proposed query `WHERE task_id = ? AND lifecycle_status = 'active_unresolved'` cannot describe which subitems a branch used. The later `version_candidate_links` sketch records `(candidate_id, item_pointer)` against the produced version instead. Its advantage is precise historical adoption, not automatic inference of current completion. The next paragraph's deletion example explains the limit. An ancestry query cannot replace current version content or active work state.

Version-to-candidate links record historical use. V10 may adopt a paragraph and V11 may delete it. V10's ancestry link remains true while V11 no longer contains the paragraph. Read current content from the specified version. Necessary unfinished work belongs to task state.

Do not require an explicit disposition report for every unused header/decorative fragment. Do not make all unadopted candidates a completion gate. General branching and a lineage UI are deferred options.

When a commit records adoption links, include the actual candidate/content locations used in that commit's metadata transaction. Otherwise a crash can register a version without its claimed provenance, or mark a candidate adopted when the version never committed. This requirement concerns the recorded relationship, not a compulsory lifecycle table or an instruction to adopt every available fragment.

<a id="candidate-repair-sequence"></a>
### Worked example: rejected body reused with a page-only repair

Suppose candidate C contains two paragraphs and page-map changes for physical pages 12 and 13. The prose includes correct `本文件`, but page 12's metadata is invalid. C's rejection has not committed those changes to base V10.

1. Retain C's original arguments and the page-12 validation error. The existing document remains V10. Do not claim C is a valid version merely because its body is readable.
2. The repair names V10, C, and the exact content to import. A reference into C's `blocks` selects prose. It does not implicitly execute a `delete` or `reorder` from another candidate field.
3. The repair supplies the page-12 correction and expresses the intended treatment of C's page-13 proposal. A content-only import does not silently inherit all rejected metadata. If the repair should retain page 13, it must explicitly import that metadata. Alternatively, it must use a declared whole-candidate merge contract that preserves it. Metadata already in V10 follows the ordinary omitted-field preservation rule.
4. Resolve C's selected content exactly. Assemble the effective submission. Keep C and the repair separately identifiable. Do not ask the model to regenerate the paragraphs. This complete-candidate case does not involve automatic malformed-JSON extraction.
5. Apply the body import and metadata changes to a working copy of V10. Validate the whole resulting map and structure, including relationships involving unchanged content. Validation succeeds for a coherent draft even when explicitly permitted facts remain unknown. It does not establish source fidelity or full-scope completion.
6. At commit, check the expected base/head again. If compatible, register the new version, the promised pointer changes, operation result, and actual adoption relations coherently. If the repair is stale or invalid, preserve C and the prepared repair. Report the conflict or error. Do not silently apply the repair to a newer head.
7. Return the new version's receipt. A retry of the same accepted operation returns that receipt. A later correction changes the effective input and receives a new operation identity.

The final Q1 schema still needs to distinguish two forms:

- Import selected candidate content with explicit new metadata.
- Reuse a broader candidate submission with declared merge/override rules.

Both forms can protect page 13. An undocumented mixture can erase it.

### Optional extraction from an incomplete call

The app retains raw malformed arguments regardless of whether automatic extraction exists. If added, exact extraction must satisfy these conditions:

- It must operate within one attempt and one call.
- It must preserve raw identity and span.
- It must understand strings, escapes, and structural closure.
- It must handle duplicate-key and array-order semantics.
- It must independently parse only fully closed original subobjects.

Do not add closure characters or synthesize fields. Do not merge attempts. Do not execute the failed original operation.

For the received text:

```text
{"blocks":[{"id":"b1","text":"A"},{"id":"b2","text":"B","page":
```

The original b1 object is closed. The b2 object is not closed. A tolerant parser may return b2 while dropping its unfinished `page`, or insert braces. That is a repaired interpretation, not evidence that b2 was received complete.

Exact extraction can expose b1 for a new validated operation. It still cannot establish correct source transcription. Report “complete subobjects extracted; remainder uncertain,” not “all early blocks are correct” or “only the last block needs regeneration.” Later ungenerated content may also be missing.

The reviewed examples were Pydantic's `allow_partial=True`, which returned b2's already-read fields, and LangChain's `parse_partial_json`, which can repair closure characters. These behaviors suit tolerant decoding. They are insufficient as the test for an exact original span. `salvaged_blocks` and `status: "salvaged_from_malformed_call"` were proposed index labels, not evidence that the original call became valid or a requirement to implement extraction in V1.

The historical 8,419-character incomplete-argument record arose during a streaming/service failure. It does not prove output-token truncation is the usual cause. Smaller saves/append/insert are available to the agent without a mandatory page/block cadence. Automatic malformed-call extraction is not a prerequisite for exact reuse of already-complete candidates.

**Source basis:** EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-27–ATT-30.

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

A proposed `edit_document(base_version, reuse_candidate_ref, block_ops, page_map_updates, provenance_updates, delivery_selection)` illustrated grouping these responsibilities. Another proposal separated `save_draft`, `edit_document`, and `select_delivery`. Tool count alone neither establishes a small schema nor reduces cognitive load. Choose the surface after specifying the behavior.

For an operation sequence:

1. Create one working copy.
2. Apply the declared sequence.
3. Validate the final merged result.
4. Commit one version. Define whether later block locators refer to the initial base or earlier operation results. Do not accidentally mix sequential block operations with simultaneous string-patch coordinates.

For patches aligned to one unchanged base, the discussion retained this option:

1. Resolve and verify all expected spans.
2. Reject overlaps and ambiguity.
3. Apply replacements from the greatest offset backward. This prevents an earlier replacement changing a later span's coordinates. Explicit sequential patches are another possible contract. Later anchors must intentionally refer to the intermediate state. Accidental creation or destruction of matches cannot choose semantics for the caller.

<a id="patch-preconditions-and-locator-fields"></a>
### Expected text and location are separate checks

The discussion cited RFC 6902's `test` because it checks an expected JSON value at a location before a later change proceeds. It does not define searching and replacing a substring inside Markdown. Our analogous precondition checks `expected_old_text` against the selected stored span at the named base. If it differs, reject the proposed patch. Do not search a newer version for something similar instead. The original `find_exact` / `replace_with` / `expected_matches` form makes a text search and count explicit, but `expected_matches: 1` is neither a source-correctness check nor a solution for deliberately repeated cells.

The locator proposals refined that search as follows. These are alternatives to specify under Q1, not a combined mandatory object:

| Discussed field or reference | Mechanical purpose and unresolved convention |
|---|---|
| `line_range: [start_line, end_line]` | Limit searching to raw stored lines. Define the line base, endpoint inclusivity, and newline convention. This edit-range proposal is separate from the parser's half-open source ranges described below. |
| `context_before`, `expected_old_text`, `context_after` | Match the target with surrounding stored text when the target value alone repeats. Context anchors still need explicit matching and ambiguity rules. |
| `occurrence_in_range` or a returned range reference | Select a particular verified match within the chosen range. A caller's explicit choice differs from silently defaulting to the first occurrence. |
| `replacement_text`, `new_text`, or `replace_with` | These are alternative names for the proposed replacement. They do not change the precondition or location semantics. |
| `table_cell_locator` or `cell_ref` | A table-aware convenience that resolves to an exact version-bound span. A read-only grid may expose `visual_row_span` / `visual_col_span` and raw HTML locations. Row/column coordinates must distinguish visual cells from stored elements. |

For example, a returned range for the second `12.4` on a raw HTML line can select that cell while `expected_old_text` guards against a stale read. Check every selected base span before applying a same-base patch set. Descending-offset replacement then preserves the remaining coordinates. The surrounding context may match twice, or an earlier sequential edit may change the intended cell. The contract must reject or deliberately resolve that condition. It must not silently choose a match.

Repeated cells make naïve matching unsafe. A table can contain many `0`, empty cells, `是`, or `12.4` values, including several on one raw line. `occurrence=1` must not silently select the first unless the caller deliberately chose that location. A returned cell/range reference, raw-line range plus expected text, or within-range position can provide precision.

Display wrapping is not stored newlines. A one-line HTML table defeats line number alone. Row 5/column 3 also needs a declared distinction between visual grid coordinates and stored cells when `rowspan`/`colspan` exist. A cell reference can be a convenience over generic patches without requiring a separate mandatory table AST.

Preserve source characters. JavaScript string positions use UTF-16 units while Python commonly exposes code-point positions. An interface needs an explicit counting convention and programmatic conversion. It must not require a model to hand-count an entire table.

The historical normalization check showed `U+2F800` becoming `U+4E3D` under NFC. That proves NFC is not universally lossless for source distinctions. Do not silently normalize glyphs, convert traditional/simplified Chinese, or fuzzy-match a correction.

An explicit LF version-storage rule remains possible. Preserve received originals. Define the mapping. Pretty-printed HTML and normalized search can be mapped read/edit views instead of rewriting canonical content.

Adding HTML whitespace can create text nodes and affect copying or parsing. A format-only change is therefore not automatically byte/behavior neutral. Likewise, the illustrative patch `<td>厲行節約</td>` to `<td><strong>礪行節約</strong></td>` changes both emphasis and a character. One exact match proves a unique target under that locator, not that the change agrees with the PDF. The app guarantees that it does not regenerate untouched content. Source-led judgment determines whether the selected edit is correct.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-1040, EVT-1068, EVT-1166. ATT-21–ATT-30.

<a id="historical-content-schema"></a>
### Historical Content and schema-version-1 records

The old `Content` model and save validator explain earlier validation failures. They are historical contracts, not the new Q1 schema.

| Record | Historical fields and constraints |
|---|---|
| `Content` | `title`, `language`, `scope`, `status`, `pages`, `blocks`, `uncertainties`, `limitations`, `metrics`. `title` and `scope` had minimum string length one. |
| Defaults | `language: "und"`, `status: "draft"`, empty `uncertainties` / `limitations` lists and an empty `metrics` dictionary. `status` accepted only `draft` or `complete`. |
| `Page` | `pdf_page` was an integer of at least one. `printed_page` defaulted to `unknown`. `disposition` accepted `in_scope`, `outside_scope` or `unprocessed`, defaulting to `unprocessed`. |
| `Block` | `id` matched `^[a-zA-Z0-9_-]+$`. Its `pages` list and `markdown` string each had minimum length one. `Content.blocks` also required at least one entry. |
| Model boundary | The common Pydantic base used `extra="forbid"`. The model rejected unknown fields. |
| Saved envelope | `schema_version: 1`, `document`, `version`, `parent_version`, `saved_at`, `source`, `content`, `assets`, `markdown`, `markdown_sha256`. `publication_operation` appeared only when supplied. |

`metrics` belonged inside `content`, not beside the snapshot's `markdown_sha256`. Its values could be strings, integers, floats or null. `markdown_sha256` hashed the assembled UTF-8 Markdown. `publication_operation` associated a saved version with its producing operation. These fields served different accounting, integrity and replay roles.

The save validator applied these additional checks:

1. The map contained every physical page exactly once. Duplicate and out-of-range entries failed.
2. Printed labels contained non-whitespace text and excluded angle brackets, carriage returns, line feeds and `|`.
3. Block IDs were unique. Each block's page list contained distinct references to `in_scope` pages.
4. Authored blocks omitted generated PDF page comments. Every `in_scope` page appeared in at least one block.
5. A `complete` submission failed if `uncertainties` was nonempty or any mapped page remained `unprocessed`.

That last check did not reject nonempty `limitations` or an `unknown` printed label by themselves. It also did not prove that every table, footnote or requested passage was correct. The broader scope and fidelity requirements still applied.

The optional top-level save argument `unmapped_disposition` accepted only `outside_scope` or `unprocessed`. It filled missing physical positions with that disposition and printed label `unknown`. It preserved supplied entries and body blocks, then applied the full validator. It did not infer labels or silently classify unfinished work as outside scope.

Q1 can change this record layout and update interface. The retained lessons are coherent source correspondence, exact body reuse, honest draft metadata and separate content-acceptance claims.

**Source basis:** SUP-06, SUP-15, SUP-16 and SUP-26. The later [page-map responsibilities](#page-maps-and-provenance) qualify the historical single-disposition model.

<a id="page-maps-and-provenance"></a>
## 6. Page maps, provenance, scope, and claims

Keep four responsibilities separate:

| Responsibility | Examples | Why it is separate |
|---|---|---|
| Source inventory and observations | Source identity, physical page order, observed printed label, blank-page observation, region evidence | The PDF can remain unchanged while a prior label reading is corrected. |
| Task scope | Requested pages, complete section, figure/table, explicit exclusions, scope revision | A partial-page task cannot be fully described by `target_pages=[12]`. |
| Output provenance | Which output blocks derive from which source pages/regions/evidence | Having one paragraph from a page does not account for its footnotes and tables. |
| Work/review claims | Drafting, known gaps, completed requested section, review tied to a version/scope | A complete structural map is not semantic acceptance. |

The Nursing example requested “Breasts and Figure 4–13,” physical page 12 / printed page 68, excluding adjacent content. That is a complete useful scope within one page. Completing it under task A does not complete task B's later full-page request. Retain useful prior content. Identify added or uncertain scope. This does not require universal rereview of every unchanged part.

Sparse updates and complete correspondence are compatible. A change for one page can merge into the named base. The service can construct the complete output map from source page count, task scope, and existing facts. Do not force resubmission of 173 entries for one correction. Validate the complete merged map rather than validating only the patch or silently treating absent entries as outside scope.

The exact per-page key and nested merge semantics remain open. A proposed `pdf_page` key expresses physical page identity. Keep `unknown` printed label distinct from `none`. `unknown` means the label is not determined. `none` means no printed label is present. Stable physical order remains available in both cases.

Source visibly blank, deliberately omitted decoration, unprocessed content, and outside this task are different observations/decisions. A copyright page can contain requested author, edition, ISBN, or other content and must not be automatically omitted.

The proposal names `source_page_inventory`, `block_provenance`, and `task_scope_and_claims` express those responsibilities. `printed_page` is an observation alongside physical `pdf_page`. `source_scope_note` describes a block's source boundary. `scope_id` / `scope_rev` and `page_coverage_claims` relate task claims to the selected `version_id`. A changed scope or corrected printed-label reading must not alter an earlier immutable version's evidence. These names aid interpretation of the discussion and leave the final record layout open.

Output page markers and structured mapping must express the same source relation. Physical pages are one-based positions in the particular PDF. Roman or other printed labels are observations from visible source content, not inferred viewer labels. If a block uses pages 12 and 14, a grouped marker must not imply that page 13 contributed. English HTML-comment labels can preserve correspondence without interrupting a sentence or table at an artificial page boundary. The product requirement and eventual document contract govern exact marker serialization, not a mandatory storage-block size.

Names such as `converted_full_page`, `converted_partial_scope`, `source_visibly_blank`, `omitted_non_content`, and `unprocessed/drafting` were proposed to improve expression, not to make the app an automatic semantic judge. “Every target page has a block or is marked blank/omitted” is too weak: a page can have a converted paragraph and a missing table. Completion binds effective scope and document version, with known material omissions/errors made explicit.

A draft may be saved, previewed, snapshotted, and exported with incomplete facts. A later `publish_version` or completion gate must not make useful drafts inaccessible. Export consistency, completion claim, and source review remain distinct records. Page mapping covers correspondence. It does not require body text on every input page.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-1040, EVT-1068, EVT-1166. ATT-21–ATT-30.

<a id="commit-visibility"></a>
## 7. File preparation, SQLite commit, and visibility

The recommended sequence is a staged immutable payload followed by a short conditional metadata transaction. It avoids claiming that SQLite also commits the filesystem or graph checkpoint.

1. Resolve the intended document, base, effective parameters, source/reference identities, and operation identity. Preserve resolved defaults for recovery.
2. Construct a working result without mutating the committed base. Validate that working result. Prepare the immutable body/assets. Verify that the required files are present and correspond to that result.
3. At the actual metadata commit boundary, check operation uniqueness and the expected base/head conditions. A prior check before parallel work is insufficient.
4. Commit version registration, the promised pointer changes, the producing operation's identity/outcome, and any actual adoption/provenance links coherently. The service rejects a same-ID/different-input submission.
5. Return the receipt and a model-facing projection. If projection fails, the commit remains a success that can be reconciled and returned again.
6. The graph records completion separately. Recovery reuses the committed result rather than repeating the edit.

This is a responsibility sequence, not a guarantee of universal power-loss durability. The selected filesystem/database settings and visibility rules still need implementation decisions. “Atomically replace one file” does not atomically publish a directory's assets, update another file, and checkpoint graph state.

The commit-as-receipt proposal usefully embeds an operation identity in a version or metadata record. It does not make folder existence equal to successful save. The old order moved a version folder and then updated `current.json`. A crash could leave useful prepared content without the working head advancing. If save promises registration and head advance together, define that effect in the metadata transaction. Alternatively, explicitly expose separate API operations.

For example, A prepares V11 from V10, then another legitimate operation advances the head to V12. Recovery of A follows its recorded state:

- If A already committed, return its historical receipt and keep V12 current.
- If A has only a complete prepared result and its expected base/target still holds, finish the originally defined conditional commit.
- If that base/target no longer holds, preserve the prepared V11 content and report conflict. Do not silently overwrite V12 or reinterpret A as an edit against V12.

The same rule applies with one active writer after restart: durable later facts can outlive an old graph checkpoint. An in-memory lock is not a durable uniqueness guarantee. Two individually serialized SQLite writes also do not resolve concurrent graph policy updates. Each authority needs its own defined writer.

Do not delete unreferenced attempt/version files simply because they are not registered or no process currently runs. They may be the only recoverable correct work. A first version can avoid background cleanup. A generalized lease/garbage-collection system is not required. Started/unknown/completed execution facts for scripts or model calls cannot be replaced by successful document-version metadata alone.

**Source basis:** EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-25–ATT-30.

<a id="historical-windows-publication"></a>
### Historical Windows replacement behavior

The historical JSON readers used `CreateFileW` with READ/WRITE/DELETE sharing. Existing-file publication used `ReplaceFileW`. In that Windows environment, `os.replace` / `MoveFileEx` failed against an open reader. Selected native sharing/access failures received eight attempts, with under one second of total retry delay. These included observed error 1175. Persistent failures still surfaced.

<a id="historical-json-write-and-read"></a>
#### Historical JSON write sequence and retry limits

The old `write_json` helper used this sequence:

1. Create a sibling temporary file named `.{name}-{uuid}.tmp`.
2. Serialize UTF-8 JSON with `ensure_ascii=False`, two-space indentation and a final LF. Use LF newline handling.
3. Flush the Python stream. Then call `os.fsync(stream.fileno())`.
4. Close the stream. Then call the replacement helper.
5. Delete any remaining temporary file in `finally`.

The helper did not fsync the parent directory. File fsync alone did not establish durable directory replacement or a transaction across several files. Its temporary-file cleanup was not a policy for deleting useful unregistered document versions.

| Windows operation | Historical eligible native errors | Bound |
|---|---|---|
| Replacement | `{5, 32, 33, 1175}` | Eight total attempts. Other errors or the final failure propagated. |
| Opening a shared read handle | `{2, 5, 32, 33}` | Eight total attempts. Error 2 could occur during the brief name transition. |

The [Win32 error reference](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-) names the shared codes:

- `2`: `ERROR_FILE_NOT_FOUND`.
- `5`: `ERROR_ACCESS_DENIED`.
- `32`: `ERROR_SHARING_VIOLATION`.
- `33`: `ERROR_LOCK_VIOLATION`.

After an eligible failure, both loops used `min(0.01 * 2**attempt, 0.16)` seconds, with zero-based `attempt`. Seven possible sleeps totaled at most 0.63 seconds. This excluded operation duration and scheduling delays. A persistent missing file, lock or permission failure still surfaced after the bounded attempts.

The Windows reader requested `GENERIC_READ` with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`. It retained that handle while parsing JSON. The non-Windows path used an ordinary binary read. These native error allowlists were implementation details, not general retry categories for every operating system.

**Source basis:** SUP-17. The following error-state distinctions qualify the historical replacement allowlist.

Microsoft documents distinct failure states for these errors:

| Error | Documented state | Historical retry policy |
|---|---|---|
| 1175 / `ERROR_UNABLE_TO_REMOVE_REPLACED` | The destination cannot be deleted. Both files retain their original names. | Eligible for bounded replacement retry. |
| 1176 / `ERROR_UNABLE_TO_MOVE_REPLACEMENT` | The replacement cannot be renamed. With a backup name, both files retain original names. Without one, the destination no longer exists. | Excluded from replacement retry. |
| 1177 / `ERROR_UNABLE_TO_MOVE_REPLACEMENT_2` | The replacement retains its name but inherits destination streams and attributes. The old destination has another name, using the backup name when supplied. | Excluded from replacement retry. |

The 1176 outcome depends on the backup argument. Thus, partial mutation is not a universal explanation for both excluded errors. The retained names for 1175 do not establish complete metadata rollback, eventual success or crash durability. The bounded allowlist was a historical implementation choice.

Readers with an open snapshot handle retained the complete old or new JSON. New readers also retried brief native name-transition errors. This mechanism avoided in-place JSON truncation. The rebuild still needs its own filesystem and visibility choices within the staged-file and metadata-commit contract.

**Source basis:** SUP-08 and SUP-09. The conditional error descriptions follow [Microsoft's `ReplaceFileW` documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew), checked 2026-10-23.

<a id="rendering-and-preview"></a>
## 8. Rendering, reading, and precise comparison

Source rendering and output preview use different identities. Source render needs PDF identity, physical page, region, DPI, and related parameters and must work before a draft exists. Output preview uses a saved document version and view parameters. Rendering a candidate may be a separate convenience. Requiring a document version for source rendering would obstruct the agent's first source read.

Comparison can provide independent native images, separate crops, or an explicitly chosen montage. Keep source pixels unmodified, with labels/dividers outside them and enough surrounding context to interpret the crop. A route's processor may still resize two native images. Neither 300–400 DPI nor a 900×350 crop guarantees model-side resolution. More DPI cannot recover detail missing from a scan. The historical proposal that 24×24 glyphs became 12×12 after joining pages was a possible scaling mechanism, not a diagnosed cause of old emphasis errors.

Render the complete Markdown document with its supported CommonMark/extensions before locating output regions. Separate block rendering changes semantics. For example:

```markdown
See [source][r].

[r]: https://example.com
```

The reference link resolves when the definition is in the same parsed document. Rendering the first content block alone can lose the definition. Parsing together still does not enable a footnote extension absent from configuration.

Parser token/source-line information may help produce app-owned DOM anchors. It is not automatically a one-block/one-element map: tokens can span content-block boundaries and one block can produce several DOM regions. Raw HTML needs explicit handling. The historical parser returned an `html_block`'s raw `token.content`, ignoring attributes attached only to the parser token. A `data-block-id` wrapper/attribute proposal therefore was not a complete 15-line mapping engine. Sanitization and allowed app-generated markers must preserve the intended rendering and security boundary without rewriting source content casually.

<a id="preview-content-and-resource-boundary"></a>
### Saved content and preview resources

Preview sanitization must not rewrite saved Markdown or delete its page-marker comments. The sanitized display is a derived view. This requirement does not require every HTML comment to remain in the rendered DOM. Preserve the canonical Markdown and its correspondence data independently of display cleanup. Keep required table spans, emphasis and notation readable.

Bind preview document assets to the selected immutable version. Load those assets from registered local bytes. Block external resource requests and source-provided active content. A link in the document is not permission to fetch its target automatically. Report unavailable resources instead of substituting mutable workspace files or remote content.

The old Playwright view froze the saved HTML and image bytes before rendering. It fulfilled a virtual origin through local routing, without a listening HTTP server. It blocked all other requests and disabled page scripts, service workers and downloads. This mechanism made the preview reproducible and prevented source content from contacting external services. See SUP-05 for the historical mechanism and SUP-04 for the saved-comment rule. A future Electron renderer needs its own verification of this boundary.

<a id="commonmark-emphasis-and-language"></a>
### CommonMark emphasis and preview language

The old renderer used `MarkdownIt("commonmark", {"html": True})` with the table extension enabled. CommonMark 0.31.2 decides whether `**` opens or closes emphasis from adjacent whitespace and Unicode punctuation. CJK punctuation is subject to those rules. Its presence does not make every adjacent delimiter invalid.

For example, applying those rules to `文字**「重點」**文字` leaves the intended delimiters literal. The opening pair follows a letter and precedes punctuation. The closing pair follows punctuation and precedes a letter. These boundaries cannot open and close strong emphasis as intended.

The historical guidance allowed `文字<strong>「重點」</strong>文字` when delimiter boundaries were ambiguous. This preserves the characters and makes the intended span explicit. Check meaningful emphasis in the actual saved reading when the formatting question warrants it. This guidance does not require automatic text rewriting, parser replacement or a preview of every page.

The optional `content.language` defaulted to `und`. The old model accepted the tag pattern `^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$`, without checking a language registry. For example, `zh-Hant` became the escaped HTML `lang` value. It did not translate source text or select OCR languages. The renderer's language metadata and the OCR request's language configuration were separate inputs.

**Source basis:** SUP-16, SUP-18 and SUP-26. The delimiter example follows [CommonMark 0.31.2's flanking rules](https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis), checked 2026-10-23.

<a id="historical-preview-parameters"></a>
### Historical preview parameters and observations

The old `view_preview` selected a saved version and used these defaults:

| Parameter | Historical default and validation |
|---|---|
| `width` / `height` | 1200 / 900. Positive integers, excluding booleans. |
| `scroll_y` | 0. A nonnegative integer, excluding booleans. |
| `full_page` | `false`. A full-page request with nonzero `scroll_y` failed. |

The result recorded `version`, `preview_sha256`, `viewport` and `requested_scroll_y`. It separately reported actual `scroll_y`, `document_width` and `document_height`. Each `images` entry represented a DOM image and included `file`, `loaded`, `natural_width`, `natural_height`, `displayed_width` and `displayed_height`. Natural dimensions described the image data. Displayed dimensions came from the image element's width and height.

Those records described this HTML view, not coverage of every source-PDF figure. A failed image load produced a warning.

The code set `page.set_default_timeout(15000)`. This covered methods that accept a timeout setting, not every browser operation. The historical notes described a 30-second launch default, but the code passed no explicit launch timeout. The current official launch reference gives 180000 milliseconds. Therefore, the old 30-second note is not a verified current default or a rebuild setting. Evaluation waits and cleanup do not acquire a global deadline from the page setting.

**Source basis:** SUP-05, SUP-09 and SUP-27. See Playwright's [page timeout scope](https://playwright.dev/python/docs/api/class-page#page-set-default-timeout) and [launch timeout](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-option-timeout), checked 2026-10-23.

<a id="historical-preview-worker-lifetime"></a>
### Historical preview worker lifetime

The old preview used a dedicated synchronous worker thread. That worker owned Playwright creation, browser calls and cleanup. The caller waited for the worker, then checked pending cancellation before recording success. A failed or cancelled preview preserved the saved document version.

Playwright supports both synchronous and asynchronous APIs. Its documentation identifies cancellation of an `asyncio` task during a Playwright call as unsupported, with undefined behavior. Its threading guidance calls for a separate Playwright instance per thread. These limits explain the historical lifecycle choice. They do not establish a browser-pipe failure diagnosis or prohibit the asynchronous API.

AnyIO's default worker wait shields cancellation. Setting `abandon_on_cancel=True` instead lets the caller stop waiting while the thread continues. The historical code retained the worker through cleanup. This arrangement delayed cancellation delivery. It did not forcefully stop the browser or guarantee one global timeout for all browser operations.

The rebuild must define its renderer's cancellation and cleanup lifecycle. The historical worker arrangement is an implementation example, not a mandatory Electron or Python threading design.

**Source basis:** SUP-08 and SUP-09. See [Playwright's API, threading and cancellation guidance](https://playwright.dev/python/docs/library) and [AnyIO's worker-thread cancellation behavior](https://anyio.readthedocs.io/en/stable/threads.html), checked 2026-10-23.

<a id="parser-source-map-mechanics"></a>
### How the proposed source-line map would locate output

The `markdown-it-py` proposal first assembles the exact whole Markdown version. It records each source block's half-open `[start_line, end_line)` interval, including the effects of separators inserted during assembly. It then parses that whole string once.

A core rule can compare each top-level token's `token.map` source interval with the recorded block intervals and associate eligible rendered regions with `data-block-id`. Multiple output elements may share one block ID. A token crossing block boundaries needs a many-to-many mapping rather than an arbitrary single owner. The mapping is to this assembled version's source lines, not PDF coordinates or editor visual wrapping.

For ordinary rendered tokens, adding an attribute may be sufficient for an appropriate renderer. In the reviewed raw-HTML path, `token.attrSet("data-block-id", "blk_01")` does not change the emitted `<table>` because the `html_block` renderer returns `token.content` directly. Explicit handling during serialization or carefully chosen containers is therefore needed for raw HTML. The `nh3` sanitization proposal would allow the intended app-generated marker on the relevant elements. Merely adding a token attribute or widening the allowlist cannot solve the missing raw-HTML mapping. The exact handling still must preserve whole-document semantics and supported extensions.

This explains why the review retained the approach as a useful implementation basis. The review rejected its “15 lines” and “100% exact” guarantees. It is an optional precise-preview technique, not a fixed dependency version, mandatory table AST, or prerequisite for saving/exporting a useful first version.

A DOM locator screenshot can be occluded or contain only the visible portion of a scrolling region. Report saved version, actual captured extent, dimensions, and location precision. Disjoint regions can be more useful than one large union rectangle. Whole-document semantics and crop completeness are separate concerns.

Keep normal reading conditions distinct from an expanded diagnostic view. Removing fixed heights, overflow, and sticky behavior or widening to `scrollWidth` can expose hidden content for diagnosis. These changes can also conceal a real defect in the ordinary user viewport. Record the changed conditions. Desktop synchronized navigation means jumping to related source/output content, not promising row-for-row coordinate alignment between PDF layout and reflowed Markdown.

A review observation belongs to the version and source/scope actually examined. After an edit, determine whether the observation still applies to the changed content. Do not automatically present an old review as a check of the current version. This traceability does not impose a universal preview count, visual gate, or extra model-call ritual.

**Source basis:** EVT-0855, EVT-0878, EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1068, EVT-1107. ATT-21–ATT-29.

<a id="q1-closure-and-scenarios"></a>
## 9. Q1 closure and concrete contract scenarios

The following scenarios explain the decisions needed before implementation. They are not a newly queued benchmark matrix.

| Scenario | Required observable behavior |
|---|---|
| Correct body, invalid page-12 metadata | Preserve the original candidate and error. Repair page 12 against a named base while retaining page 13 and unchanged prose under explicit merge rules. Validate the complete result and return a version/receipt. |
| Insert a new complete paragraph | Express an insertion/append without inventing a removal target or regenerating the surrounding section. Larger reconstruction remains available when useful. |
| Save succeeded, result-field selection failed | Distinguish the successful commit from projection failure. Return or reconstruct its original receipt on recovery. Do not make the model repeat the body. |
| Old candidate remains useful after a later save | Reuse the specified content. Do not reject it solely because another section committed more recently or because an ancestor once adopted another part. |
| Prepared version conflicts with a newer head | Preserve useful prepared files and return conflict/current facts. Do not silently rebase or roll the head backward. |
| Draft is stopped before full scope completion | Allow specified-version reading/preview/export with honest draft/gap labeling. Export consistency does not upgrade its content-completion claim. |

Q1 remains open until these matters are unambiguous:

- Reference identity and applicability.
- Insertion and edit ordering.
- Omitted-field and nested merge behavior.
- Target-match rules and base/head checking.
- Commit visibility and receipt/projection outcomes. A specific string-patch schema, table AST, lifecycle engine, malformed-JSON salvage system, or generalized branching facility is not needed to settle those boundaries. The preferred immutable-file/SQLite arrangement is a baseline to specify and implement. Old outputs and the 228-check result are not acceptance of this new engine.

**Controlling scope:** EVT-1148 and EVT-1166. Historical mechanisms and examples remain explained locally so a developer can understand the tradeoff without reopening every proposal.
