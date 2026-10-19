# Auth Navigation Requirements Checklist

**Purpose**: Проверить полноту, ясность и согласованность требований к
авторизации, сессии и native navigation до реализации.
**Created**: 2026-07-27
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are stable documents and one-shot transitions separately defined for persistence, recovery and history? [Completeness, Spec §Key Entities; FR-002–FR-003]
- [x] CHK002 Are both primary sign-in and authenticated provider-link flows included without treating them as the same session transition? [Completeness, Spec §User Story 1–3; Edge Cases]
- [x] CHK003 Are requirements stated for login success, logout, session expiry and workspace reselection? [Completeness, Spec §FR-004; Edge Cases]
- [x] CHK004 Are existing server methods, provider set and session storage explicitly outside scope? [Scope, Spec §Assumptions]

## Requirement Clarity And Consistency

- [x] CHK005 Is the prohibition on replayed one-shot actions unambiguous for method changes as well as duplicate submissions? [Clarity, Spec §FR-001; FR-003; FR-007]
- [x] CHK006 Are the safe-history requirements consistent for native buttons, browser gestures, automatic recovery and application restart? [Consistency, Spec §FR-002–FR-005; User Story 2]
- [x] CHK007 Is the timing of session-history removal specified relative to committing the stable target page? [Clarity, Spec §FR-004; Key Entities]
- [x] CHK008 Are requirements consistent in preserving normal meetings/settings navigation while blocking only transient or prior-session entries? [Consistency, Spec §FR-003; FR-006]

## Acceptance Criteria And Scenario Coverage

- [x] CHK009 Can each primary sign-in method be assessed for exactly-once action and a safe terminal outcome? [Measurability, Spec §User Story 1; SC-001–SC-002]
- [x] CHK010 Are Back, Forward and Reload requirements specified for both transient and ordinary documents? [Coverage, Spec §User Story 2; SC-003–SC-004]
- [x] CHK011 Are provider cancellation, form/server error, rate limiting and restart recovery covered as exception scenarios? [Edge Cases, Spec §Edge Cases; FR-008]
- [x] CHK012 Are the requirements explicit that no secrets, codes, cookies or meeting content enter diagnostics or evidence? [Security, Spec §FR-007; Assumptions]
- [x] CHK013 Are accessibility expectations specified for navigation controls whose availability changes by state? [Accessibility, Spec §FR-009]

## Dependencies And Assumptions

- [x] CHK014 Is the dependency on existing server-owned routes documented without requiring a server workaround? [Dependency, Spec §Assumptions; FR-007]
- [x] CHK015 Is the manual validation dependency bounded to test-only data and metadata-only evidence? [Assumption, Spec §Assumptions; SC-001]

## Актуализация 2026-10-17 — владелец отметок: независимый reviewer

Старые отметки являются архивными. Reviewer повторно проверяет каждый пункт,
меняет только checklist/report и указывает актуальные ссылки; исполнитель не
отмечает требования самостоятельно. `[x]` означает качество требований,
а не завершённую реализацию или ручную приёмку.

- [x] CHK016 Явно ли различаются текущий срез T005/T006/T010 и незавершённые требования OAuth/ручной приёмки всей F136? [Scope, Spec §Clarifications; Текущая приёмка и ограничения]
- [x] CHK017 Определено ли сохранение сессии для обычной формы при успехе, ошибке и отмене без повторной отправки? [Completeness, Spec §FR-001; FR-006; Текущая приёмка и ограничения]
- [x] CHK018 Согласованы ли отложенная успешная граница и немедленная защита при 401/выборе пространства, включая устаревший callback? [Consistency, Spec §FR-004; Текущая приёмка и ограничения]
- [x] CHK019 Отделены ли исходное воспроизведение ошибки, текущая автоматическая проверка и ручная приёмка с ограничениями стенда? [Measurability, Spec §Clarifications; Текущая приёмка и ограничения]

Все 19 пунктов, включая CHK001–CHK015, повторно проверены независимым
reviewer 2026-10-17. По каждому найдено текущее основание в
[checklist-review-20261017.md](../checklist-review-20261017.md).
Итог:19 checked/0 unchecked; runtime, OAuth и ручная приёмка не аттестованы.

Повторный независимый допуск перед исправлением stale callback — 2026-10-18:
[checklist-recheck-before-stale-fix-20261018.md](../checklist-recheck-before-stale-fix-20261018.md).
Все пункты заново проверены по текущим документам; отметки подтверждают
качество требований. Request Changes к реализации сохраняется.

## Допуск convergence T018 — 2026-10-18

- [x] CHK020 Однозначно ли различены безопасные корневые `/login` и `/sign-up` для истории/повторной загрузки/SwiftUI identity и вложенные auth actions, которые остаются допустимы текущему WebKit, но не сохраняются для повторного открытия? [Completeness, Spec FR-002–FR-003/FR-005; Data Model Stable document/Transient navigation; Research root-only decision; Tasks T018]

Повторно проверены все 20 пунктов, включая CHK001–CHK019. Обоснование,
сверка неизменных документов по SHA256 и допуск T018:
[checklist-review-before-t018-20261018.md](../checklist-review-before-t018-20261018.md).
Итог: 20 checked / 0 unchecked. Старое Request Changes по искусственному
callback order снято отдельным disposition report; это не PASS ещё не
реализованной T018 и не приёмка OAuth/ручной проверки.
