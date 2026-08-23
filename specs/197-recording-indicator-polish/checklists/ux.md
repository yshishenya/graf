# UX Requirements Checklist: Деликатный индикатор источника записи

**Purpose**: Проверить полноту и измеримость визуального, accessibility и
clean-room контракта до реализации.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates the requirements, not the implementation.

## Visual hierarchy

- [X] CHK001 В спецификации задано, что верхний индикатор остаётся одной внешней плашкой, а источник — вторичной подписью внутри неё [Clarity, Spec §FR-001, FR-004]
- [X] CHK002 Для известного приложения задан точный вид подписи `Источник · <name>`, без отдельного фона, рамки, иконки или клика [Completeness, Spec §FR-002, FR-004]
- [X] CHK003 Для ручного, неизвестного и завершённого состояний определены честные значения и граница показа [Coverage, Spec §FR-003, FR-007, Edge Cases]
- [X] CHK004 Однострочность, tail truncation, bounded layout и сохранность Stop сформулированы как измеримые критерии [Measurability, Spec §FR-005, SC-003]

## Accessibility and resilience

- [X] CHK005 Полное имя источника задано отдельно от визуального сокращения через accessibility label и системную подсказку [Accessibility, Spec §FR-006, SC-004]
- [X] CHK006 Требования защищают отдельные Pause/Resume/Stop controls, keyboard reachability, increased contrast и Reduce Motion [Coverage, Spec §FR-009, Edge Cases]
- [X] CHK007 Переходы active, paused, degraded и stopping покрыты требованием стабильности источника [Consistency, Spec §FR-001, Edge Cases]

## Brand distance and scope

- [X] CHK008 Требования используют существующую GRAF titlebar surface и не вводят чужую карточку, app icon или новый interaction pattern [Consistency, Spec §FR-004, Out of Scope]
- [X] CHK009 Явно исключены process polling, per-frame attribution, network, storage, telemetry и capture-route changes [Scope, Spec §FR-008, Out of Scope]

## Notes

No requirement gaps found. The intended visual move is deliberately small:
remove the duplicate sidebar presentation and add one quiet source label to the
existing upper indicator.
