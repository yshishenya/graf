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
**Release Gate**: no deploy in this slice; focused tests and `ci-local.sh --fast`
**Target Platform**: GRAF server and embedded/web cabinet
**Project Type**: server-rendered web service with Temporal worker
**Performance Goals**: no busy polling; bounded provider request delay
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
no new service, dependency, migration or abstraction.

## Дополнение: восстановление повреждённого источника

Для ручных загрузок playback-нормализация остаётся отдельным lifecycle-путём:
MediaScribe получает authoritative `media`, а canonical M4A используется только
для проигрывания. Если строгий первый decode обнаруживает повреждение, pipeline
однократно выполняет bounded tolerant FFmpeg transcode с `ignore_err` и
`discardcorrupt`. Результат публикуется только после строгой проверки output;
сверка длительности с принятой revision блокирует тихо усечённые файлы.

Recovery не добавляет новую durable-сущность или миграцию. Audit сохраняет
только boolean `recovered_source`, без байтов аудио, текста или stderr.

## Complexity Tracking

Нет нарушений конституции. Watchdog reuses `FAILED_RETRYABLE` and existing
manual check surface instead of adding a new durable state.
