# Production receipt: v2026.08.23.1

## Сводка

- Release tag: `v2026.08.23.1`
- Deployed/runtime SHA: `2c2bb1ef9ff6c48048c9c0018e06998d44720556`
- Ветка runtime: `master`
- Validation lane: `release-deploy`
- Backup reference: `20260822T191351Z`
- Migration head: `0076_account_linking_rls`
- Дата closeout: `2026-08-23`

Receipt metadata-only: credentials, OAuth tokens, signed URLs, raw logs,
audio, transcripts and private user data are not included.

## Exact-SHA validation

| Этап | Результат |
| --- | --- |
| macOS suite | pass; 725 тестов |
| Server suite | pass; 3296 passed / 1 skipped |
| Strict PostgreSQL/RLS | pass; 52 passed / 1 skipped |
| Account/RLS matrix | pass; 323 теста |
| Targeted strict-RLS regression | pass; 4 теста |
| Ruff, Python compile, Compose config | pass |
| Evidence scan | pass |

## Production deployment and runtime

- Branch synchronization and exact-SHA pinning: pass; `master` и runtime
  совпадают с `2c2bb1ef`.
- Backup и restore rehearsal: pass; `20260822T191351Z`.
- Migration/RLS validation и runtime database identities: pass.
- Production smoke и cleanup: pass; synthetic identity only.
- API health/readiness: HTTP 200 / HTTP 200.
- `rec-api`, `rec-media-worker`, `rec-processing-worker`, Temporal, Postgres и
  MinIO: healthy/running.
- Playback normalization worker control probe: pass; workflow/activity pollers
  ready.
- Rollback: не потребовался.

## Post-deploy maintenance evidence

- Current maintenance context: `twobrain_rec_maintenance`, RLS `on`;
  scheduler access `denied`, legacy maintenance access `allowed`.
- Current inventory: `playback_normalization_jobs=0`,
  `playback_backfill_runs=0`, uncleaned normalization attempts — `0`.
- Historical audit counts: `playback_backfill_inventory_planned=5`,
  `playback_backfill_inventory_completed=10`,
  `playback_backfill_completed=10`, `playback_normalization_retried=252`.
- A synthetic upload-only range probe returned HTTP `409`, because that fixture
  has no canonical playback artifact. Its data, temporary auth session, object
  and token were cleaned up. This is recorded as a maintenance-fixture limit,
  not as an account-linking regression; local playback range tests remain pass.

## Rollback and known limitations

- Migration `0076` is forward-only for production recovery; do not attempt a
  destructive schema downgrade.
- Real user OAuth, email codes and production accounts were not used in smoke.
- The release does not claim a production byte-range playback pass for an
  upload-only fixture that has no canonical playback artifact.

## Связи

- PR: https://github.com/yshishenya/crisp/pull/5548
- Feature spec: `specs/180-account-linking-reliability/`
- Release notes: `docs/releases/v2026.08.23.1.md`
