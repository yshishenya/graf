# Quickstart: проверка боковой навигации настроек

Run from the repository root:

```sh
cd /Users/yshishenya/.codex/worktrees/0d70/crisp
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_provider_link_settings_contract.py \
  tests/unit/test_cabinet_web_shell.py
cd ../..
git diff --check
```

Expected results:

- browser and embedded settings renders contain all five actionable links;
- group headings appear in the declared order;
- exactly one link per `data-settings-nav` ID exists and each category page has
  exactly one selected settings item; the overview has no false selection;
- the settings rail contains a working `Назад` return link, including on
  narrow browser layouts where the global cabinet sidebar is hidden;
- calendar settings preserve a 24px rail/content gap after all later CSS rules;
- calendar/provider-link surfaces keep their active settings item and full-shell
  or fragment contracts;
- existing scope, CSRF and safe-output assertions remain green;
- `git diff --check` reports no whitespace errors.

Closeout gate:

```sh
infra/scripts/ci-local.sh --fast
```

Latest verification: the focused settings/shell suite passed with 24 tests;
the full macOS suite passed with 643 tests; and
`infra/scripts/ci-local.sh --fast` passed with 859 server unit tests, lint and
Python compile. Calendar
integration/contract tests were not run in this environment because they
require `TWOBRAIN_DATABASE_URL` and the repository's local Postgres runner.

Do not run production deploy for this implementation slice. A later release
must pass the documented release gate and CD dry-run first.
