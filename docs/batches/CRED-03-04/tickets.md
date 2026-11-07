# CRED-03-04 tickets

[Spec and authority](spec.md) · [Verification](verification.md)

All work is owned by the main agent. The subsequent 2026-11-07 request selects integration review, scoped corrections and combined acceptance under the spec's offline boundary. Stop at batch closeout without starting another investigation. Shared credential state requires sequential integration.

## CRED-03

Contribution: implement the selected default-file failure correction. Basis and completion conditions: [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06), [follow-up acceptance](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependencies: inspected actual baseline and preserved inherited work under the spec. State: complete at the scoped offline boundary, main agent, 2026-11-07. The discovery-only absence correction and production-path regressions are implemented; [verification](verification.md#cred-03-offline-execution-2026-11-07) owns the baseline failure, checks and limits. This does not complete CRED-04 or integration.

## CRED-04

Contribution: implement selected Remember capability recovery. Same [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06) and [acceptance owner](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependency: CRED-03 source/build identities and passing evidence were verified at entry `8353dce` on the reused `codex/cred-03` branch. This is execution ordering, not a new product dependency. State: complete at the scoped offline boundary, main agent, 2026-11-07. Capability refresh and revision protection are implemented; [CRED-04 verification](verification.md#cred-04-offline-execution-2026-11-07) owns the baseline failures, recovery/newer-intent checks and limits. Inherited work remains preserved.

The CRED-04-only request stopped at that ticket; the subsequent request selects combined review/acceptance below.

## CRED-03-04-INTEGRATION

Main agent reviews the combined changes, executes the linked follow-up and original regression checks under the spec's offline boundary, corrects scoped failures and records the combined verdict in verification. Dependencies: CRED-03 and CRED-04, both verified present at entry `5997f14`. State: complete, main agent, 2026-11-07. [Integrated review/checks](verification.md#integration-review-and-execution-2026-11-07) and [combined acceptance](verification.md#combined-acceptance) own the observed outcome, corrections, tested identity and limits.

Execution followed both acceptance matrices and the batch's offline boundary, preserving both repair checkpoints, their distinct evidence and inherited work. The user-selected stopping point is batch closeout; no follow-on investigation or operational work is started. A future supported regression returns to the governing credential rules and its own recorded evidence rather than reopening historical execution permissions.
