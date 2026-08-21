# Release receipt: v2026.08.21.5

## Сводка

- Release tag: `v2026.08.21.5`
- Deployed SHA: `6cd0eb5e7da3569ef4ddc62e1fa92aeed04cf3d4`
- Ветка: `master`
- Validation lane: `release-deploy`
- Дата проверки и выкладки: `2026-08-21`

Receipt содержит только агрегированные результаты. Пароли, OAuth-токены,
подписанные URL, сырые логи, аудио, расшифровки и содержимое встреч сюда не
включались.

## Что вошло

- Feature 168: завершённый серверный и пользовательский календарный поток,
  включая browser/embedded состояния, выбор календарей, sync lifecycle,
  upcoming meetings, disconnect truth и native calendar tray.
- Исправлен production rollout: выключенный Google Calendar использует
  безопасный optional placeholder и не блокирует Compose отсутствующим secret;
  включённый провайдер всё ещё требует server-owned secret path.
- Google Calendar в production остаётся `Скоро` / fail-closed: external Google
  verification и production provider E2E ещё не доказаны.

## Exact-SHA validation

| Этап | Результат |
| --- | --- |
| macOS Swift tests | PASS; 725 тестов |
| ContractValidation | PASS |
| Server PostgreSQL suite | PASS; 3219 passed / 1 skipped |
| Strict RLS suite | PASS; 50 passed / 1 skipped |
| Server lint | PASS |
| Python compile | PASS |
| RLS hardening boundary | PASS; disposable SQL probes и runtime boundary |
| Production Compose config | PASS |
| Deployment evidence scan | PASS |
| Disposable cleanup | PASS; isolated PostgreSQL removed |

## Production deployment

- Dry-run: `infra/scripts/cd-remote.sh --dry-run --branch master` — PASS.
- Execute: `infra/scripts/cd-remote.sh --execute --branch master` —
  `deploy_result=pass`.
- Backup и restore rehearsal — PASS.
- Migration head — `0075_calendar_sync_maintenance` — PASS.
- Database identity, runtime secret permissions и tenant/RLS boundary — PASS.
- Temporal, processing worker и API — PASS.
- Smoke upload, cleanup, automatic dispatch, public download и update feed —
  PASS.
- Независимая HTTPS-проверка после выкладки: `/api/v1/health/live` и
  `/api/v1/health/ready` вернули HTTP 200.
- Remote `master` и deployed SHA совпали с `6cd0eb5e7da3569ef4ddc62e1fa92aeed04cf3d4`.
- Rollback не потребовался.

`automatic_retry_result`, `backfill_inventory_result`, `range_playback_result`
и `normalization_cleanup_result` остались `required_post_deploy` по
существующему playback-maintenance контуру. Это отдельные follow-ups и не
являются календарным acceptance gate.

## Ограничения после выпуска

- Google Calendar не включён для всех пользователей: Google branding/data
  verification и реальный production OAuth/catalog/sync/disconnect E2E остаются
  launch blocker.
- Production календарная интеграция не должна заявляться как работающая, пока
  этот внешний gate не закрыт.
- Автоматическая отправка итогов участникам, запись событий, auto-join и
  изменение календарей не входят в этот rollout.

## Связи

- Spec Kit: `specs/168-calendar-integration-completion/`
- Branch: `codex/168-calendar-integration-completion`
- Tag: `v2026.08.21.5`
