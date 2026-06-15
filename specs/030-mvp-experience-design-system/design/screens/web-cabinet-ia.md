# Web Cabinet IA

## Purpose

Full browser product surface for meeting library, upload, processing, review,
account/workspace, access, deletion, and future admin surfaces.

## Navigation

Primary sidebar:

- `Встречи`
- `Обзор`
- `Доступ`
- `Рабочее пространство`
- `Журнал`
- `Настройки`

Upload and processing are not permanent top-level navigation items in the MVP
cabinet. Upload starts from the meetings header, empty state, row action, or
drag/drop sheet. Processing is shown as meeting row/detail status, filter
state, and notification state.

Secondary/browser-only groups:

- Team
- Billing
- Sharing
- Downloads
- Deletion reports
- Integrations
- Developer/API
- Help
- Legal

## Home Priority

The first browser viewport must answer:

- What meetings exist?
- Which meeting needs attention now?
- What is processing or needs attention?
- What can I upload from this context?
- What is only on a device, failed, deleted, or access-blocked?

Do not lead with billing, analytics, admin settings, or generic cards.

## Route Classes

- `/meetings`: default library.
- `/upload`: manual media upload.
- `/meetings/:id/status`: processing and degraded status.
- `/meetings/:id`: complete review.
- `/meetings/:id/speakers`: server-owned speaker assignment, also embeddable as
  `/desktop/meetings/:id/speakers`.
- `/settings/account`: account/security basics.
- `/workspace`: workspace summary and policy.
- `/workspace/team`, `/workspace/billing`: browser-only.
- `/sharing`, `/downloads`, `/deletion-reports`: browser-only or deferred.

## Header

- Workspace name.
- Search/command input.
- `Загрузить медиа` button.
- Desktop app status/handoff.
- Account menu.

## Desktop Mirror Rule

Browser can mirror active recording or local queue state from the desktop, but
it cannot start/stop local recording in MVP. Browser CTAs must say
`Open desktop app` / `Открыть приложение`, not imply that the web cabinet starts
capture.

## Acceptance Evidence

Covered by Figma `V8 10 - Веб-кабинет: встречи и фильтры`,
`V8 11 - Веб-детали встречи и транскрипт`, `V8 12 - Поделиться, экспорт, удаление`,
`V8 14 - Правила интерфейса и QA`, and `design/validation-evidence.md`.
