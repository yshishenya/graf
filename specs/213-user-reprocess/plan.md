# Implementation Plan: Повторная обработка записи пользователем

**Branch**: `codex/213-reprocess-ux` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/213-user-reprocess/spec.md`

## Summary

Оставить действие `Повторно обработать запись` в обычном меню `Ещё`, но упростить путь владельца: коротко предупредить о сбросе ручных имён после успеха, скрыть прежнее содержимое и плеер под одним нейтральным индикатором, а при окончательной ошибке вернуть прежнюю версию и предложить повторный запуск. Переиспользовать существующие ProcessingWorkflow, status polling, complete-result selector и fragment response; новых сущностей и зависимостей нет.

## Technical Context

**Language/Version**: Python 3.12; server-rendered Jinja2/HTML/CSS/JavaScript

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL, Alembic, Temporal Python SDK and existing MediaScribe client; no new dependencies

**Storage**: no schema changes; existing workflow identity, result, segment, outcome and media tables are reused

**Testing**: pytest unit/contract/integration, Temporal replay tests, cabinet browser contracts and focused keyboard/accessibility acceptance

**Risk / Validation Lane**: significant/high-risk feature — shared result selection, Temporal attempt identity, user authorization and a customer-facing recovery flow change

**Target Platform**: Linux server; responsive browser and embedded macOS cabinet

**Performance Goals**: launch returns without waiting for MediaScribe; no polling faster than the existing cadence; user-facing result selection stays one indexed query

**Constraints**: owner-only action; one active attempt per meeting/revision; no second quota charge for the same revision; no partial transcript; transcript, speaker UI and player swap together; manual speaker names are result-scoped and are never reconciled; outcomes remain independent; no fake progress or browser-owned retry

**Scale/Scope**: one endpoint, one corrected shared result selector, exact Temporal row identity and existing cabinet components

## Constitution Check

*GATE: Passed before implementation.*

- **Spec-first / high-risk governance**: PASS — scope clarification removed admin work and plan/contracts/tasks are refreshed before code.
- **Privacy and secrets**: PASS — no meeting content, provider payload or credential enters the new request/status contract.
- **Authorization**: PASS — launch and replacement retry revalidate `Meeting.created_by_user_id` against the principal.
- **Published-result safety**: PASS — the complete-result selector keeps the prior result durably available; only the owner's presentation hides it during an active replacement and restores it after terminal failure.
- **Temporal durability**: PASS — durable workflow state precedes Temporal RPC; exact row UUID is carried to activities; existing duplicate and unknown-POST recovery remains.
- **Deletion/source precedence**: PASS — existing meeting lock, deletion epoch, accepted revision and fingerprint fences are unchanged.
- **AI/outcomes**: PASS — new transcript does not wait for outcomes; current outcome slots and CAS remain independent.
- **Accessibility and honest status**: PASS — existing dialog focus and polite live region are reused; hidden content leaves the accessibility tree and replacement retry internals stay out of user copy.
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

### 4. Existing UI and replacement presentation

Reuse the meeting `Ещё` menu, dialog infrastructure, processing status block, `GET /processing` polling and the existing full meeting-detail fragment response. A server-rendered replacement marker prevents a stale-content flash after refresh; the same marker is updated from status projections after launch. While active, CSS hides the old detail content and adjacent player and the status card collapses to one neutral title. On terminal failure the marker clears, revealing the unchanged DOM. On success the main detail and adjacent player are replaced in the same JavaScript turn from one response so speaker labels cannot diverge.

Normal `result_not_ready`, automatic retry timing, unknown provider outcome and temporary status-fetch failures keep the same neutral presentation. Replacement-specific manual check/countdown actions are not exposed; initial-processing recovery remains unchanged.

## Validation Plan

1. **Admission CAS**: one predecessor creates at most one immediate successor; replay, two tabs and stale predecessors are deterministic.
2. **Selector**: old complete + new active/partial/terminal remains old; new complete wins by attempt ordinal even when old `result_version` is higher.
3. **Readers**: detail, full share, exports, egress, desktop sync and outcomes use the same effective result.
4. **Admission**: owner, non-owner, stale revision, missing source, replay, two tabs, active coalescing, terminal fresh request and no second quota charge.
5. **Temporal**: exact workflow row, legacy payload replay, delayed old activity, ambiguous start and same-job manual retry.
6. **UX/a11y**: minimal warning, server-rendered and dynamic hiding, neutral wait across retry/status failures, terminal restoration, atomic main/player replacement, web/embedded parity and keyboard/screen-reader behavior.
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
