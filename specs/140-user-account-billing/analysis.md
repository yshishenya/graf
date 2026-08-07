# Cross-artifact analysis — 2026-08-07

## Результат

Повторно сопоставлены `spec.md`, `plan.md`, `tasks.md`, `contracts/`,
`quickstart.md` и `.specify/memory/constitution.md`. Критических
противоречий между артефактами не найдено. Выбранная lane — **high-risk
product area / active Spec Kit slice** (auth, billing, storage, deletion,
Temporal и UX); до публичного запуска обязательны DB-backed, live-provider и
manual UX gates.

## Покрытие

| Область | Статус | Evidence |
|---|---|---|
| Account/trial lifecycle | закрыто для выбранных сценариев | `tests/integration/test_account_lifecycle.py`, disposable PostgreSQL: 4 passed |
| Temporal billing maintenance | закрыто | `tests/contract/test_billing_reconciliation_workflow.py`, `tests/unit/test_billing_maintenance.py` |
| Storage admission | закрыто для выбранных сценариев | fail-closed artifact/expiry checks; DB/object-stat/supersede lifecycle проходит focused disposable-PostgreSQL evidence |
| Source WAV retention/COGS | реализовано с внешним gate | production gate-поля, exact-byte evidence и opt-in/fail-closed worker wiring есть; policy approval остаётся launch gate |
| Desktop billing handoff | закрыто для выбранных сценариев | browser-owned route policy, one-time browser handoff guards and dedicated Swift test; live browser/network matrix remains external |
| Security/accessibility/usability | interim | automated suites pass; live/manual review ещё обязателен |
| Product-market/pricing | hypothesis | интервью, WTP, 30-day usage, COGS и margin approval отсутствуют |

После последней проверки: **87 задач, 80 закрыты, 7 открыты**. Открытые
задачи: T078–T080, T083–T085 и T087. T036, T047, T053 и T075–T077 имеют
implementation evidence и закрыты в `tasks.md`.

## Findings

- В embedded settings финансовая навигация больше не ведёт на несуществующий
  `/desktop/settings/billing`: она передаёт пользователя в browser-owned
  `/billing`; macOS policy открывает денежные маршруты внешним браузером.
- Trial/account-close integration fixture теперь создаёт trusted
  `AuthSessionDeviceBinding`; полный disposable PostgreSQL сценарий проходит.
- Storage commit fail-closed проверяет expiry, workspace, verified canonical
  `meeting-review.m4a`, artifact bytes и запрещает `None` artifact.
- `source_lifecycle.py` содержит чистые правила и DB-backed gate/purge wiring;
  normal retention остаётся opt-in/fail-closed до утверждения политики, а
  accepted deletion/account-close имеет обязательный override path.

## Launch blockers

Публичный запуск запрещён до controlled canary T078, ручного T079,
live-security T080, подтверждения T084/T085 и повторного T083/T087. Checkout и реальные
платёжные мутации остаются default-off до merchant/legal/finance approvals.
