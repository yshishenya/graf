# Specification Analysis Report: Owner Review Live Polish

Feature: `036-owner-review-live-polish`

Date: 2026-06-22

Scope: post-implementation closeout review of `spec.md`, `plan.md`,
`tasks.md`, `.specify/memory/constitution.md`, generated readiness evidence,
and current GitHub issue state.

Prerequisite anchor:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/036-owner-review-live-polish \
  bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Result: feature directory resolved to
`specs/036-owner-review-live-polish`; available docs include `research.md`,
`data-model.md`, `contracts/`, `quickstart.md`, and `tasks.md`.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Live Owner Proof | HIGH | `tasks.md` T025-T026, `validation-log.md`, `readiness-report.md` | 036 now has browser auth/list polish and safe route evidence, but no committed metadata-only owner proof for production list/detail/governance. | Keep `web-owner-live-auth-context` open and keep `mvp_loop_ready`/pilot claims excluded until an approved owner session produces safe evidence. |
| A2 | Readiness Claim | HIGH | `readiness-report.md`, `launch-gap-register.md`, `docs/current-product-status.md` | The strongest truthful 036 claim is still `pilot_blocked`; P1 blockers remain for live owner proof, generated notes/action output or accepted pilot deferral, and production rollout evidence. | Keep bounded claim `infra_smoke_ready`; do not close pilot readiness or rollout issues from visual/auth evidence alone. |
| A3 | Desktop Evidence | MEDIUM | `tasks.md` T047, `clean-room-reference.md`, `readiness-report.md` | Visual/product polish is accepted, but the final installed-app idle/active/paused/resumed/stopped plus configured/missing-auth/local-only walkthrough evidence is still missing. | Keep T047 and its GitHub issue open until a metadata-safe walkthrough pack is committed. |
| A4 | Tracker Sync | LOW | `issues.md`, `tasks.md` T065 | The current branch reconciles tasks and readiness evidence, but several GitHub issues should only close after this closeout is committed/merged so linked evidence is visible on GitHub. | Leave T065 open until the PR/merge step, then close only issues backed by the committed evidence. |

No constitution conflicts were found. No critical blockers were introduced by the
036 closeout update.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 owner review proof | Yes | T013-T026 | Auth/session implementation is covered; final production owner proof remains open in T025-T026. |
| FR-002 list/detail/governance proof | Yes | T014-T017, T023-T026 | Fixture/local coverage exists; live owner detail/governance proof remains blocked. |
| FR-003 safe missing/invalid session state | Yes | T013-T015, T018-T021 | Covered by session dependency tests and safe recovery evidence. |
| FR-004 meeting list product labels | Yes | T038, T042 | Covered by web shell polish and tests. |
| FR-005 meeting detail truthful states | Yes | T029-T035, T038, T043 | Covered by detail rendering and notes/action state tests. |
| FR-006 no fabricated review states | Yes | T027-T035 | Covered by schema, view-model, web shell, and no-private-content tests. |
| FR-007 notes/action enum states | Yes | T027-T035, T037 | Covered; generated launchable output remains a separate readiness gap. |
| FR-008 distinguish summary/decisions/action/followups | Yes | T027-T035, T037 | Truth state artifact records the categories without private meeting output. |
| FR-009 keep readiness excluded when unavailable/deferred | Yes | T049-T055 | 036 readiness report keeps `mvp_loop_ready` excluded while notes/action output is unaccepted. |
| FR-010 installed desktop anchored to Applications | Yes | T039-T047, T060, T066 | Installed visual/auth proof exists; final capture-state walkthrough remains open in T047. |
| FR-011 V8 clean-room runtime polish | Yes | T038-T048 | Visual/product polish is accepted with remaining runtime walkthrough gap. |
| FR-012 clean-room brand distance | Yes | T048, T062 | Clean-room notes and forbidden-content scans remain metadata-safe. |
| FR-013 metadata-safe evidence | Yes | T001-T004, T024-T026, T037, T047-T048, T062 | Final scans pass for committed specs/evidence; live owner evidence remains intentionally absent. |
| FR-014 readiness report/gap update | Yes | T049-T055 | Generated 036 readiness JSON/Markdown and gap register now agree. |
| FR-015 product status/changelog update | Yes | T056-T057 | Current status and changelog now name the bounded 036 outcome. |
| FR-016 do not broaden out-of-scope claims | Yes | T049-T058, T062 | 036 keeps public-link, assisted auto-start, signed installer, and rollout claims excluded. |
| FR-017 persistent/packaged desktop cabinet configuration | Yes | T039, T044-T047, T060, T066 | Packaged/missing-auth proof exists; final state walkthrough remains open. |
| FR-018 shared cabinet base URL/session context | Yes | T039, T045, T047, T060, T066 | Local/embedded route policy is covered; live owner proof is still blocked. |
| SC-001 committed live evidence pack | Partial | T024-T026, T054-T055 | Readiness pack exists; production owner list/detail/governance proof remains open. |
| SC-002 notes/action truth coverage | Yes | T027-T037 | Truth states are covered; generated output remains unaccepted. |
| SC-003 review state recognizability | Yes | T038, T042-T043 | Covered by UI tests and evidence. |
| SC-004 desktop controls visible/usable | Partial | T039-T047, T060, T066 | Prior 035 evidence plus 036 visual proof exists; final state walkthrough remains open. |
| SC-005 clean-room zero-copy validation | Yes | T048, T062 | No private reference screenshots or copied expression are committed. |
| SC-006 forbidden-content scans | Yes | T062 | Final scan records policy-only matches and no private values. |
| SC-007 docs/status/tracker agreement | Partial | T054-T058, T064-T065 | Docs and tasks are reconciled in branch; GitHub issue closure awaits PR/merge evidence visibility. |
| SC-008 installed-app cabinet state distinction | Partial | T039, T044-T047, T060, T066 | Missing-auth/embedded login proof exists; configured/local-only walkthrough remains open. |

## Constitution Alignment Issues

None.

- Capture-first MVP integrity is preserved because 036 does not alter the
  accepted capture path and keeps native controls authoritative.
- Visible consent and user control are preserved through persistent native
  recording controls and accepted Pause/Resume/Stop evidence.
- Data boundary and secret discipline are preserved through no-token output
  tests, metadata-only evidence, and forbidden-content scans.
- Deletion truth remains bounded through existing policy lifecycle evidence.
- Spec-driven delivery is preserved by reconciling readiness, tasks, issues,
  and validation evidence before closing more GitHub issues.

## Unmapped Tasks

No problematic unmapped tasks. Remaining open tasks are intentional:

- T025-T026: live owner proof and metadata-only owner proof artifact.
- T047: installed-app capture-state and cabinet-state walkthrough evidence.
- T065: final GitHub issue closeout after committed evidence is visible.

## Metrics

- Total buildable requirements reviewed: 26
- Total tasks reviewed: 66
- Requirements with task coverage: 26
- Coverage: 100%
- Partial acceptance items: 4
- Ambiguity count: 0
- Duplication count: 0
- Critical issues count: 0
- High unresolved evidence blockers: 2

## Next Actions

- Commit/merge the 036 closeout branch before closing readiness/docs GitHub
  issues that depend on the new evidence files.
- Keep #1131/#1132 open until a safe owner session proves production
  list/detail/governance or records an explicit blocked proof artifact.
- Keep #1153 open until the installed app walkthrough pack is committed.
- Keep #1171 open until GitHub issues are actually closed with Russian closure
  comments and committed evidence links.
