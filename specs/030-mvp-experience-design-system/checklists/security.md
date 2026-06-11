# Security And Privacy Requirements Checklist: MVP Product Experience And Design System

**Purpose**: Validate that privacy, security, data-boundary, deletion-truth, external-tool, and content-safety requirements are complete, clear, measurable, and consistent before task generation.
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirement quality only. It does not verify implementation, deployment, or runtime controls.

## Requirement Completeness

- [ ] CHK001 Are requirements complete for keeping capture-critical state, Stop, recording indicator, permission state, local artifact truth, upload queue truth, and recovery actions outside server-loaded UI ownership? [Completeness, Spec §FR-003, Spec §FR-007]
- [ ] CHK002 Are requirements complete for forbidding secrets, credentials, tokens, signed URLs, raw audio, transcript text from real meetings, passwords, and live local paths in design/prototype/handoff artifacts? [Completeness, Plan §Constraints, Contract prototype-handoff]
- [ ] CHK003 Are requirements complete for desktop never receiving MediaScribe credentials, object-storage credentials, or direct third-party upload paths in this experience model? [Completeness, Spec §FR-020, Plan §Constraints]
- [ ] CHK004 Are requirements complete for separating upload success, audio extraction, transcription, transcript readiness, notes readiness, deletion, and access truth? [Completeness, Spec §FR-029, Contract cross-surface-status]
- [ ] CHK005 Are deletion/access entry-point requirements complete enough to preserve the constitution language "Delete this meeting everywhere 2brain Rec controls"? [Completeness, Constitution §IV, Spec §FR-020]
- [ ] CHK006 Are requirements complete for external prototype tools, including Figma and StitchFlow, to avoid storing sensitive product secrets or real private meeting content? [Completeness, Spec §FR-022-FR-025, Contract prototype-handoff]

## Requirement Clarity

- [ ] CHK007 Is the data boundary between local desktop, Rec server, MediaScribe, Langfuse, MinIO, Postgres, and external design tools stated clearly for design and prototype artifacts? [Clarity, Plan §Constraints, Constitution §III]
- [ ] CHK008 Are "metadata-only", "content-safe", and "source/status provenance" defined clearly enough for prototype and handoff requirements? [Clarity, Spec §FR-028, Contract prototype-handoff]
- [ ] CHK009 Is the user-facing deletion language requirement precise enough to avoid universal-erasure claims outside 2brain Rec control? [Clarity, Constitution §IV, Contract cross-surface-status]
- [ ] CHK010 Are browser-only route handoffs clear about access boundaries without revealing private meeting metadata to unauthorized viewers? [Clarity, Contract route-visibility, Contract cross-surface-status]
- [ ] CHK011 Are access-denied requirements defined without leaking meeting content or sensitive metadata beyond policy? [Clarity, Contract cross-surface-status]
- [ ] CHK012 Are requirements clear that copied Krisp screenshots, assets, copy, icons, or proprietary behavior must not appear in product/prototype artifacts? [Clarity, Spec §FR-016-FR-017]

## Requirement Consistency

- [ ] CHK013 Are privacy requirements consistent between the constitution, spec, plan, and prototype handoff contract? [Consistency, Constitution §III-IV, Spec §FR-020, Plan §Constraints]
- [ ] CHK014 Are deletion-truth requirements consistent between meeting review, cross-surface status, edge cases, and future retention/deletion slices? [Consistency, Spec §SC-005, Spec §SC-013, Contract cross-surface-status]
- [ ] CHK015 Are Figma/StitchFlow fallback requirements consistent with the rule that repo Spec Kit artifacts remain the product source of truth? [Consistency, Spec §FR-025, Contract prototype-handoff]
- [ ] CHK016 Are access, sharing, downloads, broad admin, audit, and legal/help requirements consistently deferred or handoff-only for the first prototype? [Consistency, Spec §FR-030, Contract route-visibility]
- [ ] CHK017 Are MediaScribe processing states represented as server-side status truth without moving dependency credentials or direct egress to desktop/prototype artifacts? [Consistency, Spec §FR-029, Plan §Primary Dependencies]

## Acceptance Criteria Quality

- [ ] CHK018 Can "zero copied Krisp assets/UI/copy/icons/proprietary behavior" be objectively evaluated through the brand-distance gate? [Measurability, Spec §SC-009]
- [ ] CHK019 Can "100% external design/prototype artifacts have matching repo handoff references" be objectively evaluated without requiring access to secrets or private data? [Measurability, Spec §SC-012]
- [ ] CHK020 Can "100% launch-critical prototype paths show the same status in desktop and web" be objectively evaluated for privacy-relevant states such as deleted and access denied? [Measurability, Spec §SC-013]
- [ ] CHK021 Are acceptance criteria defined for failure/degraded states that avoid exposing raw transcript or meeting content in status, diagnostics, or handoff? [Acceptance Criteria, Spec §SC-014]
- [ ] CHK022 Are security/privacy success criteria stated as requirements-quality gates rather than implementation checks? [Acceptance Criteria, Spec §SC-009-SC-015]

## Scenario Coverage

- [ ] CHK023 Are requirements defined for server/cabinet unavailability while local recording remains available by policy? [Coverage, Spec §Edge Cases]
- [ ] CHK024 Are requirements defined for app/web disagreement about upload, transcription, meeting review, deletion, or access status? [Coverage, Spec §Edge Cases, Contract cross-surface-status]
- [ ] CHK025 Are requirements defined for user sign-out, session recovery, auth-blocked upload, and account/workspace status without implying local deletion or upload completion? [Coverage, Spec §FR-005, Spec §US2]
- [ ] CHK026 Are requirements defined for unsupported, corrupted, encrypted, duplicate, oversized, no-audio, and partial media upload cases without leaking file content? [Coverage, Spec §Edge Cases]
- [ ] CHK027 Are requirements defined for processing partial success, such as transcript ready but notes failed, with truthful status and no hidden content exposure? [Coverage, Spec §Edge Cases, Spec §FR-014]
- [ ] CHK028 Are requirements defined for future deletion accounting across local buffers, server objects, backups, processing dependencies, diagnostics, and external dependency limits? [Coverage, Spec §Edge Cases, Constitution §IV]

## Dependencies And Assumptions

- [ ] CHK029 Are dependencies on already implemented `014` desktop upload and `015` processing documented as context rather than new implementation scope? [Dependency, Plan §Technical Context, Research §Owner Value Loop]
- [ ] CHK030 Are assumptions about Figma free-plan delivery and StitchFlow fallback documented with safe evidence requirements? [Assumption, Plan §Primary Dependencies, Contract prototype-handoff]
- [ ] CHK031 Are requirements clear that `016+` dashboard/access/deletion work may later implement surfaces but this design slice does not authorize production code? [Scope, Spec §FR-031, Plan §Summary]
- [ ] CHK032 Are external dependency limitations for MediaScribe/Langfuse/deletion represented in copy/status requirements rather than left for implementation teams to infer? [Dependency, Constitution §III-IV, Spec §FR-020]

## Ambiguities And Conflicts

- [ ] CHK033 Is there any conflict between showing useful prototype sample content and forbidding real private meeting content in artifacts? [Conflict, Contract prototype-handoff]
- [ ] CHK034 Is "owner-controlled" used consistently for server infrastructure and external dependencies without implying no egress when MediaScribe is enabled? [Ambiguity, Constitution §III, Plan §Constraints]
- [ ] CHK035 Are security/privacy review responsibilities clearly assigned to checklists and handoff gates before tasks are generated? [Traceability, Plan §Testing, Quickstart §8]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline.
- These items validate requirements quality, not implementation behavior.
