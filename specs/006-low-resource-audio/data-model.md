# Data Model: Low-Resource Reliable macOS Audio

This feature adds metadata-only route lifecycle and validation concepts. It does
not add product persistence, raw audio, meeting recording, transcript text,
upload payloads, MediaScribe, Langfuse, MinIO, Postgres, Temporal, Docker, or
server-side data.

## Audio Resource State

- **Purpose**: Canonical local route lifecycle state shown in UI, diagnostics,
  and validation.
- **Values**:
  - `idle_safe`: virtual devices are visible/fail-closed; no sustained heavy
    physical passthrough work.
  - `starting`: bounded route startup attempt is in progress.
  - `ready`: route has fresh evidence for publication, client IO, app bridge,
    and valid physical devices.
  - `active`: audio is flowing through at least one virtual device with healthy
    app bridge evidence.
  - `stale`: prior ready/active state was invalidated by restart, sleep/wake,
    heartbeat, or device change.
  - `blocked`: route cannot safely start within the accepted gate.
  - `failed`: route attempt failed with a recorded metadata-only reason.
  - `retrying`: a bounded retry is scheduled or user-requested.
  - `fallback`: accepted 005 app-launch lifecycle is restored without driver
    reinstall.
- **State transitions**:
  - `idle_safe -> starting`: explicit client IO state opens for expected virtual
    device.
  - `starting -> ready|blocked|failed|fallback`: startup resolves within 3
    seconds.
  - `ready -> active`: first healthy IO cycle is observed.
  - `ready|active -> stale`: `coreaudiod` restart, sleep/wake, device change,
    stale heartbeat, or route invalidation.
  - `blocked|failed|stale -> retrying -> starting`: safe retry path.
  - any state -> `idle_safe`: client IO closes and heavy physical route work is
    stopped without hiding public virtual devices.

## Route Truth Snapshot

- **Purpose**: Keep visible device publication separate from live route
  readiness.
- **Fields**:
  - `snapshot_id`: stable local identifier for the evidence record.
  - `recorded_at`: local timestamp.
  - `publication`: reference to virtual device publication evidence.
  - `client_activity`: reference to explicit client IO evidence.
  - `app_bridge_health`: reference to app heartbeat/readiness evidence.
  - `physical_devices`: reference to physical working-device selection evidence.
  - `recording_trigger`: current application recording trigger state.
  - `resource_state`: current Audio Resource State.
  - `result`: `passed`, `blocked`, `failed`, or `not_accepted`.
- **Validation rules**:
  - Device publication alone must never imply `ready`.
  - `ready` requires published devices, valid physical working devices, and fresh
    app bridge evidence.
  - `active` requires explicit client IO state; audio energy is not sufficient.

## Virtual Device Publication Evidence

- **Purpose**: Prove HAL virtual devices are installed, visible, alive, and
  fail-closed by default.
- **Fields**:
  - `microphone_visible`: yes/no.
  - `speaker_visible`: yes/no.
  - `microphone_alive`: yes/no/unknown.
  - `speaker_alive`: yes/no/unknown.
  - `microphone_running`: yes/no/unknown.
  - `speaker_running`: yes/no/unknown.
  - `hidden`: must be no for the MVP default.
  - `runtime_probe_result`: `accepted`, `blocked`, or `not_run`.
- **Validation rules**:
  - Installed devices must remain visible by default across app idle, app exit,
    stale heartbeat, and Core Audio restart unless a later accepted feature
    changes this policy.
  - `running=0` is valid in idle-safe state.

## Client Activity Evidence

- **Purpose**: Capture explicit virtual-device IO activity without relying on
  audio sample energy.
- **Fields**:
  - `microphone_client_count`: non-negative integer.
  - `speaker_client_count`: non-negative integer.
  - `microphone_running`: yes/no.
  - `speaker_running`: yes/no.
  - `source`: `driver_start_stop`, `device_is_running`, or `test_fixture`.
  - `natural_silence_allowed`: must be yes.
- **Validation rules**:
  - Active stream state is derived from client IO state, not energy.
  - A silent but open stream remains active until explicit IO closes.

## App Bridge Health Evidence

- **Purpose**: Represent whether the app-side physical route bridge is available
  without blocking driver IO.
