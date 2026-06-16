# Security And Privacy Requirements Checklist: MVP Loop Readiness

**Purpose**: Validate security/privacy requirement quality before implementation
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are forbidden evidence content classes explicitly enumerated for text, screenshots, runtime observations, and reference material? [Completeness, Spec §FR-019]
- [x] CHK002 Are secret, credential, signed URL, token, raw audio, private transcript, private email, private account, local path, and Krisp private capture exclusions specified? [Completeness, Spec §FR-019]
- [x] CHK003 Are access, sharing, download, export, retention, deletion, local purge, backup, and external dependency truth requirements represented? [Completeness, Spec §US4, FR-016, FR-017]
- [x] CHK004 Are production evidence boundaries specified so infrastructure smoke cannot become user rollout proof? [Completeness, Spec §FR-011, FR-012]

## Requirement Clarity

- [x] CHK005 Is "metadata-only evidence" defined with enough exclusion examples to avoid leaking content-bearing data? [Clarity, Spec §FR-019, Plan §Constraints]
- [x] CHK006 Are safe-to-commit and unsafe/private observation distinctions defined in the evidence schema? [Clarity, Contract §Readiness Evidence Schema]
- [x] CHK007 Is deletion copy bounded to systems controlled by 2brain Rec instead of universal erasure? [Clarity, Spec §FR-016]

## Requirement Consistency

- [x] CHK008 Do evidence safety requirements align with constitution data-boundary and deletion-truth principles? [Consistency, Constitution §III-IV, Plan §Constitution Check]
- [x] CHK009 Are reference comparison restrictions consistent with brand-distance and private-content requirements? [Consistency, Spec §FR-009, Contract §Reference Comparison]

## Scenario Coverage

- [x] CHK010 Are private live meeting and private Krisp reference inspection risks addressed without requiring committed private evidence? [Coverage, Spec §Assumptions, Research §Live Private Content]
- [x] CHK011 Are local desktop purge incomplete states represented so deletion cannot be overclaimed? [Coverage, Spec §US4, Data Model §LaunchGap]
- [x] CHK012 Are post-egress and dependency limitations represented as readiness truth rather than hidden caveats? [Coverage, Spec §FR-016, FR-017]

## Acceptance Criteria Quality

- [x] CHK013 Is there a measurable acceptance gate requiring forbidden-content scans to pass before merge? [Measurability, Spec §SC-003]
- [x] CHK014 Are P0/P1 blocker rules measurable enough to prevent launch claims while serious privacy gaps remain? [Measurability, Spec §SC-007]
