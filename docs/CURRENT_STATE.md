# Current state

Recorded 2026-10-22, Asia/Hong_Kong. This describes this new repository only. It is not standing permission for new provider calls or an implementation claim.

## Delivered scope

An independent local Git repository named `pdf-to-md-agent-2` now holds a freshly written rebuild design baseline and detailed, source-linked discussion records. The original project is a separate read-only source. Its old active documents, run ledgers, test results and closed-work permissions have not been adopted as this project's state.

The effective owners cover product requirements, architectural responsibilities, contracts, decisions and three first-version open questions. The reference layer preserves detailed reasoning, corrected/rejected ideas, examples, observations, hypotheses and deferred options. An exact source inventory and point/source coverage ledgers connect those records to the supplied export and subsequent human scoping decisions.

## Implementation status

There is no app runtime, desktop UI, installer, selected dependency lock, migrated legacy code or configured provider in this repository. No PDF conversion, Nexus/provider generation, capability probe or new benchmark was run for this documentation task. Codex agents assisted with the documentation and review. The two standard-library Python utilities check documentation and resolve preserved sources; they are not the agent implementation.

The preferred rebuild route is a small Python LangGraph StateGraph, shared Nexus request service/tool dispatcher, and document/evidence core with SQLite metadata and immutable files. These responsibilities are settled enough to guide work; their three executable contracts still need the specific decisions in [OPEN_QUESTIONS](OPEN_QUESTIONS.md). Historical framework rankings and pseudocode are not competing current plans.

No remote or release was created. The separate large raw export remains outside Git. It is required for exact original-byte lookup, while the curated design/reference docs can be read on their own.

## Review and verification

Three subagents read assigned complete discussion ranges and attachments, wrote detailed reference documents/point ledgers, and cross-reviewed the actual active/reference documentation. The root agent integrated the effective owners, inspected the source inventory, read the final consolidation and detailed late-stage record, and reconciled cross-review findings. [PRESERVATION_AUDIT](reference/PRESERVATION_AUDIT.md) records the final coverage/check results and source limits.

Checks used Python **3.13.16** from the existing local interpreter at `../pdf-to-md-agent/.venv/Scripts/python.exe`, with bytecode writing disabled. This reused an interpreter read-only; it did not import or modify the old application. The tools need only a working Python 3.9+ interpreter. Bare `python`/`python3` on the reviewed Windows host resolved to nonworking WindowsApps aliases, so use a working executable path there.

Document/hash/coverage checks do not establish runtime correctness, semantic losslessness or installed-product readiness. Source IDs and explicit dispositions make review gaps visible; exact source limits remain in SOURCE_INDEX and the audit.

## Next work

The next implementation-planning task should settle only document update/reference semantics, capacity/handoff transitions, and persistence/recovery/stop boundaries using their stated closure conditions. Preserve autonomy and full source access. A useful first implementation increment connects a real source/scope to saving, reopening and explicit-version export, including candidate preservation and basic capacity behavior; it need not wait for advanced visual helpers or generalized branch infrastructure.

The present request creates the repository and preserves knowledge. App implementation and any live verification require a subsequent human task. Broader network design remains deferred; necessary shared execution boundaries are already recorded. Reopen other design only for a concrete contract-breaking implementation/delivery issue or changed human requirement.
