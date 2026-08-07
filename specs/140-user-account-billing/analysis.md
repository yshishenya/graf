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
| Storage admission | частично | fail-closed artifact/expiry checks; полный DB/object-stat/supersede lifecycle ещё открыт |
| Source WAV retention/COGS | открыто | production gate-поля и worker wiring отсутствуют |
| Desktop billing handoff | частично | browser-owned route policy и dedicated Swift test; one-time handoff state ещё не реализован |
| Security/accessibility/usability | interim | automated suites pass; live/manual review ещё обязателен |
| Product-market/pricing | hypothesis | интервью, WTP, 30-day usage, COGS и margin approval отсутствуют |

После последней проверки: **87 задач, 76 закрыты, 11 открыты**. Открытые
задачи: T017, T020, T023, T025, T030, T079, T080, T083, T084, T085, T087.

## Findings

- В embedded settings финансовая навигация больше не ведёт на несуществующий
  `/desktop/settings/billing`: она передаёт пользователя в browser-owned
  `/billing`; macOS policy открывает денежные маршруты внешним браузером.
- Trial/account-close integration fixture теперь создаёт trusted
  `AuthSessionDeviceBinding`; полный disposable PostgreSQL сценарий проходит.
- Storage commit fail-closed проверяет expiry, workspace, verified canonical
  `meeting-review.m4a`, artifact bytes и запрещает `None` artifact.
- `source_lifecycle.py` пока содержит только чистые правила; это не считается
  production purge evidence для текущих/legacy WAV.

## Launch blockers

Публичный запуск запрещён до закрытия T025/T030, ручного T079, live-security
T080, подтверждения T084/T085 и повторного T083/T087. Checkout и реальные
платёжные мутации остаются default-off до merchant/legal/finance approvals.
