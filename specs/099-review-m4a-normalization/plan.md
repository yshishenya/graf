# Implementation Plan: Review M4A Normalization

**Branch**: `codex/099-review-m4a-normalization` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/099-review-m4a-normalization/spec.md`

## Summary

Feature 099 guarantees a stored, validated `meeting-review.m4a` for every
supported valid accepted recording source without user or administrator work.
Successful finalize creates durable normalization intent in the accepted-source
transaction; a separate non-root Temporal media worker validates an uploaded
playback candidate or derives AAC-LC/M4A from manual media or the explicit
first-party microphone/system pair. Temporary failures retry automatically and
are reconciled after restarts. Legacy records are inventoried first and then
processed in bounded automatic batches.

The design keeps source custody, transcript processing, and playback truth
separate. Only a completely decoded and profile-validated immutable artifact is
published. Playback requests continue to stream the stored object with ranges
and never transcode on demand. The cabinet shows playback preparation/readiness
independently from transcript/summary state and exposes no retry, reprocess, or
backfill control.

## 2026-07-17 Production Recovery Hotfix

Production evidence showed that an accepted first-party record could remain in
`retry_wait` for the long-cycle delay after a `worker_interrupted` recovery,
despite the media worker being healthy again. The hotfix is deliberately narrow:
the worker's one startup reconciliation admits only future-dated retry-wait jobs
whose durable reason is `worker_interrupted`, transitions them through the
existing lock, audit, lease and dispatch path, and leaves all ordinary retry
reasons on their scheduled backoff. It introduces no user/admin repair control,
schema change, source re-upload, duplicate job, native-app change, or altered
periodic reconciliation behavior.

Focused acceptance proves both sides: an interrupted job is dispatched on
startup with its original lineage, and a future-dated retry for any other reason
is not selected. The normal local CI and production closeout then prove the
existing record converges without user action.

## Technical Context

**Language/Version**: Python >=3.13; SQLAlchemy 2/Alembic; FastAPI/Pydantic 2;
Temporal Python SDK; Jinja/HTMX/vanilla JS cabinet; existing Swift 6/macOS 14+
client as a regression surface only.

**Primary Dependencies**: Existing ingest/finalize, MinIO storage, Temporal,
cabinet egress/read models, retention/deletion, support incidents, RLS and
deployment scripts. Add the Debian Bookworm `ffmpeg` package (`ffmpeg` and
`ffprobe`) only to a media-enabled Docker target; no PyAV or frontend framework.

**Storage**: PostgreSQL production with SQLite compatibility. Migration
`0022_playback_normalization.py` (after current `0021` head) adds normalization
jobs, attempts, per-workspace backfill runs, canonical validation fields on
`TrackArtifact`, and a portable partial unique index for one active stored
playback artifact per media revision. MinIO stores immutable accepted source,
candidate, attempt, and canonical objects with distinct ownership.

**Testing**: pytest unit/contract/integration tests; real FFmpeg container
capability and synthetic-media tests; SQLite and disposable PostgreSQL
migration/RLS/concurrency tests; existing Swift upload/capture regression tests;
Chrome and embedded cabinet playback/status E2E; `test-rec` end-to-end evidence;
Ruff; canonical `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk significant feature / active Spec Kit
slice. It handles untrusted media, CPU/disk subprocess work, durable queues,
storage derivation, RLS, deletion races, background recovery, cabinet UX,
Docker/deploy topology, and production backfill.

**Release Gate**: Planning performs no deploy. After implementation, focused
validation, full local CI, independent review, and explicit integration
approval, merge the scoped PR. Then prepare the next free CalVer release and run
`infra/scripts/cd-remote.sh --dry-run`. Release/tag/GitHub Release and
`--execute` require a fresh release/deploy approval for the validated candidate.
Production closeout requires migration, worker health, bounded backfill,
browser/embedded playback, real user-path E2E, and residue-free cleanup.

**Target Platform**: Linux server/cabinet and a dedicated Linux media worker;
Chrome/Safari-compatible HTTP M4A playback; embedded macOS WebView using the
same server cabinet. No native app behavior change is planned.

**Project Type**: Web service with server-rendered cabinet, background Temporal
workers, PostgreSQL/MinIO storage, and a native macOS capture/upload client.

**Performance Goals**:

