# UX Requirements Checklist: Восстановление входа

**Purpose**: Validate recovery clarity, accessibility and web/embedded parity requirements
**Created**: 2026-08-19

## Recovery Clarity

- [x] CHK001 Does the spec distinguish an account conflict from service unavailability or an invalid code? [Clarity, Spec §US2]
- [x] CHK002 Is the next user action defined for both early and late ambiguity detection? [Completeness, Spec §US2 scenarios 1–4]
- [x] CHK003 Are only configured, active providers promised on the recovery surface? [Consistency, Spec §FR-009]
- [x] CHK004 Is the one-action path to second-provider confirmation measurable? [Acceptance Criteria, Spec §SC-004]
- [x] CHK005 Does recovery avoid exposing account, meeting or provider-subject details before authentication? [Privacy, Spec §FR-015, FR-020]

## Preview And Confirmation

- [x] CHK006 Does preview explain survivor, preserved sign-in methods/data classes, separate workspaces and revoked sessions/devices? [Completeness, Spec §FR-019]
- [x] CHK007 Is explicit confirmation required for every other-account case, including empty accounts? [Consistency, Spec §FR-013–FR-014]
- [x] CHK008 Are blocker, cancellation, expiry, replay and unchanged-data outcomes described? [Coverage, Spec §US2–US3]
- [x] CHK009 Is preview content bounded and free of sensitive raw identifiers? [Security, Spec §FR-019–FR-020]

## Surface And Accessibility Parity

- [x] CHK010 Are web and embedded outcomes and user-facing reasons required to match? [Consistency, Spec §FR-018]
- [x] CHK011 Are embedded verify, resend, back, preview, confirm and cancel routes explicitly scoped to `/desktop/...`? [Clarity, Spec §FR-018]
- [x] CHK012 Are provider actions and recovery copy required to remain keyboard and assistive-technology accessible through existing semantic links/forms? [Accessibility, Spec §US2, Assumptions]
- [x] CHK013 Is the scope limited to the blocked recovery journey rather than a broad login redesign? [Boundary, Spec §Out of Scope]
- [x] CHK014 Are successful Яндекс ID and VK journeys explicitly protected from regression? [Coverage, Spec §FR-021, SC-005]

## Notes

- Review audience: product/UX and accessibility reviewer before PR.
- All requirements-quality items pass; implementation validation remains in quickstart/tasks.
