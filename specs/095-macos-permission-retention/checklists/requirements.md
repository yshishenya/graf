# Specification Quality Checklist: macOS Permission Retention

> Historical requirements checklist. Local signing is fixture scope only;
> current public macOS release acceptance is Developer ID-only in Feature 130.

**Purpose**: Validate specification completeness and quality before
implementation.
**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation-only detail is required in user stories beyond
  user-visible signing, permission, and termination behavior.
- [x] User value is clear: avoid repeated macOS permission grants and avoid
  quit/relaunch dead ends.
- [x] Requirements are written for product and engineering readers.
- [x] Mandatory sections are complete.

## Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain.
- [x] Requirements cover stable bundle id, stable signature, permission
  retention, signing drift, local self-signed limitations, and public release
  boundaries.
- [x] Requirements cover modal dismissal and app termination reply behavior.
- [x] Requirements cover metadata-only evidence and forbidden content.
- [x] Requirements explicitly keep the HAL driver out of this slice.

## Scenario Coverage

- [x] Reinstall with stable local identity is covered.
- [x] Reinstall after ad-hoc or signing identity drift is covered.
- [x] Missing, denied, restricted, and granted permission states are covered.
- [x] Permission onboarding visible during quit is covered.
- [x] Already-granted launch and quit paths are covered.
- [x] Public release/notarization is bounded out of scope.

## Measurability

- [x] Success criteria include two reinstall cycles on the same Mac.
- [x] Success criteria include non-ad-hoc signature and stable designated
  requirement evidence.
- [x] Success criteria include a 10-second termination reply bound.
- [x] Success criteria include focused Swift tests and full local CI before
  closeout.

## Notes

Initial checklist pass complete. The remaining risk is implementation evidence:
local self-signed packaging support must be formalized in the build script or
documented as blocked before any permission-retention acceptance claim.
