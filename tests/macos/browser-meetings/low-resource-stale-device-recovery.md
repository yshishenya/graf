# Low-Resource Stale Browser Device Recovery

Feature: `006-low-resource-audio`

This fixture records the metadata-only acceptance evidence for browser/meeting targets
that keep a stale virtual device identifier after driver reload, app restart,
`coreaudiod` restart, sleep/wake, or browser device-cache refresh.

## Required Evidence

- Target app/browser name and version only.
- Whether the 2brain Rec Microphone and 2brain Rec Speaker are still visible.
- Whether the target has selected stale device IDs.
- Expected resource state: `stale`.
- Required recovery action: `ask_user_to_reselect_2brain_virtual_devices`.
- Recording state: `off`.
- Raw audio, transcript text, meeting title, participant names, and meeting content: forbidden.

## Acceptance Matrix

| Trigger | Expected State | Public Devices | Recovery Action | Result |
| --- | --- | --- | --- | --- |
| Browser keeps stale microphone ID | `stale` | visible | `ask_user_to_reselect_2brain_virtual_devices` | metadata-only |
| Browser keeps stale speaker ID | `stale` | visible | `ask_user_to_reselect_2brain_virtual_devices` | metadata-only |
| Browser cache refresh reselects both devices | `ready` or `active` | visible | `none` | metadata-only |

## Notes

This is not a recording test. It proves recovery truthfulness for route state and user
guidance while preserving the no silent/invisible recording boundary.
