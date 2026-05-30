# Data Model: macOS Live Audio Passthrough

## ReadinessCheck

Represents one user-triggered attempt to prove live call readiness.

Fields:

- `id`: stable local identifier
- `started_at`, `finished_at`: timestamps
- `trigger`: `manual`
- `selected_microphone_id`: physical input device at check time
- `selected_speaker_id`: physical output device at check time
- `virtual_microphone_id`: expected 2brain Rec virtual input
- `virtual_speaker_id`: expected 2brain Rec virtual output
- `microphone_evidence_id`: link to microphone `AudioRouteEvidence`
- `speaker_evidence_id`: link to speaker `AudioRouteEvidence`
- `status`: `not_started`, `running`, `passed`, `failed`, `stale`
- `failure_reason`: machine-readable category when not passed
- `safe_to_show_ready`: boolean derived from both route evidence records

Validation:

- `safe_to_show_ready` can be true only when microphone and speaker evidence are
  both `passed`.
- A route/device change after `finished_at` makes the check `stale`.
- Hidden recording is forbidden during readiness checks.

## AudioRouteEvidence

Represents proof or failure for one route.

Fields:

- `id`
- `path`: `physical_mic_to_virtual_mic` or `virtual_speaker_to_physical_speaker`
- `source_device_id`
- `target_device_id`
- `status`: `passed`, `failed`, `stale`
- `signal_kind`: `synthetic_tone`, `live_level`, `buffer_movement`, `browser_meeting`
- `measured_level_dbfs`: optional numeric level
- `buffer_frames_observed`: optional frame count
- `latency_ms`: optional measured latency
- `dropout_count`: optional count
- `loopback_db`: optional remote-to-mic loopback estimate
- `failure_reason`
- `created_at`

Validation:

- Device visibility alone cannot create `passed` evidence.
- Speaker evidence must prove physical output movement or an explicit verified
  render path, not just virtual speaker input.
- Microphone evidence must reject any remote-to-mic loopback above threshold.

## PassthroughSession

Represents an active local bridge during readiness or capture.

Fields:

- `id`
- `mode`: `readiness_probe` or `capture`
- `started_at`, `stopped_at`
- `physical_microphone_id`
- `physical_speaker_id`
- `state`: `starting`, `running`, `degraded`, `stopping`, `stopped`, `failed`
- `last_health_at`
- `failure_reason`

Validation:

- `readiness_probe` must be bounded and must not persist raw audio.
- `capture` requires prior non-stale readiness evidence.
- Any device change invalidates the session unless the route is rechecked.

## CaptureTrackEvidence

Represents local proof that a capture track existed and stayed usable.

Fields:

- `id`
- `session_id`
- `track`: `local_microphone` or `remote_speaker`
- `first_frame_at`, `last_frame_at`
- `frames_recorded`
- `dropout_count`
- `alignment_offset_ms`
- `status`: `present`, `missing`, `silent`, `degraded`

Validation:

- Local and remote tracks must be recorded separately.
- Missing or silent expected tracks force degraded finalization.

## DeviceChangeEvent

Represents a route-affecting macOS change.

Fields:

- `id`
- `observed_at`
- `change_type`: `default_input_changed`, `default_output_changed`,
  `device_disconnected`, `device_connected`, `bluetooth_profile_changed`,
  `browser_device_changed`
- `previous_device_id`
- `new_device_id`
- `invalidates_readiness`: boolean
- `recovery_action`

Validation:

- Route-affecting changes invalidate readiness within 5 seconds.
- Recovery copy must distinguish physical device problems from virtual driver
  publication problems.

## DiagnosticRouteEvent

Redacted diagnostic event for support and QA.

Fields:

- `event_name`
- `occurred_at`
- `readiness_check_id`
- `route_evidence_id`
- `category`
- `status`
- `failure_reason`
- `redaction_status`

Forbidden:

- raw audio
- transcript text
- credentials
- tokens
- signed URLs
- hidden recording artifacts
