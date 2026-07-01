# Implementation Plan: Dead Code Batch 5

**Branch**: `codex/078-dead-code-batch-5` | **Date**: 2026-07-01 |
**Spec**: [spec.md](./spec.md)

## Summary

Remove a smaller, compile-proven set of unused `Foundation` imports from shared
macOS buffering and routing source files. Do not split files, add tooling,
rewrite APIs, alter runtime behavior, or deploy.

## Technical Context

**Language/Version**: Swift macOS app/shared package

**Primary Dependencies**: Existing SwiftPM dependencies only

**Storage**: N/A

**Testing**: SwiftPM build, focused Swift tests, repository closeout gate

**Risk / Validation Lane**: Active Spec Kit slice / high-risk-adjacent cleanup.
The intended source diff is import-only, but touched files are shared by desktop
buffering, latency, and low-resource route-truth behavior.

**Release Gate**: No deploy.

**Target Platform**: macOS desktop app and shared Swift package

**Project Type**: Swift macOS app/shared package

**Performance Goals**: No runtime behavior change; tracked Swift source surface
is smaller.

**Constraints**: import-only, negative Swift LOC, no dependency/tooling changes,
no behavior change, no release or production deploy

**Scale/Scope**: One small cleanup batch; broader dead-code deletion, import
narrowing, large-file splitting, and runtime refactors are out of scope.

## Constitution Check

- Capture-first integrity: PASS. The candidate files are capture-adjacent, so
  focused validation must cover buffering, latency, and route-truth behavior.
- Visible consent and user control: PASS. No capture UI/control behavior
  changes.
- Data boundary and secret discipline: PASS. No data egress, secrets, or
  diagnostic payload changes.
- Deletion truth and lifecycle accounting: PASS. Not touched.
- Spec-driven delivery: PASS. Full Spec Kit slice with checklist, tasks,
  analyze, issue tracking, and closeout validation.

## Validation Plan

1. Record scanner evidence and candidate classification in
   `audit-candidates.md`.
2. Compile after removing selected imports with `swift build --package-path
   apps/macos`.
3. Run focused Swift validation for touched surfaces:
   `LatencyGateTests|LowResourceRouteTruthTests|LowResourceRouteLifecycleTests|DesktopUploadQueueTests|RecordingPrerequisiteGateTests`.
4. Run `git diff --check`, Spec Kit prerequisites, GitHub issue canon, and
   `infra/scripts/ci-local.sh`.

## Project Structure

```text
apps/macos/Shared/Sources/Buffering/LocalBufferContracts.swift
apps/macos/Shared/Sources/Routing/LatencyMonitor.swift
apps/macos/Shared/Sources/Routing/LowResourceRouteTruth.swift
specs/078-dead-code-batch-5/
```

**Structure Decision**: No new runtime structure.

## Complexity Tracking

No constitution violations and no new complexity.
