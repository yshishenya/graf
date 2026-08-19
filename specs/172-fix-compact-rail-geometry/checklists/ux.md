# UX Requirements Checklist: Цельная геометрия compact rail

**Purpose**: Проверить ясность, полноту и измеримость UX/accessibility требований
до реализации
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Определены ли требования к общей оси для toggle, navigation и
  profile? [Completeness, Spec §FR-001]
- [x] CHK002 Определены ли одинаковые bounds для active, hover и focus states?
  [Completeness, Spec §FR-002–FR-003]
- [x] CHK003 Описаны ли compact и expanded states без смешения их требований?
  [Completeness, Spec §FR-004–FR-007]
- [x] CHK004 Описаны ли web и embedded surfaces, wide manual и narrow responsive
  состояния? [Coverage, Spec §FR-004]

## Requirement Clarity And Measurability

- [x] CHK005 Заданы ли размеры control и допустимая погрешность общей оси
  численно? [Clarity, Spec §SC-001–SC-002]
- [x] CHK006 Можно ли объективно отличить компактный active state от прежней
  широкой смещённой плашки? [Measurability, Spec §SC-002]
- [x] CHK007 Определено ли «то же место toggle» через проверяемое действие двух
  кликов без движения указателя? [Clarity, Spec §SC-003]

## Consistency And Accessibility

- [x] CHK008 Согласованы ли geometry requirements с текущими product widths и
  историческим baseline? [Consistency, Spec §Assumptions]
- [x] CHK009 Определены ли keyboard, accessible name и visible focus требования
  для всех compact actions? [Coverage, Spec §FR-008, §SC-004]
- [x] CHK010 Определены ли требования к отсутствию clipping, overlap и horizontal
  overflow? [Coverage, Spec §FR-008]

## Edge Cases And Boundaries

- [x] CHK011 Описаны ли titlebar safe area, long identity, missing optional
  actions и partial initialization? [Edge Cases, Spec §Edge Cases]
- [x] CHK012 Ясно ли исключены icon redesign, breakpoint/state changes, new
  persistence и unrelated product surfaces? [Scope, Spec §Out of Scope]
- [x] CHK013 Определено ли отсутствие пустого hidden header slot как отдельный
  acceptance signal? [Coverage, Spec §FR-005, §SC-005]

## Notes

- Standard depth for author and PR reviewer. Focus: shared geometry,
  responsive consistency, accessibility and explicit scope boundaries.
- All 13 requirement-quality items pass before implementation.
