# Data Model: Windows desktop-приложение GRAF

Документ описывает продуктовые и межслойные сущности. Он не создаёт новую
серверную таблицу: локальная модель должна проецироваться на существующий v5
manifest и `desktop-upload-queue.v2`.

## 1. WindowsDesktopSession

One active native recording session per user process.

| Field | Type | Persisted | Invariant |
|---|---|---:|---|
| `session_id` | opaque string/UUID | yes | immutable and unique per local package |
| `state` | `SessionState` | yes | every transition is explicit and monotonic except `paused`/`recording` |
| `started_at` / `stopped_at` | ISO-8601 | yes | server-independent local timestamps |
| `target_evidence` | bounded object | yes | absent for manual start; never guessed from process name |
| `permission_snapshot` | `PermissionSnapshot` | yes | records observed state, not proof of future consent |
| `system_route_generation` | non-negative integer | yes | changes on endpoint/clock discontinuity |
| `microphone_route_generation` | non-negative integer | yes | changes on endpoint/clock discontinuity |
| `capture_health` | `CaptureHealth` | yes | counts/reasons only, no samples |
| `finalization` | `FinalizationState` | yes | normal package only after all required artifacts pass |

### SessionState

```text
idle
checking_readiness
ready
starting
recording
paused
degraded
stopping
finalizing
saved_local
queued
uploaded
blocked
failed
```

`recording` and `paused` are the only active capture states. `degraded` can be
active only while the user can still invoke Stop; it cannot be advertised as a
normal session. There is no state in which capture is active but the indicator is
hidden.

## 2. PermissionSnapshot

```json
{
  "microphone": "granted|denied|restricted|unknown",
  "microphone_endpoint": "ready|missing|unsupported|unknown",
  "render_endpoint": "ready|missing|unsupported|unknown",
  "storage": "ready|low|full|unavailable",
  "webview_runtime": "ready|missing|repair_required|unknown",
  "recording_policy": "allowed|blocked|unknown",
  "observed_at": "2026-08-23T00:00:00Z"
}
```

The snapshot is a readiness explanation. It does not contain a Windows token,
cookie or raw device path. Device display names may be shown in UI only after
bounded normalization; diagnostics use stable hash/fingerprint or safe class.

## 3. WasapiEndpointSnapshot

The in-memory endpoint descriptor is richer than persisted metadata:

```text
endpoint_id             # in memory; never put in committed evidence
endpoint_fingerprint    # bounded hash for diagnostics
data_flow               # render | capture
role                    # console | communications | multimedia
is_default              # bool
sample_rate             # observed device rate
channel_count           # observed channel count
sample_format           # PCM/float and bit depth
route_generation        # monotonically increasing local generation
clock_domain            # opaque local identity
state                   # active | disabled | unplugged | invalidated
```

The source may use its device mix format. A worker normalizer produces the
canonical `48_000 Hz`, mono, float representation while retaining the source
PTS and route generation.

## 4. RecordingAudioBatch

Each source producer publishes a bounded value to its queue:

```text
source                  # system_render | microphone
samples                 # in-memory float samples; never persisted as metadata
source_frame_count
source_sample_rate
source_channel_count
presentation_timestamp  # qpc/device-derived timestamp
clock_domain
device_position_frames  # optional WASAPI position
qpc_ticks               # optional packet QPC position
qpc_frequency           # process-cached frequency reference
route_generation
discontinuity            # none | device_changed | clock_changed | overflow |
                         # invalid_timestamp | service_interrupted
```

Invariants:

- callback code drains packets and enqueues or records an overflow; it does not
  write files, call WebView, allocate unbounded memory or run AEC3;
- a timestamp must be finite/monotonic inside its source route generation;
- samples from different clock domains are never aligned directly;
- queue capacity and maximum reorder window are finite and covered by tests;
- the timeline emits only canonical 480-sample pairs to AEC3.

## 5. RecordingAudioTimeline

The timeline is the only alignment owner.

| Field | Meaning |
|---|---|
| `canonical_sample_rate` | 48,000 Hz |
| `canonical_channels` | 1 |
| `aec_frame_samples` | 480 |
| `system_queue` / `microphone_queue` | bounded normalized batches |
| `active_route_generations` | current system/microphone generation pair |
| `last_emitted_frame` | canonical frame index |
| `reorder_window_frames` | `48_000` canonical frames (1 s at 48 kHz) |
| `max_known_gap_seconds` | `15` seconds, matching the current macOS timeline default |
| `max_buffered_frames_per_source` | `960_000` canonical frames (20 s at 48 kHz) |
| `max_clock_recovery_frames_per_batch` | `48` canonical frames (1 ms at 48 kHz) |
| `dropped_frame_count` | diagnostic counter |
| `overflow_count` | diagnostic counter |
| `clock_discontinuity_count` | diagnostic counter |
| `aec_processed_frames` | diagnostic counter |
| `aec_error_count` | diagnostic counter |
| `trusted_prefix_only` | true after a terminal integrity error |

