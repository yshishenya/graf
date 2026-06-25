# PR Draft: 052 MVP Live UI Proof

## PR Title

`052: честная проверка MVP live UI и запуск processing dispatch`

## Summary

- Включает processing dispatch в production `rec-api`, чтобы upload finalize мог
  запускать Temporal workflow, а не оставлять accepted записи в `not_submitted`.
- Обновляет 052 readiness/report evidence: live owner review остается
  `pilot_blocked`, web/detail/outcomes/embedded отмечены как degraded, а не
  готовые.
- Фиксирует KRISP clean-room reference, web/mobile/embedded playback timeline
  verifier, macOS false-green guard и launch gaps без приватного контента.

## Validation

- `infra/scripts/ci-local.sh`: `pass`; server tests `622 passed, 4 skipped`,
  server lint, Python compile, compose render и deployment evidence scan прошли.
- `infra/scripts/cd-remote.sh --dry-run`: `deploy_result=dry_run`.
- Browser runtime verifier: `failures=[]`.
- macOS focused tests: `112 tests, 0 failures`.
- Forbidden-content scan: reviewed pass; живых приватных значений не найдено.

## Release Notes Draft

### Что изменилось

- Исправили production-конфигурацию: API теперь может запускать обработку после
  завершения upload.
- Обновили доказательный отчет MVP: интерфейс playback/timeline локально
  проверен, но live production owner review все еще не считается готовым.

### Что это дает продукту

- Убирает найденный блокер нормального пути записи к обработке.
- Не завышает статус MVP: продукт остается `pilot_blocked`, пока не пройдут
  свежий owner journey, production stored outcomes и timing на длинной записи.

### Совместимость и миграции

- Миграций БД нет.
- Production deploy меняет Compose env/secrets/dependency graph для `rec-api`.

### Known Limitations

- Authenticated live owner detail/embedded review все еще нужно доказать.
- Production stored outcomes сейчас не доказаны.
- Representative one-hour timing proof еще не выполнен.

## Issue Links

Use exact `Fixes`/`Refs` links only after confirming the final PR scope against
`specs/052-mvp-live-ui-proof/issues.md`.
