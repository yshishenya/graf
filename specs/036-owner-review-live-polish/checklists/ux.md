# UX Requirements Quality Checklist: Owner Review Live Polish

**Purpose**: Validate desktop/web review UX, clean-room baseline, accessibility, and responsive requirements
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are runtime-critical V8 surfaces enumerated instead of vaguely saying "match reference"? [Completeness, Plan §Phase 0 Research]
- [x] CHK002 Are desktop list/detail, web list/detail, governance, upload/new, search/filter/sort, and responsive states covered? [Coverage, Contract runtime-polish-cleanroom]
- [x] CHK003 Are native capture control visibility requirements defined for active, paused, resumed, and stopped states? [Completeness, Spec §US3, Quickstart §5]
- [x] CHK004 Are unavailable/deferred controls required to be truthful instead of decorative? [Completeness, Spec §FR-006/FR-007]
- [x] CHK005 Are clean-room brand-distance restrictions specified with concrete forbidden categories? [Completeness, Spec §FR-012]

## Requirement Clarity

- [x] CHK006 Is "meeting workspace first" explained as surfacing meetings/review/capture readiness before diagnostics? [Clarity, Spec §US3, Contract runtime-polish-cleanroom]
- [x] CHK007 Is "V8 polish" bounded to runtime-critical surfaces rather than all 17 frames? [Clarity, Spec §Clarifications]
- [x] CHK008 Are product-facing labels required for statuses, actions, and blocked states? [Clarity, Spec §FR-004/FR-011]
- [x] CHK009 Are text-fit and responsive constraints specified enough to guide implementation review? [Clarity, Contract runtime-polish-cleanroom]

## Requirement Consistency

- [x] CHK010 Do web polish requirements preserve server-owned review ownership and native desktop capture authority? [Consistency, Plan §Structure Decision]
- [x] CHK011 Do clean-room rules allow IA lessons while forbidding copied Krisp visual/copy expression? [Consistency, Research §V8 surfaces]
- [x] CHK012 Are desktop and web labels expected to be coherent without forcing exact Krisp wording? [Consistency, Spec §FR-012]

## Acceptance Criteria Quality

- [x] CHK013 Can a reviewer decide within 10 seconds whether transcript, playback, speakers, notes/actions, and governance are available? [Measurability, Spec §SC-003]
- [x] CHK014 Can desktop control visibility be objectively checked from installed-app evidence? [Measurability, Spec §SC-004]
- [x] CHK015 Can clean-room validation objectively record zero committed private Krisp screenshots/assets/icons/copy? [Measurability, Spec §SC-005]

## Scenario Coverage

- [x] CHK016 Are embedded web load failures covered while native capture controls remain usable? [Edge Case, Spec §Edge Cases]
- [x] CHK017 Are empty, processing, partial, failed, deleted, access-limited, and denied review states represented in requirements? [Coverage, Data Model §ReviewSurfaceState]
- [x] CHK018 Are compact/responsive layouts included in the UX requirement scope? [Coverage, Contract runtime-polish-cleanroom]
- [x] CHK019 Are diagnostic surfaces permitted only as failure/diagnostic states rather than main default? [Clarity, Contract runtime-polish-cleanroom]
- [x] CHK020 Are accessibility expectations implied by focus/text-fit/native control persistence sufficiently represented for implementation tasks? [Coverage, Plan §Testing]
- [x] CHK021 Are installed-app cabinet configured, missing-auth, missing-server, and local-only states required to be distinguishable without relying on developer shell environment? [Coverage, Spec §FR-017/SC-008]
