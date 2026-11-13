# Document, evidence, and candidate engineering handoff

This guide explains document-side responsibilities, rationale, failure cases and considered Q1 options without the original chat export. [The topic contracts](../INDEX.md#initial-contract-basis) now select Q1's schema and transitions; they supersede statements below that those choices remain open. Other example names and historical mechanisms retain their original status. [implementation evidence](../history/IMPLEMENTATION_HISTORY.md) records verification.

The active contract is [topic contracts](../INDEX.md#initial-contract-basis); [initial contract decisions](../decisions/INITIAL_CONTRACTS.md) records how Q1–Q3 were closed and the limits of that closure. It is not a current unresolved-design queue. [Execution and delivery](EXECUTION_AND_DELIVERY.md) owns durable requests, accepted batches, operation replay, cancellation, and packaging. [Context and evidence](CONTEXT_AND_EVIDENCE.md) owns selection, capacity, and history compaction. [Integration](INTEGRATION_AND_MODEL_BOUNDARY.md) owns protocol and framework wiring. The detailed late-source [reference record](../history/discussions/20261031_0157_REBUILD_DELIVERY.md) preserves rejected alternatives. [Local source material](../sources/rebuild/INDEX.md) is optional audit evidence.

The central observed problem involved a retained candidate containing correct `本文件`. Full page-map validation rejected the submission. Later regeneration produced `本文作`. Better storage cannot prove transcription correct. However, it can avoid forcing the model to rewrite already-correct prose to repair metadata. The same reasoning applies to a large table with one missing bold span: precise editing should preserve everything outside the selected change.

## Current page-marker serialization

Q1's data/commit choices are closed. The current [Documents.markdown implementation](../../src/pdfmd/documents.py) projects each saved block's physical `pages` and the corresponding page-map `printed` strings into an English comment before the exact block Markdown. It joins physical page numbers with `, ` and renders printed mappings as `physical=label`. For example, pages `[5, 6]` with printed labels `iii` and `iv` produce:

```markdown
<!-- PDF pages: 5, 6 | printed pages: 5=iii, 6=iv -->
```

The implementation places two line feeds between the comment and block content and between block pieces, with a final line feed for nonempty output. `none` and `unknown` remain distinct saved printed-label strings; this projection does not infer a printed page or prove source fidelity. [The earlier singular/plural page-comment examples](../PRODUCT_REQUIREMENTS.md#page-identity-and-logical-structure) retain their illustrative status and do not impose an exclusive input grammar. This section records current output and its relationship to the selected [Q1 page map](../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit); it does not change the serializer or product requirement.

## Guide navigation

Read the relevant mechanism below with [current contracts](../INDEX.md#initial-contract-basis) and [current verification](../INDEX.md#find-by-topic). Historical alternatives and original implementation-order proposals retain their stated status.

<details>
<summary>Sections in this guide</summary>

- [Current page-marker serialization](#current-page-marker-serialization)
- [Implemented editing and reuse behavior](#implemented-editing-and-reuse-behavior)
- [1. Identities and canonical data](#1-identities-and-canonical-data)
- [2. Evidence, precise access, and computation reuse](#2-evidence-precise-access-and-computation-reuse)
- [3. Retention precedes validation](#3-retention-precedes-validation)
- [4. Exact reuse, candidate lineage, and malformed originals](#4-exact-reuse-candidate-lineage-and-malformed-originals)
- [5. Edit semantics, locators, and character fidelity](#5-edit-semantics-locators-and-character-fidelity)
- [6. Page maps, provenance, scope, and claims](#6-page-maps-provenance-scope-and-claims)
- [7. File preparation, SQLite commit, and visibility](#7-file-preparation-sqlite-commit-and-visibility)
- [8. Rendering, reading, and precise comparison](#8-rendering-reading-and-precise-comparison)
- [9. Q1 closure and concrete contract scenarios](#9-q1-closure-and-concrete-contract-scenarios)

</details>

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

The document tests cover rejected metadata, retained candidates, later commits, local insert/replace, deliberate reconstruction, source images, reopen and byte-checked export. Controlled IPC tests cover delayed/failed/out-of-order reads and head advancement while editing; the full desktop fixture also rebuilds an older version and exports after restarting. These checks establish software/artifact behavior, not natural model adoption or universal source fidelity. [CONTRACTS Q1](../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit) is the exact current contract; the historical alternatives below retain their stated status.

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

The implemented `read_document` full view is the immutable version envelope, not the `Edit` input schema. Its blocks are at `/content/blocks`; an optional exact-version index lists block and Markdown pointers, page associations and character/byte counts. Both direct first reads and full/raw access remain valid. Range endpoints select the chosen string/array; they do not slice an arbitrary root object. [The access contract](../design/DOCUMENT_MODEL.md#exact-saved-document-and-evidence-access) defines root, pointer-target and requested-selection completeness separately. Returning every item in `/content/blocks` does not return the entire envelope, while returning the requested last block is still a fulfilled selection. These are storage/access facts, not conversion-quality claims.

Reading a narrower selection does not cancel an older full read or erase authored draft arguments. The [working-evidence contract](../design/DOCUMENT_MODEL.md#working-evidence-feedback-and-optional-preview) exposes their actual input representations and exact release references. The agent may keep both, select another range, or submit an explicit context revision; the app does not infer relevance from size or a successful save.

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

### Image mode and encoding

The historical Pillow warning concerns retained pixels, color, transparency and bit depth. A blanket `convert("RGB")` can discard alpha or change a grayscale or one-bit representation. Do not silently apply this conversion to every crop. Choose a supported representation that preserves the relevant source properties. Report any format limitation instead of silently lowering fidelity.

New JPEG encoding can introduce lossy changes, even when the crop dimensions stay unchanged. Copying an existing native JPEG stream differs from decoding and recompressing it. A PNG extension alone does not prove native resolution or unchanged pixels. The [reference-input notes](../sources/REFERENCE_INPUTS.md) explain the historical crop and image-edit defects that motivate these checks. Pillow was a proposed component in that record, not a verified rebuild implementation. See SUP-04 for the retained warning.

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

### Implemented unique-directory preparation (2026-10-31)

`Documents.edit` now exclusively creates `versions/<new-UUID>/` and prepares its immutable JSON, Markdown, HTML, assets, originals and manifest there. Each file uses exclusive creation and is flushed, fsynced and closed before the existing short SQLite transaction. That transaction checks the operation identity and expected head, then registers the version, advances head and records the original success together. Readers first require a task-owned catalog version record and verify its hashes; they never infer visibility by enumerating directories. The desktop version/preview endpoint and exporter use that same record gate. Directory existence therefore remains preparation, including when its name is the eventual version ID.

The preceding implementation prepared `.prepared-<UUID>/` and renamed that directory before the transaction. Repeated real synthetic saves failed at that extra Windows rename boundary. A controlled Windows read handle with read/write sharing but no delete sharing reproduces `WinError 5` through the actual edit path. Removing the rename lets that save, subsequent edit, reopen and export succeed while the handles remain open. This identifies a sufficient failure mechanism; it does not establish which process caused the historical refusals or whether they affected Nursing.

A file-write failure, transaction rollback or stale head leaves useful unregistered files in place and does not publish a version. A UUID-directory collision refuses without overwriting. A committed operation replays its original receipt without changing a later head. No cleanup, backoff, automatic effect replay, compatibility migration or filesystem/database joint transaction was introduced. Other write/permission/storage failures and power-loss limits remain; catalog publication is not a promise that all filesystems always succeed. [The scoped checks](../verification/20261031_2220_VERSION_PUBLICATION.md#execution-results) retain failures, corrections and saved/reopened/exported evidence.

Applicable official guidance checked for the existing Python 3.12 implementation: [flush/fsync](https://docs.python.org/3.12/library/os.html#os.fsync), [rename behavior](https://docs.python.org/3.12/library/os.html#os.rename), [SQLite transactions](https://docs.python.org/3.12/library/sqlite3.html#transaction-control), and Windows [CreateFile sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew). In particular, Windows delete sharing also governs rename access. The existing explicit Store transaction lifecycle is unchanged; LangGraph, Pydantic and dependency versions are unchanged.

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

### Shared asset-reference interpretation and selected-version view

The [asset design](../design/ASSET_REFERENCES.md#reference-interpretation-and-destination-policy) owns the rules. [Original T2 evidence](../batches/R01CAL-A03-DELIVERY-01/verification.md#t2-reference-and-selected-version-implementation) retains the preceding data-URL implementation and AR-T2-01 failure. [Protocol verification](../batches/R01CAL-A03-DELIVERY-01/verification.md#ar-s43-t2-protocol-implementation-and-verification) owns current observations and limits. The following mechanism implements the [scoped preview contract](../design/ASSET_REFERENCES.md#preview-binding-and-return-behavior); new enriched saves and writer-dependent integration remain outside T2.

`analyze(blocks, pages)` returns an `Analysis` with role-aware `Reference` records, structured issues and sanitized HTML. Parser-owned wrappers around the existing link, image and definition rules record successful destination-helper reads. The effective reference-definition entry carries its controlling span; first-definition-wins remains the pinned parser's rule. A use retains its own block/role separately from the definition's `SourceSpan`. Thus a definition shared by images and hyperlinks has one editable destination without falsely locating that destination in the use block. Image alternative-text children do not create extra dependencies. Ordinary external autolinks remain unrelated; reserved asset-handle autolinks reject because replacing only their destination with a relative URI would stop being an autolink. The feedback directs the caller to an inline/reference link or supported HTML attribute, preserving the original candidate. Parser instances and helper hooks are local to the call; upstream modules are not monkeypatched.

An HTML token scanner records raw attribute-value spans and duplicates before sanitization. It uses standard-library HTML parsing plus the token's raw tag spelling, not a second Markdown grammar. The complete rendered resource multiset is checked against nh3's HTML5 sanitization, and nested anchors are rejected because repair can preserve destinations while changing their label association. Duplicate `src`/`href`, unsupported image-resource forms and rendering disagreements become explicit issues. Source code/examples/comments remain literal. Input handles survive parser interpretation before the sanitizer removes their schemes; source-provided data/file URLs never become allowed display bindings.

`asset_uri(path)` returns the canonical uppercase UTF-8 percent-encoded destination for an exact registered path. `classify(destination, role)` separates URI components, validates escapes, decodes once using strict UTF-8, and returns `asset`, `handle`, `unrelated` or `invalid`. It performs no filesystem lookup. `+` stays literal, decoded ampersands never become query separators, and `%252F` denotes a literal `%2F` basename substring. Namespace spelling/case and separators are not aliases. Reserved local variants fail; ordinary external citations and fragment links add no local dependency.

`dependencies(analysis, registered, handles=None)` returns a path-to-reference-list union or raises `ReferenceError` with a structured issue. Registration is supplied by the caller's explicit task/base mapping, not discovered from another task. An optional handle mapping supports preparation only: Enriched creation must allocate identities/paths, call `rewrite`, reanalyze, then call final dependency validation **without** unresolved handles before publication. Unknown handles and unregistered targets fail. This helper does not allocate, enrich, publish or validate provider content.

`rewrite(blocks, pages, analysis, replacements)` copies the working blocks, guards exact expected source text, deduplicates controlling spans, rejects overlaps, and applies edits in descending offsets. Replacements are serialized canonical destinations. It then reparses the complete result and compares every operative destination, role and use-block identity with the intended bindings. Labels, titles, whitespace, inactive definitions and identical literal prose/code remain outside the edits. T3b and T4 own candidate retention, ordinary-operation ordering and atomic publication around this helper. The schema 1 save (`Documents.edit`) now collects through this resolver, implementing the [portable-link save increment](../design/ASSET_REFERENCES.md#portable-link-save-increment). It analyzes the merged working document, rejects an unresolved input handle, then calls `dependencies` with the task's registered source paths. Embeds and local image hyperlinks therefore both enter `assets`, together with each asset's associated `originals`, under existing hash paths. `source_registrations` groups registrations by `asset_path`, because hash paths can be shared: the latest non-diagnostic registration supplies a path, and a path backed only by registrations whose metadata `purpose` is `saved-output diagnostic preview` is rejected as a source deliverable. Reference validation reports the offending destination and role, the block when an exact span is available, and the retained candidate. Every display file and associated original is read and integrity-checked before the version directory is prepared. A failed object-file read identifies the referencing destination, role and block and says whether the display file or a retained original failed. A missing original-stream record fails the same way, without exposing an internal reference. The message gives the recovery: repeat the same `render_page` or `extract_image` call, then retry the retained candidate. Recovery works because objects are content-addressed under `objects/<sha256>`. `Store.blob` skips the write only when the existing object has the expected size and SHA-256. A missing, unreadable or corrupt object, including same-length corruption, is rewritten: the regenerated bytes are staged in a temporary file, the stage is verified, and `os.replace` swaps it in. A failed stage leaves the existing object unchanged. Identical regenerated evidence therefore restores the shared address and registers under the same asset path, while evidence made with different settings gets a new path that the edit must reference. The duplicate-write check hashes an existing object in full, a cost relevant to [R11](../WORK_ITEMS.md#runtime-and-engineering-inventory). The [storage recovery review](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3a-storage-recovery-review) records same-hash recovery and the remaining staging and concurrent-repair failures. The resolver is stricter than the former embed-only HTML scan: unsupported resource markup or an operative reference without a guarded span now rejects the save instead of being ignored. `classify` still applies strict percent-escape and UTF-8 rules to every image source and every destination with an `assets` path component, judged on a lenient decode so escaped separators still count. A hyperlink with a malformed escape and no `assets` component, such as `appendix/100%-coverage.md`, stays an unrelated citation.

`Documents.selected` loads one registered task/version and retains the same byte buffers it hashes. It binds preview resources from those verified version files, without reading task blobs, consulting head or regenerating an image. `assess` checks the content/Markdown relationship, version policy, referenced inventory, declared originals and applicable occurrence representation relationships. Unknown policies or failed analysis report `unavailable`; known missing dependencies report `incomplete`. Registered-file corruption or missing bytes fail the integrity gate first. A missing historical inventory entry is never filled from a still-present task blob. The response check is derived metadata; `Documents.export` still publishes only the exact verified selected member buffers, and the host response adds a live check without writing it into a stored receipt or package.

In schema 2, two independent extraction refs can describe the same original PDF stream. The selected inventory accounts for each declaration when the path exists, the registered digest matches both the declaration and the member, and the complete recorded stream provenance agrees. The distinct evidence refs and placement facts remain in the occurrence records. Schema 1 uses its recorded original ref. See the [shared-original assessment check](../batches/R01CAL-A03-DELIVERY-01/verification.md#ar-t4-02-correction).

The transient binder rewrites parsed attributes after source sanitization. Missing/unverified targets lose navigation; missing images retain alternative text and an unavailable indication. `Documents.selected` emits only referenced, verified PNG/JPEG buffers in `preview_transfer`, with task/version identity, asset/representation key, MIME, byte length and SHA-256. Repeated references share a payload. Other registered files and task blobs are not resource routes. The sanitized HTML contains inert binding keys and guarded attribute slots; slots use UTF-16 code units for JavaScript, whereas canonical block `SourceSpan` offsets remain Unicode code points. This distinction preserves bindings after astral source characters.

Electron main's `PreviewResources` verifies the complete transfer, replaces only the supplied parsed attribute slots, and prepares one immutable table under an unpredictable lease. A separate main-frame IPC activation must match the latest job/version/load generation. The renderer receives derived HTML and identity, without payload buffers, paths to host files or authority to register resources. A preparation error returns a matching preview-unavailable message while retaining raw Markdown, the independent reference assessment and exact export. No partial resource set becomes active.

Before app readiness, `main.ts` registers the standard/secure/CORS-enabled `pdfmd-preview` scheme, leaving CSP bypass, Fetch API and service-worker privileges disabled. The actual window session uses `protocol.handle` to return full PNG/JPEG response bodies with validated MIME, Content-Length, no-store and nosniff. The parent permits this scheme for frame/image loads because srcdoc inherits its CSP; the derived document permits it for images. Source sanitizer schemes remain unchanged. The iframe keeps `sandbox=""`, and Node access, parent DOM access, permissions, windows, downloads and external navigation remain denied.

The protocol callback has no caller-frame identity. `onBeforeRequest` and `onBeforeSendHeaders` require the owning webContents and the unique direct child preview frame, matching the active lease, the explicitly registered mount name and stable `frameTreeNodeId`. `SavedPreview` registers a new unpredictable mount identity through main-frame IPC before creating each iframe. Return/tab remounts retire the old frame guard while keeping the same resource table; old unmount cleanup cannot revoke the newer mount. A new frame is registered only from its app-created srcdoc. A private one-use request-header grant carries that checked context to the protocol callback, which consumes it and rechecks the active lease/frame/exact URL. Missing context, main/foreign frames, other windows/sessions, forged URLs and revoked leases cannot obtain bytes. Native frame navigation accepts only an issued image in that registered frame; redirects are denied. No filesystem, head, task-blob or network fallback exists.

`useDocumentSession` creates a fresh generation for every load/retry and activates only the matching prepared response. Starting another selection revokes the old table; late results and old cleanup cannot revive or revoke a newer lease. Pending/failed loads, editor entry, renderer loss and window destruction release resources. Editor entry retains the verified saved content for explicit-version export while the draft remains unsaved; save/discard starts a fresh preview load rather than reviving its revoked addresses. An explicit old selection stays pinned across head advance; default-follow-head loads a new generation when it actually selects another version. Export feedback also carries generation identity so a late result cannot appear under a same-version retry.

Image navigation, output-tab changes and Return remounts retain the loaded snapshot's lease. Return increments only the frame revision and restores cached matching HTML; it adds no version read, save or inference. A new srcdoc frame reestablishes the host frame guard using the same in-memory image table. Relaunch loads verified bytes under new transient addresses. No protocol URL, binding key or lease is written into canonical Markdown, HTML, manifests, receipts or ZIP members. The existing export path continues to use the explicitly loaded immutable version, including while viewing an image after head advance. Complete byte transfer adds no image-size/count quota, resampling, recompression or format change.

### Enriched creation path (T3b)

The [versioned schema](../design/ASSET_REFERENCES.md#versioned-data-and-embedded-schema), [edit API](../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics) and [enriched save flow](../design/ASSET_REFERENCES.md#enriched-save-flow) own the rules. The [T3b first-increment evidence](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-first-increment-enriched-creation) owns observations and limits. This section explains the mechanism.

Normal request preparation sends the [conversion system instructions](../../src/pdfmd/context.py) with the [evidence-tool definitions](../../src/pdfmd/tools.py). Both point to enriched creation. The tool result's `ref` identifies the evidence for the create, and the resulting edit receipt supplies the occurrence ID and the URI for the named delivery image. The agent can reuse the ID for later edits. The system and tool text changes apply to newly prepared normal requests under the existing [frozen-request rules](../design/RUNTIME_AND_DELIVERY.md#recovery-boundaries).

**When a save is schema 2.** `Documents.edit` takes the enriched path, `_save_enriched`, when the edit has `asset_changes`, supplies `source_update`, or builds on a schema 2 base. Otherwise the schema 1 hash-path save above is unchanged. On the enriched path, `page_updates` follow `asset_catalog.page_patch`:
- a `printed` value without a state is read as `unknown`, `none` or known;
- a changed known or none label needs `printed_basis`;
- an untouched legacy label keeps its null state and becomes an `i` locator with a `legacy_hint`.

A schema 1 hash path becomes a schema 2 occurrence only through a create's `legacy_path`. Every operative reference to it is then rewritten. An unadopted hash path fails with `ASSET_NOT_OWNED` and adoption guidance.

Both save paths use `dependencies` to check supported markup and classify operative destinations before giving handle guidance. A malformed handle gets the accepted spelling and key syntax. A valid `asset:new/<client_key>` without a matching create gets the exact key and `facts.image_ref` guidance. A valid `asset:id/<occurrence_id>` without a matching occurrence gets advice to use an ID from the selected schema 2 base or create a new occurrence. The rejection identifies the offending destination and retains the candidate for repair. See the [edit API](../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics) for the handle rules.

**Facts and eligibility.** `schema.py` defines `EvidencePointer`, `TextFact`, `Description`, `Location`, `LocatorGroup`, `OccurrenceFacts`, `AssetCreate` and `SourceFactsPatch`, each rejecting unknown fields. `asset_catalog.validate_occurrence` checks:
- every evidence pointer, through `check_pointers`, names an existing evidence-kind record of this task (`evidence`, `image`, `image_stream`, `tool_result`, `source_pdf` or `document_view`; not a candidate or enriched copy). A pointer's page and region must agree with what that record's metadata establishes: an image's `page` and render `region`, or an inspection's `pages`. The same check runs on merged `source_facts` and on page-label `printed_basis` and alternatives before any preparation;
- each location agrees with the image's recorded derivation. A location on another page is accepted only as a repeated occurrence whose basis cites separate evidence recorded from that page; a location region on the image's page must overlap the image's recorded region. Caption and bibliographic pointers are checked against their own evidence, not forced to the image page;
- the image is an `image` blob with a registered deliverable, not a diagnostic preview;
- the image is either a MuPDF PNG (render, decoded extract or rendered occurrence) or an unchanged `embedded_stream` JPEG whose `original_bytes_equal` is true;
- declared pages exist and coordinates lie inside the source PDF's unrotated page frame;
- locator groups cover the contributing pages exactly, in first-contribution order.

`SourceFactsPatch` rejects an explicit null for any field: omission keeps the base value, while a complete `TextFact` (state `unknown` clears a fact) or an empty list replaces it. `validate_source` checks the merged source before preparation. A base saved with an invalid fact therefore fails with the field to repair (`source_update.<field>`), and a valid patch repairs it.

Omitted groups become singles. A range needs consecutive pages and a basis. It may not mix printed and fallback labels, and numeric printed labels must be continuous. The [single-occurrence correction](#single-occurrence-correction), [shared printed-page correction](#shared-printed-page-correction) and [shared source correction](#shared-source-correction) apply the same validation to the merged facts.

**Names.** `asset_naming.build` assembles `description-locator[-figure][suffix].ext`. It flattens controls, applies the nine full-width substitutions, trims leading whitespace and trailing whitespace or dots from the label, and falls back to `image` for an empty label. It adds `image-` before a reserved device name, normalizes to NFC with the pinned `unicodedata2==17.0.0`, and checks 180 UTF-8 bytes. On overflow, `NameBudgetError.details` gives the maximum, fixed-component bytes, suffix bytes and remaining description bytes. The label is never shortened.

`comparison_key` is `NFC(fold(NFC(name)))`. The fold uses the C and F entries of the bundled `data/CaseFolding-17.0.0.txt` (licence in `data/unicode-LICENSE.txt`), never `str.casefold`. Full-width and ASCII forms stay distinct, so `（2）` and ` (2)` are different names.

**Reservations.** `Documents._reserve` writes one `asset_name` record per `sha256([job, comparison policy, key])`. The record is `pending` for an unresolved operation, `assigned` after publication, or `released` after a settled failure. A name is free when there is no record or it was released. It is the occurrence's own when the record is assigned to that occurrence, or pending under the same operation. Otherwise the next suffix is tried, starting at 2.

The `asset_preparation` record keyed by operation stores occurrence and representation IDs under the create's `client_key` or a correction key derived from the occurrence ID. In the same transaction that claims a name, it also stores that request's allocation `{name, collision, rid}`. A resumed operation reclaims that allocation, even if a lower-numbered slot has since been released, so the name-bearing enriched bytes stay identical to anything already staged. A competing owner causes `OPERATION_CONFLICT`. Publication rechecks head and reservation ownership in the same SQLite transaction that registers the version, promotes the names to `assigned`, links the committed preparation and records the receipt.

**Across threads and engine processes.** The HTTP edit handler and agent runtime hold the per-task file lock across dispatch. A simultaneous HTTP edit of that task receives a conflict, and a retry after release can recover its original receipt. Name claims and preparation lookup and insertion use SQLite write transactions. A second operation sees the earlier pending claim and takes the next suffix. The [published-suffix check](../batches/R01CAL-A03-DELIVERY-01/verification.md#ar-10-published-suffix-verification) shows the published name keeping its assigned suffix and a later save reusing the released name. Attempts of the same operation share its preparation IDs and recheck its recorded reservation before claiming a name.

**Receipt ownership.** The Dispatcher checks for a settled edit in the same transaction that creates a start record. Document preparation and publication recheck that receipt before mutating state. A late attempt reuses a committed edit's receipt and leaves its preparation link intact. On failure, the Dispatcher stages the error bytes and uses one transaction to check for an existing receipt, attach the failure result and release every pending name of the operation if failure settles first. If success already committed, the failure attempt projects the original receipt. A failure that settles first blocks later publication for the same operation. Direct `Documents.edit` callers own their operation settlement and use `_release` for preparation cleanup by default. The [two-process reproductions](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-receipt-and-preparation-correction) exercise both orderings through the Dispatcher.

**Records and enrichment.** `provenance_record` builds the exact design record, with locations carrying the shared page-map label snapshot. `record_json` serializes it with sorted keys and no insignificant whitespace, JSON-escaping U+FFFE and U+FFFF. `xmp_values` derives `dc:title` (the known image title, otherwise the derived label), an English-labelled `dc:description` with caption, description, citation fields and positions, and `dc:source` = `urn:sha256:<source>`. Language entries are added when the description's language is not `und`.

`asset_catalog.enrich_object` calls `xmp_worker.prepare_object`, which invokes the product-selected `primary_xmp.py` in a bounded child process. The writer is byte-identical to the qualified candidate (SHA-256 pinned by `SELECTED_XMP_SHA256` and a test). The engine relaunches itself as the worker using `--xmp-prepare` in the frozen executable (dispatched in `tools/build/engine-entry.py`) or `python -I -B -m pdfmd.xmp_worker` in development, with `PYTHON*` variables removed.

**Process lifetime.** On Windows the engine creates a kill-on-close Job (`EngineJob`) and keeps its only handle. The worker is started suspended (`CREATE_SUSPENDED`), assigned to the Job and only then resumed (`NtResumeProcess`), so it and any process it starts run inside the Job. That includes the interpreter behind a venv `python.exe` launcher. The worker also waits for a one-byte stdin gate, which the engine opens after assignment. If the wall limit expires, the engine terminates the Job. If the engine itself dies, its handle closes and Windows kills the worker. On POSIX the worker applies address-space and CPU rlimits after the gate; this fallback is untested and has no engine-death guarantee.

**Budget.** CPU is 5 s of job user time and wall time is 15 s. Memory is sized from the encoded image bytes the writer receives: `memory_budget(n) = max(256 MiB, 64 MiB + 8 × n)`, with a 2 GiB ceiling. The measured PNG peak is about 13 MiB + 5 × n. An input whose budget exceeds the ceiling (about 248 MiB) is rejected as `over_budget` before launch, with a suggestion to deliver a smaller representation. The engine records the Job's peak memory, charged user and kernel CPU, and queue time for every attempt.

**Writer pool.** `xmp_worker.pool()` uses a lock to create one pool on first use in each engine process. Its capacity is `clamp(30% of physical RAM, 1.5 GiB, 8 GiB)` with at most `max(1, logical CPUs − 1)` running workers. The pool admits workers in arrival order, reserving each worker's full memory limit until it finishes. CPU and wall limits start after admission. An image whose budget exceeds the host's pool receives `over_budget` before an attempt folder is created, with the pool size named. `Documents._prepare_images` submits pending representations concurrently and returns results in request order. A resumed operation reuses an intact `enriched:<representation_id>` blob.

**Streaming.** `Store.verify_object` hashes an object in 1 MiB chunks. `Store.copy_object` uses chunks to copy and verify images and originals for worker inputs and version files. The worker's verified SHA-256 is passed to `Store.blob_from_file`, which checks it during registration and verifies the staged copy against the same digest. A mismatch yields `ASSET_INTEGRITY_FAILED` and retains the attempt and candidate. `Store.head` reads the prefix for the image-type check. `_write_version` writes JSON, Markdown, HTML and the manifest from memory in both schemas. The page-frame check opens the verified source PDF by path.

**Saved-version reads.** `Documents.version`, used to load an edit base, reads the envelope into memory and streams integrity checks for every other registered member, including assets and originals the edit removes. It verifies task and version identity before returning the envelope. Selected preview and export request the verified file bytes. See the [fresh-save measurements](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-streaming-and-writer-pool) and [cold-pool, base-edit and registration checks](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-streaming-and-writer-pool-correction).

**Attempts and classification.** Each launch writes into its own `attempt-<time>-<id>/` folder under `<store>/preparation/<sha256(operation)[:24]>/<representation_id>/`. The folder holds the input, values, report, output and stdout/stderr. Success removes only that attempt, and the representation folder once it is empty. Earlier failed or interrupted attempts survive a successful retry.

The engine decides the exit status and timeout first, then parses the report defensively:
- a timeout or any exit other than 0 or 2 is `process_failed`. When stderr shows `MemoryError` or the accounting reaches a limit, the message names the limit (memory, CPU or wall);
- exit 2 needs a valid rejection report carrying the candidate's stage and code; anything else is `invalid_report`;
- exit 0 needs a valid accepted report and an output file, otherwise `invalid_report`, and hashes that match, otherwise `output_mismatch`.

Each of these becomes `ASSET_ENRICHMENT_FAILED` with the raw files kept; the operation's names are released and head does not move. An existing XMP packet with very many nodes can need far more than the image size suggests: a 14.3 MiB JPEG with 15 MiB of tiny nodes peaked at 1.1 GiB and 24 s of CPU. Such inputs are rejected with an explicit memory-limit message rather than sized for. A test compares the worker's output with the CLI output byte for byte. The [lifecycle and budget evidence](../batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-writer-lifecycle-and-budget-correction) records the checks.

The enriched bytes are stored as an `enriched_image` blob keyed `enriched:<representation_id>`. Its metadata says `deliverable_path`, not `asset_path`, so schema 1 hash-path collection never sees it. A retry yields identical bytes because the record has no timestamps.

**Publication.** Handles `asset:new/<client_key>` and `asset:id/<occurrence_id>`, and adopted legacy paths, are resolved with `dependencies(..., handles=...)`. They are then patched with `rewrite`, and the result is reanalyzed and resolved again without handles. The envelope adds `asset_policy`, `source_facts` and `asset_catalog`. The catalog keeps unreferenced occurrences so their names and identities survive. `assets` lists only the final dependency union, with `occurrence_id`, `representation_id`, the enriched `ref` and `sha256`, and the record. Each declared original is read, checked against its recorded SHA-256 and copied under its existing `originals/` path. `_enriched_bytes` reads each enriched deliverable. If its content-addressed object is missing or corrupt, it restores the object from any saved version's hash-verified copy of the same bytes, recording an `enriched_object_restored` event. Re-extracting source evidence cannot rebuild enriched bytes. With no verified copy left, the error names the file and the destination, role and block, and directs a new create. A failed original names its `originals/` path and the `extract_image` repetition that restores identical stream bytes; a missing original record directs a new create. The edit result adds `asset_changes` with the exact path, encoded URI, IDs and enriched hash.

Rejections raise `AssetEditError`. The Dispatcher adds its `error_code` and `issues` to the failed tool result, keeping the readable `error` and `candidate_ref`. `POST /jobs/{job}/edit` accepts an `Idempotency-Key` header (1–128 of ASCII letters, digits and `._:-`), mapped to operation `manual:<job>:<key>`. The Dispatcher's `candidate:` and `result:` records use store-wide keys, so the task scope lets two tasks use the same key independently. The same task, key and arguments replay the original receipt, including after a newer head. The desktop keeps a `submissionKey` (a random UUID) in each edit session. It renews the key whenever the draft changes and sends `desktop:<key>` through the main-process `edit` call as the header, so resubmitting an unchanged draft after a lost response recovers the original receipt.

<a id="commonmark-emphasis-and-language"></a>
### Single-occurrence correction

To correct an occurrence, add an `asset_changes` item with `kind: "correct"`, the occurrence ID from the selected schema 2 base, and the complete replacement value of each supplied fact. The engine validates the merged occurrence against task-owned evidence and allocates a new representation for changed facts under the same occurrence ID. An unchanged fact set reuses the existing representation when shared facts also stay the same. If the new naming inputs still produce the currently assigned name with its existing suffix, the allocator starts from that suffix.

The preparation pass embeds the updated record into bytes from the pre-enrichment evidence. The reference interpreter maps the old canonical path to the new path and rewrites operative embeds, hyperlinks and their controlling definitions. Code literals keep their original text. The new catalog, version members, head and receipt use the shared publication transaction under the per-task lock. The receipt returns the previous and current paths. The [T4 evidence](../batches/R01CAL-A03-DELIVERY-01/verification.md#t4-single-occurrence-correction) shows reopen, export and replay of a rename alongside its earlier snapshot.

### Multiple occurrence corrections

An edit can include one explicit correction for each distinct occurrence. A repeated occurrence ID rejects the edit before preparation, even when its first item leaves its facts unchanged. Shared page and source changes use the same preparation request for an explicitly corrected occurrence, so its new representation carries the merged occurrence facts and the final shared facts. The save publishes the affected representations and references in one version. The [T4-B checks](../batches/R01CAL-A03-DELIVERY-01/verification.md#t4-b-multiple-occurrence-corrections) cover both kinds of shared patch and an unaffected placement of the same picture.

### Shared printed-page correction

On a schema 2 edit, `page_updates` merges an evidenced printed observation into the selected base's page map. The engine compares that map against the embedded printed observations in the full occurrence catalog. It schedules new representations for every affected occurrence, including occurrences without a current destination. A matching explicit occurrence correction contributes its merged facts to the same preparation. Naming, source evidence validation and guarded destination rewriting use the single-occurrence path.

The writer prepares each representation before the common save transaction publishes the page map, catalog, referenced files and receipt. Failure settlement releases all pending names from that edit while retaining the candidate and staged data. Only referenced files enter the new version's delivery inventory. A later edit can link to an unreferenced occurrence by ID and reuse its corrected representation. See the [rollback, linking and replay evidence](../batches/R01CAL-A03-DELIVERY-01/verification.md#t4-shared-printed-page-correction).

### Shared source correction

On an edit of a schema 2 base, `source_update` replaces the supplied editable source fields. For example, `source_update.title` takes a complete text fact with the visible title and its evidence. The engine validates the merged source record and its pointers before preparing any image. It compares the validated record against each catalog occurrence's embedded source facts, including occurrences with no current destination. An equivalent patch reuses the existing representations.

The same preparation and save transaction as [shared printed-page correction](#shared-printed-page-correction) publishes fresh representations and the new source facts together. The filenames, suffixes and operative destinations for a source-only correction stay the same. The occurrence IDs and pre-enrichment evidence remain stable. The structured record and readable XMP description carry the corrected source title, and `dc:title` carries the separate image title. A failed preparation leaves the previous source facts and selected version available. See the [source correction verification](../batches/R01CAL-A03-DELIVERY-01/verification.md#t4-a-shared-source-correction).

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

The historical Q1 discussion required the following matters to be unambiguous. They are now selected in [implemented Q1](../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit); retain this list as closure rationale and review criteria, not work to reselect:

- Reference identity and applicability.
- Insertion and edit ordering.
- Omitted-field and nested merge behavior.
- Target-match rules and base/head checking.
- Commit visibility and receipt/projection outcomes. A specific string-patch schema, table AST, lifecycle engine, malformed-JSON salvage system, or generalized branching facility is not needed to settle those boundaries. The preferred immutable-file/SQLite arrangement is a baseline to specify and implement. Old outputs and the 228-check result are not acceptance of this new engine.

**Controlling scope:** EVT-1148 and EVT-1166. Historical mechanisms and examples remain explained locally so a developer can understand the tradeoff without reopening every proposal.
