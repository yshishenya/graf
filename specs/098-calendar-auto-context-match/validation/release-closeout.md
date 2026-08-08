# Feature 098 Release Closeout

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: release / deploy
**Status**: feature and smoke-cleanup hotfix released; `v2026.07.13.3` is
published and production serves its exact SHA with all deployment, smoke,
cleanup and public-health gates passing; task evidence, tracker comments and
feature-workspace cleanup are complete

## Merge Anchor

- Feature PR: [#3270](https://github.com/yshishenya/crisp/pull/3270).
- Merge SHA: `979dc497c1575baa886ce5d74d414e898f5ea464`.
- Feature release PR: [#3343](https://github.com/yshishenya/crisp/pull/3343).
- Feature release SHA: `fc611b631ebdc763aca78d7114e53534c8ef5b59`.
- Smoke-cleanup hotfix PR:
  [#3344](https://github.com/yshishenya/crisp/pull/3344).
- Hotfix merge SHA: `b835cb110405e50932d5a329e0ef0f1b2ccdbd73`.
- Hotfix release PR:
  [#3345](https://github.com/yshishenya/crisp/pull/3345).
- Final release and deployed SHA:
  `f0e3ee4aef81c5d7a58cf632b6513b7f38414dc9`.
- Published feature release:
  [`v2026.07.13.2`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.13.2).
- Published hotfix release:
  [`v2026.07.13.3`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.13.3).
- Validated implementation SHA:
  `13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb`.
- Feature 097 is separately released; its standalone Codex Security scan was
  explicitly skipped by user instruction and is not release evidence for 098.

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
- Historical portability migration receipts and the disposable PostgreSQL/RLS
  check with cleanup passed, along with access-boundary and privacy checks.
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
- Standalone security scan for feature 097 was explicitly skipped by the user
  and is not represented as completed by this release.

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

## T107 — Deployment Dry Run And Execute

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

Merged PR #3344 adds table-existence guarded deletion of
`calendar_audit_events`,
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

## Hotfix Release `v2026.07.13.3`

- `./scripts/prepare-release.sh 2026.07.13.3` completed from exact hotfix merge
  SHA `b835cb110405e50932d5a329e0ef0f1b2ccdbd73`.
- The command moved the smoke-cleanup fix from `[Unreleased]` into the new
  `[2026.07.13.3]` section and restored an empty `[Unreleased]` scaffold.
- Published title:
  `v2026.07.13.3 - исправление production smoke cleanup`.

Published Russian release notes:

```markdown
## Что исправлено

- Внутренняя проверка production теперь корректно удаляет календарные audit,
  context и match-attempt связи до удаления своей синтетической встречи.
- PostgreSQL foreign-key ограничения больше не прерывают финальную очистку и
  deploy gate после успешной smoke-загрузки.

## Влияние и совместимость

- Пользовательская логика записи, календарного сопоставления и кабинета не
  меняется.
- Новых миграций нет; production остаётся на
  `0021_calendar_auto_context_match`.
- Серверная выкладка не обновляет установленное macOS-приложение. Для этого
  служебного исправления переустановка приложения не требуется.

## Как проверено

- Focused cleanup tests: 6 passed.
- Полный локальный gate: macOS 631/631; server 1414 passed, 4 skipped.
- В disposable PostgreSQL 17 с миграцией `0021` реальный cleanup удалил все
  три новых FK-типа; остаток равен нулю.
- Остаток неуспешного smoke `v2026.07.13.2` удалён после fail-closed проверки;
  production сохранил `live=200` и `ready=200`.

## Выкладка и откат

- Релиз повторно проходит clean branch/SHA gate, backup, restore rehearsal,
  migration verification, runtime secret checks, production smoke и public
  health.
- При проблеме используется предыдущий стабильный SHA и резервная копия,
  созданная перед выкладкой.

## Ограничения и связи

- Feature 097 is separately released; its standalone Codex Security scan was
  explicitly skipped by user instruction and is not part of this hotfix.
- Hotfix PR: #3344. Feature PR: #3270. Release PR `v2026.07.13.2`: #3343.
- Связанные release/deploy задачи: #3188 и #3189.
```

Publication evidence:

- release PR #3345 merged as
  `f0e3ee4aef81c5d7a58cf632b6513b7f38414dc9`;
- annotated tag `v2026.07.13.3` dereferences to that exact merge commit;
- the GitHub Release was published at `2026-07-13T19:35:50Z`, is neither a
  draft nor a prerelease, and uses the title above;
- the tag object is `add58c500fead3e2f7601cef6b8f1bd489d44ccb`.

### Hotfix Exact-SHA Deployment

The first exact-SHA hotfix execution completed the full local gate, backup and
restore rehearsal, then stopped while Docker Hub returned a transient HTTP 500
for base-image metadata. No container recreation had started and production
remained healthy. A bounded retry pulled `python:3.13-slim-bookworm` at digest
`sha256:fcbd8dfc2605ba7c2eca646846c5e892b2931e41f6227985154a596f26ab8ed7`.

The canonical deploy was then repeated from the same clean `master` and exact
release SHA with `--skip-local-ci`. Only the already-passed same-SHA local CI
was skipped; all remote production gates ran again:

```text
branch=master
deployed_sha=f0e3ee4aef81c5d7a58cf632b6513b7f38414dc9
backup_reference=/opt/projects/2brain-rec/backups/20260713T194906Z
backup_result=pass
restore_rehearsal_result=pass
migration=0021_calendar_auto_context_match (head)
rls_validation_result=pass
run_id=smoke-20260713-195002
database_records_removed=35
object_keys_removed=3
cleanup_result=pass
smoke_result=pass
readiness_verdict=infra_smoke_ready
deploy_result=pass
```

The superseded first hotfix attempt created backup
`/opt/projects/2brain-rec/backups/20260713T194744Z`; no rollback was needed
because it stopped before container recreation. The successful retry created a
fresh backup and repeated the restore rehearsal before deployment.

## T108 — Production And Installed-App Proof

### Direct Production Read-Back

- Remote `HEAD` equals the final release/deploy SHA
  `f0e3ee4aef81c5d7a58cf632b6513b7f38414dc9`.
- Alembic reports `0021_calendar_auto_context_match (head)`.
- Public liveness returned HTTP 200 with `{"status":"ok"}` and readiness
  returned HTTP 200 with `{"status":"ready"}`.
- API, PostgreSQL and MinIO are healthy; the processing worker and Temporal are
  running.
- The synthetic production no-context upload completed without calendar
  availability becoming a recording/upload dependency.
- An independent metadata-only residue query found zero synthetic meetings,
  upload sessions, auth sessions, calendar-context links, organizations,
  workspaces, users and devices:
  `post_deploy_smoke_residue_total=0`.
- No private meeting content, raw media, credentials or real account
  identifiers were inspected or recorded.

### Clear, Ambiguous And Browser/Embedded Behavior

The production smoke intentionally uses a synthetic no-context identity and
does not impersonate a real owner or create private calendar content. The
clear, ambiguity/correction and browser/embedded parity receipts therefore come
from the synthetic Chrome and integration runs recorded in
`visual-qa.md`, `implementation-evidence.md` and `scenario-matrix.md`:

- browser and embedded list, matched, recurring, ambiguous chooser, correction
  and clear flows passed;
- browser and embedded POST actions produced the same durable server state;
- keyboard focus, no-context explanations and stable-title-after-clear behavior
  passed;
- authorization/privacy checks proved the owner/workspace boundaries and zero
  access/share/delivery/speaker side effects.

This is valid same-code release evidence rather than a claim of live private
calendar testing: from feature merge `979dc497` through deployed `f0e3ee4a`,
the only changed paths are release/status documents plus the internal smoke
cleanup script and its unit test. Matcher, cabinet UI, API and macOS behavior
code did not change.

### Installed macOS App Impact

- Feature 098 itself includes macOS changes, so an older installed GRAF build
  must be updated or reinstalled from the feature release to use automatic
  calendar context matching.
- The `v2026.07.13.3` hotfix is server/operations-only. The exact diff from
  `v2026.07.13.2` SHA `fc611b63` to deployed `f0e3ee4a` contains no
  `apps/macos` path, so this hotfix requires no additional rebuild, reinstall
  or app restart.
- Server deployment alone never updates an installed macOS application. Public
  Developer ID signing/notarization remains a separate product limitation.

## T109 — Tracker And Workspace Cleanup

- Issues #3082–#3189, mapping one-to-one to T001–T108, each received a detailed
  Russian closure comment before being closed with reason `completed`.
- A post-close query returned `108` closed and only #3190/T109 open. Issue
  #3190 is intentionally closed only after this final receipt reaches
  `master`.
- Clean, fully merged worktrees
  `098-calendar-auto-context-match`, `098-master-baseline-fix` and
  `release-v202607132-098-closeout` were removed after each branch proved zero
  commits ahead of `origin/master`.
- Their local branches and the merged remote feature, baseline-fix, release and
  smoke-hotfix branches were removed. The transient
  `codex/098-tracker-closeout` branch exists only to merge this receipt and is
  deleted with that merge; afterward no remote branch under the exact
  `codex/098*` feature prefix remains.
- Two pre-refresh 098 stashes remain preserved by design; no stash or unrelated
  user state was dropped.
- The clean 099 worktree remains available for the next feature. The dirty
  detached `30ac` worktree was inspected only read-only and remains unchanged.
- Feature 097 is separately released. Its standalone Codex Security scan
  `97e2db82-ff16-4fda-9167-aa52b9b9cf59` was explicitly skipped by the user,
  was not counted as 098 evidence, and is not represented as a result here.
- The two independent deployment clones are not registered repository
  worktrees. Their clean state was verified; they are removed only after the
  final evidence PR is merged so no in-progress closeout state is lost.

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
- [x] Hotfix PR #3344 is merged at exact SHA `b835cb11`.
- [x] `v2026.07.13.3` changelog is prepared from the hotfix merge.
- [x] Hotfix release commit is merged and tag/GitHub Release point to its exact
  SHA.
- [x] Hotfix production smoke finishes with `smoke_result=pass`,
  `deploy_result=pass` and `readiness_verdict=infra_smoke_ready`.
- [x] Production read-back, behavior-proof boundary, installed-app impact and
  zero synthetic residue are recorded without private content.
- [x] Detailed issue closure comments, tracker closure and worktree/branch
  cleanup are complete.
