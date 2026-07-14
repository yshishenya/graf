# UI Contract: Meeting List Presentation

## Query Controls

The list exposes exactly one search field. Status and access are grouped under `Фильтры`; sorting is under `Сортировка`. Controls submit through the existing allowlisted query parameters and HTMX list replacement.

User-facing labels:

| Control | Copy |
|---|---|
| Search placeholder | `Поиск встреч` |
| Filter trigger, default | `Фильтры` |
| Filter trigger, active | `Фильтры: N` |
| Filter reset | `Сбросить` |
| Sort trigger | Current short choice, for example `Сначала новые` |
| Upload | `Загрузить` |

Filter labels remain `Статус` and `Доступ`. Existing allowlisted values remain authoritative, but ordinary failure wording uses `Нужна помощь` rather than a raw pipeline failure term.

## Title Presentation

Presentation-only normalization is deterministic and tested.

1. Preserve a meaningful user/calendar title.
2. Strip a final known media extension (`wav`, `mp3`, `m4a`, `mp4`, `mov`, `webm`) from a file-like display title.
3. Collapse repeated underscores/separators only when the source is clearly a filename; do not rewrite normal punctuation or names.
4. Recognized generated capture titles become `Запись <localized date/time>` only when a trustworthy start time exists.
5. Recognized generated manual-upload IDs become `Загруженная запись`; no date is invented for the title.
6. Empty or unsafe titles become `Запись без названия`.
7. If trustworthy time is absent, the neutral title is paired with the existing separate `Без даты` label.

The stored title and route data are unchanged. Accessibility labels use the same human display title.

## Duration And Date

| Duration | Example |
|---|---|
| Under one minute | `27 с` |
| Minutes | `14 мин` |
| Hours and minutes | `1 ч 14 мин` |

Existing timezone-aware date presentation remains. `Без даты` is retained when no trustworthy start date exists.

## Status And Progress

| Underlying result | List copy | Meter |
|---|---|---|
| Ready | `Готово` | none |
| Ready with accepted limitation | `Готово с замечаниями` | none |
| Uploading/retrying/finalizing | `Отправляем` | only if measured |
| Processing | `Обрабатывается` | only if measured |
| Local copy awaiting server | `Сохранено на Mac` | none |
| Failed/expired and owner can recover | `Нужна помощь` | none |

A terminal `100%` bar is forbidden. A percentage is shown only while `is_active == true` and a meaningful total exists. Detailed cause and recovery remain in the meeting/native recovery context, not the compact row.

## Row Composition

Reading mode:

```text
source/select intent | result link | duration | state | date | contextual delete
```

The meeting title remains the primary semantic link that opens the existing result; clicking reading content MUST NOT silently toggle selection. In reading mode, the source icon occupies the compact intent slot while checkbox and delete controls are absent visually and from the accessibility tree. Row hover or keyboard focus swaps the source icon for the exact row-specific checkbox and reveals delete without adding a permanently empty column. When any row is selected, all visible selectable rows expose selection affordances and the toolbar shows count plus delete.

Selected rows use a subtle accent tint/border, not a saturated full-width purple block. Hover, selection, focus, failure, and active progress remain distinguishable.

## Empty States

- No meetings and no refinement in the installed macOS app: concise first-value guidance that reuses the persistent `Загрузить` control and native recording action; do not duplicate those controls or add app-download/install, calendar, or onboarding steps. Browser-only app-download behavior is outside this feature.
- No result after search/filter: `Ничего не найдено` and `Сбросить фильтры`; do not show first-run installation steps.
- List/loading replacement: preserve an accessible live status without exposing request or route details.

## Destruction

Per-row and bulk delete reuse the existing bounded confirmation copy, CSRF, authorization, HTMX feedback, and post-delete focus/selection reconciliation. Feature 104 changes visibility and hierarchy only, not deletion semantics.
