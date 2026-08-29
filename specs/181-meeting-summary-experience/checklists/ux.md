# UX and accessibility requirements quality checklist

**Purpose**: Validate summary review, format selection, recovery and accessibility requirements before implementation
**Created**: 2026-08-21
**Feature**: [spec.md](../spec.md)

## Information Architecture And Interaction

- [x] CHK001 Is outcome-first hierarchy distinguished from detailed evidence and transcript content? [Clarity, Spec §FR-011]
- [x] CHK002 Are current format, selected pending format and candidate format required to remain distinguishable? [Completeness, Spec §FR-015, §FR-019]
- [x] CHK003 Does format selection state that it creates a new reviewable variant rather than merely switching presentation? [Clarity, Spec User Story 2, §FR-016]
- [x] CHK004 Are accept, keep current, reject and choose-another-format outcomes separately defined? [Completeness, Spec §FR-017]
- [x] CHK005 Are quick picker and full catalog required to expose consistent names, purposes and current selection? [Consistency, Spec §FR-015]

## State And Recovery Coverage

- [x] CHK006 Are first-generation pending/error states defined without mock content? [Coverage, Spec §FR-009A–FR-009C]
- [x] CHK007 Are generating, slow/extended wait, ready, preview unavailable, stale, expired and terminal paths covered by a safe next action? [Coverage, Spec §FR-019–FR-023, Edge Cases]
- [x] CHK008 Is restoration after reload/background explicitly required? [Completeness, Spec §FR-022]
- [x] CHK009 Is the all-empty meeting-level outcome specified without filler? [Clarity, Spec §FR-009]
- [x] CHK010 Is current accepted content required to remain available during generation and errors? [Consistency, Spec §FR-016, §FR-020]

## Accessibility And Parity

- [x] CHK011 Are keyboard access, labels and predictable focus return defined for the complete candidate lifecycle? [Coverage, Spec §FR-027]
- [x] CHK012 Are dynamic status announcements required without unexpected focus movement? [Clarity, Spec §FR-028]
- [x] CHK013 Is 200% zoom and narrow-window reflow objectively required? [Measurability, Spec §FR-029, §SC-009]
- [x] CHK014 Are browser and embedded macOS parity requirements explicit for content, format, status and actions? [Consistency, Spec §FR-026, §SC-008]
- [x] CHK015 Is exact source navigation plus return to the prior summary context specified? [Completeness, Spec §FR-025]

## Evaluation Quality

- [x] CHK016 Are all built-in formats, buttons, transitions, retries, acceptance and rejection included in measurable UX validation? [Coverage, Spec §SC-007–SC-009]
- [x] CHK017 Are clean-room and brand-distance assumptions preserved while allowing category comparison with Krisp? [Boundary, Spec Assumptions]
