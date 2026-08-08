# Capture Session Indicator Gate

This gate controls manual local recording start/stop and visible capture
indication for the app-owned system-audio and microphone sources.

## Required Evidence

- [ ] Manual `Record` starts only after recording policy, microphone
  permission, system-audio permission, storage, indicator, and source
  eligibility pass.
- [ ] A blocked start reports the concrete metadata-safe reason.
- [ ] Active capture keeps a persistent local indicator visible.
- [ ] Active capture always exposes one-action `Stop`.
- [ ] Losing all visible indicator surfaces stops or fails capture closed.
- [ ] `Stop` finalizes the current recording without affecting unrelated app
  state.
- [ ] Capture evidence uses current capture-session state and contains no audio
  content, transcript content, credentials, or signed URLs.

## Automated Validation

```sh
swift test --package-path apps/macos --filter 'CaptureSessionSafetyTests|CaptureControlTests|RecordingPrerequisiteGateTests|RecordingEvidenceTests'
swift run --package-path apps/macos ContractValidation
sh apps/macos/Scripts/validate-capture-session-indicator.sh
```

The cleanup slice must record fresh results before these checkboxes are marked
complete. Historical pre-cleanup results do not prove the current build.

## Manual Smoke

Use `tests/macos/browser-meetings/manual-recording-smoke.md`. Confirm the
indicator appears before accepting active capture, remains visible throughout
the recording, and disappears only after finalization or a truthful failure.
