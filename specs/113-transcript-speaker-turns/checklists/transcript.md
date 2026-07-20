# Transcript Requirements Checklist: Canonical Speaker Turns

**Purpose**: Validate that speaker-turn requirements are complete, clear, and safe before implementation
**Created**: 2026-07-20
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are the review user journey and the provider-switch journey both specified as independently valuable stories? [Completeness, Spec §User Scenarios & Testing]
- [x] CHK002 Are raw segments, derived turns, and their relationship explicitly defined? [Completeness, Spec §Key Entities]
- [x] CHK003 Are out-of-scope items stated so that provider replacement, diarization tuning, and persistence expansion cannot be inferred as hidden work? [Completeness, Spec §Out of Scope]

## Boundary and Clarity

- [x] CHK004 Is the merge predicate unambiguous about speaker, processing result/run, source role, ordering, and the inclusive 1-second pairwise gap? [Clarity, Spec §FR-002]
- [x] CHK005 Is text joining defined without changing the raw source text? [Clarity, Spec §FR-003, Spec §FR-004]
- [x] CHK006 Are speaker changes, long pauses, unknown labels, malformed timing, empty text, and overlapping intervals addressed? [Coverage, Spec §Edge Cases]

## Contract and Compatibility

- [x] CHK007 Does the specification require an additive provider-neutral contract while preserving the existing raw segment field? [Consistency, Spec §FR-003, Spec §FR-007, Spec §FR-010]
- [x] CHK008 Is the client/server/provider boundary explicit enough to prevent client-side or MediaScribe-specific merge logic? [Clarity, Spec §FR-007]
- [x] CHK009 Are deterministic rebuild and idempotence requirements measurable for legacy results and retries? [Measurability, Spec §FR-006, Spec §FR-008]

## Safety and Lifecycle

- [x] CHK010 Does the specification prevent a display fallback from inventing a mergeable speaker identity? [Safety, Spec §FR-009]
- [x] CHK011 Are incomplete or non-terminal processing states prevented from publishing final derived turns? [Recovery, Spec §FR-011]
- [x] CHK012 Is the deletion/retention relationship for derived data stated without promising external erasure? [Lifecycle, Spec §Assumptions]
- [x] CHK013 Are privacy constraints explicit for diagnostics, fixtures, provider credentials, and meeting content? [Privacy, Spec §FR-007, Spec §Assumptions]

## Acceptance and Traceability

- [x] CHK014 Can each success criterion be validated from synthetic fixtures without knowing the implementation? [Measurability, Spec §Success Criteria]
- [x] CHK015 Does the acceptance coverage include playback timing and readable rendering, not only the data shape? [Scenario Coverage, Spec §US1]
- [x] CHK016 Is the one-second threshold identified as an assumption/policy that can be tuned without changing the provider contract? [Assumption, Spec §Assumptions]

## Notes

- Standard reviewer depth is sufficient for this slice; implementation correctness belongs to the tasks and test plan.
