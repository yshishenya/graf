# Contract: Readiness Check

## Purpose

Define when 2brain Rec may show ready for calls.

## Inputs

- Installed driver package state.
- Core Audio visibility of `2brain Rec Microphone`.
- Core Audio visibility of `2brain Rec Speaker`.
- Selected physical microphone.
- Selected physical speaker.
- Microphone route evidence.
- Speaker route evidence.
- Device-change events since the last check.

## Output States

- `not_installed`: driver package is absent.
- `installed_not_visible`: driver package exists but one or both virtual devices
  are not visible to macOS.
- `visible_not_ready`: both virtual devices are visible but live route evidence
  is missing or stale.
- `checking`: a user-triggered readiness check is running.
- `ready`: both live paths passed and no invalidating route change occurred.
- `failed`: the last check failed with a specific reason.
- `stale`: prior readiness was invalidated by a route/device/browser change.

## Ready Rule

The app MUST show `ready` only when all are true:

- driver package is installed;
- both virtual devices are visible;
- selected physical microphone is not a 2brain Rec virtual device;
- selected physical speaker is not a 2brain Rec virtual device;
- microphone route evidence status is `passed`;
- speaker route evidence status is `passed`;
- no route/device/browser change invalidated the evidence;
- readiness check was user-triggered and did not start hidden recording.

## Failure Reasons

- `virtual_microphone_not_visible`
- `virtual_speaker_not_visible`
- `physical_microphone_not_selected`
- `physical_speaker_not_selected`
- `self_routing_rejected`
- `microphone_silent_or_unavailable`
- `speaker_silent_or_unavailable`
- `passthrough_not_running`
- `loopback_threshold_exceeded`
- `device_changed_recheck_required`
- `browser_target_not_validated`

## Logging

Logs may include state, failure reason, device class, and redaction status. Logs
must not include raw audio, transcripts, credentials, tokens, or signed URLs.
