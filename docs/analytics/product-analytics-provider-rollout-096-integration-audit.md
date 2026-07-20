# Feature 096 integration audit

Date: 2026-07-18

## Current anchor

- Current integration base: `origin/master` at `e96debf4`.
- Integration branch: `codex/096-provider-code-integration` at `be28586d`.
- Pull request: #3852, still draft and not merged.
- Historical provider branch: `096-product-analytics-provider-rollout` at
  `137565c0`; it is source material only and was not merged wholesale.
- The current branch preserves the later Feature 097–111 changes and keeps
  provider delivery fail-closed. No release tag or production deploy exists
  for this candidate.

## Evidence that can be reused

- PostHog first-party live-safe transport was exercised on the historical
  branch with redacted metadata-only output.
- The branch contains provider contracts, secret-file boundaries, page-scope
  rules, rollback procedures, and a production deploy narrative that can be
  reviewed as source material.
- The current integration continuation now has a metadata-only backup and
  isolated restore receipt for all twelve generated PostHog volume classes;
  see `infra/posthog/backup-restore.md` and the current-master validation
  receipt. The historical GRAF rehearsal remains separate evidence.

## Evidence that remains open

- T101: independent RBAC/audit review, complete retention/deletion lifecycle
  for provider data, session data, backups and exports, dashboard freshness and
  goal visibility, and concrete resource/alert thresholds. The twelve-volume
  backup/isolated-restore subgate passed under receipt `20260718T011751Z`, but
  the generated stack still has no enforced per-service CPU/memory limits.
- T102 is now complete: the out-of-git Yandex OAuth secret-file setup is
  present and the current-candidate live-safe smoke accepted exactly
  `desktop_account_connected` and `first_value_session_completed`. Production
  upload flags remain disabled.
  The token remains outside git and evidence.
- T104: reviewer approval, merge, CalVer release/tag, production receipt and
  final status reconciliation. PR #3852 is still draft; no release or execute
  deploy is claimed.

The ClientId/Yclid gap is now explicitly scoped: the proven slice accepts only
an explicit runtime UserId and rejects unresolved attribution values. The
metadata-only rollback path and ordinary recording, processing, auth and
cabinet workflow regressions are evidenced in the current-master receipt.

## Append-only convergence worklist

These items are intentionally new work after the historical branch and do not
rewrite its checked task history.

- [X] T097 Create a clean integration branch from current `origin/master` and
  transfer only reviewed provider code, contracts, and docs; preserve all
  Features 097–111 behavior. Receipt: `validation/current-master-integration.md`.
- [X] T098 Reconcile `config.py`, Compose, OpenAPI, cabinet/admin rendering,
  and public routes manually; no wholesale merge or rebase of the historical
  branch. Receipt: current-master reconciliation and full CI.
- [X] T099 Regenerate the browser/page inventory and privacy/credential
  suppression evidence against the current master route set. Receipt: page
  validation and current-master privacy evidence.
- [X] T100 Re-run the bounded provider/privacy smoke required by the integrated
  code and record metadata-only output. Receipt: bounded smoke, rollback
  dry-run and full CI; this is not real-provider evidence.
- [ ] T101 Complete the remaining PostHog RBAC/audit, retention/lifecycle,
  dashboard freshness, and concrete resource-threshold reviews; the real
  backup/isolated-restore subgate is already evidenced, but the generated
  runtime has no enforced per-service CPU/memory limits.
- [X] T102 Provide the out-of-git Yandex OAuth secret-file setup and run the
  two-event live-safe upload smoke without committing or printing credentials.
  Receipt: `validation/current-master-integration.md`; no credential, counter
  ID, CSV row, or response body is included in evidence.
- [X] T103 Explicitly scope the ClientId/Yclid identity-resolver gap to the
  proven UserId path, execute the metadata-only rollback path, and verify
  ordinary product workflows remain intact in the current-master receipt.
- [ ] T104 Reconcile `spec.md` status, evidence wording, tasks, tracker, release
  notes, tag, and production receipt before claiming Feature 096 complete. The
  current PR is #3852 (draft); convergence issues #3853–#3860 now mirror
  T097–T104, with T101/T104 still open.

## Safety boundary

Until T101 and T104 are complete, Feature 096 remains a
provider/infrastructure integration candidate, not a production product-rollout
approval. The T102 live-safe receipt proves provider acceptance only; do not
enable long-running Yandex offline upload, change production approval flags, or
claim paid-campaign readiness from smoke evidence alone.
