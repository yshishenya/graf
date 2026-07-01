# Implementation Plan: Dead Code Batch 3

**Branch**: `codex/076-dead-code-batch-3` | **Date**: 2026-07-01 |
**Spec**: [spec.md](./spec.md)

## Summary

Remove three compiler-proved unused imports from macOS Swift source:

- `BluetoothRouteMonitor.swift`: `Foundation`
- `VolumeMuteMapper.swift`: `Foundation`
- `CaptureControlView.swift`: `AppKit`

No split, no abstraction, no product behavior change.

## Technical Context

**Language/Version**: Swift macOS app source

**Primary Dependencies**: Existing SwiftPM dependencies only

**Storage**: N/A

**Testing**: SwiftPM build, focused Swift tests, repository closeout gate

**Risk / Validation Lane**: Significant cleanup / active Spec Kit slice. The
code touched is small, but it sits in macOS capture/audio UI surfaces.

**Release Gate**: No deploy.

**Target Platform**: macOS desktop app

**Project Type**: Swift macOS app and shared package

**Constraints**: import-only, negative Swift LOC, no new dependencies, no
production deploy

## Constitution Check

- Capture-first integrity: PASS. Import deletion must not change capture
  behavior.
- Visible consent and user control: PASS. Capture UI remains behaviorally
  unchanged.
- Data boundary and secret discipline: PASS. No data egress, secrets, or
  diagnostics touched.
- Deletion truth and lifecycle accounting: PASS. Not touched.
- Spec-driven delivery: PASS. Compact Spec Kit slice with checklist, tasks,
  analyze, issue tracking, and closeout validation.

## Validation Plan

1. Record scanner evidence: zero-reference helper/type scans do not produce a
   safer larger deletion target.
2. Compile after removing candidate imports with `swift build --package-path
   apps/macos`.
3. Run focused Swift validation for touched surfaces.
4. Run `git diff --check` and `infra/scripts/ci-local.sh`.

## Project Structure

```text
apps/macos/RecApp/Sources/AudioHealth/BluetoothRouteMonitor.swift
apps/macos/RecApp/Sources/AudioSetup/VolumeMuteMapper.swift
apps/macos/RecApp/Sources/Capture/CaptureControlView.swift
specs/076-dead-code-batch-3/
```

**Structure Decision**: No new runtime structure.
