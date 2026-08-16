# UX Requirements Checklist: Источник системного звука в индикаторе записи

**Purpose**: Проверить полноту и измеримость визуального, accessibility и clean-room контракта.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates the requirements, not the implementation.

## Visual Hierarchy

- [X] CHK009 Точное место строки задано внутри существующего верхнего индикатора, а статус и Stop явно имеют больший приоритет [Clarity, Spec §FR-001, FR-006]
- [X] CHK010 Для строки заданы single-line layout, truncation, отсутствие переполнения и сохранение минимальной интерактивной высоты [Measurability, Spec §FR-007, SC-003]
- [X] CHK011 Состояния known app, «Системный звук» и «Источник не определён» имеют различимые и честные тексты [Completeness, Spec §FR-002–FR-004]

## Accessibility And Resilience

- [X] CHK012 Требования покрывают полное имя через accessibility label и системную подсказку при визуальном сокращении [Coverage, Spec §FR-007, SC-004]
- [X] CHK013 Требования явно включают повышенный контраст, keyboard actions и независимость от анимации [Accessibility, Spec §FR-008, SC-004]
- [X] CHK014 Existing Pause, Resume and Stop actions защищены от слияния или потери из-за новой строки [Consistency, Spec §FR-008]

## Brand Distance And Scope

- [X] CHK015 Требования используют существующую GRAF capture surface и не вводят вторую панель или чужой визуальный паттерн [Consistency, Spec §FR-006, Assumptions]
- [X] CHK016 Неинтерактивный источник явно отделён от действий: нет скрытого выбора, изменения маршрута или новой настройки [Scope, Contract]

## Notes

No requirement gaps found. The visual contract stays deliberately compact and native to the existing capture status card.
