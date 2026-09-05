# Проверка F242

Prerequisites: Python3.12 с project dependencies, node. Не использовать dev/prod DB. Только synthetic/in-memory данные; screenshots вне git.

```sh
env -u TWOBRAIN_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_billing_ui.py apps/server/tests/contract/test_billing_accessibility.py apps/server/tests/contract/test_billing_security.py apps/server/tests/contract/test_billing_rls.py apps/server/tests/unit/test_cabinet_navigation_model.py apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/contract/test_cabinet_static_assets_contract.py apps/server/tests/contract/test_recording_workflow_accessibility.py apps/server/tests/contract/test_settings_ui_contract.py apps/server/tests/unit/test_trial.py apps/server/tests/unit/test_cabinet_audit_fixes.py -o addopts='' -p no:cacheprovider
```

Expected: PASS. Preferences: theme-only/full/invalid/empty/org mismatch/stale menu; trial: terms before submit, precise preview/actual dates, checkout independence; profile all billing routes/deletion full pages; help with/without email/history rows; decimal boundaries; pending hooks.

Browser: changed-worktree synthetic renders wide/390px, light/dark, keyboard/no-JS trial; реальный POST trial не выполнять. Theme form без locale/timezone; history anchor к контакту; pending без повтора recovery. Общий dev stack не перезапускать.

Closeout: correctness/Ponytail review, converge, governance checks. Authoritative PR gate — governance-fast exact SHA; full CI/deploy N/A. Implementation commit после validation и explicit approval; merge не выполнять.
