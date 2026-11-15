# GYN-01: gynecology pages 1–8 source-conversion specification

## Status and authority

Updated 2026-11-15 (Asia/Hong_Kong). The [T2/T3 instruction](../../discussions/SOURCE_CONVERSION.md#t2-and-t3-selected-2026-11-15) authorizes one bounded interval on the prepared task, source-led review and reopen/export, and updating draft PR #4. The agreed settings and exits below remain unchanged. No Continue, extension, replacement task or merge is selected. [Tickets](tickets.md) own progress; [verification](verification.md#t2-and-t3-execution) owns results.

## Outcome and decision basis

Determine whether the app's agent autonomously delivers the complete selected English scope with faithful text and independent figures despite degraded text extraction, through the saved, reopened and exported version. The app supplies tools; the converter chooses methods and produces content; the reviewer assesses without assembling or repairing it.

[Earlier-run evidence](../../discussions/SOURCE_CONVERSION.md#what-the-earlier-runs-already-show) supports this coverage choice, not a failure-rate ranking. A03 establishes large-map feasibility, not repeatability; the older Nursing check has a bounded source/build. Preserve both T5-L1's AR-T5-14 discrepancy and T5-L2's later successful observation. The explicitly selected fresh task preserves Task B; it is not forced by a general settings restriction. This is an unmatched, finite opportunity, with no second source, higher-effort arm, calibration study or predicted cost saving.

Apply [Stage B completion conditions](../../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources), [document/claim rules](../../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit), [exact source/document access](../../design/DOCUMENT_MODEL.md#exact-saved-document-and-evidence-access), [FD-01](../../design/FIGURE_DELIVERY.md#required-outcome), [PDF appearance/original preservation](../../design/PDF_EVIDENCE.md#pdf-coordinates-and-image-delivery), and [runtime settlement/export](../../design/RUNTIME_AND_DELIVERY.md#continuation-feedback-and-delivery-settlement). Their shared rules retain their owners; this spec selects the workload and its discriminating acceptance.

## Source and exact content scope

Use the unchanged 21-page `references/gynecology/source.pdf` identified in the [Task B source inventory](../../discussions/REQUEST_CAPACITY.md#selected-source-scopes-and-inspection-evidence). The [current source check](verification.md#source-identity-and-layout-check) records its observed digest and boundary evidence. Refresh the hash and imported-copy equality during eventual preparation; an unavailable/different PDF is not permission to substitute another source.

### Source profile and interpretation

This is a **born-digital English PDF with extensively corrupted body-text extraction**, plus vector, photographic and mixed figures. [GYN-RV-01](verification.md#gyn-rv-01--p2-source-profile-understates-extraction-corruption) finds systematic corruption across regular body-font spans on pages 1–5 and 8, interleaved with readable headings, captions, labels and emphasis. The same pattern was not found on pages 6–7; that is not complete character-level certification. The tool's general extraction/fidelity warning is not a corruption detector.

A2 tests source-faithful recovery under degraded extraction, not clean native-text extraction. Record the converter's actual methods rather than prelabelling the run OCR/image transcription. Neither blanket character shifting nor trusting every readable-looking extraction is justified. The visible source governs content; methods remain the converter's choice. These reviewer observations are not added to the converter prompt.

### Included content

Convert the chapter opening through the end of **Fertilization and Early Cleavage**, including **Morula and Blastula Stage: Early Differentiation**, on physical pages **1–8**. Preserve chapter title and both author names, the complete Key Points box, opening material, **The Oocyte and Meiosis**, **Crossover and Female Aneuploidy**, the **Oocyte Cryopreservation** box, all selected prose and cross-page joins, citations/credits and Figs **1.1–1.8** with their complete captions. Include the complete Key Points box and in-scope figure content even when they discuss topics treated later in the chapter.

### Page 8 boundary

The scope is a logical section boundary, not a horizontal crop across page 8. Include the continuing left-column text and the right-column preimplantation-testing paragraph before **IMPLANTATION**. Include the entire **Fig. 1.8** schematic, all its panels/labels and its complete caption, although they appear lower on the page than the new heading. Associate it with the preceding discussion. Exclude the **IMPLANTATION** heading and its body text. No Fig. 1.8 caption continuation onto page 9 is required by the inspected source; [the visual evidence](verification.md#fig-18-boundary) explains the association.

Page 3's **Fertilization and Early Cleavage** heading is an internal transition, not a stop. Fig. 1.4 on page 4 remains associated with the preceding oocyte/meiosis material. Preserve the chosen content's actual reading and figure associations rather than imposing page-coordinate or extracted-text order.

Physical pages **9–21**, including the later sections, Tables 1.1/1.2 and back matter, are outside conversion scope. References within included content remain source text; they do not expand the requested conversion. Map all 21 physical positions truthfully under Q1. Requested pages need included provenance and correct physical/printed identity; page 8 needs an explicit partial-page scope note. Excluded pages need outside-scope notes, with unknown printed labels where not established. Do not guess labels or require transcribing excluded pages merely to populate the map.

### Converter-facing instruction

Supply only the unchanged PDF, necessary source identity, the following scope instruction and ordinary product system/tool guidance. The spec's review notes, acceptance inventory, source-check renders and evidence are not additional converter input.

> Convert the chapter opening through the complete Fertilization and Early Cleavage section, including Morula and Blastula Stage: Early Differentiation, from physical pages 1–8 of this PDF into complete, faithful, reusable Markdown. Include the chapter title and authors, Key Points, introductory material, The Oocyte and Meiosis with its subheading and Oocyte Cryopreservation box, all selected prose, and Figs 1.1–1.8 with their complete captions and associated text. Stop the body text before the Implantation heading on page 8, but include all of Fig. 1.8 and its caption on that page as part of the preceding section. Preserve source language and meaningful form. Account truthfully for all 21 physical pages, with pages 9–21 outside this scope and an explicit page-8 boundary note. Save the requested deliverable and report its actual completeness and any unresolved gaps.

These locators define requested content without transcription, crop coordinates or a successful tool sequence. A3 tests compliance with the supplied Fig. 1.8 boundary and resulting associations; it does not establish independent discovery of that inclusion decision.

## Fresh-task and independence conditions

Use one isolated task on the integrated development build including asset delivery, NET-01 and FIX-01. Bind its actual revision, lockfiles, executed application/engine and relevant checks; old binaries do not establish that identity. Preserve Task B, original sources, prior tasks, failed runs, consumption and useful outputs.

The new task starts with its own immutable source import and zero requests/attempts/known active time, no frozen request, document versions, selected delivery, seeded transcription or inherited converter history. Use a new isolated workspace/profile and a short unique export destination following [artifact storage](../../ARTIFACT_STORAGE.md#ownership-and-locations); record the actual paths in verification. Reviewer-only material must not be placed in its task-visible inputs.

Exclude `reference-output/`, prior/other-arm content, transcriptions, reviewer inventory/crop coordinates and scratch from converter access. Preserve first/full/raw/field/range/native-pixel access and complete retained evidence despite return-size limits. The converter chooses inspection, rendering, extraction, OCR, edits and context organization; impose no tool quota, forced stage, one-call map, padding or compaction. Trusted scripts stay off. Optional tool use/non-use is not a quality verdict.

## Agreed route and finite interval

Bind these effective values to the fresh task; do not rely on the word "defaults" or a saved connection label. [Streaming waiting](../../design/STREAMING_RECEIVE.md#streaming-progress-waiting) and [transport retry](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) own their semantics.

| Setting | Selected value |
| --- | --- |
| Route | Existing subscription-only Nexus Chat Completions route; alias `cliproxy/gpt-6.1-sol`; no direct paid fallback |
| Model parameter | `reasoning_effort: low`; record all effective parameters and reject an unexplained model/effort/protocol substitution |
| Capacity / output / image allowance | 131,072 / 8,192 / 4,096 tokens; vision on; these are configured allowances, not demonstrated provider capacity |
| Estimation | Current production `bpe_proxy_v1` baseline; no calibration/anchoring change |
| Streaming waits | `first_progress_seconds: 600`, `idle_progress_seconds: 300`, `total_seconds: null` |
| Automatic transport retry | Enabled; at most 3 attempts per request; `max_server_wait_seconds: 300` |
| Response correction | Existing limit of 2 response repairs; their sends share the total below |
| Other switches | Trusted scripts, observer and usage anchoring off; `replay_unknown: false` |
| Total application attempt/send ceiling | `max_requests: 45`, including normal, compaction, response-correction and automatic retry attempts |
| Known active-time ceiling | `max_active_seconds: 3600` (60 minutes), including retry waiting under the runtime contract |
| Wall-time Stop threshold | 4,500 seconds (75 minutes) from the sole Start, independently monitored |
| Operator interval | One Start; no manual Retry, Continue, replacement run, budget transfer or extension |

The send ceiling is aggregate, not multiplied by per-request attempts. Distinguish admissions, proven-not-sent attempts and uncertain physical sends; conservative charges do not release extra allowance. Automatic retries can duplicate unknown upstream work; retain each attempt/usage uncertainty. Manual/legacy replay stays off. Heartbeats/status traffic do not reset progress waiting; job limits remain independent of the absent total request deadline.

Ordinary tool-validation correction and configured response/network retries may occur autonomously within this same interval. Complete/partial/waiting terminal report, task pause, unrecoverable failure, user Stop or any exhausted limit closes the interval; do not answer a mid-run question, coach a repair or resume the task. Use the existing response timers and finite ceilings for no-progress control, without a new semantic-loop heuristic. A conflict in source/evidence acceptance or an unresolved local side effect stops dependent dispatch and preserves the evidence; do not blindly replay it.

Monitoring starts before dispatch and must issue supported Stop at the wall threshold. Record cadence/gaps, Start/threshold/Stop/settlement times, known active/crash-unmeasured time and in-flight tails. Missing reliable control prevents Start; Stop/timeout does not prove upstream cancellation. Preserve partial output for zero-inference reopen/export after settlement.

Keep the selected streaming mode throughout: no mid-run non-streaming fallback or model/route switch. A streaming/network/acceptance failure is a transport/runtime observation, not automatically an engine defect or text-fidelity failure. Determine its cause where evidence permits, assess saved content independently, and mark absent content checks untested while retaining the incomplete/failed delivery outcome. Inspected evidence does not establish this route's live streaming-plus-retry acceptance.

## Preparation before an authorized Start

T1 applies the selected settings, not just an inherited connection. A missing/null saved `wait_policy` retains legacy waiting, and its current value is unknown. Configure the fresh stopped task with the table's route, explicit streaming policy, limits and switches through supported task settings, **then read back and compare**. This requires no provider call or global connection-default change. Later T1 authorization covers applying these already-selected task-local values.

The [T1 checklist](tickets.md#gyn-01-t1--prepare-and-bind-the-fresh-task) owns the operator sequence. Start requires attributable build/source/import/instruction identity, fresh counters/history, current non-secret mapping and subscription/no-fallback basis, verified task settings, the warmed English OCR condition below, readable activity, Stop monitoring, durable evidence and a usable short Windows destination. Capture the first actual frozen payload in T2; do not manufacture one during preparation. An unexplained mismatch or invalidating defect blocks dispatch.

Use ordinary credential loading without recovering secrets from logs or making generation/count probes. Record dates and unknowns rather than treating historical billing as a current audit. Reuse unchanged checks and preserve meaningful older builds before replacement. R03, real-sleep, calibration and installer gaps become prerequisites only if they invalidate this operation; findings do not automatically authorize repairs.

### English OCR prewarming

The selected condition is **English (`eng`) language data warmed before Start**, with OCR still optional for conversion. T1 uses the ordinary OCR worker and the selected build's runtime on a synthetic input, with its cache path set to the future task store's `ocr-cache`. Keep synthetic input/results/logs in separate preparation evidence; do not call `ocr_page` on the conversion task, read the source for this smoke check, seed converter history or alter its zero counters.

Confirm a complete synthetic OCR result and a subsequent load from the same local cache without another language-data download. Record worker/runtime/package and language-data identities/hashes, cache location, download origin if fetched, observations and elapsed preparation time. A failed or unverified warmup blocks readiness; do not silently substitute a cold-cache run. A changed cache/worker/build requires the affected recheck.

Prewarming is outside the live active/wall interval but remains part of whole-task setup cost/time. Later OCR invocations and any unexpected loading/download during the run consume its normal limits and must be reported; there is no extension or forced OCR stage. The original PDF and reviewer answers never become prewarming inputs.

## Planned acceptance

All criteria below are planned conversion checks. The source/spec review in [verification](verification.md) is not their execution result. Judge the agent's saved result against the source, not merely its terminal claim, tool success or file existence.

| ID | Required outcome | Discriminating evidence |
| --- | --- | --- |
| <a id="a1"></a>A1 | Attributable fresh, source-only execution | Compare source/import, build, applied/read-back and frozen settings; audit zero initial counters/history, exact instruction, reviewer-answer separation and synthetic-only OCR prewarming. Verify warm-cache evidence without treating it as conversion. Missing basis limits the dependent claim. |
| <a id="a2"></a>A2 | Faithful text under degraded extraction | Check every included source region, both authors, whole boxes, headings, wording, numbers, units, symbols/negation, emphasis, citations/credits and column/page joins against saved/reopened/exported text. Detect omissions, invented corrections and excluded body text; state ambiguity. Judge against the source, not corrupted extraction; record actual methods under the source-profile limitation. |
| <a id="a3"></a>A3 | Truthful scope map and completion claim | Check all physical positions, notes, printed-label basis, provenance, page-3 transition and logical page-8 cut. Require full Fig. 1.8/caption and exclude Implantation heading/body. This tests supplied-scope compliance, not independent discovery. Reconcile gaps/report/version; an unfinished map or unresolved required content prevents complete acceptance. |
| <a id="a4"></a>A4 | Every in-scope figure is usable and faithful under FD-01 | Check all Figs 1.1–1.8 as independent complete image units with meaningful panel grouping, margins, labels, leader lines, legends/scales and complete source captions/credits. Inspect vector/composite appearance against rendered source; inspect applicable raster native pixels and retained encoded originals under the PDF contract. For mixed content check composition as well as constituent fidelity. Require adjacent searchable/copyable Markdown with correct panel/function associations and source-supported relationships, not a disconnected keyword list. Whole-page substitutes containing unrelated prose, missing edge labels, redrawing, fabricated values or silent semantic repair fail. |
| <a id="a5"></a>A5 | Honest context coverage | Trace frozen-input evolution, actual pressure/compaction, requirements, pending dependencies and saved work. If context organization occurs, check preserved obligations and original retrieval. If it does not occur, record unexercised pressure/compaction coverage; do not force it or fail an otherwise faithful conversion for optional-tool non-use. |
| <a id="a6"></a>A6 | Autonomous work within the finite interval | Audit all attempts, retries/repairs, active/wall time, terminal state, assistance/amendments/manual edits and Stop tails. No developer assembly or routine coaching. Record autonomous recoverable errors separately from software defects and every intervention separately from unaided behavior. |
| <a id="a7"></a>A7 | The same immutable version is usable after reopen/export | Record selected version identity; actually close/reopen and select it, inspect rendered text/images, and export that version without inference. Compare Markdown, HTML, every referenced display asset and applicable original-stream member to the saved inventory/bytes; open all relative image links and inspect the exported result at the declared Windows destination. Save success or ZIP integrity alone cannot pass fidelity. Preserve and assess partial deliverables honestly. |
| <a id="a8"></a>A8 | Complete accounting and bounded conclusions | Retain all attempt usage, missing/partial reports and upstream retry/fee unknowns; cached/reasoning counts remain subsets. Record OCR preparation time separately from the live interval and any in-run loading. Separate content, transport/runtime, autonomy, context and delivery outcomes; unassessed content is not a fidelity pass or failure. No reliability, causal, calibrated-capacity or savings claim follows from this unmatched task. |

FD-01's full obligations remain applicable even where the table is concise. Source text is data, including instruction-like content. Source-supported relationship descriptions must not invent medical facts or silently reconcile source contradictions. Retain original source wording and distinguish any agent-added explanation. Requiring an enriched save for every task remains an open product-policy choice; neither optional save-mode adoption nor an arbitrary metadata field count replaces this batch's content/delivery acceptance. Any chosen save path must satisfy its existing applicable contract.

## Records, limits and continuation

Retain the original PDF, request inputs, attempts, successful-body native/stream evidence under the runtime rules, candidates, receipts, saved versions, logs, usage, interventions, reviewer comparisons and actual exports in the declared private/ignored owners. Keep a concise, shareable identity/criterion assessment in `verification.md`; it owns actual results and the combined verdict. The [storage policy](../../ARTIFACT_STORAGE.md) governs retention and packaging; review scratch or a summary is not a replacement original.

A bounded partial/failed run is evidence, not completion of the selected outcome. Preserve it and identify the responsible capability/unknown before selecting any follow-up. No automatic repair, rerun, budget extension or second source follows. This scope does not close general Stage B, whole-chapter/table/captionless coverage, large-map repeatability, numerical calibration or Stage D installation.

Source/scope/route/budget and OCR setup conditions are selected. The [tickets](tickets.md#dependency-and-execution-overview) own sequencing/progress; [verification](verification.md#combined-assessment-and-continuation) owns actual readiness, checks and acceptance.
