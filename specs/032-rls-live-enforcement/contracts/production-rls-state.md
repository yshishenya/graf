# Contract: Production RLS State

## Purpose

Define the read-only production check required before claiming live production
RLS enforcement is enabled.

## Inputs

- Production deploy path, default `/opt/projects/2brain-rec`.
- Expected production database, default `twobrain_rec`.
- Covered table inventory from the `031` RLS migration/policy source.

## Required Metadata

The check must report:

- `production_rls_state_result`: `pass` or `blocked`.
- `environment`: `live_production`.
- `deployed_commit`.
- `alembic_revision`.
- `covered_table_count`.
- `rls_enabled_and_forced_count`.
- `failed_table_names` when blocked.

## Pass Criteria

- Production deploy path is reachable.
- Alembic current is `0005_rls_hardening` or a later revision that includes it.
- Every covered table exists.
- Every covered table reports `relrowsecurity=true`.
- Every covered table reports `relforcerowsecurity=true`.

## Block Criteria

- Production target is unreachable.
- Alembic current is older than `0005_rls_hardening`.
- Any covered table is missing.
- Any covered table has RLS disabled or not forced.
- The check would require reading or mutating customer rows.

## Forbidden Content

Output must not include credentials, signed URLs, raw object keys, transcript
text, raw audio, live secret paths, or customer meeting content.
