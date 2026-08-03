# Quickstart: проверка боковой навигации настроек

Run from the repository root:

```sh
cd /Users/yshishenya/.codex/worktrees/0d70/crisp
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_settings_ui_contract.py \
  tests/integration/test_settings_ia_flow.py \
  tests/contract/test_calendar_settings_contract.py \
  tests/contract/test_provider_link_settings_contract.py \
  tests/unit/test_cabinet_web_shell.py
cd ../..
git diff --check
```

Expected results:

- browser and embedded settings renders contain all six canonical links;
- group headings appear in the declared order;
- exactly one link per `data-settings-nav` ID exists and the requested page has
  exactly one selected settings item;
- the settings rail contains a working `Мои встречи` return link, including on
  narrow browser layouts where the global cabinet sidebar is hidden;
- calendar settings preserve a 24px rail/content gap after all later CSS rules;
- calendar/provider-link surfaces keep their active settings item and full-shell
  or fragment contracts;
- existing scope, CSRF and safe-output assertions remain green;
- `git diff --check` reports no whitespace errors.

Closeout gate:

```sh
infra/scripts/ci-local.sh
```

Latest verification: the focused suite passed with 72 tests; the full CI gate
passed with 2460 parallel server tests, 42 strict server tests, and 642 macOS
tests. The RLS hardening step remains an explicit `postgres_test` boundary and
reports that a live production database is required for production truth.

Do not run production deploy for this implementation slice. A later release
must pass the documented release gate and CD dry-run first.
