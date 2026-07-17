# Data Model: recording package v5

## Scope

This model defines only the new first-party recording form. It does not migrate or rewrite historical v3/v4 records and does not add database columns.

## Local Package

| Entity | Identity | Required fields / invariant |
| --- | --- | --- |
| `RecordingTimeline` | `timelineVersion`, recording epoch, output frame index | One monotonic 48 kHz mono frame sequence; each source batch has PTS, duration, actual input rate, discontinuity and route generation. Gap becomes silence; overlap is trimmed; unsafe loss fails integrity. |
| `CanonicalMixProfile` | immutable profile ID/version in v5 manifest | Bounded transparent gain/peak protection only; no AEC, VAD trimming, amplitude gate, mute or text transformation. |
| `TranscriptionArtifact` | `meeting-transcription.wav`, local role `mixed_meeting_audio`, transport role `media` | PCM s16le, mono, 16 kHz, nonempty, closed, SHA-256/byte count/duration/frame count matching manifest. Sole ASR source. |
| `PlaybackArtifact` | `meeting-review.m4a`, local role `review_playback`, transport role `playback` | AAC-LC M4A, mono, 48 kHz, nonempty, closed, SHA-256/byte count/duration matching manifest and same timeline subject to declared AAC priming. Never an ASR source. |
| `RecordingPackageV5` | `directoryId`, `sessionId`, immutable manifest SHA-256 | Exactly manifest + media + playback final artifacts. No `mic.wav`, `incoming.wav`, `.partial` or hidden raw source file. |

## Manifest Shape And Compatibility

`LocalRecordingManifest.schemaVersion` for new writes is `local-recording-manifest.v5`; `mediaScribeSourceMode` is `single_wav_v1`. The manifest must describe both artifacts and their shared timeline/version. Its completion rules are v5-specific: valid consent/permissions, finalized canonical WAV, finalized playback M4A, no integrity failure, and no external egress/transcription started yet.

Older `local-recording-manifest.v3` and v4 objects are decoded by an explicit compatibility reader. Their historical dual roles are retained only for their existing queue/read/retention lifecycle. A v3/v4 object can never be normalized into v5 or silently gain a v5 source kind.

## Server Revision And Artifacts

| Entity | v5 value | Invariant |
| --- | --- | --- |
| `MediaRevision.source_kind` | `initial_mixed_recording` | Distinct from `initial_recording` and `manual_upload`; immutable after accepted finalization. |
| authoritative roles | `("media",)` | The accepted `media` digest, manifest digest, duration and source kind make the processing fingerprint. Playback is excluded deliberately because it is a derivative. |
| accepted transport roles | `{manifest, media, playback}` | Exact for v5 at session creation and finalize. Descriptor validation is tied to source kind. |
| `TrackArtifact.media` | canonical WAV | `codec=wav-pcm-s16le`, `sample_rate_hz=16000`, `channel_count=1`; the only staged ASR file. |
| `TrackArtifact.playback` | M4A candidate | `codec=m4a-aac-lc`, `sample_rate_hz=48000`, `channel_count=1`; existing playback normalization validates/reuses it. |
| `MediaScribeJob` | `request_mode=single_track`, `source_track_artifact_id=media` | At most one external job per accepted media revision. No mic, system or playback artifact ID is set for v5. |

The `source_kind` field is already a string compatible with the new enum value; the existing revision/fingerprint/track tables require no migration.

## Processing State

| State | Required v5 behavior |
| --- | --- |
| pre-accept | package is local only; external egress flag remains false. |
| accepted | immutable manifest and authoritative `media` digest are persisted; server may create/reuse one processing workflow. |
| submitting | server stages only canonical WAV as a `.wav`, maps its verified codec to `audio/wav`, then makes one single-track request. |
| unknown POST outcome | persist safe `mediascribe_submission_outcome_unknown`, block that revision and create no automatic second request. |
| processed | transcript/diarization/result bind to the same revision; playback state remains independently truthful. |
| deletion / terminal lifecycle | source WAV, M4A candidate/canonical derivative, upload parts, processing and transcript records enter existing deletion truth; external-provider deletion remains separately bounded. |

## Rollback Record

The rollout receipt stores metadata only: baseline commit/release ID, candidate commit/release ID, test date, package schema, route/volume/timeline verdicts, safe hashes/counts/statuses and operator decision. It does not contain audio, spoken phrases, transcript content, credentials or private file paths.

Rollback changes only the app used for a future recording. An accepted v5 revision retains v5 source truth and cannot become a dual revision.
