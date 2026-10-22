# Decisions and rationale

This is the effective rebuild decision record. Detailed proposals, evidence limitations and correction chains live under [reference](reference/SOURCE_INDEX.md). Status distinguishes requirements and preferred design from open details and unimplemented behavior.

| Decision | Status | Rationale / implication | Source |
| --- | --- | --- | --- |
| Deliver complete source-faithful reusable Markdown/images with little handling | Agreed outcome | Optimize the user's complete conversion, not tool counts or framework adoption | EVT-0001, EVT-1166 |
| Keep the agent autonomous over conversion methods | Agreed constraint | Different PDF/text/image structures need different methods; app owns reliable tools | EVT-0188–0191, EVT-1166 |
| Use Nexus subscription access and portable context handling | Agreed constraint | Direct official API features do not establish the user's subscription route; other models must remain possible | EVT-0128–0137 |
| Separate evidence retrieval/retention from history compaction | Agreed design | Retrieval is reversible against originals; summaries are semantic and potentially lossy | EVT-0137, EVT-0188–0191, EVT-1166 |
| Combine agent relevance judgment with app capacity enforcement | Agreed design | Pure model initiative can miss overflow; rigid eviction can remove needed evidence | EVT-0189–0191, EVT-1166 |
| Preserve originals/useful work before context release or validation rejection | Agreed constraint | Saved correct content should be reusable without another generation | EVT-0855, EVT-0914, EVT-1166 |
| Small Python StateGraph, shared Nexus/dispatcher, document/evidence core | Preferred reconstruction baseline | Reuse orchestration primitives while keeping native protocol and domain contracts explicit | EVT-0968, EVT-1068, EVT-1107, EVT-1166 |
| SQLite metadata with external immutable content | Preferred persistence baseline | Short authoritative metadata commits and operation receipts without duplicate mutable body authority | EVT-1040, EVT-1068, EVT-1166 |
| Keep small context policy in graph state with one settlement writer | Retained simplification | External request budgets/document effects remain durable; unnecessary parallel policy-version/activation tables are removed | EVT-0872, EVT-0878 |
| One active writer per task; exact batch/operation replay | First-version recommendation | Avoid unnecessary concurrent-policy merge/branch infrastructure while protecting effects | EVT-1166 |
| Exact complete-candidate reuse and insertion/metadata edits first | First-version recommendation; contract details open | Addresses observed regeneration and full-map friction | EVT-1166; Q1 |
| Self-sufficient handoff; incremental capacity reduction | First-version recommendation; contract details open | Avoid dangling delta anchors and all-or-nothing compaction deadlock | EVT-1107, EVT-1147, EVT-1166; Q2 |
| Shared durable budgets/cancellation for normal and summary calls | Agreed execution boundary | Context work must not bypass recovery, spend limits or explicit stop | EVT-1040, EVT-1107, EVT-1166; Q3 |
| Explicit immutable-version export independent of model budget | Agreed delivery boundary | Useful saved work remains deliverable after inference stops | EVT-1107, EVT-1166 |
| Backward compatibility unnecessary; reconstruction allowed | Explicit user choice | Do not preserve old APIs/run formats merely for migration compatibility | EVT-0240, EVT-0319 and repeated attachment-review requests |
| New independent repository; old repository unchanged | Explicit user choice | Preserve the rebuild knowledge while allowing a clean implementation | LIVE-01–LIVE-05 |
| Detailed reference record with a small effective entry point | Explicit user choice | Preserve all substantive reasoning without giving obsolete guidance authority | LIVE-02–LIVE-04 |

## Consequential alternatives and corrections

The repository is a self-contained technical handoff (LIVE-06/07). [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md) and its module guides explain the development details directly, including mechanisms, examples and limits. The local source bundle supports audit; neither a source ID nor a transcript replaces a technical explanation. No separate old checkout/export is required, and old instructions remain inert.

- A filesystem-only custom context manager was an early proposal. It is superseded by the preferred SQLite/StateGraph direction, not a permanent no-database rule.
- Pi-first and LangChain `create_agent`-first rankings were interim judgments. Claims about least modification were withdrawn where the comparison omitted competing mechanisms. No framework eliminates document/evidence/context-domain work.
- A dynamic agent loop is compatible with a graph. Forum claims that LangGraph inherently prevents autonomy, that modern LangChain only provides static chains, or that feedback-driven action is necessarily "open loop" were corrected. Popularity and a maintained framework do not prove fit.
- Deep Agents offloading and summaries are reusable mechanisms, not a substitute for exact native-image/structured evidence, immutable documents and receipts. LangMem is not the entire runtime. A custom harness offers control with continuing maintenance cost.
- Dense tuples, fixed field lists, OCR-confidence/style thresholds and semantic dependency graphs were not adopted as universal conversion rules. Discoverability and source-led correctness govern representation choices.
- Timestamps, maximum policy revision, unqualified content hashes and input-view digests cannot each substitute for causal effect identity, merge rules or source coverage.
- All-exit auto-packaging, one-shot reminders, malformed-JSON salvage and fixed module/table counts are not required for first delivery. Their rationale and limitations remain preserved.

## Reopening policy

Only the three contracts in OPEN_QUESTIONS remain first-version design blockers. A framework comparison, hypothetical failure mode or historical unverified capability does not automatically create a task. Preserve useful observations; reopen the relevant decision when actual implementation/delivery evidence or the user changes its premise.

No application has been built or tested in this repository. Historical facts that motivate a decision remain observations of their original scope; they are not rebuild verification or inherited permission to run experiments.
