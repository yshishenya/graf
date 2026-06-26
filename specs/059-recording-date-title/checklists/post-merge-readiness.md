# Post-Merge Readiness Checklist: Recording Date And Smart Title

**Purpose**: Validate that 059 requirements and task artifacts are ready after 057/058 landed.
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the requirements and planning artifacts, not the runtime implementation.

## Merge Basis And Scope

- [x] CHK001 Is the 057/058 merge basis documented with concrete commit/PR evidence before implementation starts? [Traceability, Quickstart §Coordination Evidence]
- [x] CHK002 Is the final implementation branch policy explicit enough to avoid stacking 059 on old 057/058 worktrees? [Clarity, Quickstart §Coordination Evidence]
- [x] CHK003 Are completed coordination tasks T001/T002 backed by requirement artifacts rather than undocumented local knowledge? [Traceability, Tasks §Phase 1]

## Post-058 Architecture Alignment

- [x] CHK004 Are server touchpoint requirements aligned with the 058 rendering split across query, view-model, rendering, and template files? [Completeness, Plan §Source Code]
- [x] CHK005 Are planned-new resolver files distinguished from missing post-merge files so implementation does not treat them as drift? [Clarity, Quickstart §Coordination Evidence]
- [x] CHK006 Are `cabinet/web.py` route responsibilities excluded from requirements that belong in rendering helpers or templates? [Consistency, Tasks §US1]

## Requirement Coverage

- [x] CHK007 Is recording-date sort covered as both API/list behavior and visible web sort-control behavior? [Coverage, Spec §FR-014]
- [x] CHK008 Are title/date requirements still bounded away from calendar matching, window-title collection, and rename/export implementation after 058 added cabinet UI structure? [Consistency, Spec §FR-005-FR-008]
- [x] CHK009 Are local title provenance requirements aligned with 057 custody/idempotency so title metadata cannot become storage identity? [Consistency, Spec §FR-009-FR-012]

## Validation Readiness

- [x] CHK010 Are focused Swift and server validation commands scoped to the files and behavior 059 actually changes after 057/058 merge? [Measurability, Quickstart §Focused Checks]
- [x] CHK011 Are legacy fallback, timezone, delayed upload, duplicate title, and unsafe-title edge cases represented in requirements or quickstart scenarios? [Coverage, Spec §Edge Cases]
- [x] CHK012 Are evidence privacy requirements explicit enough to prevent raw audio, transcript text, emails, URLs, tokens, signed URLs, or private meeting content from entering committed evidence? [Security, Spec §FR-015]

## Notes

- Rechecked after fast-forwarding `codex/059-recording-date-title` to `origin/master` at `586691f`.
- No implementation behavior is claimed by this checklist.
