# Security and Lifecycle Requirements Checklist: Чистый единый аудиопоток

**Purpose**: Validate privacy, egress, immutable revision, retention, deletion and rollback requirements before implementation.

**Created**: 2026-07-17

**Feature**: [spec.md](../spec.md) · [data model](../data-model.md) · [processing contract](../contracts/processing-lifecycle-and-rollback.md)

## Requirement Completeness

- [X] CHK001 Are the desktop-to-GRAF and GRAF-to-MediaScribe audio boundaries explicitly defined, including the prohibition on desktop credentials and direct external egress? [Completeness, Spec §FR-007, Processing Contract §MediaScribe Egress]
- [X] CHK002 Are all v5 content-bearing artifacts—canonical WAV, playback candidate/derivative, temporary files, upload parts, transcript/diarization and processing state—named in the lifecycle requirements? [Completeness, Spec §FR-011, Data Model §Processing State]
- [X] CHK003 Are immutable package, revision, source-kind, authoritative digest and result-binding requirements specified without relying on mutable UI status alone? [Completeness, Spec §FR-008, Data Model §Server Revision And Artifacts]
- [X] CHK004 Are safe outcomes stated for invalid media, unavailable processing, unknown POST outcome, restart and deletion during processing? [Coverage, Spec §FR-012/§SC-007, Data Model §Processing State]
- [X] CHK005 Are historical v3/v4 records explicitly retained under their ordinary lifecycle without migration, silent reprocessing or v5 source-kind reassignment? [Completeness, Spec §FR-010, Data Model §Manifest Shape And Compatibility]

## Clarity And Consistency

- [X] CHK006 Is the difference between a single allowed external job, a retry of a known job and a prohibited automatic resubmission after ambiguous POST defined unambiguously? [Clarity, Spec §FR-012/§SC-007, Processing Contract §MediaScribe Egress]
- [X] CHK007 Are the rules that playback is retained/uploaded for review yet excluded from authoritative ASR fingerprint and submission consistent throughout the requirements? [Consistency, Spec §FR-003/FR-004/SC-004, Data Model §Server Revision And Artifacts]
- [X] CHK008 Is the requirement for metadata-only diagnostics/evidence concrete enough to exclude raw audio, transcript text, credentials, signed URLs and private paths? [Clarity, Spec §FR-011, Plan §Constraints]
- [X] CHK009 Are deletion claims limited to GRAF-controlled systems and does the requirement state the separately bounded MediaScribe/external-dependency status? [Consistency, Spec §FR-011, Processing Contract §Playback and Deletion, Constitution §IV]
- [X] CHK010 Are failure reasons and user-visible lifecycle status required to remain truthful without exposing content-bearing diagnostics? [Clarity, Spec §FR-012, Data Model §Processing State]

## Rollback And Recovery Coverage

- [X] CHK011 Is the known-good pre-v5 baseline specified as a recorded release/commit and installation receipt rather than an undocumented memory of a previous build? [Completeness, Spec §FR-009/SC-008, Processing Contract §Control Period and Rollback]
- [X] CHK012 Are rollback requirements explicit that they affect only future recordings and never rewrite, replace, reprocess or dual-fallback an accepted v5 revision? [Consistency, Spec §FR-008/FR-009, Processing Contract §Control Period and Rollback]
- [X] CHK013 Is server compatibility after desktop rollback defined so v5 readers persist while accepted v5 records still need processing/read/deletion? [Coverage, Processing Contract §Control Period and Rollback]
- [X] CHK014 Are retention and deletion requirements complete for a processing result that remains retryable, becomes terminal or is deleted before completion? [Coverage, Spec §Edge Cases/FR-011/FR-012]

## Dependencies And Assumptions

- [X] CHK015 Are the MediaScribe API, owner-controlled storage, Temporal workflow and local-purge lifecycle dependencies identified with timeout/failure/deletion expectations? [Dependency, Spec §Assumptions, Plan §Technical Context]
- [X] CHK016 Is the decision not to add a database migration or duplicate playback subsystem recorded with the invariants that make it safe? [Assumption, Research §Decision: v5 uses a new first-party source kind, Data Model §Server Revision And Artifacts]

## Review Result

- Requirements review passed on 2026-07-17; the immutable one-job and truthful deletion/rollback rules are explicit.
