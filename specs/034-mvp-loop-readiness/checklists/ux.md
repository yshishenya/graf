# UX Requirements Checklist: MVP Loop Readiness

**Purpose**: Validate that UX requirements are complete, clear, measurable, and clean-room before implementation
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are desktop first-surface requirements defined for both configured and unavailable cabinet states? [Completeness, Spec §US2, FR-006]
- [x] CHK002 Are native capture authority requirements defined separately from embedded web review requirements? [Completeness, Spec §FR-005, FR-015]
- [x] CHK003 Are web and embedded cabinet review surfaces enumerated with list, detail, transcript, playback, notes, and governance expectations? [Completeness, Spec §FR-008]
- [x] CHK004 Are lifecycle and governance states defined for ready, processing, failed, partial, deleting, deleted, denied, policy-gated, and local purge conditions? [Completeness, Spec §FR-017]

## Requirement Clarity

- [x] CHK005 Is "meeting workspace" constrained enough to avoid accepting a diagnostics-first surface as launchable? [Clarity, Spec §US2, FR-006]
- [x] CHK006 Are readiness claim boundaries clear enough that UI evidence cannot imply pilot or production readiness by accident? [Clarity, Spec §FR-011]
- [x] CHK007 Are screenshot evidence requirements explicit about live, local runtime, synthetic, blocked, and unavailable states? [Clarity, Spec §FR-004, SC-002]

## Requirement Consistency

- [x] CHK008 Do desktop and web ownership requirements align with ADR 001 and the server-owned cabinet strategy? [Consistency, Spec §FR-015, Plan §Constitution Check]
- [x] CHK009 Are reference-alignment requirements consistent with clean-room constraints across spec, plan, and reference contract? [Consistency, Spec §FR-009, Contract §Reference Comparison]

## Acceptance Criteria Quality

- [x] CHK010 Can the desktop UX readiness requirement be objectively verified through screenshots or explicit blocker evidence? [Measurability, Spec §SC-002]
- [x] CHK011 Can a reviewer determine the readiness outcome from the report in a bounded time? [Measurability, Spec §SC-008]

## Edge Case Coverage

- [x] CHK012 Are unavailable/auth/expired/denied cabinet states covered as requirements rather than left to implementation judgment? [Coverage, Spec §Edge Cases, US2]
- [x] CHK013 Are stale detail/list states after deletion or processing transitions represented in the requirements? [Coverage, Spec §Edge Cases]

## Ambiguities And Conflicts

- [x] CHK014 Are there no unresolved UX terms such as "polished", "intuitive", or "ready" without bounded criteria? [Ambiguity, Spec §Requirements, Success Criteria]
