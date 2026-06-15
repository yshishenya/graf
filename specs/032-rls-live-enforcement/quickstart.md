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

With a disposable or explicit test database:

```sh
RLS_TEST_DATABASE_URL="$RLS_TEST_DATABASE_URL" \
  python3 apps/server/scripts/verify_rls_hardening.py
```

Expected:

- Direct SQL RLS probes pass.
- Destructive probes run only on the disposable/test database.
- `RLS_TEST_DATABASE_URL` pointing at live `twobrain_rec` remains blocked.

## 4. Production Read-Only State Inspection

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
