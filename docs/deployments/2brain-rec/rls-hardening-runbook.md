# RLS Hardening Runbook

Feature: `031-rls-hardening`

This runbook covers PostgreSQL row-level security validation for the current
2brain Rec backend schema. It prepares evidence and rollback guidance only.
It does not enable live production enforcement by itself.

## Required Gates

Run these gates before asking for a separate operator decision:

1. Local regression: `./infra/scripts/ci-local.sh`
2. PostgreSQL RLS probe suite with `RLS_TEST_DATABASE_URL` set.
3. Production-like migration verification: `./infra/scripts/verify-rec-migration.sh --remote`
4. Metadata-only evidence scan for specs, tests, scripts, and deployment notes.

Required probe categories:

- `same_tenant_read`
- `cross_tenant_read_not_found_or_empty`
- `cross_tenant_mutation_forbidden`
- `missing_context_auth_or_context_error`
- `worker_context`
- `maintenance_context`

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

After local, PostgreSQL, and production-like gates pass, the only allowed
status is `ready_for_operator_decision=true`. Live production enforcement
requires a separate explicit operator decision and fresh metadata-only evidence.

Expected safe default:

```text
live_production_enforcement=not_changed
```
