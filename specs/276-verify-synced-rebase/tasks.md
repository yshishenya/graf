# Tasks: проверяемое слияние

Umbrella: #7268. Владельцы задач GitHub: T001 #7269, T002 #7270,
T003 #7271, T004 #7272. До кода analyze: CRITICAL 0 / HIGH 0 / MEDIUM 0,
5/5 FR покрыты; 4/4 SC покрыты; несопоставленных задач нет.

## Phase 1: Setup and foundation

Спецификация, clarify, план и независимый infra checklist 6/6 готовы.
До кода: независимая сверка этих задач, analyze и GitHub ownership.
Новых зависимостей или окружения не требуется. Владелец кода/тестов: основной
агент; reviewer владеет только checklist и независимым отчётом.

## Phase 2: US1 — корректная история

Independent test: реальный synthetic Git graph 3+sync→3 и историческое движение
API base восстанавливают точную проверенную базу; сначала зафиксировать FAIL.

- [X] T001 [US1] Добавить положительную регрессию и сохранность refs/index/files в `tests/governance/test_pr_metadata_event.py` по FR-001/FR-005 и SC-001/SC-004.

## Phase 3: US2 — отказ при неполном доказательстве

Independent test: count/base, dropped/extra/reordered replay, repaired intermediate
tampering, final tree, manual sync/conflict, source merge/missing objects дают отказ.

- [X] T002 [US2] Добавить перечисленные отрицательные истории в `tests/governance/test_pr_metadata_event.py` по FR-002/FR-003 и SC-002, сохранив прежние ожидания.

## Phase 4: shared implementation

- [X] T003 [US1] Реализовать ограниченную пошаговую проверку в `scripts/validate-pr-metadata.py` после T001/T002; count 1..1000 остаётся неизменным; FR-001–005, без bypass и новых consumers.

## Phase 5: Validation and closeout

- [ ] T004 Пройти `specs/276-verify-synced-rebase/quickstart.md`, независимое implementation review и converge; записать evidence в `specs/276-verify-synced-rebase/validation.md` и `changes/unreleased/F276.yaml`; lane significant-feature/high-risk governance, SC-001–004, exact-SHA PR gates до merge и отдельный release-full до выпуска.

## Dependencies and strategy

T001 → T002 → T003 → T004. US2 задаёт обязательные защитные тесты до
реализации US1; положительная и отрицательная приёмка проверяются отдельно.
Один владелец общего файла тестов, параллельных правок нет. Независимое ревью
может идти параллельно read-only проверкам; исполнитель не редактирует его отчёт.
MVP — обе истории вместе: одной положительной проверки недостаточно для выпуска.
Технические изменения не попадают в публичные пользовательские release notes.
