# Admin Risk Checklist: Workspace Admin Panel

**Purpose**: Validate that high-risk admin, privacy, audit, metrics, and UX requirements are complete, clear, consistent, and ready for implementation.
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirement quality, not implementation behavior.

## Admin Scope And Role Requirements

- [x] CHK001 Are Owner, Admin, and Member authority boundaries fully specified for every admin page and action? [Completeness, Spec §FR-001, Spec §FR-003]
- [x] CHK002 Is the difference between Owner-only authority and Admin-managed Member authority unambiguous? [Clarity, Spec §FR-003a, Spec §FR-003b]
- [x] CHK003 Are excluded v1 roles and surfaces stated consistently across support, Analyst, billing, global superadmin, and desktop admin UI? [Consistency, Spec §FR-004, Spec §Out Of Scope]
- [x] CHK004 Are requirements defined for permission changes between page view and action submission? [Coverage, Spec §Edge Cases]
- [x] CHK005 Is workspace isolation specified for users, files, metrics, quotas, audit, and every admin action rather than only the overview page? [Completeness, Spec §FR-028]

## User Invitations And Membership

- [x] CHK006 Are invitation states and transitions complete for pending, completed, expired, revoked, duplicate, and identity-mismatch cases? [Completeness, Spec §FR-006c]
- [x] CHK007 Is the invited-user login requirement clear enough to distinguish invitation completion from direct member creation? [Clarity, Spec §FR-006a]
- [x] CHK008 Are future referral reuse requirements bounded so they do not imply rewards, campaigns, or payout logic in v1? [Consistency, Spec §FR-006b, Spec §Out Of Scope]
- [x] CHK009 Are last-owner protection requirements defined for removal, deactivation, downgrade, block, and revoke flows? [Coverage, Spec §FR-005]
- [x] CHK010 Are user detail requirements specific enough to define role, status, devices, sessions, files, usage contribution, and recent audit activity without exposing private content? [Clarity, Spec §FR-007, Spec §FR-012]

## File Governance, Egress, And Deletion

- [x] CHK011 Are admin file-access requirements explicit about same-workspace non-owned meetings and cross-workspace denial? [Completeness, Spec §FR-010, Spec §FR-028]
- [x] CHK012 Are unavailable artifact states defined for missing artifacts, active deletion, deleted state, retention or lifecycle block, and post-egress limits? [Coverage, Spec §FR-010a]
- [x] CHK013 Are sensitive egress requirements complete for review, download, export, deletion request, allowed outcomes, denied outcomes, and audit evidence? [Completeness, Spec §FR-011]
- [x] CHK014 Is deletion wording bounded to what `2brain Rec` controls and consistent with the required reason and normal destructive confirmation? [Consistency, Spec §FR-013, Spec §FR-026]
- [x] CHK015 Are excluded file governance capabilities clear enough to prevent accidental bulk export/delete, partial artifact deletion, policy override, advanced retention editing, or legal-hold scope? [Clarity, Spec §FR-014]

## Usage, Metrics, And Analytics

- [x] CHK016 Are usage and quota dimensions complete for recording minutes, storage, processing jobs, top consumers, selected period, freshness, and quota risk? [Completeness, Spec §FR-015]
- [x] CHK017 Is read-only balance language unambiguous enough to exclude quota editing and financial billing concepts? [Clarity, Spec §FR-016a, Spec §FR-017]
- [x] CHK018 Are missing, stale, display-only, and configured quota-policy states specified consistently? [Coverage, Spec §FR-016, Spec §Edge Cases]
- [x] CHK019 Are all five metric families defined with date window, denominator, freshness, source category, and drill-down requirements? [Completeness, Spec §FR-018, Spec §FR-019]
- [x] CHK020 Are incomplete-period and source-unavailable metric states defined so sample-only production numbers remain excluded? [Coverage, Spec §FR-020, Spec §FR-021]
- [x] CHK021 Can the usage and metric success criteria be objectively measured against source-backed data without adding hidden assumptions about billing or analytics roles? [Measurability, Spec §SC-005, Spec §SC-006]

## Audit, Privacy, And Data Boundary

- [x] CHK022 Are metadata-only audit requirements complete for user, invitation, role, device/session, file access, egress, deletion, quota, metric, denied, and failed sensitive actions? [Completeness, Spec §FR-008, Spec §FR-011, Spec §FR-022]
- [x] CHK023 Is audit fail-closed behavior specified for every sensitive action that requires accountability evidence? [Coverage, Spec §FR-023]
- [x] CHK024 Are requirements clear about which metadata may survive meeting deletion and which private content must not be retained? [Clarity, Spec §FR-023c]
- [x] CHK025 Is the in-product audit journal requirement consistent with the explicit exclusion of external audit/log platform integration in v1? [Consistency, Spec §FR-023a, Spec §FR-023b]
- [x] CHK026 Are secret and private-content exclusions complete across admin UI, logs, screenshots, evidence, audit details, and API contracts? [Completeness, Spec §FR-012, Plan §Constraints]

## UX, Accessibility, And Handoff

- [x] CHK027 Are Russian-first labels and deletion copy requirements specific enough for user-facing admin pages, unavailable states, and destructive actions? [Clarity, Spec §FR-026]
- [x] CHK028 Are keyboard and compact-width accessibility requirements defined for tables, filters, destructive confirmations, and common admin workflows? [Coverage, Spec §FR-027]
- [x] CHK029 Are desktop handoff and access-denied requirements clear enough to prevent a hidden full admin UI inside the native recorder? [Clarity, Spec §FR-024, Spec §FR-025]
- [x] CHK030 Are overview, users, files, balance, metrics, and audit navigation requirements consistent with the v1 scope exclusions? [Consistency, Spec §User Scenarios, Spec §Out Of Scope]
- [x] CHK031 Are usability success criteria measurable enough to evaluate locating a user, that user's files, quota contribution, and recent audit activity within the stated time? [Measurability, Spec §SC-008]

## Dependencies And Planning Consistency

- [x] CHK032 Are the planned admin module boundaries consistent with requirements that reuse auth, cabinet egress, deletion lifecycle, RLS, and metadata-only audit behavior? [Consistency, Plan §Summary, Plan §Structure Decision]
- [x] CHK033 Are data-model requirements complete for invitations, read-only quota policy, usage rollups, admin audit events, and normalized audit journal entries? [Completeness, Plan §Project Structure]
- [x] CHK034 Are validation-lane requirements aligned with the high-risk admin/auth/privacy/deletion/Postgres/RLS scope? [Consistency, Plan §Risk / Validation Lane]
- [x] CHK035 Are performance and bounded-list requirements specified enough to avoid ambiguous unbounded admin queries during implementation planning? [Clarity, Plan §Performance Goals]

## Notes

- Check items off only after reviewing the requirements text, not after implementation.
- Add findings inline when a requirement needs clarification before `$speckit-tasks`.
- 2026-06-27 review: all 35 items were rechecked against `spec.md`,
  `plan.md`, `data-model.md`, `contracts/`, `quickstart.md`, and `tasks.md`.
  Before marking this checklist complete, `spec.md` was tightened for
  last-owner block/revoke coverage, explicit audit journal source coverage, and
  Russian-first copy for admin pages, unavailable states, and destructive
  actions.
