# Implementation Plan: Надёжная установка и выдача разрешений GRAF

**Branch**: `codex/124-macos-permission-installer-relaunch` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/124-macos-permission-installer-relaunch/spec.md`

## Summary

Исправить три связанных пользовательских разрыва в macOS MVP: честно провести
пользователя через Gatekeeper no-account канала, корректно восстановить
микрофон после отказа и сделать перезапуск после Screen/System Audio
разрешения bounded и совместимым с SwiftUI/AppKit modal lifecycle. Используем
существующие native API и package scripts: добавляем недостающее описание
system-audio capture, разделяем recovery действия по состояниям TCC, закрываем
активную modal session перед существующим `terminateLater` cleanup и обновляем
инструкции публичной страницы. По явному запросу пользователя follow-up release
также публикует updater-enabled bootstrap и подписанный Sparkle appcast через
существующий protected workflow; Developer ID и notarization в owner-only канал
не входят.

## Technical Context

**Language/Version**: Swift 6 / macOS 14.5+, POSIX shell, Python 3.13 test tooling

**Primary Dependencies**: SwiftUI, AppKit, AVFoundation, CoreGraphics,
ScreenCaptureKit, Sparkle 2.9.4, XCTest; no new runtime dependency

**Storage**: Existing local recording/upload stores; no schema change

**Testing**: Focused XCTest/source-contract tests, shell syntax checks, local
installer build/metadata inspection, server public-download tests, and
`infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature`. The slice changes macOS TCC
onboarding, capture privacy metadata, installer trust instructions, and app
termination behavior. It must pass the full Spec Kit flow and focused macOS
validation before the repository gate.

**Release Gate**: `release/deploy`. The explicit follow-up request authorizes
`v2026.07.24.2`: updater-enabled local bootstrap, protected Sparkle signing,
versioned public artifacts, last-good appcast replacement, and remote smoke.
Developer ID/notarization remain out of scope for this owner-only channel.

**Target Platform**: macOS 14.5+ Apple Silicon; public server download page is
updated only as user-facing documentation in source

**Project Type**: Native desktop app with a Python web handoff page and native
installer scripts

**Performance Goals**: Permission settings recovery opens immediately; old GRAF
process replies to termination within 10 seconds, including modal onboarding

**Constraints**: No TCC mutation/reset, no PPPC profile, no removed audio driver,
no global Gatekeeper disable, no force-kill, no raw meeting content in evidence,
no new runtime dependency, preserve manual start/stop and visible capture state

**Scale/Scope**: One macOS permission onboarding surface, one AppKit lifecycle
delegate, one local `.pkg` build path, and the public download handoff text

## Constitution Check

*GATE: PASS.* The feature preserves the macOS system-audio-first MVP, normal
manual start/stop, local capture visibility, and one-action stop. It adds no
driver, no TCC mutation, no hidden capture, no direct desktop-to-MediaScribe
credential path, and no deletion/privacy policy change. The local self-signed
channel is explicitly separated from public Developer ID/notarized release.
The gate was re-checked after design: the contracts below keep permission state
truthful and retain the bounded termination safety gate.

## Validation Plan

1. Run the no-account install and permission/relaunch scenarios in
   `quickstart.md` on a clean or disposable macOS user profile; record only
   metadata, status labels and process timing.
2. Run focused XCTest contracts for permission UI, modal dismissal, installer
   metadata, and no-driver packaging.
3. Run shell syntax checks and build a local self-signed package with the
   existing identity; inspect app and package signatures without modifying TCC.
4. Run public download page tests and `infra/scripts/ci-local.sh`.
5. Build `v2026.07.24.2` with the public feed and active manifest key; verify
   Sparkle metadata, same local designated requirement, and package integrity.
6. Run the protected `sign-graf-app-update.yml` workflow from the exact current
   `master` tag, using a metadata-only Keychain attestation from the release
   operator; never copy a private key into the repository or local evidence.
7. Run `infra/scripts/ci-local.sh`, then `cd-remote.sh --dry-run` and
   `cd-remote.sh --execute` when the release candidate gate is satisfied.
8. Upload versioned ZIP/PKG and checksums first, replace the public appcast last,
   fetch every public artifact, and verify rollback evidence and Sparkle
   continuity. Do not claim Developer ID/notarization or universal Gatekeeper
   trust.

## Project Structure

### Documentation (this feature)

```text
specs/124-macos-permission-installer-relaunch/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── validation/
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/Installer/Scripts/build-local-installer.sh
apps/macos/Installer/README.md
apps/macos/Scripts/validate-app-updates.sh
apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift
apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift
apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift
apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift
apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift
apps/server/src/twobrain_rec_server/public/templates/public/download.html
apps/server/tests/unit/test_public_landing.py
CHANGELOG.md
```

**Structure Decision**: Keep the existing native macOS app and installer as the
source of capture behavior and package metadata. Keep the server download page
as a thin handoff/documentation surface. Extend existing source-contract tests;
do not introduce a new permission framework, installer dependency, service, or
audio component.

## Implementation Phases

### Phase 1 — Installer and user-facing trust path

- Add the missing system-audio privacy description to the generated app
  `Info.plist`.
- Extend the existing update/app validation and installer evidence tests so a
  package without the required metadata fails before distribution.
- Update `apps/macos/Installer/README.md` and the public download handoff with
  the one supported Finder/System Settings Gatekeeper confirmation. State that
  the free channel is not notarized and do not prescribe global security
  changes.

### Phase 2 — Permission onboarding

- Keep normal AVFoundation request behavior for `unknown` microphone state.
- Make `denied` and `restricted` microphone states open settings as the truthful
  recovery action instead of presenting a misleading repeat request.
- Guard the shared microphone permission service so a stale/denied start path
  cannot re-request as if the user had never answered.
- Mark the system-audio settings path as requiring relaunch and expose an
  explicit `Перезапустить GRAF` action. Reset this flag on a new process and
  refresh both platform states on activation.

### Phase 3 — Bounded AppKit termination

- Preserve the existing `terminateLater` and ten-second timeout.
- Clear SwiftUI permission and meeting prompts before cleanup.
- End attached/detached sheets, abort the active AppKit modal session, and close
  visible modal helper windows before posting the existing cleanup notification.
- Add source-contract assertions for the new lifecycle guarantees without
  adding a force-kill path.

### Phase 4 — Validation and evidence

- Run focused macOS/server tests, shell syntax checks, and local package build.
- Inspect app metadata/signature and ensure no driver/TCC mutation was added.
- Run the no-account quickstart on an available disposable macOS profile if
  possible, then run `infra/scripts/ci-local.sh`.
- Mark implementation tasks complete only after their evidence exists.

### Phase 5 — Sparkle bootstrap and release publication

- Build the bootstrap with `GRAF_UPDATE_FEED_URL` and the public key from
  `UpdateSigningKey.json`; the package remains manually trusted on new Macs.
- Validate the candidate against the previous GRAF archive with the existing
  same-identity, monotonic-version and archive-safety checks.
- Keep the release tag at the exact current `origin/master` commit, let the
  protected GitHub environment sign the appcast, and require the matching
  Keychain attestation before publication.
- Publish versioned artifacts before `graf-appcast.xml`; preserve the prior
  package/appcast for rollback and record only metadata-only evidence.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| None | The feature reuses the existing macOS app, installer and server page. | No new abstraction, service, dependency, or privileged component is needed. |
