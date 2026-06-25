# Security And Privacy Requirements Checklist: MVP Owner Journey Proof

**Purpose**: Validate privacy/security requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are forbidden evidence classes explicitly listed, including raw audio, transcript text, private outcomes, account identifiers, credentials, tokens, cookies, signed URLs, storage keys, private titles, and local private paths? [Completeness, Spec §FR-014]
- [x] CHK002 Are desktop MediaScribe boundaries specified so the desktop never calls MediaScribe or stores MediaScribe credentials? [Completeness, Spec §FR-003]
- [x] CHK003 Are server-mediated playback and no signed URL/object-key exposure preserved? [Completeness, Spec §FR-020, Plan §Technical Context]

## Requirement Clarity

- [x] CHK004 Is metadata-only evidence defined clearly enough to allow statuses, counts, timings, redacted IDs, and command summaries while excluding content? [Clarity, Spec §Assumptions, Data Model]
- [x] CHK005 Are deletion and denied/deleted/deleting visibility boundaries protected from outcome/playback proof changes? [Consistency, Plan §Post-Design Constitution Check]

## Scenario Coverage

- [x] CHK006 Are privacy risks during production probing addressed as requirements, not left to implementation judgment? [Coverage, Spec §FR-014, Edge Cases]
- [x] CHK007 Is clean-room reference use covered as a privacy/brand-distance rule? [Coverage, Spec §FR-013]

## Acceptance Criteria Quality

- [x] CHK008 Can forbidden-content checks be objectively run before commit/release? [Acceptance Criteria, Quickstart §10]
