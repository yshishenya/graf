# UX Requirements Checklist: Надёжная навигация кабинета

**Purpose**: Проверить полноту UX, accessibility и error-state требований
общей панели навигации.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md)

## Interaction and state coverage

- [x] Требования описывают состояние каждой из четырёх кнопок: Домой, Назад, Вперёд и Обновить. [Completeness, Spec FR-004–FR-005]
- [x] Для каждой кнопки определены доступное состояние, действие и причина отключения. [Clarity, Contract]
- [x] Loading, cancel, failure и no-safe-history состояния явно описаны. [Coverage, Edge Cases]
- [x] Back/forward сценарии с дублирующимися URL имеют измеримый ожидаемый результат. [Measurability, Spec US1–US2]
- [x] Требования согласованы между календарями, настройками, встречами и billing. [Consistency, Spec FR-007]

## Accessibility and localization

- [x] Для всех четырёх элементов сохранены стабильные labels, hints, shortcuts и identifiers. [Coverage, Spec FR-006]
- [x] Loading state имеет понятную доступную формулировку и не оставляет интерактивные действия доступными. [Accessibility, Spec US3]
- [x] Текст «Вперёд» не обещает действие, если безопасного следующего экрана нет. [Truthfulness, Spec US2]
- [x] Размер и единая визуальная группировка верхней панели не требуют отдельного redesign. [Consistency, Assumption]

## Security and recovery UX

- [x] Пользовательский fallback после небезопасной истории определён и не ведёт на auth/external экран. [Recovery, Spec FR-003]
- [x] Истёкшая сессия и protected routes имеют fail-closed границу. [Security, Contract]
- [x] «Домой» остаётся явным recovery path, когда back history недоступна. [Recovery, Spec US3]

## Notes

- Чеклист требований закрыт до реализации; он проверяет полноту спецификации,
  а не заменяет runtime smoke и XCTest.
