# Packaging and Host Safety Requirements Checklist: Remove Legacy Separate Audio Driver

**Purpose**: Validate app-only packaging and the boundary between repository cleanup and privileged host cleanup
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are build, package, distribution choice, install, update, repair, rollback, uninstall, and postinstall surfaces all covered by the removal requirement? [Completeness, Spec §FR-006]
- [x] CHK002 Is the supported app-only installer/uninstaller behavior specified independently from legacy HAL cleanup? [Completeness, Research §Decision 7]
- [x] CHK003 Are package-content requirements explicit about component count, HAL payload absence, scripts, and service-restart absence? [Completeness, Spec §SC-005, Quickstart §4]

## Requirement Clarity and Consistency

- [x] CHK004 Is “optional driver component” explicitly disallowed rather than merely default-disabled? [Clarity, Contract §retirement-boundary]
- [x] CHK005 Are no-deploy, no-install, no-uninstall, and no-privileged-restart constraints consistent across spec, plan, quickstart, and cleanup contract? [Consistency, Spec §SC-009]
- [x] CHK006 Is responsibility for an already installed proof component clearly separated from normal release/update behavior? [Clarity, Spec §FR-016]

## Acceptance Criteria Quality

- [x] CHK007 Can the “one desktop app component, zero driver components” criterion be objectively evaluated from a built distribution? [Measurability, Spec §SC-005]
- [x] CHK008 Is the absence of hidden privileged mutation measurable for every documented validation command? [Measurability, Spec §SC-009]
- [x] CHK009 Is the local proof cleanup scope narrow enough to reject unknown bundles, lookalikes, symlinks, and broad HAL-directory deletion? [Security, Contract §local-proof-cleanup]

## Recovery and Edge-Case Coverage

- [x] CHK010 Are requirements defined for hosts with no proof component and hosts with a confirmed historical component? [Coverage, Spec §User Story 4]
- [x] CHK011 Are active call/recording disruption and audio-service restart treated as deliberate operator concerns rather than installer side effects? [Recovery, Contract §local-proof-cleanup]
- [x] CHK012 Is preservation of app data, Application Support, and both current/legacy recording roots specified during any separate cleanup? [Data Safety, Contract §local-proof-cleanup]

## Notes

- Packaging and host-state requirements are complete; implementation remains non-privileged.
