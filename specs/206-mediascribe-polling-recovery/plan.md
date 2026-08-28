# Implementation Plan: Надёжное ожидание результата MediaScribe

**Branch**: `206-mediascribe-polling-recovery` | **Date**: 2026-08-26 | **Spec**: [spec.md](spec.md)

## Summary

Разделить короткий generic recovery attempt limit и длительный provider polling.
Обычный pending MediaScribe job будет продолжаться до настроенного watchdog
deadline, а достижение deadline станет recoverable `FAILED_RETRYABLE` состоянием
с manual same-job check. Provider `failed`, malformed response и local input
failure останутся terminal.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, Jinja
**Primary Dependencies**: Temporal Python SDK, SQLAlchemy, Pydantic, httpx
**Storage**: PostgreSQL; existing ProcessingWorkflow/MediaScribeJob rows
**Testing**: pytest, Temporal WorkflowEnvironment, static cabinet contracts
**Risk / Validation Lane**: high-risk-feature — MediaScribe, Temporal, durable
recovery and user-visible degraded/error UX.
**Release Gate**: scoped/current-SHA validation, PR/review/merge/release/deploy and
production E2E are authorized; do not repeat Full CI, but preserve exact-SHA and
all repository deployment gates
**Target Platform**: GRAF server and embedded/web cabinet
**Project Type**: server-rendered web service with Temporal worker
**Performance Goals**: no busy polling; bounded provider request delay; manual
upload normalization performs one tolerant transcode plus one strict output
decode and no preliminary full source decode
**Constraints**: same-job reconciliation, server-only credentials, no content in logs
**Scale/Scope**: one processing workflow and shared meeting detail/list projection

## Constitution Check

### Before research

- PASS — MediaScribe credentials remain server-side.
- PASS — Provider errors and uncertainty are not fabricated; raw content remains
  outside ordinary logs/evidence.
- PASS — Temporal remains the durable workflow engine and workflow code stays
  deterministic.
- PASS — Existing same-job/idempotency fencing is reused; no duplicate upload.
- PASS — UX keeps transcript hidden until diarization and separates summary.

### After design

- PASS — `RetrySchedule.stop_reason` is in-memory metadata; no migration needed.
- PASS — Watchdog uses existing `FAILED_RETRYABLE` and recovery controls, so no
  new status enum or abstraction is introduced.
- PASS — Manual check wakes a durable workflow signal/update and clears the UI
  countdown through the existing action path.

## Validation Plan

1. Focused scheduler, worker, submit, status projection and Temporal tests.
2. Existing MediaScribe integration/failure tests plus new pending/watchdog cases.
3. Cabinet static/accessibility checks for header, pending placeholder and UX copy.
4. `git diff --check`.
5. `infra/scripts/ci-local.sh --fast` before PR readiness.
6. No production reprocess/deploy; release uses the separate exact-SHA gate.

## Project Structure

```text
specs/206-mediascribe-polling-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/processing-recovery.md
├── checklists/{requirements,ux,infra}.md
└── tasks.md

apps/server/src/twobrain_rec_server/
├── processing/{recovery.py,submit.py,status.py,store.py,pickup.py}
├── workflows/{worker.py,processing_workflow.py}
└── cabinet/{view_models.py,static/cabinet/cabinet.js,templates/cabinet/pages/meeting_detail_content.html}
```

**Structure Decision**: Reuse existing processing, Temporal and cabinet modules;
no new service, dependency, entity or abstraction. Migration
`0083_result_workflow_lineage` conservatively backfills the direct workflow
lineage of revision-scoped processing results. `0084_processing_recovery` is an
append-only follow-up to the production `0083` head and adds the recovery/purge
indexes and journal foreign key; it does not create a second migration head.

## Дополнение: canonical manual-upload pipeline

Для каждой ручной загрузки GRAF создаёт normalization job независимо от
`archive_audio`. Только ветка `manual_upload` включает tolerant-first mode;
capture и остальные single/dual-source пути сохраняют существующие быстрые
copy/remux/transcode решения. Media worker выполняет bounded `ffprobe`, затем один tolerant
FFmpeg transcode с `ignore_err`/`discardcorrupt` и строгую полную проверку только
готового canonical M4A. Preliminary strict source decode удаляется.

Processing workflow по-прежнему стартует после accepted commit, чтобы
сохранить durable intent, quota/transient lifecycle и пользовательское recovery
состояние. Существующая single-step activity до первого provider submit
проверяет normalization job:

