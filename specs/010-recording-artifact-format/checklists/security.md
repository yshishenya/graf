# Security Checklist: Recording Artifact Format

**Purpose**: Validate that requirements protect secrets, data boundaries, and metadata-only diagnostics before planning and implementation
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are desktop no-upload and no-direct-MediaScribe boundaries explicit? [Completeness, Spec §FR-010]
- [x] CHK002 Are MediaScribe credential storage and access forbidden for the desktop app? [Completeness, Spec §FR-010]
- [x] CHK003 Are forbidden metadata categories complete for manifests, diagnostics, and file names? [Completeness, Spec §FR-007, Spec §FR-008]
- [x] CHK004 Are local `.env` secrets accounted for without allowing desktop artifact output to include them? [Completeness, Spec §US3]

## Requirement Clarity

- [x] CHK005 Is the distinction between server-side future MediaScribe integration and local artifact preparation unambiguous? [Clarity, Spec §Assumptions]
- [x] CHK006 Is the requirement to avoid live absolute user paths clear enough for diagnostics and manifests? [Clarity, Spec §FR-007]
- [x] CHK007 Are external egress exclusions specific enough to prevent hidden upload, Langfuse, dashboard, or MediaScribe calls? [Clarity, Spec §FR-010]

## Consistency And Acceptance

- [x] CHK008 Do security requirements align with the constitution rule that desktop clients never store MediaScribe credentials? [Consistency, Constitution §III]
- [x] CHK009 Are success criteria measurable for detecting forbidden secrets and content? [Measurability, Spec §SC-005]
- [x] CHK010 Are degraded/failed states required when an artifact is not transcription-ready, instead of silently accepting risky output? [Coverage, Spec §FR-006]
