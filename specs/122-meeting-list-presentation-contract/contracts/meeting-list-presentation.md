# UI Contract: Meeting List Presentation

This contract supersedes only the meeting-list portion of feature 104. Existing meeting detail, native capture, upload, access, calendar, playback, and deletion contracts remain authoritative.

## Surface Ownership

- Browser route: `/meetings`.
- Embedded route: `/desktop/meetings`.
- Both routes render the same query, row, copy, interaction, and accessibility contract through the existing cabinet stack.
- Native macOS Record/Stop, permissions, local custody, and capture status remain outside this surface and cannot be overridden by list content.

## Toolbar Contract

Visible order:

```text
Мои встречи | Поиск встреч | Фильтры[: N] | <current sort> | Загрузить запись
```

Rules:

1. Render one `h1` with `Мои встречи`.
2. Render one search field with visible placeholder and accessible name `Поиск встреч`.
3. Render one filter disclosure. Its visible/accessible trigger is `Фильтры` or `Фильтры: N`.
4. Render one sort disclosure. Its visible trigger is the current selected label, default `Сначала новые`; its accessible name is `Сортировка: <label>`.
5. Render `Сбросить` only when query, status, or access refinement is active.
6. Render one upload action whose visible and accessible label is `Загрузить запись`.
7. Do not render a persistent sort subtitle next to the heading or a second `Записи встреч` heading.
8. Render `Найдено: N` only for active search/filter refinement and expose it as a polite status.

Filter options keep existing transport values:

| Transport | Visible copy |
|---|---|
| empty | `Все состояния` |
| `ready` | `Готовые` |
| `processing` | `В обработке` |
| `partial` | `С ограничениями` |
| `failed` | `Требуют внимания` |

Access copy remains `Любой доступ`, `Мои`, `Команда`, and `Со мной поделились`.

Sort options:

| Transport | Visible copy | Trailing time basis |
|---|---|---|
| `started_desc` | `Сначала новые` | meeting start |
| `started_asc` | `Сначала старые` | meeting start |
| `updated_desc` | `Недавно обновлённые` | explicit update time |
| `updated_asc` | `Давно обновлённые` | explicit update time |
| `duration_asc` | `Сначала короткие` | meeting start |
| `duration_desc` | `Сначала длинные` | meeting start |
| `title_asc` | `По названию` | meeting start |

Unknown sort input safely falls back to `started_desc`. The existing URL/HTMX form preserves other selected query values.

## Collection Semantics

- Non-empty rows are an ordered HTML list (`ol`/`li`) inside a region named `Встречи`.
- Each list item is one homogeneous meeting entry with one primary open action and explicit selection/delete controls.
- Row reading order is: source/selection intent → title → duration → compact status and optional action → delete → time.
- The title, duration, compact status, and time are programmatically associated with the row and announced once.
- Decorative source icons are hidden from assistive technology; their safe media label is included only where it adds meaning.
- A short `aria-label` must not replace or hide visible row metadata.

## Row Content

```text
[source or checkbox] [title] [duration] [one status] [optional explicit action] [delete] [time]
```

### Title

- Preserve meaningful authoritative/user/calendar/upload titles.
- Recognized generated capture title: `Запись`.
- Generated manual-upload identifier: `Загруженная запись`.
- Unsafe/missing non-upload title: `Запись`.
- Keep date/time separate from a neutral title.
- Existing safe filename cleanup remains presentation-only; stored titles do not change.

Examples:

| Source data | Visible title | Time |
|---|---|---|
| user title `Ольга — МНПЗ` | `Ольга — МНПЗ` | `21 июл, 19:22` |
| recognized generated capture | `Запись` | `21 июл, 19:22` |
| generated upload ID | `Загруженная запись` | `Без даты` |

### Duration

Use the existing Russian compact format: `27 с`, `14 мин`, `1 ч 14 мин`. Duration remains visible when known and does not move when contextual controls appear.

### Time

- Meeting-time modes: `<day> <month>, HH:MM`, for example `21 июл, 19:22`.
- Missing trusted meeting time: `Без даты`.
- Updated mode: `Обновлено 21 июл, 19:22` from actual `updated_at`.
- Do not present an update timestamp as though it were the meeting date.

## One-Status Contract

The renderer calls one pure projection and renders zero or one compact status. First true row wins:

| Priority | User condition | Status | Separate action |
|---:|---|---|---|
| 1 | deletion in progress | `Удаляется` | none |
| 2 | upload is terminally failed/aborted/expired, or result preparation failed/blocked/unavailable | `Не удалось обработать` | existing recovery path when available |
| 3 | ambiguous calendar context needs owner action | `Нужен выбор` | `Выбрать встречу` |
| 4 | local copy not accepted by server | `Сохранено на Mac` | existing custody recovery when available |
| 5 | active measured upload | `Отправляем N%` | none |
| 6 | active unmeasured upload | `Отправляем` | none |
| 7 | submitted/processing | `Обрабатывается` | none |
| 8 | result is openable and audio is preparing | `Аудио готовится` | primary open action remains available |
| 9 | result is openable without playable audio | `Без аудио` | primary open action opens limitation detail |
| 10 | other partial result | `Готово с ограничениями` | primary open action opens available material |
| 11 | normal ready result | no status | primary open action |

Forbidden ordinary-row tokens:

- `Готово`
- `Аудио готово`
- `Из календаря`
- `Выбрано вами`
- `Без календарного контекста`
- `Контекст убран вами`

