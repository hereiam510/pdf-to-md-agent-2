# Current state

Updated 2026-10-23, Asia/Hong_Kong. This describes the new repository only; it is not standing permission for provider calls or an application-readiness claim.

## Delivered scope

An independent local Git repository holds newly written rebuild requirements, responsibilities, contracts, decisions and detailed technical explanations. The original project remains a separate read-only source; its old status, defaults, test results and closed-work permissions are not adopted as this project's state.

[DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md) is the development entry point. Its four module guides explain integration/native model boundaries, context/evidence management, the document engine, and execution/delivery. They include data/state ownership, interface semantics, sequences, concrete examples, failure handling, rationale, historical corrections and open choices. Reading the original conversation is unnecessary to understand the development design.

The detailed reference records preserve the discussion's narrower alternatives and findings. [DEVELOPMENT_COVERAGE](reference/DEVELOPMENT_COVERAGE.json) maps every retained point to its technical explanation or explicitly historical/scope reference. The source/point ledgers retain provenance and decision status; mappings are navigation aids, not a substitute for substantive explanations.

The user's subsequent technical-detail concern led to a source-first review of the synthesis at `e243431`, using direct conversation text and attachments independently of the existing point inventory. It found that some correct high-level explanations had dropped exact technical vocabulary, framework call ordering, field relationships and illustrative failure cases. Those details are restored in the module/reference guides with their original status. [TECHNICAL_TERMS](TECHNICAL_TERMS.md) makes original names discoverable; [TECHNICAL_DETAIL_REVIEW](reference/TECHNICAL_DETAIL_REVIEW.md) explains specific deficiencies and repairs rather than claiming that matching counts proves completeness.

All 207 visible discussion messages, the inherited product handoff, all 30 attachments, 24 substantive forum figures and selected continuing source excerpts are [bundled locally](reference/sources/INDEX.md). Exact events and attachments retain their bytes; forum HTML is inert text with offline reading views. The original export remains untouched, but is no longer needed for development or cited-source lookup. Historical paths inside quotations are provenance, not required checkout locations.

## Implementation status

No app runtime, desktop UI, installer, dependency lock, migrated legacy code or provider configuration is implemented here. No PDF conversion, Nexus/provider generation, capability probe or benchmark was run for this documentation task. The two standard-library Python utilities check documentation and read preserved local sources; they are not the app implementation.

The preferred route remains a small Python LangGraph StateGraph, shared Nexus request service/tool dispatcher, and document/evidence core using SQLite metadata and immutable files. The three specific contracts in [OPEN_QUESTIONS](OPEN_QUESTIONS.md) remain open. Illustrative structures in the detailed guides do not silently choose final APIs, field names, thresholds or dependency versions. Historical framework rankings are not competing current plans.

No remote or release was created. This work preserves knowledge and makes it usable for development; it does not begin app implementation or reopen general network design.

## Review and verification

The initial review divided the complete exported discussion/attachments among three subagents and independently checked source coverage and effective-owner consistency. The subsequent self-containment work expanded the terse records, added module-oriented technical explanations, and used source-aware subagent review to find missing mechanics and cross-guide contradictions. Root integration reconciles owners, navigation, local provenance and checks. [PRESERVATION_AUDIT](reference/PRESERVATION_AUDIT.md) records the actual reviewed scope, results and limits.

The latest review rotated source areas between the three reviewers. They extracted technical details from original messages/attachments before assessing existing prose, including names and counterexamples hidden by broad point grouping. Direct chat retrieval returned actual message text: 205 overlapping discussion messages exactly matched the locally preserved source bodies. The two separate export-branch administrative messages were not returned, and the known empty message remains empty. No new source content or final API was invented to fill a gap.

A working Python 3.9+ interpreter is the only dependency of the documentation utilities. The current portable check uses a standalone bundled Python 3.12.14 interpreter outside both repositories; the initial review used an existing Python 3.13.16 interpreter read-only with bytecode writing disabled. No dependency installation or global settings change is required.

Document/hash/detail-coverage checks establish structural consistency and local availability, not runtime correctness or mathematical semantic completeness. Missing original screenshot text or an empty saved message is disclosed rather than invented. The original project's results remain historical observations, not acceptance of this unimplemented application.

## Next work

The next implementation-planning task should settle document update/reference semantics, capacity/handoff transitions and persistence/recovery/stop boundaries using their stated closure conditions. The detailed guides provide the mechanisms, tradeoffs and cases needed to do that without a chat archive. Preserve autonomy and full source access.

A useful first authorized implementation increment connects a real source/scope to candidate preservation, saving/reopening, basic capacity handling and explicit-version export. Advanced visual helpers, malformed-call salvage, generalized branches and cache tuning are not prerequisites. Reopen other design only for a concrete contract-breaking implementation/delivery issue or changed human requirement. App implementation and live verification require a subsequent human task.
