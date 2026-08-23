# Production receipt: `v2026.08.23.6`

## Immutable release

- Tag and GitHub Release: `v2026.08.23.6`
- Release SHA: `04b711bca06023772d81df165fd6a03d7142ffa0`
- Runtime branch: `master`
- Runtime SHA: `04b711bca06023772d81df165fd6a03d7142ffa0`
- Implementation PR: https://github.com/yshishenya/graf/pull/5615
- Release PR: https://github.com/yshishenya/graf/pull/5616
- Release issue: https://github.com/yshishenya/graf/issues/5607
- Feature: `specs/191-upload-status-ux/`
- Validation lane: `release-deploy`
- Дата выкладки и closeout: 2026-08-23

Receipt содержит только агрегированные технические результаты. Секреты,
приватные материалы встреч и реальные аудиофайлы в него не включались.

## Exact-SHA validation

| Гейт | Результат |
| --- | --- |
| Full CI до публикации | PASS; 726 macOS, 3313 server + 1 expected skip, 52 PostgreSQL/RLS + 1 expected skip |
| Full CI внутри production execute | PASS на том же SHA с теми же наборами |
| Lint, Python compile, Compose, evidence scan | PASS |
| CD dry-run | PASS; `master` закреплён на release SHA |
| CD execute | PASS; runtime SHA совпадает с release SHA |
| Backup и restore rehearsal | PASS; reference `20260823T072232Z` |
| Migration head | PASS; `0077_provider_unlink_xworkspace` |
| Production smoke и cleanup | PASS; synthetic identity only |
| Health/readiness и workers | PASS |
| Rollback | Не потребовался |

## Public macOS release

- Версия app/pkg: `2026.08.23.6`.
- Apple notarization: app `c3d400ca-2fc2-42ed-9769-c0e49effe915` —
  `Accepted`; pkg `99678167-9151-4ae4-abd3-62f12b7c4a09` — `Accepted`.
- App и pkg прошли stapler validation и Gatekeeper; пакет подписан
  `Developer ID Installer`, приложение — `Developer ID Application`.
- `validate-app-updates.sh` подтвердил Developer ID и Sparkle continuity
  `2026.08.21.3 → 2026.08.23.6`, неизменные bundle identity, feed и trust
  generation 1.
- Финальный ZIP SHA-256:
  `7b6b447eb584aa75af6099c97bbd79bf10ef4dfc18443deee0bc53dbbedbb929`.
- Финальный PKG SHA-256:
  `c4aabe89e1baea96fd50107b794ccc59acf63468d7c326de153cc40af5bd827a`.
- Публичный appcast указывает на `2026.08.23.6`, enclosure length `7541364`
  и versioned HTTPS ZIP. Публичный readback ZIP, PKG, checksums и appcast
  совпал с опубликованным кандидатом.
- GitHub Release опубликован 2026-08-23; промежуточный candidate asset удалён,
  финальные assets повторно скачаны и сверены байт-в-байт.
- Установленный `/Applications/GRAF.app` штатно обновился через Sparkle с
  `2026.08.21.3` до `2026.08.23.6`, перезапустился и прошёл `codesign`,
  stapler validation и Gatekeeper.

## Production deployment

- Backup и пробное восстановление прошли до миграции.
- Runtime migration head: `0077_provider_unlink_xworkspace`.
- `/api/v1/health/live` вернул `ok`, `/api/v1/health/ready` — `ready`.
- API, processing worker, media worker, Temporal, Postgres и MinIO находятся в
  рабочем состоянии; production synthetic smoke и его очистка прошли.
- Runtime `master`, tag и GitHub Release указывают на один release SHA.
- Rollback не потребовался; предыдущий appcast сохранён как операторский
  rollback reference. Для клиентов, уже установивших новую версию, откат
  выполняется только новым выпуском вперёд.

## Ограничения evidence

- Synthetic smoke не использовал реальные аккаунты, аудио, расшифровки или
  приватные материалы встреч.
- Отдельный повторный визуальный smoke приватного production-маршрута встречи
  в closeout не заявляется: текущий инструмент автоматизации заблокировал этот
  URL. До release прошли локальная Browser-матрица desktop/375px/200% reflow,
  keyboard focus, console health, focused contracts и production smoke.
- Release не меняет capture, auth, storage, privacy или deletion boundaries.

## Связи

- Release notes: [v2026.08.23.6](../../releases/v2026.08.23.6.md)
- GitHub Release: https://github.com/yshishenya/graf/releases/tag/v2026.08.23.6
- Feature tasks: `specs/191-upload-status-ux/tasks.md`
