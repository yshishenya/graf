# Deployment Helper Scripts

Scripts in this directory are operator helpers for GRAF deployment
readiness. They should fail closed, avoid printing secret values, and emit
metadata-only evidence suitable for `docs/deployments/2brain-rec/`.

Scripts must preserve the 021 boundary: first production smoke validates only the
accepted 012 ingest boundary.

Default remote target:

- SSH host: `2brain.dev`
- Deploy path: `/opt/projects/2brain-rec`
- Public endpoint: `https://rec.2brain.pro`

Local execution is for dry-run checks only: tests, compile, compose rendering,
and content scans. Backup, migration, deployment, first production smoke,
cleanup, and final evidence are remote operations on `2brain.dev`.

## CI Lanes

Use focused tests first while implementing. GitHub Actions runs the required
`governance-fast` gate for each PR. Run the local fast lane only when explicit
diagnosis or offline fallback is needed:

```sh
infra/scripts/ci-local.sh --fast
```

The lane argument is mandatory. The fast lane uses the diff from
`origin/master` to run bounded server, macOS, infrastructure/tooling and
documentation checks. Changed server contract/integration files run focused;
calendar performance paths run a focused required proof, while a missing or
renamed proof reports partial coverage without invoking a deleted path.
Deployment evidence also runs its dedicated secret/verdict scanner.
Shared/high-risk, unknown or unavailable diffs report partial coverage and
require full before release, but an explicit `--fast` never changes to `effective=full`.
Release/Spec Kit governance documents also report partial coverage. The common
whitespace check covers the merge-base diff and selected untracked files. It is
the fast feedback lane, not a release gate.

Every local lane emits one metadata-only diagnostic record under the ignored
`.dev/ci-evidence/` directory (or the path in `GRAF_CI_EVIDENCE_PATH`) and
prints `ci_evidence_path=...`. Local evidence is never authoritative for a
release candidate; supplying `GRAF_CI_CANDIDATE_FILE` does not change this.

GitHub Actions runs `governance-fast` automatically for every pull request and
is the authoritative PR gate on the exact PR SHA. The workstation does not run
CI automatically: local `ci-local.sh` is retained only for explicit diagnosis,
offline fallback, or release-operator recovery. For an early full baseline,
run locally only when it is intentionally requested:

```sh
infra/scripts/ci-local.sh --full
```

The local full lane adds macOS tests and contracts (on macOS), the complete server
suite, RLS validation, production Compose rendering and the deployment evidence
scan. Do not run it after every small edit. The normal release path runs one
manual `release-full` workflow in GitHub for the frozen candidate and reuses its
canonical evidence during production execution.

## Local CD

Deploy from the trusted workstation through the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean tracked-and-untracked local worktree, verifies
that the current branch matches `origin/<branch>`, pins the deployment to that
exact commit SHA, and re-checks the clean worktree plus local/remote SHA before
SSH. Release candidates must carry the immutable authoritative Full CI evidence
from the release workflow; the workstation does not start a local Full CI run.
On `2brain.dev`, it
verifies the remote `origin/<branch>` still resolves to the pinned SHA before reset, then performs backup,
production Compose secret-exposure scan, pinned-image startup, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the full local CI step
only. It requires explicit incident approval and does not bypass the clean
worktree, branch sync, pinned SHA, backup, secret scans, smoke, or public health
gates.

Local CD does not store production secrets in GitHub.

### Восстановление из резервной копии

Проверка восстановления больше не входит в каждую выкатку: она разворачивает
всю базу и всё объектное хранилище во временные цели и занимала заметную часть
времени релиза. Резервная копия в релизе остаётся обязательной
(`infra/scripts/backup-rec-stack.sh`), а сама проверка идёт по расписанию — раз
в неделю в `.github/workflows/backup-restore-rehearsal.yml` и вручную:

```sh
infra/scripts/rehearse-restore-scheduled.sh --dry-run
infra/scripts/rehearse-restore-scheduled.sh --execute
```

Запускать нужно с рабочей станции, у которой уже есть SSH-доступ к прод-хосту,
как у `cd-remote.sh`: у GitHub Actions доступа к прод-хосту нет, поэтому
запланированный workflow закрывается отказом с
`reason=production_host_ssh_secret_missing`, пока не заданы секреты
`PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`, `PROD_SSH_KNOWN_HOSTS`.
Сама проверка не разрушительная: временная база и временный бакет удаляются
после прогона.


### Аналитика: копии, восстановление, хранение и оповещения

