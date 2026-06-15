# Contract: Rollout Truth Remediation

## Purpose

Define which stale `031` claims must be corrected by `032`.

## Required Surfaces

The implementation must review and update:

- `docs/current-product-status.md`
- `docs/deployments/2brain-rec/rls-hardening-runbook.md`
- `docs/adr/003-tenant-isolation-rls.md`
- `CHANGELOG.md`
- `specs/031-rls-hardening/quickstart.md`
- `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- `apps/server/scripts/verify_rls_hardening.py`
- RLS production-boundary tests under `apps/server/tests/`

## Correction Rules

- Current status must state production RLS enforcement is enabled only after
  read-only production metadata proves enabled/forced state.
- Historical `031` pre-production wording may stay only when clearly framed as
  historical or as test/disposable probe behavior.
- Current command output must use `live_production_enforcement=not_inspected`
  for test/disposable validation that does not inspect or change live
  production.
- Production read-only verification must use a different field/value from
  destructive test probe validation.

## Validation

- A stale-language scan must look for `not_changed`, `separate operator
  decision`, and similar wording across the required surfaces.
- Any remaining match must be justified as historical or test-only wording.
