# Quickstart: Деликатный индикатор источника записи

## Prerequisites

- macOS 14+ host with the repository checked out.
- Existing Swift package dependencies resolved.
- No production credentials, raw audio, transcript, or meeting content.

## Focused validation

From the repository root:

```sh
swift test --package-path apps/macos --filter CaptureIndicatorTests
swift test --package-path apps/macos --filter AppControlAccessibilityTests
```

Expected: source mapping, known/manual/unknown fallbacks, lifecycle visibility,
single-line/accessibility contracts, and preserved Pause/Resume/Stop contracts
all pass.

## Local app smoke

Build the native app on a macOS host:

```sh
apps/macos/Scripts/build-local-app.sh
```

In the local GRAF app, inspect an active recording in these states:

1. A verified meeting app: the single upper capsule shows the recording state
   and a quiet `Источник · <app>` label.
2. Manual system audio: the source reads `Системный звук`.
3. Missing/invalid evidence: the source reads `Источник не определён`.
4. Pause, resume, degraded state and stopping: source text stays stable and
   existing actions remain visible and independently usable.
5. Narrow window or a long app name: source stays one line and truncates at the
   tail; the capsule does not gain a second surface and Stop remains available.
6. After stop/finalization: the active source label is no longer presented.

Also inspect the attached reference screenshot as the before state: the after
state should preserve its quiet top placement while adding only the secondary
source copy inside the existing capsule.

## Repository gate

Before closeout run:

```sh
infra/scripts/ci-local.sh --fast
```

No deploy, release, notarization, Sparkle, or appcast check is part of this
feature.
