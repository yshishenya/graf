# Data Compatibility Requirements Checklist: Remove Legacy Separate Audio Driver

**Purpose**: Validate that legacy-code removal does not make supported recordings or current manifests unreadable
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)

**Note**: This checklist validates requirement quality, not implementation behavior.

## Requirement Completeness

- [x] CHK001 Are current recording manifest, upload-queue scan, current recording root, and legacy recording root compatibility requirements all identified? [Completeness, Data Model §Retained current entities]
- [x] CHK002 Are removed optional JSON object keys distinguished from enum raw values whose removal could fail whole-object decoding? [Completeness, Data Model §Compatibility decisions]
- [x] CHK003 Are non-driver compatibility values such as `legacy_recorder_fallback` and `legacyNotReady` explicitly retained? [Completeness, Data Model §Compatibility decisions]

## Requirement Clarity and Consistency

- [x] CHK004 Is the assumption that driver-specific route metadata is unsupported backed by repository contract evidence and a stop condition if contrary evidence appears? [Assumption, Spec §Assumptions]
- [x] CHK005 Is removal of `recordingTimelineEvidence` consistent with retained duration/alignment and track truth? [Consistency, Research §Decision 6]
- [x] CHK006 Is “no migration required” limited to unknown optional keys rather than generalized to unproven enum compatibility? [Clarity, Plan §Storage]

## Acceptance Criteria Quality

- [x] CHK007 Are round-trip criteria defined so new manifests contain no driver/route lifecycle keys while retaining current schema and track contracts? [Measurability, Data Model §LocalRecordingManifest]
- [x] CHK008 Is backward-read acceptance defined with representative current, unknown-key, fallback-value, and legacy-root cases? [Measurability, Quickstart §1]
- [x] CHK009 Can a newly discovered persisted dependency force clarification/analyze instead of silently introducing a compatibility shim? [Governance, Data Model §Compatibility decisions]

## Edge-Case and Data-Safety Coverage

- [x] CHK010 Are queue-scan consequences specified for a manifest that cannot decode, making compatibility regressions observable? [Edge Case, Research §Decision 4]
- [x] CHK011 Are historical fixtures prevented from remaining compiled active contracts solely to preserve deleted behavior? [Consistency, Contract §retirement-boundary]
- [x] CHK012 Are metadata-only and forbidden-content requirements applied to all new compatibility evidence? [Security, Spec §FR-019]

## Notes

- Compatibility requirements distinguish supported recording data from unproven driver-era state.
