# Quickstart: F230

## Prerequisites

Активные branch/pointer F230/#6314 и текущий source SHA; requirements и custom
governance checklist проверены независимо; analyze без Critical/High. Чужие
рабочие изменения сохранены. Для чтения GitHub достаточно существующего gh;
никаких новых разрешений/секретов не получать. Scope US3 не запускает приложение.

## Проверка источников и gates

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 scripts/validate-agent-context.py
python3 scripts/check-development-process.py
python3 scripts/validate-changelog-fragments.py
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Сверить recovered-source-index/recovery/tasks: T001–T020 ровно по одному разу,
12 отменённых дублей имеют действующих преемников, 8 исполняемых задач — прежние
issues. Изменения source/state после снимка перечитать до решения о закрытии.

## Пять сценариев инструкции (US3)

| Сценарий | Ожидаемое решение | Отрицательный случай |
|---|---|---|
| Только чтение | вывод + точные источники + ограничения, без изменений | нужный тест пишет файлы: передать исполнителю, не расширять роль |
| Исполнение | одно задание/владелец/worktree и явные owned paths/проверки | соседний чужой файл нельзя присвоить молча |
| Пересечение | приостановить пересекающиеся записи, согласовать handoff | нельзя reset/revert чужую работу или писать параллельно один файл |
| Новый scope | сообщить факт, получить новое явное назначение | найденная проблема не даёт автоматического права исправлять |
| Приёмка ответа | основной агент сверяет фактическое evidence и полномочия | чужой PASS/диалог не заменяет независимое ревью и user approval |

Проверить путь новой сессии: AGENTS.md → docs/agent-guidance/README.md →
development-process.md → секция делегирования. Для read-only/docs/mechanical
задания без фичи достаточно repository/SHA/lane и явного N/A; выдуманный ID — FAIL.
Для активной фичи отсутствие feature/task IDs — FAIL.

Reviewer дополнительно разбирает границу исключения checklist/report и запрет
утечки секретов/содержимого встреч. В отчёте указать по каждой строке конкретную
норму итоговой инструкции; отсутствие нормы — FAIL. Число PASS не означает
измерение поведения всех будущих агентов.

## Существующие проверки общих механизмов (US1)

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/governance/test_validator_safety.py tests/governance/test_agent_context_update.py tests/governance/test_feature_allocator.py tests/governance/test_feature_identity_guidance.py
python3 scripts/claim-feature.py --self-test
python3 scripts/validate-agent-context.py --self-test
```

Все пропуски перечислить; PowerShell без pwsh остаётся SKIP, не PASS. Это не
проверка product runtime, release или настоящего merge_group.

## Наблюдение (US2)

По contracts/observe-only-rollout.md получить GET protection/effective rules/rulesets
и существующие runs. Сравнить protections до/после; сохранять точные metadata.
Не менять settings, не запускать workflow и не создавать PR ради наблюдения.
Случаи без реального evidence оставить в T013/#6327 открытыми.

## Финальная приёмка

После независимого итогового ревью и converge сохранить результаты/пропуски,
запросить разрешение на проверенный implementation commit. Только после commit
на чистом SHA выполняются финальный fast и три требуемые GitHub проверки
`governance-fast`, `macos-pr`, `pr-metadata` через `scripts/validate-pr-checks.py`.
`infra/scripts/ci-local.sh --fast` — отдельный fallback/diagnostic, его отсутствие
не заменять dirty receipt. В исходной T019 он указан как финальный gate и остаётся
открытым до согласованного исполнения на чистой проверенной версии.
Merge запрашивается отдельно; closeout имеет подробный русский комментарий и
live validator. F230 umbrella не закрывается с непроверенным US2 или прочим остатком.
