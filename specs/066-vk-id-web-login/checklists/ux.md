# UX Checklist: VK ID Web Login

**Purpose**: Validate browser login UX requirement quality before implementation
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

## Provider Choice

- [x] CHK001 Are active VK rendering requirements clear for both login and sign-up pages? [Completeness, Spec §FR-001]
- [x] CHK002 Is the removal of the VK `скоро` state measurable? [Measurability, Spec §SC-001]
- [x] CHK003 Does the spec keep Telegram disabled so the UI does not overpromise unrelated providers? [Consistency, Spec §Edge Cases]

## Recovery

- [x] CHK004 Are provider failure messages bounded and actionable without exposing provider internals? [Safety, Spec §US2, FR-007]
- [x] CHK005 Is email fallback required to remain visible on login and sign-up pages? [Coverage, Spec §FR-011]
- [x] CHK006 Are safe return-path expectations described from start through callback? [Clarity, Spec §FR-005]
