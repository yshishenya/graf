# Data Model: Meeting List Presentation Contract

Feature 122 adds no database entity, migration, API field, stored preference, meeting lifecycle state, or local manifest field. This document defines immutable presentation-only values derived from existing safe list data.

## MeetingListQueryPresentation

Projects the existing allowlisted query string into the toolbar and trailing-time semantics.

| Field | Type | Rule |
|---|---|---|
| `query` | string | Existing trimmed `q`; empty means no text refinement. |
| `status` | existing status filter or null | Transport remains `ready`, `processing`, `partial`, or `failed`; visible labels are grouped user language. |
| `access` | existing access filter or null | Existing `owner`, `team`, `shared` behavior. |
| `sort` | existing sort value | Default is `started_desc`. |
| `sort_label` | string | Exact selected label from the visual contract. |
| `active_filter_count` | non-negative integer | Counts non-default status and access filters; sorting is not a filter. |
| `has_refinement` | boolean | True for non-empty query or a non-default status/access filter. |
| `result_count_label` | string or null | `Найдено: N` only when `has_refinement`; otherwise absent. |
| `time_basis` | `meeting | updated` | `updated` only for `updated_desc`/`updated_asc`; otherwise `meeting`. |

Validation:

- Search/filter changes preserve the selected sort and other current allowlisted values.
- Reset returns to the unrefined `started_desc` route in one action.
- Unknown sort input falls back to `started_desc` presentation and ordering.
- `updated` time labels always start with `Обновлено`; meeting-time labels never do.

## MeetingListRowPresentation

A frozen value object derived from one existing `MeetingListItem` and `time_basis`. It is private to the cabinet presentation layer and is not serialized as a new public API model.

| Field | Type | Rule |
|---|---|---|
| `display_title` | non-empty string | Meaningful user/calendar title, `Запись`, `Загруженная запись`, or safe fallback. |
| `duration_label` | string | Existing compact Russian duration. |
| `time_label` | string | Trusted localized date and time, explicit updated label, or `Без даты`. |
| `media_kind` | existing presentation enum | `audio`, `video`, `transcript`, or `upload`. |
| `media_label` | string | Existing safe Russian accessible label for the source icon. |
| `status_kind` | compact status enum or null | Exactly one status from the precedence table, or null for normal readiness. |
| `status_label` | string or null | Exact compact copy; null when `status_kind` is null. |
| `status_tone` | `progress | warning | danger | neutral` or null | Visual distinction that also has text, never color-only. |
| `progress_percent` | integer `0...99` or null | Present only for active, measurable upload; terminal 100 is never projected. |
| `secondary_action` | action enum or null | Only a separately rendered applicable action, currently calendar choice or existing recovery. |
| `secondary_action_label` | string or null | Exact action copy, such as `Выбрать встречу`. |
| `open_accessible_name` | non-empty string | Includes visible title and trusted time for neutral generated titles; begins `Открыть встречу`. |
| `accessible_description` | non-empty string | Includes duration, optional compact status, and time exactly once. |

### Compact status enum and total precedence

The first matching condition wins. Lower rows remain available in source/detail data but are not projected in the compact list.

| Priority | `status_kind` | Predicate | Label | Progress |
|---:|---|---|---|---|
| 1 | `deleting` | overall status is `deleted_future` | `Удаляется` | none |
| 2 | `failed` | overall status is `blocked`, `failed`, or `unavailable` and the result is not merely a known ready playback limitation | `Не удалось обработать` | none |
| 3 | `calendar_choice` | calendar context requires owner choice | `Нужен выбор` | none |
| 4 | `saved_local` | overall status is `local_only` | `Сохранено на Mac` | none |
| 5 | `uploading_measured` | upload is active and has a trustworthy total/percentage below terminal | `Отправляем N%` | `N` |
| 6 | `uploading` | overall/upload state is actively sending without trustworthy percentage | `Отправляем` | none |
| 7 | `processing` | overall status is `submitted` or `processing` | `Обрабатывается` | none |
| 8 | `audio_preparing` | result materials are available and playback state is `preparing` | `Аудио готовится` | none |
| 9 | `without_audio` | result is otherwise openable and playback is unavailable/deleted | `Без аудио` | none |
| 10 | `limited` | overall status is `partial` without a more specific playback limitation | `Готово с ограничениями` | none |
| 11 | null | result is normally ready and playback is available | absent | none |

Validation invariants:

