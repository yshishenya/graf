# macOS Recording Device Matrix

## Purpose

Validate the current recording sources without requiring a separate audio
routing component. System audio is app-owned and captured with
`SystemAudioCaptureService`; microphone audio is app-owned and captured with
`MicrophoneCaptureService`.

## Operating Systems

| OS | CPU | Status |
|---|---|---|
| macOS 14.5 | Apple Silicon | Required MVP baseline |
| Latest stable macOS at RC | Apple Silicon | Required RC rerun |
| Intel macOS | Intel | Outside current MVP scope |

## Microphone Input Classes

| Class | Expected behavior |
|---|---|
| Built-in microphone | Eligible after permission and availability checks |
| Wired headset microphone | Eligible after permission and availability checks |
| USB microphone/headset | Eligible after permission and availability checks |
| Bluetooth/AirPods microphone | Eligible after permission and availability checks |
| Virtual, aggregate, or multi-output input | Rejected fail-closed by the generic recording-input policy |
| Unknown or unavailable input | Rejected fail-closed with a truthful blocker |

## Required Scenarios

| Scenario | Expected result | Evidence |
|---|---|---|
| Fresh app-only install | GRAF launches without privileged audio installation | Installer package inspection |
| System-audio permission denied | Recording start is blocked with a recoverable permission reason | `RecordingPrerequisiteGateTests` |
| Microphone permission denied | Recording start is blocked with a recoverable permission reason | `RecordingPrerequisiteGateTests` |
| Eligible physical microphone | Microphone source starts and feeds the writer | `MicrophoneCaptureServiceTests` |
| Ineligible microphone class | Start fails closed before recording | `RecordingMicrophoneSelectionTests` |
| Microphone changes before start | Current eligible input is resolved again | `tests/macos/physical-devices/device-change-recovery.md` |
| Permission changes | Current permissions are re-evaluated | `tests/macos/physical-devices/permission-recovery.md` |
| System audio plus microphone | Both PTS-bearing sources enter one canonical timeline | `LocalRecordingWriterSystemAudioTests` |

## Release Rule

No device class is release-ready from source review alone. Run a current-build
record/stop smoke and verify exactly the finalized v5 WAV, review M4A and
`manifest.json` for every supported class claimed by the release.
