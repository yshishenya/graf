# Contract: Current Recording Path Must Not Change

## Composition

The production application MUST create the active sources in this order:

1. Approve a bounded ScreenCaptureKit capture scope.
2. Start `SystemAudioCaptureService` for incoming system audio.
3. Resolve and start an app-owned microphone sample source.
4. Construct `LocalRecordingWriter` with both sources explicitly injected.
5. Start the writer with the same permission, scope, microphone, mute-truth, and
   processing metadata used before driver retirement.

No step may open shared memory, select a virtual device, create a passthrough
bridge, or inspect driver installation state.

## Artifacts

- Original microphone track role remains `local_mic`.
- Original incoming track role remains `remote_speaker`.
- The manifest remains `local-recording-manifest.v3` unless an independent
  requirement justifies a schema change.
- Track formats, MediaScribe field mapping, local custody, leakage finalization,
  and review-audio behavior remain governed by existing tests.

## Controls and truth

- Manual start remains available when current prerequisites pass.
- Active recording remains visibly indicated locally.
- Stop remains available in one action throughout starting/active/stopping
  states.
- Permission or source failures remain fail-closed and show current recovery
  copy; they never recommend driver repair.
- Live meters use `LocalRecordingWriter.currentLevelsAsync()` and show the two
  current sources only.

## Regression proof

The before/after focused suite MUST cover:

- ScreenCaptureKit source lifecycle and resource release;
- app-owned microphone selection and frames;
- independent incoming source injection without HAL/shared memory;
- dual-track package and manifest truth;
- start prerequisites and permission blockers;
- visible capture state and stop availability.
