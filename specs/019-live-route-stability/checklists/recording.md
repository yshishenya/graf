# Recording Timeline Checklist: Live Route Stability

**Purpose**: Validate recording timeline and manifest-truth requirement quality before task generation.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and planning artifacts, not implementation behavior.

## Timeline Alignment

- [x] CHK001 Are accepted, degraded/warning, and failed timeline bands specified consistently across spec, data model, contracts, and quickstart? [Consistency, Spec §Timeline Integrity Rule, Data Model §TimelineAlignmentBand, Contract §Recording Timeline Evidence]
- [x] CHK002 Are `<= 3 seconds`, `> 3` and `<= 10 seconds`, and `> 10 seconds` thresholds measurable enough for future tasks and release evidence? [Measurability, Spec §FR-033, Spec §SC-014, Spec §SC-015, Spec §SC-016]
- [x] CHK003 Are tens/minutes duration differences explicitly classified as route-stability bugs unless superseded by a future accepted spec? [Clarity, Spec §FR-034]

## Manifest Truth

- [x] CHK004 Are manifest requirements complete enough to distinguish route interruption from generic `timeline_misaligned` failures? [Completeness, Spec §FR-016, Research §Recording Timeline Evidence]
- [x] CHK005 Are route interruption categories sufficiently specific for incoming route stop, microphone route stop, both-route stop, Core Audio restart, default-route change, browser recreation, and unknown gap? [Coverage, Contract §Recording Timeline Evidence]
- [x] CHK006 Are requirements clear that degraded/warning artifact evidence cannot count as clean acceptance even if live audio seemed usable? [Clarity, Spec §SC-003, Quickstart §Recording Timeline Validation]

## Recording During Autorepair

- [x] CHK007 Are autorepair-while-recording requirements complete enough to prevent hidden timeline gaps, corrupted alignment, lost indicator state, or loss of one-action stop? [Completeness, Spec §FR-030]
- [x] CHK008 Are route session and autorepair correlation requirements complete for attaching route facts to final recording evidence? [Traceability, Data Model §RecordingTimelineIntegrityEvidence, Contract §Recording Timeline Evidence]
- [x] CHK009 Are frame continuity requirements sufficient to explain recovered route gaps without storing raw audio or meeting content? [Privacy, Spec §FR-019, Data Model §FrameContinuitySnapshot]

## Acceptance Readiness

- [x] CHK010 Are accepted recording-run requirements complete for both `mic.wav` and `incoming.wav` existence, duration, alignment band, and diagnostic-safe evidence? [Completeness, Quickstart §Recording Timeline Validation]
- [x] CHK011 Are failed and diagnostic recording runs allowed to preserve evidence without being counted as clean acceptance? [Consistency, Spec §SC-003, Contract §Recording Timeline Evidence]
- [x] CHK012 Are recording timeline requirements scoped to route stability rather than speaker-to-mic leakage or transcription quality? [Scope, Spec §Scope Boundary]
