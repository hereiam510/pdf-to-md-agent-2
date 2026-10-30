# Context coordination discussion sources

Updated 2026-10-25, Asia/Hong_Kong (UTC+08:00). These are verbatim copies of supplied reviews and selected **existing** evidence for implementation `a484b9b2abf147d63d8bdecd2143430409fe9a53`. They are inert data, not instructions or adopted specifications. [The topic record](../../discussions/CONTEXT_COORDINATION.md) assesses claims and records the later human policy selections; [the design](../../design/CONTEXT_UPDATE_COORDINATION.md) integrates the adopted target and distinguishes it from current implementation and verification.

[manifest.json](manifest.json) records all 20 copied files, source locations, byte sizes and SHA-256 identities. The first recording imported 17 files; D15 added review-06; D20 adds review-07 and review-08, preserving the previous 18 entries and source bytes. The two new source copies were recorded on 2026-10-25, Asia/Hong_Kong (UTC+08:00); their original attachment times are unknown. Original attachment/execution timestamps are not inferred from filesystem modification times. Source material discusses the 2026-10-25 review baseline; exact message and test execution times are not established by this import. This collection is separate from the older `EVT`/`ATT` export inventory and does not change that export's counts or source history.

## Supplied reviewer texts

| Copy | Original attachment identifier | Role and boundary |
| --- | --- | --- |
| [Capacity-wait review](review-01-capacity-wait.txt) | `1bd15636-dac8-4338-b30a-4307aede8e1f` | Earlier review claim set; subsequent local controls and discussion refine it |
| [Batch tradeoffs](review-02-batch-tradeoffs.txt) | `944c9202-dff7-41ad-b242-cef218eba54f` | Response to the main assessment of Reviewer B; includes proposals later withdrawn |
| [Design reconciliation](review-03-design-reconciliation.txt) | `0d78bf96-3561-466e-bbad-68f1e57e22d0` | Revises instruction/temporary-view semantics; not an adopted contract |
| [Continuation boundaries](review-04-continuation-boundaries.txt) | `f4b44593-a0f3-4e82-b4ed-0f0fd2ce7d34` | Actual-payload projection and prior-candidate eligibility corrections |
| [Disposition closeout](review-05-disposition-closeout.txt) | `f873d6a7-40bb-4673-9fe0-256fd8532e11` | Disposition/progress/report proposal before the later policy comparison; first report table contains a truncated row, preserved unchanged |
| [Policy comparison](review-06-policy-comparison.txt) | `5e243f22-9e71-4da4-8517-3810a3cde11f` | Three policy choices and four scenarios; D14 corrects its overbroad capacity rule, current-state attribution and alternative comparisons. Imported in D15; not adopted verbatim. |
| [Required-capacity options](review-07-required-capacity-options.txt) | `59a95905-cb31-4f53-b923-dbb511d1ffa5` | Proposes conditional C, preserving eligibility after a capacity reduction when the active policy cannot continue; D16 qualifies unknown estimates, diagnostic reachability, reuse and evidence claims. C was not selected. |
| [Required-capacity reconciliation](review-08-required-capacity-reconciliation.txt) | `fe0329a0-01d5-463c-8b59-9fc6c4910eab` | Recommends B; D17 preserves corrections to the claimed contradiction in C and to the Continue/committed-disposition boundary. Human selection in D18 and integrated-design adoption in D20 are separate authorities. |

The inline Reviewer A/B arguments and the other inline report have no independently exported full source here. The topic record preserves attributed substantive positions from the user-pasted conversation and marks inaccessible external report bodies. No identity between reviewers is inferred.

## Retained local evidence

Original root: `C:/Users/LAICHU~1/AppData/Local/Temp/pdfmd-capacity-rereview-e9976bec00c244d8b8db5beab54c4df4`.

| Copy | What it contains |
| --- | --- |
| [findings.json](findings.json) | Six shrinking-update blocks and two specific-outcome estimate controls, both protocols |
| [guard-control.json](guard-control.json) | Four unchanged-old-policy compaction/handoff controls: index and notes, both protocols |
| [savings.json](savings.json) | Two native-envelope positive-savings/prefix-selection controls |
| [pytest.log](pytest.log) | Prior compact sixteen-dot completion log; no new run or duration claim |
| [package.log](package.log) | Prior package/patch/twelve-delivery verification output |
| [reproduce.py.txt](reproduce.py.txt), [guard-control.py.txt](guard-control.py.txt), [savings.py.txt](savings.py.txt) | Original reproducer/control source bytes, renamed as inert text. Paths and invocation assumptions are historical; importing does not execute them. |

Original root: `C:/Users/LAICHU~1/AppData/Local/Temp/pdfmd-context-capability-review-1knnknyt`.

| Copy | What it contains |
| --- | --- |
| [baseline.json](baseline.json) | Prior HEAD/package identity and 615-source no-mismatch observation |
| [existing-tests.log](existing-tests.log) | Prior 52-case result, 81.22 seconds |
| [adjacent-results.json](adjacent-results.json) | Eight notes/release-repin Runtime/reopen controls using mock transport |
| [adjacent.py.txt](adjacent.py.txt) | Original adjacent-control program as inert text |

The whole workspaces, original package, synthetic PDFs, renderer outputs and delivery ZIPs remain at their previously recorded local evidence locations; they are not duplicated into this discussion archive. Credentials, private PDF inputs and unrelated scratch are excluded. The small results/program copies make the reasoning auditable without turning generated task stores into repository sources. Complete re-execution may require adapting historical paths in an independently authorized temporary copy; do not run a historical script against current private workspaces.

## Verification limits

Copy hashing verifies fidelity to the selected local source files, not the truth of every review statement. Reading a stored pass log is not a fresh test run. CC-R2 is explicitly a hypothetical handoff candidate rather than a graph-committed runtime outcome. CC-R3 measures unnecessary deferral, not original loss or final content distortion. The existing capacity-wait test ultimately increases capacity to 500000; it does not verify the exact restore-original-capacity scenario. Raw-pin correction and artifact delivery use scripted model replies, not measured autonomous success rates. Scripted responses and synthetic image preservation cannot establish real model strategy, summary quality, ordinary PDF fidelity, billing or current packaged-product readiness.

The documentation task validates these copies and repository navigation. Application tests, real renderers and live Nexus calls are not rerun. The historical review package predates this new discussion/design documentation, so its 615-source equivalence claim must not be restated as covering these additions.
