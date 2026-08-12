# GRAF macOS MVP Architecture

This document is the architecture reference for the macOS-only MVP slice.

## 1) Scope And Stack

- Scope: interactive macOS delivery only (`macOS 14.5+`) through one universal
  installer for Apple Silicon (`arm64`) and Intel (`x86_64`).
- Primary implementation stack: SwiftUI + Swift Package modules for app layer,
  ScreenCaptureKit/system-audio capture for the MVP recording pivot, and
  shell-based scripts for installer lifecycle.
- No desktop Rust/Flutter/Dart layer is used for this slice.

## 2) Functional boundaries

- **System-audio MVP recording**: uses macOS capture permissions and a
  user-confirmed capture scope. It does not require driver install, driver
  repair, virtual-device publication, Core Audio restart, or HAL runtime probes.
- **Retired virtual driver**: not part of the product, installer, or active
  build. Future routing work requires a separate decision and safety evidence.
- **App core (Swift)**: route verification, permission/device state, capture control surface, track/buffer continuity snapshots, local recovery hints, and diagnostics.
- **Storage in this slice**: local encrypted buffer artifacts and manifests only.
- **No backend audio responsibilities in client**: app does not send raw audio directly to MediaScribe and does not store API credentials.

## 2.1) Current Runtime Status (2026-06-01)

### System-audio pivot status (2026-08-12)

Accepted for the current feature branch:

- MVP recording readiness is checked from the Record flow and permission gate,
  not from driver repair or virtual-device visibility.
- The app-only universal installer is the release path; legacy driver diagnostics
  are not an installer or MVP acceptance dependency.
- No-HAL validation is enforced by
  `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`.
- CPU/resource gate evidence is recorded through metadata-only process sampling
  in `apps/macos/Scripts/sample-system-audio-cpu-gate.sh`.

Not accepted yet:

- full settled idle/active/stop/quit CPU gate evidence;
- controlled meeting artifact validation on a real app build;
- 30-minute development and 75-minute manual release recording runs.

Accepted:

- local development universal installer builds successfully;
- the packaged `GRAF` executable contains `arm64` and `x86_64` slices;
- app launches from `/Applications/GRAF.app` when Developer Tools Security
  is enabled for ad-hoc development builds;

Not accepted yet:

- active recording session start/stop as a production user workflow;
- persistent recording indicator and one-action stop during active capture;
- separate recorded local and remote track artifacts;
- long-duration 30/60 minute recording integrity acceptance;
- backend upload, MediaScribe transcription, dashboard notes, retention, and
  deletion workflows.

The correct current app behavior is to support non-recording passthrough while
remaining explicit that recording, transcription, upload, and external egress do
not start from the audio-route readiness path.

## 3) Recovery model

1. **Permission/path failures** are surfaced as distinct UI states.
2. **Restart recovery** preserves local buffer items not yet uploaded and finalizes interrupted tracks as degraded where needed.
3. **Installer safety** supports update deferral under active-call conditions and truthful partial cleanup or manual remediation reporting.

## 4) Diagnostics and redaction

- Diagnostics are manifest-first and redacted by default using the forbidden-field contract.
- forbidden keys are rejected from diagnostic payloads and replaced by redaction status.

## 5) Installer contract

- Interactive universal install/update only for the current MVP.
- Active capture/call update should not be forced through automatically.
- Reinstall and uninstall flows must be deterministic and reportable.

## 6) Delivery evidence mapping

- Universal installer proof: `specs/147-macos-arch-builds/evidence/universal-installer.md`.
- US1/US2/US3/US4 checklists and proofs: `qa/macos/release-candidate-checklist.md`, `tests/macos/*`.
- Schema and contracts: `tests/macos/contract/*`, `specs/001-macos-audio-driver/contracts/*`.

## 7) Production-readiness runbook

### Required non-interactive checks (can be rerun on CI/local dev)

- `sh apps/macos/Scripts/validate-foundation.sh`
- `sh apps/macos/Scripts/validate-us1-regression.sh`
- `sh apps/macos/Scripts/validate-us1-gate.sh`

### Required interactive checks (QA/Pre-release)

- Build the local installer with Developer Tools Security enabled for ad-hoc
  local builds, or with an Apple application signing identity for pre-release
  builds. Ad-hoc `.app` bundles may install but be killed by AMFI before launch
  when Developer Tools Security is disabled.
- Install package and grant required permissions on clean Apple Silicon and Intel macOS hosts.
- Fresh install + permissions + native system-audio capture readiness.
- Route verification UI: physical mic/speaker selection and `ready` gating.
- Browser meeting matrix on approved targets (Chrome, Opera, Yandex Browser, Yandex Telemost).
- 60-minute capture integrity run for wired/USB/Bluetooth/AirPods-class devices.
- 5-minute server/network outage with local buffering + passthrough continuity.
- Device change recovery (disconnect/switch/Bluetooth profile).
- Installer lifecycle: update (active-call deferred), repair, rollback, uninstall, reinstall.
- Diagnostics export per family with redaction checks.

### Evidence to keep with release

For every production rollout attempt, keep:

- `specs/147-macos-arch-builds/evidence/universal-installer.md` with metadata-only
  slice, package, and publication checks.
- `qa/macos/release-candidate-checklist.md` with all remaining rows filled.
- Signed/notarization completion notes for installer artifacts and installer script outcomes.
- A short note for any open known limitation and explicit product-safe workaround.
