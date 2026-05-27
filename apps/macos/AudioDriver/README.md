# 2brain Rec macOS Audio Component

This directory owns the thin macOS audio component for the driver-first MVP.

## Scope

- Publish `2brain Rec Microphone` and `2brain Rec Speaker`.
- Preserve physical microphone passthrough to meeting targets.
- Receive virtual speaker output, pass it to the selected physical output, and mirror it for desktop capture.
- Emit timing, drift, dropout, route, and passthrough health signals.
- Avoid policy, upload, retention, purge, diagnostics packaging, or MediaScribe responsibilities.

## Phase 0 Proof Gate

Before user-story implementation, the proof harness must demonstrate that the selected macOS audio technology can:

- publish both MVP virtual devices on Apple Silicon macOS 14.5 and latest stable macOS at release-candidate time;
- block or reject self-routing;
- keep remote speaker audio out of the virtual microphone path;
- sustain live passthrough while the desktop app simulates backend/network unavailability;
- surface continuity signals for dropout and clock drift accounting.

The current planning decision favors a Core Audio virtual-device approach. AudioDriverKit remains a researched fallback only if the proof shows it better satisfies the MVP virtual-device shape and distribution constraints.

## Current Proof Status

Status: scaffolded; runtime visibility probe executed and blocked because the
MVP virtual devices are not yet published to macOS Core Audio.

Created proof harnesses:

- `Sources/Proof/VirtualDeviceProof.cpp`
- `Sources/Proof/PassthroughTimingProof.cpp`
- `Sources/Proof/ProofRunner.cpp`

The selected implementation path remains Core Audio virtual-device proof first.
No user-story driver implementation should proceed until the blocked runtime
result in `RuntimeProofReport.md` is replaced with an ACCEPTED Apple Silicon
validation result.

## Proof Commands

The current reproducible scaffold check is:

```sh
make -C apps/macos/AudioDriver proof-scaffold-run
```

Expected current output includes:

```text
AudioDriver proof scaffold: PASS
Runtime Core Audio publication proof: NOT RUN
```

This command is not sufficient to start real US1 virtual-device publication.
Before US1 driver implementation, record the Apple Silicon runtime proof in
`RuntimeProofReport.md`.

The runtime visibility probe is:

```sh
make -C apps/macos/AudioDriver proof-runtime-probe-run
```

It enumerates devices visible through Core Audio and succeeds only when both
`2brain Rec Microphone` and `2brain Rec Speaker` are present.

Current observed result: BLOCKED. The command builds and runs, but the expected
virtual devices are missing because no publication implementation has been
installed yet.

The broader local foundation validation command is:

```sh
sh apps/macos/Scripts/validate-foundation.sh
```

This runs the Swift build, contract validation executable, and proof scaffold.
The local Swift toolchain used during this remediation does not provide
`XCTest` or Swift `Testing`, so `ContractValidation` is the executable validation
gate until a full Xcode test target is introduced.

The implementation-ready US1 gate is intentionally stricter:

```sh
sh apps/macos/Scripts/validate-us1-gate.sh
```

It fails until `RuntimeProofReport.md` records `**Status**: ACCEPTED` with
observed Apple Silicon Core Audio runtime evidence.

## Signing And Distribution Prerequisites

- Apple Developer Program membership with Developer ID Application and Developer ID Installer certificates.
- Notarization access for the installer package and any signed helper/component artifacts.
- Local signing identities must stay outside the repository.
- Entitlements, provisioning profiles, generated packages, notarization tickets, logs, and credentials must not be committed.

## Real-Time Boundary

Code in this directory must stay small and predictable. It should not perform network calls, server upload, transcription, LLM calls, retention deletion, or diagnostic bundle packaging.
