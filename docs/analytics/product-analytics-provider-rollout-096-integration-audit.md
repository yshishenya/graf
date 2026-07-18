# Feature 096 integration audit

Date: 2026-07-18

## Current anchor

- Current anchor: the `origin/master` line after the docs-only reconciliation
  PRs #3848 and #3849.
- The comparison snapshot before those docs-only merges was `dfa976b4`.
- Historical provider branch: `096-product-analytics-provider-rollout` at
  `137565c0`.
- The branches share merge-base `d419b5af`; `git rev-list --left-right
  --count origin/master...origin/096-product-analytics-provider-rollout`
  reports `272 15`.
- The branch is neither merged into current master nor covered by a release
  tag. It also changes files that were later changed by Features 097–111.

## Evidence that can be reused

- PostHog first-party live-safe transport was exercised on the historical
  branch with redacted metadata-only output.
- The branch contains provider contracts, secret-file boundaries, page-scope
  rules, rollback procedures, and a production deploy narrative that can be
  reviewed as source material.
- The historical GRAF backup/restore rehearsal is not evidence of a complete
  generated PostHog-volume backup/restore rehearsal.

## Evidence that remains open

- Yandex OAuth secret-file setup and a real live upload of exactly
  `desktop_account_connected` and `first_value_session_completed`.
- A resolver for runtime ClientId/Yclid values, or an explicit decision that
  the first production slice supports only the proven UserId path.
- Full PostHog backup and isolated restore, concrete resource/alert thresholds,
  retention/deletion lifecycle proof, RBAC/audit review, and real dashboard
  freshness/goal visibility review.
- Executed rollback proving that provider delivery can be disabled without
  breaking ordinary recording, processing, auth, or cabinet workflows.
- A regenerated page inventory and provider proof for the current master,
  including routes added after the historical branch.
- Legal, privacy, security, QA, disclosure, and product-rollout approvals.

## Append-only convergence worklist

These items are intentionally new work after the historical branch and do not
rewrite its checked task history.

- [ ] T097 Create a clean integration branch from current `origin/master` and
  transfer only reviewed provider code, contracts, and docs; preserve all
  Features 097–111 behavior.
- [ ] T098 Reconcile `config.py`, Compose, OpenAPI, cabinet/admin rendering,
  and public routes manually; no wholesale merge or rebase of the historical
  branch.
- [ ] T099 Regenerate the browser/page inventory and privacy/credential
  suppression evidence against the current master route set.
- [ ] T100 Re-run the bounded provider/privacy smoke required by the integrated
  code and record metadata-only output; the current turn deliberately does not
  start another long test suite.
- [ ] T101 Complete a real PostHog backup/isolated-restore, RBAC/audit,
  retention/lifecycle, dashboard freshness, and concrete resource-threshold
  review.
- [ ] T102 Provide the out-of-git Yandex OAuth secret-file setup and run the
  two-event live-safe upload smoke without committing or printing credentials.
- [X] T103 Explicitly scope the ClientId/Yclid identity-resolver gap to the
  proven UserId path, execute the metadata-only rollback path, and verify
  ordinary product workflows remain intact in the current-master receipt.
- [ ] T104 Reconcile `spec.md` status, evidence wording, tasks, tracker, release
  notes, tag, and production receipt before claiming Feature 096 complete.

## Safety boundary

Until T101, T102, and T104 are complete, Feature 096 remains a
provider/infrastructure integration candidate, not a production product-rollout
approval. Do not enable Yandex offline upload, change production approval
flags, or claim paid-campaign readiness from the historical branch's
fake-transport smoke.
