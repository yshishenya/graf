# Infrastructure and Compatibility Requirements Checklist: Feature 228

**Purpose**: Reviewer-owned quality review for protected-domain retirement
requirements, not an implementation test plan.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

All items are intentionally unchecked pending reviewer assessment.

- [ ] CHK001 Are migration/data retirement requirements explicit about isolated backup/restore, expand/contract, abort conditions and prohibition of manual pointer mutation? [Completeness, Spec §FR-010]
- [ ] CHK002 Are Temporal requirements explicit about replay/idempotency, history compatibility and no history deletion? [Completeness, Spec §FR-011]
- [ ] CHK003 Are macOS/Sparkle requirements explicit about identity, signing trust, notarized rollback and appcast continuity? [Completeness, Spec §FR-012]
- [ ] CHK004 Is the release-train requirement clear that one Full CI receipt is bound to a frozen exact candidate SHA rather than to a branch or synthetic merge SHA? [Clarity, Spec §FR-016]
- [ ] CHK005 Are Dev rehearsal boundaries clear enough to prevent production volume, TCC, credential or deploy mutation? [Safety, Spec §Scope, §Edge Cases]
- [ ] CHK006 Do protected-domain requirements state which missing evidence blocks a slice instead of allowing an implicit exception? [Fail-closed coverage, Spec §FR-008–FR-012]
