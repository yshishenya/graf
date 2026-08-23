# Upload Status UX Contract

## Backend projection

`MeetingListItem` exposes:

- `started_at`: source recording time, nullable
- `uploaded_at`: server receipt time, nullable
- `source`: `manual_upload` identifies the fallback date case
- `upload`: existing upload progress projection
- `status`: processing/review state

## Rendering rules

1. If `started_at` exists, display it.
2. Else if `source == manual_upload` and `uploaded_at` exists, display `Загружено <day> <month>, <time>`.
3. Else display `Без даты`.
4. Uploading and processing are separate labels and state styles.
5. Progress uses the central violet interaction tokens and never a product-blue fallback.
6. Percentage is adjacent to the current upload state inside the content column; it is not a detached side column.
7. Upload copy uses the short canonical states: `Загрузка`, `На сервере · Обрабатываем`, `На сервере · Ждёт обработки`, `Загрузка остановлена`, and concise recovery copy.

## Shared cabinet style contract

1. `cabinet.css` is the single canonical token and component style source.
2. Typography roles, control heights, radii, spacing, surfaces, borders, focus, and semantic colors are custom properties.
3. Checkboxes and radios use the central violet accent and preserve native semantics.
4. Settings navigation rows keep stable geometry and long labels do not create taller desktop rows.
5. Provider-brand colors are isolated to provider identity classes and do not style product controls.
