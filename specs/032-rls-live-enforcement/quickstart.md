# Quickstart: RLS Production Enforcement Truth

This guide validates that `032` corrects the `031` production RLS truth gap
without running destructive probes on the live database.

## Prerequisites

- Production target remains `2brain.dev:/opt/projects/2brain-rec`.
- Existing production SSH access is available for read-only checks.
- Local server development environment is available through `uv`.
- No raw audio, transcript text, object keys, signed URLs, passwords, tokens,
  live secret paths, or customer meeting content may be copied into evidence.

## 1. Confirm Active Feature

```sh
SPECIFY_FEATURE_DIRECTORY=specs/032-rls-live-enforcement \
  .specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- `FEATURE_DIR` points at `specs/032-rls-live-enforcement`.

## 2. Local Regression

Focused 032 contract and boundary tests:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_rls_table_inventory_contract.py \
  tests/contract/test_rls_validation_output_contract.py \
  tests/contract/test_rls_production_boundary.py \
  tests/contract/test_rls_production_state_contract.py \
  tests/contract/test_rls_rollout_truth_docs.py \
  tests/contract/test_rls_production_truth_contract.py \
  tests/integration/test_rls_rollout_gates.py
```

Expected:

- Covered-table inventory matches the `031` migration.
- Test/disposable output uses `live_production_enforcement=not_inspected`.
- Production read-only output uses `live_production_enforcement=enabled` only
  when every covered table is enabled and forced.

```sh
./infra/scripts/ci-local.sh
```

Expected:

- Server tests pass.
- Ruff passes.
- Python compile passes.
- Production Compose config renders.
- Deployment evidence scan passes.

## 3. Disposable/Test RLS Probe Path

Without a test database URL:

```sh
python3 apps/server/scripts/verify_rls_hardening.py
```

Expected:

- Output is blocked because a PostgreSQL test database is required.
- Output must not imply production RLS is disabled.
- Output includes `live_production_probe=not_attempted`.
- Output includes `live_production_enforcement=not_inspected`.

With a disposable or explicit test database:

```sh
RLS_TEST_DATABASE_URL="$RLS_TEST_DATABASE_URL" \
  python3 apps/server/scripts/verify_rls_hardening.py
```

Expected:

- Direct SQL RLS probes pass.
- Destructive probes run only on the disposable/test database.
- `RLS_TEST_DATABASE_URL` pointing at live `twobrain_rec` remains blocked.
- Passing test output includes `ready_for_production_truth=true`.

Metadata fixture contract path:

```sh
python3 apps/server/scripts/verify_rls_hardening.py \
  --production-read-only \
  --table-state-json /path/to/metadata-only-rls-state.json \
  --deployed-commit 3fd2162 \
  --alembic-revision 0005_rls_hardening
```

Expected:

- Fixture-based command does not connect to production.
- Output uses the same production read-only vocabulary as the live command.

## 4. Production Read-Only State Inspection

Preferred script command on the production host:

```sh
ssh 2brain.dev "cd /opt/projects/2brain-rec && \
  docker compose -f infra/docker-compose.yml run --rm --no-deps rec-migrate \
    python scripts/verify_rls_hardening.py --production-read-only"
```

Expected:

- `production_rls_state_result=pass`.
- `live_production_probe=read_only_metadata`.
- `live_production_enforcement=enabled`.
- `covered_table_count` equals `rls_enabled_and_forced_count`.
- `failed_table_names=none`.

Read-only manual inspection command used during clarification:

```sh
ssh 2brain.dev "cd /opt/projects/2brain-rec && \
  docker compose -f infra/docker-compose.yml run --rm --no-deps rec-migrate alembic current && \
  docker compose -f infra/docker-compose.yml exec -T rec-postgres \
    psql -U twobrain_rec -d twobrain_rec -Atc \
    \"select c.relname || '=' || c.relrowsecurity || '/' || c.relforcerowsecurity \
      from pg_class c join pg_namespace n on n.oid=c.relnamespace \
      where n.nspname='public' and c.relkind='r' and c.relname not in ('alembic_version') \
      order by c.relname;\""
```

Expected:

- Alembic current is `0005_rls_hardening (head)` or a later revision that
  includes it.
- Every covered tenant-owned table reports `true/true`.
- The command reads metadata only and does not seed or mutate customer rows.

## 5. Stale-Language Scan

```sh
rg -n "not_changed|separate explicit operator decision|live production enforcement remains|not enabled" \
  specs/031-rls-hardening docs/current-product-status.md \
  docs/deployments/2brain-rec/rls-hardening-runbook.md \
  docs/adr/003-tenant-isolation-rls.md CHANGELOG.md \
  apps/server/src apps/server/scripts apps/server/tests
```

Expected:

- Remaining matches are either removed or explicitly scoped to historical
  `031` pre-production wording or test/disposable validation not touching live
  production.

## 6. Forbidden Content Scan

```sh
rg -n "transcript_text|signed_url|api_key|password|/Users/|/opt/projects|object_key" \
  specs/032-rls-live-enforcement docs/deployments/2brain-rec \
  apps/server/src apps/server/scripts apps/server/tests || true
```

Expected:

- No forbidden evidence content is introduced.
- Allowed matches are placeholder names, field names, or approved deployment
  paths, not live secrets or customer content.

## 7. Closeout Evidence

Final closeout must record:

- local/test gate result;
- production deployed commit;
- production Alembic revision;
- production covered table count;
- production RLS enabled/forced count;
- stale wording scan result;
- forbidden content scan result.

## 8. 032 Validation Results

Recorded on 2026-06-15 from branch `codex/032-rls-live-enforcement`.

Focused 032 RLS truth tests:

```text
31 passed
```

Full local CI:

```text
server tests: 336 passed, 4 skipped
server lint: pass
python compile: pass
rls hardening validation boundary: blocked without RLS_TEST_DATABASE_URL
production compose config: pass
deployment evidence scan: pass
ci_local_result=pass
```

Production read-only state inspection:

```text
remote_sha=3fd2162f9899
alembic_revision=0005_rls_hardening (head)
covered_table_count=28
rls_enabled_and_forced_count=28
failed_table_names=none
```

The production check used only PostgreSQL catalog metadata for the covered
table list. It did not seed, mutate, or read customer rows.

Stale-language scan result:

- Current product status, ADR, runbook, changelog, scripts, and command output
  no longer contain stale production-disabled or `not_changed` claims.
- Remaining matches are historical `031` spec/plan/analysis/code-review text
  or negative tests/scanner rules that intentionally block the stale wording.

Forbidden-content scan result:

- Remaining matches are approved deployment paths, code field names,
  placeholders, or negative tests for redaction behavior.
- `./infra/scripts/ci-local.sh` deployment evidence scan passed for
  `docs/deployments/2brain-rec`.