- finalize adds only bounded database upsert/commit work and never waits for
  probe/transcode;
- accepted-source normalization is queued within 60 seconds even after a lost
  immediate dispatch;
- playback range responses perform no conversion and retain bounded streaming;
- media worker concurrency is 1 at 1 CPU/1 GiB, with no complete source object
  in process memory;
- backfill inventories 100 rows per keyset page and dispatches at most 25 jobs
  per batch, behind new-ingest and due-retry jobs;
- synthetic near-limit benchmark on production-equivalent resources completes
  within the 6-hour activity timeout before release.

**Constraints**:

- every supported valid retained source converges automatically; no user/admin
  retry, reprocess, or backfill mutation;
- exact source limits remain 4 hours, 1 GiB manual file, 2.5 GiB track, and 5
  GiB first-party package;
- at most 16 total/8 audio streams; 128 MiB final output; 6 GiB disk-backed work
  budget; concurrency 1;
- accepted source fingerprint excludes the optional playback derivative;
- byte-for-byte reuse requires the complete canonical gate and full decode;
- manual multi-stream media uses one usable stream or one unique default only;
- first-party fallback mirrors the already defined two-role 50/50 aligned mix;
- playback publication is database-atomic visibility over an immutable object,
  not a claimed MinIO/PostgreSQL distributed transaction;
- deletion wins every publish race and removes registered temporary objects;
- raw filenames, object keys, FFmpeg stderr, media, transcript, summary, URLs,
  signed tokens, credentials, and private paths are forbidden from diagnostics
  and committed evidence.

**Scale/Scope**: MVP/internal workspaces with all existing accepted revisions,
new first-party and manual uploads, one media worker initially, automatic
per-workspace legacy backfill, browser and embedded review parity. Excludes
video playback, source editing, user track selection, manual repair controls,
new upload/finalize ownership, source-only retention policy, and changes to the
MediaScribe contract.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first and manual control**: Pass. No capture, Record/Stop, active
  indicator, one-action Stop, or native source-writer behavior is removed.
  Conversion starts only after server acceptance and cannot block local capture.
- **Accepted-source custody and data boundary**: Pass with required design.
  Normalization uses accepted server artifacts only. Desktop never contacts
  MediaScribe or stores server/dependency credentials.
- **No competing source of truth**: Pass. Existing upload/finalize,
  `MediaRevision`, and `TrackArtifact` remain authoritative. The new job records
  derived playback work and does not create another meeting/source service.
- **Resource-bounded processing**: Pass with required design. Work is isolated
  to a 1-CPU/1-GiB non-root worker with concurrency 1, bounded protocols,
  streams, disk, output, subprocess output, timeouts, retries, and batches.
- **Privacy and metadata-only evidence**: Pass. Probe output is allowlisted;
  raw tags/stderr/content/path/key/filename values never enter audit, incident,
  logs, specs, Issues, PR evidence, or screenshots.
- **Lifecycle and deletion truth**: Pass with required design. Canonical and
  temporary objects are registered, deletion wins publication races, and
  reports account for both classes without promising external erasure.
- **Tenant isolation**: Pass with required design. New tables force RLS. Global
  inventory/dispatch uses two narrow maintenance operations only for bounded
  enumeration, then returns to exact tenant worker context.
- **Truthful product states**: Pass. Playback and transcript statuses are
  independent; partial/failed objects never appear ready; terminal impossible
  inputs do not spin forever; transient failures remain automatic.
- **UX/accessibility/brand distance**: Pass. Existing GRAF status/player
  primitives and one server read model are reused. No reference-product copy,
  asset, or pixel-identical UI is introduced.
- **Spec-driven delivery**: Pass. Specify/clarify are complete. This plan
  produces research, data model, contracts, and quickstart; checklist, tasks,
  analyze, GitHub issue sync, implementation, convergence, review, validation,
  and production closeout remain mandatory.

No constitution violation is accepted or justified.

### Post-Design Constitution Re-Check

- **Research**: Pass. It resolves exact canonical profile, input matrix, stream
  selection, first-party mix, subprocess isolation, limits, timeouts, retry
  cycles, backfill batching, and publication/deletion races.
- **Data model**: Pass. One job per revision/profile, registered attempts, one
  per-workspace run, and existing `TrackArtifact` are the minimum durable truth.
  `Meeting.playback_status` is deliberately not duplicated.
