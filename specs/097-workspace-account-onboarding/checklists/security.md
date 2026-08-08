# Security Requirements Checklist: Workspace Account Onboarding

**Purpose**: Validate that onboarding requirements define safe account,
membership, session, RLS and audit boundaries before implementation.
**Created**: 2026-07-17
**Feature**: `specs/097-workspace-account-onboarding/spec.md`

## Requirement Completeness

- [x] CHK001 Are requirements explicit that account creation and corporate membership are separate state changes? [Completeness, Spec §FR-002, FR-005–FR-006a]
- [x] CHK002 Are personal-space idempotency and unique ownership requirements defined for retry and callback replay? [Completeness, Spec §FR-003a–FR-003b, SC-009]
- [x] CHK003 Are invitation identity matching, expiry, revocation and replay requirements defined before membership creation? [Completeness, Spec §FR-008–FR-010, Edge Cases]
- [x] CHK004 Are requirements explicit that no raw workspace identifier, provider token or invitation contact becomes public input or evidence? [Completeness, Spec §FR-007–FR-007a, FR-023]

## Authorization And Privacy Consistency

- [x] CHK005 Are server-side active-space authority and client-hint limitations specified consistently for browser and desktop flows? [Consistency, Spec §FR-026–FR-027]
- [x] CHK006 Are personal/corporate isolation and non-transfer of recordings specified consistently for join, switch, revoke and queued-work cases? [Consistency, Spec §FR-004, FR-015–FR-017]
- [x] CHK007 Are invitation offers defined as explicit user choices rather than a login side effect? [Consistency, Spec §FR-005a, FR-006a, FR-009]
- [x] CHK008 Are audit and diagnostic requirements limited to metadata for every enrollment and revocation transition? [Coverage, Spec §FR-022–FR-023, FR-028]

## Recovery And Migration Coverage

- [x] CHK009 Are requirements defined for a revoked active corporate space and an in-flight operation that cannot be silently retargeted? [Coverage, Spec §FR-014a–FR-015a, Edge Cases]
- [x] CHK010 Does the migration requirement require reviewable classification before any membership or recording ownership change? [Coverage, Spec §FR-024–FR-024a, SC-011]
- [x] CHK011 Are provider and email enrollment parity requirements stated without weakening invitation approval? [Consistency, Spec §FR-020–FR-020a]
- [x] CHK012 Are approved-domain discovery limits explicitly privacy-safe and disabled by default for the first release? [Coverage, Spec §FR-018–FR-019, Assumptions]
