# Specification Quality Checklist: Управляемое поэтапное retirement legacy

**Purpose**: Reviewer-owned проверка качества требований перед implementation.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

Все пункты намеренно оставлены unchecked: агент не является владельцем этого
review и не меняет checkbox state.

## Requirement Completeness

- [ ] CHK001 Are candidate discovery, approved classification and removal authorization explicitly distinguished? [Completeness, Spec §US1, FR-001, FR-008]
- [ ] CHK002 Are all metadata-only record fields, forbidden content classes and stale-evidence conditions specified? [Completeness, Spec §FR-002–FR-004]
- [ ] CHK003 Are owner, expiry, trigger, risk, validation and linked work required for every retained exception? [Completeness, Spec §FR-006]
- [ ] CHK004 Are protected domains and their separate planning/rehearsal boundaries specified rather than delegated to generic cleanup? [Completeness, Spec §FR-010–FR-012]

## Requirement Clarity and Consistency

- [ ] CHK005 Is the meaning of `candidate`, `approved`, `blocked` and `retired` unambiguous and consistent with classifications? [Clarity, Spec §FR-001–FR-002]
- [ ] CHK006 Is a "legacy-sensitive path" sufficiently bounded to distinguish active compatibility from archival evidence and documentation? [Clarity, Spec §FR-007]
- [ ] CHK007 Are the no-removal, no-production-mutation and no-reviewer-checkbox boundaries consistent across scope, requirements and tasks? [Consistency, Spec §FR-017–FR-018]
- [ ] CHK008 Are the Feature 216 legacy contract and Feature 228 additions non-conflicting and traceably related? [Consistency, Spec §Assumptions]

## Acceptance and Safety Coverage

- [ ] CHK009 Can each success criterion be objectively demonstrated without exposing user or production data? [Measurability, Spec §SC-001–SC-008]
- [ ] CHK010 Are incomplete discovery, stale SHA, forbidden metadata, expired exceptions and missing rollback handled as explicit failure states? [Coverage, Spec §Edge Cases]
- [ ] CHK011 Are migration, Temporal, MediaScribe (T036), macOS/Sparkle and rollback domains covered by domain-appropriate evidence requirements? [Coverage, Spec §FR-010–FR-012]
- [ ] CHK012 Are release-train and individual fast-CI evidence requirements explicitly non-interchangeable? [Consistency, Spec §US5, FR-016]

## Agent Context and Governance

- [ ] CHK013 Does the specification define the minimum context an agent reads and prohibit full-registry/root-file duplication? [Completeness, Spec §US4, FR-014]
- [ ] CHK014 Are GitHub issue, PR, task, changelog-fragment and exact-SHA links required without making root CHANGELOG.md a parallel write target? [Completeness, Spec §FR-015–FR-017]
- [ ] CHK015 Is the decision owner/reviewer role clear for every point that could otherwise authorize removal? [Clarity, Spec §Actors, §Assumptions]
