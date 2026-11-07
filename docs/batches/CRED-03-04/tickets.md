# CRED-03-04 tickets

[Spec and authority](spec.md) · [Verification](verification.md)

All work is owned by the main agent. The current organization request does not start application execution. Shared credential state requires sequential integration.

## CRED-03

Contribution: implement the selected default-file failure correction. Basis and completion conditions: [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06), [follow-up acceptance](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependencies: inspect the actual baseline and preserve inherited work under the spec. State: not started. Evidence will link to verification after actual execution.

## CRED-04

Contribution: implement selected Remember capability recovery. Same [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06) and [acceptance owner](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependency: integrate CRED-03 before editing shared credential state. This is execution ordering, not a new product dependency. State: not started.

## CRED-03-04-INTEGRATION

Main agent reviews the combined changes, executes the linked follow-up and original regression checks under the spec's offline boundary, corrects scoped failures and records the combined verdict in verification. Dependencies: CRED-03 and CRED-04. State: not started. Existing historical results do not certify either new repair.
