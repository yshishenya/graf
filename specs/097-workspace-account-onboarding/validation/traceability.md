# Feature 097 traceability

This receipt is metadata-only and maps the Spec Kit task groups to the
existing GitHub issues. No new issue was created because the repository already
has one canonical issue for each group.

| GitHub issue | Task group | Implementation/evidence |
| --- | --- | --- |
| [#3706](https://github.com/yshishenya/crisp/issues/3706) | T001, T003–T009 | Personal/corporate schema, reversible migrations, RLS policies, idempotent helpers and onboarding audit; migration downgrade, unit and strict RLS receipts are recorded in `validation/local.md`. |
| [#3707](https://github.com/yshishenya/crisp/issues/3707) | T010–T016 | Email/provider parity, personal-space creation, scoped signup session, safe bootstrap anchor and browser contract coverage. |
| [#3708](https://github.com/yshishenya/crisp/issues/3708) | T017–T022 | User-bound join offers, explicit accept/reject lifecycle, CSRF routes, safe settings rendering and offer audit. |
| [#3709](https://github.com/yshishenya/crisp/issues/3709) | T023–T026 | Corporate-only admin permissions, invitation resend, last-owner protection and personal-space control hiding. |
| [#3710](https://github.com/yshishenya/crisp/issues/3710) | T027–T028 | Domain-only enrollment remains disabled; generic email/provider outcomes do not disclose corporate membership. |
| [#3711](https://github.com/yshishenya/crisp/issues/3711) | T029–T034 | Server-verified active-space listing and switching, revocation fallback, non-retargeting semantics and embedded macOS recovery state. |
| [#3712](https://github.com/yshishenya/crisp/issues/3712) | T035–T036 | Read-only legacy bootstrap classification and no-move backup/rollback runbook. |
| [#3713](https://github.com/yshishenya/crisp/issues/3713) | T037–T041 | Focused/full PostgreSQL receipts, review, tracker reconciliation and release/deploy closeout. Canonical CI, release, deploy and bounded production B2C/invitation/revocation receipts are recorded in `validation/local.md` and `validation/release-closeout.md`. |

## Open validation boundary

The direct expanded PostgreSQL gate is green with four workers. The canonical
`infra/scripts/ci-local.sh` gate also passed during the approved deploy at the
release-preparation SHA; the receipt is recorded in `validation/local.md`.
Release and production infrastructure closeout are complete at
`v2026.07.18.1`. A bounded metadata-only production user-path smoke then
listed and accepted a temporary identity-matched offer, switched between
personal/corporate spaces, revoked the corporate membership, confirmed the
revoked session was blocked, confirmed personal fallback and finished with
residue `0`. The smoke used an internal disposable identity rather than live
email delivery; it proves the deployed route/session semantics without
claiming an external mailbox receipt.