- **Contracts**: Pass. They add no user/admin repair mutation, keep accepted
  source and playback objects separate, expose only safe read states, and make
  deletion/RLS/readiness requirements explicit.
- **Quickstart**: Pass. It covers real format conversion, strict reuse/remux,
  multi-stream ambiguity, dual-source fallback, retries/restarts, inventory
  ordering, deletion races, PostgreSQL uniqueness/RLS, browser seek, production
  backfill, and cleanup.

No post-design constitution violation is introduced.

## Validation Plan

Implementation validation is staged:

1. Unit tests for profile validation, BMFF bounds/order, exact source matrix,
   stream selection, dual-source mix arguments, state transitions, retry due
   times, safe audit metadata, and cabinet status composition.
2. Container capability tests for the exact pinned FFmpeg/FFprobe build,
   allowlisted demuxers/decoders, AAC-LC encoder, `ipod` muxer, `+faststart`,
   protocol restriction, real synthetic formats, full decode, output cap, and
   process-group cancellation.
3. Contract/integration tests for finalize role sets, candidate status, source
   fingerprint, post-commit dispatch, deterministic workflow identity,
   duplicate pickup/publication, transient auto-retry, restart recovery,
   inventory-before-mutation, priority, and no mutation endpoints.
4. SQLite plus disposable PostgreSQL migration, partial uniqueness, row-lock,
   RLS, maintenance-operation, downgrade, and deletion-race tests.
5. Cabinet/OpenAPI/rendering tests for independent playback/transcript states,
   localized accessible copy, no retry controls, range transport, and forbidden
   diagnostic content.
6. Existing Swift capture/upload tests prove candidate descriptors and required
   WAV/source behavior remain compatible; no app rebuild is claimed necessary
   unless implementation later changes `apps/macos`.
7. Run [quickstart.md](./quickstart.md) with synthetic fixtures and working
   copies from `test-rec`, then run `infra/scripts/ci-local.sh` after the final
   code-affecting fix.
8. After merge/release approval, deploy with backup/migration/worker health,
   prove both new-ingest and legacy backfill in production, perform Chrome and
   embedded seek/playback E2E, verify transcript/playback independence, and
   remove only feature-specific test records/objects with residue zero.

The standalone feature-097 Codex Security scan remains deferred and untouched.
Normal authorization, RLS, dependency isolation, redaction, and lifecycle
assertions are acceptance tests, not a claim that the deferred scan completed.

## Project Structure

### Documentation (this feature)

```text
specs/099-review-m4a-normalization/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── playback-normalization-contract.md
│   ├── playback-status-contract.md
│   ├── automatic-backfill-contract.md
│   └── lifecycle-operations-contract.md
├── tasks.md
└── validation/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── normalization/
│   ├── audit.py                         # strict safe event metadata
│   ├── media.py                         # bounded probe, BMFF, remux/transcode
│   ├── pickup.py                        # due jobs and inventory-first backfill
│   ├── service.py                       # job state, source, publish, cleanup
│   ├── statuses.py                      # state/reason/profile constants
│   └── worker.py                        # isolated Temporal media worker
├── workflows/
│   └── playback_normalization_workflow.py
├── db/models/
│   ├── ingest.py                        # TrackArtifact validation fields
│   └── normalization.py                 # jobs, attempts, backfill runs
├── db/migrations/versions/
│   └── 0022_playback_normalization.py
├── ingest/
│   ├── finalize.py                      # durable job in accepted transaction
│   ├── manifest.py                      # optional playback candidate role
│   ├── media_revisions.py               # source-only fingerprint
│   ├── processing_dispatch.py           # post-commit side effects
│   └── store.py                         # candidate vs canonical status
├── cabinet/
│   ├── egress.py                        # transcript-independent playback truth
│   ├── queries.py                       # job + canonical artifact reads
│   ├── view_models.py                   # safe status projection
│   └── rendering.py/templates/          # localized no-retry states
├── api/
│   ├── schemas.py                       # playback status/readiness projection
│   └── health.py                        # normalization readiness summary
├── deletion/
│   ├── service.py                       # cancel/purge/lock race handling
│   └── report.py                        # playback/temp accounting classes
├── db/
│   ├── tenant_context.py                # narrow inventory/dispatch maintenance
│   └── rls_validation.py                # new workspace tables
├── storage/
│   ├── minio_client.py                  # bounded attempt upload/stat helpers
│   └── object_keys.py                   # UUID normalization object keys
└── support/                              # metadata-only stalled-job incident reuse

apps/server/tests/
├── unit/test_playback_normalization_*.py
├── contract/test_playback_normalization_*.py
├── integration/test_playback_normalization_*.py
├── integration/test_playback_normalization_migrations.py
├── integration/test_playback_normalization_postgres.py
├── integration/test_playback_normalization_deletion.py
└── integration/test_cabinet_playback_route.py

infra/
├── server/Dockerfile                    # base/runtime/media-runtime targets
├── docker-compose.yml                   # non-root rec-media-worker + work volume
├── docker-compose.dev.yml
├── env/*.example                        # explicit normalization config
└── scripts/
    ├── ci-local.sh                      # media-container capability gate
    └── cd-remote.sh                     # worker health/backfill deploy evidence

specs/012-server-ingest-foundation/contracts/openapi.yaml
CHANGELOG.md
docs/current-product-status.md
```