- `ready` + exact validated artifact — canonical M4A становится единственным
  manual-upload source для MediaScribe;
- `queued/running/publishing/retry_wait` — возвращается внутренний
  `normalization_pending`, после чего workflow ждёт bounded Temporal timer;
- `terminal/cancelled` — provider egress запрещён и сохраняется локальная
  terminal/cancelled причина.

Gate обходится только после подтверждённого provider `external_job_id` либо при
явном same-idempotency-key reconciliation неизвестного результата POST. Локальная
строка job без `external_job_id` остаётся pre-egress и повторно обязана доказать
exact canonical identity и request fingerprint. После подтверждённого provider
job workflow продолжает same-job polling и никогда не повторяет multipart upload.
До получения `external_job_id` неизвестный POST может быть повторён только
exact тем же multipart envelope и durable idempotency key. HTTP attempts может
быть несколько, но provider job остаётся один; новый key/job разрешён только
после подтверждённого terminal provider outcome и явного нового business attempt.

`archive_audio=false` использует тот же canonical artifact временно: единый
revision policy helper запрещает playback egress и storage reserve/commit, но
оставляет processing usage. Transient owner создаётся в finalize-транзакции.
Purge сначала фиксирует intent/fences в существующем journal, затем удаляет
только source/playback objects и после этого согласует DB states. Он блокирует
Meeting → workflows → normalization jobs → attempts → artifacts, учитывает все
attempts/workflows revision и самый ранний hard deadline. Processing worker не
получает FFmpeg и новый WAV не создаётся.

Для crash-gap `ProcessingWorkflow(starting)` → Temporal start добавляется
bounded reconciler. После quota admission `WORKFLOW_STARTED` фиксируется до
Temporal RPC; start использует deterministic workflow id и явную
`REJECT_DUPLICATE` policy. Running conflict переиспользуется, закрытый duplicate
заменяется новым Temporal execution без смены существующей provider operation,
ambiguous RPC не терминализирует intent. Новая durable сущность, новый workflow
type и новая task queue не требуются.

Workflow-команда до результата activity не меняется. Ветка
`normalization_pending` добавляется после существующего activity result; replay
совместимость подтверждается сохранённой pre-change history перед deploy.

Audit сохраняет policy fact `normalization_mode=tolerant`, проходы, bounded
reason/outcome и artifact identity; он не утверждает фактическое восстановление
повреждения без доказательства и не сохраняет audio/content/stderr.

После terminal hardening текущая попытка определяется только обязательной
цепочкой workflow → MediaScribe job → result. Runtime-эвристики старого result
контракта и фоновый legacy-lineage reconciler удалены; historical dual-track
чтение и Temporal patch markers сохранены для старых записей и replay. Detail
polling остаётся low-frequency и не теряется при скрытом окне до terminal
projection.

## Performance and capacity

- Initial media-worker concurrency остаётся `1` при CPU limit `1`.
- Tolerant transcode ограничен 4 часами + 1 секунда и 128 MiB output.
- Exact manual-upload subprocess budget: один source `ffprobe`, ноль source full
  decode, один tolerant transcode с `-t 14401`, один output `ffprobe`, один
  strict output full decode. Generated output может повторно читаться для hash
  verification до появления измеренного I/O bottleneck.
- Source probe duration обязана быть finite, positive, known и не больше 4 часов;
  stream/format и accepted-revision mismatch обрабатываются fail-closed по
  явному малому tolerance, а не существующему допуску до 60 секунд.
- Normalization readiness checks используют durable `next_attempt_at` либо
  bounded fallback timer и не расходуют provider retry/deadline watchdog.
  Workflow выполняет `continue_as_new` по подсказке Temporal или после
  фиксированного числа readiness checks, ограничивая history growth.
- Метрики: normalization queue age, wall duration, outcome и processing gate
  wait; Task Queue Fairness/дополнительная concurrency добавляются только при
  измеренном backlog/starvation.
- Повторное хеширование bounded output и `faststart` не оптимизируются до
  измеренного I/O bottleneck.

## Complexity Tracking

Нет новых сервисов, таблиц, task queues, WAV-артефактов или workflow types.
Watchdog reuses `FAILED_RETRYABLE`; normalization readiness остаётся внутренним
activity result. Trust-boundary output validation, deletion fences и transient
lifecycle не упрощаются.
