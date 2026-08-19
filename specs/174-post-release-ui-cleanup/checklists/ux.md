# UX Requirements Quality Checklist: Пострелизная очистка интерфейса

**Purpose**: Проверить полноту, ясность и измеримость UX/accessibility требований до реализации
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Определены ли поддерживаемые ширины и обе поверхности для responsive sidebar? [Completeness, Spec §SC-001]
- [x] CHK002 Определены ли видимость, размер цели и интерактивность профиля в узком embedded-состоянии? [Completeness, Spec §FR-001]
- [x] CHK003 Описаны ли все compact controls, которые должны делить одну ось, включая optional update/download? [Completeness, Spec §FR-002]
- [x] CHK004 Определён ли единственный navigation owner для каждой production settings surface и HTMX fragment? [Completeness, Spec §FR-005–FR-006]
- [x] CHK005 Определены ли native inspector states, position, hit target и accessibility semantics? [Completeness, Spec §FR-009]

## Requirement Clarity

- [x] CHK006 Квантифицированы ли sidebar widths, control sizes и допустимое отклонение центров? [Clarity, Spec §FR-001–FR-003]
- [x] CHK007 Явно ли разделены удаляемый dead tooltip contract и сохраняемый видимый/accessibility hint? [Clarity, Spec §FR-008]
- [x] CHK008 Явно ли указано, какая часть Feature 173 superseded, а какая остаётся действующей? [Clarity, Spec §FR-007, Assumptions]
- [x] CHK009 Определено ли «без регрессий» через измеримые geometry, overflow, navigation-count и interaction outcomes? [Clarity, Spec §SC-001–SC-004]

## Requirement Consistency

- [x] CHK010 Согласованы ли 64/176px widths и 40×40px controls между user stories, requirements, success criteria и UI contract? [Consistency, Spec §FR-001–FR-003]
- [x] CHK011 Согласовано ли удаление inner navigation с сохранением outer settings model и active state? [Consistency, Spec §FR-005–FR-007]
- [x] CHK012 Не конфликтует ли удаление wrapper с требованием сохранить native inspector geometry и scroll behavior? [Consistency, Spec §FR-009–FR-011]

## Scenario And Edge-Case Coverage

- [x] CHK013 Покрыты ли pre-ready state, page zoom, missing profile name и optional footer actions? [Coverage, Spec §Edge Cases]
- [x] CHK014 Покрыты ли full-page и fragment settings responses без изменения auth/CSRF/role boundaries? [Coverage, Spec §US2, FR-006]
- [x] CHK015 Покрыты ли pointer, keyboard, visible focus и same-coordinate repeated toggle flows? [Coverage, Spec §US1–US3]
- [x] CHK016 Определено ли поведение при constrained native window и длинной локализованной accessibility copy? [Coverage, Spec §Edge Cases]

## Acceptance Criteria Quality

- [x] CHK017 Можно ли объективно измерить profile visibility, target bounds, axis tolerance и horizontal overflow? [Measurability, Spec §SC-001]
- [x] CHK018 Можно ли объективно измерить единственный navigation landmark и active settings link? [Measurability, Spec §SC-002]
- [x] CHK019 Определяет ли spec обязательную rendered/computed проверку, способную поймать исходный 0×0 defect? [Measurability, Spec §FR-010, SC-004]
- [x] CHK020 Ограничены ли release/deploy/full-CI действия так, чтобы validation lane не обещал лишнего? [Scope, Spec §SC-006, Out of Scope]

## Notes

- Checklist complete: requirements sufficiently define UX, accessibility, responsive and non-regression boundaries for implementation.