**Structure Decision**: Keep the existing server/cabinet/macOS split and add one
small server domain plus one isolated worker. `TrackArtifact` remains canonical
artifact ownership; `MediaRevision` remains source lineage; the job is only
durable derived-work truth. The same server read model serves web and embedded
macOS. A separate media Docker target/task queue isolates untrusted FFmpeg work
without adding a new datastore, broker, frontend, or media platform.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md),
[contracts/playback-normalization-contract.md](./contracts/playback-normalization-contract.md),
[contracts/playback-status-contract.md](./contracts/playback-status-contract.md),
[contracts/automatic-backfill-contract.md](./contracts/automatic-backfill-contract.md),
[contracts/lifecycle-operations-contract.md](./contracts/lifecycle-operations-contract.md),
and [quickstart.md](./quickstart.md).

## Complexity Tracking

No constitution violations are introduced. The separate media worker is an
intentional isolation boundary, not a new product subsystem: it reuses the
existing image base, Temporal, PostgreSQL, MinIO, accepted-source registry,
cabinet, and deploy scripts. Keeping FFmpeg out of API/migration/MediaScribe
processes is required for CPU/disk isolation, non-root execution, and predictable
backfill; a shared worker would be simpler in file count but unsafe in runtime
behavior.

## 2026-07-17 Active Attempt Cleanup Hotfix

The existing maintenance cleanup selector is retained, but now excludes only a
temporary attempt whose parent job is actively `running` or `publishing` with
an unexpired worker lease. This is a single selector predicate plus a matching
PostgreSQL helper-function migration; it preserves cleanup after lease expiry
and adds no service, dependency, endpoint, queue or user action.


## 2026-10-17 — защита попытки при ошибке и прямой очистке

Lane: **high-risk-product**, продолжение US3/US6 F099 на
c6c5441c930b8c1ecffed6de9b80773aa0e757e5. Первая CI часть F290 не входит.
Constitution до/после design: I/II capture неизменен, III metadata-only,
IV immutable attempt/source и deletion fence, V без выпуска, VI полный
цикл, VII UI неизменен; исключений нет.

Исследование: два детерминированных PostgreSQL опыта показали, что старая
ошибка A сбрасывает B, а cleanup после commit A очищает B. Успешный путь
уже проверяет номер попытки/lease; catch и прямой cleanup этого не делают.
Реальные failure callers: run_normalization_job и expired recovery. Recovery
уже проверяет expired running/publishing под блокировкой job до failure.
Прямые cleanup callers: sweep, expired recovery, catch, discard-unowned и
losing publisher; защита должна находиться в общей cleanup функции.

Owned runtime paths: только
`apps/server/src/twobrain_rec_server/normalization/service.py` и
`apps/server/tests/integration/test_playback_normalization_restart.py`.
Документы этой F099 и `changes/unreleased/F99.yaml` принадлежат срезу.
Без схемы, новых зависимостей, endpoint, флагов, фоновых служб и handoff.

