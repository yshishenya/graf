# Quickstart

Из feature worktree, в существующем pytest environment, без production записей:

```sh
python3 -m pytest -q tests/governance/test_pr_metadata_event.py
python3 -m pytest -q tests/governance/test_pr_checks.py tests/governance/test_pr_scope.py
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7257
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7256
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7267
python3 scripts/check-development-process.py
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Положительная регрессия сначала FAIL, после исправления PASS. Все заданные
плохие истории отвергнуты; старые ожидания не ослаблены. Если имена consumers
отличаются, выбрать реальные файлы через rg. Не устанавливать зависимости глобально.
Ни локальный PASS, ни ошибка API/неоконченный CI не заменяют required checks
и один frozen release-full. Проверки GitHub только читают данные.
