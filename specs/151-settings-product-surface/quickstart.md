# Quickstart: Продуктовый раздел настроек

## 1. Focused source checks

```sh
python -m compileall -q apps/server/src/twobrain_rec_server
```

Run the focused settings/account/template tests from the repository test runner after locating the current marker:

```sh
rg -n "settings_category_navigation|render_settings_page|settings overview|settings navigation|AccountSettingsSurface" apps/server/tests tests
```

## 2. Browser matrix

Use the repository's credential-free cabinet/browser harness. Open:

- `/settings`
- `/settings/recording`
- `/settings/summaries`
- `/settings/integrations/calendar`
- `/settings/workspace`
- `/settings/account`
- `/settings/notifications`
- `/billing`

Check at `1280×720` and `390×844`:

1. Seven overview cards and truthful scope labels are present.
2. Active rail item has `aria-current="page"`.
3. No document-level horizontal overflow; only the mobile settings rail may scroll within its own region.
4. Account/notification forms still show server result copy after submit.
5. Recording and billing boundaries remain truthful.

## 3. Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Record the exact command and result in the implementation closeout. Do not run production deployment from this slice.

## Latest validation evidence

2026-08-16, high-risk UX lane, audit remediation:

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/test_settings_ui_contract.py tests/contract/test_billing_ui.py tests/contract/test_billing_accessibility.py tests/contract/test_account_routes.py tests/integration/test_billing_usability.py`: 78 passed.
- `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_account_lifecycle.py`: 8 passed; disposable container removed.
- `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_settings_ia_flow.py`: 4 passed; disposable container removed.
- `infra/scripts/ci-local.sh --fast`: 1088 passed, server lint passed, Python compile passed.
- `git diff --check`: passed.
- GitHub issue canon: `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py` passed for 260 Spec Kit issues.