Решение: перенести существующую подготовку попытки в run_normalization_job,
оставив исполнение в прежней функции. Перед prepare сохранить scalar текущего
attempt_count; после успешного prepare — новый номер и owner hash. В catch
после rollback/rehydration передать ожидаемые число/owner в общий failure.
Под блокировкой job сравнить их с текущими; для подготовленной попытки
проверить также действующую lease. При потере владения вернуть Deferred
без записи ошибки/инцидента/очистки B. Ошибка до создания попытки сравнивает
исходный счётчик И допустимое queued/retry_wait состояние без активной
LOCAL_PREPARING/UPLOADED попытки, сохраняя существующий source_missing путь.
Если scalar query увидел уже running/publishing B, а prepare затем упал
до проверки state, совпадающего count недостаточно: такую ошибку тоже
отклонить через Deferred. Отдельно проверить этот порядок. У recovery
проверка остаётся под его прежней блокировкой; тестовые прямые вызовы
сохраняют свой интерфейс. Никогда не читать expired ORM attributes в catch:
идентичность зафиксировать scalar значениями до rollback. Если исходный
scalar count вообще не прочитан из-за ошибки БД, не вызывать unfenced
failure: вернуть существующий DATABASE_UNAVAILABLE/retry без durable mutation.

Для обычной cleanup_normalization_attempt сначала прочитать job_id без блокировки,
затем брать Job → Attempt только через SKIP LOCKED, повторно читая
состояние. Оба новых захвата выполняются в savepoint; при занятом или
исчезнувшем row — rollback savepoint и честный False без изменения данных.
Это освобождает новые locks, не откатывая caller transaction. Прямой cleanup
никогда не ждёт Attempt при удержанном Job: deletion purge использует
Attempt → Job и иногда уже освободил Meeting; общий Meeting lock здесь
не является достаточным решением. Штатная следующая cleanup повторит
пропущенную попытку, результат cleaned не выдаётся. Текущая попытка
с номером job.attempt_count при running/publishing и будущей lease защищена
до любого изменения attempt/reservation/storage. Старые immutable attempt ID,
expired/non-active jobs, published winner, purged tombstones и late PUT
остаются в существующем жизненном цикле. Сохранить неблокирующий порядок Job → Attempt,
не добавлять I/O под блокировкой: переход cleanup_pending по-прежнему commit
до storage I/O. Sweep selection не является единственной защитой.

Исключение только для существующего `late_object_arrival=True` пути:
_discard_unowned_attempt вызывается по неизменяемому ID своей A после
проверки утраты владения/удаления. Сохранить его прежний Attempt-only lock
и позднюю очистку (без нового Job lock/SKIP LOCKED), чтобы не потерять
поздний PUT уже CLEANED/PURGED A из-за нового no-op. Здесь отсутствует
ожидание Job при удержанном Attempt. Обычная очистка и этот внутренний
fenced path не взаимозаменяемы; новый внешний параметр/вызов не добавлять.
После stale failure только подготовленной A также вызвать существующий
_discard_unowned_attempt по сохранённому до rollback scalar ID своей A;
B не затрагивается. Перед этим discard обязательно rollback транзакции
проверки failure и rehydrate контекста: освободить Job lock ДО ожидания
Attempt, даже если failure вернул Deferred. Двухсессионный тест stale
failure → discard обязан подтвердить, что держатель Attempt может взять
Job NOWAIT; затем discard заканчивается после release. Проверить поздний
объект A и сохранность B вместе.

Матрица: late exception A после B local_preparing и uploaded/reservation;
совпадающее и разное имя owner; корректная failure A → B → delayed cleanup;
оба entry points cleanup и expiry; ordinary failure/source_missing;
готовый canonical winner; deletion/late PUT; tenant boundary. Детерминированное пересечение: другая session
держит Attempt, cleanup пропускает без изменения, затем та session берёт
Job без блокировки; после release штатная cleanup работает. Отдельно занятый
Job тоже даёт no-op. Проверки в
одноразовом PG17 штатным runner, state/storage doubles явно обозначить.
Это серверная логика. Для активного repair применяется актуальная
release-and-validation.md: focused локально, три exact-SHA PR checks и
новый frozen Full при выпуске. Историческое требование полного local CI
выше описывало прежний принятый выпуск, оно не добавляет повторную
нативную сборку к серверной проверке этого repair. Native/manual app
проверка нужна лишь при изменении приложения; в этом срезе её нет.
После reviewer/checklist, analyze, issue sync — минимальный код, focused
regression/ruff/governance; независимый review и converge. Commit только
после отдельного согласия, затем три exact-SHA PR checks и merge отдельно.
Production требует нового frozen Full/dry-run/согласия и приёмки F290.


