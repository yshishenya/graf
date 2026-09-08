# Почему завершённая разработка оставляет issues открытыми

Проверено 2026-09-08 по GitHub API, текущим инструкциям и workflow. База e81b412dff920cc29ed37de60be13dd8fc4d1c43; исправления находятся в локальном diff F259.

## Подтверждённые причины

1. В 11 из 12 последних merged PR (#6792, #6791, #6790, #6785, #6784, #6762, #6661, #6610, #6609, #6589, #6581) нет closing keywords, есть Refs. Refs показывает связь, но не закрывает issue. Это не означает, что каждый такой Refs ошибочен: часть задач действительно ожидает release/hardware/ручной приёмки.
2. .specify/workflows/speckit/workflow.yml назывался Full SDD Cycle, но исполнял только specify/review/plan/review/tasks/implement. В нём отсутствовали clarify/checklist/analyze/taskstoissues/converge и завершающая сверка. Документы описывали более полный процесс, чем фактический workflow.
3. speckit-implement завершался проверкой локальных задач и тестов; speckit-taskstoissues создавал/дедуплицировал issues, но не имел режима закрытия принятых. After-implement hooks содержат только выключенный auto-commit. Возврат к трекеру зависел от отдельного ручного действия агента.
4. GitHub Actions governance-fast работает на PR/merge_group/manual и имеет read-only permissions. Release-full запускает выпусковые проверки. Ни один из активных workflows не выполняет post-merge issue reconciliation. check-development-process вызывает лишь self-test validate-issue-closeout, не проверку фактических issues конкретного PR. Наличие валидатора не означает его автоматический запуск.
5. Структурный single-issue режим валидатора проверял текст, tasks и форму ссылок; live PR/run проверка была доступна только общей фиче. Эта граница легко пропускалась при закрытии отдельных задач.

## GitHub автозакрытие работает

[PR #6491](https://github.com/yshishenya/graf/pull/6491) merged в 2026-09-04T11:46:32Z. [Issue #6489](https://github.com/yshishenya/graf/issues/6489) closed в 11:46:33Z; GraphQL ClosedEvent.closer прямо указывает PullRequest #6491. Default branch — master. Это подтверждает работу штатного механизма GitHub.

В PR #6582 GitHub распознаёт шесть closingIssuesReferences, но их closedAt предшествует mergedAt и closer отсутствует. Этот случай не использован как доказательство автоматического закрытия при merge.

Историческое ограничение GitHub на частые комментарии объясняло отдельную остановку массового аудита, но не системное отсутствие завершающего этапа.

## Исправление локального процесса

- Проектный workflow теперь содержит полный цикл, проверку analyze, gate приёмки/слияния/выпуска, taskstoissues closeout и финальную сверку. Он не заканчивается на implement.
- Closeout mode перечитывает существующие задачи и не создаёт новые issues; полный результат проходит содержательную проверку и live PR/run verification, комментарий, повторную проверку фактического issue, закрытие и read-back. Umbrella последняя; rate limit сохраняет конкретный остаток.
- При незавершённой приёмке результат — implementation ready; tracker pending, с причиной по каждой задаче. Наличие [X] само по себе не разрешает закрытие.
- Добавлен --verify-live для проверки одного issue через существующую verify_feature_runs. Команда не изменяет GitHub и не подтверждает вместо человека hardware/runtime критерии.
- Соответствующие изменения навыков/workflow сохранены в source speckit-bootstrap; проектная замена workflow включается только в репозиториях с validate-issue-closeout.py. GitHub Actions не получает новых write permissions.

## Что остаётся до применения

Изменения ещё не закоммичены и не включены в master. Уже запущенные задачи и старые рабочие копии автоматически не получают новые инструкции. Нужны review/commit/PR, обновление закреплённых generated artifacts штатным процессом и governance-fast на exact SHA; затем новый workflow используется для последующих этапов. Этот аудит не закрывал исходные issues и не выдаёт отсутствие приёмки за выполнение.
