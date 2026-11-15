# Stage B source-led conversion: discussion

## Current question and authority

2026-11-15 (Asia/Singapore). After the [FIX-01 post-merge review](../batches/FIX-01/verification.md#post-merge-review-and-orientation), the user asked to discuss Stage B. This file owns the discussion of the next source-led conversion batch toward the [Stage B outcome](../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources). It builds on the [recommendation after NET-01](NETWORK_RECOVERY.md#next-step-recommendation-after-net-01). [WORK_ITEMS](../WORK_ITEMS.md#selection-now) keeps selection.

The initial discussion and later specification/ticket work remain in the dated selections below. The latest [T1 and publication selection](#t1-preparation-and-draft-pr-selected-2026-11-15) authorizes preparation and a draft PR; the live interval remains unselected.

## What the earlier runs already show

- **Complete-section map (R01CAL-A01).** Historical Task A ended partial with pages 17–290 unclassified. The fresh [A03 run](../batches/R01CAL-A03/verification.md#t4-a1-a8-assessment) on the same 290-page source classified all 290 entries correctly without help (A3, A6). So the large-map path has one failure and one unaided success. The remedy stays unselected until a new run shows the obstruction again.
- **Text fidelity on a scanned/searchable Chinese source.** A03 passed substantive text review for five pages (A2). The T5-L1 discrepancy ([AR-T5-14](../batches/R01CAL-A03-DELIVERY-01/verification.md#ar-t5-14--contributor-name-differs-from-the-visible-source)) and the later [T5-L2 source-led review](../batches/R01CAL-A03-DELIVERY-01/verification.md#t5-live-re-run-after-the-guidance-clarification) must both inform selection. T5-L2 converted the covers and title page, physical pages 1–3; that review found no substantive discrepancy and specifically confirmed the contributor name. It was not another five-page news-writing section or an independent-figure test. The later bounded success does not erase the earlier transcription failure or establish general fidelity.
- **Figures (FD-01).** A03 had no independent figure (A4). The only figure evidence is the 2026-11-01 [two-page Nursing check](../verification/20261101_0103_FD01_TWO_PAGE_LIVE.md), from before the asset-delivery batch and NET-01. Vector diagrams, multi-panel micrographs, tables and forward figures on later pages are untested on the current build.
- **Delivery chain.** Saving, reopening and exporting with portable asset links passed on Windows in the [asset-delivery final verdict](../batches/R01CAL-A03-DELIVERY-01/verification.md#t5-final-verdict). They have not been exercised with independent figure assets from this born-digital English source.

Figure delivery on the current build and source-text recovery under the [qualified extraction profile](../batches/GYN-01/spec.md#source-profile-and-interpretation) offer useful next coverage. This is an evidence-gap recommendation, not a measured ranking of failure rates. A03 establishes that an unaided complete large map is possible on its source; repeatability remains unestablished.

## Local source facts

Read on 2026-11-15 with PyMuPDF (page text length, image and drawing counts, headings by font). These are layout facts, not content claims. `reference-output/` folders exist and stay reviewer-only.

**`references/gynecology/source.pdf`** (21 pages, SHA-256 recorded in the [Task B plan](REQUEST_CAPACITY.md#selected-source-scopes-and-inspection-evidence)). This is chapter 1, *Fertilization and Embryogenesis*, a born-digital English source with an author line and text layer. The initial 2026-11-06 inspection identified garbling; the later [font-span review](../batches/GYN-01/verification.md#gyn-rv-01--p2-source-profile-understates-extraction-corruption) establishes its broader extent. Use the [current source profile](../batches/GYN-01/spec.md#source-profile-and-interpretation), not the earlier impression of occasional damage, when interpreting the planned run.

| Section (heading) | Pages | Figures and tables | Figure character |
| --- | --- | --- | --- |
| Chapter opening, Key Points, The Oocyte and Meiosis (with Crossover and Female Aneuploidy) | 1–3, with forward figure on 4 | Fig. 1.1–1.4 | p2 vector diagrams, p3 raster micrograph, p4 forward meiosis diagram |
| Fertilization and Early Cleavage (with Morula and Blastula Stage) | 3–8 | Fig. 1.5–1.8 | p5 dense vector summary (~2,600 drawing operations), p6 vector diagram, p7 six-photo grid, p8 mixed schematic (~780 small images and ~4,000 drawings) |
| Implantation (Decidualization, Embryo-Endometrial Communication, Immunology, Early Organogenesis) | 8–10 | Table 1.1, Fig. 1.9 | table, micrograph |
| Development of the Genitourinary System; Molecular Basis of Sex Differentiation; Genital Development; External Genitalia | 11–20 | Fig. 1.10–1.16, Table 1.2 | vector diagrams, micrographs, SEM images, table |
| Back matter | e1 | — | — |

**`references/news-writing/source.pdf`**: 290 pages, one page image per page with a thin text layer. This is the Task A/A03 source.

**`references/nursing/source.pdf`**: 14 pages of native text, two images per page. This is the historical Nursing source.

The prepared Task B (`327179798c14475f8000a69a75a353f6`) is frozen on the 2026-11-06 build. It predates asset delivery and NET-01 and stays untouched.

The later [GYN-01 visual check](../batches/GYN-01/verification.md#source-identity-and-layout-check) qualifies the preliminary layout table and owns the confirmed Fig. 1.8 boundary. The table's figure grouping now reflects association rather than the page on which the next body section begins.

## Decisions for the user

The assistant's original recommendations are retained below. All four were open at that point; the [answers](#user-answers-2026-11-15) and later selections qualify their status. The original native-text description is superseded by the [current source profile](../batches/GYN-01/spec.md#source-profile-and-interpretation).

**D1 — Source and class.**

- *Recommended:* gynecology, native English text with figures. One run tests native-text fidelity, including the garbled-extraction passages, the author line (the AR-T5-14 kind of check), FD-01 across vector, raster and mixed figures, and the delivery chain with real figure assets. Limit: its 21-page map does not stress the large-map case.
- Alternative: a new news-writing section (scanned/searchable class, CTX-08). This retests the 290-page map and Chinese names, but it repeats a class A03 already covered and has few figures.
- Alternative: both, gynecology first, then news-writing as a separately selected run.

**D2 — Scope** (all are complete logical units; the agent must map all 21 pages truthfully).

- (a) Task B's defined scope in a fresh task: chapter opening through The Oocyte and Meiosis, pages 1–3, plus the forward Fig. 1.4 and its caption on page 4. Four figures, already inspected, cheapest.
- (b) *Recommended:* chapter opening through Fertilization and Early Cleavage, pages 1–8, stopping before Implantation on page 8. Eight figures, adding the dense vector summary, the photo grid and the mixed schematic, plus two partial-page section boundaries (pages 3 and 8). This is a larger workload than (a); its whole-task cost is unmeasured. It may reach context pressure naturally, which would exercise context organization (PHASE_PLAN's context condition). Preparation must confirm from the rendered pages which section Fig. 1.8 belongs to.
- (c) Whole chapter, pages 1–20 plus e1: 16 figures and two tables. Broadest, but several times the cost, and a failure is harder to attribute.

**D3 — Fresh task.** *Recommended:* a fresh task on the current `master` build, with Task B left frozen. Only the source PDF and the scope instruction go to the converter.

**D4 — Route, waiting and budget.**

- Model: `cliproxy/gpt-6.1-sol` with `reasoning_effort: low`, the user's [2026-11-06 choice](REQUEST_CAPACITY.md#model-and-preserved-behavior), unless the user wants a higher effort for figure work. The mapping is verified before dispatch.
- *Recommended:* the current product defaults for new connections. Streaming progress waiting (600 s to first progress, then 300 s), three attempts per request for temporary network failures. A02/A03 used the non-streaming 180 s deadline. Using the defaults tests the build users get; A03 is not a matched arm anyway. Any retry is incidental evidence, not the separate live route check.
- Unchanged: context 131,072, output 8,192, image allowance 4,096, vision on, production calibration, trusted scripts off, observer off.
- Budget proposal, one Start, no Continue, no extension:

  | Scope | Physical sends | Known active time | Wall-time Stop |
  | --- | --- | --- | --- |
  | (a) | 12 (the accepted Task B plan) | 1,200 s | 1,500 s |
  | (b) | 30 | 2,400 s | 3,000 s |
  | (c) | 60 | 4,800 s | 6,000 s |

  For calibration of these numbers: A03 used 6 sends and 250 s for five text-only pages. Figures add renders, crops and edits. These caps are finite opportunities, not predictions. Billing goes through the existing subscription route, verified before dispatch.

**Can wait for the run's evidence:** whether to require enriched saves ([open choice](ASSET_REFERENCES.md#t5-final-route-and-merge-approved)) and any REPLY-AUTO-01 remedy.

## Planned acceptance (for the spec)

This is the discussion-stage proposal retained as the basis. The [GYN-01 acceptance criteria](../batches/GYN-01/spec.md#planned-acceptance) now own the selected batch's planned checks.

Each condition comes from the [Stage B completion conditions](../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) and [FD-01](../design/FIGURE_DELIVERY.md#required-outcome):

1. A saved deliverable for the full requested scope without developer help. Every intervention is recorded.
2. Source-led review of wording, units, symbols, reading order, the author line and section boundaries, especially where extracted text is garbled.
3. Each in-scope figure delivered as an independent, faithful asset with its complete caption, substantive labels and source association. Vector figures are judged against the rendered page; raster figures against native pixels.
4. A truthful 21-page map with correct physical and printed page identity.
5. The saved version, the reopened app and the exported Markdown, HTML and assets agree, with working relative links.
6. Accounting and limits are recorded honestly: sends, active time, retries, unknown fees and context events.

## User answers (2026-11-15)

The user answered in the question dialog:

- **D1:** gynecology.
- **D2:** pages 1–8, chapter opening through Fertilization and Early Cleavage, Figs 1.1–1.8, stopping before Implantation on page 8.
- **D4 route:** current defaults for new connections with `cliproxy/gpt-6.1-sol`, reasoning effort Low.
- **D4 budget:** looser, about 1.5× the proposal. For scope (b) that is **45 physical sends, 3,600 s known active time and a 4,500 s wall-time Stop**, with one Start, no Continue and no extension.

D3 was not asked separately at this point and remained the assistant's recommendation for the spec. A fresh task would preserve the prepared Task B and give the new scope/build/settings their own execution identity. D4 does not itself establish a technical requirement for a fresh task: the [current settings contract](../design/RUNTIME_AND_DELIVERY.md#existing-task-settings-and-active-time-accounting) permits waiting/retry changes for newly prepared requests on a stopped task while preserving existing frozen requests. Reusing or migrating Task B was not assessed or selected. The [subsequent specification instruction](#specification-selected-2026-11-15) explicitly selects a fresh task.

These answers settle the batch's direction. They do not authorize a Start or provider call; that needs a separate selection once the spec and preparation are ready.

## Status

The current selected agreement is [GYN-01](../batches/GYN-01/spec.md). Its [verification and continuation](../batches/GYN-01/verification.md#combined-assessment-and-continuation) own actual checks and readiness; the [preparation gate](../batches/GYN-01/spec.md#preparation-before-an-authorized-start) defines remaining operational bindings. The discussion below preserves the earlier review and later instruction basis.

## Comment review (2026-11-15)

This subsection records the earlier comment review, before the [subsequent specification selection](#specification-selected-2026-11-15).

**Scope and conclusion.** The user requested comment on the Stage B summary. Review compared its claims with the maintained A03, T5-L2, FD-01 and runtime evidence, the relevant work-register comparison and Stage B conditions. Gynecology remains a well-supported next source for specification: it adds figure classes and native-text checks that the news-writing runs do not supply. This review does not authorize a spec, task preparation or a provider interval.

- **SC-RV-01 — incomplete use of the later rerun.** The original summary carried forward AR-T5-14 without the later successful observation. The [earlier-runs discussion](#what-the-earlier-runs-already-show) now reconciles both and explains the coverage difference. Its evidence-gap recommendation also avoids treating one successful large map as repeatability proof or limited figure testing as a demonstrated higher failure rate.
- **SC-RV-02 — inferred task choice.** The original D3 explanation conflated preserving an old prepared task with inability to change task settings. The [answers record](#user-answers-2026-11-15) now preserves D3 as a recommendation and links the actual frozen-request boundary. This changes no task or agreed route/budget.
- **Specification carry-forward.** Apply the full [FD-01 outcome](../design/FIGURE_DELIVERY.md#required-outcome), including complete panels/edges, adjacent searchable caption and label text, and source-supported relationships; an image that looks correct alone is insufficient. Review mixed figures against the rendered composition as well as applicable raster originals. Confirm Fig. 1.8's association and caption extent before freezing the scope; surface any conflict with the selected section boundary rather than silently excluding content. Natural context-pressure coverage is conditional under [Stage B](../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources). The agreed caps bound an opportunity; they do not predict cost or establish parity with A03.

**Documentation impact and limits.** This discussion corrects the evidence summary, D3 attribution, the initial-open-choice wording and the unsupported cost ratio. CURRENT_STATE routes to this review. INDEX already discovers this owner; WORK_ITEMS retains its comparative selection and provider-authority boundary, and PHASE_PLAN's acceptance is unchanged. Their relevant routes were checked without copying this review into them. Source hashes/layout, Fig. 1.8, private route/billing settings and effective task settings were not rechecked here; they remain preparation work. No application test, app launch, task creation, configuration read or provider call occurred. The repository documentation/link check returned zero errors, and Git whitespace checks passed. These checks do not establish source-layout or runtime acceptance.

## Specification selected (2026-11-15)

The user requested the Stage B spec for gynecology pages 1–8, explicitly **using a fresh task** and the agreed route/budget, incorporating the review qualifications and confirming Fig. 1.8's boundary, with the instruction **"Don't start the live run yet."** This settles D3 by current human choice. It selects specification and the necessary offline PDF check, not application-task creation or a provider interval.

[GYN-01/spec.md](../batches/GYN-01/spec.md) owns the selected scope, fresh-task conditions, route/limits and planned acceptance. [The source-boundary evidence](../batches/GYN-01/verification.md#fig-18-boundary) owns the visual finding; the scope needs a logical section boundary because the required figure sits below the excluded heading's vertical position. No scope expansion or new fidelity policy is selected. Source-review material remains reviewer-only. The [batch review](../batches/GYN-01/verification.md#specification-review) records the qualifications and remaining operational gaps.

## Local ticket planning selected (2026-11-15)

The user requested local GYN-01 tickets covering preparation, the bounded live run and source-led verification, explicitly **keeping this to planning and not creating the application task or starting the run**. This selects task decomposition under the existing spec without changing source, scope, fresh-task choice, route, allowance or acceptance.

[The local tickets](../batches/GYN-01/tickets.md#dependency-and-execution-overview) own responsibilities, dependencies, handoffs and progress. [The planning review](../batches/GYN-01/verification.md#ticket-planning-review) owns observed document checks. This instruction grants no operational preparation, provider call, product repair or publication authority; the task plan describes those later activities within their applicable boundaries.

## Documentation corrections selected (2026-11-15)

2026-11-15 (Asia/Hong_Kong). The user selected the supported GYN-01 review corrections, planned English OCR prewarming and shorter operator steps, explicitly keeping the work to documentation with no application task or run. "Fix them first" is applied to those documentation findings within that stated boundary.

The [revised spec](../batches/GYN-01/spec.md) owns the qualified source profile, explicit task configuration/readback, separated transport/content interpretation and supplied-scope acceptance limit. [English OCR prewarming](../batches/GYN-01/spec.md#english-ocr-prewarming) selects warm language data before Start using a synthetic input: setup time remains recorded, while conversion methods stay autonomous. This chooses the warm-cache condition over an undeclared first-use download during the timed run; it does not authorize downloading now.

The existing [T1–T3 tickets](../batches/GYN-01/tickets.md#dependency-and-execution-overview) cover the preparation and result checks, with one operator checklist per ticket. No separate software repair is justified by these documentation findings. Source, section boundary, model, budget and content-fidelity requirements remain selected as before. [Amendment verification](../batches/GYN-01/verification.md#documentation-correction-review) owns correction evidence and remaining limits; historical reviews retain their original observations.

## Local Git checkpoints selected (2026-11-15)

The user accepted a GYN-01 branch with separate commits and requested comment on the follow-up review. This selects local Git checkpoints separating the inherited FIX-01 review from GYN-01 planning. [The follow-up assessment and checkpoint record](../batches/GYN-01/verification.md#follow-up-review-and-local-git-checkpoints) own the review qualification, actual Git actions and checks. T1 preparation and remote publication remain unselected.

## T1 preparation and draft PR selected (2026-11-15)

2026-11-15 (Asia/Hong_Kong). The user agreed to publish the records through a draft PR and explicitly selected GYN-01 T1: create the isolated fresh task, apply and verify the agreed settings, prewarm English OCR, and report readiness/blockers without starting the live run. The selected prewarming includes the ordinary worker's language-data download. T2/T3 execution and merging remain unselected. [Ticket progress](../batches/GYN-01/tickets.md#dependency-and-execution-overview) and [T1 evidence](../batches/GYN-01/verification.md#t1-preparation-and-publication) own execution and results.
