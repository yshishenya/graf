# Security And Privacy Checklist: Manual Capture Session And Visible Indicator

**Purpose**: Validate security, privacy, and data-boundary requirement quality before implementation
**Created**: 2026-06-01
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are no-upload/no-transcription/no-MediaScribe/no-Langfuse/no-dashboard boundaries explicit? [Completeness, Spec §FR-011]
- [x] CHK002 Are forbidden diagnostic/evidence content classes listed explicitly? [Completeness, Spec §FR-015]
- [x] CHK003 Are metadata-only recording evidence requirements defined for start, stop, failure, and blocked starts? [Completeness, Spec §FR-010]
- [x] CHK004 Are local policy and permission blockers required before recording start? [Completeness, Spec §FR-001, FR-007]
- [x] CHK005 Is assisted auto-start explicitly out of scope to prevent hidden capture expansion? [Completeness, Spec §FR-016]

## Requirement Clarity

- [x] CHK006 Is "manual start" unambiguous as explicit local user action only? [Clarity, Spec §Clarifications]
- [x] CHK007 Is "metadata-only evidence" defined by allowed/forbidden content, not vague privacy language? [Clarity, Contract recording-evidence]
- [x] CHK008 Are blocked start reasons required to be concrete and user-facing? [Clarity, Spec §FR-014]
- [x] CHK009 Is the recording boundary distinguished from non-recording passthrough across UI, diagnostics, and evidence? [Clarity, Spec §FR-005]

## Consistency And Coverage

- [x] CHK010 Do evidence requirements align with the constitution's deletion truth and lifecycle accounting rules? [Consistency, Constitution §IV]
- [x] CHK011 Do data-boundary requirements preserve the desktop-never-sends-to-MediaScribe rule? [Consistency, Constitution §III]
- [x] CHK012 Are crash, bridge loss, `coreaudiod` restart, storage, and indicator-loss failure paths covered as privacy/safety risks? [Coverage, Spec §Edge Cases]
- [x] CHK013 Are success criteria measurable for invisible recording, blocked starts, and redaction? [Measurability, Spec §SC-001..SC-007]
