# Foundations, research, and framework decisions

This reference preserves the substantive discussion from **EVT-0002 through EVT-0414**, including attachments **ATT-01 through ATT-06**. It records why the rebuild direction changed, not a second implementation backlog. The controlling later correction is **EVT-1148 / EVT-1166**. It prefers a small **Python LangGraph `StateGraph` with SQLite** as the rebuild baseline. The discussion settled responsibilities, but implementation and proof remain incomplete.

The remaining V1 contracts concern document edits and candidate references, context capacity and handoff, and persistence, recovery, and stopping. Earlier Pi, Deep Agents, `create_agent`, filesystem-only, and custom-controller rankings below are historical.

This document explains the decisions and their reasons without requiring the old project or conversation export. The repository's discussion-source archive supplies the cited original text and attachment material when a reader needs exact wording. `EVT` identifies an exported event and `ATT` an attachment. These are provenance labels, not application APIs or runtime object IDs. [SOURCE_INDEX.md](SOURCE_INDEX.md) explains their origins and lookup.

Links to public documentation preserve the conversation's research trail. This documentation rebuild did not freshly check them. Their historical versions are not dependency pins.

Status meanings used throughout:

- **Agreed direction:** a product principle accepted in the discussion, subject to the later bounded consolidation.
- **Observed-v1:** an observation reported and checked in the old project discussion. It is not a new implementation claim for this repository.
- **Proposal/open:** a historical option, research lead, or illustrative implementation. It does not become a V1 requirement by appearing here.
- **Corrected/rejected:** a claim, prescription, or ranking that the discussion withdrew, narrowed, or superseded. This reference preserves the useful reasoning with its correction.

## Reading this reference on its own

