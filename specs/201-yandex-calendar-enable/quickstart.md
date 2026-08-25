# Quickstart: Яндекс Календарь

## Preconditions

```sh
specify --version
git status --short --branch
```

For automated database scenarios, start the repository disposable PostgreSQL
runner. Keep its URL in process environment only.

```sh
cd "$(git rev-parse --show-toplevel)"
bash apps/server/scripts/run_local_postgres_tests.sh
```

For real provider validation, use a dedicated Yandex test account and enter the
app password only into the authenticated local/browser form. Never put it in a
command, chat message, fixture, log or evidence file.

The local form is enabled by the canonical launcher:

```sh
cd "$(git rev-parse --show-toplevel)"
sh infra/scripts/start-local.sh
```

Then open `http://127.0.0.1:8081/settings/integrations/calendar`, sign in with
`local@graf.test` and code `000000`, choose `Яндекс Календарь`, and enter the
Yandex username plus app password in the dialog. This development-only form is
not production availability or real E2E certification.

## Focused automated checks

```sh
cd "$(git rev-parse --show-toplevel)/apps/server"
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_caldav_provider.py \
  tests/unit/test_calendar_worker.py \
  tests/unit/test_calendar_credentials.py \
  tests/unit/test_calendar_normalization.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/contract/test_calendar_settings_contract.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py
```

With PostgreSQL available, also run:

```sh
cd "$(git rev-parse --show-toplevel)/apps/server"
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_provider_runtime.py \
  tests/integration/test_calendar_provider_failures.py \
  tests/integration/test_calendar_disconnect_lifecycle.py \
  tests/integration/test_calendar_deletion_lifecycle.py \
  tests/integration/test_calendar_settings_flow.py \
  tests/integration/test_calendar_access_policy.py
```

## Real browser/embedded sequence

1. Open calendar settings in browser and embedded macOS.
2. Connect the dedicated Yandex account using username and app password.
3. Confirm the catalog appears only after provider validation.
4. Save one calendar; reload and confirm the selection.
5. Confirm the first sync starts as part of the successful Yandex connection;
   then select one calendar and verify selection triggers an immediate sync.
6. Run the settings sync button; verify the request waits for the provider read
   and returns a completed or safe failure state rather than only `queued`.
7. Verify an active selected Yandex source is eligible again five minutes after
   its last run; Google and disabled providers remain outside this scheduler.
8. Save zero calendars; confirm no upcoming/context rows are produced by that
  source.
9. Reconnect and verify no duplicate active source.
10. Disconnect, reload, repeat sync, and confirm fail-closed cleanup.
11. Confirm Record/Stop and upload remain available in every calendar state.

Record only the metadata required by
[yandex-certification.md](contracts/yandex-certification.md).

## Closeout

```sh
cd "$(git rev-parse --show-toplevel)"
infra/scripts/ci-local.sh
```

Do not run production
execute/deploy from this worktree without explicit release approval. If any
real E2E scenario fails, leave Yandex labeled `Скоро` and record the blocker.
