# Recovery Requirements Checklist: macOS Real Bidirectional Passthrough

**Purpose**: Validate failure, stale-state, and installer/runtime recovery requirement quality
**Created**: 2026-05-31
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is app heartbeat loss required to fail closed within 5 seconds? [Completeness, Spec §FR-008]
- [x] CHK002 Is `coreaudiod` restart required to mark passthrough stale before recovery? [Completeness, Spec §SC-006]
- [x] CHK003 Are physical device changes required to invalidate live passthrough? [Completeness, Spec §FR-009]
- [x] CHK004 Are browser target device changes required to invalidate live passthrough? [Completeness, Spec §FR-009]

## Requirement Clarity

- [x] CHK005 Is recovery defined as heartbeat plus route revalidation, not app relaunch alone? [Clarity, Spec §SC-005]
- [x] CHK006 Are stale, degraded, failed, and blocked statuses modeled separately? [Clarity, Data Model]
- [x] CHK007 Are recovery actions user-facing and actionable? [Clarity, Spec §FR-017]

## Scenario Coverage

- [x] CHK008 Are app quit/crash during browser use and stale device IDs covered? [Coverage, Edge Cases]
- [x] CHK009 Is backend/network outage non-interference covered? [Coverage, Spec §FR-013]
- [x] CHK010 Is installer/runtime probe validation included in quickstart? [Coverage, Quickstart]