The detail page retains those facts when they explain provenance or recovery.

Measured progress requirements:

- Render percentage and progressbar only while upload is active, total is trustworthy, and projected percentage is below terminal completion.
- If total becomes untrustworthy, remove percentage and meter immediately and keep `Отправляем`.
- Never render a terminal `100%` meter.
- `aria-valuenow` equals the visible percentage.

## Interaction Contract

### Open

- Pointer click on the readable row area or title opens the meeting.
- `Enter` on the focused row or primary link opens the meeting.
- Opening never changes selection.
- When calendar choice is required, the primary route may retain the existing detail anchor; the separate action is visibly named `Выбрать встречу`.

### Select

- A real checkbox performs selection.
- `Space` on the focused selectable row or checkbox toggles the same checkbox state without opening the meeting or scrolling the page.
- Selection state is exposed programmatically and visibly, not only by color.
- Selecting one row reveals batch mode; clearing the last row removes it.

### Contextual controls

- Checkbox and `Удалить встречу <title>` appear on row hover, row focus-within, or selected state.
- Their 32×32 CSS-pixel target columns are reserved at all times; title, duration, status, and time do not shift.
- On coarse-pointer/no-hover media, checkbox and delete remain persistently reachable.
- Hidden controls are removed from the tab/accessibility sequence; focusing the row reveals them before the user needs the action.
- Focus order remains row → selection control → open link/action → delete, or another documented logical order that exposes each function once and does not trap focus.

### Batch mode

Absent when selection count is zero. When active, render exactly:

| Element | Copy/behavior |
|---|---|
| Count | `Выбрано: N` |
| Select-all checkbox/button | `Выбрать все` (or selected state allowing clear) |
| Clear | `Снять выбор` |
| Delete | `Удалить` with accessible name `Удалить выбранные встречи` |

All four elements remain keyboard and VoiceOver reachable.

## Deletion Contract

- Reuse the existing row forms, CSRF, authorization, bounded confirmation dialog, and request endpoints.
- Do not add `Отменить удаление` or claim deletion outside GRAF control.
- Place the deletion feedback live region between the toolbar/batch state and the list, not after a long list.
- Accepted copy: `Запись удалена из списка. Очистка данных GRAF продолжается.`
- Partial failure copy: `Не удалось удалить N записей. Попробуйте ещё раз.`
- Feedback is polite/atomic and does not receive focus.
- After the focused row disappears, focus moves to the next surviving row, otherwise previous row, otherwise the list heading/status anchor.
- Failed batch rows remain selected so retry scope is clear.

## Empty, Loading, And Recovery Contract

| State | Title/status | Body | List-region action |
|---|---|---|---|
| first empty | `Пока нет встреч` | `Начните запись или загрузите готовый файл.` | none |
| refined empty | `Ничего не найдено` | `Измените запрос или сбросьте фильтры.` | `Сбросить` |
| loading | `Загружаем встречи…` | row-shaped skeleton geometry | none |
| offline | `Нет подключения` | `Запись на Mac продолжает работать.` | `Повторить` |
| service unavailable | `Не удалось загрузить встречи` | `Попробуйте ещё раз.` | `Повторить` |
| session expired | `Нужно войти снова` | `Сессия завершилась.` | `Войти` |
| access revoked | `Встреча больше недоступна` | no cached private metadata | return to list |

First-empty reuses the persistent toolbar upload and native recording surface; it adds no duplicate CTA, app installation, calendar onboarding, or future feature.

## Accessibility Contract

- Use native links, checkboxes, buttons, select controls, list semantics, dialog, and status/live-region behavior before adding ARIA.
- Every control has a programmatic name containing its visible label where a visible label exists.
- The open action's name includes the meeting title and trusted time when needed to distinguish neutral `Запись` rows.
- Row description includes duration, compact status if present, and time once; no internal IDs, reason codes, or hidden duplicate status.
- `Enter`, `Space`, `Tab`, `Shift+Tab`, and `Escape` preserve their expected meaning.
- Every critical target has a visible ≥2 CSS-pixel-equivalent focus indicator and meaningful state cues with applicable 3:1 non-text contrast.
- Context controls are at least 32×32 CSS px; toolbar actions meet at least the repository's existing control target.
- Result count, loading, progress, deletion success, and errors are announced without moving focus.
- Increased contrast and Reduce Motion retain state/meaning; state is never color-only.

## Responsive Contract

At `1280×760` and `1040×680`:

- no outer horizontal scrolling;
- title truncation is visual only and the full safe title remains accessible;
- ready rows remain 48 px; exceptional rows may grow to 60 px for one secondary line;
- time and delete targets do not overlap;
- toolbar labels may compact only while exact accessible names remain;
- native capture rail remains visible and unchanged.

## Privacy And Clean-Room Contract

- Unavailable/session/access-revoked states do not render cached private meeting metadata.
- Committed tests/evidence use synthetic names and identifiers only.
- No raw audio, transcript text, participant names, account email, credential, token, signed URL, live local path, or provider secret enters screenshots or docs.
- Krisp copy, assets, icons, palette, composition, and unsupported organization/collaboration features are absent.

## Compatibility

Preserved without new storage or API fields:

- search;
- grouped status/access filters;
- all existing sort choices;
- manual upload;
- browser and embedded routes;
- meeting detail navigation;
- selection and bounded row/batch deletion;
- calendar/playback truth on detail surfaces;
- native recording authority.
