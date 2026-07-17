# Security Requirements Checklist: Safe Browser Login Returns and Callback Diagnostics

**Purpose**: Validate that authentication, authorization, privacy, and diagnostic requirements are complete and reviewable before implementation.
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [browser auth return contract](../contracts/browser-auth-return.md)

## Requirement Completeness

- [x] CHK001 Are post-session destination requirements specified for every supported browser sign-in family, including external providers, email login, and email registration? [Completeness, Spec §FR-001, §FR-005]
- [x] CHK002 Is the authorization authority for retaining a meeting detail explicitly limited to the existing meeting access decision, rather than a new or implicit policy? [Completeness, Consistency, Spec §FR-003, Assumptions]
- [x] CHK003 Is the source of the email return candidate explicitly bound to one-time server-side state, with a later verification-form value prohibited from overriding it? [Clarity, Security, Spec §FR-012]
- [x] CHK004 Are callback anti-forgery, expiry, single-use, cancellation, replay, and initiating-browser-binding requirements preserved rather than weakened by the return policy? [Coverage, Spec §FR-006, §SC-005]
- [x] CHK005 Are ownership, active workspace membership, explicit sharing, deletion, cross-workspace, and access changes during sign-in identified as the policy conditions relevant to a deep return? [Coverage, Spec §User Story 1, Edge Cases, Assumptions]

## Privacy And Non-Disclosure

- [x] CHK006 Do the fallback and unavailable-page requirements explicitly prohibit disclosure of meeting existence, title, owner, workspace, transcript, media, and sharing state? [Completeness, Spec §FR-008]
- [x] CHK007 Is the required convergence of missing, deleted, malformed, and denied detail states documented without an observable reason-specific outcome? [Consistency, Coverage, Spec §FR-007, §FR-013, Edge Cases]
- [x] CHK008 Is the RLS requirement specific about using the completed authenticated context and about avoiding content-bearing review loading for a redirect decision? [Clarity, Plan §Technical Context, Data Model §RLS and privacy invariants]

## Diagnostic Requirements

- [x] CHK009 Do callback diagnostic requirements enumerate prohibited authorization material and raw callback query data, rather than relying on a vague term such as "sensitive data"? [Clarity, Spec §FR-009]
- [x] CHK010 Do callback diagnostic requirements enumerate the minimum support metadata retained after redaction, so privacy and operability are balanced measurably? [Completeness, Spec §FR-010]
- [x] CHK011 Is the header/query/cookie exclusion boundary documented for both runtime access output and application request events? [Consistency, Contract §Callback diagnostics contract]
- [x] CHK012 Is the synthetic-marker success criterion measurable without requiring real credentials, user identifiers, meeting content, or production logs in test evidence? [Measurability, Spec §SC-004, Quickstart §Required scenarios]

## Dependencies And Boundaries

- [x] CHK013 Is the boundary between repository-controlled server logging and separately authorized external reverse-proxy or retention operations explicit? [Dependency, Assumption, Spec §Assumptions]
- [x] CHK014 Is the exclusion of provider-link callbacks, access-policy changes, new providers, client permissions, and production release work recorded so the auth hardening cannot silently broaden scope? [Scope, Spec §Out of Scope, Plan §Constraints]

## Notes

- Review pass 1: 14/14 requirement-quality questions pass. The specification and contract define the security boundary, trusted return source, non-disclosure behavior, metadata allowlist, and operational exclusions without embedding credentials or private evidence.
