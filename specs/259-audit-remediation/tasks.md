# F259 — задачи этапа B019

Только US3 / FR-012–FR-018. Остальные 279 исходных issues остаются в backlog.md; T001–T006 не означают выполнение всего бэклога. Tracker: #6827; исходная ошибка F225 #6189 сохраняет отдельную приёмку.

## Подготовка

- [X] T001 [US3] Зафиксировать уточнение и план B019 в specs/259-audit-remediation/spec.md и plan.md; прочитать всех потребителей scripts/claim-feature.py. (Issue #6837)

## Исправление и проверка

- [X] T002 [US3] В tests/governance/test_feature_allocator.py воспроизвести service refs, завышенный номер, GitHub failure, конкурентное резервирование и отсутствие метки. (Issue #6837)
- [X] T003 [US3] Исправить scripts/claim-feature.py: refs, единый выбор, strict online и создание метки без перезаписи. (Issue #6837)
- [X] T004 [US3] Согласовать Bash/Python/PowerShell входы .specify/extensions/git/scripts и source overlay /Users/yshishenya/Documents/speckit-bootstrap/bin/speckit-bootstrap. (Issue #6837)
- [X] T005 [US3] Выполнить quickstart, review и convergence; записать реальные результаты/ограничения в specs/259-audit-remediation/validation.md и changes/unreleased/F259.yaml. (Issue #6837)
- [ ] T006 [US3] После разрешённого commit/PR получить governance-fast на exact SHA и согласовать исходные критерии F225 перед любым закрытием. (Issue #6837)

Зависимости: T001 → T002/T003 → T004 → T005 → T006. Независимых write owners нет; все изменения последовательные. Новых дублирующих child issues не создаётся.

## Дополнение: завершение workflow

- [X] T007 [US3] Проверить реальные PR/issue timelines, инструкции и Actions; зафиксировать причины в specs/259-audit-remediation/workflow-audit.md. (Issue #6837)
- [X] T008 [US3] Исправить .specify/workflows/speckit/workflow.yml и implement/taskstoissues skills; сохранить source bootstrap overlay. (Issue #6837)
- [X] T009 [US3] Добавить single-issue live проверку scripts/validate-issue-closeout.py и регрессии в tests/governance/test_validator_safety.py. (Issue #6837)
- [X] T010 [US3] Проверить workflow и отрицательные сценарии, дополнить validation.md; actual tracker closeout остаётся за evidence, PR и разрешёнными gates. (Issue #6837)

Зависимости: T007 → T008/T009 → T010 → существующий T006 (PR/CI). Другие направления бэклога не реализуются этим этапом.

## Завершение проверки PR

- [X] T011 [US3] Проверить полный повторяемый bootstrap существующего GRAF, сохранить настройки проекта и исправления F259, устранить известные migration blockers в source bootstrap PR #39; результаты записать в specs/259-audit-remediation/review.md. (Issue #6837)

T006: PR создан и governance-fast на исходном SHA прошёл. Исходные критерии F225 и закрытие issues остаются отдельным незавершённым этапом; снятие Draft не означает выполнение всего бэклога.


## Дополнительный review перед выпуском

- [X] T012 Устранить четыре замечания PR #6831 в scripts/claim-feature.py, .specify/workflows/speckit/workflow.yml и связях задач; проверить существующий umbrella, блокировку и подсказку Windows, остановку после convergence и task-backed ownership согласно FR-012–FR-022. (Issue #6837)

## Исправление распознавания занятых номеров

- [X] T013 [US3] Устранить замечание PR #6831 о пропуске существующих названий с `_` и `.` в scripts/claim-feature.py; в tests/governance/test_feature_allocator.py проверить реальные локальные/удалённые refs, specs и следующее предложение номера по FR-012/013; записать проверку в validation.md. (Issue #6837)

T013 уточняет действующее правило занятых номеров: распознаётся числовой префикс `NNN-`, ограничения генерации новых slug не применяются к уже существующим именам. Исключения служебных refs и timestamps сохраняются. План: регрессия → общий parser → целевые проверки → governance-fast на точном SHA PR. Авторский analyze: FR-012/013, план общего parser и T013 согласованы, новых требований и блокирующих неоднозначностей нет. Независимая приёмка US3 уже записана в review.md; общий checklist не изменяется. T006 остаётся отдельным условием закрытия.

## Восстановление последовательности без перенумерации

- [X] T014 [US3] Уточнить FR-023–FR-026/SC-006/007 в specs/259-audit-remediation/spec.md, plan.md и contracts/allocator.md; получить независимый checklist и синхронизировать существующий Issue #6837.
- [X] T015 [US3] Добавить регрессии исторического spec6788, правил политики, F1000+, инварианта занятости и общих входов в tests/governance/test_feature_allocator.py. (Issue #6837)
- [X] T016 [US3] Исправить общий старт поиска в scripts/claim-feature.py через .specify/feature-numbering.json; уточнить начало новой работы в docs/agent-guidance/codex-worktrees.md. (Issue #6837)
- [X] T017 [US3] Выполнить quickstart, review и converge; записать фактические результаты в specs/259-audit-remediation/validation.md и changes/unreleased/F259.yaml; оставшиеся commit/CI/merge gates не закрывать. (Issue #6837)

Порядок: T014 → T015 → T016 → T017 → T006. Изменения последовательные,
параллельных исполнителей кода нет. Это ремонт B019, не весь бэклог F259.
