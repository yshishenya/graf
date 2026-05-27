# Runtime Core Audio Proof Report

**Status**: ACCEPTED

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

## Publication Spike Attempt

- Date: 2026-05-27
- Build command: `make -C apps/macos/AudioDriver proof-plugin-build`
- Build artifact: `apps/macos/AudioDriver/.build/proof/2brainRecProof.driver`
- Artifact status: Builds as a Mach-O arm64 bundle and passes ad-hoc code-sign
  verification.
- Exported factory symbol: `_TwoBrainRecProofDriverFactory`
- Installation status: Not installed by the agent. `/Library/Audio/Plug-Ins/HAL`
  is root-owned and local passwordless sudo is unavailable, so installing the
  proof bundle and restarting `coreaudiod` requires an interactive admin
  password.
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
