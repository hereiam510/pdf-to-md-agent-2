# Document model, editing and precise evidence access

## Basis for this revision

**Design identity:** Existing implemented contract; no separate historical design revision ID was recorded. This 2026-10-31 organization does not change adopted meaning, reset acceptance or create a newly adopted design revision. HEAD `ba8bad3` plus pre-existing uncommitted implementation is the entry worktree; see [current state](../CURRENT_STATE.md) for actual source/check identities and limits.

- **Applicable shared rules:** [requirements, captured edition](../history/contracts/20261031_0157_PRODUCT_REQUIREMENTS.md#acceptance-and-cost), [architecture, captured edition](../history/contracts/20261031_0157_ARCHITECTURE.md#responsibilities), and [preceding shared contract](../history/contracts/20261031_0157_CONTRACTS.md#q1-document-schema-and-commit). Current topic rules below retain that edition's effective guarantees; today's global owners are reached through [the contract navigator](../CONTRACTS.md).
- **Choices and reasons:** [applicable decision entry](../decisions/REBUILD.md#established-rebuild-decisions) and [supporting discussion / contract closure](../decisions/INITIAL_CONTRACTS.md#q1-document-update-and-candidate-reference-contract). The detailed rule sections retain additional supporting entries; carried-forward choices remain applicable.
- **Verification:** adoption and local mechanism checks do not establish real-route compatibility, full fourteen-page fidelity or installed-product readiness. Follow the specific evidence entries below and [current verification](../CURRENT_STATE.md#verification-basis).

## Preserved source edition

The [entry source edition](../../docs/history/contracts/20261031_0157_CONTRACTS.md) preserves the preceding combined owner, its original statements and links to captured shared rules. Capture time `20261031_0157` is not a reconstructed older adoption time. Earlier version identities/snapshots unavailable in the records remain unclaimed. Later substantive changes must retain a version list and exact basis; unrelated cosmetic edits need no new version.

## 1. Document updates and candidate references

### Identity and original content

Keep source identities, derived evidence identities, received candidate identities, committed document versions and operation identities distinct. A content hash establishes byte identity, not ownership, scope, whether the agent saw the data, or whether it remains in the current document. An unqualified path, mutable `head`, timestamp or hash alone must not ambiguously select a source/version.

Preserve complete received native responses/tool arguments before framework parsing or tool schema validation can discard useful content. An accepted response and an executable tool call are later states. Framework tool middleware may run after native JSON parsing. Malformed calls may never reach that middleware. Retention therefore begins in the Nexus receiving layer, with dispatch-layer retention as an additional boundary.

Preserve what was actually received. Do not claim missing trailing content was saved. A rejected or incomplete call remains non-executable. A candidate reference identifies exact original content and its source operation/version/range. A repaired new request has its own identity.

### Edits and validation

The first version should support exact reuse of complete candidate content, pure insertion/append and partial page-map updates. Preserve unchanged body and metadata by default.

Apply a local metadata patch in this sequence:

1. Merge it into the explicitly named base version.
2. Validate the resulting complete map/structure.
3. Conditionally commit against the expected head.

A stale base must not silently become today's latest version. Do not require the model to regenerate all prose or resend a full map merely to repair one entry.

A referenced prior candidate is usable even if a later save exists. Adoption in an ancestor records historical use, not proof that every part survives in the current version. Unused candidate material need not all be adopted or explicitly rejected before a task can complete.

Distinguish reusing content from replaying operations. A `block_ops` object can delete/reorder/replace content. Copying its prose differs from executing that operation sequence against a changed base. Operations need applicability checks against the intended base. Literal patching must have defined target and match semantics. Unique byte matching prevents ambiguous replacement but does not establish semantic correctness.

The agent can choose a larger reconstruction when the source requires it. Local-edit support is an ergonomic capability, not a mandate to use the smallest edit. Logical output blocks do not dictate a token/chunk/storage size or require a complex semantic dependency graph.

### Commit and replay

Recommended body authority: immutable version files. SQLite owns version registration, head/pointers and the unique operation receipt. Stage the file payload. Validate it before the metadata commit that makes it visible. Define cleanup/reconciliation for files without a committed registration. Do not maintain a second independently mutable body as an equal authority.

Operation retries return the original committed receipt and its produced version. A newer head does not invalidate that receipt and must not be rewound. A receipt describes the historical operation. It is not a fresh selection/update of the current document. Validation rejection, successful commit and failure to build/return a model-facing projection are distinguishable outcomes.

No memory-only lock is a durable uniqueness guarantee. The first version uses one active writer per task plus persistent operation identity and short metadata transactions. SQLite ordering does not automatically serialize parallel graph-state `Command` updates. Graph policy updates must have a defined single writer.

### Partial-content salvage boundary

Preserving malformed originals is required. Automatically indexing complete subobjects from an incomplete response is a deferred useful option, not a first-version dependency. If added, automatic indexing must satisfy these conditions:

- Identify closed exact source spans within one attempt/call.
- Handle escapes, duplicate keys and array order.
- Preserve the original hash/span.
- Create a new valid operation for reuse.

Tolerant parsing that closes strings/braces, synthesizes defaults or merges attempts is not proof of a complete original subobject. Extractability is not source correctness.


### Q1: document schema and commit

`schema.py` defines `Document` with `title`, `scope`, ordered `blocks`, a complete physical-page `pages` map, `claim` (`partial` or `complete`), and `known_gaps`. Each block has a stable task-local `id`, exact `markdown`, physical `pages`, and optional `source_note`. Each page has `printed`, `disposition`, and `note`. Disposition is `unprocessed`, `included`, `outside_scope`, or `omitted_non_content`. Printed labels remain strings; `unknown` and `none` have different meanings.

`edit_document` requires `base_version` and `expected_head`. The base supplies content; the expected head is the commit precondition. Default `mode="edit"` requires both identifiers to match, including null/null for an initial document. A mismatched ordinary edit fails with repair guidance and retains its candidate. The agent may explicitly choose `mode="rebuild"` to start from another task-owned saved version or a null (empty) base. This requires no separate human approval and imposes no reconstruction-size limit. Both modes still compare `expected_head` with the actual head inside the commit transaction. A stale expected head fails without silently rebasing or overwriting newer work. The saved document envelope records `edit_mode`, `parent` (the content base), and `expected_head`; the receipt also identifies the mode. These establish the requested operation, not semantic correctness.

Omitted content and metadata remain unchanged relative to the named base. `replace_blocks` replaces the full ordered list; top-level `reuse_candidate` copies a block list at a task-owned candidate's RFC 6901 JSON Pointer. These alternatives cannot be combined. Neither replays the candidate's old operation.

Sequential `operations` support `insert` after an existing ID (null means beginning), `replace`, `delete`, and `patch`. Each insert/replace supplies exactly one non-null content source: `blocks` or `reuse_candidate: {ref, pointer}`. A local candidate pointer selects one `Block` or a list of `Block` objects, such as `/operations/0/blocks` or `/operations/0/blocks/0`. The resolver checks task ownership, candidate kind, pointer syntax and block schema. It copies only those blocks, without importing other operations or rejected metadata. Existing target, unique block ID, page and asset checks still apply to the merged result. Candidates remain reusable after later versions are saved. Invalid inputs retain their new candidate and leave head unchanged. An empty block list is allowed as an explicit operation, not mistaken for a missing content source.

Patch offsets are zero-based, half-open Unicode code-point positions in the current block after earlier operations in this request. `expected` must match exactly. `page_updates` merges only supplied page fields before validating the entire result. The tool schema exposes the page fields, disposition values, edit modes and candidate-content choices to the model.

Every accepted call's raw argument string is retained as `candidate:<request>:<call-index>` before domain validation. Reuse works after rejection or a later save. The full native response is retained earlier, before native parsing. Invalid and truncated calls remain non-executable.

The document core writes immutable version files, flushes them, then commits the version registration, head and original operation receipt in one SQLite transaction. Unregistered prepared/version directories remain preserved but invisible; there is no automatic destructive cleanup. A replay returns its original receipt/version without rewinding a newer head. The whole Markdown document is parsed together, so cross-block references and footnotes can resolve. Preview sanitization does not rewrite saved Markdown. Image links must name registered local assets; version files and exports preserve those bytes.

`complete` is an agent content claim with structural checks: no known gaps or unprocessed pages, output provenance for included pages, and a note for outside-scope/non-content pages. These checks cannot establish source fidelity. Partial versions can be saved and exported at any time.

The desktop treats a selected version as ready only after loading content with the matching task and version identity. Pending/failed reads hide the previous content and disable editing/export; failed reads have a local retry. Late responses for previous selections are ignored. An edit session captures the loaded base, expected head, mode and draft blocks together. It remains bound to them if the head advances. Save uses the session's captured fields; a conflict retains the draft and the backend candidate. Version/task switches are disabled while editing until save or explicit discard. Historical versions offer **Rebuild from this version**, with an explanation that later content is not included. Manual saves remain partial claims. Export always targets the loaded saved version; unsaved edits are excluded and identified as such in the editor.

### Exact saved-document and evidence access

`read_document` resolves an omitted `version_id` to the current head once for that operation; an explicit ID stays immutable. Its full result is the saved **version envelope**, with `content.blocks`, `content.pages`, `assets`, `originals` and provenance. `edit_document` accepts `Edit` operations against the content, not that envelope. Select `/content/blocks`, `/content/blocks/11`, or `/content/blocks/11/markdown` directly. A range requires a selected string or array; the root envelope is an object. Invalid paths/ranges return actionable structure guidance and preserve the original arguments. No index-first step is required.

Optional `view="index"` returns the exact version, block IDs/pages, Unicode character and UTF-8 byte counts, and exact pointers. It does not include block bodies or certify fidelity. The index does not take content selectors; use its version/pointers in a full read. Full and raw reads remain available, including on the first access. A smaller read leaves earlier full results in history unless an explicit policy or the existing compaction/admission rules change their projection.

Read results distinguish three facts in `completeness`:

| Field | Meaning | Twelve-block `/content/blocks`, range `[11,12)` |
| --- | --- | --- |
| `root` | The whole saved root is returned in the named access representation | false |
| `target` | The JSON Pointer target (before range selection) is entirely returned | false |
| `selection` | The valid requested selection is entirely returned | true |

An unsliced target or explicit `[0,12)` has `target=true` and `selection=true`, but still `root=false` when the pointer selects a field. A full root has all three true. The retained `complete` field aliases root completeness only; document `claim="complete"` is a different fact. `total` is measured before slicing. String ranges use Unicode code points; arrays use item indexes; raw/Base64 reads use original-byte offsets. `original_bytes` describes the stored original and `returned_bytes` describes selected content under `returned_size_basis`, excluding receipt/native-envelope escaping. Neither is a provider token count.

Metadata indexes have root/target false and selection true. Native-image reads identify a complete saved image selection, not proof that its pixels were included in a model request: actual projection reports `pixels_delivered`. Index reads do not inject image pixels. Unsupported selectors on indexes, native images or raw JSON fields are rejected rather than ignored. All completeness facts concern access, not PDF scope, model understanding or source fidelity.

### Working-evidence feedback and optional preview

Every newly assembled normal input contains one compact `Working context feedback` summary: current head, representation counts, actual document-read bodies, native-image count, total local input estimate, output reserve and remaining allowance. It counts its own emitted bytes and all tool descriptions. Numeric rendering uses monotonic whitespace width to avoid self-cost oscillation at a digit boundary. Unknown-result reservations remain separate admission metadata; the summary describes the actual emitted payload, not future results. It does not select, release or silently change evidence.

`inspect_context` is optional. Its detailed inventory describes the **frozen normal input that produced the current response**, including full/selected/index/raw results, reference-only projections, authored tool arguments, assistant text, pins and handoff summaries. `release_ref` names the exact history-result/argument/pin representation; `ref` identifies its underlying source when available. Edit commit receipts are not document-read bodies. The inventory can be read whole or with explicit zero-based item ranges. Component costs are labeled native-envelope deltas, not an additive breakdown or a semantic-relevance judgment.

The tool deliberately excludes **all results of its current response batch**, including preceding reads or edits. It reports both the snapshot head and current head, input request/payload identities and active-policy identity. Optional `changes` accepts agent-selected `pin`, `release`, and `notes` against that snapshot active policy. It uses the production normal assembler and estimates the resulting hypothetical input; it does not import pending intent, apply a policy, consume a model request, or guarantee the later batch's admission. New results, outcomes, settings and head changes can alter that later input. This is information for ordinary agent work, not a mandatory preview or confirmation-only turn.

New frozen normal requests retain a compact context/anchor snapshot outside graph hydration. An exact preview is available only when the current assembler reproduces the recorded payload; older requests without that snapshot or changed assembly recipes cannot claim an exact reconstruction. Read-only inventory remains available from the actual frozen payload. Tool capture and immutable receipts still persist normally; their replay returns the same observation. No original receipt/frozen input, policy eligibility, head or consumed budget is changed by inspection. Normal whole-batch coordination remains the only policy activation path.