## 2026-11-17 — T014/#3361: не удалять существующий destination

Активный срез: **high-risk-product**, existing F099/T014/#3361, база
`c22500f994a0dc5f951341e3c5f202d5d21ac8a2`. Исторические разделы выше и их
ограничения разрешений не заменяют текущее поручение владельца; commit/push/PR/merge
разрешены, выпуск и развёртывание имеют отдельные ворота.

Constitution pre-design и post-design: I/II capture не меняется; III только
безопасные метаданные и синтетические данные; IV исходник и чужой destination
сохраняются; V нет выпуска/развёртывания; VI полный Spec Kit и точные SHA/base;
VII UI не меняется. Исключений и новой сложности нет.

Исследование: неизменённый метод из указанной базы в ограниченном AST probe
удалил собственные заранее существовавшие файл и ссылку при `O_EXCL/EEXIST`.
Fresh success и digest cleanup сработали. Это доказательство дефекта, не проверка
полного модуля или рабочего провайдера. H1–H3 независимого ревью уточняются
FR-045/SC-025 и матрицей Quickstart ниже. Новых зависимостей/API/схем/флагов нет.

Owned code/test: `apps/server/src/twobrain_rec_server/storage/minio_client.py`,
`apps/server/tests/unit/test_playback_normalization_storage.py`; документы
этой F099, validation receipt и `changes/unreleased/F99.yaml`.
Общий sync `MinioStorage.download_verified_to_path` вызывается async wrapper;
production consumers — `processing.submit._stage_artifact` и
`normalization.service._download_verified_artifact`. Иные download/copy helpers
не исправляются автоматически. Точки проверки ниже используют реальные
потребители с подменой только транспорта; production I/O не выполняется.

Минимальный дизайн: существующий sentinel `descriptor = -1` отличает отказ
exclusive create от владения своим partial. В обработчике `OSError` удалять
partial только после успешного создания; сохранить очистку после ошибки
проверки размера/digest, `finally`, `O_EXCL/O_NOFOLLOW`, `0600`, bounded reads,
`fsync`, закрытие descriptor и response close/release. Не вводить дополнительную
систему владения. Concurrent pathname replacement после open и сбои самого
close/unlink/release остаются непроверенными; защита от них не заявляется.

Порядок: уточнение spec/clarify → этот plan → независимая повторная проверка
всех reviewer-owned списков → согласование существующей T014 → analyze →
sync существующего #3361 со штатным canon → permanent regression RED на
старом коде → общий guard → GREEN/ruff/governance → converge и независимое
code review. До admission код/тесты не менять. Исторические marks и receipts
не стирать. Объектные key builders проверяются существующим тестом.

Приёмка FR-029/031/037/045 и SC-025: Quickstart §2026-11-17. Существующий
`source_missing/source_mismatch/temporary_storage_unavailable/storage_unavailable`
контракт сохранить. Processing по-прежнему отображает missing/mismatch в
ArtifactStagingError, прочие storage ошибки в TempStorageUnavailableError;
normalization передаёт StorageTransferError. Все проверки — синтетические
байты и настоящие временные файлы, полный импорт production-модулей, без
реальных записей, почты, платежей и production. Больших сборок нет.

После проверки — commit/push/PR `Refs #3361` до доказанного полного закрытия,
три штатных exact-head/current-base checks через validate-pr-checks.py и
разбор открытых замечаний. Merge штатный, результат и ancestry проверить.
Issue closeout отдельно сверяет исходные критерии T014, подробный русский
комментарий, штатный validate-issue-closeout.py --verify-live и фактическое
состояние. Выпуск/развёртывание/пользовательская приёмка не выводятся из unit PASS.


## 2026-11-17 — T014/#3361: настоящая автоматическая серверная цепочка

