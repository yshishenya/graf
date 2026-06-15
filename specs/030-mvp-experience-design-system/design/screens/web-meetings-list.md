# Web Meetings List

## Purpose

Browser home for meetings, upload entry, and current processing status. The
meeting is the core object: recording, upload, validation, transcription,
speaker review, notes, share/export/delete, and errors appear as meeting row or
meeting-detail states instead of standalone MVP destinations.

## Layout

- Target: `1440 x 900`.
- Sidebar: `248 px`.
- Header: `64 px`.
- Content max width: `1120 px`.
- Filter row: `44 px`.
- Table/list row: `64 px`.

## Header

Left:

- `Встречи` title.
- Count and last sync/update.

Right:

- Primary `Загрузить медиа`.
- Secondary `Открыть приложение для записи`.
- Refresh icon.

## Search And Filters

Search:

- Placeholder: `Поиск по встречам, тексту, людям`.
- Global search may also open a command palette over the current workspace, but
  it does not replace the list route.

Filters:

- Date: `Дата`.
- Status: `Статус`.
- Source: `Источник`.
- Owner/shared: `Доступ`.
- People/company: `Люди` / `Компания`.
- Tags: `Теги`.
- Sort: `Сортировка`.

Rules:

- Active filter chips appear only when a value exists.
- Empty filter categories stay inside a compact filter menu.
- Desktop embedded subset shows only saved views and search.
- Browser can expose full filter chips, historical ranges, and broad search.

## List Row

Required cells:

- Source icon.
- Title.
- Owner/source provenance.
- Duration.
- Status chip.
- Progress if active.
- Updated/date.
- Primary action.
- Overflow menu.

Allowed row actions:

- `Открыть`.
- `Подробнее`.
- `Повторить`.
- `Дозагрузить с Mac`.
- `Отчет об удалении` when relevant.

Browser-owned overflow:

- Share.
- Export.
- Download.
- Delete.

## Required States

- Empty.
- Ready.
- Uploading.
- Validating.
- Processing.
- Transcript ready.
- Notes ready.
- Needs speaker review.
- Local-only waiting for desktop upload.
- Upload failed.
- Access denied.
- Deleted.
- Degraded.

## Empty State

- Primary: `Загрузить медиа`.
- Secondary: `Открыть приложение`.
- Copy must explain that transcripts appear after processing.
- No fake rows.

## Acceptance Evidence

Covered by Figma `V8 10 - Веб-кабинет: встречи и фильтры`,
`V8 06 - Загрузка и обработка в списке`, and
`design/validation-evidence.md`.
