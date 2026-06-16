# Audio Capture Requirements Checklist: Meeting-App Mute Truth

**Purpose**: Validate local microphone suppression, timeline truth, target matrix, artifact status, and capture-boundary requirement quality before implementation.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirement quality only. It does not verify implementation behavior.

## Requirement Completeness

- [x] CHK001 Are requirements complete for local microphone treatment during `2brain Pause`, including silence/redaction and metadata-only segment evidence? [Completeness, Spec §FR-002, Contract §Product Privacy Control]
- [x] CHK002 Are requirements complete for preserving dual-track artifact truth while adding optional mute-truth manifest fields? [Completeness, Contract §Mute-Truth Manifest, Plan §Storage]
- [x] CHK003 Are target matrix requirements complete for Zoom native, Chrome/Telemost, Opera/Telemost, Yandex Browser, and unknown targets? [Completeness, Spec §FR-006, Contract §Target Matrix]
- [x] CHK004 Are requirements complete for preserving existing visible recording, one-action Stop, local artifact persistence, role mapping, and metadata-only diagnostics from features 007, 008, and 010? [Completeness, Spec §FR-008-FR-010]

## Requirement Clarity

- [x] CHK005 Is the phrase "silenced/redacted local mic segment" clear enough to guide manifest, writer, and validation tasks without inventing a second artifact format? [Clarity, Research §Pause Writes Silence/Redaction, Data Model §ProductPrivacySegment]
- [x] CHK006 Is the distinction between recording status (`saved`, `degraded`, `blocked`, `failed`) and mute-truth decision (`meeting_mute_unproven`, `unsupported`, `degraded`) clear? [Clarity, Data Model §LocalRecordingManifest Extension]
- [x] CHK007 Are timing requirements for Pause suppression and timeline alignment quantified enough for focused tests? [Clarity, Plan §Performance Goals, Spec §SC-001]

## Requirement Consistency

- [x] CHK008 Are manifest extension requirements consistent with existing `LocalRecordingManifest` and dual-track local artifact contracts? [Consistency, Plan §Primary Dependencies, Contract §Mute-Truth Manifest]
- [x] CHK009 Are target support claims consistent between spec, data model, contracts, and quickstart without allowing target names to imply adapter support? [Consistency, Spec §FR-006, Data Model §TargetMuteCapability]
- [x] CHK010 Are Pause/Resume/Stop transitions consistent with the existing capture-state model and visible indicator rules? [Consistency, Contract §Product Privacy Control, Spec §FR-008]

## Scenario Coverage

- [x] CHK011 Are requirements defined for active recording -> pause -> resume -> stop and pause -> stop flows? [Coverage, Contract §Product Privacy Control]
- [x] CHK012 Are requirements defined for the alternate path where the user relies only on third-party meeting-app mute? [Coverage, Spec §US1 Acceptance Scenario 3]
- [x] CHK013 Are requirements defined for unsupported/deferred targets so release validation cannot silently pass them as mute-respecting? [Coverage, Spec §US2, Contract §Target Matrix]
- [x] CHK014 Are requirements defined for hardware mute, macOS input mute, stale evidence, contradictory evidence, and route ambiguity? [Coverage, Spec §Edge Cases]

## Acceptance Criteria Quality

- [x] CHK015 Can local microphone suppression during `2brain Pause` be objectively validated from artifact metadata and focused tests? [Measurability, Spec §SC-001, Quickstart §4]
- [x] CHK016 Can unsupported target outcomes be objectively validated without inspecting raw audio or private meeting content? [Measurability, Spec §SC-002, Quickstart §5]
- [x] CHK017 Are regression gates for features 007, 008, and 010 explicitly represented in validation requirements? [Traceability, Spec §SC-003, Quickstart §6]

## Notes

- All generated audio-capture requirement checks pass for the clarified 2026-06-16 spec and plan artifacts.
