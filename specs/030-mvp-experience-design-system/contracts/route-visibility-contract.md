# Contract: Route Visibility Matrix

## Purpose

Define which server cabinet routes can appear inside the macOS desktop app and
which routes belong only in the full browser cabinet.

## Route Classification Values

- `embedded_desktop`: Route may render inside the desktop app's allowlisted
  server-loaded cabinet subset.
- `browser_only`: Route belongs only in the browser web cabinet.
- `hidden_in_desktop`: Route is not shown in desktop navigation.
- `disabled_in_desktop`: Route may be visible as unavailable with clear copy.
- `handoff_to_browser`: Desktop opens or directs the user to the browser.

Unknown routes default to `handoff_to_browser` or `hidden_in_desktop`.

## Required Matrix Fields

Each route row must include:

- `route_id`
- `route_name`
- `route_classification`
- `desktop_entry_point`
- `browser_entry_point`
- `primary_actor`
- `user_goal`
- `status_dependencies`
- `native_boundary_notes`
- `deferred_reason` when not embedded

## Initial Route Set

| Route ID | Route Name | Classification | Notes |
|---|---|---|---|
| `desktop.native.home` | Native desktop trust shell | `embedded_desktop` context only | Native shell owns recording readiness, record/stop controls, permission/local artifact truth, minimal connection/session/policy badge for route guard, and the embedded route host. Account/workspace summaries and recent meeting status render through embedded server-owned routes. |
| `desktop.native.recording` | Active recording | Native-only | Must never be server-rendered. |
| `cabinet.account.status` | Account/workspace status | `embedded_desktop` | Useful in app; cannot own capture truth. |
| `cabinet.auth.recover` | Sign-in/session recovery | `embedded_desktop` | Blocks upload only; local recording truth remains local. |
| `cabinet.meetings.recent` | Recent meetings | `embedded_desktop` | Shows current status, opens review. |
| `cabinet.upload.manual` | Manual media upload | `embedded_desktop` | Audio-first upload, no direct credentials. |
| `cabinet.processing.status` | Upload/processing status | `embedded_desktop` | Must align with cross-surface status model. |
| `cabinet.meeting.review` | Meeting review | `embedded_desktop` | Core review is allowed; broad admin/share/download actions may hand off. |
| `cabinet.meeting.speakers` | Speaker assignment | `embedded_desktop` | Server-owned speaker naming, merge, and assignment may render inside desktop; native macOS hosts the route but does not own diarization/editing logic. |
| `cabinet.settings.basic` | Basic account/settings entry | `embedded_desktop` | Keep compact; hand off advanced settings. |
| `web.admin.workspace` | Broad workspace admin | `browser_only` | Too broad for recorder app. |
| `web.billing` | Billing | `browser_only` | Business/accounting surface, not recorder-app core. |
| `web.team.management` | Team management | `browser_only` | Admin-heavy. |
| `web.sharing.public` | Public sharing pages | `browser_only` | Later access-sharing slice. |
| `web.exports.downloads` | Advanced exports/downloads | `browser_only` | Later access/download slice. |
| `web.audit.detailed` | Detailed audit views | `browser_only` | Later audit/admin surface. |
| `web.help.legal` | Help/legal | `browser_only` or `handoff_to_browser` | May be linked from desktop, not embedded by default. |
| `web.video.full` | Full video review | Deferred | Full video UX is outside MVP promise. |

## Native Boundary Rules

- Embedded routes must not show stop, recording indicator, microphone/system
  audio permission controls, local queue control, or capture recovery controls.
- Embedded routes must not obscure native recording status or one-action stop.
- Embedded route copy must not claim recording, upload, transcription, deletion,
  or access truth unless that truth is sourced from the approved status model.
- Embedded speaker assignment must source speakers, segments, confidence, and
  save state from the server/web cabinet contract. Native macOS may only host
  the route and keep capture status visible.
- Browser-only handoff must be explicit and understandable.

## Validation

- 100% of cabinet routes and navigation elements are classified before tasks.
- 100% of embedded desktop routes are reviewed against the native capture
  boundary.
- Unknown routes are treated as safe handoff/hidden until explicitly approved.

## Final Design References

- Matrix source: `design/route-visibility-matrix.md`.
- Screen mapping: `design/screen-inventory.md`.
- Active Figma route references on page `030 MVP Experience v8 - Clean RU`:
  - `V8 00 - Карта MVP-потока и границы`
  - `V8 03 - Рабочее пространство встреч`
  - `V8 09 - Настройки записи и темы`
  - `V8 10 - Веб-кабинет: встречи и фильтры`
  - `V8 11 - Веб-детали встречи и транскрипт`
  - `V8 12 - Поделиться, экспорт, удаление`
  - `V8 14 - Правила интерфейса и QA`
- Historical V5 route boards are retained only as coverage evidence and must
  not be used as current implementation handoff without reconciling against V8.
