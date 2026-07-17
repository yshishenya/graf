# UX Requirements Checklist: Workspace Account Onboarding

**Purpose**: Validate onboarding, invitation and active-space requirements for
clarity, accessibility and safe recovery.
**Created**: 2026-07-17
**Feature**: `specs/097-workspace-account-onboarding/spec.md`

## Onboarding Clarity

- [x] CHK001 Are simple registration requirements explicit that users do not need to know workspace, organization or role terminology? [Clarity, Spec §US1, FR-001, FR-007]
- [x] CHK002 Are personal-space naming and the distinction from a corporate team defined consistently? [Consistency, Spec §FR-004a, FR-025, Assumptions]
- [x] CHK003 Are pending invitation offers specified as a separate post-authentication action with a safe refusal state? [Completeness, Spec §US1–US2, FR-006a, FR-009]

## Active Space And Recovery

- [x] CHK004 Are requirements defined for showing an active space before upload or recording when multiple spaces are accessible? [Coverage, Spec §US5, FR-014–FR-015]
- [x] CHK005 Are unavailable, revoked and stale-session states specified without exposing corporate data or deleting personal access? [Coverage, Spec §US5, FR-014a, FR-017, FR-027]
- [x] CHK006 Are requirements defined for multiple invitations and a user choice rather than an implied bulk acceptance? [Coverage, Spec §US2, Edge Cases]

## Accessibility And Localization

- [x] CHK007 Are status, confirmation, error and retry requirements defined for keyboard and screen-reader users in the shared cabinet surface? [Completeness, Spec §US2, FR-025, Product Gates]
- [x] CHK008 Are human-facing terms required to remain localized and free of internal tenancy identifiers? [Consistency, Spec §FR-007a, FR-025]
