# Feature 208: implementation evidence

Дата: 2026-08-28.

## Реализация

- Общая macOS route policy разрешает только текущие server-rendered billing
  actions: checkout preview/start, promo apply/remove, trial activation,
  payment-method deletion, subscription cancel/resume и safe status
  refresh/continue.
- Неизвестные static/dynamic sibling-маршруты остаются fail-closed.
- Серверные handlers, БД, YooKassa-конфигурация и платёжная семантика не
  изменялись; новый платёж не создавался.

## Локальная проверка

- `DesktopCabinetBillingHandoffTests`: PASS, 10 tests, 0 failures.
- `DesktopCabinetRoutePolicyTests`: PASS, 16 tests, 0 failures.
- `swift build --package-path apps/macos`: PASS.
- `infra/scripts/ci-local.sh --fast`: PASS; server unit `1250 passed`, Ruff и
  Python compile — PASS.

## Release gate

- Validation lane: high-risk product area / shared billing navigation boundary.
- Full exact-SHA CI, Developer ID, notarization, stapling, Gatekeeper, Sparkle
  publication и installed-app smoke остаются открытыми в T004.
- Релиз не начинается, пока занят единый release/deploy lock; YooKassa остаётся
  в test-shop.
