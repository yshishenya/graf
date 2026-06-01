# Driver And Audio Route Checklist: Manual Capture Session And Visible Indicator

**Purpose**: Validate driver/audio route requirement quality before implementation
**Created**: 2026-06-01
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are valid route prerequisites required before recording can start? [Completeness, Spec §FR-001, FR-006]
- [x] CHK002 Are publication-only, stale, blocked, failed, and unknown route states explicitly blocked from recording start? [Completeness, Spec §FR-006]
- [x] CHK003 Is low-resource non-recording passthrough required to remain separate from recording state? [Completeness, Spec §FR-005, FR-012]
- [x] CHK004 Are app bridge loss and `coreaudiod` restart covered as fail-closed recording events? [Completeness, Spec §FR-013]
- [x] CHK005 Are physical device change and route degradation edge cases listed? [Coverage, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK006 Is route readiness defined as evidence-based rather than device visibility alone? [Clarity, Spec §FR-006]
- [x] CHK007 Is the driver ownership boundary clear enough to avoid moving policy/UI logic into HAL callbacks? [Clarity, Plan §Summary]
- [x] CHK008 Are realtime safety constraints preserved for HAL callback-sensitive paths? [Clarity, Plan §Performance Goals]

## Acceptance Criteria Quality

- [x] CHK009 Are route-blocked start success criteria measurable as zero invalid starts? [Measurability, Spec §SC-004]
- [x] CHK010 Are browser/app smoke targets named and bounded? [Measurability, Spec §SC-008]
- [x] CHK011 Is Yandex Browser status explicit enough to prevent false support claims? [Consistency, Spec §Assumptions]
- [x] CHK012 Are no-upload/no-egress constraints included in audio smoke acceptance? [Coverage, Quickstart §5]
