# Implementation Plan: Universal macOS Installer

**Branch**: `147-macos-arch-builds` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/147-macos-arch-builds/spec.md`

## Summary

Keep one public GRAF installer and make the packaged macOS application
universal. The build script will compile the existing SwiftPM app for `arm64`
and `x86_64`, merge the app executable into one universal Mach-O, package the
app-only installer, and validate both slices before returning success. The
public download page will keep one stable `graf.pkg` link. ARM-only product
gates and stale driver build/installer references will be removed from the
active build and release documentation; historical evidence remains archival.

## Technical Context

**Language/Version**: Swift 6 / SwiftPM, macOS 14.5 minimum; Python 3.13
FastAPI/Jinja for the public download page.

**Primary Dependencies**: SwiftPM, Apple `swift build`, `lipo`, `file`,
`pkgbuild`, `productbuild`, `codesign`, existing FastAPI/Jinja/static public
assets, pytest, XCTest.

**Storage**: No database or storage schema change. The installer is a static
public release asset.

**Testing**: Focused SwiftPM cross-architecture build, architecture inspection,
Swift/XCTest platform support tests, public download unit and contract tests,
shell syntax checks already used by the repository, and the repository gate
`infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: Significant feature / architecture. This changes
the native desktop release artifact, supported platform contract, public
download flow, installer validation, and active release documentation.

**Release Gate**: No production deploy in this slice. Run local build and
repository validation; production publication requires the separate release
gate and explicit approval.

**Target Platform**: macOS 14.5+ on Apple Silicon and supported Intel Macs;
Linux containerized server for the public static asset and download page.

**Project Type**: Native macOS desktop app plus server-rendered public web
surface.

**Performance Goals**: The installed app must launch in the native slice on
both architectures. The public page must retain its existing server-rendered
response path without a client-side architecture decision.

**Constraints**: One installer filename and one product version per release;
no browser architecture detection requirement; no permanent code fork; no
legacy driver package, driver opt-in, driver validation, or driver artifact in
the active build; no new frontend build pipeline; no secrets or private meeting
content in release evidence.

**Scale/Scope**: One macOS app product, one public download page, two native
Mach-O slices, and the active release/install documentation and validation
surfaces.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS.

- Capture-First MVP Integrity: PASS. The slice does not change capture logic,
  recording controls, permissions, or audio data flow; it only makes the
  existing native app executable available to Intel and Apple Silicon.
- Removed routing boundary: PASS with required tasks. The superseded driver is
  not packaged or used as a fallback; active installer/validation references
  must be removed rather than preserved as an opt-in path.
- Data Boundary And Secret Discipline: PASS. No new egress or credentials are
  introduced; release checks inspect metadata and binary architecture only.
- Visible Consent And User Control: PASS. No recording behavior changes.
- Spec-Driven Delivery: PASS. This is a significant architecture/release
  slice and follows the full Spec Kit sequence.
- UX and accessibility: PASS with required public-page checks. The single
  download action remains keyboard accessible and works without JavaScript.

**After Phase 1 design**: PASS. The research and contracts keep the change to
the app executable, installer packaging, public download asset, platform gate,
and active release documentation. No schema, API, or capture contract changes
are required.

## Validation Plan

- Run `swift build` for both `arm64-apple-macosx14.5` and
  `x86_64-apple-macosx14.5` using isolated SwiftPM scratch paths.
- Inspect the merged app executable and final package with `file`/`lipo` and
  verify both slices, bundle metadata, minimum OS, and absence of driver
  package references.
- Run focused Swift platform-support/contract tests and public download unit
  and contract tests.
- Run the feature scenarios from [quickstart.md](./quickstart.md).
- Run `infra/scripts/ci-local.sh` before closeout because the slice changes
  release artifacts, supported architecture, installer validation, and a
  public user-facing flow.
- Do not run production CD or publish the package in this implementation
  slice.

## Project Structure

### Documentation (this feature)

```text
specs/147-macos-arch-builds/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── universal-installer-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/Installer/Scripts/build-local-installer.sh
apps/macos/Installer/README.md
apps/macos/Shared/Sources/Models/PlatformSupport.swift
apps/macos/Shared/Tools/ContractValidation/main.swift
apps/macos/Shared/Tests/PlatformSupportTests.swift
apps/macos/Scripts/validate-system-audio-capture-pivot.sh
apps/macos/Scripts/validate-us1-regression.sh
apps/server/src/twobrain_rec_server/public/templates/public/download.html
apps/server/tests/unit/test_public_landing.py
apps/server/tests/contract/test_public_landing_contract.py
docs/prd-voice-layer-final.md
docs/current-product-status.md
CHANGELOG.md
```

**Structure Decision**: Reuse the existing SwiftPM package, shell installer,
server-rendered public page, static download asset, and focused validation
surfaces. No new runtime dependency, frontend toolchain, app target, database
model, or architecture-specific product fork is introduced.

## Complexity Tracking

No constitution violations. The second architecture build is required by the
user-approved Intel support decision; the universal merge is the smallest way
to keep one installer and one public download path.
