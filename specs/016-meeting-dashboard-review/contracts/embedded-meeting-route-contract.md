# Contract: Embedded Meeting Routes

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

## Purpose

Define which 016 web-cabinet routes are allowed to render inside a native
desktop shell and what native boundaries must remain outside server-rendered UI.

## Route Manifest

| Route ID | Browser Path | Embedded Path | Owner | Desktop Classification | Auth Required | Offline Fallback |
|---|---|---|---|---|---|---|
| `cabinet.meetings.recent` | `/meetings` | `/desktop/meetings` | `server_product_ui` | `embedded_desktop` | yes | Cached/retry meeting list shell; no fake rows |
| `cabinet.meeting.review` | `/meetings/{meeting_id}` | `/desktop/meetings/{meeting_id}` | `server_product_ui` | `embedded_desktop` | yes | Meeting title/status if cached; transcript unavailable truth |
| `cabinet.processing.status` | `/meetings/{meeting_id}/status` | `/desktop/processing/{meeting_id}` | `server_product_ui` | `embedded_desktop` | yes | Last known stage with stale marker |
| `cabinet.meeting.speakers` | `/meetings/{meeting_id}/speakers` | `/desktop/meetings/{meeting_id}/speakers` | `server_product_ui` | `reserved_embedded` | yes | Speaker correction disabled/offline |

## Native Shell Requirements

Native desktop shell must remain authoritative for:

- active recording indicator;
- one-action Stop;
- microphone/system-audio permission recovery;
- local recording package truth;
- local upload queue truth and retry;
- local diagnostics/support bundles;
- route guard/session state outside the embedded content frame.

## Embedded Web Must Not Expose

- Start recording.
- Stop recording.
- Toggle microphone/system audio capture.
- Select audio devices.
- Screen recording picker.
- Noise/accent/capture-time controls.
- Raw local file paths.
- Raw audio file access.
- Direct MediaScribe/object-store credentials or signed URLs.
- Diagnostics export without a native confirmation path.

## Allowed Bridge Intent Slots

016 does not implement bridge calls, but routes may reserve these future intent
slots in copy/contracts:

- `openExternal(url)` for browser-only/share/admin handoff.
- `showLocalQueue(meetingId)` for upload/local truth.
- `copyText(value)` for explicit user copy.

All future bridge intents must be typed, user-initiated, audited, and
deny-by-default.

## Browser-Only Or Future Routes

These routes must not be embedded by 016:

- public share pages;
- advanced export/download pages;
- deletion execution and reports;
- broad workspace admin/team management;
- billing;
- full Contacts management;
- full Action Items center;
- AI assistant/global search across all meetings;
- policy/settings editing beyond basic safe links.

## Validation Rules

- Unknown routes fail closed to hidden, disabled, or browser handoff.
- Server-unavailable embedded surface cannot hide local active capture truth.
- Embedded route screenshots must show no native capture controls inside the
  server-rendered content.
- Gated future actions must be visually discoverable but non-mutating.
