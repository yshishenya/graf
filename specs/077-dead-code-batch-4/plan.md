# Implementation Plan: Dead Code Batch 4

**Branch**: `codex/077-dead-code-batch-4` | **Date**: 2026-07-01 |
**Spec**: [spec.md](./spec.md)

## Summary

Remove a small set of compiler-proved unused `Foundation` imports from macOS
Swift audio, capture, and shared model files. No split, no abstraction, no
product behavior change, and no new tooling.

## Technical Context

**Language/Version**: Swift macOS app/shared package

**Primary Dependencies**: Existing SwiftPM dependencies only

**Storage**: N/A

**Testing**: SwiftPM build, focused Swift tests, repository closeout gate

**Risk / Validation Lane**: Active Spec Kit slice / high-risk-adjacent cleanup.
The source diff is import-only, but touched files sit near macOS audio, capture,
route, and shared model surfaces.

**Release Gate**: No deploy.

**Target Platform**: macOS desktop app and shared Swift package

**Project Type**: Swift macOS app/shared package

**Performance Goals**: No runtime behavior change; compile surface is smaller.

**Constraints**: import-only, negative Swift LOC, no dependency/tooling changes,
no release or production deploy

**Scale/Scope**: One small cleanup batch; broader architecture splits are out of
scope.

## Constitution Check

- Capture-first integrity: PASS. Import deletion must not change capture,
  route, recording, or permission behavior.
- Visible consent and user control: PASS. No active-capture UI/control behavior
  changes.
- Data boundary and secret discipline: PASS. No data egress, secrets, or
  diagnostics payloads touched.
- Deletion truth and lifecycle accounting: PASS. Not touched.
- Spec-driven delivery: PASS. Compact Spec Kit slice with checklist, tasks,
  analyze, issue tracking, and closeout validation.

## Validation Plan

1. Record scanner evidence and compile-probe classification in
   `audit-candidates.md`.
2. Compile after removing candidate imports with `swift build --package-path
   apps/macos`.
3. Run focused Swift validation for touched surfaces:
   `BluetoothRoutePolicyTests|GuidedDeviceManagementTests|RecordingPrerequisiteGateTests|RecordingRouteMetadataTests|LiveRouteClientActivityTests|RecordingTimelineEvidenceTests|SystemAudioAccessibilityTests|SystemAudioResponsiveStateTests`.
4. Run `git diff --check`, Spec Kit prerequisites, GitHub issue canon, and
   `infra/scripts/ci-local.sh`.

## Project Structure

```text
apps/macos/RecApp/Sources/AudioHealth/BluetoothRoutePolicy.swift
apps/macos/RecApp/Sources/AudioSetup/GuidedDeviceManagementService.swift
apps/macos/RecApp/Sources/AudioSetup/PhysicalDeviceSelectionViewModel.swift
apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift
apps/macos/RecApp/Sources/Capture/RecordingRouteMetadataService.swift
apps/macos/Shared/Sources/Models/AudioStates.swift
apps/macos/Shared/Sources/Models/RecordingTimelineEvidence.swift
apps/macos/Shared/Sources/Routing/LiveRouteClientActivity.swift
specs/077-dead-code-batch-4/
```

**Structure Decision**: No new runtime structure.

## Complexity Tracking

No constitution violations and no new complexity.
