# Security And Privacy Checklist: MediaScribe Processing Pipeline

**Purpose**: Validate requirement quality for secrets, egress, content handling, audit, observability, tenant isolation, and deletion truth.
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the requirements themselves, not the implementation.

## Requirement Completeness

- [x] CHK001 Are MediaScribe credential boundaries defined for desktop, server workers, logs, diagnostics, API responses, committed files, and future dashboard clients? [Completeness, Spec FR-004/FR-018/FR-020]
- [x] CHK002 Are raw audio and transcript-content restrictions defined separately from metadata-only audit/status allowances? [Clarity, Spec FR-018/FR-019/FR-020]
- [x] CHK003 Are server-side egress rules explicit enough to prevent desktop clients from calling MediaScribe or starting workflows? [Completeness, Spec Clarifications/FR-004]
- [x] CHK004 Are tenant authorization requirements defined for processing pickup, status reads, and replay/retry operations? [Coverage, Spec FR-026/SC-008]
- [x] CHK005 Are Langfuse/default observability boundaries defined as metadata-only by default? [Completeness, Spec FR-021]

## Requirement Clarity

- [x] CHK006 Is it clear which data may appear in audit events versus controlled result stores? [Clarity, Data Model ProcessingAuditEvent/TranscriptSegment]
- [x] CHK007 Are workflow id and external job id safety rules specific enough to avoid PII, secrets, and private paths? [Clarity, Plan/Temporal Contract]
- [x] CHK008 Are blocked, retryable, and terminal dependency failures distinguishable without leaking sensitive details? [Clarity, Spec FR-016 and MediaScribe Contract]

## Scenario Coverage

- [x] CHK009 Are missing, invalid, expired, unreadable, and placeholder MediaScribe credential cases represented in requirements or edge cases? [Coverage, Spec Edge Cases/User Story 2]
- [x] CHK010 Are malformed result and unknown dependency status cases covered with safe reason-code behavior? [Coverage, Spec Edge Cases/Contracts]
- [x] CHK011 Are cross-tenant denial requirements measurable enough for tests and future access review? [Measurability, Spec SC-008]
- [x] CHK012 Are deletion/dependency accounting requirements explicit without promising deletion execution in this slice? [Consistency, Spec FR-022/SC-011]

## Acceptance Criteria Quality

- [x] CHK013 Are secret/content leak success criteria measurable across responses, logs, diagnostics, audit metadata, tests, and evidence? [Measurability, Spec SC-007]
- [x] CHK014 Are out-of-scope requirements strong enough to prevent dashboard, downloads, sharing, deletion execution, and macOS capture drift? [Scope, Spec FR-027/FR-030/SC-010]
- [x] CHK015 Are privacy requirements consistent with the constitution and not diluted by implementation assumptions? [Consistency, Constitution III/IV]
