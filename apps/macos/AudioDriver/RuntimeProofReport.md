# Runtime Core Audio Proof Report

**Status**: BLOCKED

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

Runtime Core Audio publication is not yet proven. The runtime visibility probe
was added and executed on an Apple Silicon Mac, but no `2brain Rec` virtual
devices are currently published to Core Audio.

- Date: 2026-05-27 15:26:00 MSK
- Machine: MacBook-Pro-7.local
- CPU architecture: arm64
- macOS version: 26.2 (25C56)
- Proof command: `make -C apps/macos/AudioDriver proof-runtime-probe-run`
- Build artifact: `apps/macos/AudioDriver/.build/proof/runtime-device-probe`
- Virtual device publication result: BLOCKED; the probe enumerated Core Audio
  devices visible to the current user but did not find the required virtual
  devices.
- `2brain Rec Microphone` visible to macOS: No
- `2brain Rec Speaker` visible to macOS: No
- Self-routing rejection baseline: Not exercised because the virtual devices
  are not present.
- Passthrough/mirror exercised: Not exercised because the virtual devices are
  not present.
- Continuity signal exercised: Not exercised because the virtual devices are
  not present.
- Permissions/signing/notarization assumptions: No signed AudioServerPlugIn or
  installer package was installed for this probe. This result validates only
  runtime visibility of currently installed Core Audio devices.
- Known limitations: The current implementation still contains a scaffold proof
  and a runtime visibility probe, not a device-publication implementation.
- Decision: Core Audio path is still blocked. US1 implementation must not start
  until an ACCEPTED runtime proof shows both `2brain Rec Microphone` and
  `2brain Rec Speaker` visible to macOS.

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
- Current decision: still BLOCKED until the proof bundle is installed by an
  admin user, Core Audio reloads it, and `proof-runtime-probe-run` observes both
  MVP virtual devices.

Observed device list:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: MISSING
- 2brain Rec Speaker: MISSING
Runtime Core Audio publication proof: BLOCKED
```
