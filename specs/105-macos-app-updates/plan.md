# Implementation Plan: Safe macOS App Updates

**Branch**: `105-macos-app-updates` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/105-macos-app-updates/spec.md`

## Summary

Add a release-grade self-update path to `GRAF.app` using the latest stable Sparkle 2 framework, its standard update UI, signed HTTPS appcasts, EdDSA archive verification, and the existing stable `pro.2brain.graf` application identity. Sparkle owns scheduling, download, validation, replacement, rollback, and relaunch. A small app-owned controller adds capture-aware deferral and publishes a compact state to the native shell and embedded cabinet sidebar. The existing `.pkg` remains the initial/bootstrap installer; later in-app updates use a versioned signed app archive.

## Technical Context

**Language/Version**: Swift 6.0 package on macOS; POSIX shell for packaging; Python 3 only for existing repository validation helpers

**Primary Dependencies**: AppKit, SwiftUI, WebKit, Sparkle `2.9.4` pinned exactly as the latest stable release verified on 2026-07-17

**Storage**: Sparkle-owned `UserDefaults` for check schedule and user choices; no new database or meeting-data storage; generated update archives/appcast are release artifacts

**Testing**: XCTest through SwiftPM, existing server pytest contracts for the embedded sidebar, shell validation, signed-bundle inspection, controlled old-to-new update smoke, and canonical `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: High-risk feature. The work changes application update trust, signing, permission retention, app relaunch, capture-adjacent UX, and a public release surface.

**Release Gate**: No production publish or deploy in the implementation lane. Public activation requires a separately approved release closeout with Developer ID signing, notarization, stapling, signed feed/archive publication, controlled update smoke, and deployment approval if the public server assets change.

**Target Platform**: Apple Silicon, macOS 14.5+

**Project Type**: Self-hosted macOS desktop application with an embedded server-rendered cabinet and an app-only native installer

**Performance Goals**: Updater initialization adds less than 200 ms to launch; scheduled checks remain asynchronous; sidebar state converges within 5 seconds; manual checks usually resolve within 10 seconds; no capture callback or one-action stop path waits on update work

**Constraints**: Preserve bundle identifier, install location, signing lineage, designated requirement, microphone and Screen/System Audio permissions; never interrupt active capture or finalization; no silent installation; no system profiling; no secrets or meeting content in update traffic/evidence; fail closed when configuration or trust is incomplete

**Scale/Scope**: One stable channel, one desktop application, one public HTTPS appcast, one versioned full archive per published update; beta channels, mandatory updates, enterprise fleet management, and custom delta-retention policy are out of scope

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **Capture-First MVP Integrity — PASS**: installation/relaunch is postponed while capture, transitions, finalization, or termination cleanup are protected; no audio component or Core Audio mutation is introduced.
- **Visible Consent And User Control — PASS**: updates are offered, not silently installed; recording controls and one-action stop remain authoritative.
- **Data Boundary And Secret Discipline — PASS**: the client receives a public HTTPS catalog, sends no meeting content or profile, embeds only a public verification key, and keeps release private keys outside git and the hosting server.
- **Deletion Truth And Lifecycle Accounting — PASS / not content-bearing**: the feature creates no meeting artifact. Update logs are metadata-only and bounded.
- **Spec-Driven Delivery With Testable Gates — PASS**: full specify, clarify, plan, checklist, tasks, analyze, issues, implementation, quickstart, focused tests, canonical CI, and release-only gates are defined.
- **Platform constraints — PASS**: native macOS packaging and update primitives remain authoritative; no cross-platform updater abstraction owns application identity or installation.
- **Post-design re-check — PASS**: the design keeps app identity stable, uses authenticated release artifacts, defines rollback and capture deferral, and does not require a constitution exception.

## Validation Plan

1. Resolve the pinned dependency and run focused Swift tests for update state, capture deferral, user choices, menu availability, and WebView bridge behavior.
2. Run focused server template/static-asset tests proving the embedded-only left-sidebar slot is present, hidden by default, accessible, and does not appear in ordinary browser cabinet pages.
3. Build a release-like local app with the existing stable local signing identity, verify the embedded framework and nested helpers, archive contents, Info.plist security keys, bundle identity, designated requirement, and update catalog contract.
4. Run a controlled two-version HTTPS update smoke: current/no-update, newer update, user defer, active-capture install deferral, post-capture offer, install/relaunch, invalid signature rejection, and old app rollback/continued launch.
5. Run the existing permission-retention procedure before and after two sequential same-identity updates without modifying TCC databases.
6. Run `swift test --package-path apps/macos`, the feature quickstart, and `infra/scripts/ci-local.sh` before closeout.
7. Do not publish an appcast/archive, tag, GitHub Release, or production change without explicit release approval and Developer ID/notarization evidence.

## Project Structure

### Documentation (this feature)

```text
specs/105-macos-app-updates/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── update-client-contract.md
│   ├── update-publication-contract.md
│   └── sidebar-update-badge-contract.md
├── checklists/
│   ├── requirements.md
│   └── update-safety.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── Package.swift
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/Updates/AppUpdateController.swift
├── RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
├── RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift
├── RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
├── Installer/Scripts/build-local-installer.sh
├── Installer/Scripts/prepare-app-update.sh
├── Installer/README.md
├── Scripts/validate-app-updates.sh
└── Shared/Tests/
    ├── AppUpdateControllerTests.swift
    ├── EmbeddedCabinetUpdateBridgeTests.swift
    └── InstallerLifecycleEvidenceTests.swift

apps/server/src/twobrain_rec_server/
└── cabinet/
    ├── templates/cabinet/components/sections.html
    └── static/cabinet/cabinet.css

apps/server/tests/
├── unit/test_cabinet_template_sections.py
└── contract/test_cabinet_static_assets_contract.py

qa/macos/release-candidate-checklist.md
docs/current-product-status.md
CHANGELOG.md
```

**Structure Decision**: Reuse the existing SwiftPM app, installer, public download surface, embedded cabinet sidebar, and their existing tests. Add one updater controller and one release helper; do not introduce a second installer, background daemon, bespoke download client, new database, or new service.

## Complexity Tracking

No constitution violations or justified exceptions.
