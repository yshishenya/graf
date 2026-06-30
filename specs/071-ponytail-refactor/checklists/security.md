# Security Checklist: Ponytail Refactor Audit

**Purpose**: Requirement-quality gate for auth, privacy, deletion, diagnostics, and secret-safety cleanup.
**Created**: 2026-06-30
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are auth, session, device, permission, audit, privacy, deletion, diagnostics, and secret-handling boundaries explicitly protected from behavior-changing cleanup? [Spec §FR-006]
- [x] CHK002 Are framework and adapter contract signatures treated as in-use unless proven otherwise? [Spec §FR-007]
- [x] CHK003 Are dependency removal requirements strong enough to cover runtime-only and CLI-only security dependencies? [Spec §FR-005, Spec §FR-012]

## Requirement Clarity

- [x] CHK004 Is "unused" defined with both source/caller evidence and validation evidence rather than static analysis alone? [Spec §FR-005]
- [x] CHK005 Is the rule for retaining suspicious high-risk candidates clear and testable? [Spec §FR-014]

## Scenario Coverage

- [x] CHK006 Are negative scenarios covered for dependencies, entrypoints, side-effect imports, and safety tests that appear unused? [Spec §Edge Cases]
- [x] CHK007 Are dirty-worktree preservation requirements explicit enough to avoid accidental deletion or staging of unrelated security-sensitive files? [Spec §FR-004]

## Notes

- This checklist validates requirement quality only; implementation validation is listed in `quickstart.md`.
