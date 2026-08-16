# Audio Capture Requirements Checklist: Источник системного звука в индикаторе записи

**Purpose**: Проверить полноту и правдивость требований на границе capture и видимого статуса.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates the requirements, not the implementation.

## Capture Truth

- [X] CHK001 Требования различают подтверждённое имя приложения, общий системный звук и неизвестный источник [Completeness, Spec §FR-002–FR-004]
- [X] CHK002 Требования запрещают угадывание приложения и отдельное per-process определение, если capture-контракт этого не подтверждает [Clarity, Spec §FR-009]
- [X] CHK003 Зафиксировано, что источник не меняет маршрут, разрешения, дорожки и время старта записи [Consistency, Spec §SC-005]

## Lifecycle And Failure States

- [X] CHK004 Описано сохранение источника на этапах подготовки, записи, паузы, деградации и остановки [Coverage, Spec §FR-005]
- [X] CHK005 Описаны пустое, неизвестное и ручное значения источника с явным fallback-текстом [Edge Case, Spec §Edge Cases]
- [X] CHK006 Требования сохраняют видимый индикатор и one-action Stop при добавлении информационной строки [Safety, Spec §FR-006]

## Privacy And Scope

- [X] CHK007 Явно исключены аудиосодержимое, сетевой вызов, телеметрия, история источников и новый persisted field [Privacy, Spec §FR-009, Assumptions]
- [X] CHK008 Граница первой версии ограничена верхним локальным индикатором, без выбора источника и advanced routing [Scope, Spec §Assumptions]

## Notes

No requirement gaps found. Per-process audio attribution is intentionally deferred because display-wide system audio does not provide a truthful single-app guarantee in the current MVP.
