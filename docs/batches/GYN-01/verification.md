# GYN-01 verification

## Scope and inspected basis

2026-11-15 (Asia/Singapore). This record covers the offline source-boundary and specification work requested in [the spec](spec.md#status-and-authority). It does not record a conversion run. The checkout was `codex/fix-01-closeout` at `0417061f7f21b602de85690e950ab3b58d1801b4`; product/test/tool/manifests/lockfile paths had no diff from local `master`. Existing CURRENT_STATE, INDEX, FIX-01 verification edits and the untracked source-conversion discussion were preserved. No build, application test, task creation, app launch, private configuration read or provider request was made.

## Source identity and layout check

The available `references/gynecology/source.pdf` contains **21 pages**, **7,270,474 bytes**, with SHA-256 **`02b75c73392265549e911152312e4727d81d6446eef28906d66330873df0d420`**, matching the [recorded source](../../discussions/REQUEST_CAPACITY.md#selected-source-scopes-and-inspection-evidence). The digest was checked before and after rendering/inspection; source bytes were not changed.

Poppler `pdftoppm` 26.07.0 rendered complete physical pages 1–6 at 105 DPI and 7–9 at 145 DPI. All nine pages were visually inspected for scope, figure identity and layout; this is not a glyph-by-glyph transcription review. PyMuPDF 2.0 confirmed inventory and supplied supporting text reads. Its page-8 text layer visibly contains garbled strings while the rendered text is legible. An initial console print failed on the Windows `cp1252` encoding; an explicit UTF-8 rerun succeeded. This affected the inspection helper's output only, not the PDF or converter behavior.

Reviewer-only PNGs and `source-check.json` with source/render hashes are retained in ignored `.local/sc01-spec-20261115-8f7fb7f8/`. They are not deliverables or converter inputs. Private source/render availability is required to repeat the visual inspection; the substantive boundary conclusion is recorded below so ordinary project reading needs no private export.

| Physical page | Scope/layout observation |
| --- | --- |
| 1 | Chapter title, two author names, full Key Points box, introductory material and start of The Oocyte and Meiosis; printed page 1 is visible. |
| 2 | Figs 1.1 and 1.2 are distinct figures; the graph and linked meiosis diagram require separate usable units and associated text. |
| 3 | Fig. 1.3 has four photographic panels. Crossover and Female Aneuploidy and the Oocyte Cryopreservation box precede the Fertilization and Early Cleavage heading. Both sides of that internal transition are selected. |
| 4 | Fig. 1.4 is a forward meiosis figure associated with preceding material; later-section body text below it is also selected in this larger scope. |
| 5 | Fig. 1.5 is a dense integrated diagram; Morula and Blastula Stage: Early Differentiation begins in the later body text. The complete figure/caption remains included, including its discussion of implantation. |
| 6 | Fig. 1.6 contains related A/B views and numbered relationships; grouping matters. |
| 7 | Fig. 1.7 is a six-photo A–F grid with its complete caption/credit below it. |
| 8 | Continuing selected prose, the preimplantation-testing paragraph and Fig. 1.8 share the page with the excluded Implantation opening; see the boundary below. |
| 9 | Implantation continues, with Table 1.1 and later text. No continuation of Fig. 1.8's caption appears here. Outside the selected conversion scope. |

### Fig. 1.8 boundary

**Confirmed: Fig. 1.8 belongs with the selected preceding section.** On page 8 the preimplantation genetic testing paragraph starts at the bottom of the left text column and continues at the top of the right column, where it refers to Fig. 1.8. It ends before the **IMPLANTATION** heading. The schematic occupies the lower page and is captioned **Schematic of preimplantation testing**, with panels A–D and a complete caption on page 8.

The heading and opening body paragraph of Implantation lie vertically above part of the schematic. Therefore a simple horizontal cutoff at the heading would wrongly omit the required figure. [The normative scope](spec.md#page-8-boundary) includes the entire figure/caption and selected preceding prose while excluding that new heading/body. Page 9 confirms the later-section continuation rather than a missing figure-caption tail. This resolves the stated boundary check without changing the user's requested figure range or adding another conversion page.

## Specification review

The spec was checked against the user's selected D1/D2/D4 and explicit fresh-task instruction, [SC-RV-01/02](../../discussions/SOURCE_CONVERSION.md#comment-review-2026-11-15), the applicable Stage B conditions and FD-01/PDF/runtime owners. It preserves the T5-L1 failure alongside T5-L2's later bounded success, limits the A03 map inference to feasibility, and separates the selected fresh task from a technical settings restriction.

The acceptance table links the complete scope, map, source text, figures, conditional context coverage, unaided finite execution, exact-version delivery and honest accounting to observable checks. Page-8 layout provides the negative case against a geometric section cut; the multi-panel figures provide grouping/edge/adjacent-text cases. No minimum tool adoption or forced context exercise is substituted for content acceptance.

The current `Limits` schema supplies the recorded repair/retry defaults. Nexus compares admitted attempts against `max_requests`; consequently the spec makes automatic retries part of the aggregate 45-attempt/send ceiling, not a multiplier. These static reads establish intended binding, not a configured new task or live enforcement result. The existing waiting/retry owners define semantics; no framework implementation or version change was made.

**Operational gaps.** Current upstream model/account mapping, subscription/no-fallback facts, actual future build/task settings, fresh import/state, Stop monitoring and destination readiness remain unverified and belong to [preparation](spec.md#preparation-before-an-authorized-start). No new provider call is required merely to inspect configuration. Captionless/table/whole-chapter coverage, 290-page repeatability, natural compaction if not encountered, and installer acceptance remain outside this result.

## Documentation impact and checks

The spec owns the selected workload, interval and planned acceptance; this file owns observed source/spec checks. SOURCE_CONVERSION preserves the new selection and routes current scope to the batch, including the resolved boundary and D3 attribution. WORK_ITEMS records the distinct source-selection rationale and residual/revisit conditions; INDEX registers the new spec/verification and topic route; CURRENT_STATE points to the completed specification and its unstarted execution boundary. PHASE_PLAN, product contracts and README retain their existing meaning: no product behavior or phase acceptance changed. The earlier FIX-01 verification edits remain untouched.

`python tools/docs/check_docs.py` returned zero errors across the maintained documentation, links and source-integrity checks. Git whitespace checks passed for tracked edits and the new discussion/spec/verification files. The private PDF and source-review directory remain ignored. A final meaning check traced the selected scope and limits to their spec owner, the Fig. 1.8 conclusion to its source evidence, and the entry/catalogue/work-register links to their respective responsibilities. These checks do not establish runtime or content-delivery acceptance.

## Ticket planning review

2026-11-15 (Asia/Singapore). The user selected local tickets only under the [planning instruction](../../discussions/SOURCE_CONVERSION.md#local-ticket-planning-selected-2026-11-15). The [task plan](tickets.md#dependency-and-execution-overview) separates preparation, the single bounded interval and source-led/same-version verification. Its dependencies and shared evidence handoffs were reviewed against the existing spec and Stage B conditions; no new source inspection or runtime check was performed.

The plan assigns one main operator/reviewer/integrator and keeps conversion content with the app's agent. It covers A1–A8 through linked spec criteria, preserving the Fig. 1.8 logical boundary, all-figure and all-page-map coverage, the aggregate retry budget and conditional context assessment. T1 supplies an effective-settings/fresh-state preparation record without manufacturing a frozen request; T2 supplies the actual frozen payload and settled evidence. T3 can assess a partial/failed interval without treating success as a dependency, and no saved version leads to an explicit unavailable delivery check rather than developer assembly. Completing a review ticket remains distinct from accepted conversion.

**Documentation impact.** `tickets.md` now owns work descriptions, responsibilities, dependencies and progress. The spec links that owner and reflects planning-only authority without changing its requirements or numerical settings. SOURCE_CONVERSION preserves the new instruction; INDEX registers the execution owner; WORK_ITEMS links the task plan without copying ticket status or changing relative priority; CURRENT_STATE resumes at the plan and the unexecuted preparation boundary. The earlier source/spec evidence, Fig. 1.8 conclusion and failed console-print observation remain intact. PHASE_PLAN, README and product contracts need no change because no behavior, phase acceptance or source scope changed. The inherited FIX-01 edits remain untouched.

`python tools/docs/check_docs.py` returned zero errors for the planning document set and its links/source-integrity checks. Git whitespace checks passed for tracked edits and the new discussion/spec/tickets/verification files; the superseded future-ticket wording is absent from the active spec, catalogue and register. These checks validate documentation structure and consistency, not execution readiness. No application task, app launch, build, configuration read/write, provider call or conversion occurred during this planning round.

## External comment review

This is the review before the [selected documentation correction](#documentation-correction-review); its recommendations and readiness qualification retain that historical scope.

2026-11-15 (Asia/Singapore). The user supplied a review with two P2 findings, three P3 improvements and an uncommitted-work observation. This response checked the current spec/tickets, source extraction, relevant engine/UI/OCR code and the NET-01 evidence boundary. It is a standalone assessment and record update, not execution or selection of the proposed amendments. The checkout remains `codex/fix-01-closeout` at `0417061f7f21b602de85690e950ab3b58d1801b4` with the previously recorded uncommitted document work.

### GYN-RV-01 — P2 source profile understates extraction corruption

**Supported, with a source-class qualification.** The unchanged PDF hash matches the source identity above. New PyMuPDF `dict` inspection found systematically garbled `JansonTextLTStd-Roman` body spans on pages 1–5 and 8, interleaved with readable bold/italic text, headings, captions and labels. This is broader than an occasional damaged passage. The prior rendered-page inspection remains the visible-source comparison basis; this review did not perform a complete transcription or a new converter run.

| Physical page | All extracted span characters | Characters in regular body-font spans containing the unusual U+0001 separator |
| --- | --- | --- |
| 1 | 5,410 | 4,882 |
| 2 | 3,618 | 2,364 |
| 3 | 6,403 | 3,975 |
| 4 | 3,372 | 2,321 |
| 5 | 2,951 | 1,687 |
| 6 | 1,177 | 0 |
| 7 | 655 | 0 |
| 8 | 3,980 | 2,213 |

These whole-page counts locate affected spans; they are not character-error rates or proof that every character in a counted span is wrong. Page 8 includes excluded body text. The reviewer's common-word before/after counts are a useful supplied diagnostic, not independently reproduced recovery/coverage evidence. Alphabetic shift patterns do not validate applying one inverse shift to all fonts, numbers, symbols or punctuation. Pages 6–7 contain no regular body-font spans in this inspection; that does not certify every extracted character there.

The PDF remains a born-digital English source with a text layer and mixed vector/raster figures. Recommended description: **born-digital English PDF with extensively corrupted body-text extraction**. The run would exercise source-faithful recovery under degraded extraction, not establish clean native-text extraction fidelity. It cannot be labelled primarily an OCR/image-transcription run before observing the converter's methods. A2's source-fidelity standard remains valid; its source-profile interpretation needs clarification. Active source descriptions in the discussion, spec and CTX-08/GYN-01 work entries need a consistent qualification before execution; the selected content scope need not change.

The claim that tools provide no warning is too broad: [PDF inspection](../../../src/pdfmd/evidence.py) returns a general warning that extraction does not certify reading order/fidelity and marks coverage as extraction only. It does not detect or diagnose this font-specific corruption. No automatic detector, source-specific decoder or extra converter coaching is selected by this finding.

### GYN-RV-02 — P2 preparation should explicitly apply the selected settings

**Supported as an operational wording gap; the asserted lack of configuration authority is not established.** [Route/limits schema](../../../src/pdfmd/schema.py) confirms missing/null `wait_policy` retains the legacy deadline, while [connection initialization](../../../src/renderer/main.tsx) preserves the saved route's missing policy. An existing connection therefore must not be assumed to acquire new-connection defaults. Its actual saved value was not read here; earlier legacy runs do not prove its present mode.

T1 says bind/verify settings but should state **configure the new task from the selected spec values, then read back and compare them**. The selected streaming/retry values already exist; a later instruction to execute preparation can cover applying those task-local settings without a new policy decision or changing global connection defaults. The [settings API](../../../src/pdfmd/server.py) can configure a stopped fresh task without sending a request; [Task settings](../../../src/renderer/features/settings/TaskSettings.tsx) exposes waiting/retry updates for a configured task. No settings operation is authorized or performed by this comment review.

The review's schema/limit observations are confirmed: `total_seconds` is nullable, automatic retry defaults on, and [Nexus admission](../../../src/pdfmd/nexus.py) charges the task's aggregate attempts against `max_requests`. Retry waiting uses active time without admitting an attempt. [NET-01](../NET-01/verification.md#combined-verdict) retains an unperformed live-route boundary; inspected evidence does not establish live acceptance of this route with both streaming and automatic retry. Calling GYN-01 the first such run ever would exceed this review's coverage.

Recommended interpretation clarification: record a streaming/network/acceptance failure as a transport/runtime observation with attributable cause or uncertainty. It is not automatically a software defect or a text-fidelity failure. Assess any saved content independently; mark content criteria untested where there is no assessable output, while retaining the overall incomplete/failed delivery outcome. Preserve the selected mode throughout the interval with no non-streaming fallback. Existing spec distinctions already support this; an explicit operator note would reduce misreading.

### GYN-RV-03 — P3 OCR cold-cache conditions need declaring

**Supported.** [The OCR call](../../../src/pdfmd/tools.py) supplies the task store's `ocr-cache` to [the worker](../../../tools/runtime/ocr-worker.cjs). Installed Tesseract loader inspection confirms cache-first language-data loading and a download on a missing cache entry. A fresh workspace is normally cold unless preparation populates it. If the converter chooses OCR, downloading/loading can consume the timed interval; local process timeouts/unknown-effect handling also apply. No OCR invocation or download was performed here.

Recommendation, not yet selected: prepare English language data through the ordinary worker on a synthetic input in the future workspace before Start, record resource identity/cache state and preparation time, and leave OCR optional. Keep synthetic preparation outputs separate from converter history and source answers. The alternative is a deliberately cold-cache run with the download included in active/wall time and identified in the result. Choose and record one condition before execution; neither justifies a compulsory OCR conversion stage or a free extension.

### GYN-RV-04 — P3 page-8 acceptance tests compliance, not unaided discovery

**Supported interpretation limit, not answer leakage.** The converter instruction explicitly includes Fig. 1.8 and its caption. This is an authorized scope locator consistent with the confirmed boundary, not a matching-range transcription or crop recipe. A3 can assess compliance, association in the saved content, map truthfulness and exclusion of Implantation body text; it cannot establish that the agent independently discovered the inclusion decision. Preserve the clear scope instruction and state that limitation in result interpretation.

### GYN-RV-05 — P3 operator usability and Git housekeeping

**Useful improvement, not a length-based validity failure.** Whitespace counts for the reviewed files are 2,605 words in the spec and 1,815 in the tickets; FIX-01 is 1,076/872. Different workloads do not create a word-count target. Repeated authority prose does obscure the operational sequence. Recommend a short T1/T2 checklist in their existing ticket sections and one shared authority paragraph, retaining the source boundary, evidence handoffs, failure exits and zero-inference verification. Do not add a second checklist with copied scope/limit values.

The supplied uncommitted-work/branch observation matches Git status. Use scoped checkpoints separating inherited FIX-01 review work from GYN-01 documentation and a descriptive GYN-01 branch when Git delivery is selected. Branch naming is not an experiment-validity blocker and does not authorize a rename, checkout, commit, push or PR here. No Git mutation was performed.

### Review disposition and document impact

The selected source, scope, fresh task, route, budget and fidelity requirements remain coherent. Recommend one bounded documentation amendment addressing GYN-RV-01/02/04, declaring the OCR preparation condition in GYN-RV-03 and simplifying the operator path under GYN-RV-05. This is not a prerequisite software-repair batch or a reason to repeat source selection. The factual source-profile correction and explicit settings operation should precede execution; the OCR condition remains an operational choice.

This review preserves the supplied claims and their qualifications here. WORK_ITEMS and CURRENT_STATE route to this assessment; the ticket closeout links the new qualification. WORK_ITEMS also replaces the unqualified native-text label with the source-profile review link. The effective spec/ticket procedures have not been rewritten or their recommendations adopted by this standalone review. Earlier source/spec/planning observations retain their original basis. Product contracts, PHASE_PLAN and README are unchanged. No application task, provider call, configuration change, OCR download or product test occurred. The repository documentation/link check returned zero errors; tracked and new review-document whitespace checks passed. These checks establish neither operational readiness nor conversion acceptance.

## Documentation correction review

2026-11-15 (Asia/Hong_Kong). The user selected the [documentation corrections](../../discussions/SOURCE_CONVERSION.md#documentation-corrections-selected-2026-11-15), English OCR prewarming as a planned preparation condition, and shorter operator steps. The appended request to fix the issues first was applied within the explicit documentation-only boundary. No separate software-repair ticket was needed: the reviewed gaps concern source characterization, preparation instructions and interpretation, and the existing T1–T3 tasks cover the selected changes.

| Finding | Correction and evidence destination | Disposition |
| --- | --- | --- |
| GYN-RV-01 | [Source profile](spec.md#source-profile-and-interpretation) and [A2](spec.md#a2) now frame source fidelity under extensive extraction corruption. Current discussion/register descriptions route to that profile. The generic warning and its lack of diagnosis remain distinguished. | Documentation corrected; original font-span evidence preserved. No decoder/detector or converter coaching added. |
| GYN-RV-02 | [Preparation condition](spec.md#preparation-before-an-authorized-start) and [T1](tickets.md#gyn-01-t1--prepare-and-bind-the-fresh-task) require task-local configuration followed by readback. [The interval](spec.md#agreed-route-and-finite-interval) prohibits fallback and distinguishes transport/runtime observations from content judgments. | Planning corrected; no assumption about the actual saved connection, no settings changed. |
| GYN-RV-03 | [English OCR prewarming](spec.md#english-ocr-prewarming), T1 and [A1/A8](spec.md#planned-acceptance) require synthetic-only preparation, cache reuse without another language download, resource/log/timing evidence and unchanged conversion counters. | Warm-cache condition selected and planned, not executed. Failed warmup blocks readiness; setup cost is recorded separately from live time. |
| GYN-RV-04 | The [converter-instruction interpretation](spec.md#converter-facing-instruction), [A3](spec.md#a3) and T3 distinguish supplied-scope compliance from independent boundary discovery. | Interpretation corrected; exact converter prompt unchanged. |
| GYN-RV-05 | The three existing tickets now use one checklist each, common authority/ownership and linked requirements/handoffs. | Operator usability corrected. Git branch/checkpoint housekeeping remains outside this documentation-only execution; inherited changes are preserved. |

**Preservation and usability.** Compared the revised files with pre-amendment copies in ignored `.local/gyn01-doc-amendment-15b924bd/` (spec SHA-256 `8f2dbbe79947edd2a979dc7586422a0854664ec82770aa0a057df8e6c4093859`; tickets `5063a6dc8f865c135f3bdec7502ed774a5bd0fc7a65214a622658ef0d412f556`). The exact converter prompt and complete settings table are unchanged, and every previous spec/ticket heading remains. A meaning review traced scope, all A1–A8 criteria, sole-interval exits, source/reviewer separation, full evidence preservation and failed-run review through the shortened tickets. These guarantees remain operative through their linked owners. Word counts alone were not treated as preservation evidence.

The operator ticket text decreased from 1,828 to 1,177 whitespace-separated words. The spec adds the necessary source-profile and prewarming conditions; it is not claimed shorter. T1 now gives a direct sequence from identity through configuration, prewarming, controls and readiness; T2 proceeds from monitoring/Start through capture, exits and settlement. A failed T2 still proceeds to available-evidence review; no saved version is never silently replaced by developer assembly. A new cache condition changes setup accounting, not the finite live budget or autonomous method choice.

**Documentation impact.** Spec/tickets own the revised conditions and actions; this section owns observed correction checks. SOURCE_CONVERSION records adoption and qualifies its earlier source description while preserving attributed historical proposals. WORK_ITEMS links the selected amendment without copying ticket progress, INDEX adds the OCR preparation route, and CURRENT_STATE resumes at the corrected plan. Product code, shared contracts, PHASE_PLAN and README require no changes because their behavior and phase acceptance are unchanged. The inherited FIX-01 review edits remain untouched.

`python tools/docs/check_docs.py` returned zero errors. Git whitespace checks passed for tracked edits and all amended new documents, and the product source/test/tool/manifest/lockfile paths have no diff. No source/conversion recheck, application task, app launch, configuration change, OCR download, provider call or application test was performed. The stored source evidence and code inspection from the earlier review supply the basis; this round does not claim operational or content acceptance.

## Follow-up review and local Git checkpoints

2026-11-15 (Asia/Singapore). Under the user's [local Git selection](../../discussions/SOURCE_CONVERSION.md#local-git-checkpoints-selected-2026-11-15), the supplied follow-up review agrees with the documented corrections to GYN-RV-01–05. One wording qualification remains: the per-page counts locate affected font spans, not proved-corrupted characters or character-error rates. The existing evidence already states this limit. The timezone labels both denote UTC+8; historical entries are preserved.

Read-only inspection reconfirmed that the settings handler accepts an explicit `wait_policy`, the Task limits form sends a changed policy, and the OCR path passes the store's `ocr-cache` to the ordinary worker. These mechanisms support the plan; actual configuration, warm-cache reuse and readiness still require T1 evidence. No new documentation blocker or software-repair ticket was identified.

Created `codex/gyn-01` from `0417061`, preserving the working tree. Commit `355a433` contains only the inherited FIX-01 verification changes. The separate GYN-01 checkpoint groups its spec, tickets, verification, source-conversion discussion and INDEX/WORK_ITEMS/CURRENT_STATE updates. This retains the prior local closeout commit in the branch history; no push or PR is selected.

**Documentation impact and checks.** This section records the assessment and Git scope; SOURCE_CONVERSION records the instruction and CURRENT_STATE points here. The spec, tickets, phase acceptance and work-selection conditions need no further change. `python tools/docs/check_docs.py` returned zero errors, and Git whitespace checks passed. Product/test/tool/manifest/lockfile paths have no diff from local `master`. No application task, configuration write, OCR invocation, provider request or product test occurred.

## Combined assessment and continuation

**Documentation corrections complete; operational preparation and conversion remain untested.** The supported review corrections and the selected warm-cache condition are incorporated without changing the source range, Fig. 1.8 boundary, converter prompt, route or live budget. A1–A8 remain planned. [T1](tickets.md#gyn-01-t1--prepare-and-bind-the-fresh-task) is the next operational step under later preparation authority. The [local Git checkpoint record](#follow-up-review-and-local-git-checkpoints) owns delivery of the planning documents; it does not establish application readiness or conversion acceptance.
