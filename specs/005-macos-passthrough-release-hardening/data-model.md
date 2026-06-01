# Data Model: macOS Passthrough Release Hardening

This feature adds metadata-only evidence concepts. It does not add persistent
product storage, raw audio, transcripts, upload payloads, or server-side data.

## Release Hardening Run

- **Purpose**: Dated validation attempt for the pre-recording macOS passthrough
  release-hardening gates.
- **Fields**:
  - `run_id`: stable local identifier
  - `created_at`: date/time of validation
  - `macos_version`: observed macOS version
  - `app_build`: local app/package build identifier when available
  - `driver_build`: HAL driver/proof build identifier when available
  - `result`: `passed`, `blocked`, or `not_accepted`
  - `notes`: metadata-only summary
- **Relationships**:
  - has many no-hang evidence records
  - has many route recovery evidence records
  - has many installer lifecycle evidence records
  - has one deferred recording acceptance checklist state

## No-Hang Evidence

- **Purpose**: Prove common audio surfaces remain responsive while the driver is
  installed and the app is open.
- **Fields**:
  - `target_surface`: macOS Sound, Chrome settings, Opera settings, Zoom
    settings, Telemost settings, or other documented target
  - `launch_time_seconds`: measured or observed time to usable UI
  - `coreaudiod_cpu_peak_percent`: observed peak during the window
  - `coreaudiod_cpu_sustained_percent`: sustained CPU observation
  - `route_state_before`: ready, active, stale, degraded, failed, blocked
  - `route_state_after`: ready, active, stale, degraded, failed, blocked
  - `result`: `passed`, `blocked`, or `not_accepted`
  - `failure_reason`: metadata-only reason when blocked

## Short Smoke Evidence

- **Purpose**: Preserve lightweight user-observed browser audio smoke evidence
  without treating it as long-duration final release proof.
- **Fields**:
  - `target_app`: browser or meeting app name
  - `selected_input`: expected `2brain Rec Microphone`
  - `selected_output`: expected `2brain Rec Speaker`
  - `local_speech_observed`: yes/no/unknown
  - `remote_audio_observed`: yes/no/unknown
  - `loopback_observed`: yes/no/unknown
  - `recording_started`: must be no
  - `result`: `passed`, `blocked`, or `not_accepted`

## Route Recovery Evidence

- **Purpose**: Capture route behavior around device changes, `coreaudiod`
  restart, and sleep/wake.
- **Fields**:
  - `trigger`: physical input change, physical output change, aggregate route,
    Bluetooth route, stale browser device ID, `coreaudiod` restart, sleep/wake
  - `detected_within_seconds`: measured or observed detection time
  - `expected_state`: stale, degraded, blocked, or ready after recovery
  - `actual_state`: observed state
  - `recovery_action`: recheck, repair, reselect device, restart Core Audio, or
    none required
  - `result`: `passed`, `blocked`, or `not_accepted`

## Installer Lifecycle Evidence

- **Purpose**: Prove install, update, repair, rollback, uninstall, and reinstall
  behave safely after passthrough work.
- **Fields**:
  - `operation`: install, update, repair, rollback, uninstall, reinstall
  - `pre_state`: installed, missing, stale, incompatible, or unknown
  - `post_state`: installed, removed, repaired, failed, or unknown
  - `core_audio_refresh_required`: yes/no
  - `runtime_probe_result`: accepted, blocked, or not run
  - `result`: `passed`, `blocked`, or `not_accepted`

## UX Readiness Evidence

- **Purpose**: Confirm UI states are truthful and distinguish non-recording
  passthrough from recording/capture.
- **Fields**:
  - `state`: ready, active, stale, degraded, failed, blocked, repair
  - `copy_claim`: visible status text or summarized copy
  - `non_recording_explicit`: yes/no
  - `recording_implied`: must be no
  - `accessibility_notes`: keyboard/non-color/localization notes
  - `result`: `passed`, `blocked`, or `not_accepted`

## Deferred Recording-Assisted Acceptance Checklist

- **Purpose**: Define future long-duration acceptance once recording exists.
- **Fields**:
  - `blocked_until`: local recording support
  - `required_evidence`: recorded local mic path, recorded remote speaker path,
    no-loopback replay, distortion/dropout notes, channel separation
  - `retention_policy_required`: yes
  - `deletion_policy_required`: yes
