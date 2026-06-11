# UX Requirements Checklist: Desktop Upload Queue

**Purpose**: Validate upload queue status and recovery requirement quality
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

## Status Visibility Requirements

- [x] CHK001 Are user-facing upload states enumerated and distinguishable from local recording states? [Clarity, Spec §FR-003]
- [x] CHK002 Is the timing for queue truth visibility quantified? [Measurability, Spec §FR-004]
- [x] CHK003 Are progress and server truth requirements defined so UI cannot show optimistic success? [Consistency, Spec §FR-007, Contract §UI Contract]

## Recovery Flow Requirements

- [x] CHK004 Are retry, stop retry, and manual recovery actions required without app restart? [Completeness, Spec §FR-010]
- [x] CHK005 Are blocked/manual-only states defined for auth, schema, local resource, and retention-expiry scenarios? [Coverage, Data Model §UploadFailureCategory]
- [x] CHK006 Are accessibility-friendly reason and action requirements present for problematic upload states? [Coverage, Contract §UI Contract]

## Scope And Simplicity Requirements

- [x] CHK007 Is the UI scope constrained to the existing native recording surface instead of a product-wide redesign? [Clarity, Spec §Clarifications]
- [x] CHK008 Is active recording status protected from being covered or replaced by upload queue UI? [Consistency, Spec §FR-017, Contract §UI Contract]
