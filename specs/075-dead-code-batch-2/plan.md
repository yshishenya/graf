# Implementation Plan: Dead Code Batch 2

**Branch**: `codex/075-dead-code-batch-2` | **Date**: 2026-07-01 |
**Spec**: [spec.md](./spec.md)

## Summary

Delete two Swift helpers with direct zero-reference evidence:
`DesktopMeetingShellView.statusChip` and `LivePassthroughPolicyTests.waitUntil`.
No split, no abstraction, no behavior change.

## Technical Context

**Language/Version**: Swift macOS app/test code

**Primary Dependencies**: Existing SwiftPM/Xcode dependencies only

**Storage**: N/A

**Testing**: Focused SwiftPM/Xcode validation for touched targets plus repo diff
checks

**Risk / Validation Lane**: Significant cleanup, because desktop visible-state
code is product-sensitive even when deletion is small.

**Release Gate**: No deploy.

**Target Platform**: macOS desktop app

**Project Type**: Swift macOS app and tests

**Constraints**: deletion-only, net Swift LOC negative, no dependencies, no
production deploy

## Constitution Check

- Capture-first integrity: PASS. Do not change capture behavior.
- Visible consent and user control: PASS. Do not change recording indicator or
  stop paths.
- Data boundary and deletion truth: PASS. Not touched.
- Spec-driven delivery: PASS. Compact Spec Kit slice with tasks and validation.

## Validation Plan

1. Confirm zero matches after deletion.
2. Run focused Swift validation for touched package/tests.
3. Run `git diff --check`.
4. Run `infra/scripts/ci-local.sh` if the repo gate is required by closeout.

## Project Structure

```text
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift
specs/075-dead-code-batch-2/
```

**Structure Decision**: No new runtime structure.
