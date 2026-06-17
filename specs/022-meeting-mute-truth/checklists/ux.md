# UX Requirements Checklist: Meeting-App Mute Truth

**Purpose**: Validate visible control, limitation copy, accessibility, localization, and user-trust requirement quality before implementation.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirement quality only. It does not verify implementation behavior.

## Requirement Completeness

- [x] CHK001 Are native desktop requirements complete for Pause, Resume, Stop, active indicator, paused indicator, local recording status, and limitation warning visibility? [Completeness, Spec §US1, Contract §Product Privacy Control]
- [x] CHK002 Are user-facing limitation copy requirements complete for unavailable, stale, contradictory, unsupported, and deferred meeting-app mute truth? [Completeness, Spec §FR-014, Contract §Desktop Limitation Copy]
- [x] CHK003 Are requirements complete for keeping Pause/Stop visible without obscuring local recording status or upload/review states from earlier slices? [Completeness, Contract §Desktop Limitation Copy]
- [x] CHK004 Are requirements complete for explaining that `2brain Pause` protects local recording speech while third-party meeting-app mute remains unproven? [Completeness, Spec §Clarifications, Contract §Desktop Limitation Copy]

## Requirement Clarity

- [x] CHK005 Is the required limitation copy exact enough to avoid implementation teams inventing weaker or overpromising copy? [Clarity, Spec §FR-014]
- [x] CHK006 Are user-visible states named clearly enough to distinguish normal recording, paused recording, degraded/unproven mute truth, unsupported target, and stopped recording? [Clarity, Data Model §§ProductPrivacyControlState/MuteTruthDecision]
- [x] CHK007 Are allowed and forbidden user-facing claims explicitly documented? [Clarity, Contract §Desktop Limitation Copy]

## Requirement Consistency

- [x] CHK008 Are UX requirements consistent with the clean-room design direction and do they avoid copying Krisp-specific UI, copy, icons, assets, or brand expression? [Consistency, Constitution §Product And Platform Constraints]
- [x] CHK009 Are user-facing warning requirements consistent with manifest truth and target matrix outcomes? [Consistency, Contract §Desktop Limitation Copy, Contract §Target Matrix]
- [x] CHK010 Are desktop-native control requirements consistent with the product rule that capture-critical state remains local/native and not server-rendered? [Consistency, Plan §Structure Decision]

## Accessibility And Localization

- [x] CHK011 Are accessibility requirements defined for the limitation warning, Pause/Resume, Stop, and paused/active state labels? [Coverage, Contract §Desktop Limitation Copy]
- [x] CHK012 Are text wrapping and non-truncation requirements defined for the core action phrase "Use Pause or Stop"? [Coverage, Contract §Desktop Limitation Copy]
- [x] CHK013 Are requirements clear enough to support Russian/English localization later without changing the MVP claim boundary? [Clarity, Spec §FR-014]

## Scenario Coverage

- [x] CHK014 Are UX requirements defined for first recording on an unproven target before the user relies on meeting-app mute? [Coverage, Spec §US2]
- [x] CHK015 Are UX requirements defined for a paused active recording where Stop must remain immediately available? [Coverage, Contract §Product Privacy Control]
- [x] CHK016 Are UX requirements defined for unsupported/deferred targets without implying app failure or hidden recording? [Coverage, Contract §Target Matrix]

## Acceptance Criteria Quality

- [x] CHK017 Can reviewers objectively evaluate whether the limitation warning is present, accessible, and not overclaiming? [Measurability, Quickstart §4-5]
- [x] CHK018 Are UX acceptance criteria traceable to privacy and capture-truth requirements rather than visual preference alone? [Traceability, Spec §US1-US4]

## Notes

- All generated UX requirement checks pass for the clarified 2026-06-16 spec and plan artifacts.
