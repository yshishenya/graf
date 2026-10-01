# Implementation Plan: Понятная повторяющаяся встреча

**Branch**: `283-calendar-series-ux` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)
**Input**: `specs/283-calendar-series-ux/spec.md`

## Summary

Убрать повторение и смешение расписания с результатами. Сохранить компактный обзор, добавить два периода внутри нативного details, спокойные строки и единую справку. Будущие и прошлые страницы запрашивать отдельно, чтобы 180 дней истории не вытесняли ближайшие даты.

## Technical Context

**Language/Version**: Python 3.12+, plain JavaScript/CSS, существующий HTML renderer.
**Primary Dependencies**: FastAPI, SQLAlchemy, штатный Intl/GRAFTime, native details/buttons. Новых зависимостей нет.
**Storage**: существующие PostgreSQL snapshots и recording links, без миграций.
**Testing**: существующие pytest и Playwright production-asset harness.
**Risk / Validation Lane**: high-risk-feature: user-facing UX, privacy и API compatibility.
**Release Gate**: разработка/PR; production только после отдельного разрешения, frozen release-full и cd dry-run.
**Target Platform**: браузер и WKWebView GRAF Dev на macOS.
**Project Type**: существующий web cabinet внутри desktop.
**Performance Goals**: максимум 50 экземпляров/страницу, записи в существующем candidate limit200; Join feedback≤200ms maximum, series p95≤500ms (F279 SC-007).
**Constraints**: F279 identity/authorization/Join guards; без реальных звонков, записи и повторной проверки VoiceOver.
**Scale/Scope**: только home recurring-series; без нового editor/filter/history service.

## Constitution Check

До и после design: PASS. Capture/Stop/consent не меняются; Join не записывает. ACL/deletion/privacy сохраняются на каждом запросе. Никаких секретов/частного содержимого в evidence. Независимый код/собственный inline SVG; внешних ассетов нет. Наблюдаемая и опубликованная логика Krisp разделения предстоящей встречи и записей сохраняется; inline и два периода адаптируют существующий GRAF home. Обязательные ux/security reviewer gates перед tasks и implement. Корневой AGENTS не меняется.

## Phase 0: Research

Официальные источники и наблюдение: [research.md](research.md). Не извлекать закрытый код или данные. Выбор: встроенное раскрытие (сохранение контекста), native переключатели, общий часовой пояс в кратком header, подробности только по запросу. Не угадывать RRULE и completeness.

## Phase 1: Design

API добавляет optional `view=all|upcoming|history` (default all). Для новых периодов подписанный context хранит view и anchor; query фильтрует ends_at относительно anchor. history сортируется starts_at/id DESC с обратным cursor comparison. Cursor decoder восстанавливает signed anchor; старый all contract остаётся. Response добавляет temporal_state по snapshot anchor для ближайшей/текущей метки без передачи скрытого времени. Авторизация precedes payload. См. [contracts/calendar-series.md](contracts/calendar-series.md), [data-model.md](data-model.md).

HTML summary «Даты и записи», имя серии в data только уже разрешённое. В body именованная группа buttons aria-pressed, period hint, rows, live-status, more, единая help details. Ровно одно название на overview; exception title only if different, at most two visual lines and full authorised title in tooltip. Inline help contains truthful saved-window and bounded recording search, link to general meeting list. Строки use existing type/space/color tokens, 12–16px text, soft dividers, muted metadata, 32px actions, status and exception badges with text. Focus on small controls, no outer giant white border. No CSS descendant rules applied to arbitrary nested divs. Native keyboard semantics; don't pretend ARIA tabs without proper key behavior.

JS WeakMap selected-view state, AbortController on switch/close, request identity after await, timeout, fresh scope checks and coalesced refresh. No caching previously authorised rows across period changes. Keep count/period/focus on calendar refresh; expiry clears old rows. Pagination error keeps only already authorised current rows; refresh error clears old data. Changed title masks respected, hidden timestamp never written. Existing shared Join listener unchanged.

## Validation Plan

[quickstart.md](quickstart.md): API temporal boundaries/order/cursors/compatibility/privacy; real production-assets browser states plus retained native-bridge/browser Join guards. Inspect synthetic screenshots dark/light/wide/narrow/zoom. Only /Applications/GRAF Dev.app via harness after validated approved commit. PR governance-fast, macos-pr, pr-metadata exact SHA/base; frozen release-full required for release, not claimed from local tests.

## Project Structure

`apps/server/src/twobrain_rec_server/{api/calendar.py,calendar/series.py,api/schemas.py}` — scoped view contract.
`apps/server/src/twobrain_rec_server/cabinet/{rendering.py,static/cabinet/calendar-series.js,static/cabinet/cabinet.css}` — production UI.
`apps/server/tests/{unit/test_calendar_series.py,contract/test_calendar_join_series_contract.py,browser/calendar_series.mjs}` — existing checks.
`changes/unreleased/F283.yaml` — owned fragment.
`specs/283-calendar-series-ux/` — intent, design, review and validation.

## Complexity Tracking

No constitution violations; no dependencies or abstractions added. Existing query, cursor and UI helpers extended in place.
