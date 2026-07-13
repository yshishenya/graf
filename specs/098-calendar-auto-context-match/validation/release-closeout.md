# Feature 098 Release Closeout

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: release / deploy
**Status**: release and production execution explicitly approved; execution pending

## Merge Anchor

- Feature PR: [#3270](https://github.com/yshishenya/crisp/pull/3270).
- Merge SHA: `979dc497c1575baa886ce5d74d414e898f5ea464`.
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

## T106 — Russian GitHub Release Draft

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

The dry run describes the gate only; it does not prove branch sync, backup,
restore rehearsal, migration, runtime smoke or production health. Those remain
pending until the release commit is merged and the user approves `--execute`.

## Approval Gate

- [x] Feature PR merged and exact merge SHA recorded.
- [x] Next CalVer selected and release diff reviewed.
- [x] Russian release notes drafted.
- [x] Required deployment dry run recorded.
- [x] User approves release commit/PR/merge, tag, GitHub Release and production
  `infra/scripts/cd-remote.sh --execute --branch master`.
- [ ] Release commit is merged and the exact deploy SHA is pinned.
- [ ] Tag and GitHub Release point to the deployed SHA.
- [ ] Backup/restore, migration, runtime smoke and installed-app impact are
  reconciled without private content.
