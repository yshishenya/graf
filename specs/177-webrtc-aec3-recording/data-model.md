# Data Model: WebRTC AEC3 Recording

## EchoProcessorDescriptor

Backward-compatible optional manifest value identifying the processor used for
new recordings.

| Field | Type | Rule |
|---|---|---|
| `algorithm` | String | Exact value `webrtc_aec3_m131` |
| `libraryVersion` | String | Exact value `2.1` |
| `sourceCommit` | String | Exact pinned commit |
| `sampleRate` | Int | `48000` |
| `channels` | Int | `1` |
| `frameSamples` | Int | `480` |
| `streamDelayMs` | Int | `0` until a measured host/HAL delay exists |
| `optionalProcessingEnabled` | Bool | Must be `false` |

The descriptor is absent on historical packages. A newly saved/ready package
created by this feature must contain the exact descriptor.

## EchoProcessingHealth

Metadata-only result accumulated by the timeline and attached to the manifest.

| Field | Type | Rule |
|---|---|---|
| `state` | Enum | `ready`, `active`, `completed`, `degraded`, `failed` |
| `reason` | Optional enum | Safe bounded code; required for degraded/failed |
| `processedFrameCount` | Int64 | Non-negative count of successful 10 ms pairs |
| `processErrorCount` | Int | Non-negative; zero for a normal package |
| `resetCount` | Int | Non-negative; a trusted segment does not span reset |
| `ptsGapCount` | Int | Count of missing-reference/timeline gaps |
| `estimatedDriftPpm` | Optional Double | Finite bounded host estimate over the observed mic/render PTS span |
| `hostUnderrunCount` | Int | Host-side reference shortage count |
| `hostOverrunCount` | Int | Host-side bounded-queue overflow count |
| `clippedSampleCount` | Int64 | Host-side absolute samples at clipping threshold |
| `nonFiniteSampleCount` | Int64 | Must be zero for emitted audio |
| `aecDelayMs` | Optional Int | Bounded public AEC3 statistic |
| `echoReturnLossDb` | Optional Double | Finite public AEC3 statistic |
| `echoReturnLossEnhancementDb` | Optional Double | Finite public AEC3 statistic |
| `processingTimeP95Ms` | Optional Double | Finite, non-negative summary only |

No field may contain audio, transcript text, device-owner data, credentials,
paths, WebRTC dumps or unbounded logs.

## EchoProcessingFailureReason

Bounded values:

- `processor_unavailable`
- `processor_configuration_failed`
- `render_reference_missing`
- `process_reverse_failed`
- `process_capture_failed`
- `route_changed`
- `format_changed`
- `timebase_changed`
- `pts_discontinuity`
- `source_stopped`
- `source_overflow`
- `non_finite_samples`
- `finalization_failed`

Unknown internal errors map to the existing bounded capture failure rather than
serializing exception text.

## Canonical frame pair

Transient in-memory value owned by `RecordingAudioTimeline`:

| Field | Type | Rule |
|---|---|---|
| `startFrameIndex` | Int64 | Contiguous canonical PTS position |
| `systemSamples` | 480 Float | Valid render reference, mono 48 kHz |
| `microphoneSamples` | 480 Float | Matching capture interval |
| `routeGeneration` | Int | Same trusted route segment |

The pair is never persisted. True system silence is a valid all-zero reference;
an absent reference is not represented as silence and terminates trust.

## State transitions

```text
ready --start--> active --clean stop--> completed
  |                  |\
  |                  | runtime integrity failure
  |                  v
  +--start failure-> failed       degraded --Stop--> degraded final package
```

- `ready` requires successful processor creation/configuration and both capture
  prerequisites.
- Only `active` may emit a cleaned frame.
- `completed` requires zero process errors and a complete package.
- `degraded` may retain only the successfully processed prefix and is not
  upload/transcription ready.
- State never returns from `degraded`/`failed` to `active` within a recording.

## Relationships and compatibility

- One active recording owns exactly one AEC processor and one health accumulator.
- One successfully processed pair creates one cleaned microphone frame, then one
  canonical mixed frame with the unchanged system samples.
- One manifest optionally owns one descriptor and one health snapshot.
- Existing `canonical-mix.v1` remains unchanged because the mix equation and
  artifact roles do not change.
- Historical v3/v4 and pre-feature v5 manifests decode with absent optional AEC
  values; they are readable but never presented as newly AEC-verified packages.
