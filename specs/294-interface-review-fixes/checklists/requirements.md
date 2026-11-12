# Requirements Checklist: Исправления после ревью интерфейса

**Purpose**: Проверить полноту, однозначность и проверяемость требований перед реализацией.
**Created**: 2026-11-12
**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned requirements-quality artifact.
**Marker Semantics**: `[x]` — критерий проверен и выполнен; это не означает завершение реализации.

## Completeness

- [x] CHK001 Определены ли все состояния записи, в которых доступен Stop/Pause? [Completeness, Spec §US1]
- [x] CHK002 Определено ли поведение при `.stopping`, `.degraded` и `.failed` для панели, titlebar, меню и accessibility? [Completeness, Spec §FR-002, FR-003]
- [x] CHK003 Определены ли fallback и объяснение для отсутствующего сохранённого микрофона? [Completeness, Spec §FR-004]
- [x] CHK004 Определено ли поведение при отключении системного микрофона во время записи? [Completeness, Spec §FR-005]
- [x] CHK005 Определён ли порядок очистки storage, уведомления и перезагрузки кабинета? [Completeness, Spec §FR-006]
- [x] CHK006 Определено ли обновление строк записей при смене часового пояса? [Completeness, Spec §FR-007]
- [x] CHK007 Определены ли состояния меню-бара recording/degraded/failed? [Completeness, Spec §FR-008]
- [x] CHK008 Определены ли все пять разделов фолбэка настроек и действие «Все настройки»? [Completeness, Spec §FR-009, FR-010]
- [x] CHK009 Определены ли требования к frame окна: минимум и видимая область? [Completeness, Spec §FR-011]
- [x] CHK010 Определены ли критерии удаления мёртвого кода без потери поведения? [Completeness, Spec §FR-012, FR-020]

## Clarity

- [x] CHK011 Однозначно ли, что `⌘0` принадлежит только сбросу масштаба? [Clarity, Spec §FR-001]
- [x] CHK012 Уточнено ли, что считается «доступным действием» для VoiceOver? [Clarity, Spec §FR-002]
- [x] CHK013 Уточнено ли, когда сохранённый микрофон очищается, а когда остаётся? [Clarity, Spec §FR-004]
- [x] CHK014 Уточнено ли, что очистка storage должна завершиться до перезагрузки? [Clarity, Spec §FR-006]
- [x] CHK015 Уточнено ли, какие тексты статусов являются единственным источником? [Clarity, Spec §FR-013]

## Consistency

- [x] CHK016 Согласованы ли требования к Stop между панелью, titlebar, меню и accessibility? [Consistency, Spec §FR-002, FR-003]
- [x] CHK017 Согласованы ли требования к смене аккаунта с приватностью и удалением? [Consistency, Spec §FR-006, FR-019]
- [x] CHK018 Согласованы ли требования к меню-бару с typed presentation? [Consistency, Spec §FR-008, FR-013]
- [x] CHK019 Согласованы ли требования к удалению мёртвого кода с сохранением локального буфера и analytics scaffold? [Consistency, Spec §Legacy Impact]

## Acceptance Quality

- [x] CHK020 Измеримо ли отсутствие конфликтующих shortcut-ов? [Measurability, Spec §SC-001]
- [x] CHK021 Проверяемо ли поведение Stop/Pause без привязки к точному тексту? [Measurability, Spec §SC-002]
- [x] CHK022 Проверяемо ли обновление строк при смене часового пояса? [Measurability, Spec §SC-005]
- [x] CHK023 Проверяемо ли отсутствие неиспользуемых presentation-полей? [Measurability, Spec §SC-006]
- [x] CHK024 Определены ли release/deploy evidence и public health? [Measurability, Spec §SC-007]

## Notes

- Отмечать `[x]` только при наличии evidence в spec/plan.
- Неподтверждённые пункты оставлять `[ ]` с причиной в отчёте ревью.
