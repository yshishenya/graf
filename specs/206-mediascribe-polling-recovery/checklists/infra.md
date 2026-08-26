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
- [X] Focused tests и `infra/scripts/ci-local.sh --fast` пройдены.
- [X] Production deploy/reprocess выполняются только через отдельный release gate.
