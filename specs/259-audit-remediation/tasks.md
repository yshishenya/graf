# F259 — задачи этапа B019

Только US3 / FR-012–FR-018. Остальные 279 исходных issues остаются в backlog.md; T001–T006 не означают выполнение всего бэклога. Tracker: #6827; исходная ошибка F225 #6189 сохраняет отдельную приёмку.

## Подготовка

- [X] T001 [US3] Зафиксировать уточнение и план B019 в specs/259-audit-remediation/spec.md и plan.md; прочитать всех потребителей scripts/claim-feature.py. (Issue #6837)

## Исправление и проверка

- [X] T002 [US3] В tests/governance/test_feature_allocator.py воспроизвести service refs, завышенный номер, GitHub failure, конкурентное резервирование и отсутствие метки. (Issue #6837)
- [X] T003 [US3] Исправить scripts/claim-feature.py: refs, единый выбор, strict online и создание метки без перезаписи. (Issue #6837)
- [X] T004 [US3] Согласовать Bash/Python/PowerShell входы .specify/extensions/git/scripts и source overlay /Users/yshishenya/Documents/speckit-bootstrap/bin/speckit-bootstrap. (Issue #6837)
- [X] T005 [US3] Выполнить quickstart, review и convergence; записать реальные результаты/ограничения в specs/259-audit-remediation/validation.md и changes/unreleased/F259.yaml. (Issue #6837)
- [X] T006 [US3] После разрешённого commit/PR получить governance-fast на exact SHA и согласовать исходные критерии F225 перед любым закрытием. (Issue #6837)

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

T013 уточняет действующее правило занятых номеров: распознаётся числовой префикс `NNN-`, ограничения генерации новых slug не применяются к уже существующим именам. Исключения служебных refs и timestamps сохраняются. План: регрессия → общий parser → целевые проверки → governance-fast на точном SHA PR. Авторский analyze: FR-012/013, план общего parser и T013 согласованы, новых требований и блокирующих неоднозначностей нет. Независимая приёмка US3 уже записана в review.md; общий checklist не изменяется. T006 принят после исходной проверки F225 и GitHub CI; само закрытие требует включения PR в master.

## Восстановление последовательности без перенумерации

- [X] T014 [US3] Уточнить FR-023–FR-026/SC-006/007 в specs/259-audit-remediation/spec.md, plan.md и contracts/allocator.md; получить независимый checklist и синхронизировать существующий Issue #6837. (Issue #6837)
- [X] T015 [US3] Добавить регрессии исторического spec6788, правил политики, F1000+, инварианта занятости и общих входов в tests/governance/test_feature_allocator.py. (Issue #6837)
- [X] T016 [US3] Исправить общий старт поиска в scripts/claim-feature.py через .specify/feature-numbering.json; уточнить начало новой работы в docs/agent-guidance/codex-worktrees.md. (Issue #6837)
- [X] T017 [US3] Выполнить quickstart, review и converge; записать фактические результаты в specs/259-audit-remediation/validation.md и changes/unreleased/F259.yaml; оставшиеся commit/CI/merge gates не закрывать. (Issue #6837)

Порядок: T014 → T015 → T016 → T017 → T006. Изменения последовательные,
параллельных исполнителей кода нет. Это ремонт B019, не весь бэклог F259.

## Завершение B019 перед общим аудитом

- [X] T018 [US3] Согласовать генерируемый umbrella с каноном: область заголовка/метки и `Spec tasks: T000` в scripts/claim-feature.py; проверить готовое тело штатным валидатором в tests/governance/test_feature_allocator.py. (Issue #6837)
- [X] T019 [US3] Сверить исходные задачи F225, сохранить её потерянные из master документы в specs/225-feature-id-allocator, восстановить service-ref regression внутри --self-test и подготовить acceptance.md/связи issues и сверить исходные критерии; само закрытие требует последующего точного CI, слияния и штатного валидатора. (Issue #6837)

T018 следует существующему обязательному issue canon и FR-017/019–022, T019 реализует незавершённую приёмку T006 без изменения границ F225. Уточнение: T000 остаётся временной резервацией нового umbrella; перед закрытием получает реальную задачу. Анализ требований: переиспользуются общий generator и валидатор, новых схем или независимых источников номеров нет; исходные критерии F225 сохраняются. Порядок T018/T019 → T006.

## Итог B019 — 2026-09-10

T001–T019 выполнены в ограниченном объёме инструментов. Исходная приёмка F225 сверена в acceptance.md; governance-fast34391513703 PASS на2292e67fd043d357ece64defe52fc821b5f19349. Исторические записи об открытом T006 выше описывают прежние этапы. Финальный документационный commit требует обновлённого CI; merge и live closeout выполняются после него. Общий бэклог F259 остаётся открытым.

## Возврат к трёхзначным номерам — 2026-09-11

Продолжение US3/B019 по FR-027–029, SC-008/009. Исторический Issue #6837
остаётся закрытым; текущий ремонт связан с Issue #6938 и требует отдельного PR/CI evidence.

- [X] T020 [US3] Уточнить spec.md, plan.md, contracts/allocator.md и quickstart.md; проверить требования нового диапазона и общего номера до реализации. (Issue #6938)
- [X] T021 [US3] Добавить регрессии каскада больших specs, границы, ошибок и claims в tests/governance/test_feature_allocator.py; исправить scripts/claim-feature.py и .specify/feature-numbering.json. (Issue #6938)
- [X] T022 [US3] Согласовать spec creation и pointer в .agents/skills/speckit-specify/SKILL.md, .specify/scripts/bash/create-new-feature.sh и source bootstrap; сохранить контрольные суммы генерируемых файлов. (Issue #6938)
- [X] T023 [US3] Проверить quickstart, записать validation.md и changes/unreleased/F259.yaml; выполнить converge, отделить локальную готовность от commit/CI/merge. (Issue #6938)
