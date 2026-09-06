# Production closeout: `v2026.08.30.1`

Дата closeout: 2026-08-30

Receipt содержит только агрегированные технические метаданные. Секреты,
идентификаторы встреч, object keys, signed URLs, аудио и расшифровки не
включались.

## Exact release identity

- Release tag и GitHub Release:
  [`v2026.08.30.1`](https://github.com/yshishenya/graf/releases/tag/v2026.08.30.1).
- Release и deployed SHA:
  `2e7ef275b6fc2e1749201916202870da6d19ef4a`.
- Implementation PR:
  [#6004](https://github.com/yshishenya/graf/pull/6004).
- Feature: `specs/211-optimize-ci-cd/`.
- Validation lane: high-risk infrastructure / release-deploy.

## Validation and production deployment

| Гейт | Результат |
| --- | --- |
| Authoritative full внутри production execute | PASS; `1117s` |
| macOS | PASS; `769/769` |
| Server | PASS; collection `3807`; parallel `3752 passed, 1 skipped` |
| Performance и strict RLS | PASS; `1 passed`; `52 passed, 1 skipped` |
| Lint, compile, Compose и evidence | PASS |
| Branch/tag/runtime synchronization | PASS на release SHA |
| Backup и restore rehearsal | PASS; `20260830T084202Z` |
| Migration/RLS, secrets и runtime identities | PASS |
| Temporal, API и processing/media worker readiness | PASS |
| Production synthetic smoke и cleanup | PASS |
| Public health | PASS; live и ready вернули HTTP 200 |
| Rollback | Не потребовался |

`--skip-local-ci` не использовался. Production execute самостоятельно провёл
один обязательный full на синхронизированном SHA, повторно проверил неизменность
кандидата и только затем начал удалённые production gates.

## Post-deploy maintenance audit

После выкладки следующий release train продвинул `master` и production до
`44e25fccf703d76a485cbe25f156b8561a5206dd`. Этот SHA содержит release SHA
Feature 211 в истории. Read-only аудит текущего production состояния показал:

- playback worker control: PASS; workflow и activity pollers готовы;
- backfill runs: `22`, все в состоянии `complete`;
- normalization jobs: `131`; незавершённых и due/expired — `0`;
- normalization attempts: `462`; cleanup candidates — `0`;
- public live и ready: HTTP 200.

CD-поля `automatic_retry`, `backfill_inventory`, `range_playback` и
`normalization_cleanup` намеренно остаются `required_post_deploy`. Inventory и
cleanup подтверждены read-only аудитом. Automatic-retry и Range не запускались
повторно: для них нужна отдельная контролируемая synthetic maintenance
процедура с остановкой worker либо созданием playback artifact. Они не являются
release-smoke гейтами CI/CD-релиза, и реальные пользовательские записи для них
не использовались.

## Compatibility and limitations

- Публичные API, схема БД и пользовательские данные не менялись.
- Bare `infra/scripts/ci-local.sh` больше не выбирает lane молча: оператор
  передаёт `--fast` или `--full` явно.
- Immutable image build/push/deploy-by-digest остаётся отдельной
  архитектурной задачей.
- Публичный macOS package и appcast в этом релизе не публиковались.
