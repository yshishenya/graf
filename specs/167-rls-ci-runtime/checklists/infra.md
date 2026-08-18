# Infrastructure Requirements Checklist: Надёжный RLS release gate

**Purpose**: Проверить полноту требований к release-readiness, disposable
границам и безопасному отказу до реализации.

**Created**: 2026-08-18

**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] Требование явно разделяет project-managed runtime и системное окружение. [Spec §FR-001]
- [X] Описаны успешный disposable path и оба blocking path: отсутствующий URL и production database name. [Spec §FR-002, §FR-003]
- [X] Зафиксирован порядок release gate stages и продолжение после RLS pass. [Spec §FR-004]
- [X] Описаны cleanup database и temporary probe role для success и failure paths. [Spec §FR-006, Edge Cases]

## Requirement Clarity

- [X] Термин disposable database ограничен loopback-only и исключает `twobrain_rec`. [Spec §Key Entities]
- [X] Metadata-only boundary перечисляет запрещённые классы вывода без требования к содержимому встречи. [Spec §FR-005]
- [X] Критерии успеха задают измеримые результаты (100%, 0 и exact commit). [Spec §SC-001–SC-005]

## Requirement Consistency

- [X] Fail-closed security requirement согласован с разрешением pass path только для disposable URL. [Spec §User Story 1–2, §FR-002–FR-003]
- [X] Cleanup requirement не расширяет полномочия RLS probe и не меняет production schema. [Spec §Key Entities, Assumptions]

## Scenario And Recovery Coverage

- [X] Основной release path, dependency failure, missing configuration, production-target rejection и interrupted-run cleanup описаны. [Spec §User Stories, Edge Cases]
- [X] Rollback/deploy scope отделён от runner fix и оставлен отдельному release gate. [Spec §Assumptions, Plan §Release Gate]

## Dependencies And Assumptions

- [X] Зафиксировано, что server dependencies уже объявлены в существующем lockfile. [Spec §Assumptions]
- [X] Production deploy approval и exact-SHA full gate явно остаются внешними условиями closeout. [Plan §Validation Plan, Quickstart §5]

## Notes

- Это checklist качества требований; executable checks находятся в `quickstart.md` и `tasks.md`.