The timeline calls AEC3 in the fixed order `system/reference` then
`microphone/near-end`, combines the cleaned microphone with the unchanged system
component and sends canonical chunks to the writer. It never returns raw
microphone samples as a normal artifact.

These starting bounds are deliberately copied from the active macOS
`RecordingAudioTimelineConfiguration` and `BufferedLocalRecordingSampleSource`
defaults. A Windows change requires synthetic evidence for latency, memory,
overflow and duration; it must not silently choose an unbounded queue or a new
gap-recovery policy.

## 6. LocalRecordingPackage

The directory is user-scoped and contains only the established v5 package shape:

```text
LocalRecordingPackage {
  directory_id: String,
  schema_version: "local-recording-manifest.v5",
  canonical_mix_profile: "canonical-mix.v1",
  source_kind: "initial_mixed_recording",
  manifest: LocalRecordingManifest,
  artifacts: [ArtifactDescriptor],
  integrity: PackageIntegrity,
  local_deletion_registered: Bool
}
```

`ArtifactDescriptor` fields:

| Field | Normal value |
|---|---|
| `role` | `mixed_meeting_audio` / `review_playback` |
| `file_name` | `meeting-transcription.wav` / `meeting-review.m4a` |
| `format` | PCM S16LE 16 kHz mono / AAC-LC 48 kHz mono |
| `byte_count` | positive bounded integer |
| `sha256` | 64-char digest |
| `duration_ms` | duration measured from decoded/known frames |
| `status` | `writing` / `verified` / `degraded` / `failed` |

The local role names are an app-facing projection. At upload time they MUST map
to the server roles `media` and `playback`; the manifest track descriptors and
upload-session request also include `manifest`. The v5 session therefore uses
`media_scribe_source_mode=single_wav_v1` and the exact role set
`{manifest, media, playback}`. It must never be sent as the historical dual
shape `{manifest, microphone, system}`.

The manifest may carry optional Windows capture health and endpoint class fields
compatible with existing optional v5 decoding. It must not introduce a second
server-required package schema or store raw endpoint ids, local absolute paths,
cookies, tokens, audio samples or transcript content in evidence.

## 7. UploadCustodyItem

Windows uses the existing queue ledger and maps it to the same custody projection
as macOS:

```text
local_recording_id
local_media_revision_id
platform = windows
state = queued | uploading | retrying | uploaded | degraded | blocked | failed |
        terminal_deleted
server_truth
accepted_bytes_by_track
retry_class = automatic | manual_only | terminal
failure_category
sync_conflict_state
retention_deadline
```

The ledger is written atomically. A malformed document is quarantined with a
bounded reason code and a recoverable backup; it is never replaced by an empty
document. Server reconciliation wins over local guesses for server meeting,
media revision, upload session and accepted ranges.

## 8. WebViewBridgeEnvelope

All native↔WebView messages use one JSON shape:

```json
{
  "protocol": "graf.desktop.bridge",
  "version": 1,
  "direction": "native_to_web|web_to_native",
  "message_id": 1,
  "nonce": "ephemeral-nonce",
  "origin": "https://rec.2brain.pro",
  "command": "native_ready|request_native_settings|request_diagnostics|request_runtime_repair|ack_display",
  "payload": {},
  "sent_at_monotonic_ms": 12345
}
```

Rules:

- `nonce` changes whenever the WebView document/origin/session boundary
  changes;
- native validates `Source`, exact origin, route kind, version, direction,
  message id, payload size and command-specific payload before action;
- web receives state events but never file paths, tokens, device handles or raw
  samples;
- unknown commands, stale nonce, duplicate id, oversized payload and invalid JSON
  are rejected with a bounded error and no side effect;
- an acknowledgement is not a claim that audio was saved or uploaded; only local
  custody/server truth can establish that.

## 9. VerifiedTargetIdentity

```text
target_key                 # stable product registry key
display_name               # user-facing name
executable_identity_hash   # stable identity proof, not a raw path in evidence
publisher_or_signature     # approved bounded proof
installation_scope         # per_user | machine | unknown
registry_version           # reviewed registry version
prompt_capable             # bool
user_auto_record_enabled   # bool, target-scoped and reversible
```

A friendly process name without the identity proof cannot enable automatic
recording. Target configuration is scoped to the current user/workspace/device
and is not a global “record everything” switch.

## 10. CaptureHealth and reason codes

Persist only bounded codes/counters, for example:

```text
ready
permission_denied
endpoint_missing
endpoint_invalidated
audio_service_unavailable
protected_audio_limited
unsupported_format
clock_untrusted
timestamp_discontinuity
timeline_gap_exceeded
source_overflow
aec_processor_failed
writer_failed
disk_full
playback_encoder_unavailable
webview_runtime_unavailable
```

Reason code text is product-owned and localized at the UI layer. Diagnostics may
include counts and durations, but never the content that was spoken or recorded.
