# FIX-01 specification

[Local tickets](tickets.md) · [Verification](verification.md) · [Inventory and selection basis](../../verification/20261106_0112_WORK_REGISTER.md#open-defect-inventory-before-stage-b-2026-11-14)

## Selected outcome and authority

2026-11-15, Asia/Singapore. Before Stage B, the user prefers to fix known bugs. The [open-defect inventory](../../verification/20261106_0112_WORK_REGISTER.md#open-defect-inventory-before-stage-b-2026-11-14) found three registered code defects still present at `2b9b86c` and one stale documentation finding. To the proposal to fix all four, the user replied "yes, fix all four", then asked to "create tickets first, then delegate to gpt-6.1-sol-extra-high to implement".

That authorizes this spec and its tickets, offline implementation and checks for the four items, the records, and a local commit on `codex/fix-01`. It does not authorize a push, PR, merge, provider call, conversion, packaging or another batch. Stage B remains unselected.

**Baseline.** Branch `codex/fix-01` from `bb326fd`. That commit adds only records on top of `master` at `2b9b86c`, so the application code equals `master`.

## Scope

| ID | Problem | Required outcome |
| --- | --- | --- |
| [H02](../../WORK_ITEMS.md#runtime-and-engineering-inventory) | The agent-facing preview argument error in `src/pdfmd/tools.py` reads `320â€“3000` and `200â€“3000` (mojibake for an en dash). | The message is readable and correct. Any other mojibake of the same kind in maintained source is corrected. |
| [H03](../../WORK_ITEMS.md#runtime-and-engineering-inventory) | Several local API routes in `src/pdfmd/server.py` take an untyped `body: dict` and read required keys directly. Only `ValueError` has a handler, so a missing or wrongly typed field becomes an unhandled exception, normally HTTP 500, with no useful message. | A missing or wrongly typed field returns a client error (4xx) that names the field. Valid requests behave exactly as before, including the desktop's existing calls. |
| [R01-SURROGATE](../../WORK_ITEMS.md#production-estimation-residuals) | A lone UTF-16 surrogate (for example U+D800) in a request makes `storage.encode` raise `UnicodeEncodeError`, so the request cannot be estimated or persisted and the task fails. Which producers can create one is untraced. | See the rule below. |
| [NET-PM-01](../NET-01/verification.md#post-merge-review-and-orientation) | README routes readers to CURRENT_STATE for facts it no longer holds, and names an installer path that does not exist. | README routes each fact to its actual owner and describes the build artifacts that actually exist, or states how to create them. |

### R01-SURROGATE rule (agreed 2026-11-14)

1. **Trace first.** Determine which inputs can carry a lone surrogate into a request or a persisted record. At minimum check: PDF text extraction, OCR output, script and tool output, the model's reply (JSON escapes such as `"\ud800"` decode to a lone surrogate), user-entered text, and file names. Record which producers are reachable and the evidence for each.
2. **Never replace or drop source characters silently.** Do not substitute U+FFFD, strip the character or use `surrogatepass` to store invalid text as if it were valid.
3. **Reject at the earliest reachable boundary, with an actionable message.**
   - Source extraction or OCR that can produce one: report at that tool, with the page and character offset, so the agent can see and describe it.
   - The model's reply: treat it as an invalid reply on the existing rejected-reply path, so the existing automatic response repair applies.
   - Anything else that can still reach request preparation or persistence: reject with a clear error instead of an unhandled `UnicodeEncodeError` crash.
4. Unreachable producers need no code change; record why they are unreachable.

**Corrected premise and open decision (2026-11-15).** Step 3's model-reply bullet assumed that a rejected reply enters automatic response repair. The [T3 trace](verification.md#stopped-rejected-native-replies-do-not-enter-automatic-repair) shows it does not: a rejected native reply settles as `response_rejected`, the task blocks, and the user resumes with explicit Continue. Automatic repair applies only to accepted replies (text-only replies, invalid handoffs). The implementer stopped as instructed. The user must choose:

- **A. Keep the existing rejected-reply contract.** A reply carrying a lone surrogate is rejected with its native bytes preserved, the task blocks, and Continue recovers it. All other boundaries are implemented as planned. Automatic repair of rejected replies becomes a separately registered follow-up.
- **B. Extend the contract in FIX-01.** Add bounded automatic repair for rejected replies, using the retained native or SSE evidence when no accepted reply exists. This changes the shared rejected-reply path (also used for malformed replies, R07) and needs its own design and checks.

The implementer may choose the exact mechanism within this rule. A finding that the rule cannot be met without a material behavior change (for example to the stored record format, or to how source text is represented) is a stop-and-report point, not something to decide alone.

## Constraints

- Follow AGENTS.md: preserve source characters and form, full agent access and existing contracts; no backward-compatibility shims are needed.
- FastAPI and Pydantic are already pinned in the lockfile. Use their native request-validation mechanisms for the installed versions; do not upgrade dependencies.
- Offline only. Synthetic fixtures, no credentials, no private task stores, no provider calls.

## Acceptance

- **H02.** A test or direct check shows the corrected message. A search of `src/` and `tests/` finds no remaining `â€` mojibake sequences, or each one is explained.
- **H03.** Tests send requests with a missing field and a wrongly typed field to each changed route, and get a 4xx that names the field. Existing tests for valid requests still pass, and the desktop tests that drive these routes pass.
- **R01-SURROGATE.** The trace records each producer as reachable or unreachable, with evidence. For each reachable producer, a test feeds a lone surrogate through the real path and observes the agreed rejection, with the task left in a recoverable state and no source text altered. A test confirms valid non-BMP text (for example an emoji or CJK Extension B character, encoded as a proper surrogate pair in JSON) still passes.
- **NET-PM-01.** Every README pointer touched leads to a section that holds the stated fact. `tools/docs/check_docs.py` passes.
- **Whole batch.** The full engine suite (`pytest tests/engine`) passes on the final revision. `pnpm build` passes. The affected desktop specs pass. Results and revision are recorded in [verification](verification.md).
