# Context compaction progress review handoff

The current review target is follow-up phase 1 on the working tree based on `2d60c68`, retaining the three editing/continuation batches and context-capacity/pin increment. The preceding snapshot's independent re-review is complete. On 2026-10-24, Asia/Hong_Kong, the user accepted the three-phase follow-up order and acceptance conditions below and subsequently authorized phase 1 only, without live Nexus calls. Phase 1 is implemented and locally verified; phases 2 and 3 remain unimplemented. [CURRENT_STATE](CURRENT_STATE.md#review-follow-up-progress) owns actual progress and verification; [PRODUCT_REQUIREMENTS](PRODUCT_REQUIREMENTS.md) owns intended outcomes. This document owns the follow-up scope and acceptance conditions. Local verification is distinct from independent review, live-model content acceptance and release.

## Product and revision scope

The user supplies a PDF and scope. The app runs its own agent through Nexus and supports complete, faithful, readable and reusable Markdown plus source images, with little routine user handling. The agent keeps its choice of methods, tools and reconstruction scope. No fidelity reduction, hidden scope reduction, compulsory extraction recipe or new per-tool approval is part of this revision.

| Batch | Implemented behavior | Main review locations |
| --- | --- | --- |
| Current follow-up phase 1: compaction progress | Per-object admission in the actual compaction envelope; reference-only prefixes can include later material; last-history overflow uses bounded correction with prior context retained; useful partial reductions remain valid | `src/pdfmd/context.py:admit_group/compact_request/apply_handoff`; `tests/test_context_progress.py`; Q2 and the context guide |
| Retained: capacity and independent pins | Explicit deferral of an individually unfit body with precise read references; no arbitrary normal-input eviction of individually fitting evidence; pins hydrate independently of compacted history; original bodies and native pairs retained | `src/pdfmd/context.py:normal/pins/group`, tool guidance; `tests/test_context_admission.py`, `test_context.py`, `test_response_repairs.py` |
| 1. Version-bound editing and reuse | UI draft bound to loaded task/version/head; ordinary edit versus explicit autonomous rebuild; local insert/replace from exact candidate content | `src/renderer/useDocumentSession.ts`, `main.tsx`, `types.ts`; `src/pdfmd/schema.py`, `documents.py`, tool/system guidance; `tests/test_documents.py`, desktop session/workbench tests |
| 2. New instructions before old pending tools | Recover completed receipts and context intents; pair unstarted obsolete calls with unexecuted results; retain candidates; keep unknown effects unknown; old report cannot terminate a new amendment | `src/pdfmd/runtime.py:tools`, `tools.py:reconcile/skip/settle`, `nexus.py:instruction_basis`; `tests/test_continuation.py` |
| 3. Explicit failed-request Continue | New request after HTTP/rejected reply or amended never-sent input; persistent decision before checkpoint update; latest input and failure references; original unknown replay gates and budgets retained | `server.py:Engine.start`, `runtime.py:resume_pending/run`, `nexus.py:reconcile/send`, `context.py:continuation_feedback`; `tests/test_continuation.py` |
| Integration | Local Stop/amend/Continue, version preservation, restart and ZIP delivery; earlier UI edit/rebuild coverage retained | `tests/desktop/continuation-workflow.spec.ts`, `boundary-hook/sitecustomize.py`, `verify_delivery.py`, `workbench.spec.ts` |

