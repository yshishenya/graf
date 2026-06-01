# Driver Requirements Checklist: macOS Real Bidirectional Passthrough

**Purpose**: Validate driver and routing requirement quality before tasks/implementation
**Created**: 2026-05-31
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is the physical microphone to `2brain Rec Microphone` direction explicitly required? [Completeness, Spec §FR-001]
- [x] CHK002 Is the `2brain Rec Speaker` to physical output direction explicitly required? [Completeness, Spec §FR-002]
- [x] CHK003 Is the app heartbeat fail-closed behavior preserved with a measurable timeout? [Completeness, Spec §FR-008]
- [x] CHK004 Are stale route events defined for physical device, browser, heartbeat, and `coreaudiod` changes? [Coverage, Spec §FR-009]
- [x] CHK005 Are built-in/wired release-quality targets separated from Bluetooth pilot routes? [Consistency, Spec §FR-016]

## Requirement Clarity

- [x] CHK006 Is "ready" gated by both microphone and speaker path evidence, not publication alone? [Clarity, Spec §FR-003]
- [x] CHK007 Is self-routing rejection unambiguous for both virtual input and virtual output selections? [Clarity, Spec §FR-004]
- [x] CHK008 Are aggregate/multi-output route expectations bounded by the prior measurable-evidence rule? [Clarity, Assumptions]

## Acceptance Criteria Quality

- [x] CHK009 Are latency and leakage thresholds measurable and traceable to success criteria? [Measurability, Spec §SC-003, §SC-004]
- [x] CHK010 Is fail-closed recovery measurable before and after app relaunch? [Measurability, Spec §SC-005]
- [x] CHK011 Is `coreaudiod` restart recovery specified as stale then revalidated, not silently ready? [Measurability, Spec §SC-006]

## Edge Case Coverage

- [x] CHK012 Are permission-blocked, muted, disconnected, and empty-frame device cases covered? [Coverage, Edge Cases]
- [x] CHK013 Are stale browser device IDs after reload covered? [Coverage, Edge Cases]
- [x] CHK014 Is backend/network outage explicitly non-interfering for local passthrough? [Coverage, Spec §FR-013]

## Dependencies & Assumptions

- [x] CHK015 Does the spec identify 003 as the accepted dependency baseline? [Assumption, Spec §Assumptions]
- [x] CHK016 Does the plan preserve the existing HAL/app/shared-memory ownership boundaries? [Consistency, Plan §Summary]
