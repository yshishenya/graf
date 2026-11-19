# Contract: Capture continuity

## Inputs

- `RecordingAudioBatch` for `.microphone` and `.systemAudio`.
- `discontinuity`: `.none`, `.knownGap`, `.dropped`, `.routeChanged`, `.sourceStopped`.
- `routeGeneration`: integer that changes when the capture stream is recreated.
- `presentationTime`: source PTS/clock domain.

## Timeline rules

1. A forward system-audio gap `0 < delta <= maximumClockRecoveryFramesPerBatch` is recovered as today.
2. A forward system-audio gap `maximumClockRecoveryFramesPerBatch < delta <= 500 ms` is bridged with zero samples in the system-reference segment. `gapFramesBySource[.systemAudio]` and `continuityGapBridgedFrames` increase; `ptsGapCount` increases once. Recording does not fail.
3. A forward system-audio gap `500 ms < delta <= maximumKnownGapSeconds` (15 s) is **not** bridged with silence. The recording becomes an explicit partial result or stops with a preserved prefix; the UI must not present it as a complete recording.
4. A system-audio gap `> maximumKnownGapSeconds` throws `gapExceedsBound`. Recording stops; the prefix is preserved.
5. A microphone gap is not bridged; it remains `missingRequiredSource`/fail-closed.
6. `.routeChanged` marks a rebase for that source. The next batch with a new `routeGeneration` is rebased so its first frame equals the source's `lastInputEndFrame`. No negative PTS trimming, no frame loss. `continuityRouteChangeCount` increases; recording continues.
7. `.sourceStopped` and `.dropped` keep their existing fail-closed behavior.
8. If the route change cannot produce a trusted continuation, the writer preserves the playable prefix and maps `routeGenerationChanged`/`renderReferenceMissing` to `timelineMisaligned` with `partialContinuity=true`. The meeting may be uploaded as a partial recording; the UI must say so.
9. The continuity notice/status must be exposed as an accessible status/alert, keyboard reachable, VoiceOver-labelled, and must not steal focus or disappear before it can be read.

## Outputs

- One canonical WAV and one review M4A per recording.
- `RecordingAudioTimelineMetrics` includes gap/route counters (`continuityGapBridgedFrames`, `continuityRouteChangeCount`).
- Manifest fields are additive; old clients ignore them.
- No transcript/audio/path content in logs.

## Invariants

- The visible recording indicator and one-action Stop remain available.
- AEC3 remains mandatory; no raw-microphone fallback.
- A real source loss above the bound is still visible and fails closed.
- No second concurrent recording is created.
