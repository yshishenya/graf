# Implementation Plan: Безопасный запуск macOS после обновления

**Branch**: `codex/232-macos-resource-bundle-hotfix` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/232-macos-resource-bundle-hotfix/spec.md`

## Summary

Исправить общий resolver встроенного meeting-target registry: в готовом
`GRAF.app` читать SwiftPM resource bundle из `Bundle.main.resourceURL`, а
`Bundle.module` оставлять только для development/test запуска. Отсутствующий
ресурс должен давать `nil`, чтобы существующий registry store мог использовать
cache/remote/degraded path без `fatalError`. Перед созданием appcast добавить
один fail-closed smoke, запускающий точный бинарник извлечённого candidate app.

## Technical Context

**Language/Version**: Swift 6.0; POSIX shell (`/bin/sh`)

**Primary Dependencies**: Foundation, SwiftPM resources, XCTest, Sparkle 2.9.4, native macOS signing/notarization tools

**Storage**: Existing local Application Support registry cache only; no schema or data change

**Testing**: Swift XCTest plus shell self-test fixtures and a real packaged-app launch smoke

**Risk / Validation Lane**: `release-deploy` with high-risk macOS startup and capture-adjacent behavior; the broken public update blocks the whole app and the fixed artifact must pass public Developer ID gates

**Release Gate**: `cd-remote.sh --dry-run` is required for exact-SHA release evidence; backend `--execute` is not required because no server runtime changes. Public macOS publication requires Developer ID, notarization, stapling, Gatekeeper, Sparkle continuity and appcast-last publication.

**Target Platform**: macOS 14.5+, universal arm64/x86_64 public app

**Project Type**: Native macOS desktop application and release tooling

**Performance Goals**: Candidate stays alive for at least five seconds in each smoke; ten consecutive production-like launches without startup crash

**Constraints**: Minimal shared resolver fix; no capture-policy, registry-content, backend, UI or data changes; no new dependency; smoke must own and terminate only its direct child; evidence metadata-only

**Scale/Scope**: One Swift resolver, one release smoke script, its bounded fixtures, one signing workflow hook and release metadata

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I Capture-first integrity**: PASS. The change does not alter audio capture,
  routing, permissions or recording state. Missing registry data degrades meeting
  detection instead of falling back to removed audio routing.
- **II Visible consent/control**: PASS. Three-state auto-recording, prompt,
  visible indicator and Record/Stop remain unchanged; focused regressions prove
  the resolver change does not bypass their gates.
- **V Public macOS integrity**: PASS WITH RELEASE GATE. Only Developer ID signed,
  notarized, stapled and Gatekeeper-accepted ZIP/PKG may be published; Sparkle
  continuity and appcast-last are mandatory.
- **VI Spec-driven delivery**: PASS. Full clarify, reviewer checklist, tasks,
  analyze, issue sync, implementation, converge and exact-SHA release evidence
  are required.
- **Secrets/evidence**: PASS. Tests use loopback and temporary homes; committed
  and release evidence remains metadata-only.

Post-design re-check: PASS. No new dependency, storage model, privileged
boundary or capture behavior is introduced. The startup smoke strengthens the
existing public release boundary and cannot publish anything itself.

## Validation Plan

1. RED/green XCTest for packaged-resource lookup and missing-resource nil.
2. Shell self-test for a living direct child, immediate exit and isolation from
   an unrelated process.
3. Production-like universal build, resource-layout inspection, ten arm64
   launches, x86_64/Rosetta launch where available, and missing-resource launch.
4. Feature [quickstart.md](quickstart.md), then
   `infra/scripts/ci-local.sh --fast` before PR.
5. Moving-master/exact-SHA PR and release guards. Prepare `2026.09.02.2`, freeze
   the merged release candidate and run exactly one authoritative
   `infra/scripts/ci-local.sh --full` bound to it.
6. `infra/scripts/cd-remote.sh --dry-run --branch master`; no backend execute.
7. Build/sign/notarize/staple/re-ZIP, validate Gatekeeper, manual repair over
   `.1`, Sparkle update from the confirmed healthy predecessor, and public
   redownload/hash/signature/startup checks. Publish appcast last.

## Project Structure

### Documentation (this feature)

```text
specs/232-macos-resource-bundle-hotfix/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
apps/macos/
├── RecApp/Sources/MeetingDetection/MeetingDetectionAppModule.swift
├── Shared/Tests/MeetingTargetRegistryTests.swift
├── Scripts/validate-packaged-app-launch.sh
└── Installer/Scripts/
    ├── sign-graf-app-update-local.sh
    └── test-packaged-app-launch.sh

tests/governance/
├── test_dev_runtime.py
└── test_release_candidate.py

infra/scripts/
└── ci-local.sh

changes/unreleased/
└── F232.yaml
```

**Structure Decision**: Reuse the existing Swift package, XCTest target and
release-signing scripts. Add no module, service, dependency or generic process
framework; the smoke is one standalone native shell gate.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | No constitution violation | Existing modules and native tooling are sufficient |
