# Product delivery phase plan

Updated 2026-10-25, Asia/Hong_Kong (UTC+08:00). The initial planning baseline was implementation `e7e30c0`; the capacity-waiting/projection correction was completed at `a484b9b`. Subsequent review identified remaining context-capability defects. The user has selected four context policies including B, adopted the integrated target design and authorized recording, not implementation. [CURRENT_STATE](CURRENT_STATE.md#context-coordination-discussion-and-design-record) distinguishes unchanged code, retained evidence and the selected target. Stages B-E remain recommendations, not execution, provider-call or release authorization.

## Ownership and intended outcome

The user supplies a PDF and a conversion scope. The app runs its own agent through Nexus to deliver complete, faithful, readable and reusable Markdown and source images with little routine human intervention. It supports evidence acquisition, document editing, context management, self-correction, continuation and delivery. The subscription connector remains the intended access path; direct pay-as-you-go APIs are not substituted as the assumed solution.

[PRODUCT_REQUIREMENTS](PRODUCT_REQUIREMENTS.md) owns outcomes and fidelity. [CONTRACTS](CONTRACTS.md) owns executable behavior. [ARCHITECTURE](ARCHITECTURE.md) owns responsibilities. This plan owns delivery order, dependencies and observable phase outcomes. [CURRENT_STATE](CURRENT_STATE.md) owns implementation, actual validation, limits and the next action. [REVIEW_HANDOFF](REVIEW_HANDOFF.md) retains the detailed acceptance criteria and evidence for existing batches; its accepted Phase 1/2/3 are not renumbered or reopened by this plan. [DESIGN_OPTIONS](DESIGN_OPTIONS.md) retains unselected alternatives.

This is a synthesis of the conversation available in this task and the maintained owners, not a fresh source-code audit, a rereading of every historical attachment, or a new conversion experiment. Historical proposals and reviewer comments are references, not adopted requirements merely because they were repeated. The validation results below are inherited records, not checks rerun while writing this plan.

## Direction retained from the conversation

- The agent chooses evidence, representations, tools, scripts, verification methods and reconstruction scope. The app supplies reliable access and execution boundaries; it does not replace agent judgment with a fixed conversion recipe.
- Context management has two related responsibilities: preserve continuation across growing task history, and expose exact file/evidence content at useful granularity. Keep originals outside transient input, with first/full/raw/field/range/native-pixel access. A summary or index is neither the only original nor proof of coverage.
- The agreed hybrid approach lets the agent select what matters while the app enforces capacity and initiates necessary bounded organization. A proposed update becomes effective only after admission; failure preserves the effective policy. Never silently downgrade a full pin, remove a pin or shrink the requested conversion scope.
- Preserve received messages, candidates, versions, original receipts, consumed usage and frozen-request boundaries. Saving an intent, applying a policy, telling the agent the outcome and accepting content are distinct facts.
- Prioritize consequential defects, then missing capabilities in the complete user flow, then useful improvements. A necessary new capability can belong in a repair. Do not wait for hypothetical zero risk, or keep extending a context project while actual delivery remains untested.
- No backward compatibility with the old implementation is required. Refactoring or reconstruction is available when justified by product effect, reliability, autonomy, quality and maintenance cost. Useful originals and results remain protected.

The current Electron/Python application, small LangGraph StateGraph, native Nexus service, shared tools, SQLite metadata and immutable files remain the implementation baseline. Earlier comparisons of Pi, LangChain, Deep Agents, SDKs and custom code informed that choice; they are not a queued framework competition. Retain the baseline because it already connects the required workflow and the recorded recent defects have identifiable application-level causes. Revisit boundaries or frameworks if a concrete requirement exposes a persistent mismatch. A replacement proposal must identify the responsibilities it takes over, the domain logic still needed, preservation costs and outcome-based validation. Framework maturity alone does not establish Nexus or PDF-domain fit.

## Existing completion anchors

These entries preserve completed scope without treating local mechanism checks as universal product acceptance.

| Delivered foundation | Implementation anchor | Evidence and remaining boundary |
| --- | --- | --- |
| Independent desktop agent, exact candidates, version-bound editing, deliberate rebuild, local reuse and continuation | Retained in `e7e30c0` | [Application](CURRENT_STATE.md#implemented-application), [editing](CURRENT_STATE.md#document-editing-increment), [continuation](CURRENT_STATE.md#continuation-and-integration-increment). A development workflow exists; the installed build is older. |
| Accepted Phase 1: context compaction progress and applied-handoff replay | `637380d`, `442bcfa` | [Phase 1](CURRENT_STATE.md#phase-1-context-compaction-progress) and [closeout](CURRENT_STATE.md#phase-1-closeout-handoff-application-replay). Scoped review reconciled; the subsequent Stage A correction addresses the measured short-reference retention edge. |
| Accepted Phase 2: existing-task settings and active time | `bce2f7b` | [Phase 2](CURRENT_STATE.md#phase-2-existing-task-settings-and-active-time). Known consumption is retained; unknown interrupted tails are not a strict lifetime-work or cost bound. |
| Accepted Phase 3: coordinates, image provenance and stencil/pin closeout | `64466ac`, `c073abc` | [Phase 3](CURRENT_STATE.md#phase-3-pdf-coordinates-and-image-delivery) and [closeout](CURRENT_STATE.md#phase-3-closeout-stencil-appearance-and-pin-admission). Bounded image/rendering cases, not every PDF format. |
| History-pressure proposals and validity/admission/outcome coordination | `6e1dfb3`, `e7e30c0` | [Coordination](CURRENT_STATE.md#history-pressure-context-update-coordination) and [latest increment](CURRENT_STATE.md#proposal-validity-admission-and-outcome-delivery). Preceding evidence retained; re-review identified two capacity-wait branches and a short-reference estimate defect, addressed by the current Stage A correction. |

The preceding lifecycle record reported passing coverage for 232 Python cases across separate runs and 12 desktop cases. [Current evidence](CURRENT_STATE.md#capacity-waiting-and-projection-estimates) distinguishes the newer correction's runs, independent before-change failures and delivery fixtures. Scripted responses establish exercised transitions and artifact preservation, not real-model strategy or summary fidelity. The older [live Nexus section](CURRENT_STATE.md#live-nexus-exercise) required review-directed corrections and did not exercise compaction; it does not certify unaided conversion or the latest revision.

## Delivery route

Letters distinguish these product stages from the completed numbered follow-up phases.

| Stage | Useful outcome | Status and ordering |
| --- | --- | --- |
| A. Close the current context coordination baseline | Long-task context changes have explicit, recoverable outcomes and a bounded acceptance conclusion | Four target policies and integrated design adopted; documentation updated. Implementation and verification await authorization. Known gaps remain; Stage A is not closed. |
| B. Establish complete autonomous conversion on actual sources | The app's own agent completes agreed real PDF scopes and delivers verified saved/reopened/exported content | Recommended next product stage; source, route and finite live-call authorization remain to be selected. |
| C. Continue through ordinary interruptions | Selected recoverable network/local-operation failures no longer require avoidable manual reconstruction | Provisional; choose related increments from recorded gaps and Stage B observations. |
| D. Make delivery usable outside the development checkout | Users install, reopen and export the selected version with working source assets in the declared target environment | Provisional; Windows first, with destination and installation acceptance defined before work. |
| E. Improve provider choice and whole-task efficiency | Selected Nexus routes meet the same quality target with understood cost, latency and intervention tradeoffs | Conditional optimization, not a prerequisite for an initial useful Windows delivery. |

A -> B is the recommended immediate order. C and D are revisable: promote a concrete recovery or export blocker when it prevents B's intended delivery. Do not wait to finish every possible C scenario before obtaining useful B evidence. E can move earlier when an actual route or cost constraint prevents use, but no all-provider matrix is implied. Within an authorized increment, capability work and root-cause refactoring may be included without creating a new phase simply because they are new features.

## A. Close the current context coordination baseline

**Outcome and rationale:** complete supported context updates as a capability without making endless state-machine expansion the product's main activity. The preceding changes address particular admission failures; subsequent controls show that normal admission, actual compaction feasibility, final-handoff preview and projection savings still disagree. Retained evidence supports a focused responsibility redesign, not a presumption of framework replacement.

**Current scope and authority:** update the discussion and [target design](design/CONTEXT_UPDATE_COORDINATION.md) after explicit selection of whole-batch admission, non-partial context revision, agent reselection after amendments and B for confirmed necessary-content excess. The former correction's immediate/deferred behavior remains implemented; policy adoption does not retroactively change its tests. The canceled implementation attempt is not resumed. OCR recovery, export portability, Alpha, packaging and live calls remain outside this work.

**Proposed implementation scope, only if subsequently authorized:** separate composition, request projection/cost, disposition/continuation and durable commit/recovery. Address CC-R1/2/3 and the supported ordered-update/diagnostic/report/reopen paths together. [The target acceptance matrix](design/CONTEXT_UPDATE_COORDINATION.md#observable-acceptance-and-limits) gives observable checks, including fresh explicit content reuse. The [selected B rule](design/CONTEXT_UPDATE_COORDINATION.md#capacity-classification-and-policy-b) replaces the previously open classifier. [The implementation route](design/CONTEXT_UPDATE_COORDINATION.md#implementation-route-if-authorized) orders request/cost foundations, whole-batch disposition/commitment, then agent correction/recovery and complete local delivery. These are milestones of one capability, not new independent phases or a renewed whole-project review.

**Completion conditions:**

- Supported findings have an evidence-based disposition. Any unresolved issue that directly defeats this phase's outcome remains visible rather than being called complete. A hypothetical counterexample without a concrete mechanism is not automatically a blocker.
- Notes/index/range/release and shorter-note updates can remain pending through reducible history pressure and apply after complete admission. Test actual compaction rather than infer its impossibility from a normal-input gate. Non-admitted updates preserve the previous effective policy and have an executable diagnostic route or an honest external-condition wait.
- Eligible history-pressure waiting, unknown estimates, needs-revision under B, terminal dispositions, committed application and delayed result delivery remain distinguishable across the exercised interruption/re-entry boundaries. Original receipts are not rewritten, ineligible revisions do not revive after capacity restoration, and completed effects do not repeat. A supported necessary-cost proof cannot replace full-input admission; a fitting compaction request alone does not establish a reachable diagnostic target.
- Both native protocols retain exact originals/access, valid amendments, consumption and frozen-request boundaries. Relevant save/reopen/export evidence remains applicable to the final reviewed source; changed behavior receives proportionate new checks.
- Record a bounded conclusion: ready for the next product stage, or a specific repair still required. The current controls show a direct remaining continuation blocker and two planning/projection inconsistencies; they are not fixed by documenting a design. Do not claim real-model summary fidelity from fixtures or add unrelated hypothetical prerequisites.

This phase does not require a new provider experiment, a fixed reviewer count, or recurring review rounds after agreement. Reopen a disputed point only for material new evidence or an unresolved acceptance condition.

## B. Establish complete autonomous conversion on actual sources

**Outcome and rationale:** determine whether the supplied tools and state handling actually let the agent finish a useful PDF task with faithful content and little human handling, and implement directly evidenced missing capabilities. This is the largest product uncertainty left by the current mechanism-heavy evidence.

**First increment:** select an actual user PDF and its complete requested scope, or an explicitly agreed complete-section evaluation. Record exact source/version, Nexus route and native protocol, configured capabilities/capacity, finite request/time allowance, and what counts as developer or user intervention. Use the current development app initially; a release rebuild is not a prerequisite for learning about conversion. Live calls require authorization covering that run; closed historical allowances are not reused.

The agent receives the source, scope and necessary tool guidance. It chooses methods and reads. Do not feed it matching-range answers, developer transcriptions, previous conversion outputs or a prescribed successful tool sequence. Reviewer feedback can help diagnose and repair a run, but preserve its timing and distinguish the initial autonomous result from an assisted result.

**Work within the stage:** inspect the actual source and saved output; trace substantive omissions, wrong relationships, repeated regeneration or unnecessary questions to their cause. Improve source access, tool guidance, candidate reuse, document correction, context continuation or output inspection only where they address an evidenced need. A successful tool call is not the acceptance target. Select a further source class only to resolve an important remaining uncertainty, not to fill a fixed benchmark quota. Native, scanned and mixed PDFs remain product targets; one successful native section does not certify the other classes.

**Completion conditions for each agreed scope:**

- The agent reaches a saved deliverable for the full requested scope without developer assembly or routine step-by-step prompting. Record every intervention and its cause. If review-assisted repair was needed, do not label that initial run unaided; assess whether the repaired path needs a fresh, bounded confirmation within authorization.
- Source-led checking covers substantive wording, units/negation/symbols, reading order, tables and cross-page relationships where present; correct physical/printed page identity; faithful figures/captions and required searchable labels. No known substantive omission, fabricated content or unresolved required unread scope is called a complete accepted result.
- Saved document, reopened app, exported Markdown/HTML/assets and the selected immutable version agree. Inspect actual rendered output and relevant original/pixel bytes. Export/reopen needs no additional inference and remains available after budget exhaustion.
- Where a real task exercises context organization, check whether the agent retains requirements, unfinished dependencies and useful saved work and can retrieve originals. Do not force compaction merely to claim natural adoption. If the chosen scope never reaches pressure, retain the limitation and use a separately labeled, authorized pressure exercise only when needed.
- Preserve unsuccessful attempts and budgets. A bounded run that ends partial is useful evidence and a follow-up input, not fulfillment of the complete conversion target. Model behavior, software behavior and content acceptance are reported separately.

**Stage closeout:** identify exactly which source classes/scopes and route were accepted, remaining failure causes and the next most valuable capability increment. No whole-book, all-provider or universal-fidelity certification is required. The product target is not reduced to whichever excerpt happened to succeed.

## C. Continue through ordinary interruptions

**Outcome and rationale:** reduce avoidable human handling when a conversion is interrupted. Existing HTTP/rejected-reply Continue, durable effects and bounded unknown-request replay provide a basis. The recorded `local_outcome_unknown` gap for started OCR/scripts is a real remaining capability limit; general autonomous reconciliation is not established.

**Proposed scope:** select one related interruption family per increment. Begin with a managed local worker if it is the demonstrated blocker, or with network behavior if it prevents the selected task. Distinguish app-controlled OCR from arbitrary opt-in host scripts; a task directory is not an OS sandbox. Distinguish a known failed/unsent request from an unknown upstream outcome, accepted response and completed local effect. Do not infer remote cancellation, background retrieval or provider compaction from an OpenAI-compatible endpoint.

The design question is which outcomes can be recovered from durable evidence, which work can safely resume or repeat, and which uncertainty must remain explicit. Compare improving operation-specific receipts/reconciliation with replacing an execution boundary where needed. Do not add a general scheduler, unconditional retry layer or automatic replay of all failed records merely to avoid a stop.

**Completion conditions for the selected family:** local fault/restart checks in affected protocols demonstrate reuse of completed work, continuation of eligible unfinished work, no duplicate writes/publication, preserved original requests/receipts/consumption, and effective amendments. Known safe recovery should require less manual action; unresolved side effects remain honestly blocked with useful work accessible. The app must reach a correct saved/reopened/exported result after the exercised interruption, not merely resume requests. Automatic retry, if selected, is finite, shares existing budgets, respects Stop and cannot multiply independently across SDK/proxy/app layers. Live route behavior remains separately scoped.

The exact automatic-retry policy, supported local operations and interruption cases remain open until this stage is selected. Network management belongs here; streaming is an optional technique to justify by need, not an assumed prerequisite or a repair for unknown effects.

## D. Make delivery usable outside the development checkout

**Outcome and rationale:** a user can use the current app and reuse its outputs without developer tools or manual package assembly. The existing Windows distribution predates recent fixes. Destination filesystems without the current hard-link publication behavior are unverified, not already proven broken in every case.

**Provisional scope:** first verify and, where necessary, repair explicit-version export to the declared everyday destination; then build the current Windows runtime/app and check it outside the development environment. Keep credentials and private source/workspaces out of distribution. Reuse existing build/export mechanisms if they satisfy the outcome; change publication strategy if the target environment disproves it. Broader platforms and signing/distribution choices need a separate selected scope.

**Completion conditions:** exported content opens after relocation with its relative image links and required original/provenance files; selected-version consistency and exact source assets survive. A failed or interrupted export preserves the previous usable package and can be retried without inference. A clean-environment Windows check can launch, configure Nexus without bundled secrets, import a source, use the selected conversion path, reopen saved work and export. Local scripted checks and any authorized live check are labeled separately. Release artifacts are tied to source/lockfile/build identities; installing, publishing and source synchronization are distinct actions. An old installer or a successful frontend build cannot stand in for this acceptance.

This stage may use separately verifiable export and packaging increments. Offline OCR resource provisioning and upgrade/data preservation should be checked when relevant to the selected distribution; do not silently make first-use downloads or loss of prior task data the user's repair task.

## E. Improve provider choice and whole-task efficiency

**Outcome and rationale:** support the user's selected subscription/cost-saving routes without trading away conversion quality or agent freedom. Current cross-protocol local tests do not prove compatibility with every model, image mode or Nexus route, and usage totals are not an actual bill.

**Conditional scope and acceptance:** choose a real needed route/model, inspect its actual capabilities, and evaluate a complete relevant task against the same source-led requirements as Stage B. Retain native protocol semantics and explicit unsupported-capability feedback. Do not silently change an already frozen request or reinterpret old native history when experimenting with a new route. Compare whole-task latency, interventions, normal/compaction/retrieval/repair usage and price-weighted cost where pricing is known; retain unknown usage and subscription fee attribution honestly. An efficiency change is accepted only with unchanged scope, fidelity and full access, not because input or cache metrics look better.

Provider selection, supported task classes and any comparison budget remain open. Automatic route fallback, new memory/retrieval frameworks, pin expiry, semantic dependency graphs, cache optimization and universal provider matrices are not selected by this stage. Use existing choices first when they can solve the measured need.

## Remaining needs that are not automatic prerequisites

| Need or observation | Evidence status | Selection condition and owner |
| --- | --- | --- |
| Small-result compaction retention edge | Previously reproduced; original remains readable, no demonstrated delivery loss | Revisit for meaningful extra rereads or delivery impact. [Remaining observations](REVIEW_HANDOFF.md#remaining-observations-outside-the-three-phases). |
| Capacity estimates and semantic summaries | Byte/image heuristics and scripted validation; no universal token bound or summary-fidelity proof | Stage B pressure/route evidence; fix estimation or continuation contracts if a concrete failure requires it. [Limits](CURRENT_STATE.md#limits-and-remaining-work). |
| Alpha, arbitrary ICC/high-depth images and broader OCR quality | Partial format coverage; specific unverified cases remain | Select from actual source requirements; preserve originals and fidelity. No blanket image-format project before ordinary delivery. [PDF evidence](CURRENT_STATE.md#phase-3-pdf-coordinates-and-image-delivery). |
| Evidence lifetime and repeated full reads | Usage strategy and unmeasured opportunity, not proof that full reads are wrong | Keep explicit choice and existing precise access; revisit only with task evidence. [Options](DESIGN_OPTIONS.md). |
| External MCP/CLI surface, macOS Apple Silicon and Debian x86_64 | Retained product intentions, not implemented/validated product surfaces here | Later delivery scopes using the shared core. They remain visible without becoming Windows-first prerequisites. [Product surface](PRODUCT_REQUIREMENTS.md#outcome-and-product-surface). |
| Broader script isolation, general branching or every-crash recovery | Unselected architecture/deployment scope | Evaluate only for a concrete use or trust requirement. Do not claim current opt-in scripts are sandboxed. [Architecture](ARCHITECTURE.md#authority-and-recovery). |

## How to use and revise this plan

At the start of an authorized increment, identify its intended outcome, relevant stage, actual source state, evidence and completion condition. Current human instructions authorize execution; this plan does not revive inherited requests or require redundant approval when an existing instruction already covers the work. The current instruction authorizes discussion/design documentation and proportionate document checks. It does not authorize app implementation, live model calls, publication, installation or Stages B-E.

Keep current and next stages concrete; refine later stages only when selected or when material new evidence changes their priority. At closeout, assess the accumulated phase outcome, not just the newest passing test. If necessary work expands, explain the new root cause, preserved requirements and observable milestone. Split work when it creates a useful independently verifiable result, not at an arbitrary line count or number of review rounds. A failed acceptance condition remains unresolved after renaming a phase.

Record material plan revisions here with their rationale. Update CURRENT_STATE and affected owners within the relevant write authority, link the final code/snapshot and retained evidence, and keep failed controls available. Distinguish planned, authorized, implemented, locally verified, source-accepted and released. A later regression does not erase earlier measurements, but it can require qualifying present completion claims.

The remaining human choices are the next execution authorization/scope; actual PDF/range, route and finite provider-call allowance when live work is selected; and later installation/distribution destinations. The four context policies and integrated design are already adopted, with no remaining policy conflict identified. Routine methods, API names and internal layouts do not require another policy vote. Adopting the target does not authorize coding. Changes to fidelity, autonomy, scope or explicit budget/frozen-request boundaries must not be silently introduced.

Current disposition: retain completed numbered-phase results and the useful graph/storage foundation. The preceding 248-case Python pass and six desktop deliveries remain evidence for their exercised behavior; later CC-R1/2/3 controls prevent calling the whole capability closed. The selected policies and integrated design are documented; implement/verify the bounded complete capability only when authorized. Recommend B after that closeout, with actual source, route and finite live-call authorization still open. C/D/E stay provisional; no unrelated infrastructure prerequisite or recurring review ritual is added.
