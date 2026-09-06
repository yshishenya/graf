# UX Requirements Checklist: Playback layout

**Purpose**: Проверить полноту требований перед реализацией
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

## Layout completeness

- [x] CHK001 Определено ли разделение scroll-area и playback для основного сценария? [Completeness, Spec §FR-001–FR-002]
- [x] CHK002 Определены ли границы панели для collapsed и expanded sidebar? [Completeness, Spec §FR-003]
- [x] CHK003 Описано ли изменение доступной высоты при resize timeline? [Coverage, Spec §FR-004]
- [x] CHK004 Определено ли поведение страниц без playback? [Edge Case, Spec §FR-006]

## Responsive and accessibility coverage

- [x] CHK005 Указаны ли web, desktop-embedded, wide, narrow и short viewport состояния? [Coverage, Spec §FR-005]
- [x] CHK006 Сохранены ли требования к keyboard, focus и reduced-motion? [Coverage, Spec §FR-007]
- [x] CHK007 Определены ли degraded playback states и stacking overlays? [Edge Case, Spec §Edge Cases]

## Measurability and scope

- [x] CHK008 Можно ли объективно измерить отсутствие пересечения и совпадение границ? [Measurability, Spec §SC-001–SC-002]
- [x] CHK009 Ограничен ли scope layout-изменением без редизайна controls и backend? [Clarity, Spec §Out of Scope]
- [x] CHK010 Зафиксировано ли отсутствие новой frontend dependency? [Constraint, Spec §FR-008]