For the effective product and responsibility boundaries, start with [PRODUCT_REQUIREMENTS](../PRODUCT_REQUIREMENTS.md), [ARCHITECTURE](../ARCHITECTURE.md), and [CONTRACTS](../CONTRACTS.md). This reference supplies the reasoning behind them. [P1-098](#p1-098) explains the final framework choice. [P1-099–101](#p1-099) describe the three bounded open contracts. The earlier proposals remain here because their corrections explain constraints that a simple implementation must still respect.

Several terms had distinct meanings in the discussion:

| Term | Meaning in this reference |
|---|---|
| Agent / runtime / harness | The agent is the model making task decisions. The runtime or harness surrounds those decisions with requests, tool execution, state, capacity handling, and continuation. A framework can supply parts of that machinery. It does not replace source interpretation. |
| Nexus route | The configured connection from this app through the user's Nexus gateway to an upstream model service. The particular historical subscription path was Nexus → CLIProxyAPI → subscription accounts. A model alias or OpenAI-shaped request format does not identify every upstream feature. |
| Active context / complete record | Active context is what a particular model request actually contains. The complete record includes durable original messages, results, and files that may be absent from that request. The model does not know a file's contents merely because it receives its path. |
| Evidence / artifact | Evidence is source material or an actual tool-produced result used to reason about the PDF, with its scope and provenance. An artifact is prepared or saved output, such as reconstructed document content. Reading output successfully does not prove that it faithfully represents the evidence. |
| Offloading / release / retrieval | Offloading preserves content outside model input. Release removes a selected representation from later active input while preserving the original and a retrieval route. Retrieval supplies that original, or an explicitly selected part, again. These actions do not automatically preserve the agent's unrecorded interpretation. |
| Summary / handoff / compaction | A summary condenses earlier content. A handoff describes enough effective task, work, unresolved issues, and references to continue. App-owned compaction changes future request assembly using retained content and such continuation material. Producing a summary alone changes no future input. |
| Context checkpoint / graph checkpoint | The old application's context checkpoint started a new working context with continuation material. A LangGraph checkpoint persists graph execution state for continuation. Either can exist without the other: persisting a huge history does not shorten it, and shortening input does not by itself provide crash recovery. |
| Candidate / committed version / head | A document candidate is received prepared content, including content that failed validation. A committed version is an immutable saved document result. The head is the current version pointer. A proposed context assembly can also be called a candidate. It is a different object from candidate document content. |
| Operation receipt | A durable record of the result of one identified operation, used to recognize a completed local effect after interruption. It is not a quality certificate, a fresh command to republish, or proof of what an upstream model did after a client disconnect. |
| Protocol / adapter / frozen request | Chat Completions and Responses are alternative wire formats. An adapter preserves their actual images, tool exchanges, and applicable native items. A frozen request preserves the app's selected and encoded content for one request. Resuming that same request does not silently substitute a new context. |

These definitions unpack the discussion's responsibilities rather than prescribe new class names or database tables.

**Sources: EVT-0137, EVT-0249, EVT-0318, EVT-0382, EVT-0414, EVT-1166.**

## Reading scope and limits

The later [ATT-31 supplement](#supplemental-first-response) preserves a response from a separately supplied document. It was not among the original 30 exported attachments. Its historical proposals do not change the final architecture.

The review read the complete EVT-0002–EVT-0414 source packet: 120,772 decoded characters and 2,680 lines after newline normalization. It also read the full initial handoff EVT-0001 (11,695 normalized characters) and the complete final consolidation EVT-1166. It read ATT-03 through ATT-06 in full where inserted into the packet.

The review parsed the two forum HTML originals as inert data. ATT-01 yielded 17,303 readable text characters and 14 embedded illustrations. ATT-02 yielded 1,189 text characters and 10 substantive image pages. The review inspected all those texts and images. Byte comparison found that the ten preserved `answer-01.webp` through `answer-10.webp` files matched the images embedded in ATT-02.

Source screenshots clip some code at their right edges. The review invented no missing code. Interface chrome, vote counts, and unrelated collapsed-answer fragments are not architecture evidence.

This work reviews the conversation and attachments. It does not rerun old conversions or newly verify all linked research, framework code, old test logs, deployment settings, or billing. The initial handoff supplies background. The rebuild does not copy its old execution boundary and old defaults as standing instructions. The review executed no source HTML commands or embedded scripts.

## Product purpose and the starting evidence

<a id="p1-001"></a>
**P1-001 — Delivery is the purpose.** **Status: agreed direction.**

The agent completes the conversion. The app provides reliable tools. A user should supply a PDF and scope, then receive complete, readable, reusable Markdown and faithful source images with little manual handling. Product progress means useful delivery, less user work, reliability, recoverability, and reasonable whole-task cost. Tool counts, test counts, document counts, a success flag, and a polished screen do not substitute for these outcomes.

The initial review identified the next useful delivery question as an actual PDF or complete natural section and its reading, search, or editing purpose.

**Sources: EVT-0053, EVT-0001.**

<a id="p1-002"></a>
**P1-002 — Independent desktop delivery remains part of the product.** **Status: agreed direction.**

The intended application is an independent Electron, TypeScript, and React desktop app that runs its own agent. It supports configurable Chat Completions and Responses connections. Independence from the Codex or ChatGPT UI does not mean an offline model. The old headless Python core and an external assistant successfully using tools did not prove installed desktop readiness.

At the start, UI integration and Windows packaging were absent. The later consolidation still requires that work if “delivery” means an installable app. It does not make every backend unknown a prerequisite.

**Sources: EVT-0021, EVT-0053, EVT-1166, EVT-0001.**

<a id="p1-003"></a>
**P1-003 — Fidelity and reading form.** **Status: agreed direction.**

Preserve these source features:

- Substantive wording, numbers, names, units, punctuation, symbols, and glyph distinctions.
- Meaningful emphasis, superscripts and subscripts.
- Headings, paragraphs, lists, footnotes, and meaningful side content.
- Reading order and cross-page relationships.

The product permits reflow of columns, lines, typefaces, or spacing. It does not permit guessing, paraphrasing, normalizing meaningful characters, or dropping difficult content to make it look readable. Tables retain values, intentional blanks, headers, groups, spans, and relationships. They need not use a simple pipe table. Figures retain panels, captions, and important searchable labels.

The agent may omit pure decoration and repeated non-substantive running matter. It preserves uncertain substantive content or makes that uncertainty explicit.

**Sources: EVT-0382, EVT-0414, EVT-0001.**

<a id="p1-004"></a>
**P1-004 — Images, page identities, and one-version outputs.** **Status: agreed direction.**

Sources stay intact. Extract complete native images at their original size and encoding when possible. An existing JPEG is legitimate, and PNG alone proves no fidelity. Faithful lossless crops or renders are legitimate for vector, composite, or scanned content, with page, region, and rendering provenance. Do not silently resize, redraw, whiten, reduce color or bit depth, or add lossy recompression.

Physical PDF positions and visibly printed labels are separate. Printed `none` differs from `unknown`, and Roman labels remain. Viewer labels or inferred offsets are not evidence. The full map distinguishes outside-scope and unprocessed pages without splitting sentences or tables merely to insert markers. Markdown, document JSON, safe HTML, assets, and ZIP must correspond to the same specified immutable version and use portable relative links.

**Sources: EVT-0047, EVT-0053, EVT-0382, EVT-0414, EVT-1166, EVT-0001.**

**Page-label example.** In the observed delivery, physical PDF page 12 carried printed label `68`. That one correspondence does not authorize assigning every page a fixed offset. Front matter, inserted plates, or an unprinted page may break that offset. `none` means the evidence establishes that the page has no printed label. `unknown` means the evidence does not yet establish its label.

Both differ from a page outside the requested scope or still unprocessed. These separate states show what the output covers without guessing labels or damaging a continuing paragraph to force a marker.

**Sources: EVT-0047, EVT-0053, EVT-0001.**

<a id="p1-005"></a>
**P1-005 — Method autonomy and full access.** **Status: agreed direction.**

The agent may choose extraction, OCR, visual reading, scripts, or combinations, including re-OCR of a damaged existing text layer. It chooses pages, regions, DPI, language, and reconstruction scope. Neither a framework nor the app should impose a page-by-page conversion pipeline, compulsory text-first reading, OCR, scripts, preview, or a fixed unit of repair. Full first-call and later full/raw/field/range/native-pixel access remain available without hidden truncation or a summary gate. Discoverable shapes, sizes, pointers, warnings, coverage, and omissions help selection.

Disk availability does not establish that the model saw, understood, or remembered the content. A path or base64 text is not visual input. Full access also cannot make an arbitrarily large object fit in one request.

**Sources: EVT-0137, EVT-0249, EVT-0265, EVT-0297, EVT-0318, EVT-0382, EVT-0414, EVT-0001.**

<a id="p1-006"></a>
**P1-006 — Scripts and source authority.** **Status: agreed direction.**

Scripts let the agent handle legitimate transformations, joins, filtering, checks, and large intermediate data without adding a new product API for each PDF. They do not remove already-consumed history. Preserve original files and full logs despite return-size limits. The old trusted-host execution mode was explicitly opt-in, ran with host-user permissions, and was not an OS sandbox. Those facts do not settle a rebuilt desktop isolation design.

Source documents, OCR, examples, forum posts, and their commands remain data, including in summaries. They cannot become higher-priority operating instructions.

**Sources: EVT-0249, EVT-0382, EVT-0001.**

<a id="p1-007"></a>
**P1-007 — What the initial review actually established.** **Status: observed-v1.**

The opening review found a source-accepted headless conversion core, not a completed desktop app. It checked the Breasts/Figure 4–13 delivery at physical page 12 / printed 68, including cross-column continuation, three paragraphs, two bullets, the figure, and 18 searchable labels. The Markdown, saved preview, output directory, ZIP, and unique immutable version were consistent, and preview PNG pixels entered later model requests. R1/R2/P and earlier examples had their own bounded source-accepted scopes. This supported actual content handling and saved-output inspection, not unseen-book reliability, correction of a real visual defect, or universal capabilities. The old checkout commit and local-ahead count were review identity, not rebuild defaults or a current remote-sync claim.

**Sources: EVT-0002, EVT-0007, EVT-0021, EVT-0047, EVT-0053.**

The old labels `R1`, `R2`, `P`, and `B/C` identify bounded comparison or exercise runs, not rebuild components or required future test names. R1/R2 are relevant here only for the injected interruption limits described at [P1-011](#p1-011). P and B/C are relevant for the limits of adoption claims at [P1-010](#p1-010). Reproducing their run configurations is unnecessary to understand those conclusions.

**Sources: EVT-0053, EVT-0068, EVT-0414.**

<a id="p1-008"></a>
**P1-008 — Closed audit conclusions stay closed.** **Status: observed-v1.**

The old eight-reply audit reported 636,591 input tokens, 537,088 cached, 99,503 arithmetic non-cached, and 1,587 output including reasoning. Its US$0.2685848 calculation was a conditional price benchmark, not a Nexus bill. Request 2 accounted for about 61.0% of the input-cost benchmark through its non-cached portion. The audit did not isolate marginal layout/word value or avoidable cost.

The audit never sent its 191,662-to-5,014-character in-memory projection to the converter. That projection proved neither adequate fields, equal quality, token savings, nor whole-task savings. The first request already exposed `_select`. Later selected reading did not explain the first full read. Zero changes was a valid audit result. Repeated audit prose was a documentation burden, not evidence that the runtime was conclusively overengineered.

**Sources: EVT-0047, EVT-0053, EVT-0378, EVT-0382, EVT-0001.**

<a id="p1-009"></a>
**P1-009 — Starting context gap.** **Status: observed-v1.**

The user identified context and network management as the two areas needing attention. Existing precise reads could reduce first intake. Enabled scripts could transform data before intake. Selective history could release eligible previously read text or images and retain exact retrieval. It could not bound all assistant drafts, tool arguments, and save history.

The project's “context checkpoint” could start a new working context with notes, task, saved-version identity, and retrieval routes. It was not lossless memory. Full history was the old default and the optional controls were off. There was no complete automatic capacity policy. Oversized accumulated input or one large OCR/layout reply could stop work before the agent had another chance to compact. These old settings describe the gap, not new defaults.

**Sources: EVT-0054, EVT-0055, EVT-0064, EVT-0068.**

<a id="p1-010"></a>
**P1-010 — Capability, adoption, and benefit differ.** **Status: observed-v1.**

Prescribed selective and checkpoint exercises showed mechanism use, actual changed input, retrieval of original pixels, and bounded completed delivery. Ordinary B/C jobs did not use optional transitions. P did not use scripts. That does not prove lack of need, misunderstanding, inevitable future non-use, or that optional notes would also be unused. Larger or smaller request counts, an interruption before a transition, and total tokens are not causal evidence of context-policy value. The open question was reliable long-task continuation with fidelity and net benefit, not use of every tool.

**Sources: EVT-0053, EVT-0068, EVT-0214, EVT-0414, EVT-0001.**

<a id="p1-011"></a>
**P1-011 — Starting network gap and its limited role here.** **Status: observed-v1.**

The old core had streaming and non-streaming paths, finite recoverable-error retries when enabled, cancellation-aware backoff/jitter, applicable `Retry-After`, persistent attempts/time/turn budgets, receipts, and complete-response validation. Defaults included non-streaming and zero automatic retries. A finite trial's two retries did not establish a new product default.

R1's roughly 90-second injected outage took roughly 188 seconds before forwarding, including about 98 seconds after recovery. R2 tested interruption before stream completion. These were not natural prolonged outages, remote cancellation, original-generation retrieval, or universal crash recovery. Client timeout can leave the upstream result unknown. The discussion separated connection/header/body/idle/whole-job bounds, in-band errors, and context overflow. It rejected inferring cause from HTTP 500 alone.

**Sources: EVT-0053, EVT-0068, EVT-0001.**

## Industrial research and the Nexus correction

<a id="p1-012"></a>
**P1-012 — Research method and common practices.** **Status: proposal/open (research background).**

The user requested an industrial-practice search. The historical review used first-party OpenAI, Anthropic, LangChain/LangGraph, AWS, and Microsoft materials. Recurring practices were just-in-time retrieval, clearing older tool bodies, summaries or working notes, persisted task state, and measuring complete request capacity. They form a repertoire rather than one universal standard. Exploration and later retrieval also cost time and tokens. Storage, input compaction, and request recovery are separate responsibilities.

**Sources: EVT-0069, EVT-0070, EVT-0073, EVT-0090, EVT-0097.** Relevant historical references: [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), [LangChain short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

<a id="p1-013"></a>
**P1-013 — Native provider features were examples, not assumptions.** **Status: corrected/rejected.**

The industrial survey described provider-specific compaction, OpenAI background responses, and token-counting services. Native compaction need not be ordinary prose: OpenAI's compact endpoint can return opaque compaction items whose expected continuation window should not be casually edited. An API-compatible base URL or model alias does not imply the availability of these features. No general 30%, 50%, 80%, or other mandatory compaction threshold followed from the sources.

**Sources: EVT-0090, EVT-0097, EVT-0130, EVT-0137.** Historical references: [OpenAI compaction](https://developers.openai.com/api/docs/guides/compaction), [Anthropic compaction](https://platform.claude.com/docs/en/build-with-claude/compaction), [OpenAI token counting](https://developers.openai.com/api/docs/guides/token-counting), [OpenAI background mode](https://developers.openai.com/api/docs/guides/background).

<a id="p1-014"></a>
**P1-014 — Network practices retained as context, with broader design deferred.** **Status: proposal/open (deferred).**

Research distinguished these responsibilities:

- Timeout semantics and bounded classified retries.
- One retry owner across app/SDK/proxy.
- Idempotent or reconciled side effects.
- Stream completion errors, even after HTTP 200.
- Provider-supported asynchronous status/result/cancel operations.

Circuit breakers, aggregate retry budgets, and traffic limits may matter for sustained shared-service load. One desktop task does not automatically need them. LangGraph checkpoint persistence differs from the old application's context checkpoint. The user explicitly deferred broader network discussion at EVT-0186. Later references to network contracts preserved necessary integration boundaries rather than reopening that topic.

**Sources: EVT-0097, EVT-0186, EVT-0188, EVT-0318, EVT-0382, EVT-0414.** Historical references: [AWS timeouts and retries](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/), [Microsoft transient faults](https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults), [Microsoft circuit breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker).

<a id="p1-015"></a>
**P1-015 — CLIProxyAPI inspection narrowed an overbroad “unsupported” claim.** **Status: observed-v1.**

At the user's request, the earlier review inspected CLIProxyAPI routes and local build metadata. It reported `v8.0.29+dirty` based on commit `5fc580b`, while cautioning that a dirty public commit is not the full local binary. The inspected Codex executor implemented a standalone `POST /v1/responses/compact`. Its translator removed `context_management`, so ordinary automatic compaction settings did not pass through that path.

The review found no standard `GET /v1/responses/{id}` or HTTP `/responses/{id}/cancel` route. `GET /v1/responses` was a WebSocket entry. An active Codex WebSocket could forward `response.interrupt`, with session restrictions and no general remote-stop guarantee. This was source/metadata evidence without generation or compaction requests, not end-to-end Nexus proof or a new dependency/version requirement.

**Sources: EVT-0098, EVT-0099, EVT-0111, EVT-0124, EVT-0126.** Historical source: [inspected routes](https://github.com/router-for-me/CLIProxyAPI/blob/5fc580b1d72d87a7bcfe5cfb6f479c1aea5625b3/internal/api/server_routes.go).

<a id="p1-016"></a>
**P1-016 — The user's monthly-subscription route controls the premise.** **Status: corrected/rejected.**

The assistant widened the discussion to Nexus's other official pay-as-you-go providers and gateway endpoints. The user corrected this: their route was Nexus → CLIProxyAPI → monthly subscription accounts. Other providers' documented capabilities did not establish capabilities of that route. Standalone Codex compaction remained a code-level exception, but the review did not test route usability. The distinction matters because an SDK connection through Nexus does not itself imply purchasing or using official metered APIs.

**Sources: EVT-0126, EVT-0128, EVT-0129.**

<a id="p1-017"></a>
**P1-017 — Portable baseline deliberately does not rely on native services.** **Status: agreed direction.**

The user then explicitly asked to treat native compaction, background retrieval, and cancellation as unavailable. They might choose DeepSeek, GLM, Qwen, and other providers to reduce cost. The design therefore uses normal model calls for app-owned context organization and works without those native capabilities. An implementation existing in one subscription route does not weaken this baseline. Model aliases cannot safely determine capacity, vision, reasoning format, upstream identity, tier, or cache behavior.

**Sources: EVT-0130, EVT-0132, EVT-0137, EVT-0349, EVT-1166.**

## Agreed context responsibilities and supporting research

<a id="p1-018"></a>
**P1-018 — Two coordinated forms of context management.** **Status: agreed direction.**

File/evidence management governs which PDF text, layout, OCR, images, and tool results enter, remain in, leave, or re-enter active input. Conversation/work-history compaction governs accumulated instructions, decisions, drafts, and operation history. A model writing a summary does not itself shorten future input. The app must change request assembly. Durable task state and source indices support both rather than constituting a third competing compression system.

**Sources: EVT-0130, EVT-0137, EVT-0186, EVT-0188, EVT-1166.**

<a id="p1-019"></a>
**P1-019 — Explicit agreement on mixed control.** **Status: agreed direction.**

The app owns capacity estimates, output/management reserve, original preservation, valid message assembly, and applying context changes. The agent chooses useful evidence, release or retrieval, unresolved relationships, and the content of a handoff. The agent can act proactively. Near capacity, the app triggers organization early enough to permit it. The user explicitly accepted this division of responsibility. It neither delegates semantic understanding to a heuristic app nor assumes that the agent will always invoke optional tools in time.

**Sources: EVT-0188, EVT-0189, EVT-0190, EVT-0214, EVT-1166.**

<a id="p1-020"></a>
**P1-020 — Explicit agreement on release before older-history compaction.** **Status: agreed direction.**

First consider releasing exactly retrievable material that is no longer needed. If necessary, then organize older working history. Protect effective requirements, unresolved dependencies, and useful unsaved output, including by saving exact work and retaining references. This is a priority, not compulsory per-section cleanup. The agent may retain evidence or organize history directly when appropriate.

“Already processed” and “saved” do not mean “no longer depended on.” Summary prose is not the original or a proof of complete coverage.

**Sources: EVT-0190, EVT-0191, EVT-0206, EVT-0214, EVT-0215, EVT-1166.**

<a id="p1-021"></a>
**P1-021 — What a continuation must convey.** **Status: agreed direction.**

The discussion identified these continuation categories:

- Effective task and later corrections.
- Current work and restart point.
- Completed, saved, drafted, and unchecked ranges.
- Unresolved questions and dependencies.
- Exact evidence and artifact/version locations.
- Decisions and reasons that affect future work.
- Next useful actions.

Examples included a table spanning pages 18–19, a header still needed on the next page, and a doubtful unit. Other examples included a footnote awaiting verification and an unusable text layer that prompted pixel checking. These categories guide meaningful notes. They are not a mandatory form to fill after every call.

**Sources: EVT-0137, EVT-0214, EVT-0215, EVT-0249.**

**Worked continuation example from the early design.** The proposal used evidence `ev_0042`, saved artifact `document_v8`, and a table spanning physical pages 18–19. These names and fields were illustrative, not selected public API names.

| Continuation information | What it enables the next request to do |
|---|---|
| Current work: reconstruct the table spanning pages 18–19 | Resume reconstruction of the actual relationship, rather than merely start at “page 19.” |
| Note: page 19 continues the header on page 18 | Keep or retrieve the earlier exact header even if page 18 has already been saved. |
| Open item: verify the unit in the final column. Evidence: `ev_0042`. | Carry uncertainty forward instead of turning a tentative unit into an accepted value. |
| Saved artifact reference `document_v8` | Recover prepared work without generating it again. Existence of that version is an app fact. Completeness of the table is a separate judgment. |
| Exact evidence reference and retention reason | Make the relevant original available while the dependency persists. Permit release when that dependency ends. |

A note saying only “page 18 completed” would lose the header dependency and the unresolved unit. A complete page map would locate pages but would not supply those meanings either. This is why mechanical progress records and agent working notes complement each other. A full semantic dependency graph is not required to record this small example.

**Sources: EVT-0137, EVT-0249, EVT-0318, EVT-0360.**

<a id="p1-022"></a>
**P1-022 — Fact ownership does not make meaning deterministic.** **Status: agreed direction.**

The app can record that a tool result, candidate, version, or receipt exists, which scope it identifies, and whether retrieval is possible. The agent judges whether a table is faithful, an uncertainty is resolved, an OCR interpretation is only tentative, or a dependency remains useful. The app can mechanically preserve exact user messages and their ordering. Interpreting how requirements combine or conflict still needs semantic judgment and provenance. Saving an interpretation as JSON does not turn it into independently verified fact.

**Sources: EVT-0137, EVT-0214, EVT-0249, EVT-0382, EVT-0414.**

<a id="p1-023"></a>
**P1-023 — Research supported the direction, not an optimal PDF policy.** **Status: proposal/open (research background).**

The user asked for journals and related projects, then asked to continue researching. The historical review found these relevant principles:

- *The Complexity Trap* and its JetBrains implementation compared observation masking with LLM summaries in code repair, including hybrid masking-then-summary strategies.
- Deep Agents described saving large outputs, offloading before summarizing, and preserving originals.
- MemGPT supported agent-managed external memory with runtime capacity warnings.
- ACE motivated structured incremental updates over repeated complete rewrites.
- *Lost in the Middle* showed information-position effects in long context.

These principles did not prove PDF-specific thresholds, dependency judgments, or equal-quality cost savings. Poor hybrid parameters could lose benefits through summary and cache costs.

**Sources: EVT-0191, EVT-0192, EVT-0201, EVT-0206, EVT-0207, EVT-0208.** Historical references: [Complexity Trap](https://arxiv.org/html/2508.21433v3), [implementation](https://github.com/JetBrains-Research/the-complexity-trap), [Deep Agents context management](https://www.langchain.com/blog/context-management-for-deepagents), [MemGPT](https://arxiv.org/html/2310.08560v2), [ACE](https://arxiv.org/html/2510.04618v3), [TACL paper](https://aclanthology.org/2024.tacl-1.9/).

<a id="p1-024"></a>
**P1-024 — Further research cautioned against token-only evaluation.** **Status: proposal/open (research background).**

Deep Agents reported conservative autonomous compression adoption, including no autonomous invocation in one Terminal-Bench 2 setting. A 2026-08 preprint reported additional retrieval after compression even where completion rates were similar, with different findings in another environment. A 2026-09 preprint compared strategies across three open-weight models and two coding task families. It found that fewer tokens did not consistently mean lower cost or latency. The review treated these newer papers as preprints rather than established peer-reviewed conclusions.

Anthropic's long-running-agent report also motivated progress records. Compaction alone could leave an agent unclear about completed work or falsely treating partial output as done.

**Sources: EVT-0214.** Historical references: [autonomous compression](https://www.langchain.com/blog/autonomous-context-compression), [2026-08 preprint](https://arxiv.org/abs/2608.16370), [2026-09 preprint](https://arxiv.org/html/2609.32961v1), [long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

<a id="p1-025"></a>
**P1-025 — Evaluation follows complete work, not memory mechanics alone.** **Status: agreed direction.**

Inspect fidelity and relationships, omissions and unnecessary regeneration, retrieval count, latency, peak capacity, and whole-task resource use. Include organization calls, rereads, retries, checking, and recovery. The assessment should distinguish a subscription route's observable allowance and rate limits from hypothetical official API prices. Unknown usage or fees are not zero. Do not count reasoning again if output already includes it. Cumulative input is not a single context length.

Source-accepted content, software paths, actual image intake, natural adoption, and installed readiness remain distinct.

**Sources: EVT-0053, EVT-0068, EVT-0137, EVT-0206, EVT-0214, EVT-0382, EVT-0001.**

**Capacity, accounting, and reuse answer different questions.** Cumulative input adds the input of successive requests. Repeatedly sending the same material increases that total even when each request fits the model window. Cache reuse may lower the price or latency of repeated input under a route's actual policy. The cached material still occupies that request's context.

A price benchmark weights cached input, non-cached input, and output at their respective rates. It also includes the extra calls caused by summaries, retrieval, retries, and checks. Fewer characters, fewer cumulative tokens, or a higher cache-hit ratio alone cannot settle which strategy delivers equal fidelity at lower whole-task cost. The historical dollar calculation did not measure what the monthly subscription charged.

**Sources: EVT-0053, EVT-0137, EVT-0214, EVT-0382.**

<a id="p1-026"></a>
**P1-026 — The discussion was documented before technical redesign.** **Status: observed-v1.**

The user requested detailed documentation of topics, discussion, considerations, findings, conclusions, and remaining questions. The old conversation recorded an English `CONTEXT_MANAGEMENT_DISCUSSION.md` and owner/index updates, with design agreement distinguished from implementation and thresholds/framework still open. That old document is historical evidence of the discussion's recording, not an active requirement to copy old project status or create a new session prompt. The user then asked for technical design and explicitly removed backward-compatibility constraints.

**Sources: EVT-0215, EVT-0216, EVT-0225, EVT-0232, EVT-0239, EVT-0240, EVT-0241.**

## The first technical proposal and its later supersession

<a id="p1-027"></a>
**P1-027 — Unified context management was proposed instead of isolated modes.** **Status: proposal/open (historical design).**

With no compatibility requirement, EVT-0249 proposed replacing separate `full / agent_selected / checkpoint` modes with an app-owned context manager. That manager projects a working view from complete records. The proposal suggested these concepts:

- `EventLog` for original events.
- `EvidenceStore` for original results and images.
- `TaskContract` for effective requirements with original user provenance.
- `WorkingState` for agent progress and unresolved work.
- `ContextManifest` for what a particular request includes or omits.

The proposal preferred stable content IDs over historical-array positions, which the old evidence mapping used. It initially suggested filesystem JSON/JSONL and atomic writes, with no reason then established for a database. The later SQLite baseline supersedes that storage preference. These conceptual responsibilities do not require five separately elaborate subsystems.

**Sources: EVT-0248, EVT-0249, EVT-1166.**

<a id="p1-028"></a>
**P1-028 — Evidence identity and presentation are different states.** **Status: agreed direction.**

An evidence object can remain immutable while its input presentation is full content, a selected field/range/image, or a reference with diagnostics. The illustrative record included evidence/source/operation IDs, physical-page scope, content path and hash, media references, presentation mode, and a release reason. Retrieval need not reconstruct an entire old dialogue: an exact old result can be reintroduced through a current read with correct source/time identity. Image adapters must create real model image input. Re-running OCR is not equivalent to retrieving the exact prior OCR result.

**Sources: EVT-0206, EVT-0249.**

**Evidence lifecycle example.** Suppose the requested OCR operation produced a complete result for pages 18–19. The core saves the full produced result once with its identity and scope. The current request may receive its complete text. A later request may need only the table region or a reference. After a context change, a precise read can return the original table result again.

None of those presentations edits the saved original. If the task needs pixels, the adapter must deliver actual image input, rather than merely repeat a path. Re-running OCR would be a new computation with its own result and provenance. It cannot substitute for retrieving the exact old result. The preservation obligation covers the OCR result actually produced. It does not require also calculating unrequested word data, character data, or page renders.

**Sources: EVT-0249, EVT-0382, EVT-0414.**

<a id="p1-029"></a>
**P1-029 — Small structured state plus free notes.** **Status: proposal/open (illustrative form).**

The first schema suggested a revision, `based_on_event`, current work, open items with IDs and evidence references, artifact references, retention references, and prose notes. The proposal preferred incremental updates to repeated rewrites of all memory. It called for independent preservation of user revisions, with only explicitly superseded requirements marked as such. The schema supported reference/version/conflict checking, not automatic semantic proof. Later discussion kept independent note updates, exact provenance, and effective requirements without freezing these exact field names or a full dependency graph.

**Sources: EVT-0249, EVT-0360, EVT-0414.**

<a id="p1-030"></a>
**P1-030 — Deterministic assembly must respect native protocol structure.** **Status: agreed direction.**

The proposed context compiler assembles stable instructions and tool definitions, effective user requirements, current working state, needed recent complete interactions, relevant evidence, and retrieval guidance. This is a logical composition, not permission to put everything in a system message. Tool calls/results must pair correctly. The compiler must not split incomplete tool interactions. It must preserve source identity, images, warnings, and protocol-specific reasoning items.

The adapter must not blindly replay different providers' opaque reasoning across a model switch. A manifest makes actual input inspectable without conflating context policy with Chat Completions or Responses wire encoding.

**Sources: EVT-0249, EVT-0318, EVT-1166.**

<a id="early-context-vocabulary"></a>
**The early names and fields, with their actual purposes.** EVT-0249 named this deterministic assembler `ContextCompiler`. It consumes already selected requirements, working state, interactions and evidence. It does not discover which table header matters by itself. The provider adapter then encodes valid native messages. In the later small-graph baseline these are cooperating responsibilities, not a mandate for a second context engine or independent policy database.

| Historical identifier | Meaning and the problem it addressed |
|---|---|
| `EventLog` | Original user/assistant/tool/context-change events. A later working view does not rewrite these originals. |
| `EvidenceStore`, `evidence_id`, `source_id`, `operation_id` | The stored result, the source it concerns, and the operation that produced it are different identities. The same source can have several OCR/render results. |
| `scope.physical_pages`, `content_ref`, `content_hash`, `media_refs` | Scope locates the result. A reference resolves bytes. A hash checks those bytes. Media references locate related original images. A hash alone does not recover a missing object or state whether the model read it. |
| `presentation.mode`, `presentation.reason` | Describes a chosen full/partial/reference presentation and why it changed. Changing presentation does not edit the evidence. `released_by_agent` was an illustrative reason, not proof the dependency was actually resolved. |
| `EvidenceHistory` | The old message-position mapping whose array offsets were fragile under reordering and cross-context retrieval. Stable evidence identity avoids confusing a shifted position with the original result. |
| `TaskContract` | Effective requirements and their original user provenance. The record retains later amendments. Summary prose cannot silently replace the human's requirements. |
| `WorkingState.revision`, `based_on_event` | The working-state update and source event on which a proposal depends. They can expose stale updates. They cannot prove that the agent understood the latest requirement correctly. |
| `current_work`, `open_items` with `id`, `description`, `evidence_refs` | Work and unresolved questions, such as checking the final column's unit against a particular result. A generic “page done” flag cannot carry that uncertainty. |
| `artifact_refs`, `retain_refs`, `notes` | Exact saved work, deliberately retained evidence, and explanation of dependencies/decisions. `document_v8` existing is a mechanical fact. A complete faithful table is a separate supported judgment. |
| `ContextManifest` | The events, evidence and state versions included or omitted in one assembled view, supporting inspection and stale-reference checking. It is not the entire database repeated in every request. |

For the pages 18–19 example, preserving `ev_0042` and `document_v8` is insufficient. The continuation must also say that page 19 uses page 18's header and the final unit remains uncertain. Conversely, that sentence alone cannot reproduce the exact header. Small notes and exact references solve complementary parts of the problem.

Filesystem JSON/JSONL was the original storage proposal. SQLite metadata plus immutable files later superseded it. These field spellings are preserved design vocabulary, not final schemas for Q1 or Q2.

**Sources: EVT-0249, EVT-0256, EVT-0318, EVT-0414, EVT-1166.**

<a id="p1-031"></a>
**P1-031 — Capacity is route-specific and checked before the request.** **Status: agreed direction.**

The proposal called for a route's effective context limit, output capacity/reserve, counting method and confidence, image accounting, and protocol abilities. The complete assembled request must fit after output reserve and estimation margin. Counting only text characters is insufficient. Normal operation, approaching capacity, and inability to send require distinct behavior. A reminder should identify major contributors. Organization must occur early enough to be feasible and leave headroom.

The app may use reliable token counting where available. Estimates and later usage calibration are not a capacity guarantee. The discussion rejected universal 80% or 85% triggers and assuming capacity from an alias.

**Sources: EVT-0137, EVT-0249, EVT-0414, EVT-1166.**

The early proposal expressed the pre-send comparison as:

```text
estimated complete input + output reserve + estimation margin
    <= effective capacity of the selected route
```

“Complete input” includes instructions, tools and their schemas, messages, selected evidence, and actual image/protocol content. Organization also needs enough input and output space to run. Intervention must begin while the app can still assemble a useful management request. This expression explains what the app must account for. It supplies neither numeric defaults nor a guarantee that an estimator matches the upstream provider.

A provider-reported overflow is a capacity problem to resolve, not a reason to repeatedly resend the same oversized request under network retry logic.

**Sources: EVT-0137, EVT-0249, EVT-0414.**

<a id="p1-032"></a>
**P1-032 — One oversized result has its own boundary.** **Status: agreed direction.**

Preserve the full result actually produced. Then evaluate the next input. When it fits, provide the requested representation. When it does not, first consider organizing existing context.

If the result itself exceeds capacity, explicitly return its size, scope, location, and available precise reads. The agent can then choose segments or scripts. Do not silently substitute the first few lines as though complete. Distinguishing execution success from successful full presentation avoids unnecessary repeated OCR. Preservation must not force unrequested OCR, word extraction, or rendering merely to fill an evidence record.

**Sources: EVT-0137, EVT-0249, EVT-0382, EVT-0414.**

Two different cases explain the fallback. The requested result may fit by itself while the accumulated working input does not. Releasing unrelated retrievable material or organizing older history may then make room for that result. If the result alone exceeds usable input capacity, even an empty history cannot make a full one-request presentation possible. In that case, preserve the result. Expose explicit ranges, representations, or a script route.

A notice must describe the content omitted from presentation. The statement “tool completed” does not mean “model received every byte.” This avoids both hidden omissions and repeating expensive work merely because presentation failed.

**Sources: EVT-0137, EVT-0249, EVT-0382.**

<a id="p1-033"></a>
**P1-033 — Candidate context before activation.** **Status: agreed direction, with later simplification.**

The first transition proposal asked the working agent to perform these steps:

1. Prepare continuation state.
2. Construct a candidate manifest.
3. Verify references, versions, message structure, and capacity.
4. Save the candidate.
5. Switch the active pointer.

A cheap separate summarizer was not a prerequisite. A failed summary or invalid reference must not discard the original history. New user instructions arriving during organization must survive. Revision checks prevent stale state becoming authoritative. Structural checking cannot prove semantic completeness. The later consolidation allows progressive reduction without requiring every intermediate organization step to fit the final normal-request target.

**Sources: EVT-0249, EVT-0414, EVT-1166.**

<a id="p1-034"></a>
**P1-034 — Proposed controls were capabilities, not a compulsory routine.** **Status: proposal/open.**

Suggested names were `context_status`, `context_select`, `update_working_state`, `compact_context`, and evidence read/search tools. Status could expose capacity and retained material. Select could retain/release/reload. Notes could update progress and dependencies. Compact could submit a handoff. Names and schemas were explicitly adjustable.

The agent need not query status every round or fill notes after every operation. The app should surface useful capacity information when needed. Neither this tool list nor module names are independent V1 requirements under the final reset.

**Sources: EVT-0249, EVT-1166.**

## Framework candidates, corrections, and the decision trail

<a id="p1-035"></a>
**P1-035 — The first LangChain/LangGraph inquiry.** **Status: proposal/open (historical comparison).**

The user asked whether these libraries could support the application's context management. The response distinguished their responsibilities:

- LangChain supplies model/tool/agent interfaces and summary middleware.
- LangGraph supplies state, graph control, persistence, and continuation.
- LangMem supplies separate `summarize_messages`, running-summary, and `SummarizationNode` components.

App-side model summaries do not need provider-native compaction. The first recommendation favored custom-controller improvement or partial summary-component reuse, retaining existing evidence tools. It judged whole-graph migration to be larger. The assistant revised this recommendation when the user prioritized long-term reliability and maintenance.

**Sources: EVT-0138, EVT-0139, EVT-0146, EVT-0250, EVT-0256.**

<a id="p1-036"></a>
**P1-036 — Framework help has a boundary.** **Status: agreed direction.**

A framework can host precise PDF tools and manage messages/state. It does not decide which OCR/layout/images remain necessary or automatically preserve a cross-page relationship. It cannot establish complete source coverage from semantic-search hits or prove fidelity. The app still needs source/evidence identity, exact ranges, real pixel delivery, versioned output, effective requirements, and recoverable useful work. LangGraph checkpoints persist execution state and do not by themselves shorten input. A memory backend in RAM is not process-restart persistence.

**Sources: EVT-0146, EVT-0256, EVT-0265, EVT-0318.**

<a id="p1-037"></a>
**P1-037 — Defaults and wrappers must be checked, not inherited.** **Status: agreed direction.**

The historical LangMem documentation said that the component could trim overlarge summary inputs to their last portion. This conflicts with silent-loss avoidance unless the app handles coverage and segmentation. Summary middleware itself can call a model and may retry. Thus, cancellation, time, usage, and retry budgets must have a shared owner. Translating native messages into framework forms and back must preserve tool pairing, images, and relevant Responses items. `ChatOpenAI`'s documented treatment of third-party nonstandard reasoning fields was a concrete risk, not a proof that the whole LangChain ecosystem is unusable.

**Sources: EVT-0146, EVT-0256, EVT-0265, EVT-0318.** Historical references: [LangMem API](https://langchain-ai.github.io/langmem/reference/short_term/), [summary middleware](https://reference.langchain.com/python/langchain/agents/middleware/summarization), [ChatOpenAI scope](https://docs.langchain.com/oss/python/integrations/chat/openai).

The exact component distinctions matter:

- `SummarizationMiddleware` selects when to summarize and what recent material to retain.
- `summarize_messages` / `SummarizationNode` can maintain a running summary.
- `InMemorySaver` keeps graph checkpoints in RAM.
- The proposed `SqliteSaver` provides persistent graph checkpoints.

None supplies all four responsibilities. A `max_tokens` limit that supplies only the tail to a summarizer does not establish coverage of the whole older interval. A persistent graph checkpoint still cannot atomically commit external document files. The [component mechanism explanation](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#summary-and-checkpoint-components) shows the request, coverage and restart consequences without selecting these components as dependencies.

**Sources: EVT-0146, EVT-0256, ATT-03, EVT-0318.**

<a id="p1-038"></a>
**P1-038 — The user made reliability and remaining maintenance central.** **Status: agreed direction.**

The user challenged the custom-controller preference because mature frameworks seemed more reliable, then asked whether they actually fit or whether custom code would function better. The assistant revised its recommendation: reuse suitable general mechanisms and keep PDF-specific rules, instead of enlarging a home-built runtime solely because it already exists. A framework may reduce maintenance of loops, message handling, checkpoints, and recovery, but does not guarantee integration reliability, source quality, or compatibility. These are engineering judgments, not measured reliability rankings.

**Sources: EVT-0250, EVT-0251, EVT-0256, EVT-0259, EVT-0260, EVT-0265.**

<a id="p1-039"></a>
**P1-039 — The high-level-first recommendation was provisional.** **Status: corrected/rejected (superseded ranking).**

The revised sequence first compared Deep Agents and LangChain `create_agent` with limited middleware, both using LangGraph. It added LangMem only for an actual missing function. Later it ranked `create_agent` first, with direct LangGraph second if higher-level abstraction obstructed control. It recommended a custom controller only if even lower-level framework use introduced a concrete obstacle.

Reasons to use a thinner framework included private-API workarounds, loss of native images/reasoning/message control, and competing execution-state authorities. Another reason was an adapter costing more than the code it replaced. The final preferred small StateGraph baseline supersedes this order. No automatic fallback ladder is an active requirement.

**Sources: EVT-0256, EVT-0265, EVT-1166.**

<a id="p1-040"></a>
**P1-040 — A graph can express an autonomous agent.** **Status: agreed direction.**

LangGraph need not encode `inspect → OCR → draft → revise` as a fixed document workflow. It can express a small control loop such as context preparation, model decision, chosen-tool execution, preservation, and continuation. The model still decides methods and branches. `create_agent` is a native agent abstraction rather than only old static chains. Deep Agents uses LangChain/LangGraph infrastructure. ReAct is an action pattern and does not replace its runtime.

Graph persistence/forking cannot undo external side effects automatically.

**Sources: EVT-0265, EVT-0266, EVT-0281, EVT-0297.** Historical references: [workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents), [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview), [time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel).

<a id="p1-041"></a>
**P1-041 — Forum terminology and the “three-line loop” claim.** **Status: corrected/rejected.**

The user's quoted forum comments called a fixed workflow “closed loop” and feedback-driven exploration “open loop”. Standard feedback-control usage is the reverse. The intended distinction was fixed workflow versus open-ended task autonomy. Stronger models can reduce hand-coded domain branches. The app must still determine actual visible evidence, capacity behavior, candidate versus committed state, valid image/protocol handling, and the version behind a completion claim. A short conceptual loop does not demonstrate a reliable runtime of equally small size.

**Sources: EVT-0266, EVT-0268, EVT-0281, EVT-0297.**

<a id="p1-042"></a>
**P1-042 — The wider forum debate represented competing experience.** **Status: proposal/open (unverified opinion).**

The forum comments advocated several approaches:

- Learn Pi/Codex/Claude Code internals before choosing a framework.
- Use thin loops, bash and memory files.
- Use mature runtimes or agent SDKs.
- Use LangGraph for state, API calls, tools, observability, and maintainability.

Others described repeated rewrites of home-built frameworks, reconstruction of ReAct-like graphs, steep learning curves, and awkward unsupported operations. They also described fast-moving paradigms and prototype-first then custom implementations. Some mentioned Google ADK, Antigravity, DeepSeek Harness, Claude Agent SDK, OpenSandbox, Docker, and Kubernetes. These anecdotes concerned varied products and loads. They did not select dependencies, mandate production monitoring, or establish that the PDF app needs multi-agent or container orchestration.

**Sources: EVT-0266, EVT-0297.**

<a id="p1-043"></a>
**P1-043 — Compare candidates at the correct layer.** **Status: proposal/open (historical comparison).**

Pi supplies an agent loop and, in its richer coding SDK, sessions, branching, compaction, events, and extensions. LangChain/LangGraph provide composable loops, state, middleware, and persistence. Deep Agents adds a more assembled filesystem/offloading/summary harness. OpenAI Agents SDK supplies an agent runner, tools, sessions, and handoffs. The ordinary OpenAI API client primarily supplies API access.

A self-made controller maximizes direct control while retaining responsibility for all runtime behavior. Download counts, code size, feature quantity, and time to a demo do not settle maintenance or reliability.

**Sources: EVT-0266, EVT-0268, EVT-0297, EVT-0318.**

<a id="p1-044"></a>
**P1-044 — Pi's actual strengths and limits.** **Status: proposal/open (historical candidate).**

The discussion identified Pi as the `badlogic/pi-mono` / later linked Pi project. Its lower agent layer exposed `transformContext` and `convertToLlm`. The richer SDK supported embedding in Node.js/Bun and supplied persistent sessions and compaction. `context_edit` could change the later-visible content while retaining original entries. `session_before_compact` could cancel, adjust, or supply compaction.

A TypeScript runtime could cooperate with Python PDF tools. Pi was not merely an external CLI. Lower-level loop adoption still leaves session/compaction integration, while fuller SDK adoption carries coding defaults to review. Historical Pi 1.3.0 defaults included image resizing and truncated tool-result material in summary serialization. Preserve original pixels and adequate summary material through public settings/extensions.

**Sources: EVT-0297, EVT-0318, EVT-0349, ATT-04.** Historical references: [Pi SDK](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md), [session format](https://github.com/earendil-works/pi/blob/v1.3.0/packages/coding-agent/docs/session-format.md), [compaction](https://github.com/earendil-works/pi/blob/v1.3.0/packages/coding-agent/docs/compaction.md).

<a id="p1-045"></a>
**P1-045 — Deep Agents' actual strengths and limits.** **Status: proposal/open (historical candidate).**

Deep Agents provided large-result offloading, file access, history summaries, optional agent-driven `compact_conversation`, persistence through LangGraph, and public backend/middleware customization. The reviewed 0.7.29 source already handled inline media offloading and image references, so describing it as text-only was inaccurate. Size and recency policies still needed to respect useful old headers, corrections, drafts, and reliable original storage. One offload-failure branch could continue summarization, but that alone did not prove permanent loss because original state, checkpointer, and independent evidence storage also mattered.

**Sources: EVT-0265, EVT-0331, EVT-0349, EVT-0358, EVT-0360, ATT-04.** Historical references: [context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering), [0.7.29 summarization](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.29/libs/deepagents/deepagents/middleware/summarization.py), [customization](https://docs.langchain.com/oss/python/deepagents/customization).

<a id="p1-046"></a>
**P1-046 — OpenAI client and Agents SDK are distinct options.** **Status: proposal/open (historical candidate).**

Both support configuration or adaptation for non-OpenAI endpoints in appropriate ways. Neither forces official pay-as-you-go service. The API client does not supply a full agent/context system. Agents SDK supplies more runtime structure, with Python and TypeScript routes. Some published memory examples depend on provider-side Responses compaction. The Nexus portable baseline cannot assume those examples are available.

A custom session strategy may fit, but it still needs the required behavior. ATT-03 selected the Python client while presenting a verdict on all candidates without actually evaluating Agents SDK. That comparison was incomplete.

**Sources: EVT-0297, EVT-0318, ATT-03.** Historical references: [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk), [providers](https://developers.openai.com/api/docs/guides/agents/models), [custom session example](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory).

<a id="p1-047"></a>
**P1-047 — Nexus fit must be evaluated per route.** **Status: agreed direction.**

Pi's `baseUrl`, `openai-completions`/`openai-responses`, and thinking/reasoning compatibility options were promising interfaces, not proof of a working Nexus route. The `pi-cliproxyapi-provider` plugin used a specific model catalog and `/backend-api/` routes that Nexus might not expose. Deep Agents' integrations similarly needed per-route examination. `ChatOpenAI` was not its only possible path. Real tool/image round-trips, native items, pairing, and capability settings matter more than a blanket “OpenAI-compatible” label. The discussion included no end-to-end test of a proposed framework here.

**Sources: EVT-0265, EVT-0297, EVT-0331, EVT-0349, EVT-0360, EVT-0382.**

<a id="p1-048"></a>
**P1-048 — Pi's first-place ranking was expressly withdrawn.** **Status: corrected/rejected.**

The user requested the best fit with minimal modification and permitted a complete rebuild. EVT-0349 ranked Pi first, Deep Agents second, and direct LangGraph third. It proposed Electron → independent Node Pi runtime → Nexus and Python PDF tools. That proposal included PDF context extensions, evidence/artifact storage, and route adapters. The rationale credited Pi's separation of original session from active input. ATT-04 repeated that same answer for adversarial review.

EVT-0360 withdrew the “Pi needs the least work” conclusion. Deep Agents also constructs effective messages from summary events without simply deleting original state. LangChain can alter one request without mutating stored state. No measurement established the maintenance ranking.

**Sources: EVT-0319, EVT-0320, EVT-0346, EVT-0349, EVT-0350, EVT-0351, EVT-0358, EVT-0360, ATT-04.**

The concrete correction named Deep Agents' `_summarization_event` and `_get_effective_messages()`. Summary information can describe an older covered interval. A temporary effective-message list supplies that summary plus the remaining messages to the model. Preserved original state and projected input are therefore separate.

These underscored historical implementation names are evidence for withdrawing the asymmetric ranking, not supported customization APIs to depend on. Whether those originals survive a process restart still depends on persistence. The [state-projection explanation](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#framework-state-projection) compares this mechanism with Pi's `context_edit`, `transformContext`, `convertToLlm`, and `session_before_compact`.

**Sources: EVT-0349, EVT-0360, ATT-04.**

For a reader encountering these recommendations out of order, the decision trail is:

| Discussion stage | Historical recommendation | Why its authority changed |
|---|---|---|
| EVT-0249 | Keep the Python controller and add an app-owned context manager. Initially use files/JSON. | It prioritized reuse of the existing controller. The user then made long-term framework reliability and maintenance central. |
| EVT-0256 / EVT-0265 | Consider higher-level Deep Agents or `create_agent` before a direct graph | A provisional way to reuse mature loop/session machinery, subject to native-protocol and domain-control fit. |
| EVT-0349 | Pi first, Deep Agents second, direct LangGraph third | The “least modification” reasoning overcredited Pi's original-record/active-context separation. |
| EVT-0360 | Withdraw the Pi-first verdict and compare equivalent public customization fairly | Deep Agents and LangChain also separate preserved state from effective request messages. No measured least-maintenance result existed. |
| EVT-1148 / EVT-1166 | Prefer a small Python StateGraph and SQLite. Settle only three remaining contracts. | This later bounded consolidation controls the rebuild. It does not retrospectively turn any earlier candidate assessment into an implementation result. |

The durable lesson is to preserve responsibilities and evaluate actual integration work. There is no remaining mandate to run the abandoned ranking sequence before implementation.

**Sources: EVT-0249, EVT-0256, EVT-0265, EVT-0349, EVT-0360, EVT-1148, EVT-1166.**

<a id="p1-049"></a>
**P1-049 — Fair comparison counts the same work on both sides.** **Status: agreed direction.**

Treating Pi customization as a benefit while treating equivalent Deep Agents customization as a cost was asymmetric. Both need effective requirements, unresolved dependencies, useful drafts, exact retrieval, adequate summary input, and storage checks. An “extension” and a “middleware” can each contain substantial code. Module counts do not measure work.

Compare public configuration, remaining domain code, and any need for private internals or a fork. This comparison does not imply a full semantic dependency graph. Agent notes and precise references may suffice. Automatic saving/offloading does not inherently violate autonomy. The relevant question is accessible content and preservation of useful understanding.

**Sources: EVT-0360, EVT-1166.**

<a id="p1-050"></a>
**P1-050 — Total integration burden and scenario comparisons.** **Status: proposal/open (historical evaluation method).**

The conversation proposed checking these scenarios:

- An oversized stored OCR result with full/range retrieval.
- An older header still needed on the next page.
- A mid-task corrected requirement with an unsaved draft.
- Restoration of original pixels.
- Stale references after an edit.
- Requirements arriving during compaction.

It also counted Electron/runtime lifecycle, Python IPC, session/evidence/version consistency, and upgrade maintenance. The corrected recommendation temporarily favored mapping Deep Agents public settings first, using Pi as a contrast. It also recognized direct LangGraph's value for custom execution/recovery. These were candidate-evaluation ideas, not authorization for new PoCs or a renewed benchmark matrix. The final architecture reset closed framework ranking as an independent research problem.

**Sources: EVT-0297, EVT-0349, EVT-0360, EVT-0414, EVT-1166.**

## The two forum originals: useful ideas and their limits

<a id="p1-051"></a>
**P1-051 — Different source types require different confidence.** **Status: agreed direction.**

The user explicitly questioned the credibility of two saved forum pages. ATT-01 is piggy's AI-assisted Chinese translation/reposting of Lilian Weng's *Harness Engineering for Self-Improvement*, attributed to 2026-07-04. It is a research survey rather than a uniform industrial standard. ATT-02 is an image-based explanation by 古希腊代码之神. It mixes Manus, Letta/MemGPT, Mem0, Claude Code, Deep Agents, a survey taxonomy, benchmark results, code screenshots, reverse engineering, and interpretation.

The historical assistant reported reading all ten substantive image pages and checking selected first-party claims. This rebuild independently read those pages and ATT-01's text and illustrations. Preserve specific claims and confidence, rather than approving or rejecting a whole forum answer.

**Sources: EVT-0147, EVT-0148, EVT-0158, EVT-0183, EVT-0185, ATT-01, ATT-02.** Original trail: [Weng article](https://lilianweng.github.io/posts/2026-07-04-harness/).

<a id="p1-052"></a>
**P1-052 — What the forum review contributed to this product.** **Status: agreed direction.**

The review retained these useful themes:

- Persistent originals with precise retrieval.
- Release of retrievable old tool material before paying for broader summaries.
- Model content judgment with harness execution.
- Separately recorded working state.
- Failure traces that distinguish oversized outputs, missing summary information, poor retrieval, mistaken interpretation, and network failures.

“Harness-owned context” can still use model judgment and model-generated handoffs. These themes support the already agreed division of responsibility. Forum discussion of background-task cancellation establishes nothing about Nexus's remote cancellation. The pages contain much more context material than retry-budget or unknown-outcome analysis.

**Sources: EVT-0185, ATT-01, ATT-02.**

<a id="p1-053"></a>
**P1-053 — ATT-01's harness and self-improvement framing.** **Status: proposal/open (research background).**

The survey traces recursive self-improvement to I. J. Good and Yudkowsky, then distinguishes direct weight changes from improving training and deployment systems. A harness surrounds a model with observation, planning, tools, state, permissions, evaluation, and artifact handling. Its design may become more general as model capability improves. Models may absorb prompt tricks, while goals, constraints, interfaces, context, and evaluation remain necessary.

The text favors deliberate simplicity and familiar filesystem/software practices, with an operating-system analogy. It predicts near-term improvement of mechanisms around a model rather than assuming direct self-rewriting weights. None of this authorizes a self-modifying PDF agent.

**Sources: ATT-01, EVT-0185.**

<a id="p1-054"></a>
**P1-054 — ATT-01's basic patterns and tools.** **Status: proposal/open (research background).**

The survey describes goal-driven plan/act/observe/refine loops, persistent files instead of carrying every log in context, and explicit inspectable subagent/background-task management where needed. The parent may launch, monitor, cancel, and merge isolated tasks. Durable files/logs make their results recoverable rather than hidden in transient chat. Coding examples list discovery/read/edit/patch tools, shell execution, language-server and Git operations, MCP/skills, web/browser tools, artifact readers/generators, scheduled jobs, and agent delegation. Its diagrams show the model/tool loop and iterative coding/testing.

These are examples of general agent interfaces. They do not require scheduling, multi-agent orchestration, broad shell access, or all coding tools in this app.

**Sources: ATT-01.**

<a id="p1-055"></a>
**P1-055 — ATT-01's context-optimization research.** **Status: proposal/open (research background).**

ACE uses generator, reflector, and curator roles. Trajectories yield insights, and incremental merges update identified context items instead of rewriting a whole playbook. This addresses brevity bias and context collapse. MCE separates the mechanism for building context from its contents. It uses a base optimizer and a meta-level skill search with static material, dynamic search/selection/filtering/formatting, historical scores, and skill recombination.

Meta-Harness searches executable context-management/harness code. Candidate directories retain code, scores, traces, and state. Its evaluator considers only interface-valid candidates. The survey's diagram returns a Pareto frontier rather than one universal winner. It reports text-classification and Terminal-Bench-2 results seeded from strong existing harnesses. These numbers are not PDF-quality predictions.

**Sources: ATT-01.**

<a id="research-context-algorithms"></a>
**What those research loops actually change.** ACE's Generator performs a task with a playbook. The Reflector derives lessons from the trajectory/outcome. The Curator proposes identified playbook-item changes. A deterministic merge applies those changes, with consolidation/deduplication to keep the playbook usable.

“Brevity bias” means repeated whole-document rewriting can progressively prefer short generic advice. The term “context collapse” means accumulated useful detail disappears. Keeping identified items reduces that particular rewrite pressure. This is a playbook-update method. It does not establish that a delta-only task handoff suffices after its prior anchor leaves input. The final V1 handoff remains self-sufficient.

MCE distinguishes static context components such as prompts, knowledge and code from dynamic operators such as search, select, filter and format. Its inner process optimizes context for task use. Its outer process uses results and traces to revise/recombine the context-building skill, represented by material such as `skill.md`.

Meta-Harness moves the searched object further toward executable harness code. Its loop has these steps:

1. Retain candidate code and its scores/traces.
2. Let a proposer inspect earlier attempts.
3. Generate candidates.
4. Reject interface-invalid candidates.
5. Evaluate eligible candidates.
6. Repeat under a finite search budget.

A Pareto frontier retains different quality/cost tradeoffs instead of pretending there is one winner on every objective. These algorithms explain why persistent negative evidence and evaluators matter. They do not authorize an automatic search process in this app.

**Source: ATT-01 text and figures 03–05, historical research summary, not newly verified results.**

<a id="p1-056"></a>
**P1-056 — ATT-01's workflow-search research.** **Status: proposal/open (research background).**

The AI Scientist example covers ideation, novelty checks, experiments, tuning, ablations, logging, plots, writing, and review. ScientistOne emphasizes traceable chains of evidence for claims. Autodata uses a challenger, weak and strong solvers, and a verifier to create appropriately difficult training examples. These examples train a weaker solver rather than recursively improving the strong one. The survey therefore limits the RSI interpretation.

ADAS archives agent programs, asks a meta-agent to propose and refine novel code, evaluates it, and retains successful candidates. AFlow represents workflows as graphs and uses a Monte Carlo tree search with evaluation, expansion, and bounded stopping. The attached benchmark table spans QA, coding, and math rather than conversion.

**Sources: ATT-01.**

<a id="research-workflow-search"></a>
**The selection rules explain the limits.** In Autodata, a challenger proposes tasks and a verifier compares weak/strong solver outcomes. Cases where the strong solver succeeds and the weak one fails target useful training difficulty. Improving that weak solver can resemble distillation without establishing recursive improvement of the strong solver.

ADAS keeps an archive of tested agent programs. It proposes a new coded agent, uses feedback to refine novelty/correctness, and evaluates it. It then adds a successful candidate for later proposals. Its archive supplies examples and failed directions, not only the latest prompt.

AFlow represents LLM operations as nodes connected by executable control edges. Its Monte Carlo tree search balances higher scores with exploration. It asks a model to alter a selected workflow, evaluates the change, and stops on its budget or improvement criterion. The comparison measures those evaluated tasks, not arbitrary software quality.

The AI Scientist's idea/novelty, preliminary experiment, tuning/research/ablation, logging, plot/write/review stages describe an automated paper-production workflow. Completing those stages does not guarantee an important scientific discovery. ScientistOne's chain of evidence asks whether supporting material substantiates a claim, citation, number or method. The useful distinction here is between an executed workflow and a substantiated conclusion.

**Source: ATT-01 text and figures 06–09.**

<a id="p1-057"></a>
**P1-057 — ATT-01's self-improving harness caution.** **Status: proposal/open (research background).**

STOP recursively improves an improver against average downstream utility. It discovered strategies including genetic search, decomposition, multi-armed prompting, temperature variation, annealing, and beam/tree search. The survey reports improvement with GPT-4 and degradation with weaker GPT-3.5/Mixtral settings. Recursion therefore does not remove the need for capable models.

Self-Harness mines rich failure traces and distinguishes similar terminal symptoms with different causal mechanisms. It proposes bounded diverse edits and accepts only candidates without regressions on held-in and held-out sets. Existing passing behavior and rejected attempts remain visible. The survey warns that self-edited operating boundaries, permissions, and evaluators must not simply fall inside the optimization loop. These are research cautions, not a new automatic optimization cycle for V1.

**Sources: ATT-01.**

<a id="p1-058"></a>
**P1-058 — ATT-01's evolutionary and weight-update research.** **Status: proposal/open (research background).**

Promptbreeder evolves prompts and mutation prompts. GEPA uses trajectory reflection with evolutionary search. AlphaEvolve keeps candidate program pools, generates diffs with fixed models, and marks editable regions. It studies the value of search, context, metaprompts, broader editing, and stronger models.

ShinkaEvolve pursues sample efficiency through parent choice, novelty rejection, and successful-pattern summaries. ThetaEvolve combines search with learning. DGM evolves editable agent harness code. Hyperagents adds a meta-agent controlling changes. The survey reports DGM benchmark improvements but notes that automatic evaluation, sampling cost, slow/ambiguous judges, and domain choice limit generalization.

SIA jointly chooses harness or weight updates. Strong/weak-model and weak-baseline confounds make its evidence hard to interpret. Self-play, synthetic data, test-time learning, and continual learning are adjacent topics rather than this app's roadmap.

**Sources: ATT-01.**

<a id="research-evolution-mechanics"></a>
**Evolution changes a candidate under an evaluator.** AlphaEvolve's illustrated loop is `database.sample` → `prompt_sampler.build` → `llm.generate` → `apply_diff` → `evaluator.execute` → `database.add`. It chooses a parent, constructs the prompt, generates/applies a change, evaluates it, and retains the evaluated candidate. `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` delimit editable regions in the example. A human still defines the problem and evaluator. This is frozen-model program search, not automatically a model-weight update.

ShinkaEvolve's mechanisms include parent choice balancing performance and offspring history, embedding-cosine novelty checks that can reject near-duplicates, and summaries of successful mutation patterns. DGM similarly uses evaluated harness variants and parent/offspring selection. Hyperagents adds modification of the meta-agent's control behavior. In SIA the feedback agent can choose a harness edit or a weight update such as LoRA reinforcement learning. Using a stronger model for meta/feedback work than the task baseline confounds a claim that the improvement comes solely from self-improvement.

ThetaEvolve combines evolutionary/in-context search with learning. Thus, its changes are not exclusively fixed-weight harness edits.

STOP passes the improver itself to the previous improver and judges the result by average downstream utility. Its pictured recurrence is `I_t = I_(t-1)(u_hat, I_(t-1), L)`. The learned search strategies and the regressions with weaker models explain why recursion is not a guarantee of improvement.

Self-Harness instead uses failure traces to identify a causal weakness. It proposes bounded edits with prior passing behavior and failed attempts visible. It then checks held-in and held-out behavior before accepting a change. Rejection retains the previous working version. Validators and permission boundaries cannot safely become whatever the candidate chooses to rewrite. These are mechanisms and cautions from the supplied survey, not an adopted optimization engine.

**Source: ATT-01 text and figures 10–14.**

<a id="p1-059"></a>
**P1-059 — ATT-01's failure taxonomy and long-term cautions.** **Status: proposal/open (research background).**

A study of autonomous research attempts described six recurrent failures:

- Training-default assumptions.
- Implementation drift under pressure.
- Memory/context loss.
- Excessive optimism despite weak results.
- Missing domain craft.
- Poor scientific question selection.

The survey adds weak evaluators, memory lifecycle, publication bias against negative results, diversity collapse, and reward hacking. It also identifies short-horizon benchmarks that miss maintainability, ownership, migration, compatibility, and future debugging. It suggests preserving failed attempts, separate evaluators and permission controls, trace audits, and human supervision at meaningful decisions. The useful transfer is disciplined evidence and scope. Neither mandatory repeated review nor a general research platform follows.

**Sources: ATT-01.**

<a id="p1-060"></a>
**P1-060 — ATT-01's benchmark appendix is background only.** **Status: proposal/open (research background).**

The appendix lists these benchmarks:

- PaperBench: 20 ICML papers and 8,316 grading items.
- CORE-Bench: 270 reproduction tasks from 90 papers.
- ScienceAgentBench: 102 tasks from 44 publications.
- RE-Bench: seven ML engineering environments and human-versus-agent time-budget comparisons.
- MLE-bench: 75 Kaggle competitions.
- KernelBench: 250 PyTorch tasks measuring correctness and speed.

Reported scores include weak reproducibility results and agents' advantage at short budgets versus stronger human returns with longer time. These illustrate evaluation design and limitations. They do not establish a necessary benchmark suite, acceptance threshold, or expected PDF performance. The original attachment retains its full 35-item bibliography and figures for exact research provenance.

**Sources: ATT-01.**

<a id="p1-061"></a>
**P1-061 — ATT-02's harness-performance claim was too strong.** **Status: corrected/rejected.**

The image essay's “binding-constraint” claim says the harness determines production reliability rather than the model. It cites fixed-model Deep Agents changes taking Terminal-Bench 2.0 from 52.8% to 66.5%. Those changes involved prompt/self-check instructions, environmental context, and loop/exit hooks. It also cites Meta-Harness and contrasts these gains with modest model upgrades.

Fixed-model gains show that a harness matters, not that model ability does not. The source's claimed 2–4 percentage-point model-upgrade comparison and benchmark plots are workload-specific. The conversation did not transfer these gains or forced self-check hooks to PDF conversion.

**Sources: ATT-02 image 1, EVT-0183, EVT-0185.** Historical reference: [Deep Agents harness engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering).

<a id="p1-062"></a>
**P1-062 — ATT-02's taxonomy and long-context rationale.** **Status: proposal/open (research background).**

The essay uses a seven-part execution/tooling/context/lifecycle/observability/verification/governance taxonomy, then organizes examples along a task's execution. It distinguishes short working input, medium-term external notes/plans, and long-term retrievable memory. It offers dense-attention cost, *Lost in the Middle*, and *Context Rot* as reasons why a bigger window does not ensure useful recall. Particular model counts, percentage drops, and the illustrative “200k window may deteriorate around 50k” do not establish a universal trigger. The conversation retained concern about length and position while rejecting fixed degradation thresholds.

**Sources: ATT-02 image 2, EVT-0185.**

The source calls the taxonomy **ETCLOVG**:

- **E**xecution supplies the execution environment.
- **T**ooling supplies callable interfaces/protocols.
- **C**ontext organizes memory/input.
- **L**ifecycle controls orchestration/continuation.
- **O**bservability records what happened.
- **V**erification checks outcomes.
- **G**overnance applies operating constraints.

This taxonomy is comparison vocabulary, not a requirement for seven services. The dense-attention `n²` argument counts pairwise token relationships and helps explain prefill/first-token costs. It is not a universal formula for every model architecture or total task latency. Positional recall and context-length degradation are empirical concerns separate from the nominal window size.

**Source: ATT-02 image 2.**

<a id="p1-063"></a>
**P1-063 — ATT-02's prompt-cache advice needs workload and pricing context.** **Status: corrected/rejected.**

The essay describes stable prefixes, append-only history, stable serialization, avoiding changing time near the front, and tool-use logit masking with stable tool lists/prefixes. It cites Manus-style input-heavy workloads, roughly 80%+ hit rates, cached-versus-uncached API prices, and first-token latency reductions. These examples explain possible reuse, not the user's subscription billing or a mandatory hit-rate target. Cache impact begins at a differing prefix and depends on provider behavior. It does not prove that every context change destroys all cache.

Preserve useful stable instructions, schemas, ordering, and settings where practical. Allow compaction when capacity or continuation needs it. Logit masking is an external example, not an adopted interface requirement.

**Sources: ATT-02 image 3, EVT-0185, EVT-0382.** Historical reference: [Manus context engineering](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus).

<a id="forum-cache-mechanics"></a>
**How the cache examples work.** The pictured aggregate hit ratio is `sum(cached_prefix_tokens) / sum(input_tokens)`. Input volume weights that ratio, so it differs from averaging one percentage per request. An early changing timestamp, reordered schema, or different serialization can alter the reusable prefix even when the later substantive content is unchanged. Stable tool definitions avoid that source of churn. They do not keep an ever-growing transcript within capacity.

The illustrative accounting assumes fixed input volume `N`, output volume `M`, hit fraction `h`, and prices `p_cached`, `p_uncached`, `p_output`. Its expression is `N × ((1-h) × p_uncached + h × p_cached) + M × p_output`. Under the screenshot's illustrative tenfold cached-input discount, increasing `h` by one percentage point reduces the input charge by `0.009 × N × p_uncached`. That reduction is a fraction of the hypothetical all-uncached input charge. It is not a universal 0.9% saving on the current whole-task bill.

Changed call volume, organization output, rereads and subscription accounting can change the conclusion. The source's input-heavy 100:1 example explains its emphasis on cache. It does not establish this app's workload or prices.

The **ToolUse logit masking** example keeps a stable tool catalog in the prompt. At a particular step, it permits only selected output tool tokens, including groups with names such as `browser_` or `shell_`. It masks the disallowed choices. Masking decoder choices is different from deleting/rebuilding tool schemas in the prefix.

This requires an appropriate runtime/model capability. The discussion did not establish availability through this Nexus route. The design therefore retains practical stable prefixes without adopting that masking interface, a permanent append-only history, or a fixed hit-rate target.

**Sources: ATT-02 image 3, EVT-0185, EVT-0382. Arithmetic above explains the stated pricing assumptions, it is not a measured saving.**

<a id="p1-064"></a>
**P1-064 — ATT-02's Letta/MemGPT example.** **Status: proposal/open (research background).**

The essay likens current context to RAM and archival/recall stores to disk, with model-driven swapping. It shows a memory-oriented system prompt, detailed tool docstrings, exact replacement, append/archive operations, and a runtime memory-pressure warning followed by model-assisted organization. The example makes memory operations understandable and available, with capacity signals and an opportunity to preserve useful state. Anthropomorphic prompt wording, specific functions, warning counters, and the pictured code are source material. They are not app instructions or proof that a particular warning policy always works.

**Sources: ATT-02 images 3–5, EVT-0185.**

<a id="forum-memory-operations"></a>
**What the pictured memory operations do.** The MemGPT diagram separates system instructions and working context, a FIFO conversation queue and output buffer, from external archival storage and recall storage. Its “heartbeat” lets the agent request continued execution after a tool operation. It is not a scheduled reminder or the desktop app's automation feature. JSON-schema descriptions present tool docstrings so the model knows when and how to use memory operations. Description quality helps choice, but is not a software guarantee of correct use.

The screenshot's `core_memory_replace(agent_state, label, old_content, new_content)` selects a named memory block and requires the specified old content to be present. It then replaces that content. Empty new content can remove the matched material. A missing old string yields an error instead of silently claiming a successful edit. `core_memory_append` adds content, while `archival_memory_insert(content, tags=None)` places material in external archival memory.

These operations explain explicit editable memory. They do not automatically infer that the stored statement is correct or globally applicable to a PDF.

The warning example compares usage against `summarizer_settings.memory_warning_threshold`. It tracks whether `agent_alerted_about_memory_pressure` already marks an alert and exposes `response.usage.total_tokens` / `summarize_messages_inplace()` in the pictured control path. Its warning creates an opportunity for the model to preserve useful information before stronger organization. Check the usage field's meaning and the warning's timing in the actual implementation. Total usage is not by name alone a complete next-request capacity estimate.

This reference selects no value or exact warning algorithm from the screenshot. The original screenshot clips part of its code. These names and visible operations are explanatory historical evidence rather than reconstructed runnable code.

**Source: ATT-02 images 4–5.**

<a id="p1-065"></a>
**P1-065 — ATT-02's Mem0 contrast.** **Status: proposal/open (research background).**

The essay contrasts explicit agent-managed memory with an application workflow that extracts facts after a dialogue and injects retrieved material later. It claims the then-current implementation simplified model-selected ADD/UPDATE/DELETE/NONE decisions into streamed addition plus system-side retrieval/deduplication. It illustrates fusion of semantic vectors, BM25, and entity matches before reranking. This is an example of an alternative memory architecture. It does not establish requirements for a vector database, automatic fact extraction, or semantic-search-only PDF coverage. This rebuild did not independently revalidate claims about current Mem0 code.

**Sources: ATT-02 images 5–6.**

<a id="forum-fused-retrieval"></a>
**Retrieval and reranking are two steps.** The pictured Mem0 path first requests a wider candidate set, illustrated by `internal_limit = max(limit * 4, 60)`, then calls `score_and_rank`. Its signals include vector similarity, normalized BM25 lexical relevance and entity overlap. Vector similarity can retrieve related meaning without exact wording. BM25 rewards relevant terms. Entity matches favor the named things in the question.

Combining those signals can change ordering before returning the requested number of results. The multiplier/floor and fusion implementation are screenshot details, not tuned defaults for this app.

Ranking chooses likely useful matches from candidates. It cannot prove that the results represent every table cell, footnote, or page range. Model-extracted facts are derived interpretations, whereas the original OCR/text/image bytes remain source evidence.

The source contrasts model-selected `ADD` / `UPDATE` / `DELETE` / `NONE` with streamed `ADD` and deterministic deduplication. This describes a claimed implementation evolution. It is not a freshly verified Mem0 version fact or permission to replace exact evidence with inferred memory.

**Source: ATT-02 images 5–6.**

<a id="p1-066"></a>
**P1-066 — ATT-02's Claude Code instruction and compaction examples.** **Status: proposal/open (version-specific illustration).**

The essay discusses enterprise/user/project/local `CLAUDE.md` levels, concatenation and instruction placement. Its reverse-engineered code prepends project instructions as a user-role message with metadata. It then illustrates these mechanisms:

- Light tool-result cleanup before heavier summary compaction.
- Output reserve plus a cited 13,000-token buffer.
- Retention of recent results.
- Time-triggered cleanup to reduce cache costs.
- A guard against recursive compaction calls.

These were code screenshots/analysis, not stable official contracts. The discussion did not adopt the 13,000 buffer, internal APIs, ordering, or a fixed recent count as product requirements. The names still help explain the mechanism, so this reference preserves them below with that status. The source claims that guidelines shape rather than mechanically enforce behavior. This reinforces the distinction between prompt intent and software guarantees.

**Sources: ATT-02 images 6–9, EVT-0183, EVT-0185.**

<a id="forum-instruction-injection"></a>
**Instruction discovery, message role and display metadata differ.** The essay lists enterprise rules, user `~/.claude/CLAUDE.md`, project `./CLAUDE.md` or `./.claude/CLAUDE.md`, and local `CLAUDE.local.md`. It claims the implementation concatenates the relevant texts rather than letting one file simply override all others. Its pictured `prependUserContext(messages, context)` extracts the `claudeMd` context and uses `createUserMessage`. It prepends content wrapped in `<project-instructions>` and environment-oriented `<system-reminder>` blocks.

The figure shows `isMeta: true` as display metadata. Hiding a message in the UI does not transform its protocol role or make it a security boundary. These file names and internals describe the supplied Claude Code illustration. They neither prescribe this repository's instruction hierarchy nor promote retrieved source text into developer instructions.

**Source: ATT-02 images 6–7, reverse-engineered example, not a verified current API.**

<a id="forum-microcompaction"></a>
**Light cleanup, cache timing and heavy compaction form different mechanisms.** The screenshot's effective window calculation, `getEffectiveContextWindowSize = WindowSize - MaxOutputLen`, reserves output capacity before applying a trigger such as `getAutoCompactThreshold`. `AUTOCOMPACT_BUFFER_TOKENS = 13_000` is the illustrated additional buffer. The retained lesson is that organization must still have room to run. None of these arithmetic names or constants defines Q2's route-specific policy.

The light-cleanup path illustrated by `microCompact.ts` and `maybeTimeBasedMicrocompact` works approximately as follows, limited to what is visible in the supplied figures:

1. Identify eligible tool calls/results using `COMPACTABLE_TOOLS`, illustrated by Read, Bash, Grep, Glob, WebSearch, WebFetch, Edit and Write.
2. Keep a recent eligible set. The visible code clamps `keepRecent` with `Math.max(1, config.keepRecent)` and selects recent IDs with `compactableIds.slice(-keepRecent)`.
3. Build the older eligible set to clear. Match result blocks to their calls by `tool_use_id`. Leave other message blocks alone. Skip already-cleared content.
4. Replace the selected `tool_result.content` body with a marker, illustrated by `[Old tool result content cleared]` / `TIME_BASED_MC_CLEARED_MESSAGE`. Preserve the call/result envelope rather than delete an arbitrary half of the exchange.
5. Account for removed body tokens, illustrated by `calculateToolResultTokens` and `tokensSaved`. Use the resulting input view for subsequent requests.

This is **observation masking**: the mechanism keeps the trajectory and result identity while omitting older observation bodies. It is not a semantic summary. It does not know whether an old header remains necessary or itself prove exact original retrieval. The PDF app must provide preservation and references separately before analogous release is safe.

`evaluateTimeBasedTrigger(messages, querySource)` and the visible `gapMinutes` calculation consider time since the last assistant activity. The essay's rationale is to avoid changing a still-reusable cached prefix immediately. It then considers cleanup after cache expiry would already reduce that benefit. This trades context pressure against possible reuse. The provider's actual cache rules and the next request's ability to fit still control usefulness. Waiting for an illustrated time gap cannot justify sending an oversized request.

The heavier `autoCompact.ts` / `compactConversation` path generates summary material in another model invocation. The figure shows an experimental `trySessionMemoryCompaction` path before fallback to a summary call. `querySource='compact'` distinguishes that call so it does not recursively trigger the same compaction process. A summary call needs its own sendable input and output room, consumes usage, can fail, and can omit meaning. The pictured reduction from roughly 85k to 25k is illustrative rather than a bound.

The discussion retained the ability to release retrievable material before broader history organization. It did not adopt this exact mandatory ladder, time policy or undocumented hook set.

**Source: ATT-02 images 7–9, comparisons in EVT-0185, EVT-0206, EVT-0214.**

<a id="p1-067"></a>
**P1-067 — ATT-02's Deep Agents examples and final cautions.** **Status: corrected/rejected where generalized.**

The essay shows `write_todos`, a plan held in agent state, filesystem state, read/write/edit tools, and middleware as a way to keep content outside the window. Its closing recommendations combine cache-friendly short-term input, notes/files/todos, long-term editable memory or retrieval, and progressively stronger cleanup. It says the harness should own context changes. That does not exclude model summaries or model judgment. The historical review checked that Deep Agents v0.7 made task planning opt-in. Thus, the screenshots' planning defaults were not a current universal requirement.

Saving in a state dictionary is also not by itself durable disk persistence.

**Sources: ATT-02 images 9–10, EVT-0183, EVT-0185, EVT-0360.**

<a id="forum-deepagents-state"></a>
**Plans and virtual files need actual persistence semantics.** The `write_todos` example uses guidance named `WRITE_TODOS_SYSTEM_PROMPT`, updates a todo list in state and returns the latest plan through a tool result. This makes recorded work available without relying on the model's unrecorded recollection. It does not prove that a completed checkbox represents source-accepted output. It also does not prove natural agent use or planning availability in every version.

The pictured `StateBackend.edit(file_path, old_string, new_string, replace_all=False)` operates on files represented in backend state. It checks that the path exists and uses `perform_string_replacement`. It prepares a file-state update using helpers such as `prepare_for_storage`, `update_file_data` and `_send_files_update`. The illustrated `EditResult` can report an error or occurrence count.

A virtual `file_path` is therefore not automatically an ordinary OS file written durably on disk. The configured backend/checkpointer determines persistence. Exact replacement also needs a defined match rule. Its occurrence count is an edit result, not a PDF fidelity check. These names explain the source example, not a selected document-edit API or permission to call framework internals.

**Source: ATT-02 images 9–10, correction in EVT-0185 and EVT-0360.**

## ATT-03: the first complete Python/StateGraph proposal

<a id="p1-068"></a>
**P1-068 — Useful layering, premature final verdict.** **Status: proposal/open (historical proposal).**

ATT-03 proposed three layers:

- OpenAI Python SDK `AsyncOpenAI` behind custom Responses and Chat Completions drivers.
- LangGraph `StateGraph` plus SQLite checkpointing for the turn loop and UI pause/resume.
- Domain evidence/context modules borrowing Deep Agents patterns without its coding tools.

Its table selected the API client, LangGraph, and domain code while dropping LangChain and Pi and using Deep Agents only as a reference. Clear communication/execution/domain responsibilities were useful, but “use/drop” was premature and did not prove least maintenance or reliability. The later final baseline resembles part of this proposal without adopting its fixed stages, policies, budgets, or overclaims.

**Sources: EVT-0298, EVT-0299, EVT-0312, EVT-0318, ATT-03, EVT-1166.**

<a id="p1-069"></a>
**P1-069 — Dual-protocol mapping was illustrative, not a canonical flattening rule.** **Status: corrected/rejected in part.**

ATT-03 proposed canonical turn/image/tool objects with drivers converting them to Responses `input_image` / `function_call_output` and Chat image blocks / paired tool messages. Keeping native protocol handling separate was useful. `model_extra` preserving extra response fields is unrelated to `max_retries=0`. The latter disables SDK retry ownership.

A universal `TurnReasoning` must not flatten ordinary text, structured reasoning items, encrypted/opaque items, or provider-specific `reasoning_content` into interchangeable data. Preserve native content, type, provenance, and adapter-specific replay requirements. The app cannot preserve internal reasoning that the service never delivered. It cannot join partial attempts into a subsequent reply.

**Sources: ATT-03, EVT-0318.**

**Why native structure matters.** Text that contains an image path is not a model image block. A tool result without its matching call identity is not an intact tool exchange. A provider's opaque reasoning item is not ordinary assistant prose for copying into an unrelated protocol. A common application envelope may identify these objects, but the adapter still needs their original kinds and applicable replay rules.

A universal reasoning object cannot recover fields that the model service never returned. These distinctions motivate preserving native response data and adapter responsibility, not exposing private reasoning or adopting ATT-03's proposed classes.

**Sources: ATT-03, EVT-0318.**

The [native payload examples](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#native-payload-examples) preserve the exact illustrative identifiers: `ModelTransport`, `ResponsesDriver`, `ChatCompletionsDriver`, `TurnInput`, `TurnOutput`, `ToolCall`, `ImageBlock`, `TurnReasoning`, `AsyncOpenAI`, `client.responses`, `client.chat.completions`, `input_image`, `image_url`, `function_call_output`, `call_id`, and `tool_call_id`. They explain the payload shapes and why preserving `model_extra` is independent of `max_retries=0`. This is the technical substance behind the correction, not a new class hierarchy.

<a id="p1-070"></a>
**P1-070 — The proposed graph schema embedded invalid policy assumptions.** **Status: corrected/rejected.**

The attachment's schema contained task source/output/pages/invariants, active pages, page status, evidence index, retry ledger, and `active_messages`. It also contained a fixed `current_stage` enum of inspect/OCR/draft/revise/done. Its four nodes were compile context, call model, execute MCP tools, and compact/release. It proposed image injection only for active pages, pointer replacement of older results, cleanup at save/batch boundaries or 75%, and a fixed three-attempt ledger. These details could exclude needed older headers, impose conversion order, treat saved as dispensable, or import an old trial budget.

The correction retained flexible current work and dependency state, pre-send capacity checks, per-route reserve, and normal tool calls. It did not fix an internal MCP transport or a stage enum.

**Sources: ATT-03, EVT-0312, EVT-0318.**

<a id="rejected-graph-schema"></a>
**Why the exact fields and nodes were not accepted as a recipe.** `TaskContract(pdf_path, output_dir, target_pages, invariants)` describes the task envelope in ATT-03. `target_pages` alone cannot describe every complete-section or subpage source scope. `WorkingState.current_stage` was a `Literal["inspect", "ocr_extract", "draft_md", "revise", "done"]`. Treating it as a required progression would prevent legitimate revisiting or skipping of methods.

`active_pages` can describe current focus. Excluding every image outside that set could remove page 10's saved header while page 11 still needs it. `page_status` values such as pending/extracted/saved/verified mix progress with source judgment unless the app distinguishes their scope and evidence. `evidence_index` supplies references. It is not proof of complete review.

The proposed nodes were `compile_context`, `call_model`, `execute_mcp_tools`, and `compact_and_release`. Their responsibility separation remains useful. The final graph need not have exactly these four nodes or force internal tools through `MCPClient`. It need not flush images/reasoning whenever a page is saved or input crosses 75%.

A `retry_ledger` counted by stage/round does not itself preserve the original whole-task attempts/time/turn limits across new stages and restart. Annotating `AgentState.active_messages` as “ephemeral” does not exempt it from checkpoint serialization. The [summary and checkpoint explanation](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#summary-and-checkpoint-components) explains this storage problem and the `MessagesState` / `add_messages` correction. The final baseline retains small graph orchestration with explicit request/batch/domain boundaries. The schema and node list remain rejected or adjustable proposal details.

**Sources: ATT-03, EVT-0318, EVT-1166.**

<a id="p1-071"></a>
**P1-071 — SQLite graph checkpoints do not atomically commit external files.** **Status: agreed direction.**

If a save succeeds before a graph checkpoint, node re-execution can repeat effects unless operation identity, versions, and receipts reconcile them. A checkpointer cannot make SQLite, Markdown, and image files one transaction. Naming `active_messages` “ephemeral” does not prevent checkpoint persistence. Storing huge base64 bodies in graph state can create storage/serialization cost. Persist references and versions. Load content for assembly where appropriate.

`MessagesState` is not simply append-only: its reducer can update by message ID. Those corrections explain why a small graph still needs domain persistence contracts.

**Sources: ATT-03, EVT-0318, EVT-1166.**

**Crash-boundary example.** A document-save operation can finish writing and registering its immutable version. The process can then stop before graph state records that the node completed. On restart, the graph may try the node again. The original operation identity and completion receipt let the document service recognize that completed effect. The service can then return its historical result instead of writing the same version again.

A file hash alone says that bytes match. It does not identify the completed requested operation. If a newer document head now exists, replaying the older receipt must not move that head backward. This is the reason for explicit reconciliation at the graph/document boundary. The exact finite recovery rules remain within the third open contract. This example does not claim support for every arbitrary crash.

**Sources: EVT-0318, EVT-1166.**

<a id="p1-072"></a>
**P1-072 — Tooling and runtime language cannot be decided by dismissal.** **Status: corrected/rejected.**

Pi's embeddable SDK refutes “external CLI only.” Existing Python PDF tools do not by themselves require the whole runtime to remain Python. TypeScript plus Python is a possible tradeoff. Deep Agents built-in files/todos may overlap domain tools, but customization is possible. Overlap is not proof of unavoidable conflict. `ChatOpenAI` limitations do not disqualify all model integrations or `create_agent`.

ATT-03's suggested `transport/`, `memory/`, `orchestration/`, and `ipc/` layout and stdio/JSON-RPC bridge are illustrative organizational choices, not selected package boundaries. Its invitation to generate code was source text, not implementation authorization.

**Sources: ATT-03, EVT-0318, EVT-0319.**

## ATT-05: product-first reconstruction and overclaims

<a id="p1-073"></a>
**P1-073 — Product-first criticism contained useful proposals and unsupported conclusions.** **Status: corrected/rejected in part.**

ATT-05 challenged the move toward Deep Agents as framework-first. It argued that independently saving full evidence and providing `read_evidence` would make general offloading redundant. It claimed that only a summary call, allegedly under 100 lines, would remain. It also claimed that a thin TypeScript/Pi runtime or retained Python controller would solve all context pain.

Useful proposals were evidence preservation when produced, easier incremental edits, reusable rejected candidates, and shared preview rendering. The review rejected these unsupported claims:

- Session/loop/persistence/events/summary-boundary/failure handling reduces to one tiny function.
- Deep Agents must be discarded.
- Porting a few hundred lines to TypeScript automatically retains old reliability.

The user allowed complete reconstruction. An attachment's preferred blueprint was not automatically an agreed implementation.

**Sources: EVT-0361, EVT-0362, EVT-0378, EVT-0382, ATT-05.**

<a id="p1-074"></a>
**P1-074 — Old cost numbers did not establish a universal cache policy.** **Status: corrected/rejected.**

ATT-05 attributed the old high cache reuse to strict append-only history. It rejected context editing using a more expensive selective branch and a checkpoint followed by a 796,420-token request. The response narrowed each inference:

- That selective strategy did not demonstrate benefit. The comparison did not test all selective strategies.
- Reading nine complete OCR objects after a checkpoint can erase savings. The evidence did not show that the checkpoint alone caused that choice.
- Large cache reuse does not prove that permanent full-history retention is best.

The 191,662-to-5,014-character projection did not establish a 90% reduction in useless material, equal-quality intake, or Nexus cost. Stable useful prefixes are worth preserving. The review rejected an 80% cache target and strict append-only mandate.

**Sources: ATT-05, EVT-0378, EVT-0382.**

<a id="p1-075"></a>
**P1-075 — Always-minimal intake would constrain legitimate evidence.** **Status: corrected/rejected.**

ATT-05 proposed a default compact semantic envelope containing text, anomaly warnings, and structure/size pointers, with coordinates and layout fetched only later. The response kept convenient concise representations and explicit omission metadata as options, while preserving full/raw/image access from the first call. Layout, words, character positions, style, and regions may resolve columns, figures, tables, or meaningful emphasis. Size alone cannot establish that they are redundant.

The app can manage an oversized saved result before it enters input. The earlier scenario never required flooding context before offloading. Preserving originals means preserving what the call actually computed, not running extra extraction/OCR/rendering unasked.

**Sources: ATT-05, EVT-0382.**

<a id="p1-076"></a>
**P1-076 — Diagnostics aid judgment but do not certify a page.** **Status: agreed direction.**

Examples in the attachments included transparent `GlyphLessFont`, low OCR confidence, embedded image counts, and suspected columns. Such warnings can guide investigation, but observed attributes, inferred risks, and uncertainty must remain distinct. No warning does not mean no problem. Font/opacity information should retain locations where meaningful differences occur. Pagewide counts alone cannot replace those locations. The app must not state that block/line extraction already determines true reading order.

**Sources: ATT-05, ATT-06, EVT-0382, EVT-0414.**

<a id="p1-077"></a>
**P1-077 — Incremental edits address actual friction.** **Status: agreed direction, contract details still open.**

The old contiguous-replace/full-map interface did not directly support pure insertion/append or local page-map changes. The proposed improvement included these capabilities:

- Add, insert, replace, and delete specified content.
- Merge local page-map patches into the full document.
- Identify an explicit `base_version`.
- Preserve complete candidates before validation.
- Return specific errors.
- Reuse exact content when only metadata changes.

The goal is to avoid asking the model to resend unchanged prose and a complete map. The app validates the merged full document. These capabilities do not make every historical API name or CRUD schema final. EVT-1166 narrows the V1 contract to exact complete-candidate references, insert/append, local map changes, preservation semantics, and commit success.

**Sources: ATT-05, EVT-0382, ATT-06, EVT-0414, EVT-1166.**

The older request named the replacement targets `remove_ids` and supplied a complete `content_updates` page mapping. The alternatives were named `append_blocks`, `insert_after_id`, `replace_ids`, `delete_ids`, and `patch_page_map`. `commit_candidate(candidate_id, ...)` illustrated applying a correction to already-retained content. These are historical names for distinct edit capabilities, not a frozen CRUD surface.

Appending new paragraphs should preserve the existing body. A local mapping patch should merge into and validate the full map. Candidate reuse should preserve every untouched body field exactly. Changing only mapping metadata cannot resolve a stale `base_version`. The [document edit guide](../design/DOCUMENT_ENGINE.md#edit-semantics) explains the retained behavior and open merge/omission semantics.

**Sources: ATT-05, ATT-06, EVT-0382, EVT-0414, EVT-1166.**

**Candidate-repair example.** Consider complete received prose with a page-map error. The document service should perform these steps:

1. Retain that exact prose.
2. Return a candidate reference and the specific map problem.
3. Accept a later correction that identifies the candidate and changes only the affected mapping.
4. Merge the mapping.
5. Validate the resulting whole document.

The prose should not need a second model generation merely to correct metadata. Insertion/append solves a related problem: adding new content should not require replacing and resending an unchanged surrounding range. These are behavioral examples. Exact request shapes and omission-versus-replacement semantics belong to the first open contract.

**Sources: EVT-0382, EVT-0414, EVT-1166.**

<a id="p1-078"></a>
**P1-078 — Candidate storage, committed versions, and quality differ.** **Status: agreed direction.**

A metadata rejection should preserve received useful candidate content and identify it so a later call can correct metadata without rewriting text. That does not prove the prose is perfect, publish a version, or establish content completeness. The attachment's “zero token waste” and “all failures can commit after a patch” were too strong. A missing field and a stale `base_version` are different: version conflict requires checking/merging rather than blindly patching metadata and overwriting newer work. Printed-page `unknown` is legitimate and should not force guessing merely to satisfy validation. The final consolidation requires preserving received original parameters before validation, while making automatic repair of incomplete JSON optional outside V1 necessities.

**Sources: ATT-05, ATT-06, EVT-0382, EVT-0414, EVT-1166.**

A stale base version changes the repair problem. A prepared candidate may use an older document while a newer version is already current. Metadata repair alone then cannot authorize replacing the newer work. The agent must inspect the conflict and choose an appropriate merge or renewed edit. Preserving a received malformed or incomplete call supplies useful evidence, but does not make its content a complete reusable candidate. The final V1 direction preserves the received parameters and supports complete-candidate reuse without requiring an automatic partial-JSON salvage engine.

**Sources: EVT-0414, EVT-1166.**

<a id="p1-079"></a>
**P1-079 — Deterministic ledgers cannot replace unrecorded understanding.** **Status: corrected/rejected.**

ATT-05 proposed a `WorkingLedger` with requirements, version, per-page progress, last two blocks, candidate references, and notes attached to save/revise. It argued chapter-boundary/high-water resets could deterministically inject this and eliminate nearly all summaries. It promised “100 times” accuracy, zero latency/cost, and no lost dependency. A ledger preserves recorded information, not unrecorded discoveries.

App facts differ from reasons for rejecting OCR, paragraph continuation, a provisional glyph interpretation, or remaining quality work. Two trailing blocks can miss an earlier definition or a multi-page table. Save-only notes miss exploration before saving. Existing notes can sometimes make an extra summary unnecessary, but optional summaries and independent notes remain useful.

**Sources: ATT-05, EVT-0378, EVT-0382.**

The proposed `working_ledger.json` separated app-maintained execution facts from agent-authored `active_notes` / `open_dependencies`. Its **Epoch Compaction** rebuilt input from requirements, a ledger snapshot, unfinished candidates and retained dependencies at a chapter boundary or high-water mark. Assembling those recorded fields is deterministic. Deciding what belongs in the notes is semantic work.

The agent might never record why a glyph was doubtful. A `project(history) -> request_messages` function cannot recover that private judgment merely by reinjecting version IDs and the last two blocks. Useful notes already recorded can reduce the need for another summary call. The final design therefore retains notes and optional model-assisted handoff without the attachment's universal no-summary, free, or zero-loss claims.

**Sources: ATT-05, EVT-0382, EVT-0414.**

<a id="p1-080"></a>
**P1-080 — Document conventions are working judgments, not automatic global facts.** **Status: agreed direction.**

The attachments correctly highlighted agent-discovered conventions:

- Heading hierarchy and physical/printed label relationships.
- Damaged OCR fonts, provisional glyph interpretations, and rejected extraction.
- Unresolved six-column table headers and unclosed paragraphs.

These are important continuation material, alongside unpublished candidate content. They need source and scope, because an apparent offset or convention may not apply to every page. Persisting judgments lets future work use them but does not certify them. The app should make them easy to record rather than automatically declare every observation globally correct.

**Sources: ATT-05, ATT-06, EVT-0382, EVT-0414.**

<a id="p1-081"></a>
**P1-081 — Autonomy does not exclude user intervention.** **Status: agreed direction.**

ATT-05 characterized mid-task user corrections as a chatbot scenario irrelevant to an automated converter. The response rejected that restriction. Low routine user handling means the user need not direct each page. The user can still narrow scope, correct a goal, pause, or stop. Continuation must respect currently effective requirements and their changes, not merely reinject the original prompt.

ATT-06 accepted this correction. The system still should not turn ordinary conversion into mandatory approval or repeated manual instructions.

**Sources: ATT-05, EVT-0382, ATT-06.**

<a id="p1-082"></a>
**P1-082 — A Node-led desktop topology was a proposal, not the final choice.** **Status: corrected/rejected (superseded topology).**

ATT-05 proposed Electron/TypeScript owning the harness, task/version ledger, Tesseract.js workers, and hidden preview capture. Python would supply stateless PyMuPDF/Pillow operators without a Python MCP/HTTP/runtime stack. The proposal aimed to avoid nested Python→Node OCR and a second Chromium, simplify packaging, and centralize publication. The response supported a clear runtime owner, suitable workers, and shared rendering, but did not require moving all control to TypeScript.

Electron itself is multiprocess. The UI/main should manage windows and lifecycle while long agent work runs separately. The later preferred runtime is a single Python control layer using a small StateGraph and SQLite.

**Sources: ATT-05, EVT-0382, EVT-1166.**

<a id="p1-083"></a>
**P1-083 — Workers may cache data without owning competing task state.** **Status: agreed direction.**

Python need not restart for every operation or be mathematically stateless. A persistent PDF worker may cache an open document handle, parsing, or fonts. Workers can create independent evidence files. One publication authority registers/commits document versions and reconciles them. That authority does not require one process to write every byte. Changing languages does not automatically prevent split state.

Neither cached handles nor a Node worker proves millisecond performance for all extraction/rendering, instant initialization, or zero packaging overhead.

**Sources: ATT-05, EVT-0382, ATT-06, EVT-0414.**

<a id="p1-084"></a>
**P1-084 — Framework transport is not necessarily an uncontrollable black box.** **Status: corrected/rejected.**

ATT-05 cited old header timeouts, 5xx errors, interrupted SSE, nonstandard fields, and successful-write/failed-projection reconciliation. It then asserted that Deep Agents necessarily nests four black boxes requiring monkey patches. The response retained the behavioral needs: one retry authority, complete attempt-local replies, preserved native images/reasoning, valid tool pairing, and receipts. It found no proof of unavoidable private patching.

Deep Agents accepts suitable model integrations rather than requiring one fixed `ChatOpenAI → OpenAI SDK` stack. A framework does not guarantee less adaptation. Old test counts preserve useful contracts. They neither forbid reconstruction nor certify a port. Exact old endpoints, model aliases, timeout values, and trial retry counts are not new defaults.

**Sources: ATT-05, EVT-0382.**

The attachment's concrete diagnostic vocabulary included a 180-second header `ReadTimeout`, HTTP 500/502/503, an SSE interruption after 36 frames, and the nonstandard `service_tier` field. These identify reported symptoms/metadata in a historical route. Frame count does not establish a complete reply. A header timeout does not establish remote cancellation. A returned tier field does not by itself prove upstream identity or billing.

The details support preserving actual native errors/metadata and separating transport, completion and accounting. They do not diagnose every error or establish a new timeout default.

**Sources: ATT-05, EVT-0382.**

## ATT-06: refinement, remaining risks, and useful mechanisms

<a id="p1-085"></a>
**P1-085 — The attachment explicitly accepted four previous corrections.** **Status: agreed direction.**

ATT-06 accepted four corrections:

- Old cache/projection numbers do not prove equal-quality savings or permanent append-only superiority.
- Last-two-block and save-only notes are insufficient.
- Original preservation should cover only actual requested computation.
- Users may change requirements during autonomous conversion.

It then proposed granularity-aware intake, piggybacked notes with a pre-compaction handshake, exact pinned content, and framework behavior checks. Acceptance of those corrections does not turn all subsequent proposed mechanisms or guarantees into settled contracts.

**Sources: EVT-0384, EVT-0385, ATT-06, EVT-0414.**

<a id="p1-086"></a>
**P1-086 — The “blind first read” explanation remained a hypothesis.** **Status: corrected/rejected.**

ATT-06 argued that an agent cannot choose fields before seeing a page. It therefore attributed the initial full inspect to a discovery dilemma and predicted that future calls would always choose full. The evidence establishes that `_select` was already available, but the private reason for not using it is unknown. A friendly representation/size catalog may improve discovery without requiring the agent to guess a JSON Pointer. It does not justify claiming a causal diagnosis, a fixed field set, or that fine-grained extraction is never useful on the first call.

**Sources: ATT-06, EVT-0412, EVT-0414.**

<a id="p1-087"></a>
**P1-087 — Layout granularity alone did not explain output size.** **Status: observed-v1.**

ATT-06 suggested default block/line layout would retain all essential relations while shrinking output to a few thousand characters, with words/chars only on demand. The historical check found that existing `get_text("dict")` already supplied blocks, lines, and spans: `layout` alone was 147,366 of the 191,662 characters, with `words` around 39,324. Removing word data therefore did not demonstrate the proposed size or complete fidelity. This observation motivates examining repeated representations and encoding, not reopening the closed audit or mandating a new extractor by itself.

**Sources: ATT-06, EVT-0400, EVT-0412, EVT-0414.**

<a id="p1-088"></a>
**P1-088 — Representation design can reduce duplication without hiding evidence.** **Status: proposal/open.**

The discussion suggested these improvements:

- Clear `text`, `layout`, `words`, `chars`, and image/region entry points.
- Avoidance of multiple full copies of text in one default reply.
- Shared style/font tables that spans reference.
- Retention of locations where styling or opacity differs.

Block/line structure does not establish natural reading order, and spans carry actual text and style. If words/chars remain uncomputed, describe how to obtain them. Do not invent exact saved sizes or pretend an evidence object already exists. These are representational options to apply where useful, with full detail still directly available.

**Sources: EVT-0414, ATT-06.** Historical references: [PyMuPDF reading order](https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-extract-text-in-natural-reading-order), [span structure](https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary).

ATT-06 called this a **Granularity-Aware Evidence Contract** and illustrated `inspect_pdf`, `ocr_pdf` and `render_region`. Its default `block_and_line` representation proposed full text, block/line bounding boxes, font/opacity diagnostics and discovery of words/chars. The correction concerns both computation and presentation. `_select` can choose fields from an existing result, while requesting an uncomputed granularity is a new extraction operation. A catalog can advertise that operation without inventing a stored result's ID or size.

Full first-call choices remain available. The name `block_and_line` did not establish either a sufficient field preset or a small representation.

**Sources: ATT-06, EVT-0414.**

<a id="p1-089"></a>
**P1-089 — Non-adoption evidence cannot establish a future note-taking failure.** **Status: corrected/rejected.**

ATT-06 combined B/C's non-use of optional context tools and P's non-use of scripts into a “0% adoption” argument. It predicted that agents would almost certainly neglect separate notes. Those jobs did not test the proposed notes mechanism or establish that causal conclusion. Piggybacked `working_notes` on normal save/revise/stage calls may lower friction, but an independent note-update path is still useful during exploration before a draft. Notes should survive even if associated page-map metadata fails validation. No mandatory per-call note form or fixed frequency follows.

**Sources: ATT-06, EVT-0414.**

The illustrative note categories were `conventions`, `open_questions` and `unresolved_links`. Examples were a scoped heading rule, an uncertain glyph/unit, and a continuing header/paragraph relationship. A `stage_draft` or save operation could carry those notes, but making that the only update route would miss discoveries made before any draft. These fields are agent judgments with provenance, not automatic global facts. They also need a clear retention boundary when validation rejects the accompanying document metadata.

**Sources: ATT-06, EVT-0414.**

<a id="p1-090"></a>
**P1-090 — A pre-compaction handoff is useful but fallible.** **Status: agreed direction, exact mechanism open.**

ATT-06 suggested a dedicated turn asking the current agent for unsaved page/layout conventions, doubtful glyph/OCR judgments, unfinished paragraphs/headers, and exact evidence/block references before switching. This agrees with agent meaning judgment plus app capacity intervention. The turn must begin before input and output space are exhausted and at a safe tool-turn boundary.

On failure, retain originals and useful work. Reassemble where feasible, or stop under the persistent budget. Do not endlessly resend one oversized context. The same agent can still omit information. Thus, handoff offers an opportunity for preservation, not a lossless-memory guarantee or a reason to delete needed recent material.

**Sources: ATT-06, EVT-0400, EVT-0414, EVT-1166.**

<a id="p1-091"></a>
**P1-091 — Exact working-set retention avoids paraphrase, not all error.** **Status: agreed direction, implementation form optional.**

ATT-06 proposed `pinned_block_ids` and `pinned_evidence_ids` for old definitions, a table's exact header, unfinished content, or image pixels. Carrying the exact original is preferable to paraphrasing details that must remain literal. The correction requires versioned references or an evidence range, a reason, dependency state, a release condition, and input-cost awareness. References to changed/deleted content require an explicit update or stale mark.

Overlarge retained sets need adjusted work scope or segmented retrieval, not silent shrinking. A last-N heuristic is only a convenience, not proof of dependency. Exact retention guarantees identity of selected material, not correct selection, understanding, or faithful future output.

**Sources: ATT-06, EVT-0400, EVT-0414.**

**Stale-retention example.** EVT-0414 asks what should happen after correction of retained table header `blk_089`. An unversioned block ID cannot tell the next request whether it is using the pre-correction or corrected header. The retention record therefore needs to identify the intended version or exact evidence range and make a change or invalidation visible. Retention can end after reconstruction and checking of the cross-page table. The original remains recoverable.

If all retained items no longer fit, the agent must narrow or segment the next work. The app must not silently shorten an item it promised to keep exact. This illustrates version and capacity semantics, not a compulsory pinning subsystem or fixed record schema.

**Sources: EVT-0414, EVT-1166.**

<a id="p1-092"></a>
**P1-092 — Context transactions have mechanical and semantic limits.** **Status: agreed direction.**

The app can check a candidate context for object/version existence, hashes, registered references, preserved user-revision records, native protocol validity, and capacity. Those checks cannot prove that the record includes every important dependency, that interpretations of requirements are correct, or that fidelity will persist. EVT-0414 proposed recording requirement/artifact/notes revisions and evidence references, rechecking before commit, and persisting the candidate before pointer activation.

If requirements or artifacts change during organization, reassemble the affected parts. Under the final simplified contract, failed organization preserves originals. The contract permits intermediate reduction. The exact manifest/schema machinery remains proportionate implementation work.

**Sources: ATT-06, EVT-0414, EVT-1166.**

<a id="early-continuation-vocabulary"></a>
**Handshake, pinned set and candidate view describe different operations.** ATT-06 called the early request for continuation material a **Pre-Compaction Handshake**. It gives the working agent a sendable turn before a view change. The agent can record useful conventions, uncertain OCR/glyph decisions, unresolved paragraphs or headers, and exact references. Asking only after the window is exhausted defeats the mechanism, because the request and answer also need room.

A complete tool batch is the safe boundary. The handshake does not make partial native calls executable or guarantee the agent recalls every dependency.

Its **Pinned Working Set**, including `pinned_block_ids` / `pinned_evidence_ids`, carries selected exact content rather than paraphrasing it. The correction adds version/range identity, purpose, dependency/release condition and capacity cost. An exact old header can still be the wrong header after an edit. The label “pinned” does not mean permanently current.

Its **CandidateContext** denotes a proposed model-input view for assembly and checking before activation. The source suggested the basis `requirements_revision + artifact_version + notes_revision + evidence_refs`. A user amendment, version change or note update may occur while organization runs. In that case, recheck the basis. Rebuild the affected view rather than silently activate stale material.

That dry run can check reference resolution and native structure. It cannot prove preservation of all significant meaning. Failure leaves the previous usable view and all originals available. The later consolidation permits progressive reduction and does not require every intermediate step to satisfy the final normal-request target. These early names do not mandate an external manifest engine alongside graph-owned policy, a second writer, a fixed threshold, or a final Q2 schema. [Handoff and working notes](../design/CONTEXT_AND_EVIDENCE.md#handoff-and-working-notes) and [rolling compaction](../design/CONTEXT_AND_EVIDENCE.md#rolling-compaction) explain the full current mechanism.

**Sources: ATT-06, EVT-0414, EVT-1166.**

<a id="p1-093"></a>
**P1-093 — Durable indices need not all be in every request.** **Status: agreed direction.**

ATT-06 proposed injecting the full page map, candidate list, evidence index, notes, and pinned material. The response cautioned that those records themselves can grow beyond useful input. Keep the complete records durably accessible. Include relevant items, progress context, unresolved work, precise references, and query routes in active input. This also applies to saved drafts and the latest artifact. Durable authority is separate from content that every model request must repeat.

The final consolidation expressly permits portions of current versions or unfinished candidates to leave active input while exact originals remain retrievable.

**Sources: ATT-06, EVT-0414, EVT-1166.**

<a id="p1-094"></a>
**P1-094 — Artifact state and review evidence are separate dimensions.** **Status: agreed direction.**

ATT-06's one-way `CandidateStaged → VersionPublished → SourceVerified → export` diagram conflated storage with content judgment. Store candidate and committed immutable version state separately from review evidence. Record the reviewed source/range/content, its version, and remaining uncertainty. Reopen success proves readability. Preview success proves that a preview exists. Neither establishes full-source acceptance.

A local table review does not cover an entire section. Changes to headers, page mappings, or images can affect prior review applicability. Draft partial output should still be exportable with clear labeling. No compulsory review count, approval gate, or permanent global “verified” flag follows.

**Sources: ATT-06, EVT-0400, EVT-0414, EVT-1166.**

A source check should therefore state its scope rather than become a permanent badge on the document. For example, a reviewer checked the header and values of a specified table on a specified saved version. Reopening that version demonstrates access to its saved content. Obtaining a preview demonstrates that rendering succeeded. Inspecting the preview may support a reading-form judgment, while comparing the relevant source supports fidelity.

These facts can coexist without certifying the rest of the chapter. A later edit can change which earlier checks still apply. This separation permits export of an explicitly labeled partial draft while useful work continues.

**Sources: EVT-0414, EVT-1166.**

<a id="p1-095"></a>
**P1-095 — Same-version preview is the outcome. One screenshot method is not.** **Status: agreed direction.**

Shared UI/agent rendering can reduce divergence and duplicate browser resources. Electron `capturePage()` and DOM/block-based CDP capture were useful options. Target block IDs or source-page mappings can locate a table or figure. The outcome still depends on the same version, HTML/CSS, font resources, viewport, zoom, asset readiness, and coordinate interpretation. Visible-area limits, clipping containers, huge blocks, and font/image loading may require bounded region capture.

Do not promise that one screenshot captures all content merely because the app shares Chromium. Do not promise byte-identical appearance on that basis. Preview pixels assess reading output. Exported source images retain their own quality/provenance.

**Sources: ATT-05, EVT-0382, ATT-06, EVT-0414.** Historical references: [Electron capturePage](https://www.electronjs.org/docs/latest/api/web-contents#contentscapturepagerect-opts), [CDP protocol](https://github.com/ChromeDevTools/devtools-protocol/blob/master/json/browser_protocol.json).

The concrete proposed `view_preview` sequence used `BrowserWindow` / `webContents.capturePage()`, then `getBoundingClientRect()` with CDP `Page.captureScreenshot`, `clip`, and `captureBeyondViewport` for targeted regions identified by `target_block_ids` or `pdf_pages`. The [capture and worker explanation](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#capture-and-worker-mechanics) explains coordinate/viewport/resource limits and why a cached `fitz.Document` can avoid repeated parsing without making OCR or all rendering instantaneous. These API names preserve the engineering discussion while leaving advanced capture and exact worker placement as implementation choices.

<a id="p1-096"></a>
**P1-096 — Proposed framework touchstones test behavior, not one lock layout.** **Status: corrected/rejected in part.**

ATT-06 proposed four checks:

- Preservation of images/reasoning under both protocols.
- Candidate context validation and rollback.
- Persistent retry/stream isolation with receipt reconciliation.
- Candidate retention/local mapping merge.

Those behaviors are useful integration boundaries. Requiring the framework and tool layer to share one document lock is not itself a product requirement. The agent plans, while the runtime owns model/tool lifecycle. The document service owns evidence/candidates/versions/receipts. The context module owns assembly/capacity, and the adapter owns wire differences.

A normal tool call can enter a short document transaction. Model inference, OCR, and an entire turn should remain outside that lock.

**Sources: ATT-06, EVT-0414.**

The attachment called the proposed shared lock **Document Transaction Lock**. Its useful purpose is a short consistency boundary around validation/conditional publication in the document service. Keeping that lock across a network call or long OCR operation would unnecessarily couple document access to unbounded external work. Pi, Deep Agents and LangGraph do not need to possess the same lock object to call a service with that contract. This is a rejected coupling requirement with a retained publication responsibility, not a new lock implementation.

**Sources: ATT-06, EVT-0414.**

<a id="p1-097"></a>
**P1-097 — Mechanism proposals did not complete design or authorize implementation.** **Status: corrected/rejected.**

ATT-06 declared disagreements fully converged and offered precise JSON schemas or immediate framework tests. EVT-0414 accepted the useful direction—layered evidence, early handoff, versioned exact working material, and candidate reuse—but still identified capacity, stale-version, semantic, and quality-state behavior to resolve. It retained optional summaries and independent note updates, and suggested examining those boundary scenarios before freezing an oversized schema. Later EVT-1148/1166 expressly stopped round-by-round expansion: the residual work is three bounded contracts, not indefinite discovery of more mechanisms.

**Sources: ATT-06, EVT-0414, EVT-1148, EVT-1166.**

## Controlling consolidation and how to use this reference

<a id="p1-098"></a>
**P1-098 — Final architecture responsibilities supersede framework ranking.** **Status: agreed direction.**

The controlling final consolidation prefers a small LangGraph `StateGraph` plus SQLite under one Python control layer. The agent chooses methods freely. One Nexus request service covers normal reasoning and organization with persistent budgets/cancellation, native protocols, and frozen requests. It does not rely on native compaction, remote result retrieval, or remote cancellation.

The document/evidence core preserves source, evidence, received candidates, and immutable versions with precise reads, local edits, previews, and specified-version export. Context keeps evidence use separate from history organization. Recovery uses original calls and historical receipts. It does not regenerate saved content, reset budgets, duplicate commits, or regress the head. Execution stop, content-completion claims, and export consistency remain distinct. This is design agreement, not an implemented/proven product.

**Sources: EVT-1148, EVT-1166.**

<a id="p1-099"></a>
**P1-099 — The first remaining contract is edits and candidate references.** **Status: proposal/open (V1 contract).**

The final observed trigger was a complete candidate that failed page-map validation. A later generation introduced a wording regression. This supported exact reuse, not a proven compaction cause. The recommended V1 tradeoff includes these choices:

- Complete-candidate references and insertion/append.
- Local page-map changes merged and then validated against the complete document.
- Immutable version files as body authority.
- SQLite as registration/pointers/receipts rather than a separately mutable duplicate body.

Preserve incomplete calls. Automatic block salvage is not necessary for V1. Closure means specifying original identity, updated fields, untouched-field preservation, and successful commit. Three cases must be intelligible: page-map-only repair, insertion, and reuse of a rejected candidate without rewriting.

**Sources: EVT-1166.**

<a id="p1-100"></a>
**P1-100 — The second remaining contract is capacity and handoff.** **Status: proposal/open (V1 contract).**

The final evidence showed large inspect/OCR intake and an existing checkpoint that reduced input and retrieved earlier evidence. It did not prove universal savings or lossless continuation. Overflow after release and a delta-summary anchor losing information were hypotheses, not observed project failures.

The recommended tradeoff uses configurable route capacity/output reserve over the whole request. It releases persisted material not currently needed, then organizes older history. References can replace parts of the latest output and unfinished candidates in input. V1 uses a self-sufficient handoff, not a delta-only summary.

Reduction can be progressive. Normal requests must fit the final capacity, originals survive failure, and the runtime stops explicitly when the budget ends. The contract specifies no fixed recent K, required replacement draft, or universal percentage. It does not promise that two or three passes always suffice.

**Sources: EVT-1166.**

<a id="p1-101"></a>
**P1-101 — The third remaining contract is persistence, recovery, and stopping.** **Status: proposal/open (V1 contract).**

The discussion observed saved-work continuation and injected R1/R2 failures. It did not observe arbitrary crashes or natural prolonged outages. Tool commit before graph checkpoint and replay of an old receipt after head advancement are boundary scenarios requiring finite rules. They do not justify a general distributed system.

The recommended design keeps these boundaries:

- One active task writer.
- Unique authority for requests/tool-batch progress/versions/receipts.
- Frozen input for resuming the same request.
- Newly assembled input only after a completed tool-result batch.

Completed operations return their historical receipt. Unreconciled local effects stop with preserved work. A real user question waits for an answer. Saved versions can export independently and partial output stays draft. Automatic reminders and packaging on every exit are not V1 prerequisites. Closure specifies behavior at request-saved, reply-accepted, tool-committed, and graph-recorded boundaries.

**Sources: EVT-1166.**

<a id="p1-102"></a>
**P1-102 — Reopening is tied to a real contract blocker.** **Status: agreed direction.**

Framework names, module counts, table counts, old trial reserves, whole-book/provider matrices, and hypothetical optimization ideas are not independent current tasks. The architecture contracts must be consistent and have clear ownership. Implementation then receives proportionate offline checks and an authorized PDF or full-section delivery. Independent desktop UI/backend integration and Windows packaging remain required if an installable product is the intended output. They do not reopen context architecture.

Revisit the corresponding design only when implementation or actual delivery exposes a blocker that would violate a settled contract. This reference preserves reasons and discarded possibilities. Thus, the new repo can remain traceable without importing old current-state documents or closed jobs as instructions.

**Sources: EVT-1148, EVT-1166.**

## Source routing

Use the repository-local [discussion-source archive](sources/INDEX.md) for readable event text, attachment text, and forum pages/images. [SOURCE_INDEX.md](SOURCE_INDEX.md) and the public `source-inventory.json` describe exact `EVT` and `ATT` identities and provenance. Every substantive point has an explicit `p1-001` through `p1-102` anchor. The explanations and worked examples above carry the useful rationale. Reading the original sources is optional unless a reader needs exact wording or additional source detail. Understanding this reference requires no old checkout, external export folder, or private review scratch.

Each substantive point covers the repeated commentary that previews it, without reproducing that commentary as another decision. EVT-0258 has an empty final-answer body and adds no substantive claim. The adjacent reference documents preserve the broader later discussion. This reference repeats only its final controlling reset to distinguish historical options from active requirements.


<a id="supplemental-first-response"></a>
## Separately recovered first architecture response

ATT-31 preserves lines 109–309 of the separately supplied `conversation 2.md`. The excerpt contains 8,631 characters, including its `response:` label. ATT-04 instead matches EVT-0349 after surrounding whitespace removal. That duplication establishes which text the exported attachment held. It does not establish the clipboard's cause or every message another assistant received.

The supplement supplies an earlier critique of the Pi-first proposal. It is not an omitted adopted decision. The final Python `StateGraph` baseline still controls. Its detailed proposals and qualifications are preserved below.

### Proposed ownership and the reason for it

The response proposed this alternative arrangement:

```text
Electron UI / preview
        |
Node host: Pi SDK + session / operation / version ledger
        |-- Nexus adapter: stream assembly and bounded retries
        |-- PDF context extension: read structured work state
        |-- Tesseract.js workers
        |-- Electron BrowserWindow / webContents.capturePage()
        |-- Stateless Python operators: PyMuPDF + Pillow
        `-- Store: Node owns state, versions and evidence registration
```

The proposed Python operators returned extracted text, coordinates, native images or rendered files with metadata. They held no job state or version lock. Node would own `save`, `revise`, `reopen`, export, validation and state registration. Node would validate Markdown/JSON, generate HTML with an nh3-equivalent sanitizer and build ZIP packages. The proposal also moved OCR into Node and reused Electron for preview.

The motivation was to avoid conflicting store owners and duplicated state schemas across runtimes. One process does not itself guarantee correct persistence or recovery. The diagram still allowed Python to write output files. File creation and authoritative state registration therefore needed distinct ownership. Claimed reductions in package size, failure rate and maintenance cost were predictions, not measured results.

The response ranked Pi first, LangGraph second and Deep Agents third. It asserted that overriding middleware always cost more than building a thin graph. That universal ranking was not established. The [framework history](../design/INTEGRATION_AND_MODEL_BOUNDARY.md#framework-choice-and-history) explains the later responsibility-based choice.

### Intake, cache and working-ledger proposals

The response connected large first reads, later evidence release and prompt-cache cost. It proposed small default returns and batched projection at capacity or saved-chapter boundaries. It also cited historical large-payload and cache measurements. Those observations did not isolate a universally superior context policy or prove lower cost at equal fidelity.

The retained boundary allows precise first-call selection and full evidence access. It does not mandate summary-first intake, permanent append-only history or one chapter-based release schedule. [Cache tradeoffs](../design/CONTEXT_AND_EVIDENCE.md#prompt-cache-and-cost) include retrieval cost, request timing, capacity and source fidelity.

The proposed `WorkingLedger` held effective requirements, saved versions, page coverage, pending candidates and open cross-page dependencies. It proposed updates through `save` / `revise` or a separate state tool. Deterministic code would prepend that ledger at every compaction, outside model-selected summary retention. That was the proposed mechanism, not a guarantee of semantic correctness. Its example was:

```json
{
  "type": "continued_table",
  "from_pdf_page": 14,
  "header_columns": ["..."],
  "evidence_ref": "..."
}
```

The original sketch used `header_columns: [...]` as pseudocode. The quoted form above uses a placeholder string for valid JSON. The response placed this optional record in `open_dependencies`. It also named `pending_candidate_ref`. It did not use the later audit's `from_page`, `table_continuation` or `header_ref` fields in this passage.

These names illustrate semantic dependencies, not a final schema. The response's claim that deterministic injection makes compaction fully reliable was too strong. The app can preserve recorded facts and references. The agent must still interpret the source and record useful unresolved meaning. A structured field alone cannot establish completeness or prevent an incorrect dependency assessment.

The response also proposed `append_blocks`, `patch_blocks` and partial page-map updates to avoid resending a complete map for every local edit. The retained design supports useful local changes with whole-document consistency checks. [Q1](../OPEN_QUESTIONS.md#q1-document-update-and-candidate-reference-contract) still owns exact update and reference semantics.

### Five proposed Pi proof-of-concept checks

The original response proposed five checks before adopting Pi. Their scenarios remain useful historical comparison ideas:

| Proposed check | Scenario and retained limit |
| --- | --- |
| Nexus protocol compatibility | Exercise Chat Completions and Responses with images, tool calls, `service_tier` and custom reasoning fields. A configured route does not imply full protocol compatibility. |
| Interruption and recovery | Use a 90-second fault interval and an interrupted SSE tool-argument stream. Check partial-call exclusion, bounded replay and reconciliation of committed effects. |
| Projection and cache | Compare reported `cached_tokens` before and after `context_edit`. Cache counts alone do not establish price-weighted savings or equal-quality delivery. |
| Exact retrieval | Release an image or OCR result, then compare the native PNG SHA-256 or retrieve a selected JSON Pointer field. Representation and source identity must remain explicit. |
| Compaction continuity | Combine a table spanning pages 14–15 with a rejected `revise` candidate. Check retained requirements, table meaning and exact candidate reuse after organization. |

The second item described a proposed fault scenario. It was not a precise description of every historical relay injection mode. The response's loopback URL was an example, not a production endpoint or current configuration.

These checks were proposals, not completed validation, fresh permission for provider calls or additional first-version prerequisites. The final consolidation reduced open work to Q1–Q3. The response's closing Node-versus-Python ownership question was later superseded by the preferred Python controller arrangement.

**Sources:** ATT-31, ATT-04, EVT-0349, EVT-0382, EVT-0414, EVT-1148 and EVT-1166.
