# Implementation Plan: Стабильные статусы обработки в списке встреч

**Branch**: `codex/202-fix-processing-list-flicker` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Устранить двойное владение строкой: не заменять весь meeting list каждую секунду
из-за submitted/processing, резервировать readiness-строку на сервере, опрашивать
content-safe projection только для server-marked processing строк раз в 15 секунд
и делать один обычный list refresh при terminal/processed transition.

## Technical Context

**Language/Version**: Python 3.12, vanilla JavaScript, server-rendered HTML

**Primary Dependencies**: FastAPI/Jinja, HTMX 2.x; новых зависимостей нет

**Storage/API**: Без миграций и новых endpoint; существующий content-safe
`GET /api/v1/meetings/{meeting_id}/processing`

**Testing**: Pytest rendering/integration contracts, Node VM lifecycle harness,
rendered browser and embedded-width QA

**Risk / Validation Lane**: `significant/high-risk UX`; shared processing truth,
accessibility, browser/WebView parity and processing-facing workflow

**Release Gate**: implementation + focused/fast validation; deploy не входит

**Constraints**: Сохранить identity/generation/auth fences, focus/selection,
metadata-only evidence и upload/playback polling

## Constitution Check

- Capture and user control: **PASS** — capture/upload custody не меняются.
- Privacy and truthfulness: **PASS** — используется только content-safe metadata;
  terminal truth остаётся серверной.
- Processing boundary: **PASS** — MediaScribe/Temporal/API semantics не меняются.
- Accessibility/clean-room UX: **PASS** — стабильная геометрия, focus/selection и
  aria-live входят в acceptance.
- Spec-driven delivery: **PASS** — clarify/checklist/tasks/analyze выполняются
  до implementation.

## Implementation Approach

1. В server presentation заранее вернуть существующий active-processing
   readiness copy, чтобы DOM-слот и высота строки были стабильны с первого paint.
2. Исключить submitted/processing из условия секундного full-list HTMX polling;
   upload progress, empty embedded discovery и playback preparing не менять.
3. Ограничить processing projection только `.meeting-status[data-status-kind=processing]`.
4. Использовать существующий 15-second throttle как lifecycle timer и переиспользовать
   текущие identity/generation/AbortController fences.
5. При `processed`, `blocked`, `failed_terminal` или `canceled` не рисовать
   client terminal copy, а один раз вызвать существующий authoritative list refresh.
6. При upload/playback progress swap сохранить bounded projection state и
   синхронно восстановить его только на совпавшей processing-строке.

## Validation Plan

1. Сначала добавить failing regression на server poll contract и JS sequence:
   active processing + две failed строки + progress swap + повторные ticks +
   terminal transition.
2. Запустить focused rendering/list/static-asset tests.
3. Запустить cabinet fragment/list integration tests и JS syntax/Ruff checks.
4. Проверить browser и embedded-width rendering на локальном metadata-only fixture.
5. Выполнить `infra/scripts/ci-local.sh --fast` перед PR; full lane оставить
   exact-SHA deploy gate.

## Project Structure

```text
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/contract/test_cabinet_static_assets_contract.py
apps/server/tests/integration/test_cabinet_meeting_list.py
CHANGELOG.md
```

## Complexity Tracking

Новых endpoint, dependency, component abstraction или OOB protocol нет. Текущий
server rendering, processing endpoint, refresh form и stale-response fences
достаточны.
