# Security Requirements Checklist: Desktop Upload Queue

**Purpose**: Validate security/privacy requirement completeness before implementation
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

## Data Boundary Requirements

- [x] CHK001 Are owner-controlled upload boundaries explicitly defined and traceable to the allowed `012` server-mediated API? [Completeness, Spec §FR-014, Spec §Dependencies]
- [x] CHK002 Are direct MediaScribe, object-storage, signed URL, token, and credential paths explicitly excluded from desktop behavior? [Clarity, Spec §FR-014, Contract §Server-Mediated Upload]
- [x] CHK003 Are failure states required to avoid implying transcript, summary, workflow, or dashboard readiness before server ingest truth? [Consistency, Spec §US5, Contract §Server-Mediated Upload]

## Secret And Diagnostic Requirements

- [x] CHK004 Are forbidden diagnostic fields specified for credentials, tokens, signed URLs, raw audio, transcript text, and meeting content? [Coverage, Contract §Diagnostic Contract]
- [x] CHK005 Are absolute local paths treated separately from safe metadata in default diagnostics? [Clarity, Contract §Local Queue Store]
- [x] CHK006 Are upload retry and failure reasons constrained to safe classes rather than raw server/credential details? [Measurability, Spec §FR-013]

## Retention And Deletion Truth

- [x] CHK007 Are requirements explicit that local artifacts are retained while upload truth is pending, retrying, degraded, or blocked? [Completeness, Spec §FR-015]
- [x] CHK008 Are terminal deletion and purge states tied to explicit policy/user evidence instead of retry expiry alone? [Consistency, Spec §Clarifications]
