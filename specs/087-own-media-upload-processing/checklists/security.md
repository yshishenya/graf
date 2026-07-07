# Security And Privacy Checklist: Own Media Upload Processing

**Purpose**: Validate data-boundary and privacy requirement quality before
implementation
**Created**: 2026-07-06
**Feature**: [spec.md](../spec.md)

## Secret And Egress Boundaries

- [x] CHK001 Are MediaScribe credentials explicitly server-only for manual uploads? [Completeness, Spec FR-005]
- [x] CHK002 Are desktop/browser direct MediaScribe egress and dependency URLs excluded? [Consistency, Spec Clarifications/FR-005]
- [x] CHK003 Are committed evidence and diagnostics forbidden from containing raw audio, transcript text, secrets, signed URLs, object keys, and private paths? [Coverage, Spec FR-009]

## Data Lifecycle

- [x] CHK004 Are uploaded media, transcript, summary/outcomes, workflows, and dependency state included in lifecycle/deletion truth requirements? [Completeness, Spec FR-010]
- [x] CHK005 Is the deletion wording bounded to GRAF-controlled storage and dependencies? [Consistency, Product Gates]
- [x] CHK006 Are dependency failure classes required to be safe and non-content-bearing? [Clarity, Spec FR-009]

## Access Control

- [x] CHK007 Are owner/workspace/device scope requirements present for upload creation and review access? [Completeness, Spec FR-001/FR-003]
- [x] CHK008 Are cross-workspace or foreign meeting inference risks covered by existing review/access requirements? [Coverage, Spec FR-004/FR-008]
