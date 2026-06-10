# Contract: Validation Run Evidence

## Purpose

Define the evidence needed to claim `019` acceptance for meeting targets,
duration windows, and device classes without over-claiming untested
combinations.

## Required Fields

```json
{
  "validationRunId": "uuid",
  "feature": "019-live-route-stability",
  "durationGate": "development_30_minute",
  "meetingTarget": "chrome",
  "physicalDeviceClass": "built_in",
  "startedAt": "2026-06-04T09:16:21Z",
  "completedAt": "2026-06-04T09:46:21Z",
  "result": "accepted",
  "userActionsRequired": [],
  "routeReleaseCount": 0,
  "unexpectedReleaseCount": 0,
  "autorepairAttempts": [],
  "eventFamiliesPresent": [
    "route_lifecycle",
    "client_activity",
    "idle_release_decision",
    "autorepair",
    "external_disruption",
    "recording_timeline",
    "user_action_audit"
  ],
  "timelineIntegrity": {
    "alignmentBand": "accepted",
    "durationDifferenceSeconds": 1.2
  },
  "notTestedCombinations": [
    "chrome+usb",
    "opera+wired"
  ],
  "diagnosticSafe": true
}
```

## Duration Gates

- `development_30_minute`
- `release_75_minute`

## Results

- `accepted`
- `degraded`
- `failed`
- `blocked`
- `not_tested`

## Acceptance Rules

- Chrome, Opera, Zoom, and Telemost each require accepted 30-minute and
  75-minute evidence.
- Built-in, wired, and USB device classes each require accepted long-duration
  evidence.
- Clean accepted runs require zero required user actions.
- Clean accepted runs require zero unexpected releases.
- Clean accepted recording runs require `durationDifferenceSeconds <= 3`.
- Any untested target/device-class combination must be listed as not tested and
  cannot be claimed release-ready.
- Bluetooth/AirPods-class routes must be listed as backlog/not accepted for
  `019`, never accepted.
