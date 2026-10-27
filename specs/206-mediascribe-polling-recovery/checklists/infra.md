# Infrastructure Checklist: MediaScribe polling recovery

**Purpose**: Проверить границы MediaScribe, Temporal и durable recovery.
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md)

- [X] Provider credentials остаются только на сервере.
- [X] Existing provider job/idempotency key используется для reconciliation.
- [X] Pending и retryable ответы не создают новый multipart job.
- [X] Retry-After/next_retry_at ограничены и не приводят к busy polling.
- [X] Watchdog deadline отделён от короткого generic retry limit.
- [X] Temporal wait использует durable timer и manual signal/update.
- [X] Workflow deterministic и replayable.
- [ ] Focused tests и `infra/scripts/ci-local.sh --fast` пройдены.
- [X] Production deploy/reprocess выполняются только через отдельный release gate.
- [X] Удалён только мёртвый runtime legacy; historical dual-track и Temporal replay compatibility сохранены.
- [X] Provider submit запрещён до exact normalization `ready` artifact.
- [X] Existing provider job обходит readiness gate и только продолжает polling.
- [X] No-archive canonical остаётся в existing transient lifecycle без storage quota.
- [X] Crash до Temporal start восстанавливается deterministic reconciler.
- [X] Новый workflow type, task queue, persistent WAV и FFmpeg в processing worker не требуются.

## Независимая сверка 28.10.2026

Подтверждены 14 из 15 пунктов в пределах требований, исходников и синтетических
проверок; новый успешный `infra/scripts/ci-local.sh --fast` пока отсутствует.
Первый новый запуск остановлен обязательной проверкой Legacy Impact; это FAIL,
не PASS. Исправление документов само по себе не доказывает повторный fast.
Постатейные основания и границы T029/T030/T031: [отчёт](../review-t029-20261028.md).
