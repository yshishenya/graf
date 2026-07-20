# Feature 090: production closeout receipt 2026-07-20

This receipt contains only deployment metadata. It does not contain audio,
transcript or summary text, credentials, cookies, object keys, private paths or
real user identifiers.

- Release: `v2026.07.20.4`.
- GitHub Release: published and points to the merged master line.
- Production runtime SHA: `7575838fff41e4f82945f45d3014460cc40702ea`.
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

The remaining production boundary is the separate `test-rec` final-review path
that must prove non-empty transcript, speaker truth, stored GRAF summary and
zero residue without recording private content in evidence.
