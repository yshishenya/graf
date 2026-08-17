# UX Requirements Checklist: Непрерывная навигация кабинета

**Purpose**: Проверить, что UX/accessibility требования shared shell измеримы и
покрывают web, embedded, keyboard и narrow states.
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] Toggle, search, profile, download and settings rail requirements покрывают browser и embedded surfaces. [Spec §FR-001–FR-010]
- [x] Для каждого ключевого control описаны normal, alternate, error/empty и recovery states. [Spec §Edge Cases]
- [x] Узкий viewport, dark/light, reduced motion, keyboard и visible focus включены в acceptance и success criteria. [Spec §FR-014, SC-002–SC-005]

## Requirement Clarity

- [x] Stable location, next-action label, `aria-expanded` и `aria-controls` определены без расплывчатого «понятный». [Spec §FR-001–FR-002]
- [x] Количество CTA и navigation landmarks задано как exact one/zero, а не «не дублировать». [Spec §FR-004, FR-008, SC-001, SC-003, SC-005]
- [x] Profile menu boundaries и focus-return semantics отделены от настоящей modal focus trap. [Spec §FR-006]

## Scenario Coverage

- [x] Pointer, Enter, Space, Escape, outside click, repeated partial initialization и missing/long profile values явно покрыты. [Spec §US1, Edge Cases]
- [x] Settings category, calendar, account alias и canonical return-to-meetings flows определены. [Spec §US2, FR-010]
- [x] Download availability и embedded native update ownership не смешаны с meeting artifact downloads. [Spec §FR-004, contracts]

## Clean-room and Localization

- [x] Public references используются только для принципов interaction/accessibility; GRAF copy, iconography и composition остаются оригинальными. [research.md]
- [x] Russian user-facing labels, accessible names and degraded states являются обязательными. [Spec §FR-014]

## Notes

- Checklist checks requirement quality, not implementation pass/fail; runtime proof is defined in `quickstart.md`.