Exact contracts are in [Q1–Q3](CONTRACTS.md#implemented-first-version-contracts). The [context guide](design/CONTEXT_AND_EVIDENCE.md#implemented-capacity-admission-and-independent-pins), [document guide](design/DOCUMENT_ENGINE.md#implemented-editing-and-reuse-behavior) and [execution guide](design/EXECUTION_AND_DELIVERY.md#implemented-continuation-boundaries) explain mechanisms and rationale. The existing single-writer graph and native Nexus services fit these boundaries; dependency pins are unchanged. No general recovery rewrite was needed.

## Evidence and independent reproduction

Use `.local/review-2026-10-24-context-progress.zip` rather than HEAD alone. `manifest.json` lists every packaged source byte hash and additions that ordinary `git diff` does not display. `changes.patch` includes tracked and new files relative to HEAD; `phase-1-increment.patch` isolates this batch against the preserved 582-file preceding snapshot, including its accepted-phase documentation. The package includes that before snapshot so the original six failing regressions are auditable. Existing root review scratch, credentials, private PDF packages and real Nexus workspaces are excluded. Optional historical design sources in the source ZIP remain reference data, not current instructions.

From the extracted source with the locked development environment installed:

```powershell
.venv\Scripts\python.exe -m pytest -o addopts= -q
pnpm build
pnpm test:desktop
.venv\Scripts\python.exe tools/check_docs.py
```

These commands do not require Nexus credentials. Python tests use mock HTTP; desktop conversion tests use a loopback server with scripted responses. The three renderer-session tests use controlled IPC replies. The continuation desktop test uses the real backend with a test-only delay after a real settled context-tool receipt, allowing UI Stop at a deterministic boundary. Normal app startup does not load that hook. This is not a test of safely terminating arbitrary running scripts.

The phase-1 run passes **92 Python tests in 87.42 seconds**, **five desktop tests in 1.4 minutes**, the TypeScript/desktop build and documentation checks. The earlier 80-test context-capacity and 68-test editing/continuation snapshots remain preserved separately. Current evidence is bundled under `evidence/`:

- Six pre-fix failures for the three observed defects in both protocols; focused and full pass logs, build/desktop/docs checks, and the intermediate fixture-authoring failures. Those fixture failures concern missing mandatory fixture metadata and a wrongly assumed size boundary; no product validation was weakened to make them pass.
- Both native-protocol final-handoff fixtures: source PDF, exact prior/final versions, all synthetic original blobs and journals, paused/finished checkpoints, fixture payloads, exported ZIP, source/output screenshots and verification. Seven mock responses per fixture exercise rejection, pause/reopen, correction and completion of useful saved work. A scripted agent chooses an explicit pin release and source reads; this is not natural model adoption evidence.
- Direct controls for partial rolling progress with unchanged prior handoff text, reference-only prefix progress, 200KB/20KB retention, and persistent bounded exhaustion. The exact maintained test source is included.
- This run's two-page desktop continuation and editing/rebuild sources, reopened screenshots, exported ZIPs and verification JSON. These retain prior effective UI capabilities; they are not a new real-provider test.

The retained checks compare all exported members with the reopened saved version, compare native source image samples and retain the original PDF unchanged. Full/raw/field/range access and exact candidate syntax survive compaction/reopen. The current source page and exported HTML previews were inspected, and Edge decoded the image. Exact extracted lines remain in Markdown; CommonMark soft breaks display as one paragraph. Scripted fixtures are not evidence of natural agent strategy, universal formatting fidelity, model summary semantics or real cost savings. Re-entry tests cover the selected paths, not every possible crash. The earlier active-script unknown-effect evidence remains in the preceding package and outside this phase.

## Review questions and remaining limits

Review the implementation independently; the following questions help locate consequential boundaries, not prescribe findings:

- Can a reducing final handoff still empty history while normal input overflows? Does correction retain the old history, candidate, pins, useful draft and consumed counters across reopen/Continue? Are genuine mandatory-context obstructions still explicit?
- Does mixed-size compaction retain the fitting member and record only the actual per-object deferrals? Does a reference-only prefix reach later material without accepting expanding handoffs or evicting normal-input bodies by aggregate size? Does useful partial progress remain possible when uncovered history still exceeds capacity?
- Does a fitting full selection remain full? Can a giant first result be reached by arbitrary precise/full/raw reads after an explicit deferral, with original warnings/coverage intact? Does aggregate history pressure still exercise compaction rather than silently evicting evidence?
- After removing covered history, do exact pins still hydrate from immutable originals, including candidate syntax and image pixels? Do mandatory oversized pins stop explicitly? Does a pin protect only its selected object rather than freezing an entire batch or recursively claiming referenced content was read?
- Are native call/result pairs and reasoning items preserved? Are capacity decisions visible in frozen inputs/metadata without putting hydrated bodies into graph checkpoints? Do correction and Continue tests still exercise actual compaction after the fixture changes?
- Can a stale/asynchronous renderer read change draft identity or exported version? Can an explicit rebuild or local candidate reuse change unrelated content without declaring it?
- Does amendment handling preserve actual completed work, exact native pairing and context intents while stopping unstarted obsolete work? Is every unknown effect reported honestly?
- Does Continue retain old evidence and consumption, recover its own persistence gaps, and prevent a new-ID bypass of unknown-outcome replay limits?
- Do retained originals, reopened versions and ZIP bytes agree? Distinguish structural completeness from source-led content acceptance.

No new Nexus/model call, external change, dependency upgrade, old-repository modification or Windows repackaging occurred. `Start Workbench.cmd` and existing `release/` artifacts still use the earlier response-correction build. Use the development launcher to exercise this source. No migration of pending requests created by older builds is provided; use isolated development test workspaces. Older completed saved versions remain readable/exportable.

## Re-review outcome and corrections

The following findings describe the preceding snapshot before phase 1. Its three context findings motivated the implemented change; phase-2/3 findings remain unresolved. [CURRENT_STATE](CURRENT_STATE.md#review-follow-up-progress) separates those identities and verification. The original reports and counterexamples remain under ignored `.local/review-follow-up-2026-10-24/`. The explanations remain understandable without those local artifacts or the original chat.

| Finding and evidence class | Mechanism, impact and correction to the external review | Follow-up |
| --- | --- | --- |
| P1, reproduced: final-handoff dead end | `Context.apply_handoff` accepts any whole-input reduction and removes covered history. If it consumes the last batch but normal input still exceeds capacity, `compact_request` has no history to select and Continue blocks again. Both protocols reproduced this even though required pins fit and a shorter handoff fits. | Phase 1 |
| P2, reproduced: ineffective short-prefix selection | `compact_request` may select only a small reference-only prefix. Adding a handoff then costs more than removing that prefix. Rejection protects capacity; accepting an expanding handoff is not a fix. The external review's claim that an old 700-byte handoff makes reduction mathematically impossible was disproved: the old handoff is replaced, and an unchanged 814-byte handoff reduced input in the control. | Phase 1 |
| P2, reproduced: avoidable whole-batch deferral | Compaction's `group(defer=True)` removes a fitting 20KB result along with a 200KB result, although a finer projection fits the same request. This removes information from that summary input, not from immutable originals. A completed tool operation is not proof that the model read its output. Actual model-quality/re-read impact remains unmeasured. | Phase 1 |
| P2, reproduced: existing-job settings and active time | `Engine.start` can retain a bad route even after a zero-attempt/zero-request capacity failure. Later limits changes also fail to extend an exhausted task. A simulated unclosed active interval adds 10,000 seconds of downtime on restart. The settings and clock reproductions retain saved work. | Phase 2 |
| Source-supported and locally demonstrated proposed-change risk: mutable replay policy | `Nexus.freeze` stores route/payload, not an original replay-policy snapshot; `send` reads current job limits. A blanket limits overwrite can extend an old unknown request's replay allowance despite unchanged counters/payload. This is not an existing UI update path. Correction-episode extensions and protocol changes also need distinct policies. | Preserve boundaries in phase 2; do not introduce generic settings mutability |
| P1, reproduced: mixed PDF coordinate frames | `inspect` labels rotated `page.rect` and unrotated text boxes together. `render_page` accepts rotated clips; direct box reuse can render blank/wrong content or reject valid source areas. PyMuPDF text/image boxes are unrotated, so relabeling all output as rotated is incorrect. The shared render path affects OCR regions; OCR itself was not rerun. | Phase 3 |
| P1, reproduced: image delivery/provenance failures | CMYK plus SMask fails PNG encoding; JPX bytes survive save/export but fail browser decoding. The tested unmasked CMYK JPEG is converted/reencoded by library extraction, contradicting the native-byte label. RGB/SMask and RGBA controls pass. The source PDF survives; not all claimed alpha/mask-size/other-format failures were reproduced. | Phase 3 |
| P3, contract clarification: result release and image selection | Capacity deferral of JSON can retain fitting pixels, while agent release of a result also removes its unpinned accompanying image. Different intentions can justify different behavior. `body_in_context=false` and `pixels_delivered=true` are not inherently contradictory. No delivery loss was demonstrated. | Retain as a clarification; not an extra phase-1 mechanism |

The final-handoff reproduction used an input budget of 63,488 estimate units. Required instructions/pins occupied 62,489. The accepted handoff reduced normal input from 69,272/69,305 to 64,485 but emptied history; a shorter control reached 62,907. These are app estimates, not measured provider tokens. The real Runtime and plain Continue both reached `capacity_blocked` using local scripted replies, with zero provider attempts.

The PDF reproduction used installed PyMuPDF 2.0 / MuPDF 1.28.5 and Electron 45.0.0 / Chromium 156.0.8078.48. [PyMuPDF's coordinate rules](https://pymupdf.readthedocs.io/en/latest/page.html#modifying-pages) explain the unrotated extraction versus rotated rectangle distinction; [supported image outputs](https://pymupdf.readthedocs.io/en/latest/pixmap.html#supported-output-image-formats) explain the CMYK PNG failure. Saved/exported HTML, not only file hashes, established the JPX display failure. The CMYK JPEG changed from 5,358 to 5,842 bytes with different quantization tables; the raw original remained in the source PDF. The review did not quantify perceptual color error.

## Accepted three-phase follow-up

Use this sequence and these acceptance conditions as the development decision basis. These are follow-up phases, not the completed editing/continuation batches numbered above. Actual implementation status belongs in CURRENT_STATE. No backward compatibility is required. Choose local fixes or responsible-module refactoring by correctness, autonomy, fidelity and maintenance cost; current evidence does not require a framework replacement or establish that a few lines suffice.

Keep each phase focused. The order does not require eliminating every hypothetical risk before moving on. Evidence that materially changes the next delivery need can justify an explicit plan revision; do not silently merge independent phases or reopen historical experiments. Provider calls, external publication and release work remain separately scoped.

### Phase 1: Context compaction progress

**Purpose and scope:** repair the three related context transitions above in the assembler/acceptance boundary and affected runtime tests. Preserve independent pins, immutable originals and exact native call/result pairs. The normal-request and compaction envelopes have different overhead; shared projection logic must still measure each actual payload.

Acceptance:

- When a handoff consumes the last history batch, it must not create the reproduced state with oversized normal input and no supported next compaction step. Use bounded handoff correction or a supported handoff-only compaction path. Required pins that genuinely cannot fit remain explicit capacity blocks. When uncovered history remains, useful partial reductions must still be accepted.
- Reference-only prefixes must not force repeated unproductive compaction. Verify real progress using assembled input, including replacement of any prior handoff. Keep the non-reduction guard. A fixed 500/1,000-byte summary allowance is not a universal acceptance rule, and content fidelity must not be traded away to satisfy a size example.
- In a reachable compaction case with a 200KB result and a fitting 20KB result, retain the fitting content where the actual compaction envelope permits it. Describe any deferred body accurately, keep its exact references and originals, and do not infer relevance or reading coverage from capacity decisions.
- Exercise both native protocols through the Runtime, bounded correction and Continue using local fixtures. Preserve full/raw/field/range/native-pixel access, pinned data across reopen, useful candidate/saved work, original history records and task budgets. Check source-led saved/reopened/exported Markdown and image results after the corrected path, plus relevant existing regressions.

Keep existing-job settings, active-time accounting and PDF evidence fixes out of this phase. Do not add a fixed extraction recipe, arbitrary eviction/quota, or a general recovery subsystem to make the compaction tests pass.

### Phase 2: Existing-job settings and active time

**Purpose and scope:** let an explicit change to a task's total request/time allowance or route capacity take effect without discarding its work or consumed usage. Make effective values visible through the UI/API. Correct interrupted-interval accounting within the existing execution boundary.

Acceptance:

- A task blocked by its total request/time allowance can use an explicit increase and continue to saved, reopened and exported delivery without resetting consumed counters. A capacity failure before the first request can be corrected on the same task.
- Capacity changes apply to newly prepared requests. Preserve the identity, bytes and applicable limits of an already frozen request. Demonstrate that changing total allowances cannot silently reopen an exhausted unknown-outcome replay allowance or bypass an unknown-effect gate.
- State the crash-time accounting policy before implementing it. Preserve known active consumption and represent the uncertain interval honestly; neither all downtime charged as active work nor silently zeroing uncertain work is acceptable. Simulate the retained 10,000-second stale-interval case and check the recorded/effective budget and subsequent behavior.
- Verify the affected UI/API continuation path, relevant clock/fault and replay controls, unchanged saved content/assets, and source-led reopen/export. Retain the context behavior established in phase 1.

Do not treat this phase as permission for arbitrary protocol switching, retroactive replay-policy changes, correction-episode extensions or general local-script reconciliation. `vision=false` suppressing pixels is distinct from capacity overflow. A changed protocol cannot simply reinterpret saved native history.

### Phase 3: PDF coordinates and image delivery

**Purpose and scope:** make extraction positions reliable inputs to rendering/OCR and make delivered images both readable and traceable to accurately identified originals. Work at the evidence/asset boundary; the agent retains the choice of extraction, rendering, OCR, scripts and reconstruction scope.

Acceptance:

- Define one public coordinate convention or an explicit conversion between named frames. Verify text/image boxes on 0/90/180/270-degree pages against actual rendered targets, including a region that otherwise falls outside the rotated rectangle. Include fractional crop/pixel-origin mapping where exposed by the contract. Labels alone do not establish a coordinate conversion.
- Handle CMYK plus SMask without the PNG encoding failure and retain RGB/SMask and RGBA behavior. Preserve source PDF data and accurately distinguish embedded originals, decoded images, color conversions and composed/rendered derivatives. Do not assume `Document.extract_image()` returns original JPEG bytes for every color space.
- Provide a usable asset for the reproduced JPX case while retaining its original data and provenance. Open the saved version and the reopened exported HTML in the actual renderer; byte-identical but broken images do not pass.
- Verify the tested CMYK JPEG original bytes against the embedded stream, and source appearance/labels against any derived asset. PNG encoding can be lossless even when an earlier color conversion changed data; record that distinction. Check exact saved/reopened/exported Markdown/image assets, relevant coordinates and normal RGB controls without imposing a compulsory rendering method on the agent.

This phase may use separate verifiable coordinate and image substeps. Its acceptance is bounded to the evidenced cases, not a universal PDF/image-format or OCR-quality certification.

### Remaining observations outside the three phases

General local-effect recovery is a real delivery gap: stopping a started script without a recoverable receipt can leave `local_outcome_unknown`. However, a per-operation working directory is not an OS sandbox; trusted scripts run with host-user permissions, OCR uses a shared cache, and waiting for the direct child does not prove that descendants stopped or completed writes were undone. Any later recovery work must distinguish controlled workers from arbitrary scripts and retain truthful effect status. Ordinary Continue is not proof of reconciliation.

Repeated oversized full reads remain an unmeasured model-behavior opportunity. Deferred receipts already expose `source_view.total`, `value_keys`, pointer/range options and exact originals where applicable. New references do not necessarily duplicate content-addressed bytes. Add feedback only for an evidenced need; do not remove full/raw access or impose a reading sequence.

Windows distribution still needs a future rebuild, and export to destinations without hard-link support remains unverified. Live-model summary quality, natural tool adoption, real-provider continuation and arbitrary crash recovery are not established by the offline results. None is a hidden prerequisite for phase 1 or permission to reopen closed Nexus experiments.

For each implemented phase, update the affected contract/guide and CURRENT_STATE with the actual working-tree identity, checks, source-led delivery evidence, limits and next action. Preserve earlier artifacts and failed controls. Passing software tests, verified fixture delivery and installed-product readiness remain distinct.
