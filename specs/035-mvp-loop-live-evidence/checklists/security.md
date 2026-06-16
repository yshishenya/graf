# Security And Privacy Requirements Checklist: MVP Loop Live Evidence

**Purpose**: Validate that requirements fully specify evidence safety,
forbidden content, and claim boundaries before implementation.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are forbidden evidence classes explicitly documented, including raw audio, transcript text, credentials, tokens, signed URLs, private emails, private account identifiers, and private reference screenshots? [Completeness, Spec §FR-010]
- [x] CHK002 Are metadata-safe evidence requirements defined for desktop screenshots, web review evidence, readiness reports, and clean-room reference notes? [Completeness, Spec §FR-002, §FR-004, §FR-011]
- [x] CHK003 Are claim restrictions defined so stronger MVP, pilot, rollout, and production claims cannot bypass unresolved P0/P1 launch gaps? [Completeness, Spec §FR-006]
- [x] CHK004 Are data-boundary assumptions clear for live web evidence versus fixture-backed evidence? [Assumption, Spec §Assumptions]

## Requirement Clarity

- [x] CHK005 Is the accepted desktop bundle path specified precisely enough to avoid permission-path ambiguity? [Clarity, Spec §FR-001]
- [x] CHK006 Is the no-new-behavior boundary explicit enough to prevent hidden implementation of notes/actions, sharing, deletion, installer, or deployment changes? [Clarity, Spec §FR-012]
- [x] CHK007 Are manifest spot-check requirements limited to metadata fields rather than content-bearing payloads? [Clarity, Spec §FR-003]

## Requirement Consistency

- [x] CHK008 Do the spec, plan, and contracts consistently forbid private content in committed evidence? [Consistency, Spec §FR-010, Plan §Constraints]
- [x] CHK009 Do clean-room reference requirements align with the constitution's brand-distance and data-boundary rules? [Consistency, Spec §FR-011]

## Acceptance Criteria Quality

- [x] CHK010 Are forbidden-content scan expectations measurable and tied to committed evidence paths? [Acceptance Criteria, Spec §SC-003]
- [x] CHK011 Is the latest-artifact validator outcome defined as either pass evidence or a blocker, avoiding ambiguous partial acceptance? [Acceptance Criteria, Spec §SC-004]
