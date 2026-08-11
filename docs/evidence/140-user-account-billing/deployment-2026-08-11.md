# Deployment evidence — 2026-08-11

Metadata-only record for Feature 140. No provider credentials, customer IDs,
emails, raw webhook bodies, audio, transcripts or private meeting content are
stored here.

- Host: `2brain.dev`; project: `/opt/projects/2brain-rec`
- Branch/SHA: `master` / `24e55765e412686291861464b845a62974a7c666`
- Migration: `0057_referral_workspace_scope (head)`
- Health: `/api/v1/health/live`, `/api/v1/health/ready`, `/` → HTTP 200
- Smoke: config validation, migration/RLS disposable probes and metadata-only
  cleanup → PASS
- Cleanup: 43 database rows, 3 object keys, residue list empty
- Billing: `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`; no provider mutation or
  real-shop canary was performed

This evidence proves deployed runtime readiness only. Public billing remains
blocked until controlled YooKassa canary, edge source/TLS allowlist and live RLS
review, plus merchant/product/finance/legal/security/QA sign-offs, are attached
to `docs/runbooks/billing-launch.md`.
