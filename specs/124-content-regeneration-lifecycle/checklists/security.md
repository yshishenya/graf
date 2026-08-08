# Requirements Quality Checklist: Security, Privacy and Deletion

**Purpose**: Validate that security and deletion requirements are complete, clear and consistent.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are owner, shared-viewer and automatic-system authorization boundaries explicit? [Completeness, Spec §User Stories 2/6, FR-009/028]
- [X] CHK002 Are source, current-pointer and deletion fences required on every mutating lifecycle path? [Completeness, Spec §FR-003/012/022]
- [X] CHK003 Are content-bearing generation calls, Langfuse observations and Temporal History explicitly classified as retained observability while GRAF-controlled copies remain in the deletion inventory? [Completeness, Spec §FR-026/027, Constitution §III/IV]
- [X] CHK004 Are workspace/RLS isolation and cross-tenant failure behavior stated? [Completeness, Spec §NFR-003, Key Entities]

## Requirement Clarity and Consistency

- [X] CHK005 Is “current accepted” unambiguously different from candidate, superseded and historical output? [Clarity, Spec §FR-005/017]
- [X] CHK006 Is the prohibition on universal erasure claims consistent with controlled GRAF purge and retained observability/external-provider limits? [Consistency, Spec §FR-027, Constitution §III/IV]
- [X] CHK007 Are shared/export/public paths consistently prohibited from exposing candidate or private provenance? [Consistency, Spec §FR-028, User Story 6]
- [X] CHK008 Are deletion states specific enough to distinguish retained plaintext observability from metadata-only audit? [Clarity, Spec §FR-026/027, Contract §deletion-generation]

## Scenario and Edge Coverage

- [X] CHK009 Are delete-vs-import, delete-vs-generate and delete-vs-accept races explicitly addressed? [Coverage, Spec §User Story 6, Edge Cases]
- [X] CHK010 Are late callbacks after tombstone and partial object-store purge covered? [Coverage, Spec §FR-022, Edge Cases]
- [X] CHK011 Are stale candidate IDs/preview URLs outside owner scope fail-closed? [Edge Case, Spec §User Story 6, FR-011/028]

## Acceptance Quality

- [X] CHK012 Can privacy/deletion acceptance be measured without requiring private content in evidence? [Measurability, Spec §SC-005/009, NFR-001]
