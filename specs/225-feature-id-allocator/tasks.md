# Tasks: Надёжный allocator свежих Feature ID

## Phase 1: Setup and contracts

- [X] T001 [P] Зафиксировать service-ref boundary и governance checklist в `specs/225-feature-id-allocator/research.md` и `specs/225-feature-id-allocator/checklists/requirements.md`. (Issue #6190)
- [X] T002 [P] Добавить metadata-only changelog fragment `changes/unreleased/F225.yaml`. (Issue #6191)

## Phase 2: User Story 1 — Fresh number

**Independent test**: allocator игнорирует high numeric Codex capture ref и возвращает ближайший product ID.

- [X] T003 Изменить `_ids_from_refs` в `scripts/claim-feature.py`, исключив `codex/turn-diffs/captures/`. (Issue #6192)
- [X] T004 Добавить regression/self-test для service ref и normal feature branch в `scripts/claim-feature.py` и `tests/governance/test_validator_safety.py`. (Issue #6193)

## Phase 3: User Story 2 — Collision safety

**Independent test**: existing claim/GitHub validation продолжает отклонять занятую feature.

- [X] T005 [US2] Проверить local/remote/spec/GitHub collision paths и offline/strict semantics targeted tests. (Issue #6194)
- [X] T006 [US2] Обновить quickstart с командой проверки свежего номера и запретом ручного угадывания. (Issue #6195)

## Final Phase: Validation

- [X] T007 Запустить self-test, governance tests, обязательный GitHub `governance-fast`, analyze и converge на exact SHA. (Issue #6196)

## Dependencies

`T001,T002 → T003 → T004 → T005,T006 → T007`.

## Legacy Impact

`untouched`: служебная фильтрация не добавляет legacy runtime path.

## Итоговая приёмка исходного umbrella

- [X] T008 Сопоставить все исходные критерии #6189 с реализацией и матрицей acceptance.md, подготовить проверку точного SHA и штатный live closeout после дочерних задач; включение в master проверяется отдельно перед закрытием. (Issue #6196; umbrella #6189)

Задачи перенесены из сохранённой рабочей копии F225 для сверки в общем PR F225/F259. Её незакоммиченные изменения не менялись. Исторические отметки не заменяют новую приёмку; доказательства текущей проверки — acceptance.md и PR.
