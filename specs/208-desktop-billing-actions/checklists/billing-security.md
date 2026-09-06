# Requirements Checklist: Desktop Billing Security

**Purpose**: Проверить полноту и однозначность требований к desktop billing boundary перед реализацией
**Created**: 2026-08-28
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Определён ли полный источник перечня поддерживаемых billing-действий? [Completeness, Spec §Assumptions]
- [x] CHK002 Описаны ли требования для preview, начала checkout, promo, trial, subscription, payment method и status recovery? [Coverage, Spec §FR-001]
- [x] CHK003 Зафиксировано ли отсутствие изменений server-side billing semantics и production-конфигурации? [Scope, Spec §FR-004–FR-005]

## Requirement Clarity

- [x] CHK004 Ограничен ли allowlist точными текущими действиями без разрешения всего `/billing` namespace? [Clarity, Spec §FR-002]
- [x] CHK005 Определено ли правило безопасного динамического номера операции? [Clarity, Spec §FR-003]

## Scenario and Edge-Case Coverage

- [x] CHK006 Описано ли ожидаемое поведение неизвестных static и dynamic sibling-маршрутов? [Edge Case, Spec §FR-002, §FR-007]
- [x] CHK007 Сохранены ли требования к CSRF, auth, tenant, idempotency и launch gates после разрешения навигации? [Security, Spec §Edge Cases]
- [x] CHK008 Определено ли, что query и fragment не расширяют allowlist? [Security, Spec §Edge Cases]

## Acceptance and Release Quality

- [x] CHK009 Измеримы ли положительный и отрицательный route-coverage outcomes? [Measurability, Spec §SC-001–SC-002]
- [x] CHK010 Отделена ли code-level проверка без платежа от отдельного подписанного release и test-shop smoke? [Release, Spec §SC-003–SC-004, §Assumptions]
