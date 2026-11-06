# DOC-LAYOUT-01 verification

[Spec](spec.md) · [Tickets](tickets.md)

## Source basis

2026-11-07, Asia/Hong_Kong. Entry HEAD f1929b7. Inherited modifications: CURRENT_STATE, DEVELOPMENT_GUIDE, INDEX, WORK_ITEMS and the untracked 20261106_2307_ORGANIZATION_REVIEW. Raw entry copies, inherited patch and tracked-file hashes are retained in ignored `.local/batch-layout-20261107/`; this local recovery copy is not remotely available. Maintained pre-migration work register and handoff editions are linked from the catalogue.

## Preservation and ownership review

Compared 809 tracked files against their actual entry working-tree hashes. Only AGENTS, CURRENT_STATE, INDEX, REVIEW_HANDOFF and WORK_ITEMS changed; all other tracked files remain byte-identical, including the inherited DEVELOPMENT_GUIDE edit, product code, tests, lockfiles and historical evidence. The inherited untracked organization review also remains byte-identical. The documentation checkpoint includes the related inherited entry/planning changes and that review as preserved input; DEVELOPMENT_GUIDE is excluded.

DOC-ORG-R1's five criterion rows retain their original text, with explicit criterion anchors added. Outcome, scoped method, preservation guarantees, tickets and dependencies remain available in the batch. The policy supersedes its old combined-file location and verdict placement, not its substantive acceptance conditions. The old WORK_ITEMS specification/ticket headings now lead to those separate files. CRED-03/04 retains the full assignment, offline boundary, baseline, source/evidence links, preservation requirements and delivery limits from REVIEW_HANDOFF. Its normative behavior and regression matrices remain with their existing mechanism owners. Local ticket decomposition makes integration explicit without starting either repair.

Reader review followed README/AGENTS -> INDEX -> each batch spec, tickets and verification, and checked return links and legacy entry anchors. Historical planning snapshots remain visibly historical. A task-progress change now belongs in the local ticket file; its register entry links it. Broader pre-existing duplication identified by DOC-ORG-R1 is still outside this layout-only migration and is not claimed repaired.

## Checks and combined verdict

`python tools/docs/check_docs.py` passed with no errors: 108 Markdown files, 5,330 local link/destination checks and 503 bundled source-file integrity checks; existing preservation/coverage structures also passed. `git diff --check` passed. The main agent reviewed moved prose, authority boundaries, criterion preservation and the scoped diff separately from these mechanical checks.

Accepted for DOC-LAYOUT-01 A1-A3: fixed local-ticket structure, preserved substantive content and usable navigation. This is document organization acceptance only. DOC-ORG-R1 repair and CRED-03/04 product acceptance remain unassessed in their own verification files. No application repair, provider operation, conversion, remote Issue creation or publication has been performed. No application tests were required or run for this documentation-only change.