- **Fields**:
  - `heartbeat_state`: `waiting_for_app`, `connected`, `heartbeat_lost`.
  - `last_heartbeat_at`: local timestamp or null.
  - `timeout_ms`: default 3000 for app-side route readiness.
  - `driver_fail_closed`: yes/no.
  - `public_device_availability`: `available` for the MVP default.
  - `recovery_action`: `none`, `restart_desktop_audio_engine`, `retry_route`,
    `repair_driver`, or `reselect_physical_device`.
- **Validation rules**:
  - Stale or missing heartbeat downgrades live route readiness.
  - Stale or missing heartbeat does not hide public devices in this feature.
  - Driver IO must fail closed without waiting on app/process health.

## Physical Working Device Selection

- **Purpose**: Record the real physical input/output selected by the app route
  engine.
- **Fields**:
  - `input_device_id`: metadata-only Core Audio id or stable local label.
  - `input_device_name`: metadata-only display name.
  - `output_device_id`: metadata-only Core Audio id or stable local label.
  - `output_device_name`: metadata-only display name.
  - `input_kind`: `physical`, `2brain_virtual`, `other_virtual`, `aggregate`,
    `multi_output`, `bluetooth`, or `unknown`.
  - `output_kind`: same value set as `input_kind`.
  - `selection_result`: `accepted`, `rejected`, `blocked`, or `not_accepted`.
  - `rejection_reason`: metadata-only reason when not accepted.
- **Validation rules**:
  - 2brain Rec virtual devices must be rejected as physical working devices.
  - Other virtual, aggregate, and multi-output devices are unsupported/not
    release-ready unless later validation accepts them.
  - Built-in and wired physical devices are release-quality route targets.

## Startup Attempt Evidence

- **Purpose**: Prove route startup cannot hang UI, validation, browsers, meeting
  apps, or System Settings.
- **Fields**:
  - `attempt_id`: stable local identifier.
  - `trigger`: `client_io_opened`, `retry`, `recovery`, or `manual_check`.
  - `started_at`: local timestamp.
  - `completed_at`: local timestamp.
  - `duration_ms`: integer.
  - `outcome`: `ready`, `blocked`, `failed`, or `fallback`.
  - `blocked_reason`: metadata-only reason when blocked.
  - `fallback_used`: yes/no.
- **Validation rules**:
  - Every attempt must complete or fall back within 3000 ms.
  - Startup must not run as an unbounded UI/main-path operation.

## Realtime Safety Evidence

- **Purpose**: Prove HAL callback-sensitive paths remain realtime-safe.
- **Fields**:
  - `scan_id`: stable local identifier.
  - `checked_paths`: list of source paths.
  - `forbidden_operation_findings`: list of metadata-only findings.
  - `result`: `passed`, `blocked`, or `not_accepted`.
- **Validation rules**:
  - Callback paths must not contain file IO, logging, allocation, wall-clock
    calls, lock waits, blocking IPC, process launches, network calls, or UI work.
  - Findings block low-resource default promotion.

## Low-Resource Validation Run

- **Purpose**: Bundle local acceptance evidence for promotion to default.
- **Fields**:
  - `run_id`: stable local identifier.
  - `created_at`: local timestamp.
  - `app_build`: local app/package build identifier when available.
  - `driver_build`: HAL driver/proof build identifier when available.
  - `baseline`: accepted `005-macos-passthrough-release-hardening` app-launch
    lifecycle.
  - `route_truth_snapshots`: list of Route Truth Snapshots.
  - `startup_attempts`: list of Startup Attempt Evidence.
  - `realtime_safety`: Realtime Safety Evidence.
  - `no_hang_results`: metadata-only no-hang evidence.
  - `cpu_results`: metadata-only CPU evidence.
  - `recovery_results`: metadata-only recovery evidence.
  - `result`: `passed`, `blocked`, or `not_accepted`.
- **Validation rules**:
  - Low-resource mode becomes default only when every local P1 gate passes.
  - Any P1 failure preserves or restores fallback to the accepted 005 lifecycle.

## Recording Trigger Boundary

- **Purpose**: Document that audio routing and recording are separate.
- **Fields**:
  - `recording_trigger_state`: `off`, `armed_future`, or `active_future`.
  - `driver_recording_owner`: must be `false`.
  - `app_recording_owner`: must be `true` for future recording slices.
  - `recording_artifacts_created`: must be `false` for this feature.
  - `external_egress_started`: must be `false`.
- **Validation rules**:
  - Routing can be ready/active while recording is off.
  - This feature must not create recordings, transcripts, uploads, server jobs,
    MediaScribe requests, or Langfuse traces.
