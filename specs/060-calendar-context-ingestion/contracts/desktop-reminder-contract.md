# Desktop Reminder Contract

**Feature**: 060-calendar-context-ingestion

## Purpose

Define the macOS-facing behavior for calendar-driven prompts without adding auto-recording in 060.

## Prompt Rules

- At `event.start - 1 minute`, if the desktop app is running, authenticated, workspace policy allows meeting prompts, and the event has an authorized meeting link, show a join/open prompt.
- At `event.start`, if the desktop app is running, authenticated, recording is allowed, and no active recording already covers the event, show a record prompt.
- Neither prompt starts recording automatically in 060.
- Any later auto-record option may skip pre-start prompts, but active recording must still be visible locally and one-action Stop must remain available.

## Desktop Input

The desktop app consumes `GET /api/v1/desktop/calendar/upcoming`.

Required fields:

- `event_id`
- `starts_at`
- `ends_at`
- `title` plus `title_state`
- `meeting_link_present`
- `open_meeting_url` only when authorized
- `join_prompt_due_at`
- `record_prompt_due_at`
- `join_prompt_state`
- `record_prompt_state`

## Prompt Copy Rules

- If `title_state=available`, prompt may show the event title.
- If `title_state` is private, free/busy-only, or policy hidden, prompt uses generic copy such as "Calendar meeting".
- Prompt copy must not expose attendee emails, passcodes, full meeting URLs, agenda text, or attachment links.
- Join prompt action label: "Join meeting".
- Record prompt action label: "Start recording".
- Secondary action label: "Dismiss".

## State Transitions

```text
not_due -> shown -> opened
not_due -> shown -> dismissed
not_due -> not_available
not_due -> blocked_by_policy
shown -> expired
```

Record prompt may transition to `started` only after the existing visible desktop recording control starts a recording.

## Accessibility And Localization

- Prompt action labels must have accessible names.
- The visible recording state and Stop action must remain discoverable through the existing desktop accessibility checks.
- Russian localization is required for user-facing prompt text before production rollout.

## Failure Behavior

- If calendar context is unavailable, do nothing; do not start recording.
- If multiple current events overlap, show a choice flow or fall back to generic record start without claiming a calendar event.
- If the provider link is stale or unavailable, the join prompt may open the event detail instead of a meeting link.
- If the app is not running, 060 does not require a server push notification.