- `status_kind is null` if and only if `status_label`, `status_tone`, `progress_percent`, and status-specific action are absent.
- At most one `status_label` is rendered.
- `progress_percent` is present only for `uploading_measured`, `is_active == true`, a positive trustworthy total, and `0 <= N < 100`.
- `available` playback never creates a token.
- Matched, declined, cleared, or absent calendar context never creates a compact status.
- Calendar choice uses a static status plus a separate real link/action; the badge itself is not interactive.
- Source reason codes, local IDs, paths, provider IDs, and raw pipeline labels are never projected.

### Title projection

1. Preserve authoritative user, calendar, or upload-provided titles after existing safe path handling.
2. Preserve meaningful safe derived titles after existing filename cleanup.
3. Recognized generated capture titles become `Запись`; date/time remains in `time_label` and the accessible name.
4. Generated manual-upload identifiers become `Загруженная запись`.
5. Missing or unsafe non-upload titles become `Запись`; no date is invented.
6. Stored data is never rewritten.

### Time projection

| `time_basis` | Source | Visible form |
|---|---|---|
| `meeting` | trusted `started_at` with recorded display offset | `21 июл, 19:22` |
| `meeting` with no start | none | `Без даты` |
| `updated` | trusted `updated_at` | `Обновлено 21 июл, 19:22` |
| `updated` with no update | fallback to trusted meeting time | `Обновлено 21 июл, 19:22` only when source is truly update time; otherwise `Без даты` |

The same normalized time is used in the visible label and accessible name. No hidden alternative name may replace the visible duration/status/time content.

## MeetingListSurfacePresentation

Projects the list collection and asynchronous state without changing routes.

| Field | Type | Rule |
|---|---|---|
| `rows` | ordered tuple of row presentations | Follows the selected existing query sort. |
| `query` | `MeetingListQueryPresentation` | One toolbar state. |
| `surface_state` | enum | `content`, `first_empty`, `no_results`, `loading`, `offline`, `unavailable`, or `session_expired`. |
| `state_title` | string or null | Exact visual-target copy for non-content states. |
| `state_body` | string or null | One short explanation. |
| `state_action` | action or null | At most one applicable reset/retry/sign-in action. |
| `announcement` | string or null | Polite result/progress/error text that does not move focus. |

Validation:

- `first_empty` has no duplicated record/upload action in the list region.
- `no_results` is possible only when refinement is active and exposes `Сбросить`.
- Session/access failure projections contain no cached meeting title, participants, calendar context, or other private meeting metadata.
- Loading placeholders preserve row geometry and include `Загружаем встречи…` for assistive technology.

## MeetingSelectionPresentation

Client-only state managed by the existing cabinet JavaScript.

| Field | Type | Rule |
|---|---|---|
| `selected_ids` | set of visible meeting IDs | Changes only through explicit selection controls/keyboard selection. |
| `visible_ids` | ordered list of visible meeting IDs | Rebuilt after HTMX replacement. |
| `mode_active` | boolean | True iff at least one visible row is selected. |
| `selected_count` | non-negative integer | Equals intersection of `selected_ids` and `visible_ids`. |
| `all_visible_selected` | boolean | True only when the non-empty visible set is fully selected. |

Transitions:

```text
reading --open/Enter--> navigation (selection unchanged)
reading --checkbox/Space--> selecting
selecting --checkbox/Space--> selecting or reading when last selection clears
selecting --select all--> selecting
selecting --clear--> reading
selecting --confirm delete--> pending deletion
pending deletion --accepted--> reconcile visible rows + announce
pending deletion --partial failure--> keep failed rows selected + announce applicable retry
HTMX replacement --> intersect selection with visible IDs; restore deterministic focus
```

Batch mode exposes exactly `Выбрано: N`, `Выбрать все`, `Снять выбор`, and `Удалить`. It is absent, not merely visually empty, while `mode_active` is false.

## DeletionFeedbackPresentation

Reuses existing deletion request results.

| State | Message | Focus behavior |
|---|---|---|
| accepted | `Запись удалена из списка. Очистка данных GRAF продолжается.` | Announce politely; next row, previous row, then list heading. |
| partial failure | `Не удалось удалить N записей. Попробуйте ещё раз.` | Announce; preserve failed selection and existing retry path. |
| confirmation | Existing bounded dialog copy | Dialog owns focus and returns it on cancel. |

No `Undo` state is added. The projection does not promise erasure outside GRAF control.

## Ownership And Migration

```text
Existing database/access/upload/calendar/playback/deletion truth
  -> existing MeetingListItem / MeetingListResponse
  -> private MeetingListQueryPresentation + MeetingListRowPresentation
  -> current browser/embedded Jinja + HTMX surface

Existing native capture/session/custody truth
  -> unchanged macOS capture rail and titlebar Stop
```

Migration: none. Existing records, public payloads, URLs, filter values, upload sessions, calendar links, playback states, deletion requests, and native recording behavior remain unchanged.
