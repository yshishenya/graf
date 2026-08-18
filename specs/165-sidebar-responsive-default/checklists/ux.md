# UX Requirements Checklist: Адаптивное стартовое состояние боковой панели

**Purpose**: Проверить responsive navigation, accessibility и clean-room UX
**Created**: 2026-08-18
**Feature**: [spec.md](../spec.md)

## Responsive interaction

- [x] CHK001 Are wide and narrow browser outcomes defined in terms of navigation discoverability? [IA, Spec §US1]
- [x] CHK002 Does the spec explain why embedded 721–1120 px starts in compact mode? [Responsive, Spec §Edge Cases]
- [x] CHK003 Is one stable toggle, rather than a second control, required across states? [Consistency, Spec §FR-005]

## Accessibility and visual quality

- [x] CHK004 Are keyboard focus, `aria-expanded`, label/icon parity and reduced-motion expectations stated? [Accessibility, Spec §FR-005–FR-006]
- [x] CHK005 Are resize and partial-initialization expectations clear without implying persistence? [Trust, Spec §FR-004]
- [x] CHK006 Are no-overflow, theme and clean-room constraints represented as observable acceptance outcomes? [Visual, Spec §SC-002–SC-005]

## Notes

Responsive state выбирается CSS-aligned breakpoint decision; persistence и
новая onboarding surface намеренно не добавляются.
