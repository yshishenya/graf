# Payment Security Requirements Checklist: Billing presentation

**Purpose**: Проверить, что visual redesign не ослабляет money, auth и desktop boundaries
**Created**: 2026-08-29
**Feature**: [spec.md](../spec.md)

## Server and money authority

- [x] CHK001 Остается ли `POST /billing/checkout/start` единственной initial money-mutation точкой? [Boundary, Spec §FR-009–FR-010]
- [x] CHK002 Зафиксировано ли, что preview не создает invoice, operation, promo reservation или provider request? [Boundary, Spec §FR-009]
- [x] CHK003 Сохранены ли owner, auth, CSRF, RLS, catalog, emergency stop, consent, idempotency и rate-limit requirements? [Completeness, Spec §FR-010]
- [x] CHK004 Сохраняются ли raw promo normalization/hash, one-discount policy и checkout revalidation? [Data Security, Spec §FR-009–FR-010]
- [x] CHK005 Блокирует ли pending/unknown/reconciliation/manual-resolution конкурентную новую оплату? [Concurrency, Spec §FR-011]

## Data and external navigation

- [x] CHK006 Исключены ли provider secrets, payloads, raw payment data, private reference/account data и signed URLs из UI/evidence? [Privacy, Spec §FR-003, §Out of Scope]
- [x] CHK007 Сохраняются ли safe invoice number, masked method и allowlisted receipt/provider URL projections? [Trust Boundary, Data model]
- [x] CHK008 Остаются ли `/offer` sanitization и YooKassa checkout-origin/HTTPS-host allowlist неизменными? [Desktop Boundary, Desktop contract]
- [x] CHK009 Не расширяется ли exact desktop route allowlist и fail-closed unknown-sibling policy? [Desktop Boundary, Spec §FR-017]

## Failure and release boundaries

- [x] CHK010 Требуют ли unavailable/stale/store-disabled states скрывать или отключать monetary actions без guessed data? [Fail Closed, Spec §FR-012]
- [x] CHK011 Разделены ли non-mutating local/installed-app QA и отдельно разрешаемая реальная оплата/provider mutation? [Release, Spec §Out of Scope]
- [x] CHK012 Зафиксирован ли запрет commit/release/deploy и real payment без отдельного явного разрешения? [Authorization, Plan §Release Gate]
