# Implementation Plan: Developer ID как единственный публичный macOS-релиз

**Branch**: `130-developer-id-release` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Summary

Закрепить Developer ID Application/Installer, notarization, stapling и
Gatekeeper как единственный активный путь публичной macOS-дистрибуции. Для уже
опубликованного перехода `v2026.07.26.6` добавить отдельную проверку ручного
`.pkg` bootstrap от исторического local/self-signed клиента к Developer ID,
которая запрещает appcast. После перехода обычный Sparkle-путь принимает только
Developer ID→Developer ID lineage. Активные runbook/README/checklist и Spec Kit
артефакты привести к этой схеме; старые receipts оставить только как
помеченную историю.

## Technical Context

**Language/Version**: POSIX `sh` для release scripts; Swift 5.9+/XCTest для статических lifecycle evidence tests; Markdown/YAML/JSON/XML для release artifacts.

**Primary Dependencies**: Apple `codesign`, `productbuild`, `pkgutil`, `xcrun stapler`, `spctl`; существующий Sparkle 2.9.4 и `release-signing-common.sh`; GitHub Actions/CLI. Новые зависимости не нужны.

**Storage**: Filesystem bundles/packages, public appcast/download host, GitHub Releases; private Apple/Ed25519 material remains in local Keychain/GitHub environment and is not stored here.

**Testing**: `sh -n`, focused shell validator/build tests, `swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests`, `infra/scripts/ci-local.sh`, and the release quickstart. Existing notarized artifacts provide metadata-only transition evidence.

**Risk / Validation Lane**: `high-risk-feature` for release trust, update lineage and operator guidance. The change can block publication and must fail closed for local/ad-hoc identities.

**Release Gate**: `cd dry-run` for this documentation/validator slice; `cd execute` is reserved for the next CalVer release after validation. `v2026.07.26.6` has already passed its separate deploy gate.

**Target Platform**: macOS 14.5+ direct distribution; Apple Developer ID Application/Installer identities; public HTTPS download and Sparkle feed.

**Project Type**: Self-hosted desktop macOS app with a server-backed release/download workflow.

**Performance Goals**: Validation must fail before any public file/feed mutation; no new runtime path or network service is introduced.

**Constraints**: Preserve exact bundle identity `pro.2brain.graf`, CalVer, Sparkle feed URL/public key continuity, hardened runtime, privacy/capture gates, rollback assets and secret-free evidence. Do not revive self-signed public release or add App Store distribution.

**Scale/Scope**: One macOS app, one public feed/download channel, one historical signing transition, and all active release documentation/instructions discovered by the repository-wide audit.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence / decision |
|------|--------|--------------------|
| Public macOS distribution integrity | PASS | Public app/package require Developer ID, hardened runtime, notarization, staple and Gatekeeper. |
| Update lineage | PASS | Ordinary updates preserve bundle/team/designated requirement/feed/Sparkle trust; migration is manual `.pkg` only. |
| Fail-closed publication | PASS | Build/validation reject local, ad-hoc and owner-only identities before public mutation. |
| Secret and evidence hygiene | PASS | Only checksums, IDs and metadata are documented; no keys, passwords, signed URLs or meeting content. |
| Product/privacy/capture gates | PASS | No capture, transcript, storage or deletion behavior changes. |
| Ponytail | PASS | Reuse the existing validator and release-signing helpers; add one explicit migration mode and one thin wrapper. |

## Research

Phase 0 is captured in [research.md](research.md). The decisive local evidence is
that `validate-app-updates.sh` currently rejects a signing-kind change, while the
published `.5` predecessor is local/self-signed and `.6` is notarized Developer
ID. Therefore the transition needs a named manual mode rather than weakening
ordinary continuity checks.

## Validation Plan

1. Static source audit: active docs/scripts contain Developer ID-only release
   guidance; every remaining legacy phrase is under an explicit historical or
   isolated-fixture heading.
2. Shell syntax and source evidence tests: validator/build/wrapper guards,
   mutually exclusive modes, no archive/appcast in migration mode, package
   identity checks and ordinary continuity checks.
3. Artifact checks: on the existing `.6` evidence, app/package signatures,
   notarization staple, Gatekeeper and checksums remain verifiable without
   embedding secrets.
4. Repository gates: focused Swift tests, `infra/scripts/ci-local.sh`, then
   `infra/scripts/cd-remote.sh --dry-run`. A later release may use
   `--execute` only after its own release approval and exact-tag evidence.

## Project Structure

### Documentation (this feature)

```text
specs/130-developer-id-release/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── developer-id-release.md
│   └── migration-bootstrap.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── infrastructure.md
└── tasks.md
```

### Source Code (repository root)

```text
AGENTS.md
docs/agent-guidance/release-and-validation.md
docs/current-product-status.md
docs/spec-kit-feature-index.md
docs/releases/v2026.07.26.6.md
docs/deployments/2brain-rec/release-v2026.07.26.6.md
qa/macos/release-candidate-checklist.md
apps/macos/Installer/README.md
apps/macos/Installer/Scripts/build-local-installer.sh
apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh
apps/macos/Installer/Scripts/validate-manual-update-bootstrap.sh
apps/macos/Scripts/validate-app-updates.sh
apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift
specs/095-macos-permission-retention/
specs/105-macos-app-updates/
specs/109-release-signing-key-custody/
```

**Structure Decision**: Keep the existing shell-first macOS release flow and
its shared update validator. Documentation changes are limited to active
operator surfaces and release evidence; historical facts are not rewritten.

## Complexity Tracking

No constitution violations. No new dependency, service, abstraction layer or
parallel release channel is introduced.
