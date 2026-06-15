# Data Model: RLS Production Enforcement Truth

## RLSProductionTruthVerdict

Represents the current accepted truth about live production RLS enforcement.

Fields:

- `status`: one of `test_gate_required`, `production_verified_enabled`,
  `production_verification_blocked`, `halted`, `rolled_back`.
- `target_environment`: production target label, expected `2brain.dev` /
  `/opt/projects/2brain-rec`.
- `deployed_commit`: Git commit observed on the production deploy path.
- `alembic_revision`: current Alembic revision observed in production.
- `checked_at`: timestamp of the verification.
- `evidence_references`: metadata-only links to safe evidence.
- `blocking_reasons`: list of missing gates, failed tables, or unreachable
  checks.

Validation rules:

- `production_verified_enabled` requires the production table-state evidence to
  prove every covered table has RLS enabled and forced.
- `production_verified_enabled` requires a current test/disposable validation
  evidence reference.
- No field may contain credentials, secret paths, object keys, transcript text,
  raw audio, or customer meeting content.

## RLSTableStateEvidence

Read-only evidence for one covered production table.

Fields:

- `table_name`: covered tenant-owned table name.
- `rls_enabled`: PostgreSQL `relrowsecurity` value.
- `rls_forced`: PostgreSQL `relforcerowsecurity` value.
- `source`: `pg_catalog`.

Validation rules:

- Covered tables must come from the `031` RLS policy inventory.
- A table passes only when `rls_enabled=true` and `rls_forced=true`.
- Missing tables or tables with false values block the production-enabled
  verdict.

## RLSTestGateEvidence

Metadata-only proof that destructive RLS probes were run on a safe database.

Fields:

- `environment`: `local`, `postgres_test`, or `production_like`.
- `database_class`: `disposable` or `explicit_test`.
- `probe_results`: same-tenant, cross-tenant, missing-context, worker-context,
  and maintenance-context outcomes.
- `migration_revision`: Alembic revision tested.
- `created_at`: timestamp of the evidence.

Validation rules:

- `database_class` must not be `live_production`.
- Any failed, missing, stale, or inconclusive probe blocks production truth
  claims.

## RolloutTruthRemediation

Tracks stale wording corrected by this feature.

Fields:

- `source_path`: documentation, script, or test path with stale wording.
- `old_claim`: short summary of the stale claim.
- `new_claim`: corrected production truth wording.
- `status`: `updated`, `historical_note_kept`, or `blocked`.

Validation rules:

- Current validation output must use `not_inspected` for test/disposable
  validation that does not touch live production.
- Current product status must not say live production RLS is still only a
  future separate decision when production metadata proves enabled/forced.
