# Validation Checklist: Live Route Stability

**Purpose**: Validate long-duration acceptance and validation-matrix requirement quality before task generation.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and planning artifacts, not implementation behavior.

## Duration Gates

- [x] CHK001 Are 30-minute development and 75-minute release gates specified as separate acceptance windows with separate evidence? [Completeness, Spec §SC-001, Quickstart §Development Gate, Quickstart §Release Gate]
- [x] CHK002 Are requirements clear that short smoke validation is insufficient for `019` acceptance? [Clarity, Spec §FR-021]
- [x] CHK003 Are accepted-run criteria measurable for no recurring `Run Check`, zero unexpected release, fresh evidence, and route audibility/speakability? [Measurability, Spec §SC-001, Spec §SC-002, Contract §Validation Run Evidence]

## Target And Device Matrix

- [x] CHK004 Are Chrome, Opera, Zoom, and Telemost each required to have accepted evidence for both duration gates? [Completeness, Spec §SC-012a]
- [x] CHK005 Are built-in, wired, and USB device-class acceptance requirements complete without requiring the full `4 x 3` cross-product? [Clarity, Spec §FR-051, Spec §SC-019]
- [x] CHK006 Are not-tested target/device-class combinations required to be listed without being claimed release-ready? [Acceptance Criteria, Spec §SC-021, Contract §Validation Run Evidence]
- [x] CHK007 Are blocked, failed, degraded, and not-tested outcomes distinguished from accepted outcomes clearly enough for release notes? [Clarity, Spec §FR-025, Contract §Validation Run Evidence]
- [x] CHK008 Are Bluetooth/AirPods-class requirements consistently represented as backlog/not accepted for `019` validation? [Consistency, Spec §FR-042, Spec §FR-043, Quickstart §Release Gate]

## Autorepair Validation

- [x] CHK009 Are validation requirements complete for `coreaudiod` restart, sleep/wake, temporary physical-device disappearance/return, browser stream recreation, and app-side route engine restart? [Coverage, Spec §FR-031, Quickstart §Autorepair Scenarios]
- [x] CHK010 Are macOS default route-change validation requirements complete for user-initiated changes to accepted built-in, wired, or USB routes? [Coverage, Spec §FR-050, Spec §SC-025]
- [x] CHK011 Are non-recoverable validation requirements complete for missing permissions, missing accepted devices, meeting target changes, unsupported default routes, and refused stream reopen? [Coverage, Contract §Autorepair, Quickstart §Non-Recoverable Scenarios]
- [x] CHK012 Are slow-recovery outcomes specified clearly enough to classify `> 10 seconds` as degraded/failed evidence rather than clean acceptance? [Measurability, Spec §FR-048, Contract §Autorepair]

## Evidence Quality

- [x] CHK013 Are validation-run evidence fields sufficient to prove duration gate, target, device class, user actions, route releases, autorepair attempts, timeline integrity, and not-tested combinations? [Completeness, Contract §Validation Run Evidence]
- [x] CHK014 Are quickstart expected outcomes specific enough to support future tasks with exact validation artifacts and commands? [Task Readiness, Quickstart]
- [x] CHK015 Are validation requirements scoped to local live route stability without depending on backend ingest or upload readiness? [Scope, Spec §FR-013, Plan §Storage]
