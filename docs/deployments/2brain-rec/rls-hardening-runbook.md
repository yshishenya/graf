# RLS Hardening Runbook

Feature: `031-rls-hardening`

This runbook covers PostgreSQL row-level security validation for the current
2brain Rec backend schema. The `031` migration enables and forces RLS when it
is applied. A 2026-06-15 production inspection confirmed the live Rec database
is at `0005_rls_hardening` and every covered table has RLS enabled and forced.

## Required Gates

Run these gates before changing RLS policy coverage or accepting a new
production truth record:

1. Local regression: `./infra/scripts/ci-local.sh`
2. PostgreSQL RLS probe suite with `RLS_TEST_DATABASE_URL` set, or the
   disposable database path created by the canonical release flow.
3. Production-like migration verification: the migration gate inside
   `./infra/scripts/cd-remote.sh --execute --branch master`.
4. Production read-only state inspection:
   `python3 apps/server/scripts/verify_rls_hardening.py --production-read-only`
5. Metadata-only evidence scan for specs, tests, scripts, and deployment notes.

Required probe categories:

- `same_tenant_read`
- `cross_tenant_read_not_found_or_empty`
- `cross_tenant_mutation_forbidden`
- `missing_context_auth_or_context_error`
- `worker_context`
- `maintenance_context`

Production verification must run probes against a disposable `twobrain_rec_rls_*`
database unless an operator intentionally provides a separate test database URL.
Do not point `RLS_TEST_DATABASE_URL` at the live `twobrain_rec` production
database. The validation helper fail-closes before probes when
the URL database name is `twobrain_rec`.

Direct `verify-rec-migration.sh --remote` and `--execute` calls are blocked;
this prevents an isolated check from competing with another release or
accidentally touching the shared production runtime.

## Halt Criteria

Halt rollout if any probe is missing, blocked, failed, or inconclusive.

Do not include transcript text, raw audio, object keys, tokens, signed URLs,
passwords, live secret paths, or customer meeting content in evidence.

Halt if evidence would require forbidden content.

## Rollback

If migration validation fails before live enforcement, use
`docs/deployments/2brain-rec/rollback-runbook.md` with trigger `migration` and
the latest verified backup reference. Record any residue owner and follow-up
reason before retrying.

## Live Production Decision

Current production truth is accepted only from metadata-only state inspection,
not from destructive probes. The 2026-06-15 inspection showed:

- deploy path: `/opt/projects/2brain-rec`;
- deployed commit: `3fd2162`;
- Alembic revision: `0005_rls_hardening`;
- covered tables: all enabled and forced through PostgreSQL catalog metadata.

Expected production read-only success:

```text
production_rls_state_result=pass
environment=live_production
live_production_probe=read_only_metadata
live_production_enforcement=enabled
```

Expected test/disposable safe default when no PostgreSQL test database is
provided:

```text
rls_validation_result=blocked
environment=postgres_test
live_production_probe=not_attempted
live_production_enforcement=not_inspected
```
