# Quickstart: Provider Link Verified Callback

## Focused development validation

1. Run the provider-link contract and callback tests. Prove a raw `/auth/link` request returns the safe compatibility error and does not create an identity.
2. With fake providers, start a link from an authenticated session, complete a verified callback, and verify that no identity or session changes before the explicit CSRF-protected confirmation.
3. Confirm with the originating session. Verify one linked identity, terminal intent, cleared candidate claims and metadata-only audit. Repeat with a new intent for the same subject and verify idempotence.
4. Verify conflict, disabled provider, revoked membership, wrong user/workspace or session, expiry, callback replay and confirm replay make no identity mutation and reveal no owner/contact information.
5. Run Postgres RLS integration tests to prove callback lookup is exact-nonce scoped and request-context rows are owner/session scoped.
6. Render browser and embedded Settings flows. Verify labelled controls, focus and status messaging, safe cancelled/expired/conflict text, CSRF rejection, and no raw identity data in HTML.
7. Re-run normal provider login/signup contracts to prove the login resolver is unchanged.

## Closeout validation

Run `infra/scripts/ci-local.sh`. For the behavior release, perform the project release flow, `infra/scripts/cd-remote.sh --dry-run`, production deploy, and a metadata-only browser/embedded Settings smoke. Do not use a real provider credential or include a raw callback payload in evidence.

## 2026-07-17 local evidence

- Focused contract/cleanup/RLS-migration/UI suites pass with fake providers;
  link lifecycle, CSRF, expiry/replay, exact initiating session, conflict,
  safe Settings copy and audit redaction are covered.
- Canonical `infra/scripts/ci-local.sh` passes: 643 macOS tests, 1757 server
  tests, 28 expected PostgreSQL-only skips, Ruff, compile, Compose rendering
  and deployment-evidence scan (`ci_local_result=pass`).
- Disposable local PostgreSQL RLS module passes 16/16, including two concurrent
  confirmations of one provider subject; it leaves zero residual
  `crisp_feature100_race_*` or `crisp_feature100_rls_*` databases. PR review
  record and production dry-run/deploy/smoke remain release gates.
- Independent product/UX, architecture/code and security/privacy reviews found
  no Critical or High issue. The formal repository scan 097 remains deferred
  by user direction; it is not represented as completed evidence for this PR.
- A separate disposable PostgreSQL migration receipt passes `0023 → 0025 →
  0023 → 0025 (head)` with zero residual `crisp_feature100_migration_*`
  databases.
