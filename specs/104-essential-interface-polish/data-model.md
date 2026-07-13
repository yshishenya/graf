# Data Model: Essential Interface Polish

Feature 104 adds no database table, migration, stored preference, API payload, or local manifest field. This document defines presentation-only entities and state transitions that existing server/native data is projected into.

## NavigationPresentation

Represents the visible server-owned sidebar.

| Field | Type | Rule |
|---|---|---|
| `active_destination` | `meetings | settings` | Exactly one enabled destination is active. |
| `destinations` | ordered list | Contains only reachable destinations with non-empty labels and icons. |
| `can_logout` | boolean | True for an authenticated cabinet shell. |

Validation:

- Disabled/future navigation items are not part of the visible projection.
- Search is not a navigation destination.
- Product branding appears once in the sidebar.
- No plan/trial label is projected without an authoritative billing source.

## MeetingQueryPresentation

Projects the existing query string into one search field and contextual controls.

| Field | Type | Rule |
|---|---|---|
| `query` | string | Trimmed existing `q`; empty means no text filter. |
| `status` | existing status filter | Empty means all statuses. |
| `access` | existing access filter | Empty means all accessible meetings. |
| `sort` | existing sort value | Always has one supported value. |
| `active_filter_count` | integer | Count of non-default `status` and `access` filters; sorting is represented separately. |
| `has_refinement` | boolean | True when query or any non-default filter is active. |
| `reset_href` | URL | Same list route without query/filter parameters and with default sort. |

Validation:

- Every selected value is one of the existing allowlisted server values.
- Search, filter, and sort changes preserve the other current values.
- Clear/reset returns to the complete default list in one action.

## MeetingListItemPresentation

Projects an existing meeting/list item without mutating stored data.

| Field | Type | Rule |
|---|---|---|
| `meeting_id` | existing identifier | Used for route/selection only; never rendered as title. |
| `display_title` | string | Human title according to the title rules below. |
| `media_kind` | `audio | video | transcript | upload` | Existing presentation mapping. |
| `duration_label` | string | Russian compact duration. |
| `date_label` | string | Existing timezone-aware local date or `Без даты`. |
| `result_state` | enum | One of the user-facing states below. |
| `progress_percent` | optional `0...100` | Present only for an active measurable operation. |
| `is_selected` | boolean | Existing client-only selection state. |
| `can_delete` | boolean | Existing bounded owner/deletion policy. |

Title projection priority:

1. A meaningful stored title remains unchanged except safe filename cleanup.
2. A recognized capture-generated title becomes `Запись <localized date/time>` only when trustworthy start time exists.
3. A generated manual-upload identifier becomes `Загруженная запись`; it does not invent a date.
4. A file title loses only its final known media extension and repeated separator noise.
5. Missing/unsafe title becomes `Запись без названия`.
6. When start time is absent or untrusted, `date_label` remains `Без даты` independently of the neutral title.

User-facing result states:

| State | Label | Progress |
|---|---|---|
| `ready` | `Готово` | none |
| `ready_with_notes` | `Готово с замечаниями` | none |
| `uploading` | `Отправляем` | optional measured percent |
| `processing` | `Обрабатывается` | optional measured percent only when real |
| `saved_local` | `Сохранено на Mac` | none |
| `needs_help` | `Нужна помощь` | none |
| `deleting` | Existing truthful deletion copy | none |

Validation:

- `progress_percent` is absent when the operation is terminal.
- A failure cannot project to `ready`.
- Presentation never exposes a local path, generated ID, status key, or diagnostic code.

## SelectionPresentation

Client-only state managed by existing cabinet JavaScript.

| Field | Type | Rule |
|---|---|---|
| `selected_ids` | set of meeting IDs | Contains only visible selectable rows. |
| `visible_total` | integer | Existing list-region count. |
| `mode_active` | boolean | True after first explicit selection; false after clear or list replacement with no selection. |
| `all_visible_selected` | boolean | Derived from selected count and selectable visible rows. |

Transitions:

```text
reading --select row--> selecting --select/clear rows--> selecting
selecting --clear last row--> reading
selecting --confirm delete--> reading with feedback
query/list replacement --> reconcile to visible IDs; reading if none remain
```

The mode changes visibility only; it does not change deletion authorization or server behavior.

## CaptureSurfacePresentation

Native projection for rail, titlebar HUD, and expanded panel.

| Field | Type | Rule |
|---|---|---|
| `capture_state` | enum | See state table below. |
| `status_label` | string | Short human truth. |
| `primary_action` | optional action | Exactly one of start, stop, resume, open settings, retry/review, or none. |
| `primary_action_enabled` | boolean | False only while the current transition cannot accept another command. |
| `requires_attention` | boolean | True only when the meeting owner can/should act. |
| `local_custody_count` | non-negative integer | Shown only when action/awareness is required. |
| `shows_expanded_panel` | boolean | Manual disclosure or `requires_attention`; active recording alone does not change width. |
| `shows_meters` | boolean | True only in an active capture state and only when the panel is expanded. |
| `shows_support_action` | boolean | True only for a support-eligible actionable failure. |

State projection:

| Capture state | Status | Primary action | Persistent behavior |
|---|---|---|---|
| `ready` | `Готово к записи` | `Начать запись` | Rail action available. |
| `permission_required` | `Нужно разрешение` | `Открыть настройки` or existing permission action | Explain only the affected capability. |
| `meeting_detected` | `Встреча обнаружена` | Existing ask/start decision | No candidate ID or telemetry count. |
| `starting` | `Начинаем запись…` | none | Prevent duplicate start. |
| `recording` | `Идёт запись` | `Стоп` | Titlebar HUD and rail both preserve Stop. |
| `paused` | `Запись на паузе` | `Продолжить`; Stop remains available in HUD/rail | Not visually confused with recording. |
| `stopping` | `Сохраняем запись…` | none | Never claim ready early. |
| `saved_local` | `Сохранено на Mac` | context-dependent | Explain that upload/retry is separate. |
| `actionable_failure` | `Нужна помощь` | one recovery action | Panel may expand; support action is secondary. |

## Relationship And Ownership

```text
Existing server meeting/query data
  -> MeetingQueryPresentation
  -> MeetingListItemPresentation
  -> server-rendered WebView

Existing native capture/session/queue data
  -> CaptureSurfacePresentation
  -> compact rail + titlebar HUD + optional inspector
```

The two projections share wording principles and visual tokens but not authority. Server content cannot produce or override native capture state; native controls do not rewrite server meeting/list data.

## Migration

None. Existing stored titles, meeting records, URLs, filters, upload sessions, queue items, manifests, diagnostic records, and user settings remain unchanged.
