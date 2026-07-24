# Requirements Quality Checklist: AI and Processing Semantics

**Purpose**: Validate that processing, generation, provenance and retry requirements are precise enough for safe implementation.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are media revision, processing result, outcome, template and generator versions treated as separate lineage axes? [Completeness, Spec §FR-016, Data Model §Identity axes]
- [X] CHK002 Are changed provider hashes, duplicate hashes and late callbacks distinguished? [Completeness, Spec §FR-004/022, Contract §processing-lineage]
- [X] CHK003 Are automatic baseline, manual format change, same-format refresh and new-source follow-up policies stated? [Completeness, Spec §FR-006/008/009/014]
- [X] CHK004 Are source/template/generator/model/config provenance fields required for every candidate? [Completeness, Spec §FR-010/019]

## Requirement Clarity and Consistency

- [X] CHK005 Is the boundary between automatic retry and manual retry explicit by error class? [Clarity, Spec §FR-007, Contract §processing-lineage]
- [X] CHK006 Is an accepted outcome protected from candidate generation, failure or rejection? [Consistency, Spec §FR-013/017]
- [X] CHK007 Is a new source allowed to prepare a candidate without being allowed to silently replace current? [Consistency, Spec §FR-006/017, Assumptions]
- [X] CHK008 Is preview provenance bounded to safe human context rather than raw provider/prompt data? [Clarity, Spec §FR-011, Contract §content-regeneration]

## Scenario and Edge Coverage

- [X] CHK009 Are missing transcript, malformed payload, no speech, provider timeout and auth/policy block covered? [Coverage, Spec §User Story 1/7]
- [X] CHK010 Are concurrent candidate accept, changed source during generation and template archive/delete covered? [Coverage, Spec §User Story 3/5, Edge Cases]
- [X] CHK011 Are model/prompt deployment and repeated meeting views explicitly excluded from silent regeneration? [Edge Case, Spec §FR-008]

## Acceptance Quality

- [X] CHK012 Can the system prove one active candidate per full idempotency key and zero stale accepts? [Measurability, Spec §SC-001/003]
- [X] CHK013 Can historical outcomes be explained by source/result/template/generator provenance after template changes? [Measurability, Spec §SC-002, Data Model]
