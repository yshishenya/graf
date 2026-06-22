# Security And Privacy Requirements Checklist: WebRTC AEC3 Speakerphone Spike

**Purpose**: Validate metadata safety, diagnostics, licensing, dependency, and privacy requirements before task generation.
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the written requirements and plan artifacts, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are forbidden evidence classes explicitly listed for diagnostics, committed evidence, issue comments, PR text, and release notes? [Completeness, Spec §FR-013b, Spec §FR-015, Plan §Constraints]
- [x] CHK002 Are allowed diagnostic fields bounded to metadata, status fields, reason codes, counters, threshold summaries, and readiness states? [Completeness, Contract §Diagnostics And Evidence Safety]
- [x] CHK003 Are raw audio, debug WAVs, transcripts, meeting content, participant names, signed URLs, credentials, tokens, object keys, secret paths, and private local paths explicitly forbidden? [Completeness, Contract §Forbidden Diagnostic Fields]
- [x] CHK004 Are WebRTC license, patent grant, redistribution, packaging, signing, notarization, binary-size, and release-readiness checks represented before promotion? [Completeness, Spec §FR-016, Research §License And Packaging Review Blocks Promotion]
- [x] CHK005 Are runtime private captures, if manually used, explicitly excluded from committed artifacts and public workflow text? [Completeness, Contract §Redaction Rules]
- [x] CHK006 Are app statuses required to avoid private meeting content and unnecessary technical internals? [Completeness, Spec §FR-013b, Contract §App Recording Status]

## Requirement Clarity

- [x] CHK007 Is "metadata-only" defined through allowed and forbidden field classes rather than left as a broad label? [Clarity, Contract §Allowed Diagnostic Fields, Contract §Forbidden Diagnostic Fields]
- [x] CHK008 Is a diagnostics row that cannot be safely redacted required to become blocked? [Clarity, Contract §Redaction Rules]
- [x] CHK009 Is diagnostic usefulness after redaction required so privacy does not erase all review value? [Clarity, Contract §Redaction Rules]
- [x] CHK010 Are failure reasons required to be bounded reason codes instead of raw logs or private traces? [Clarity, Spec §SC-005, Contract §Diagnostics And Evidence Safety]
- [x] CHK011 Is dependency readiness described as a release gate with repo-specific evidence rather than a general claim about WebRTC? [Clarity, Plan §Primary Dependencies, Research §License And Packaging Review Blocks Promotion]

## Requirement Consistency

- [x] CHK012 Do privacy requirements align across spec, diagnostics contract, app-status contract, research, quickstart, and plan constraints? [Consistency, Spec §FR-015, Contract §Diagnostics, Quickstart §Out Of Scope]
- [x] CHK013 Do app status privacy rules align with diagnostic privacy rules, including no raw content and no private local paths? [Consistency, Spec §FR-013b, Contract §App Recording Status, Contract §Diagnostics]
- [x] CHK014 Do controlled real-hardware validation assumptions use consented test content or synthetic fixtures consistently across spec, data model, and quickstart? [Consistency, Spec §Assumptions, Data Model §ControlledRealHardwareRecordingEvidence, Quickstart §Controlled Real-Hardware App Recording Matrix]
- [x] CHK015 Do rollback and blocked states remain metadata-only even after unsafe runtime conditions? [Consistency, Spec §FR-006e, Data Model §AEC3RollbackEvent, Contract §Diagnostics]

## Acceptance Criteria Quality

- [x] CHK016 Are privacy success criteria measurable with zero forbidden-content tolerance for diagnostics and committed evidence? [Measurability, Spec §SC-004, Spec §SC-010]
- [x] CHK017 Are user-facing/release-facing copy constraints measurable with zero clean-recording overclaim tolerance? [Measurability, Spec §SC-006, Spec §SC-011]
- [x] CHK018 Are unsafe diagnostics represented as a promotion blocker rather than only a post-hoc audit concern? [Measurability, Spec §FR-014, Contract §Failure Rules]
- [x] CHK019 Are acceptance-threshold summaries required to remain bounded and content-free? [Measurability, Spec §FR-012a, Contract §Required Result Fields]

## Edge Case Coverage

- [x] CHK020 Are private-content leakage risks covered for evidence files, diagnostics, app statuses, issue comments, PR descriptions, release notes, and runtime-only manual captures? [Coverage, Spec §FR-015, Contract §Redaction Rules]
- [x] CHK021 Are dependency blockers covered for incomplete license, patent, packaging, signing, notarization, and release review? [Coverage, Spec §Edge Cases, Spec §FR-016]
- [x] CHK022 Are app status states prevented from revealing route internals beyond what a user needs to understand the recording state? [Coverage, Spec §FR-013b, Contract §Copy Rules]
- [x] CHK023 Are unbounded platform or WebRTC logs forbidden when they may contain device-owner or system-private content? [Coverage, Contract §Forbidden Diagnostic Fields]

## Dependencies & Assumptions

- [x] CHK024 Are owner-controlled infrastructure and desktop egress constraints preserved by keeping AEC3 validation local and metadata-only? [Dependency, Constitution §III, Plan §Constitution Check]
- [x] CHK025 Are downstream transcription and MediaScribe boundaries protected by requiring package-readiness gates before candidate promotion? [Dependency, Spec §FR-008, Contract §Recording Package Lineage]
- [x] CHK026 Are release and packaging assumptions tied to evidence rather than broad external best-practice claims? [Dependency, Research §Primary Sources And Local Evidence]

## Notes

- 2026-06-22: Passed with metadata-only diagnostics, bounded threshold summaries, and dependency readiness as blockers.
