# Security Requirements Checklist: Provider Link Verified Callback

**Purpose**: Assess whether the authentication, privacy, RLS and shared Settings requirements are complete, clear and testable before implementation.
**Created**: 2026-07-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are start, verified callback, explicit confirmation, terminal-state cleanup and legacy compatibility requirements defined for the full provider-link lifecycle? [Completeness, Spec §Required Product Direction]
- [X] CHK002 Are authorization requirements specified separately for start, callback and confirmation, including exact user, workspace and initiating-session binding? [Completeness, Spec §FR-003–FR-005, FR-008b]
- [X] CHK003 Are requirements explicit that the link callback cannot create an identity/user, issue or switch a GRAF session, or expose a token before confirmation? [Completeness, Spec §FR-006–FR-008a]
- [X] CHK004 Are requirements specified for provider policy and active membership changes between start, callback and confirmation? [Completeness, Spec §FR-012–FR-014]
- [X] CHK005 Are requirements defined for candidate-claim lifetime, minimization and terminal-state cleanup without weakening required identity persistence after a confirmed link? [Completeness, Spec §FR-021]
- [X] CHK006 Are RLS requirements documented for both authenticated owner access and public callback lookup bound to exactly one callback state? [Completeness, Plan §Validation Plan; Data Model §Invariants]

## Requirement Clarity and Consistency

- [X] CHK007 Is "verified provider callback" defined as adapter-verified server-side claims, and is every client-originated identity claim explicitly excluded as proof? [Clarity, Spec §Product Principles, FR-001–FR-002]
- [X] CHK008 Is the opaque confirmation identifier distinguished from provider subject, callback state, authorization code and session token so no client value can select identity material? [Clarity, Spec §FR-008b; Contract §Confirmation]
- [X] CHK009 Are new-intent idempotence and replay of the same terminal intent specified as separate outcomes with no conflicting interpretation of "one-time-use"? [Consistency, Spec §FR-005, FR-009, FR-014]
- [X] CHK010 Are the conflict requirements consistent with the prohibition on identity transfer, account merge, primary-provider change and owner/contact disclosure? [Consistency, Spec §FR-010–FR-011, FR-022]
- [X] CHK011 Is the direct-link compatibility response specified as safely retained for this release without reintroducing a second client-provided identity path? [Consistency, Spec §FR-016–FR-017; Contract §Legacy compatibility]

## Scenario and Edge-Case Coverage

- [X] CHK012 Are requirements defined for malformed, missing, expired, cancelled, provider-denied and replayed callback states without naming sensitive provider payloads in responses or evidence? [Coverage, Spec §Edge Cases]
- [X] CHK013 Are wrong user, workspace and active-session confirmation attempts covered independently, including multiple browser tabs and a session that expires or is revoked mid-flow? [Coverage, Spec §User Story 5]
- [X] CHK014 Are requirements defined for an existing same-user identity, another-user identity in the same organization, and another-user identity in another organization? [Coverage, Spec §User Story 4]
- [X] CHK015 Are requirements defined for absent/unverified email or phone and conflicting contact claims without treating contacts as a merge or enrolment signal? [Coverage, Spec §User Story 4; Edge Cases]
- [X] CHK016 Are ordinary provider login/signup and invitation/self-enrolment behavior explicitly preserved and excluded from the link flow? [Coverage, Spec §User Story 3, FR-015, FR-022]
- [X] CHK017 Are migration-failure, partially written candidate and cleanup-retry expectations defined sufficiently to preserve the existing safe legacy rejection path? [Gap, Recovery]

## Non-Functional and UX Requirements

- [X] CHK018 Are metadata-only audit requirements specified for every lifecycle outcome, including permitted safe fields and prohibited raw provider/session/callback values? [Completeness, Spec §FR-018–FR-019]
- [X] CHK019 Are Settings requirements defined for safe provider-only copy, explicit user confirmation, cancellation/retry, localized status, keyboard focus and screen-reader status messaging? [Completeness, Research §Decision 5]
- [X] CHK020 Are browser and embedded desktop parity requirements explicit while excluding a duplicated native macOS auth screen? [Consistency, Spec §Clarifications; Plan §Structure Decision]
- [X] CHK021 Is the 15-minute lifetime and bounded callback/confirmation transaction requirement measurable and consistent with existing callback-state behavior? [Measurability, Plan §Technical Context]
- [X] CHK022 Are required validation boundaries specified for contract, PostgreSQL RLS, audit redaction, UI accessibility/parity, ordinary login preservation, repository CI and production release? [Traceability, Plan §Validation Plan; Quickstart]

## Dependencies and Remaining Gaps

- [X] CHK023 Are the provider adapter verification, existing auth-session principal fields, callback-state semantics, RLS helper and cabinet CSRF dependencies documented as constraints rather than assumed behavior? [Dependency, Research §Decisions 2–7]
- [X] CHK024 Is the cleanup schedule for abandoned `initiated`/`callback_verified` states defined—transactional on access, scheduled job, or both—without retaining raw candidate claims past TTL? [Gap, Lifecycle]
- [X] CHK025 Are release rollback requirements defined for the schema/RLS migration and compatibility guard if production callback errors occur? [Gap, Release Recovery]

## Notes

- This is a requirements-quality checklist, not an implementation test plan.
- Resolve the three marked gaps in plan/tasks before implementation, or record a bounded design decision with its validation evidence.
