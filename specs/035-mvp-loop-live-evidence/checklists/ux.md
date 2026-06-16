# UX And Reference Requirements Checklist: MVP Loop Live Evidence

**Purpose**: Validate that requirements specify live desktop/web UX evidence and
clean-room reference boundaries clearly enough for review.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are desktop evidence states defined for idle or ready, active recording, paused recording, resumed recording, and stopped/list states? [Completeness, Spec §FR-002]
- [x] CHK002 Are web owner review list/detail/governance states required to be represented as ready, blocked, or deferred? [Completeness, Spec §FR-004]
- [x] CHK003 Are notes/action output truth requirements defined when generated notes are unavailable? [Completeness, Spec §US2]
- [x] CHK004 Are clean-room reference comparison outputs defined with allowed lessons and intentional differences? [Completeness, Spec §US4, §FR-011]

## Requirement Clarity

- [x] CHK005 Is the one-action Stop and visible capture requirement clear in the desktop acceptance scenario? [Clarity, Spec §US1]
- [x] CHK006 Is fixture-backed web evidence labeled distinctly from live metadata-safe web evidence? [Clarity, Spec §US2]
- [x] CHK007 Are "reference alignment" requirements framed as product lessons rather than copied visual implementation? [Clarity, Spec §US4]

## Scenario Coverage

- [x] CHK008 Are wrong bundle path, stale permission, degraded incoming audio, unavailable web auth, stale blockers, unsafe evidence, and too-close reference cases covered as edge cases? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are both successful and blocked readiness outcomes represented in user scenarios? [Coverage, Spec §US3]

## Acceptance Criteria Quality

- [x] CHK010 Can each screenshot/evidence requirement be objectively reviewed from committed artifacts or blocker notes? [Measurability, Spec §SC-001]
- [x] CHK011 Is the strongest claim required to be singular and traceable rather than implied by UI polish? [Acceptance Criteria, Spec §SC-006]