Продолжение существующей F099, lane **high-risk-product**, исходная база
`193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка
`codex/099-real-transport-acceptance`. Guard сохранности destination уже слит
в #8128. Его 50 тестов и 100/0 reviewer gate не допускают новый этап.

Clarify: Spec §«фактическая автоматическая обработка»; вопросов 0, продуктовые
границы исходные. Конституция до design: I/II не меняются capture/Stop/индикатор;
III только синтетические данные, очищенное окружение и локальные зависимости;
IV immutable source/attempt и deletion fence; V выпуск отдельно; VI полный
Spec Kit и независимые ворота; VII интерфейс не меняется. Исключений нет.

Решение Phase 0/1: [контракт настоящей цепочки](./contracts/real-transport-acceptance.md)
фиксирует изоляцию до collection/Alembic, реальные зависимости, media-role,
наблюдение исходного verified-download и скачанного результата, сроки/cleanup.
Переиспользуются create_app, post-commit dispatcher, Temporal SDK/factory,
production activity, MinioStorage, FFmpeg и PostgreSQL runner. Новый runtime
сервис, схема, product config или Python dependency не нужны.

Owned implementation paths после admission:
`apps/server/acceptance/playback_normalization_real_transport.py`,
`apps/server/scripts/run_playback_normalization_real_transport.py`,
`apps/server/scripts/run_local_postgres_tests.sh`,
`apps/server/tests/contract/test_local_postgres_test_runner.py` и
`apps/server/tests/contract/test_playback_normalization_real_transport_runner.py`.
Первый содержит собственную MinIO fixture и наблюдение настоящего API/worker;
второй очищает окружение до collection, проверяет зависимости и владеет
процессным пределом/очисткой, делегируя штатному PostgreSQL runner.
Независимое ревью106/14 выявило H1: у прежнего runner нет передачи identity
внешнему владельцу. Разрешено только дополнение служебного контекста
GRAF_TEST_POSTGRES_RESOURCE_DIR по точной схеме нового контракта, image ID /
label/cidfile/state handoff, проверка до SQL и безопасная очистка; обычный
runner contract сохраняется. H2 решается явным acceptance-путём вне обычного
discovery, ранним stdlib guard и подключением существующих fixtures после него;
общие CI/pytest config не меняются. Оба вида управления проверяются отдельными
ограниченными contract tests до настоящего A. Runtime код продукта не меняется;
новые дефекты за этой границей требуют отдельного описания и ревью.
Документы F099 и новый F99 fragment после архивации прежнего fragment свои.

Объём первого независимо проверяемого шага — этап A: положительный WAV и
отрицательный принятый непустой файл. B сохраняет полную format/copy/remux/
track-selection матрицу, C — failure/limits/retry/recovery/backfill/lifecycle.
Все строки B/C и отдельные startup/container/UI/release/deploy ворота остаются
открытыми до собственных доказательств. Два A не являются полным T014 closeout.
Устаревшие dual-source примеры выше — исторические; новые fixtures не создают
legacy v3/v4 upload или provider submission после F275.

Post-design constitution check: те же I–VII соблюдены по описанному контракту,
нарушений/исключений нет. Реализация пока не допущена: обязательны reviewer
всех применимых списков, согласование T014, analyze и sync существующего #3361.
После admission — сначала проверки изоляции/cleanup запускателя, затем real
A без fake fallback, focused lint/governance, converge и independent code review.
Любой setup/skip/cleanup failure сохраняет FAIL. Перед PR проверить свежую
base, изменившиеся зависимости и exact SHA; штатные три checks обязательны.
Новый frozen Full, выпуск/развёртывание и фактическая приёмка — отдельно по
актуальной release guidance. Исторические широкие local-CI указания не требуют
слепого повторения завершённых проверок.

На planning-этапе read-only inventory подтвердил локальные PostgreSQL/MinIO
images и FFmpeg/ffprobe8.1.2, но это не запуск ресурсов. В собственной venv
24 прямых зависимости совпали с lock, evaluation/gepa0.1.4 отсутствует;
штатный runner требует этот extra. Перед опытом нужна явная подготовка frozen
окружения и проверка его готовности, без скрытой установки при collection.
Online master продвинулся до2805b0f91d5c6d13aad13edb573274b8460e1d19:
delta общего PG fixture затрагивает только отдельный isolated bootstrap;
используемый worker/media prefix побайтно сохранён. HEAD193e сохранён до
окончания review; до реализации/PR требуется актуализация собственной базы
и зависимых документов/evidence без потери текущих изменений.
