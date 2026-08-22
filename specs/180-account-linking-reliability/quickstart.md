# Quickstart: Надёжное подключение способов входа

## Focused checks

```sh
cd apps/server
uv run pytest tests/contract/test_auth_contracts.py tests/contract/test_account_merge_contract.py tests/contract/test_account_routes.py
uv run pytest tests/integration/test_web_owner_session_context.py tests/integration/test_account_merge.py
uv run ruff check src/twobrain_rec_server/auth/provider_links.py src/twobrain_rec_server/api/auth.py src/twobrain_rec_server/cabinet
```

## Strict production-equivalent RLS

Run the focused strict-RLS provider-link test through the repository PostgreSQL
harness documented by `tests/integration/test_rls_postgres_policies.py`. The
test must use the exact app role with `NOBYPASSRLS` and prove both denied
ordinary request insert and successful bounded provider-link start context.

## Runtime UX matrix

1. Start from account settings in browser and embedded routes.
2. Capture direct-link, merge preview, blocker, stale proof, cancel and success.
3. Repeat at wide viewport and 390 px.
4. Check keyboard order, visible focus, heading/status semantics, one primary
   action and no horizontal overflow.
5. Use synthetic identities only; keep captures outside git and record only
   metadata-safe conclusions.

## One-personal-space merge checks

Run the focused merge/workspace checks through the repository PostgreSQL
harness:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_account_merge_contract.py \
  tests/integration/test_account_merge.py \
  tests/unit/test_workspace_onboarding.py
```

The acceptance path is: survivor has 4 meetings, source has 10, confirm the
merge, then the survivor personal space shows 14 meetings. Audio, transcript,
processing and summary rows stay attached to their meeting; no deduplication is
performed. Corporate memberships remain separate, and a source personal root
is removed when no dependent rows remain.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

No production deploy or commit is part of this quickstart.
