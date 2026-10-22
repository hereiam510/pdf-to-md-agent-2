# Preservation audit

Recorded 2026-10-22, Asia/Hong_Kong. This audit concerns documentation coverage and source traceability, not application behavior. The original export remains outside the new repository. No recorded source command was executed.

## Source integrity and coverage

| Check | Result and scope |
| --- | --- |
| Supplied export manifest | All **5,222 listed files** matched recorded byte size and SHA-256; no mismatch |
| Visible conversation | All **207 user/assistant messages** have a disposition: 47 user, 48 final assistant records and 112 commentary records |
| Attachments | All **30** preserved: 28 pasted-text files and two forum HTML files; source hashes matched |
| Embedded substantive forum content | All 14 research illustrations in ATT-01 and all 10 substantive image pages in ATT-02 inspected; the ten separate ATT-02 images matched embedded bytes |
| Later human scoping decisions | LIVE-01 through LIVE-05 preserved separately from the earlier export snapshot |
| Selected background sources | EVT-0001 inherited product context and SUP-01/02 selected continuing requirements/guidance, without importing old task/default/status authority |
| Point ledger | **308 entries** with source IDs, status, explanation and documentation destination: 102 foundations, 116 context/state, 65 delivery/recovery, 25 effective-owner mappings |
| Source disposition ledger | **245 sources** accounted for: 242 mapped to retained points, one empty saved message, two administrative export messages; no unresolved classification |

The [point ledger](POINT_COVERAGE.json) is a navigation and omission-audit aid, not a count of independent features. Some entries group related nuances and some active-owner mappings overlap the detailed discussion. [SOURCE_COVERAGE](SOURCE_COVERAGE.json) makes administrative and empty-message treatment explicit. [SOURCE_INDEX](SOURCE_INDEX.md) records exact provenance and source limitations.

The synthesis preserves final requirements, preferred architecture, reasons, cautions, observations, hypotheses, rejected/superseded alternatives and open questions. It does not make every preserved proposal a current requirement. Detailed reference material is optional reading for a relevant question, rather than a mandatory development prompt.

## Delegated authorship and independent checks

| Reviewer | Full assigned source reading and authorship | Cross-review |
| --- | --- | --- |
| Foundations agent | EVT-0002–0414; ATT-01–06; inherited product handoff; final consolidation; forum text and images | Active owners and the late final-contract narrowing; framework rankings/statuses |
| Context/state agent | EVT-0415–0826; ATT-07–20; all 5,500 prepared lines; final consolidation | Foundations' framework claims and active state/hydration/recovery/capacity boundaries |
| Delivery/recovery agent | EVT-0827–1168; ATT-21–30; final consolidation | Active owners, source lookup and actual new repository entry points; then the completed middle record's policy/recovery sections |
| Root integration | Product/scoping sources, final consolidation, detailed late-stage record, source/attachment inventory, selected earlier source passages | Reconciled findings, authored effective owners, audited source dispositions, links, Git scope and preservation of the old repository |

These were source-reading, writing and review assignments in this task. They are not future runtime approval gates or a requirement for a fixed number of reviewers.

Material corrections made during cross-review:

- Local metadata edits now explicitly target a named base version and expected head, preventing an ambiguous interpretation of “current document.”
- The later EVT-0878 simplification controls the effective design: small context policy lives in Graph State with one settlement writer; earlier external policy-version/activation tables are historical proposals. Durable model budgets, document commits and actual external-effect receipts remain separate.
- Payload hash equality is distinguished from operation identity and semantic intent.
- Native encoding follows the context-selected frozen input; the request service does not independently select old evidence again.
- Public lookup and ledger destinations use stable source IDs and versioned documents, not ignored private review packets. Later user highlighting is not misdescribed as agreement, and LIVE anchor lookup is distinguished from hash-verified exported sources.

## Documentation and repository checks

`tools/check_docs.py` passed with no missing local links/anchors, duplicate point identities, unknown source IDs, unresolved source dispositions or invalid point destinations. It checks the 14 Markdown files and both preservation ledgers. Syntax parsing passed for the two standard-library utilities. EVT-1166, ATT-30, SUP-02 and LIVE-05 lookup paths were checked; EVT/ATT/SUP source hashes passed, and LIVE resolved to its maintained anchor. These are documentary utility checks, not application tests.

Checks used an existing Python 3.13.16 interpreter with bytecode writing disabled. The reviewed host's bare WindowsApps Python aliases were unusable; a full interpreter path worked. No environment/dependency install or global setting change was needed.

The original repository was checked before and after: **HEAD and Git status unchanged**, all **103 tracked/nonignored untracked file hashes unchanged**, and no new nonignored file. Its pre-existing uncommitted changes remain intact. Ignored runtime trees were not copied or intentionally modified; they are outside the file-hash comparison. The new repository has its own Git directory/history and contains only the curated design/reference documents and source/document checking utilities. Private scratch and runtime inputs/outputs are ignored.

No remote publication, app implementation, provider generation/probe, PDF conversion, benchmark or installer verification was performed. The supplied raw export was read without modification.

## Honest completeness boundary

All available discussion messages and user attachments in the selected export have been read and assigned a preservation disposition, supplemented by the later repository instructions. This combines complete delegated source reading, point-level synthesis and independent semantic review. Neither counts nor hashes mathematically prove that no nuance could ever be interpreted differently.

The original source limits remain visible: EVT-0258 has an empty saved final-answer body; some forum screenshot code is clipped in the original; five older development-file revisions were not recoverable from the saved patches; and the export records missing incidental linked assets/path candidates. These do not represent missing pasted-text attachments. No missing text/code/private reasoning was invented. Exact originals remain in the separate export, whose lifetime is independent of this Git repository.

No unresolved source-disposition gap or known material contradiction remains after this task's review. The three product-contract questions in [OPEN_QUESTIONS](../OPEN_QUESTIONS.md) remain intentionally open. They are design work, distinct from preservation coverage.
