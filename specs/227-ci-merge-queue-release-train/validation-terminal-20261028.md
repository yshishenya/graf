# F227 T014: приоритет известного неуспеха задания CI

Дата: 28.10.2026. Ветка `codex/227-terminal-receipt-status`, исходная основа
`908670770cffe1c3e26fd1212c2837bd1bfeb229`. Lane: `Active Spec Kit slice`.
Владелец: T014 / #6221; общая issue #6207. Это локальная проверка, до нового
PR и его обязательных проверок. Выпуск и развёртывание не выполнялись.

## Причина и минимальное исправление

Terminal step `governance-fast.yml` раньше учитывал JOB_STATUS только при
отсутствии локального файла. Сохранённый PASS перекрывал уже известные
failure/cancelled. Теперь любое известное этому шагу состояние, отличное от
success, использует существующее terminal evidence. Причина указывает момент
формирования, а не утверждает, что локального evidence ещё не было.
Исходный локальный файл сохраняется. При success локальные non-success не
повышаются до PASS; отсутствие файла или неизвестное состояние не дают PASS.

Прочитаны оба рабочих вызова `emit-ci-receipt.py`: governance-fast и
release-full. Последний сначала проверяет component/SHA/skips/coverage и
валидирует новое authoritative evidence; ошибочную ветку выбора старого PASS
не использует. Producer, consumer, схемы, защита GitHub, приложение и данные
не изменены. Новых зависимостей или параллельных механизмов нет.

## Исходный отказ и итог

Добавлена одна параметризованная исполняемая проверка в существующий файл:
4 состояния задания × 7 состояний локального файла × 2 способа поиска = 56.
Задание: success/failure/cancelled/unknown. Локальные состояния: отсутствие,
passed/failed/stale/cancelled/superseded/ambiguous. Путь — явный либо найденный
по target SHA. Исполняются неизменённый извлечённый YAML step, настоящий CLI
`emit-ci-receipt.py` и оба настоящих validator.

Проверяются status/conclusion, cancellation/supersession, cleanliness, SHA/base,
PR/run/attempt, digest выбранного файла и неизменность исходного файла.
Корректный terminal non-success принимается как metadata-only receipt, но
отвергается как release evidence. Статус superseded поддержан receipt adapter;
схема локального release evidence им не расширяется.

| Этап | Выбранных уникальных случаев | PASS | FAIL | SKIP | Время |
|---|---:|---:|---:|---:|---:|
| Существующие четыре файла до нового теста | 311 | 311 | 0 | 0 | 60.55 с |
| Новая матрица до изменения workflow | 56 | 20 | 36 | 0 | 5.61 с |
| Те же четыре файла после исправления | 367 | 367 | 0 | 0 | 68.72 с |

Числа и уникальность подтверждены сохранёнными JUnit XML, а не только строкой
pytest. Исходный RED сохранён до изменения двух строк workflow. Никакие
исходные проверки не удалены. Команда итогового профиля:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/governance/test_governance_workflow.py \
  tests/governance/test_ci_event_identity.py \
  tests/governance/test_ci_evidence_producer.py \
  tests/governance/test_pr_checks.py
```

Самопроверка governance workflow, проверки agent-context, development-process,
Spec Kit governance и `git diff --check`: PASS. Локальный общий fast/full не
запускался: профиль покрывает изменённое поведение, а обязательный PR gate
выполнится в GitHub. macOS сборка для двух строк CI не требуется локально;
её применимость определяет существующий macos-pr. Настоящая отмена GitHub
не моделируется как проведённая операция; это исполнение кода с синтетическими
входами во временных каталогах pytest.

## Сверка реализации с требованиями

`speckit-converge`, текущая область T014: FR-004/FR-006/SC-002, US2/AC4 и
три решения плана сопоставлены с кодом и 56 случаями. Конституционные
metadata-only и exact-SHA ограничения сохранены. Новых missing/partial/
contradicts/unrequested задач в этой области нет; новые задачи не добавлены.
Это не общая сходимость F227: существующие T015/T016/T028/T029/T030/T031
и общая issue остаются открытыми. Исходные 33 описания/ID/порядок сохранены;
отмечена только локальная реализация T014. Hooks converge не настроены,
автоматические commit hooks implement отключены.

`validate-pr-checks.py` отдельно требует фактические успешные run и job,
проверяет SHA/base/attempt и повторно читает источники перед PASS. Поздняя
ошибка или отмена после формирования receipt остаётся его обязанностью;
ранняя квитанция не доказывает окончательный успех. Обход слияния/выпуска
не установлен. Схема/consumer не ослабляются ради завершения задачи.

## Контрольные суммы

Операторский каталог проверки за 27.10.2026 содержит журналы и JUnit XML;
они не включают данные встреч. SHA-256 проверенной версии:

```text
191f01fc6837a7486f3ed6220b5cd6cc7e2d5966932678f5208686a87d54f0b5  .github/workflows/governance-fast.yml
d81cb9e6874bafa2214a8d47059fc1386df4b1a819c168c12527473f111ce6a4  tests/governance/test_governance_workflow.py
da1f72ade8ea2a9ba57efcfbc87a01912eef6c0af0e2040d39d6766177f8e98f  f227-terminal-red-20261028.log
a0fc576a6cd29e1faf3f11e8c41942c2315f80bd5353255b829b3ec2819a8615  f227-terminal-red-20261028.xml
c76d2412e886002a39f7dd4f619704d2a2295af43bedb445147bd5a6174c4b45  f227-terminal-green-20261028.log
fce54229bbea84f3dd03a22cb06a6ad10e90c029ad10f50f7378fffc5fb00223  f227-terminal-green-20261028.xml
```

Независимое предреализационное ревью: requirements 16/0, infra 13/0, blockers 0.
Итоговое ревью кода и результатов, новый PR, exact-SHA/base gates, слияние и
индивидуальная live-проверка #6221 ещё требуются. Окно соседнего frozen
выпуска сохраняется; текущий срез туда не включён.
