# F259 — точная связь CI с повторным PR, 2026-10-16

Полоса: high-risk-product / significant governance, существующая US3.
Основа: c6c5441c930b8c1ecffed6de9b80773aa0e757e5.
Ветка: codex/259-ci-proof-binding. Задачи T027–T029, issue #7644.
Общий бэклог F259 и пользовательская приёмка F267 остаются открытыми.

## Причина и решение

PR #7123 и прежний #7059 имеют один head:
751d52a9381f8db2b2464dd5fcccfcbf4c7e480d. У governance run35139578748
массив pull_requests пуст. Общий validate-pr-checks.py подтверждает #7123
и отвергает #7059 с code receipt identity mismatch, но дополнительный
commit lookup в validate-issue-closeout.py ошибочно отвергал #7123.

Из verify_feature_runs удалён только commit fallback/cache и единственный
неиспользуемый helper. Непустая противоречащая связь самого запуска
остаётся отказом. Обязательный _github_pr_checks по точным PR/head/run
вызывает прежний полный валидатор с --expected-sha и --code-run-id;
тот проверяет head/base/run/attempt, workflow/event/path, jobs, актуальность
метаданных и подлинность артефактов. Общий валидатор не менялся.
Кэш точного полного доказательства сохраняется для нескольких issues.
Новых флагов, исключений конкретной фичи и зависимостей нет.

## Последовательность и проверки

- Clarify/spec/plan/quickstart согласованы до кода; analyze текущего объёма:
  7 требований, 3 задачи, покрытие 100%, CRITICAL0/HIGH0. Синхронизация
  добавила только (Issue #7644); смысл задач не менялся. Повторный анализ
  после этой привязки: новых противоречий или пропусков нет.
- Независимая проверка всех пяти списков: 43 отмечено / 0 не отмечено.
  checklists/pr-run-binding.md: 8/0. Исполнитель отметки не менял.
- Canon ensure PASS; post-sync validate PASS (300 возвращённых Spec Kit issues).
  Дополнительно отдельная живая #7644 и её обратные ссылки проверены reviewer.
  Историческая #7631 не переоткрывалась и не получила новый код.
- Направленная регрессия до исправления: 1 failed / 53 deselected,
  ожидаемый отказ is not uniquely bound to PR #6383. После исправления:
  1 passed / 53 deselected. Ошибочное прежнее ожидание commit-only отказа
  заменено PASS с проверкой точного обязательного полного proof вызова.
- Полные test_validator_safety.py + test_pr_checks.py: 189 passed /20.23s.
  Независимый повтор: 189 passed /19.99s, ошибок/пропусков нет.
- Пустая API-связь при missing/expired, чужом и устаревшем proof даёт отказ;
  для двух issues одного PR/head/run полный proof вызывается один раз.
- self-test validate-issue-closeout.py PASS. Ruff двух Python-файлов PASS.
  Development-process, agent-context, changelog-fragments, legacy-impact,
  check_spec_kit_governance.py и git diff --check PASS.
- AST-сравнение: 13 других функций валидатора неизменны, изменена только
  verify_feature_runs, удалена _github_commit_pull_requests, новых функций нет.
  validate-pr-checks.py и test_pr_checks.py побайтно не менялись.

## Живое повторение без записи GitHub

Временный локальный JSON #7020 содержит только предложенный комментарий.
На одинаковом JSON и неизменном tasks F267:

- До исправления single/live FAIL: run35139578748 is not uniquely bound to PR #7123.
- После исправления single/live PASS. Настоящий полный валидатор проверил
  #7123, head751d52a..., base7e60fba40f491a833d52257bfce5fc1d352b362c,
  mergeb74b3d99333c6314711abfaa2151f69c79c9a9c5 и три CI-доказательства:
  governance-fast35139578748, macos-pr35139578778, pr-metadata35139577566.
- Отдельный прежний #7059 с тем же head и governance-run даёт exit1:
  code receipt identity mismatch. То есть общий SHA не разрешает чужой PR.

Журналы находятся во внешнем реестре:
/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/checks/
F259-pr-binding-red.log, F259-pr-binding-green.log,
F259-pr-binding-full-tests.log, F259-pr-binding-live-before.log,
F259-pr-binding-live-after.log, F259-pr-binding-wrong-pr-after.err.
Reviewer прочитал живые журналы, сам сетевой повтор не запускал.
Синтетическая подмена _github_pr_checks проверяет вызов, не подлинность CI.
Никакой предложенный комментарий #7020 не опубликован; issue не закрыта.

## Независимое ревью и converge

review-implementation-pr-run-binding-20261016.md: PASS, замечаний0.
Сверка уточнения: 7 требований FR-007/008/020–022, SC-003/004;
3 решения плана (общий proof/cache, удаление commit lookup, сохранение отказов);
конституционные III/VI. Пропусков реализации выбранного объёма нет,
новых задач реализации не требуется. Общая F259 не объявляется converged.

## Оставшиеся условия

Изменения не закоммичены. Требуется отдельное разрешение implementation
commit и чернового PR после этой проверки, затем обязательные GitHub
checks на точном итоговом SHA и разрешённое слияние. #7644 остаётся OPEN.
Закрытие F267 требует принятого исправления и проверки каждого исходного
критерия; этот отчёт её пользовательское поведение не принимает.
На Mac34GiB; крупные сборки, приложение, Docker, живой стенд и production
не запускались и не изменялись. Пользовательские данные не читались.
