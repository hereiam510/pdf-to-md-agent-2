# Changelog

This file records application changes and important validation limits. The dated entries below currently cover development snapshots through 2026-10-25, not all later accumulated work and not published releases. For subsequent A/SC02, diagnostics, recovery, estimator/storage and Nursing records, start with [current verification](docs/CURRENT_STATE.md#verification-basis) and [implementation history](docs/history/IMPLEMENTATION_HISTORY.md). Updating documentation does not rebuild or publish an application. [CURRENT_STATE](docs/CURRENT_STATE.md) routes current status, [implementation history](docs/history/IMPLEMENTATION_HISTORY.md) retains detailed dated evidence, and [CONTRACTS](docs/CONTRACTS.md) owns implemented behavior.

## Unreleased

### 2026-10-25 — Capacity waiting and projection estimates

- Retain already saved proposals when a capacity reduction makes the actual active fallback unusable, including pending releases and oversized previous handoffs.
- Preview the fallback's normal/compaction input and bounded rejection outcome before a capacity rejection; retain legitimate rejection, supersession and frozen-input replay.
- Keep short arguments/results inline when replacing them with references increases the measured native input. Do not defer a fitting neighbour because of an inflated scaffold.
- Preserve same-batch settlement, original receipts, full/raw/field/range reads and consumed work. Dual-protocol regression and delivery checks are recorded in CURRENT_STATE; no Nexus call or release build is included.

### 2026-10-25 — Proposal validity, admission and outcome delivery

- Distinguish retryable capacity waits, immutable terminal outcomes and outcome delivery; checkpoint coordination before request preparation.
- Preserve pending intent through temporary capacity blocks and resume after settings repair. New instructions supersede unsettled intent without reviving old decisions.
- Keep bounded context-control receipts visible, with complete originals and diagnostics behind exact references; reserve the complete native outcome envelope.
- Admit fitting proposals without compulsory compaction. Avoid admission by additional unselected evidence deferral; honor explicit releases and pin representations.
- Allow clearly labeled pending-release compaction views and bounded final-handoff correction for feasible pending policy. Preserve original active policy until admission.
- Extend dual-protocol state/fault tests and source-led delivery through capacity block, settings repair and reopen. CURRENT_STATE records actual verification and limits.

### 2026-10-25 — Deferred context updates under history pressure

- Save exact context updates as inactive proposals when accumulated history prevents immediate admission. Compact under the active policy, then check the complete proposed input before application.
- Compose later valid updates in call order. Preserve an earlier pending proposal when a later update is invalid or irreducibly oversized.
- Keep original tool receipts unchanged and record a separate applied, rejected or superseded settlement. Recover committed decisions across result, event, checkpoint and frozen-request boundaries.
- Retain proposals through interrupted or failed compaction without resetting consumed requests or active time. Preserve complete originals and full/raw/field/range access.
- Add both-protocol local tests and source-led save/reopen/export fixtures. Existing records report 206 passing Python tests, ten retained desktop cases passing, and two new desktop cases passing after correcting their seeded request metadata. These are separate runs; scripted replies do not establish real-model conversion quality.

Historical review follow-up, addressed by the subsequent coordination entry above: rejection or supersession feedback can itself exceed the remaining context capacity after history has been compacted, preventing the agent from receiving the outcome. Review also identified incomplete agent-facing guidance for notes replacement and release/pin precedence. Mandatory compaction after capacity pressure has already cleared, and blanket supersession on new instructions, remain implemented policies under discussion rather than completed improvements.

### 2026-10-24 — Stencil appearance and explicit pin admission

- Distinguish a stencil's coverage mask from its painted page appearance. Let the agent select a page occurrence or another source-led rendering method, retaining color, orientation and provenance.
- Expose explicit index, native-image, full/selected-content and raw-byte pin representations. Check the proposed policy before application and retain the previous policy when admission fails.
- Account for raw streams as Base64 text, keep exact original streams readable, and preserve admission decisions on replay.
- Add both-protocol delivery checks using Electron and Edge, including saved/reopened images, exported files and original-stream integrity.

### 2026-10-24 — PDF coordinates and image delivery

- Define unrotated page coordinates for extraction, rendering and OCR regions, with invertible mappings to rendered pixels and explicit page rotation.
- Preserve original image/mask streams and provenance. Handle tested CMYK/SMask and JPX display cases, while retaining compatible RGB JPEG bytes.
- Carry selected source-image originals into immutable document versions and exports.
- Add synthetic coordinate/image fixtures and actual-renderer delivery checks. General alpha handling, arbitrary color profiles and high-bit-depth fidelity remain outside the demonstrated coverage.

### 2026-10-24 — Existing-task settings and active time

- Add task-scoped capacity and total request/time controls. Continuing an existing task uses its saved settings instead of replacing them with connection defaults.
- Preserve already consumed work and the original payload, route and replay policy of frozen requests.
- Measure known active time with a shared monotonic meter. Retain interrupted intervals as explicitly unknown rather than charging all downtime or reporting zero work.
- Expose effective limits and time uncertainty in the desktop/API, with both-protocol continuation and delivery fixtures.

### 2026-10-24 — Handoff application replay

- Recover an already committed handoff application across checkpoint gaps, including when new instructions arrive before recovery.
- Preserve its original acceptance event, archive links and consumed usage. Check the current input before preparing subsequent work.
- Retain validation for an archived but unapplied handoff; an archive alone does not establish successful application.

### 2026-10-24 — Compaction progress

- Assess evidence against the actual compaction envelope and preserve fitting objects within mixed-size batches.
- Continue beyond a reference-only prefix when it provides no useful body reduction, without making pins a barrier to history selection.
- Accept useful partial reductions. If a handoff covers the last history batch but still cannot fit normal input, retain the old context and use bounded correction.
- Keep correction requests within the existing persistent request/time budgets.

### 2026-10-24 — Context capacity and independent pins

- Return explicit deferral references for individually oversized bodies while preserving exact originals and unrestricted full/raw/field/range retrieval.
- Hydrate pins independently of their original history, so compaction can advance without silently releasing pinned evidence.
- Preserve native tool-call/result pairing, omission information and coverage metadata in context projections.
- Handle aggregate history pressure through compaction rather than silently removing individually fitting evidence.

### 2026-10-24 — Version-bound editing and continuation

- Bind UI drafts to the loaded task, version and starting head. Preserve unsaved content when a save conflicts.
- Separate ordinary edits from deliberate rebuilds, and allow local insertion/replacement from exact retained candidate content.
- Reconcile completed tool effects before processing new user instructions. Mark obsolete, unstarted calls as unexecuted and prevent old reports from completing a newer instruction.
- Support explicit Continue after a failed or rejected model response while retaining original records, consumed budgets and unknown-outcome replay boundaries.
- Add desktop editing, restart, continuation and export checks.

## Development baseline — 2026-10-23

- Introduce the Electron workbench and Python agent engine with native Nexus Chat Completions and Responses support, shared source/document tools, persistent execution and explicit-version ZIP export.
- Add bounded automatic correction for text-only responses and invalid handoffs, preserving original replies and task budgets.
- Produce an initial Windows development build. Existing packaged artifacts predate the unreleased changes above; use the development launcher for the current source.

## Validation and release boundary

- The unreleased increments above were checked locally with scripted inference responses; they do not establish natural model strategy, arbitrary-summary fidelity or unseen-PDF quality.
- Save/reopen/export evidence is scoped to the retained fixtures. Export-filesystem portability, OCR recovery, broader alpha handling and updated Windows packaging are not claimed complete here.
- This changelog and the associated Git publication record existing work. They do not constitute a new model trial, a new installer build or a release acceptance decision.
