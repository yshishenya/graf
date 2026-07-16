# Validation

```sh
cd apps/server
uv run pytest tests/integration/test_web_owner_session_context.py \
  tests/integration/test_rls_postgres_policies.py
cd ../..
infra/scripts/ci-local.sh
```

The PostgreSQL test requires the existing disposable RLS test database setup.
