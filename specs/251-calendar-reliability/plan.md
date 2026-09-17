# Implementation Plan: Надёжные календари
**Branch**: codex/251-calendar-reliability | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)
## Summary
Исправить аудит, сохраняя полные provider-authorized owner данные. Переиспользовать providers/sync/worker и существующие UI routes.
## Technical Context
Python 3.13 / FastAPI / SQLAlchemy async / PostgreSQL; Swift 6; vanilla JS. Для корректного iCalendar применить icalendar 7.3.0 и recurring-ical-events 3.8.2 (новые зависимости оправданы RRULE/DST/exceptions, ручной parser удаляется). Обновить pyproject.toml, uv.lock, constraints.txt вместе.
## Risk / validation lane
High-risk product area: backend, privacy, credentials, lifecycle, UX. Full Spec Kit sequence; focused PostgreSQL + provider + web JS/browser + Swift tests; scoped fast gate before review. Production only after explicit approved commit/release and exact-SHA governance-fast/release-full/CD dry-run.
## Constitution Check
Pre-research PASS: owner instruction supersedes earlier private-content suppression in calendar specs, no constitution rule requires it. Auth/tenant/escaping, secure URLs, read-only provider access, deletion, visible manual capture remain. No content-bearing external AI calls. Post-design PASS subject to reviewer checklist. Legacy untouched; no compatibility aliases.
## Project Structure / ownership
- Provider/content: calendar/normalize.py, caldav.py, google.py, providers.py, unit provider tests; source content preserving, library recurrence, tombstones, participants, links.
- Sync: calendar/worker.py, sync.py, service.py, provider lifecycle tests, models/migration as needed; one-minute scheduler, 5-minute reclaim + claim identity CAS, catalog refresh and selection fence. Existing last_sync_started_at serves as claim identity, no separate job framework.
- Owner content persistence: title Text; full description/location encrypted using existing Fernet and extras envelope, authenticated owner accessor reconstructs complete fields; no private content in logs. Preserve source labels/participant names without metadata-content filters. Migration must provide guarded rollback without truncation. Force one full resync of existing Google cached data when content representation version changes.
- UI: cabinet/view_models.py, rendering.py, calendar_helpers.py, calendar routes, calendar_settings.html, cabinet.js; refresh only display/status fragments, preserve dirty forms/dialogs, source-isolated errors. Native CalendarTray + client call path for truthful refresh.
## Implementation sequence
Tests then provider/content and UI independent [P] work; sync/persistence integrates provider tombstones sequentially; final end-to-end/convergence review. Schema tests and old privacy fixtures updated only where owner contract intentionally changed; unrelated context restrictions retained.
## Validation
See quickstart.md. Existing 258 server + 28 native baseline passes are audit evidence, not change validation. Tests must assert complete content roundtrip, not merely encrypted field presence; no raw real fixtures. Browser synthetic journey connects/selects/imports and exercises no-button updates, long sync/dirty form, link action, disconnect/reconnect. External live test limitations explicit.

## Design clarification 2026-09-06
Полное owner content (title, description, location, participants, attachments) сохраняется в encrypted envelope. Индексные/plaintext текстовые поля могут сохранять обычный текст, но тексты с URL/кодом доступа хранятся только в envelope и восстанавливаются исключительно для авторизованного owner read, без ORM flush открытого содержимого. Никакого усечения при шифровании/дешифровании. Проверять claim и исходный выбор под source row lock ДО любого изменения каталога, событий, cursor или error state; claim не изменять в текущем исполнителе до финального результата. Для floating time сначала использовать timezone компонента/календаря X-WR-TIMEZONE; при отсутствии зоны явно сообщать limitation, не назначать UTC молча. Открытие ссылок только HTTPS, исходный текст сохраняется. Владелец разрешил использовать подключённые production календари для отдельно помеченных тестовых событий без участников; existing private meetings не менять.
