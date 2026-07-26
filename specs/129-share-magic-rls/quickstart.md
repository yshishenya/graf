# Quickstart: invitation magic-link RLS hotfix

## Focused validation

From the repository root:

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh -q \
  apps/server/tests/contract/test_recording_share_invitation_contract.py \
  apps/server/tests/contract/test_recording_share_ui_contract.py \
  apps/server/tests/integration/test_recording_share_public_link.py
```

The focused matrix must cover first-entry email magic-link acceptance, the
pending-audit/context-switch regression, existing identity, replay,
wrong-recipient, expiry/revoke and notification failure without unexpected 500.

The strict-RLS boundary regression is also required:

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh -q \
  apps/server/tests/integration/test_rls_postgres_policies.py::test_share_magic_link_flushes_audit_before_source_workspace_context
```

## Repository gate

```sh
git diff --check
infra/scripts/ci-local.sh
```

The repository gate must pass before PR/merge. Evidence remains metadata-only.

Validation snapshot for this slice: focused invitation matrix `23 passed`;
full `infra/scripts/ci-local.sh` passed with macOS `640 passed`, server
`2440 passed / 1 skipped`, strict PostgreSQL `42 passed / 1 skipped`, lint,
compile, Compose and deployment evidence scan.

## Production gate

```sh
infra/scripts/cd-remote.sh --dry-run --branch <immutable-deploy-branch>
infra/scripts/cd-remote.sh --execute --branch <immutable-deploy-branch>
```

Production execution requires explicit release approval and must report backup,
restore rehearsal, migration verification, disposable RLS, production smoke,
automatic dispatch, rollback readiness and public live/ready checks. After
deploy, inspect sanitized invitation logs and verify the exact deployed SHA.
