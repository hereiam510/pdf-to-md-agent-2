# CRED-03-04 tickets

[Spec and authority](spec.md) · [Verification](verification.md)

All work is owned by the main agent. The subsequent 2026-11-07 request selects CRED-04 only, after checking the CRED-03 prerequisite, under the spec's offline boundary. Stop before combined integration acceptance. Shared credential state requires sequential integration.

## CRED-03

Contribution: implement the selected default-file failure correction. Basis and completion conditions: [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06), [follow-up acceptance](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependencies: inspected actual baseline and preserved inherited work under the spec. State: complete at the scoped offline boundary, main agent, 2026-11-07. The discovery-only absence correction and production-path regressions are implemented; [verification](verification.md#cred-03-offline-execution-2026-11-07) owns the baseline failure, checks and limits. This does not complete CRED-04 or integration.

## CRED-04

Contribution: implement selected Remember capability recovery. Same [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06) and [acceptance owner](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependency: CRED-03 source/build identities and passing evidence were verified at entry `8353dce` on the reused `codex/cred-03` branch. This is execution ordering, not a new product dependency. State: complete at the scoped offline boundary, main agent, 2026-11-07. Capability refresh and revision protection are implemented; [CRED-04 verification](verification.md#cred-04-offline-execution-2026-11-07) owns the baseline failures, recovery/newer-intent checks and limits. Inherited work remains preserved.

The current request stops here; combined review/acceptance remains in the integration ticket below.

## CRED-03-04-INTEGRATION

Main agent reviews the combined changes, executes the linked follow-up and original regression checks under the spec's offline boundary, corrects scoped failures and records the combined verdict in verification. Dependencies: CRED-03 and CRED-04. State: not started. Existing historical results do not certify either new repair.

Continuation when selected: reconcile both implementation checkpoints, their distinct source/build/evidence identities and inherited Git changes. Review the combined credential owner and main/renderer integration against both acceptance matrices, then run the credential-state and credential-loader specs on the exact reviewed development build in a fresh isolated run (preserving meaningful builds before any rebuild). Resolve supported integration gaps, check affected records/type/build state as needed, and assess combined acceptance in verification. Preserve all offline exclusions; this continuation authorizes no provider/conversion, real-task, private-credential, global-settings, packaging, publication, cleanup or subagent work.