Задачи фазы 3 работают на сервере аналитики по расписанию systemd и пишут
только метаданные: имена классов томов, размеры, счётчики строк, коды причин и
время. Ни содержимое событий, ни данные посетителей и пользователей, ни
секреты в файлы состояния и в оповещения не попадают.

| Задача | Скрипт | Состояние | Юнит и таймер |
| --- | --- | --- | --- |
| Копия по расписанию, минимум две копии, одна выгружена за пределы сервера | `infra/scripts/backup-posthog.sh` | `/var/lib/graf-posthog-backup/backup-state` | `infra/posthog/graf-posthog-backup.{service,timer}`, ежедневно 02:30 |
| Проверка восстановления в изолированных томах | `infra/scripts/verify-posthog-restore.sh` | `/var/lib/graf-posthog-backup/restore-state` | `infra/posthog/graf-posthog-restore-verify.{service,timer}`, 1 и 15 числа в 04:30 |
| Принудительный срок хранения по категориям | `infra/scripts/enforce-product-analytics-retention.sh` | `/var/lib/graf-posthog-retention/retention-state` | `infra/posthog/graf-posthog-retention-enforce.{service,timer}`, ежедневно 03:15 |
| Срок жизни строк событий в ClickHouse | `infra/scripts/apply-posthog-event-ttl.sh` | — | вручную при изменении срока |
| Внешнее оповещение о деградации измерения | `infra/scripts/alert-analytics-degradation.sh` | `/var/lib/graf-analytics-alert/{last-delivery,channel-state}` | `infra/posthog/graf-analytics-degradation-alert.{service,timer}`, каждые 5 минут |
| Независимая проверка самого канала оповещения | тот же скрипт, `--check-channel` | `/var/lib/graf-analytics-alert/channel-state` | `infra/posthog/graf-analytics-alert-channel-check.{service,timer}`, каждые 15 минут |
| Абсолютный объём хранилища аналитики и скорость роста | `infra/scripts/measure-posthog-storage-growth.sh` | `/var/lib/graf-posthog-storage/storage-growth-state` | вручную, два запуска с интервалом не менее 24 часов |

Проверочные команды без изменений на сервере:

```sh
infra/scripts/backup-posthog.sh --dry-run
infra/scripts/verify-posthog-restore.sh --status
infra/scripts/enforce-product-analytics-retention.sh --status
infra/scripts/apply-posthog-event-ttl.sh --status
infra/scripts/alert-analytics-degradation.sh --status
infra/scripts/alert-analytics-degradation.sh --dry-run
infra/scripts/alert-analytics-degradation.sh --check-channel
infra/scripts/alert-analytics-degradation.sh --drill
infra/scripts/measure-posthog-storage-growth.sh --window-hours 24
```

`--drill` отправляет учебную тревогу и подтверждает срок доставки не более
15 минут (SC-009). `--check-channel` проверяет сам канал независимым путём и
при недоступности пишет `alert_channel_unavailable` в journald и в файл
состояния, а не молчит (FR-056).

Правила и владельцы лежат в `infra/posthog/alert-rules.txt`: у каждого кода
есть роль владельца, а конкретное имя задаётся вне репозитория переменными
`GRAF_ANALYTICS_ALERT_OWNER_<РОЛЬ>`. Пока имя не задано, оповещение всё равно
уходит и помечается `alert_owner_unnamed`.

Примеры окружения: `infra/posthog/runtime-guard.env.example`,
`infra/posthog/alert-analytics-degradation.env.example`,
`infra/posthog/backup.env.example`, `infra/posthog/retention.env.example`.
Рабочие файлы копируются в `/etc` с правами `0600` и не попадают в git.

### Образы выпуска и повтор выкатки

Обычный `cd-remote.sh` готовит два образа (runtime и media-runtime) до остановки
служб. API, workers и одноразовые команды используют их точные IDs. Повтор
того же SHA на той же платформе проверяет сохранённые образы и использует их
без сборки. Разрешённый откат возвращает реальные прежние образы, без сборки
и скачивания. Зависимости и FFmpeg находятся в сохраняемых слоях Docker.

Состояние находится в приватном каталоге Git `graf-release-images`; его
обслуживает `infra/scripts/release-images.py` под существующей блокировкой
выкатки. Незавершённая попытка сохраняет прежний baseline и блокирует новый
запуск. Не удаляйте её файлы и не запускайте `finish` для обхода: сначала
восстановите службы штатной процедурой отката, подтвердите образы, backup,
схему, smoke и public download. Ошибка отката требует восстановления; она
не считается успешным повтором выкатки. `result.json` записывается только
после проверенного результата. Самостоятельные smoke/migration/backup и
restore rehearsal автоматически проверяют сохранённый набор образов.
