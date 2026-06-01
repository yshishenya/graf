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

Status: Phase 0 Core Audio publication proof, low-resource idle-safe
publication, and non-recording passthrough smoke are accepted for the current
local development build. The local proof AudioServerPlugIn publishes both MVP
virtual devices and the runtime probe sees them in macOS Core Audio.

This is not recording acceptance. It does not prove durable recorded
local/remote track artifacts, long-duration capture integrity, upload,
transcription, retention, or deletion behavior. The current expected app state
after local install is non-recording passthrough ready when route evidence is
valid, with recording/transcription/upload inactive.

Safety behavior while recording is pending:

- proof devices are visible for Core Audio publication validation;
- physical routes are opened only when virtual-device client I/O or an explicit
  check needs them;
- low-resource idle keeps public virtual devices visible/alive but non-running;
- verbose HAL callback tracing is disabled by default to avoid high `coreaudiod`
  CPU during audio IO.

After changing driver code, reinstall the proof bundle and restart Core Audio
before judging runtime behavior:

```sh
make -C apps/macos/AudioDriver proof-plugin-install
```

Created proof harnesses:

- `Sources/Proof/VirtualDeviceProof.cpp`
- `Sources/Proof/PassthroughTimingProof.cpp`
- `Sources/Proof/ProofRunner.cpp`

The selected implementation path remains Core Audio virtual-device proof first.
US1 implementation may proceed because `RuntimeProofReport.md` records an
ACCEPTED Apple Silicon validation result. The proof bundle is not production
routing, passthrough, capture, signing, notarization, or installer UX.

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

Current observed result: ACCEPTED after installing the proof HAL bundle. The
probe finds both `2brain Rec Microphone` and `2brain Rec Speaker`.

The minimal publication proof bundle is built with:

```sh
make -C apps/macos/AudioDriver proof-plugin-build
```

The generated bundle is:

```text
apps/macos/AudioDriver/.build/proof/2brainRecProof.driver
```

For local proof only, install it into the system HAL plug-in directory and
restart Core Audio:

```sh
make -C apps/macos/AudioDriver proof-plugin-install
```

This command requires an admin password because Apple's AudioServerPlugIn header
documents `/Library/Audio/Plug-Ins/HAL` as the HAL plug-in location. The proof
installer also clears extended attributes after copying the bundle so local
provenance metadata does not interfere with HAL discovery. After installation,
rerun:

```sh
make -C apps/macos/AudioDriver proof-runtime-probe-run
```

The probe reports both MVP devices as found in the current local proof state.
Remove the proof plug-in with:

```sh
make -C apps/macos/AudioDriver proof-plugin-uninstall
```

Verbose driver trace is intentionally opt-in and only takes effect after the next
Core Audio restart:

```sh
make -C apps/macos/AudioDriver proof-plugin-trace-enable
make -C apps/macos/AudioDriver proof-plugin-install
make -C apps/macos/AudioDriver proof-plugin-trace-read
make -C apps/macos/AudioDriver proof-plugin-trace-disable
```

The broader local foundation validation command is:

```sh
sh apps/macos/Scripts/validate-foundation.sh
```

This runs the Swift build, contract validation executable, and proof scaffold.
In standard macOS dev environments, it is followed by full `swift test` and
manual capture-path regression verification (`sh apps/macos/Scripts/validate-us1-regression.sh`).

The implementation-ready US1 gate is intentionally stricter:

```sh
sh apps/macos/Scripts/validate-us1-gate.sh
```

It fails until `RuntimeProofReport.md` records an `ACCEPTED` Core Audio
publication result with observed Apple Silicon runtime evidence. Passing this
gate does not mean recording, long-duration capture, upload, or transcription is
ready.

## Signing And Distribution Prerequisites

- Apple Developer Program membership with Developer ID Application and Developer ID Installer certificates.
- Notarization access for the installer package and any signed helper/component artifacts.
- Local signing identities must stay outside the repository.
- Entitlements, provisioning profiles, generated packages, notarization tickets, logs, and credentials must not be committed.

## Real-Time Boundary

Code in this directory must stay small and predictable. It should not perform network calls, server upload, transcription, LLM calls, retention deletion, or diagnostic bundle packaging.
