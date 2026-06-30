# Quickstart: Ponytail Refactor Audit

## Prerequisites

- Work from `codex/071-ponytail-refactor`.
- Preserve unrelated dirty files unless the user explicitly approves staging or cleanup.
- Do not run deploy commands for this slice.

## 1. Confirm Active Feature

```sh
SPECIFY_FEATURE_DIRECTORY=specs/071-ponytail-refactor .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: JSON points to `specs/071-ponytail-refactor` and lists `tasks.md`.

## 2. Baseline Static Checks

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests
cd apps/server && PYTHONPATH=src uv run --with vulture --extra dev vulture src tests --min-confidence 80
find apps/server/src apps/server/tests apps/macos infra scripts -type f -name '*.js' -print0 | xargs -0 -n1 node --check
find apps/macos infra scripts .specify/scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

Expected: default lint/syntax checks pass. Vulture or extended Ruff findings are candidate inputs, not automatic deletion instructions.

## 3. Validate Batch A

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_admin_permissions.py tests/unit/test_app_lifecycle.py tests/unit/test_media_revision_persistence_order.py tests/unit/test_cabinet_view_models.py tests/unit/test_cabinet_web_shell.py tests/integration/test_minio_upload_storage.py tests/integration/test_recording_sync_conflicts.py tests/integration/test_rls_auth_conflict_handling.py tests/integration/test_web_owner_session_context.py::test_browser_email_login_wrong_code_consumes_state
infra/scripts/ci-local.sh
cd apps/macos && swift test
git diff --check
```

Expected: focused server tests pass, `ci_local_result=pass`, Swift tests pass, and diff check is clean.

## 4. Validate Future Server Batch

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q <focused tests for touched domain>
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests
infra/scripts/ci-local.sh
```

Expected: focused tests and repository gate pass before the batch is complete.

## 5. Validate Future macOS Batch

```sh
cd apps/macos && swift test --filter <focused test filter>
cd apps/macos && swift test
```

Expected: focused and full Swift package tests pass.

## 6. Closeout

Record:

- Completed batches.
- Removed dependencies/files/symbols.
- Retained high-risk candidates.
- Validation commands and results.
- Confirmation that production deploy was not run.
