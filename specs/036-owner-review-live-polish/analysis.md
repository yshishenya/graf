# Specification Analysis Report: Owner Review Live Polish

Feature: `036-owner-review-live-polish`

Date: 2026-06-16

Scope: `spec.md`, `plan.md`, `tasks.md`,
`.specify/memory/constitution.md`, and supporting design artifacts.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Auth Boundary | LOW | `research.md`, `tasks.md` T018-T023 | The implementation will add browser-safe owner review session handling, which is the highest-risk part of the slice, but tasks correctly bind it to existing `AuthSession`, device, workspace, and cleanup rules. | Proceed, but keep T013-T017 red-first and do not implement any unauthenticated debug/backdoor route. |
| A2 | Readiness Claim | LOW | `spec.md` FR-009, `tasks.md` T052-T058 | Notes/action output may remain unavailable or deferred, and the artifacts consistently require `mvp_loop_ready` to stay excluded if that happens. | Proceed; implementation must not close `notes-action-output` unless stored output or accepted deferral evidence exists. |

No critical, high, or medium consistency issues were found.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 owner review proof | Yes | T013-T026 | Covers live owner session proof and sanitized evidence. |
| FR-002 list/detail/governance proof | Yes | T014-T017, T023-T026 | Allows ready, empty, blocked, or deferred proof state. |
| FR-003 safe missing/invalid session state | Yes | T013-T015, T018-T021 | Covered through web session dependency tests and implementation. |
| FR-004 meeting list product labels | Yes | T038, T042 | Covered in web shell polish and tests. |
| FR-005 meeting detail truthful states | Yes | T029-T035, T038, T043 | Covered by notes/action and detail rendering tasks. |
| FR-006 no fabricated review states | Yes | T027-T035 | Covered by schema, view-model, and web shell tests. |
| FR-007 notes/action enum states | Yes | T027-T035 | Covered by contract and implementation tasks. |
| FR-008 distinguish summary/decisions/action/followups | Yes | T027-T035 | Available output requires stored data. |
| FR-009 keep readiness excluded when unavailable/deferred | Yes | T049-T058 | Covered by readiness matrix/report tasks. |
| FR-010 installed desktop anchored to Applications | Yes | T039-T047, T060, T066 | Covered by desktop tests and runtime proof. |
| FR-011 V8 clean-room runtime polish | Yes | T038-T048 | Covered by web/desktop polish tasks and evidence. |
| FR-012 clean-room brand distance | Yes | T048, T062 | Covered by reference notes and forbidden scans. |
| FR-013 metadata-safe evidence | Yes | T001-T004, T024-T026, T037, T047-T048, T062 | Covered across evidence scaffolding and scans. |
| FR-014 readiness report/gap update | Yes | T049-T058 | Covered by readiness and doc tasks. |
| FR-015 product status/changelog update | Yes | T056-T057 | Covered directly. |
| FR-016 do not broaden out-of-scope claims | Yes | T049-T058, T062 | Covered by readiness claim and scan tasks. |
| SC-001 committed live evidence pack | Yes | T024-T026, T054-T055 | Covered by owner proof and readiness artifacts. |
| SC-002 notes/action truth coverage | Yes | T027-T037 | Covered by schema, view model, web, fixtures, and evidence. |
| SC-003 quick recognition of review states | Yes | T038, T042-T043 | Covered by web IA tests and polish. |
| SC-004 desktop controls visible/usable | Yes | T039-T047, T060, T066 | Covered by Swift tests and installed-app proof. |
| SC-005 clean-room zero-copy validation | Yes | T048, T062 | Covered by clean-room evidence and scan. |
| SC-006 forbidden-content scans | Yes | T062 | Covered directly. |
| SC-007 docs/status/tracker agreement | Yes | T054-T058, T064-T065 | Covered by readiness/docs/analyze/issues tasks. |

## Constitution Alignment Issues

None.

- Capture-first MVP integrity is preserved because 036 does not alter the
  accepted capture path and requires native controls to stay authoritative.
- Visible consent and user control are preserved through desktop control
  visibility tasks.
- Data boundary and secret discipline are preserved through session cleanup,
  no-token-output tests, and forbidden-content scans.
- Deletion truth remains bounded through governance/readiness tasks.
- Spec-driven delivery is satisfied through specify, clarify, plan, checklist,
  tasks, analyze, task-to-issue sync, and implementation gates.

## Unmapped Tasks

No problematic unmapped tasks. Setup and polish tasks map to evidence,
validation, or tracker closeout rather than a single FR, which is expected.

## Metrics

- Total buildable requirements reviewed: 23
- Total tasks reviewed: 66
- Requirements with task coverage: 23
- Coverage: 100%
- Ambiguity count: 0 blocking, 1 low-risk implementation attention area
- Duplication count: 0
- Critical issues count: 0
- High issues count: 0
- Medium issues count: 0

## Next Actions

- Proceed to `$speckit-taskstoissues`.
- Keep US1 tests red-first before changing auth/session behavior.
- Implementation is blocked only if owner-review proof requires bypassing
  existing AuthSession/RLS/device validation or committing secret/private
  evidence.
