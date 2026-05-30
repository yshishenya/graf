# Runtime Core Audio Proof Report

**Status**: ACCEPTED (Core Audio publication only; real passthrough pending)

This report is the required evidence gate before any US1 implementation task
that publishes real virtual devices or installer behavior.

## Evidence Requirements

Fill this report only after running the runtime proof on an Apple Silicon Mac.
One machine result unlocks architecture work; it is not release-candidate matrix
coverage.

Required evidence:

- Date:
- Machine:
- CPU architecture:
- macOS version:
- Proof command:
- Build artifact:
- Virtual device publication result:
- `2brain Rec Microphone` visible to macOS:
- `2brain Rec Speaker` visible to macOS:
- Self-routing rejection baseline:
- Passthrough/mirror exercised:
- Continuity signal exercised:
- Permissions/signing/notarization assumptions:
- Known limitations:
- Decision: Core Audio path accepted, rejected, or still blocked.

## Current Result

Runtime Core Audio publication is accepted for the Phase 0 architecture gate.
The proof AudioServerPlugIn bundle was installed into the HAL plug-in directory,
Core Audio loaded it, and the runtime visibility probe observed both required
MVP virtual devices.

- Date: 2026-05-27 16:10:10 MSK
- Machine: MacBook-Pro-7.local
- CPU architecture: arm64
- macOS version: 26.2 (25C56)
- Build command: `make -C apps/macos/AudioDriver proof-plugin-build`
- Install command: direct equivalent of `make -C apps/macos/AudioDriver proof-plugin-install`
- Proof command: `make -C apps/macos/AudioDriver proof-runtime-probe-run`
- Build artifact: `apps/macos/AudioDriver/.build/proof/2brainRecProof.driver`
- Runtime probe artifact: `apps/macos/AudioDriver/.build/proof/runtime-device-probe`
- Virtual device publication result: ACCEPTED; the probe enumerated Core Audio
  devices visible to the current user and found both required virtual devices.
- `2brain Rec Microphone` visible to macOS: Yes
- `2brain Rec Speaker` visible to macOS: Yes
- Self-routing rejection baseline: Not exercised by this publication proof;
  remains a US1 implementation and route-verification task.
- Passthrough/mirror exercised: Not exercised by this publication proof;
  remains a US1/US2 implementation task.
- Continuity signal exercised: Not exercised by this publication proof; remains
  a US2 timing implementation task.
- Permissions/signing/notarization assumptions: The proof bundle was ad-hoc
  signed for local validation only and installed into
  `/Library/Audio/Plug-Ins/HAL`. It is not a release installer, Developer ID
  signature, or notarized package.
- Known limitations: This proof publishes visible devices with minimal silent
  streams. It does not implement production routing, passthrough, buffering,
  self-routing rejection, installer UX, notarization, or track capture.
- Decision: Core Audio publication path is accepted for architecture work. US1
  implementation may start, but production tasks must replace the proof bundle
  with the real signed/notarized driver and route-verification implementation.

## Current Runtime Alignment (2026-05-31)

The desktop app now launches locally when Developer Tools Security is enabled for
ad-hoc development builds. The installed driver package and both virtual devices
are visible to macOS.

The app must still report **not ready for calls** because real bidirectional
audio passthrough has not been implemented and verified end to end. Current
readiness checks are intentionally strict:

- virtual microphone visible in macOS: accepted
- virtual speaker visible in macOS: accepted
- physical microphone to virtual microphone audio path: pending
- virtual speaker to physical speaker audio path: pending
- browser/meeting end-to-end call validation: pending

Any UI state, checklist item, or task that suggests production passthrough is
complete is obsolete and must be corrected before release readiness review.

Safety correction added on 2026-05-31:

- high-frequency HAL callback trace is disabled by default and can only be
  enabled through the explicit verbose trace flag;
- proof devices report that they cannot become the system default device while
  passthrough is pending, so a local install should not steal normal system
  input/output.

## Passthrough Prototype Scope (2026-05-28 to 2026-05-31)

- Decision: Passthrough scaffolding exists, but production passthrough is not yet
  accepted.
- Implemented/prototyped pieces:
  - shared memory ring buffer bridge between the HAL driver and desktop app:
    `apps/macos/Shared/Sources/SharedAudioMemory.swift` and
    `apps/macos/Shared/CShmHelpers/shm_helpers.c`
  - app-side Core Audio bridge scaffolding:
    `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`
  - driver-side shared memory reads/writes in
    `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`
  - route status model updates in `AudioModels.swift`
- Not accepted yet:
  - `StartIO`/`StopIO` do not yet prove a live physical-device bridge for normal
    calls.
  - The app does not yet run a safe user-visible readiness flow that proves real
    microphone and speaker audio movement.
  - Browser meeting targets have not been validated against the virtual
    microphone and virtual speaker paths.
- Validation completed so far:
  - `swift build --package-path apps/macos -c release --product TwoBrainRecApp`
  - `make -C apps/macos/AudioDriver proof-plugin-build`
  - `sh apps/macos/Scripts/validate-us1-regression.sh`

These commands validate buildability, model behavior, and Core Audio publication
regression coverage. They do not prove production passthrough.

## Publication Spike Attempt

- Date: 2026-05-27
- Build command: `make -C apps/macos/AudioDriver proof-plugin-build`
- Build artifact: `apps/macos/AudioDriver/.build/proof/2brainRecProof.driver`
- Artifact status: Builds as a Mach-O arm64 bundle and passes ad-hoc code-sign
  verification.
- Exported factory symbol: `_TwoBrainRecProofDriverFactory`
- Initial installation status: `/Library/Audio/Plug-Ins/HAL` is root-owned, so
  installing the proof bundle and restarting `coreaudiod` requires admin
  privileges.
- Follow-up after first manual install: the bundle installed successfully, but
  Core Audio still did not list the proof devices. The installed bundle was
  structurally present and signed, but discovery logs did not show the proof
  bundle being loaded. The proof package now includes an
  `IOPlatformExpertDevice` loading condition and clears extended attributes
  during install before restarting `coreaudiod`.
- Final follow-up: after fixing the AudioServerPlugIn driver reference shape,
  adding empty device control lists, and adding `kAudioDevicePropertyClockDomain`
  responses, Core Audio loaded the proof bundle and published both MVP devices.
- Current decision: ACCEPTED for the Phase 0 Core Audio publication gate.

Observed device list:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: FOUND
- 2brain Rec Speaker: FOUND
Runtime Core Audio publication proof: ACCEPTED
```
