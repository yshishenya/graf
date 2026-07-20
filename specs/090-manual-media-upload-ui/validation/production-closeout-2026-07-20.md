# Feature 090: production closeout receipt 2026-07-20

This receipt contains only deployment metadata. It does not contain audio,
transcript or summary text, credentials, cookies, object keys, private paths or
real user identifiers.

- Follow-up hotfix PR: `#3877`, merged before the release.
- Release PR: `#3878`.
- Release: `v2026.07.20.5`.
- GitHub Release: published and points to merged master SHA
  `271ba65c433025fb10c7ef57004acc56cb325f13`.
- Production runtime SHA: `271ba65c433025fb10c7ef57004acc56cb325f13`.
- Deploy gate: `infra/scripts/cd-remote.sh --dry-run` passed, followed by the
  approved execute gate.
- Backup and restore rehearsal: pass.
- Migration head: `0028_active_space_read`.
- Runtime secret group, service-secret permissions, database and media secret
  provisioning: pass.
- API, PostgreSQL, Temporal, processing worker and media worker readiness: pass.
- Disposable PostgreSQL RLS probe: pass. This is not a live production RLS
  enforcement claim.
- Production smoke: `smoke_result=pass`, `readiness_verdict=infra_smoke_ready`.
- Smoke upload reached `ingested_pending_processing`; the infrastructure smoke
  intentionally does not claim transcript, speaker or stored-summary readiness.
- Auth cleanup: pass. Artifact cleanup: pass, residue records empty, three
  synthetic objects removed, no keys emitted.
- Public health: `/api/v1/health/live` returned `{"status":"ok"}` and
  `/api/v1/health/ready` returned `{"status":"ready"}`.
- Final local CI: macOS 582 passed; PostgreSQL parallel 1935 passed / 1 skipped,
  strict 34 passed / 1 skipped; Ruff, compile, Compose and deployment evidence
  scan passed. Boundary suite passed 20 tests and the two-transaction lock
  selection passed 2 tests.
- Deferred post-deploy checks are reported by the deploy gate as
  `automatic_retry_result=required_post_deploy`,
  `backfill_inventory_result=required_post_deploy`,
  `range_playback_result=required_post_deploy`, and
  `normalization_cleanup_result=required_post_deploy`; no pass claim is made
  for those separate receipts.

The remaining production boundary is the separate `test-rec` final-review path
that must prove non-empty transcript, speaker truth, stored GRAF summary and
zero residue without recording private content in evidence.
