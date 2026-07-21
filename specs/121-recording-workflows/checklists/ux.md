# UX And Accessibility Requirements Checklist: Complete Recording Workflows

**Purpose**: Validate cross-surface IA, state, modal, localization, and accessibility requirement quality
**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md)

## Information Architecture

- [x] CHK001 Is one meeting workspace limited to two content tabs, a persistent player, Share, and contextual More actions? [Completeness, Spec §FR-019]
- [x] CHK002 Are templates and Share contextual meeting actions rather than new top-level destinations? [Consistency, Spec §US4–US6]
- [x] CHK003 Are local/native capture controls separated from server-owned post-meeting actions? [IA, Spec §Product Scope, FR-023–FR-024]
- [x] CHK004 Are browser and embedded desktop required to show the same authorized lifecycle truth? [Consistency, Spec §FR-023, SC-009]

## Recording-State UX

- [x] CHK005 Are idle, detected, starting, active, paused, degraded, offline, stopping, finalizing, saved, upload, processing, partial, ready, failed, deleting, and deleted states covered? [Coverage, Spec §US1–US4, Edge Cases]
- [x] CHK006 Are primary and recovery actions defined without speculative repair controls? [Clarity, Spec §FR-009, FR-018]
- [x] CHK007 Is active-source truth required without confusing silence with failure? [Clarity, Spec §FR-010, Edge Cases]
- [x] CHK008 Is Stop prominence objectively measurable in pointer and keyboard paths? [Measurability, Spec §SC-002]

## Template And Share UX

- [x] CHK009 Does the template selector require `Авто`, at most four recommendations, and `Все форматы`, with create/manage in Settings? [Completeness, Spec §FR-026]
- [x] CHK010 Are current template, default, per-meeting override, immutable built-ins, and personal-copy behavior specified? [Consistency, Spec §FR-027–FR-030]
- [x] CHK011 Does regeneration preserve the accepted result until a successful candidate is explicitly used, without an up-front replace/preserve question? [Clarity, Spec §US5, FR-033–FR-034]
- [x] CHK012 Does the first Share surface stay limited to recipient entry, current viewers/revoke, and one collapsed content row while advanced policy remains contextual? [Completeness, Spec §US6, FR-036–FR-042]
- [x] CHK013 Are broader-audience warnings and policy-disabled reasons specified before activation? [Coverage, Spec §FR-043–FR-044, FR-058]

## Modal And Keyboard Accessibility

- [x] CHK014 Are modal focus entry, containment, Escape behavior, and focus return explicitly required? [Accessibility, Spec §FR-060, US8]
- [x] CHK015 Are visible focus, logical order, Russian accessible names, and non-color state cues defined for every control? [Accessibility, Spec §FR-059]
- [x] CHK016 Are status announcements bounded so elapsed time is not continuously announced? [Accessibility, Spec §FR-061]
- [x] CHK017 Are destructive and broadened-scope consequences readable before the primary action receives completion? [Accessibility, Spec §FR-058, US8]

## Responsive, Theme, And Localization

- [x] CHK018 Are supported narrow desktop/browser layouts required to preserve Stop, warnings, fields, and primary actions without horizontal scrolling? [Responsive, Spec §FR-062]
- [x] CHK019 Is Russian-first copy required without coupling UI locale, transcript language, and summary output language? [Localization, Spec §US8, FR-031, FR-059]
- [x] CHK020 Is the existing GRAF visual system required instead of a competitor-derived or parallel kit? [Clean Room, Spec §FR-063]
- [x] CHK021 Are light/dark, reduced-motion, increased-contrast, keyboard, and screen-reader proofs represented in acceptance/validation? [Coverage, Spec §US8, SC-010]

## Measurable Outcomes

- [x] CHK022 Can first-time Start, share configuration, playback alignment, cross-surface parity, and accessibility completion be objectively measured? [Measurability, Spec §SC-001, SC-005, SC-007, SC-009–SC-010]
- [x] CHK023 Are privacy and content-leak outcomes measurable rather than described only as “secure” or “safe”? [Measurability, Spec §SC-008, SC-011]
- [x] CHK024 Does every normal state have at most one visually primary action? [Simplicity, Spec §FR-064, SC-013]
- [x] CHK025 Are permanent lifecycle steppers, right control rails, and first-screen sharing matrices explicitly forbidden? [Simplicity, Spec §FR-025, FR-036, UX IA]
- [x] CHK026 Is plain Escape forbidden from stopping recording while retained for safe transient-UI dismissal? [Safety, Spec §FR-060, FR-065]

## Notes

- 26/26 requirement-quality checks pass for the current spec.
- Prototype selection remains a visual-expression gate; it cannot weaken these
  state, trust, or accessibility requirements.
