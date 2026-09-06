# Production closeout: `v2026.08.25.4`

Дата closeout: 2026-08-25

## Exact release identity

- Release tag: `v2026.08.25.4`
- Release commit: `82b7389e9a6dffc77828ba561ad4e8507a11d9b5`
- `master` и `origin/master` после closeout совпадали на этом SHA.
- GitHub Release: [v2026.08.25.4](https://github.com/yshishenya/graf/releases/tag/v2026.08.25.4)

## Изменения

- В production выкачены исправления списка встреч Feature 202 и меню профиля GRAF Feature 201.
- Billing checkout больше не зависит от внутреннего launch-gate реестра.
- Счётчики промокодов обновляются PostgreSQL-триггером внутри доверенной RLS-границы.
- Migration `0081_secure_promo_counter` закрепляет `public.promotion_campaigns` и защищает SECURITY DEFINER-функцию от подмены через временную схему.

## Validation evidence

- Focused billing/security contracts: `44 passed`.
- Disposable PostgreSQL migration/RLS checks: `24 passed`.
- Final SHA migration head, calendar performance thresholds и settings flow: `3 passed`.
- Final SHA browser problem contract и worker migration-head checks: `18 passed`.
- macOS build, contract validation и Swift package tests: `766 passed`.
- Production health после deploy: `/api/v1/health/live` и `/api/v1/health/ready` — HTTP 200.
- Remote checkout: `/opt/projects/2brain-rec`, ветка `master`, `HEAD=82b7389e`; runtime containers healthy.

## Production deployment

- Backup перед migration: PASS.
- Restore rehearsal: PASS.
- Migration/RLS verification, API/media/processing/Temporal readiness и synthetic smoke: PASS.
- Guarded rollback: не потребовался.
- После deploy повторно проверены public health endpoints: PASS.

## Ограничения и незакрытые внешние gates

- Полный локальный CI не является PASS: первый прогон на промежуточном SHA `488b2968` завершился с performance-threshold failures и contract false positive; contract-проверка была исправлена до финального SHA, а оба performance-теста повторно прошли на `82b7389e`.
- По согласованному release-пути полный локальный CI перед production execute был пропущен; этот факт не скрывается и не считается PASS.
- Реальный платёж и production-shop не запускались.
- Публичная macOS notarization/appcast-публикация в этом server release не выполнялась и не входит в его артефактный scope.

## Rollback

Для отката использовать штатный `docs/deployments/2brain-rec/rollback-runbook.md` и предыдущий проверенный CalVer-релиз. Миграции `0079`–`0081` применяются вперёд автоматически; при необходимости отката сначала сохранить backup и выполнить migration/restore rehearsal.

