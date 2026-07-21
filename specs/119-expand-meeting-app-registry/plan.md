# Implementation Plan: Expanded Meeting App Registry

**Branch**: `119-expand-meeting-app-registry` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/119-expand-meeting-app-registry/spec.md`

## Summary

Expand the released feature 092 meeting-target baseline from 31 targets and 23
native bundle identifiers to at least 40 product families and 50 independently
verified macOS bundle identifiers. Enable every verified native identity for the
same prompt and user-selected auto-record flow as Zoom and Yandex Telemost, and
show them in the existing common scrollable applications list. Record live
AudioHAL/capture-control results as post-enable QA rather than a publication gate.
Publish the expansion through a new server migration and make native identity
matching and validation case-insensitive. Keep the researched browser catalog honest:
the existing five service-family resolvers remain the only implemented metadata
classifiers until a live browser adapter is delivered.

## Technical Context

**Language/Version**: Python 3.13, Swift 6, JSON schema 2020-12.

**Primary Dependencies**: Existing FastAPI/Pydantic/SQLAlchemy/Alembic server,
SwiftUI/AppKit desktop app, Foundation Codable cache. No new dependency.

**Storage**: Existing Postgres meeting-target registry tables and desktop
last-good JSON cache; one immutable migration-owned global registry version.

**Testing**: pytest unit/integration/contract tests, Swift XCTest, migration
upgrade/downgrade tests, JSON/catalog consistency checks, per-target live
validation matrix, full local CI.

**Risk / Validation Lane**: High-risk feature. The allowlist influences meeting
detection and recording eligibility and the slice changes user-facing settings.
Full Spec Kit sequence, capture/privacy/UX checklists, task-to-issue sync, focused
tests, and repository CI are required.

**Release Gate**: No commit, push, PR, release, registry production publication,
or deploy in this lane without the separate approval gates.

**Target Platform**: Apple Silicon macOS desktop plus Linux server containers.
Windows, Linux, iOS, and Android identities are research-only and not claimed as
supported.

**Project Type**: Cross-module desktop/server registry expansion.

**Performance Goals**: Registry lookup remains linear over fewer than 150 rows;
settings opens without blocking network work; no new detector process, polling,
or steady-state resource cost.

**Constraints**: Package/source identity evidence may enable a native target, but
auto-record still requires explicit user selection and existing prerequisite,
visible-state, policy, and Stop gates. Unknown apps and generic browser audio
remain fail-closed; no meeting content, raw URLs, logs, or credentials enter the
catalog, diagnostics, fixtures, or cache.

**Scale/Scope**: At least 50 distinct case-insensitive macOS bundle IDs across at
least 40 target families, all 31 released targets accounted for, with Telegram
for macOS, Telegram Desktop and shared-ID derivatives, Telegram A, AyuGram, and
Kotatogram explicitly classified.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0: PASS.**

- Capture-first integrity: no capture implementation or routing changes. New
  identities reuse the existing target-scoped prompt/recording policy.
- Visible consent/control: manual Record and one-action Stop are unchanged;
  all verified identities are eligible, while auto-record remains disabled until
  the user selects targets or presses “Выбрать все”.
- Data/secret boundary: public package identity and bounded family labels only;
  no app inventory upload, meeting content, or new egress.
- Deletion lifecycle: registry metadata is operational configuration and adds no
  meeting-content artifact or deletion promise.
- Spec-driven delivery: high-risk sequence and issue sync are mandatory before
  implementation.
- UI/accessibility: use one existing native applications list, scroll semantics,
  textual live-validation status, keyboard and VoiceOver labels; no engineering
  “diagnostic” section and no borrowed product UI.
- Ponytail: reuse the registry, migration, cache, validator, and settings view;
  add no new service, framework, scanner, or dependency.

**After Phase 1: PASS.** The data model documents aliases without changing the
runtime schema, the migration affects only the global baseline, validation
rejects duplicate case-folded identities on both server and client, and the UI
keeps every verified native target in one list. Package/source identity controls
initial prompt eligibility; live evidence is post-enable QA.

## Validation Plan

- Validate catalog/registry counts, released-target preservation, evidence
  source presence, aliases, evidence-backed prompt targets, and case-folded uniqueness.
- Record per-target live start/end and false-positive results in
  [live-validation.md](./live-validation.md); correct or disable failed targets.
- Run server registry unit tests and migration upgrade/downgrade tests, including
  workspace-registry precedence and previous-global restoration.
- Run macOS registry, policy, settings accessibility/source-contract, and cache
  fallback tests.
- Execute scenarios in [quickstart.md](./quickstart.md), including Telegram
  shared-ID resolution and generic-browser fail-closed behavior.
- Run `infra/scripts/ci-local.sh` before implementation closeout.
- No deployment dry-run or execute command in this feature lane.

## Project Structure

### Documentation (this feature)

```text
specs/119-expand-meeting-app-registry/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── target-catalog.md
├── live-validation.md
├── quickstart.md
├── contracts/
│   └── registry-expansion.md
├── checklists/
│   ├── requirements.md
│   ├── capture-privacy.md
│   └── settings-ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/meeting_detection/registry.py
apps/server/src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json
apps/server/src/twobrain_rec_server/db/migrations/versions/0030_expand_meeting_target_registry.py
apps/server/tests/unit/test_meeting_detection_registry.py
apps/server/tests/integration/test_meeting_detection_migrations.py

apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift
apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift
apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift

specs/092-automatic-meeting-detection/contracts/meeting-target-registry.schema.json
docs/current-product-status.md
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Extend the existing feature 092 registry contract and
consumer instead of creating a parallel allowlist. The research catalog remains
the evidence/audit surface; the migration JSON is the bounded runtime subset.

## Complexity Tracking

No constitution violations or new architectural components.
