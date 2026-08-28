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
- Exact SHA `c428f7990843cc39c141b25c3d8dfdc8de3d66f2` прошёл полный CI:
  macOS `768/768`, server `3487 passed, 1 skipped`, performance `1 passed`,
  strict RLS `52 passed, 1 skipped`, lint/compile/Compose/evidence — PASS.
- `v2026.08.28.11` собран universal, подписан Developer ID
  Application/Installer, нотариализован Apple, stapled и опубликован через
  локальный Keychain signer Sparkle. Public ZIP/appcast и переход
  `2026.08.28.8 -> 2026.08.28.11` прошли `validate-app-updates.sh`.
- Установленный `/Applications/GRAF.app` обновлён штатным Sparkle до
  `2026.08.28.11`; codesign, stapler и `spctl` приняли приложение.
- Installed-app smoke открыл `/billing` и `/billing/checkout` без экрана
  «Функция недоступна». Promo preview для уже использованного `P4_GRAF`
  вернул ожидаемый `promo_invalid`; checkout start вернул `already_active` и
  явно подтвердил, что повторная оплата не создана.
- YooKassa осталась в test-shop; новый платёж не создавался. Полный receipt:
  `docs/deployments/2brain-rec/release-v2026.08.28.11.md`.
