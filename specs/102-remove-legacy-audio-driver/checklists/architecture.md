# Architecture Requirements Checklist: Remove Legacy Separate Audio Driver

**Purpose**: Validate that the retirement boundary is complete, unambiguous, and reviewable before implementation
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are all executable legacy layers named across source, package graph, runtime orchestration, UI, diagnostics, installer, validation, tests, QA, and active documentation? [Completeness, Spec §FR-001–FR-008]
- [x] CHK002 Is the supported current-capture keep boundary defined separately from generic Core Audio terminology so broad deletion cannot remove valid code? [Completeness, Spec §FR-009–FR-012]
- [x] CHK003 Are historical evidence, active documentation, and executable source classified as distinct surfaces with different retention rules? [Completeness, Spec §FR-013–FR-015]

## Requirement Clarity and Consistency

- [x] CHK004 Is “remove” clarified to reject rename-only, disabled-toggle, dormant fallback, or optional-package interpretations? [Clarity, Contract §retirement-boundary]
- [x] CHK005 Are the no-replacement and no-new-dependency constraints consistent with the planned adaptations of mixed current files? [Consistency, Spec §FR-017, Plan §Summary]
- [x] CHK006 Is the future-architecture boundary consistent between the active docs requirement and retained historical audit evidence? [Consistency, Spec §FR-014–FR-015]

## Acceptance Criteria Quality

- [x] CHK007 Can “zero unexplained active references” be objectively evaluated using a defined active-root scope and explicit allowlist? [Measurability, Spec §SC-003, Contract §retirement-boundary]
- [x] CHK008 Is the requirement that deletion exceed additions measurable without treating required Spec Kit documentation as executable production code? [Clarity, Spec §SC-007]
- [x] CHK009 Are active-document truth criteria specific enough to distinguish historical mention from a claim that legacy code remains parked or recoverable? [Measurability, Spec §SC-008]

## Scenario and Edge-Case Coverage

- [x] CHK010 Are mixed files/types with both current and driver-era callers covered by an explicit dependency-driven decision rule? [Coverage, Spec §FR-020]
- [x] CHK011 Are unrelated uses of “driver”, “route”, “virtual”, and Core Audio explicitly excluded from blind pattern deletion? [Edge Case, Spec §Edge Cases]
- [x] CHK012 Is generated/ignored build output distinguished from tracked active source for the retirement inventory? [Edge Case, Spec §Edge Cases]

## Notes

- All architecture requirement-quality items are resolved in the spec, research, and retirement contract.
