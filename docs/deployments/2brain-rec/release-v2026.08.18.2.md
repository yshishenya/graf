# Release receipt: v2026.08.18.2

## Сводка

- Merge SHA: `ce62fbf1c1a9b2959c9a38baef6b29a8c2d5e0b9`
- Ветка проверки: `master`
- Validation lane: `release-deploy`
- Результат merge-SHA gate: `pass`
- Дата проверки: `2026-08-18`

Этот receipt содержит только агрегированные результаты. Пароли, токены,
подписанные URL, сырые логи, аудио и содержимое встреч сюда не записываются.

## Exact-SHA full local gate

Команда: `RLS_TEST_DATABASE_URL=<loopback disposable URL> infra/scripts/ci-local.sh --full`

| Этап | Результат |
| --- | --- |
| macOS Swift tests | pass; 693 теста |
| ContractValidation | pass |
| Server PostgreSQL suite | pass; 3046 passed / 1 skipped |
| Strict RLS suite | pass; 42 passed / 1 skipped |
| Server lint | pass |
| Python compile | pass |
| RLS hardening validation | pass; direct SQL probes завершены |
| Production Compose config | pass |
| Deployment evidence scan | pass; 27 файлов |
| Disposable cleanup | pass; database=0, role=0 |

Проверка выполнялась на отдельном loopback PostgreSQL-контейнере с базой,
ограниченной именем disposable RLS scratch database. После завершения база,
временная probe role и контейнер удалены.

## Production deployment dry-run

Команда: `infra/scripts/cd-remote.sh --dry-run --branch master`

Результат: `deploy_result=dry_run`.

План подтвердил branch sync, pinned SHA, обязательный полный local CI, backup,
restore rehearsal, runtime secret checks, migration/RLS boundary, readiness,
production smoke, rollback и post-deploy maintenance checks. Remote state не
изменялся.

## Release and rollback status

- Production `--execute`: ещё не выполнялся в рамках этого receipt.
- Публичный macOS Developer ID/notarization/Sparkle gate: отдельный обязательный
  этап перед публикацией приложения.
- Rollback: не требуется; до production execute сохраняется предыдущий
  опубликованный релиз `v2026.08.18.1`.
- После добавления этого metadata-only receipt полный gate будет повторён на
  финальном release commit перед tag и production execution.

## Связи

- Spec: `specs/167-rls-ci-runtime/spec.md`
- Plan: `specs/167-rls-ci-runtime/plan.md`
- Tasks: `specs/167-rls-ci-runtime/tasks.md`
- PR: #5325
- GitHub issues: #5316–#5324
