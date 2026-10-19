# Tasks: F230 — восстановленный план и безопасное делегирование

**Input**: spec/plan/research/data-model/contracts/quickstart этой фичи.
**Prerequisites**: независимый design review 18/18; перед реализацией повторный
review этого tasks, analyze и taskstoissues. Номера исходных задач сохранены.
T021 добавлена при повторной сверке 2026-10-19: отдельный владелец операторского применения.
**Risk lane**: significant-feature, governance. **Umbrella**: #6314.

Это реконструкция, не оригинальные потерянные байты. Полная таблица T001–T020,
включая 12 отменённых NOT_PLANNED дублей с преемниками, — `recovery.md`.
Отменённые задачи не имеют фиктивных completed checkboxes и не исполняются заново.

## Phase 1: Setup — источник и договорённости

- [X] T001 Зафиксировать allocator/enforcement contracts, data model, exact base SHA и источники всех исходных задач в `specs/230-process-enforcement/{plan.md,research.md,data-model.md,recovery.md,recovered-source-index.json,contracts/}`; отметить реконструкцию и действующих преемников. (Issue #6315; umbrella #6314)
- [X] T002 Добавить metadata-only changelog fragment `changes/unreleased/F230.yaml` без изменения root CHANGELOG.md; отдельным результатом назвать только текущий срез. (Issue #6316; umbrella #6314)

## Phase 2: Foundational — ворота до реализации

- [X] T017 Выполнить speckit-analyze текущих `specs/230-process-enforcement/{spec.md,plan.md,tasks.md}` с конституцией; устранить Critical/High, не менять reviewer-owned checklist; сохранить read-only результат в журнале проверки. (Issue #6331; umbrella #6314)
- [X] T018 Выполнить speckit-taskstoissues для `specs/230-process-enforcement/tasks.md`: сверить прежние восемь issues, canon/labels и отсутствие дублей, не создавать повторные задачи. Для добавленной T021 после нового analyze и поиска дублей найти или создать ровно одного отдельного владельца до реализации поправок. (Issue #6332; umbrella #6314)

## Phase 3: User Story 1 — существующие механизмы (P1)

Новая реализация US1 не назначается: результаты исходных T003–T012/T014–T015
уже имеют проверенных владельцев в F216/F227/F234/F235 (`recovery.md`).
**Independent Test**: четыре существующих context/allocator набора и self-tests
из quickstart; все SKIP перечисляются. Они не закрывают F216/F227 или US2.

## Phase 4: User Story 2 — наблюдение и операторский переход (P1)

**Goal**: наблюдаемый rehearsal и explicit rollback без автоматического изменения защиты.
**Independent Test**: реальные события/receipt на точной версии плюс сравнение
GET protection/rulesets/effective rules до/после; неизвестный сценарий не PASS.

- [ ] T013 [US2] Подготовить observe-only rehearsal report и explicit rollback procedure в `specs/230-process-enforcement/{contracts/observe-only-rollout.md,validation/enforcement-observation-20261016.md}`; подтвердить реальные PR/manual/merge_group сценарии и before/after; required checks не включать автоматически. Неподтверждённый сценарий оставляет задачу открытой. (Issue #6327; umbrella #6314)

## Phase 5: User Story 3 — границы агентов (P2)

**Goal**: исследователь возвращает summary/evidence, исполнитель имеет одного
владельца/рабочую копию; чужие изменения и пределы approvals сохранены.
**Independent Test**: пять положительных/отрицательных сценариев из quickstart,
дополнительно reviewer checklist исключение и запрет передачи секретов/контента.

- [X] T016 [US3] Добавить одну секцию в `docs/agent-guidance/development-process.md` и маршрут к ней в `docs/agent-guidance/README.md`: read-only исследование, назначение executor/owner/worktree/owned paths, конфликт/новый scope и краткий evidence handoff; пройти пять сценариев и независимое итоговое ревью, результаты записать в `specs/230-process-enforcement/validation/agent-delegation-20261016.md`. (Issue #6330; umbrella #6314)

## Phase 6: Final validation and convergence

- [ ] T019 Выполнить `specs/230-process-enforcement/quickstart.md`, governance checks и `infra/scripts/ci-local.sh --fast` на финальном чистом exact SHA; проверить три required GitHub checks через `scripts/validate-pr-checks.py`; сохранить пределы и результаты в `specs/230-process-enforcement/validation/agent-delegation-20261016.md`. Dirty diagnostics, исходный base или чужой PR не заменяют финальные checks. (Issue #6333; umbrella #6314)
- [X] T020 Выполнить speckit-converge всего `specs/230-process-enforcement/{spec.md,plan.md,tasks.md}`: новые пробелы добавлять только append-only в этот tasks.md; известные открытые T013/T019 не дублировать, operator-owned gates явно сохранить. (Issue #6334; umbrella #6314)

## Дополнения по повторной сверке 2026-10-19

- [ ] T021 [US2] Оператор F230 после принятой T013 выполняет согласованный переход required checks/режима слияния по `specs/230-process-enforcement/contracts/observe-only-rollout.md`; сохраняет точные before/after, разрешение, реальное испытание и проверку отката в `specs/230-process-enforcement/validation/operator-cutover.md`. Если защита уже включена, сначала проверить историю её перехода и остаток; повторно включать её ради отчёта нельзя. Отсутствие платформенного merge queue оставить открытым ограничением до принятого решения владельца; отсутствие доказательства не считать выполнением. (Issue #7662; umbrella #6314)

## Dependencies & Execution Order

`design review → tasks → independent task review → T001 → T017 → T018 → T002`.
После этих ворот T013 и T016 независимы; отсутствие реального merge_group не
разрешает T013, но не блокирует письменную процедуру T016. Затем focused checks,
независимое итоговое ревью и T020; T019 завершить только после разрешённого commit
на чистом SHA и PR checks. T021 выполняется только после принятой T013 и
подготовленного конкретного операторского действия/отката; T019 её не заменяет.
Перед любым изменением design/tasks анализ и review
актуализируются. К реализации перейти только после полного PASS обязательных ворот.

## Parallel Opportunities

Наблюдение T013 только чтением может идти отдельно от T016 в другом явно назначенном
задании. В этой работе файлы пишет один владелец; reviewer может менять только
custom checklist и свой отчёт. Нет основания создавать параллельных writers одного файла.

## Implementation Strategy

Сначала восстановление и review/analyze/sync, затем минимальный текст T016 и
фрагмент T002. Никакого нового orchestrator/parser/framework, root/generic копий
правил, runtime изменения или включения GitHub settings. Успешная локальная
проверка US3 — не закрытие issues до разрешённого commit, точных PR checks и merge.
Точное операторское применение и разрешение отменённых задач в общем closeout
остаются проверяемыми требованиями всей фичи, без специального исключения F230.

## Legacy Impact

`untouched`: новые compatibility paths, aliases, flags и dependencies отсутствуют.
