# Production closeout: v2026.08.26.3

Дата: 2026-08-26  
Контур: `2brain.dev` / `https://rec.2brain.pro`

## Результат

- Production runtime SHA: `7eb7cf3dbff48cef7817a3856f53b506fb35ebd7`.
- Production deploy: `deploy_result=pass`.
- Backup и restore rehearsal: PASS.
- Backup reference: `/opt/projects/2brain-rec/backups/20260825T223653Z`.
- Migration verification, production smoke, cleanup, health и worker readiness: PASS.
- `/api/v1/health/live`: `ok`; `/api/v1/health/ready`: `ready`.

## Валидация

- Focused Feature 199 и receipt suite: `74 passed`.
- Fast CI: `1241 passed`, lint и compile PASS.
- Full exact-SHA CI: `766` Swift tests; `3444 passed / 1 skipped` server tests;
  performance PASS; `52 passed / 1 skipped` strict RLS; lint, compile и
  deployment-evidence scan PASS.
- Browser E2E на существующем оплаченном счёте подтвердил активную месячную
  подписку до 26.09.2026, автопродление, скидку 99%, статус «Оплачен» и «Чек
  зарегистрирован» в истории и карточке счёта.

## YooKassa и ограничения

- Production-приложение использует YooKassa environment `test` и test-shop с
  suffix `6758`.
- Checkout включён; emergency stop выключен.
- Production-магазин YooKassa не включался.
- Новый платёж во время финального browser E2E не создавался; использован уже
  подтверждённый счёт.
- URL чека провайдер не сохраняет, поэтому UI правдиво показывает регистрацию
  чека без неработающей ссылки.

## Связи

- Feature PR: https://github.com/yshishenya/graf/pull/5853
- Release PR: https://github.com/yshishenya/graf/pull/5854
- Tracking issue: https://github.com/yshishenya/graf/issues/5848
