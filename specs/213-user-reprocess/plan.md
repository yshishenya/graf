# Implementation Plan: Повторная обработка записи пользователем

**Branch**: `codex/213-user-reprocess` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/213-user-reprocess/spec.md`

## Summary

Добавить владельцу готовой встречи действие `Повторно обработать запись` в обычное меню `Ещё`. Переиспользовать существующие ProcessingWorkflow, MediaScribe job, Temporal workflow, статус, таймер и ручную проверку. Во время новой попытки все пользовательские каналы продолжают использовать последний полный результат с расшифровкой и диаризацией; новый полный результат автоматически становится текущим. Административных страниц, операторских ролей, причин и отдельного аудита нет.

## Technical Context

**Language/Version**: Python 3.12; server-rendered Jinja2/HTML/CSS/JavaScript

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL, Alembic, Temporal Python SDK and existing MediaScribe client; no new dependencies

**Storage**: no schema changes; existing workflow identity, result, segment, outcome and media tables are reused

**Testing**: pytest unit/contract/integration, Temporal replay tests, cabinet browser contracts and focused keyboard/accessibility acceptance

**Risk / Validation Lane**: significant/high-risk feature — shared result selection, Temporal attempt identity, user authorization and a customer-facing recovery flow change

**Target Platform**: Linux server; responsive browser and embedded macOS cabinet

**Performance Goals**: launch returns without waiting for MediaScribe; no polling faster than the existing cadence; user-facing result selection stays one indexed query

**Constraints**: owner-only action; one active attempt per meeting/revision; no second quota charge for the same revision; no partial transcript; transcript and diarization become visible together; outcomes remain independent; no fake progress or browser-owned retry

**Scale/Scope**: one endpoint, one corrected shared result selector, exact Temporal row identity and existing cabinet components

## Constitution Check

*GATE: Passed before implementation.*

- **Spec-first / high-risk governance**: PASS — scope clarification removed admin work and plan/contracts/tasks are refreshed before code.
- **Privacy and secrets**: PASS — no meeting content, provider payload or credential enters the new request/status contract.
- **Authorization**: PASS — launch and replacement retry revalidate `Meeting.created_by_user_id` against the principal.
- **Published-result safety**: PASS — customer content uses one complete-result selector; operational latest workflow cannot hide the prior complete result.
- **Temporal durability**: PASS — durable workflow state precedes Temporal RPC; exact row UUID is carried to activities; existing duplicate and unknown-POST recovery remains.
- **Deletion/source precedence**: PASS — existing meeting lock, deletion epoch, accepted revision and fingerprint fences are unchanged.
- **AI/outcomes**: PASS — new transcript does not wait for outcomes; current outcome slots and CAS remain independent.
- **Accessibility and honest status**: PASS — existing focus/live-region/countdown patterns are reused.
- **Minimality**: PASS — no meeting publication pointer, command table, admin UI, queue, scheduler, workflow type or dependency is introduced.

## Design

### 1. Durable request admission

The new owner endpoint receives the workflow ID shown by the page, locks the meeting and workflow rows, verifies the expected accepted revision and complete current result, then:

- returns the existing immediate successor when this predecessor was already used;
- returns the one active successor;
- or creates a new workflow with the next ordinal.

The predecessor/successor comparison survives a lost response from either browser tab without a command table or schema field. The revision-scoped usage reservation keeps billing idempotent.

### 2. One effective complete result

Extend `effective_processing_result_query()` with the existing complete predicate and workflow-attempt ordering. Latest workflow remains status truth; the effective result becomes content truth for detail/share/export/egress/desktop sync/outcomes.

No persistent publication pointer is added because import already commits complete result data atomically and rejects stale workflow/revision/deletion lineage.

### 3. Exact Temporal attempt

Add `processing_workflow_id` to all new processing payloads. The activity and its error-persistence path load that exact row and verify payload lineage. A nullable legacy fallback preserves replay of old histories without changing workflow command order.

### 4. Existing UI and retry

Reuse the meeting `Ещё` menu, dialog infrastructure, processing status block, `GET /processing`, `POST /processing/check`, server time and `schedule_generation`. Add only the launch confirmation and replacement-specific copy.

## Validation Plan

1. **Admission CAS**: one predecessor creates at most one immediate successor; replay, two tabs and stale predecessors are deterministic.
2. **Selector**: old complete + new active/partial/terminal remains old; new complete wins by attempt ordinal even when old `result_version` is higher.
3. **Readers**: detail, full share, exports, egress, desktop sync and outcomes use the same effective result.
4. **Admission**: owner, non-owner, stale revision, missing source, replay, two tabs, active coalescing, terminal fresh request and no second quota charge.
5. **Temporal**: exact workflow row, legacy payload replay, delayed old activity, ambiguous start and same-job manual retry.
6. **UX/a11y**: menu eligibility, confirmation, busy state, quiet countdown, `Повторить сейчас`, refresh and terminal recovery.
7. **Repository gates**: feature quickstart and focused tests during implementation, then `infra/scripts/ci-local.sh --fast`. Full CI is reserved for an approved frozen release candidate/deploy.

## Project Structure

```text
specs/213-user-reprocess/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── user-reprocess-api.md
│   ├── published-processing.md
│   ├── temporal-reprocessing.md
│   └── ui-ia-status.md
├── checklists/
└── tasks.md

apps/server/src/twobrain_rec_server/
├── api/{processing.py,schemas.py}
├── cabinet/
│   ├── {queries.py,view_models.py,egress.py,exports.py}
│   ├── static/cabinet/cabinet.js
│   └── templates/cabinet/{fragments/meeting_governance.html,pages/meeting_detail_content.html}
├── ingest/desktop_sync.py
├── outcomes/{service.py,ai_service.py}
├── processing/{results.py,status.py,store.py}
└── workflows/{processing_workflow.py,temporal_client.py,worker.py}
```

## Complexity Tracking

The initial plan proposed an operator command table, admin journal, explicit meeting publication pointer and request-ID column. The clarified owner flow removes all four. Existing workflow predecessor/successor identity plus the complete-result/import fences provides the required idempotency and automatic publication behavior.
