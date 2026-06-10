# Contract: Route Evidence Events

## Purpose

Define the metadata-only event contract for live route lifecycle, client
activity, idle/release decisions, autorepair, external disruptions, recording
timeline, and user action audit.

## Transport And Storage

- Local-first JSON Lines or JSON array.
- No external upload in `019`.
- Events may be attached to a local route diagnostics bundle or recording
  package manifest evidence.

## Required Fields

```json
{
  "eventId": "uuid",
  "eventName": "route.lifecycle.started",
  "family": "route_lifecycle",
  "occurredAt": "2026-06-04T09:16:21Z",
  "routeSessionId": "uuid",
  "recordingSessionId": "optional-uuid",
  "meetingTarget": "chrome",
  "stateBefore": "starting",
  "stateAfter": "active",
  "triggerCategory": "client_io_opened",
  "virtualClientState": {
    "microphoneClientOpen": true,
    "speakerClientOpen": true,
    "microphoneRunning": true,
    "speakerRunning": true,
    "freshnessMs": 250
  },
  "macOSDefaultRoute": {
    "defaultInputDeviceId": "safe-id",
    "defaultInputSafeName": "MacBook Pro Microphone",
    "defaultInputClass": "built_in",
    "defaultOutputDeviceId": "safe-id",
    "defaultOutputSafeName": "MacBook Pro Speakers",
    "defaultOutputClass": "built_in",
    "acceptedFor019": true
  },
  "frameContinuity": {
    "microphoneFrameCounter": 123456,
    "speakerFrameCounter": 123450,
    "microphoneGapMs": 0,
    "speakerGapMs": 0,
    "summary": "continuous"
  },
  "autorepairAttemptId": null,
  "userActionRequired": false,
  "diagnosticSafe": true
}
```

## Event Families

- `route_lifecycle`
- `client_activity`
- `idle_release_decision`
- `autorepair`
- `external_disruption`
- `recording_timeline`
- `user_action_audit`

## Event Names

Minimum event names:

- `route.lifecycle.armed`
- `route.lifecycle.started`
- `route.lifecycle.active`
- `route.lifecycle.preserved`
- `route.lifecycle.stopped`
- `route.lifecycle.released`
- `route.lifecycle.stale`
- `route.lifecycle.blocked`
- `route.lifecycle.failed`
- `route.lifecycle.recovered`
- `client_activity.snapshot`
- `idle_release.keep_active`
- `idle_release.release_denied_client_active`
- `idle_release.release_denied_unknown_state`
- `idle_release.released_after_client_closed`
- `autorepair.started`
- `autorepair.attempt`
- `autorepair.succeeded`
- `autorepair.blocked`
- `autorepair.failed`
- `autorepair.retry_budget_exhausted`
- `external_disruption.coreaudiod_restart`
- `external_disruption.sleep_wake`
- `external_disruption.physical_device_changed`
- `external_disruption.default_route_changed`
- `external_disruption.browser_stream_recreated`
- `recording_timeline.snapshot`
- `recording_timeline.alignment_band`
- `user_action.run_check`
- `user_action.meeting_device_reselect`
- `user_action.app_relaunch`
- `user_action.meeting_settings_reopen`

## Redaction Rules

MUST NOT contain:

- raw audio samples or audio-derived content snippets;
- transcript text or participant speech;
- meeting title/content;
- credentials, tokens, signed URLs, passwords, API keys;
- live credential paths or full local user paths.

Allowed:

- safe device display names;
- safe/stable device ids when they do not expose secrets;
- route/session ids;
- frame counters and timing summaries;
- accepted/degraded/blocked/failed/not-tested result labels.

## Acceptance Rules

- Every accepted 30-minute and 75-minute validation run must include all event
  families.
- Any accepted run must show no required user action audit events.
- Any route release during a formerly active meeting must include a
  release-decision event with fresh client activity evidence.
