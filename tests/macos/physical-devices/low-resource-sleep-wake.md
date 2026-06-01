# Low-Resource Sleep/Wake Recovery Fixture

Feature: `006-low-resource-audio`

This fixture captures metadata-only evidence for macOS sleep/wake while 2brain Rec
virtual devices are selected by a meeting client.

## Required Evidence

- Sleep/wake trigger timestamp.
- Previous low-resource state.
- New low-resource state: `stale` until route revalidation completes.
- Public device availability: `available`.
- Recovery action: `revalidate_route_after_sleep_wake`.
- Physical input/output IDs before and after wake.
- Recording state: `off` unless the user explicitly starts capture in a separate flow.

## Forbidden Evidence

- Raw audio buffers.
- Transcript or meeting content.
- Participant names.
- Credentials, signed URLs, tokens, or device secrets.

## Acceptance Matrix

| Trigger | Expected State | Public Devices | Recovery Action | Result |
| --- | --- | --- | --- | --- |
| Wake with same physical devices | `stale` then `ready` | visible | `revalidate_route_after_sleep_wake` | metadata-only |
| Wake with changed input | `stale` | visible | `reselect_physical_working_devices` | metadata-only |
| Wake with changed output | `stale` | visible | `reselect_physical_working_devices` | metadata-only |
