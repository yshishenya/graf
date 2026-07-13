# Feature 098 Release Closeout

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: release / deploy
**Status**: `v2026.07.13.2` published and serving from its exact SHA; final
production smoke gate blocked on cleanup ordering, recovered without user-data
impact; validated `v2026.07.13.3` hotfix approved for commit, release and deploy

## Merge Anchor

- Feature PR: [#3270](https://github.com/yshishenya/crisp/pull/3270).
- Merge SHA: `979dc497c1575baa886ce5d74d414e898f5ea464`.
- Release PR: [#3343](https://github.com/yshishenya/crisp/pull/3343).
- Release/deployed SHA: `fc611b631ebdc763aca78d7114e53534c8ef5b59`.
- Published release:
  [`v2026.07.13.2`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.13.2).
- Validated implementation SHA:
  `13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb`.
- The separately deferred feature 097 and its resumable Codex Security scan
  remain untouched and are not release evidence for 098.

## T105 — Release Preparation

- Existing same-day product tag before preparation: `v2026.07.13.1`.
- Selected next free CalVer: `v2026.07.13.2`.
- `./scripts/prepare-release.sh 2026.07.13.2` completed successfully from the
  merge SHA and moved the 098 entries from `[Unreleased]` into
  `[2026.07.13.2]`.
- The generated release diff was reviewed. Its operations wording was updated
  to reflect the actual merge while keeping publish/deploy status pending.
- No release commit, tag or GitHub Release had been created at this checkpoint.

## T106 — Russian GitHub Release

**Title**: `v2026.07.13.2 - безопасный автоконтекст календаря`

```markdown
## Что изменилось

- GRAF теперь может автоматически связать начатую в приложении запись с одним
  подходящим событием календаря.
- Если подходящих событий несколько, пользователь выбирает нужное вручную или
  продолжает без календарного контекста.
- В кабинете появился единый блок «Контекст встречи» с безопасным названием,
  временем и ограниченным списком приглашённых. Контекст можно исправить или
  очистить; уже показанное название встречи при этом не меняется.
- Недоступный, отключённый или устаревший календарь не блокирует запись,
  загрузку и обработку.

## Совместимость и миграции

- Миграция базы `0021_calendar_auto_context_match` добавляет одноразовые
  попытки сопоставления, снимок контекста и источник названия. Она выполняется
  штатным migration-контейнером во время выкладки.
- Старые записи и пользовательские, файловые и исторические названия не
  перезаписываются.
- Старые версии приложения продолжают записывать и загружать встречи без
  автоматического календарного контекста. Для нового сценария приложение GRAF
  нужно обновить или переустановить из сборки этого релиза.

## Как проверено

- Полный локальный gate: 631 тест macOS и 1414 серверных тестов прошли, 4
  серверных теста пропущены по заявленным условиям.
- Отдельно прошли миграции SQLite, одноразовая PostgreSQL/RLS-проверка с
  очисткой, проверки границ доступа и приватности.
- В Chrome проверены список встреч, однозначное и повторяющееся событие,
  неоднозначный выбор, исправление и очистка контекста для browser и embedded
  маршрутов.

## Выкладка и откат

- Перед production-выкладкой обязателен чистый `master`, совпадающий с
  опубликованным SHA, локальный CI, резервная копия и rehearsal восстановления.
- При проблеме используется предыдущий стабильный релиз и созданная перед
  выкладкой резервная копия; результат фиксируется в release evidence.

## Ограничения

- Этот релиз не включает auto-record, автоматическую выдачу доступа или
  отправку материалов приглашённым и автоматическое именование спикеров.
- Публичный подписанный и notarized установщик macOS остаётся отдельным
  ограничением: production-выкладка сервера сама по себе не обновляет локальное
  приложение.
- Отдельная проверка безопасности feature 097 отложена пользователем и не
  считается выполненной этим релизом.

## Связи

- Feature PR: #3270.
- Исполнительные задачи 098: #3082–#3185.
- Release/deploy/closeout задачи: #3186–#3190.
```

Publication evidence:

- release PR #3343 merged as
  `fc611b631ebdc763aca78d7114e53534c8ef5b59`;
- annotated tag `v2026.07.13.2` points to that exact merge commit;
- the GitHub Release is published, not draft and not prerelease;
- published title:
  `v2026.07.13.2 - безопасный автоконтекст календаря`.

## T107 — Deployment Dry Run

Command:

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
```

Result:

```text
deploy_result=dry_run
remote_host=2brain.dev
remote_path=/opt/projects/2brain-rec
branch=master
local_ci=required
steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup,restore_rehearsal,compose_config_secret_scan,deploy_build_up,runtime_secret_env_scan,production_smoke,public_health
```

The first `--execute` attempt stopped during local Swift validation before any
remote action after one non-reproducible failure. The complete Swift rerun then
passed 631/631, and the second exact-SHA execution reached production with:

```text
remote_sha=fc611b631ebdc763aca78d7114e53534c8ef5b59
backup_result=pass
backup_reference=/opt/projects/2brain-rec/backups/20260713T174606Z
restore_rehearsal_result=pass
migration=0021_calendar_auto_context_match (head)
rls_validation_result=pass
```

The API and worker images were rebuilt, the migration completed and production
served the intended SHA. The deployment command nevertheless exited non-zero
before `deploy_result=pass`: synthetic smoke run
`smoke-20260713-174702` created the expected recording context link, but the
cleanup script attempted to delete `meetings` before the new
`recording_calendar_context_links` dependency. PostgreSQL rejected the delete
and rolled back that database transaction.

## Production Safety And Residue Recovery

- Remote `HEAD` remained the intended release SHA and Alembic remained at
  `0021_calendar_auto_context_match (head)`.
- `rec-api`, PostgreSQL and MinIO reported healthy; the processing worker and
  Temporal remained up.
- Public `/api/v1/health/live` and `/api/v1/health/ready` both returned HTTP
  200 after the failed cleanup.
- A fail-closed recovery query first proved that the exact meeting and upload
  session belonged to the expected `internal-smoke` organization, workspace
  and device for that run. It then removed only the two new blocking rows:
  one `calendar_audit_events` row and one
  `recording_calendar_context_links` row; there was no consumed match-attempt
  row in this production run.
- The existing cleanup then passed, removing 33 remaining database rows and
  three synthetic object keys. A separate read-back found zero meeting,
  upload-session, organization, workspace, user or device residue.
- No private meeting content or real account identifiers were inspected or
  recorded.

## Smoke Cleanup Hotfix Validation

The uncommitted branch `codex/098-smoke-cleanup-hotfix` adds table-existence
guarded deletion of `calendar_audit_events`,
`recording_calendar_context_links` and possible consumed
`recording_calendar_match_attempts` before the synthetic meeting.

Validation evidence:

- focused cleanup tests: 6 passed;
- Ruff and `git diff --check`: passed;
- canonical local gate: macOS 631/631, server 1414 passed and 4 conditionally
  skipped, contract validation/lint/compile/compose/evidence scan passed;
- disposable PostgreSQL 17 upgraded through migration `0021`, seeded with all
  three new FK row types, then executed the real patched cleanup: 10 database
  rows removed and `residue_total=0`;
- disposable proof container was removed automatically.

Because `v2026.07.13.2` is already published, the tag must not be moved. The
fix requires a separate `v2026.07.13.3` commit, PR, tag, GitHub Release and
production deploy. The user explicitly approved that complete hotfix path
after reviewing the validation result.

## Approval Gate

- [x] Feature PR merged and exact merge SHA recorded.
- [x] Next CalVer selected and release diff reviewed.
- [x] Russian release notes drafted.
- [x] Required deployment dry run recorded.
- [x] User approves release commit/PR/merge, tag, GitHub Release and production
  `infra/scripts/cd-remote.sh --execute --branch master`.
- [x] Release commit is merged and the exact deploy SHA is pinned.
- [x] Tag and GitHub Release point to the deployed SHA.
- [x] Backup/restore, migration and installed-app impact are reconciled without
  private content.
- [x] Failed smoke residue is removed and production remains healthy.
- [x] User approves the validated hotfix implementation commit and separate
  `v2026.07.13.3` release/deploy.
- [ ] Hotfix production smoke finishes with `smoke_result=pass`,
  `deploy_result=pass` and `readiness_verdict=infra_smoke_ready`.
