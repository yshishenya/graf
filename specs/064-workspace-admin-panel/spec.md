# Feature Specification: Workspace Admin Panel

**Feature Branch**: `codex/064-workspace-admin-panel`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "Workspace admin panel for creating and monitoring users, balance/quotas, user files, detailed statistics, product metrics, and audit. V1 has no support role, no Analyst role, no billing/payments, and no internal global superadmin UI."

## Clarifications

### Session 2026-06-27

- Q: How should Owner/Admin add a new user in v1? → A: Admin creates an invite/onboarding request, and the user completes login through an allowed provider. The invite mechanism should be reusable later for referrals, but referral rewards/campaign mechanics are out of v1.
- Q: What should v1 do with balance and limits? → A: V1 is read-only monitoring. Owner/Admin can see usage, configured limits, top consumers, and quota risk, but cannot change limits from the admin panel.
- Q: What can Owner/Admin see in other users' files and meetings? → A: Owner/Admin can open review, download, export, and request deletion for any server-known meeting in their workspace. Every sensitive action still requires current role/workspace checks, metadata-only audit, and deletion confirmation where applicable.
- Q: How should admin meeting deletion be confirmed in v1? → A: Admin deletion requires a normal destructive action confirmation and a required reason, but not a typed confirmation phrase.
- Q: Should v1 connect a ready-made audit/log platform? → A: V1 keeps one product audit journal inside the admin panel and leaves room for future export to an owner-controlled observability/log system, but does not connect an external audit/log platform now.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open Workspace Admin Overview (Priority: P1)

A workspace Owner or Admin opens the admin panel and sees a compact overview of workspace health: user state, quota/usage risk, file/processing health, metric freshness, and recent sensitive activity. A Member cannot open the admin panel.

**Why this priority**: This is the smallest safe vertical slice. It proves the admin surface exists, is workspace-scoped, and enforces the role boundary before any destructive action is added.

**Independent Test**: Can be tested by signing in as Owner, Admin, and Member in the same workspace and verifying that Owner/Admin see the overview while Member is denied without seeing workspace data.

**Acceptance Scenarios**:

1. **Given** an active Owner in a workspace, **When** they open the admin panel, **Then** they see overview cards for users, usage, files, metrics freshness, and recent audit activity for that workspace only.
2. **Given** an active Admin in a workspace, **When** they open the admin panel, **Then** they see the same workspace-scoped overview except actions reserved for Owner authority.
3. **Given** an active Member, **When** they attempt to open any admin page, **Then** access is denied and no admin data is exposed.
4. **Given** a user belongs to one workspace, **When** they inspect admin overview data, **Then** no users, files, metrics, quotas, or audit events from another workspace are visible.

---

### User Story 2 - Manage Workspace Users (Priority: P1)

An Owner or Admin reviews users, creates invitations for new users, changes allowed roles/states, inspects devices/sessions, and sees each user's usage and recent activity. Invited users complete login through an allowed provider before becoming active workspace members. Owner authority controls Owner/Admin role assignment; Admins can manage Members within policy but cannot grant or revoke Owner/Admin authority. The system prevents loss of the last Owner.

**Why this priority**: User administration is the core admin job and the prerequisite for trustworthy file, quota, and metric ownership.

**Independent Test**: Can be tested by creating an invitation, completing the invited user's login through an allowed provider, changing that user's role/state within allowed bounds, attempting to downgrade the last Owner, and confirming the user list/detail/audit reflects the outcome.

**Acceptance Scenarios**:

1. **Given** an Owner, **When** they invite a user, **Then** the user appears with a clear pending state and an auditable source of invitation.
2. **Given** an invited new user, **When** they complete login through an allowed provider, **Then** they become an active workspace member with the invited role and the invitation is linked to the completed membership.
3. **Given** an invited identity already has a workspace membership, **When** they complete the invitation, **Then** the invitation is linked but their existing role and status are not changed by invite completion.
4. **Given** an Admin, **When** they manage a Member, **Then** allowed state changes are applied and audited.
5. **Given** an Admin, **When** they try to grant Owner/Admin authority or remove Owner/Admin authority, **Then** the action is blocked with a clear reason.
6. **Given** an Owner, **When** they change Owner/Admin/Member role authority, **Then** the change is applied only if the workspace keeps at least one active Owner and the action is audited.
7. **Given** a user detail page, **When** Owner/Admin opens it, **Then** it shows role, status, devices, sessions, files, usage contribution, and recent audit activity.

---

### User Story 3 - Govern User Files (Priority: P2)

An Owner or Admin searches workspace files/meetings by owner, type, date, state, processing result, retention/deletion state, and size/duration. They can open review, download/export allowed artifacts, and request whole-meeting deletion for any server-known meeting in their workspace. Full workspace-admin file access does not bypass missing-artifact, deletion, retention, or product safety states. Each sensitive action is audited.

**Why this priority**: File governance is high value and high risk. It must be useful enough for real administration while preserving privacy, deletion truth, and auditability.

**Independent Test**: Can be tested by using an admin account to find a non-owned meeting in the same workspace, performing an allowed review/export/download/delete action, and confirming current permission checks, metadata-only audit, and deletion report state.

**Acceptance Scenarios**:

1. **Given** an Admin viewing files, **When** they filter by owner, date, file state, or processing state, **Then** the list updates within the selected workspace and shows enough metadata to choose the next action.
2. **Given** a non-owned meeting in the same workspace, **When** an Admin opens review, download, export, or delete, **Then** the action is allowed after current workspace admin permission is confirmed.
3. **Given** an allowed download or export, **When** it completes, **Then** the action writes a metadata-only audit event and does not expose raw storage identifiers, signed URLs, local paths, tokens, secrets, raw audio, or transcript text in admin logs or evidence.
4. **Given** an allowed deletion request, **When** Admin confirms the destructive action and provides a reason, **Then** the system requests deletion of the whole meeting everywhere `2brain Rec` controls and shows a bounded deletion report.
5. **Given** local-only desktop files or buffers, **When** Admin views file state, **Then** the admin panel shows only metadata-safe sync/purge state and never raw local paths.
6. **Given** an artifact is unavailable, deleted, blocked by lifecycle state, or outside `2brain Rec` control, **When** Admin attempts review, download, export, or deletion, **Then** the admin panel shows the truthful unavailable state instead of overriding it.

---

### User Story 4 - Monitor Usage And Quotas (Priority: P2)

An Owner or Admin sees quota and usage health for recording minutes, storage, processing jobs, and top consumers. V1 shows quota/usage state and risk as read-only monitoring; changing limits from the admin panel is excluded. Financial billing, credit ledgers, invoices, tariffs, and payments are also excluded.

**Why this priority**: Admins need to find quota and usage problems before users are blocked, but billing is a separate product feature.

**Independent Test**: Can be tested by seeding users and files with different usage profiles, opening balance/limits, and verifying totals, top consumers, time windows, freshness, and quota-risk labels reconcile to source data.

**Acceptance Scenarios**:

1. **Given** workspace usage exists, **When** Owner/Admin opens balance/limits, **Then** they see recording minutes, storage, processing jobs, usage by user, and top consumers for a selected period.
2. **Given** quota policy exists for the workspace, **When** usage approaches or exceeds a limit, **Then** the panel labels the risk and identifies affected users/files.
3. **Given** quota policy is not configured, **When** Owner/Admin opens balance/limits, **Then** the panel says limits are not configured instead of inventing limits.
4. **Given** Owner/Admin opens balance/limits, **When** they look for limit-editing controls, **Then** the UI makes clear that v1 is read-only monitoring and limits are managed outside this admin panel.
5. **Given** the user expects financial balance, **When** they open v1 balance/limits, **Then** the UI makes clear that money, tariffs, invoices, debt, and credit ledger are not part of v1.

---

### User Story 5 - Analyze Product Metrics And Audit (Priority: P3)

An Owner or Admin opens product metrics for adoption/activity, usage/quotas, recording-to-processing funnel, reliability/quality, and governance. Each metric shows definition, freshness, and drill-down to relevant users/files/actions. The single product audit journal lets them inspect auth, user, file, export, deletion, quota, and admin-action events. Future technical log export must not replace this product audit journal.

**Why this priority**: Metrics and audit complete the control-room model, but they should build on safe user/file/usage foundations.

**Independent Test**: Can be tested by generating known user/file/action events, opening metrics and audit, and confirming each displayed number and event reconciles to the expected source and date window.

**Acceptance Scenarios**:

1. **Given** product activity exists, **When** Owner/Admin opens metrics, **Then** all five metric families are present with date window, freshness, definition, and drill-down.
2. **Given** recent data may still be incomplete, **When** Owner/Admin views current-period metrics, **Then** incomplete periods are clearly marked.
3. **Given** audit events exist, **When** Owner/Admin filters the single product audit journal by user, action, object, outcome, or period, **Then** matching metadata-only events are shown without private meeting content.
4. **Given** no source-backed data exists for a metric, **When** Owner/Admin opens metrics, **Then** the metric is absent or explicitly unavailable; sample-only production numbers are not shown.

### Edge Cases

- Owner/Admin loses permission between page render and action submission.
- Workspace has no users beyond the current Owner.
- The last Owner is deactivated, downgraded, or removed.
- A user exists in the organization but has no active workspace membership.
- An invitation is expired, revoked, duplicated, or completed by a login identity that does not match the invitation.
- Admin attempts to inspect or export a meeting outside their workspace.
- A meeting is already deleting, deleted, retained by policy, or blocked by post-egress limits.
- A workspace user invitation is confused with an external meeting-recipient invitation or public meeting link.
- Quota policy is missing, stale, or not enforceable for the selected period.
- Current-day metrics are incomplete because upload or processing is still lagging.
- Audit persistence is unavailable during a sensitive action.
- A desktop client is offline, unreachable, or has only local metadata for files/purge state.
- An admin deep link is opened inside the desktop app.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a workspace-scoped admin panel for active Owners and Admins only.
- **FR-002**: The system MUST deny all admin panel pages and actions to Members and unauthenticated users without exposing admin data.
- **FR-003**: The system MUST support exactly these v1 workspace roles in the admin panel: Owner, Admin, Member.
- **FR-003a**: Only Owners MUST be able to grant or revoke Owner/Admin role authority.
- **FR-003b**: Admins MUST be able to manage Members within policy but MUST NOT be able to grant or revoke Owner/Admin authority.
- **FR-004**: The system MUST exclude Analyst, support/break-glass, billing/payment, and global superadmin roles from v1.
- **FR-005**: The system MUST prevent removing, deactivating, blocking, revoking, or downgrading the last active Owner in a workspace.
- **FR-006**: The system MUST let Owner/Admin create invitations for new workspace users and show each invited or existing user as pending, active, inactive, blocked, or revoked.
- **FR-006a**: The system MUST require an invited user to complete login through an allowed provider before they become an active workspace member.
- **FR-006b**: The invitation capability MUST be generic enough to support future referral sources, while v1 excludes referral rewards, campaigns, and payout logic.
- **FR-006c**: The system MUST prevent duplicate active invitations for the same target in a workspace, support invitation expiry/revocation, and reject completion by a login identity that does not match the invitation target.
- **FR-006d**: Invitations created by Admins MUST grant Member access only; invitations that grant Owner or Admin authority require Owner action.
- **FR-007**: The system MUST show user detail with role, status, devices, sessions, files, usage contribution, and recent audit activity.
- **FR-008**: The system MUST record metadata-only audit events for user creation, role changes, state changes, device/session administrative actions, and failed unauthorized attempts.
- **FR-009**: The system MUST provide a file/meeting list filterable by owner, type, date, processing state, retention/deletion state, size, and duration.
- **FR-010**: The system MUST allow active Owners and Admins to review, download, export, or request deletion for any server-known meeting in their workspace after current role and workspace checks.
- **FR-010a**: Workspace-admin file access MUST NOT override missing artifacts, active deletion, retention/lifecycle blocks, post-egress limits, or other truthful unavailable states.
- **FR-011**: The system MUST record metadata-only audit events for admin review access, download, export, deletion request, denied file access, and failed sensitive actions.
- **FR-012**: The system MUST never expose raw storage identifiers, signed URLs, local file paths, tokens, secrets, raw audio, transcript text, or private meeting content in admin UI logs, screenshots, evidence, or audit details.
- **FR-013**: The system MUST support admin deletion as whole-meeting deletion everywhere `2brain Rec` controls, with destructive action confirmation, required reason, clear lifecycle state, and bounded deletion report.
- **FR-013a**: The system MUST NOT require typed confirmation phrases for v1 admin deletion.
- **FR-014**: The system MUST exclude bulk export, bulk delete, individual artifact deletion, policy override, advanced retention editing, and legal-hold management from v1.
- **FR-015**: The system MUST show quota and usage health for recording minutes, storage, processing jobs, usage by user, selected period, quota risk, and top consumers.
- **FR-016**: The system MUST clearly distinguish configured limits from missing or display-only limits.
- **FR-016a**: The system MUST NOT allow Owners or Admins to change quota or limit policy from the v1 admin panel.
- **FR-017**: The system MUST exclude financial balance, credit ledger, tariffs, invoices, debt, payments, and external billing integrations from v1.
- **FR-018**: The system MUST show product metrics for adoption/activity, usage/quotas, recording-to-processing funnel, reliability/quality, and governance.
- **FR-019**: Every production metric MUST define date window, denominator, freshness, source category, and drill-down path.
- **FR-020**: The system MUST mark recent or incomplete metric periods when upload or processing can lag.
- **FR-021**: The system MUST not show fake or sample-only numbers as production metrics.
- **FR-022**: The system MUST provide a single product audit journal filterable by period, user, action, object, and outcome, covering auth/session/device, user invitation, role/state, file access, egress, deletion, quota, metric/admin sensitive, denied, and failed sensitive events.
- **FR-023**: The system MUST keep admin audit data metadata-only by default and fail closed when required audit evidence for a sensitive action cannot be written.
- **FR-023a**: The system MUST keep the v1 product audit journal as the admin-facing source for user, file, export, deletion, quota, and admin-action accountability even if future technical log export is added.
- **FR-023b**: The system MUST NOT connect an external audit/log platform as part of v1.
- **FR-023c**: The system MUST preserve enough metadata-only audit evidence for sensitive admin actions after meeting deletion to support accountability without retaining private meeting content.
- **FR-024**: The admin panel MUST be a browser-owned workspace administration surface, not a desktop-embedded capture workflow.
- **FR-025**: Desktop attempts to open v1 admin pages MUST show a browser handoff or access-denied state, not a hidden full admin UI.
- **FR-026**: The admin panel MUST use Russian-first user-facing labels for admin pages, unavailable states, and destructive actions, and deletion copy MUST NOT promise universal erasure.
- **FR-027**: The admin panel MUST keep common workflows accessible by keyboard and usable on compact desktop/tablet-width screens.
- **FR-028**: The system MUST preserve workspace isolation for users, files, metrics, quotas, and audit in every admin view and action.

### Key Entities

- **Workspace Admin**: An active workspace user with Owner or Admin authority.
- **Workspace Member**: An active workspace user without admin panel access by default.
- **User Invitation**: A pending, completed, expired, or revoked workspace membership request that introduces a user to the workspace and is completed by login through an allowed provider. This is not a public meeting link or external meeting-recipient invitation.
- **Admin Permission Decision**: The result of evaluating whether the actor can open a page or run an admin action at execution time.
- **Workspace File / Meeting**: A server-known meeting and its associated review, processing, egress, retention, and deletion state.
- **Admin File Access Decision**: The result of confirming that an admin action targets a server-known meeting in the actor's workspace and that the actor is still an active Owner or Admin.
- **Egress Action**: A download or export action with actor, target, outcome, and metadata-only audit state.
- **Deletion Request And Report**: A whole-meeting deletion request, confirmation, reason, lifecycle state, and bounded report of controlled and uncontrolled areas.
- **Quota Policy**: Workspace limits or lack of limits for minutes, storage, and processing usage.
- **Usage Rollup**: Aggregated usage by workspace, user, and period.
- **Product Metric**: A source-backed KPI with definition, date window, freshness, and drill-down.
- **Admin Audit Event**: Metadata-only record of auth, user, file, export, deletion, quota, or admin action outcome.
- **Future Log Export**: A later optional export path for technical logs or observability data that does not replace product audit accountability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In role-based validation, 100% of Owner/Admin attempts can open the admin overview and 100% of Member/unauthenticated attempts are denied without admin data exposure.
- **SC-002**: In validation fixtures, 100% of last-owner removal, deactivation, blocking, revocation, and downgrade attempts are blocked with a clear reason, and 100% of Admin attempts to grant or revoke Owner/Admin authority are blocked.
- **SC-003**: In file-governance validation, 100% of non-owned same-workspace meeting review/download/export/delete attempts succeed for active Owner/Admin users, fail for unauthorized or cross-workspace users, and produce metadata-only audit evidence when allowed or denied.
- **SC-004**: In deletion validation, 100% of admin deletion requests create whole-meeting bounded deletion reports that distinguish controlled deletion, local desktop purge, backup expiry, dependency limits, and post-egress limits where applicable.
- **SC-005**: In usage validation, displayed usage and quota totals reconcile to source-backed counts within the documented aggregation tolerance for every displayed period.
- **SC-006**: In metrics validation, every displayed KPI has a visible definition, date window, freshness state, and drill-down path; no sample-only production metric is displayed.
- **SC-007**: Privacy validation finds zero raw storage identifiers, signed URLs, local paths, tokens, secrets, raw audio, transcript text, or private meeting content in admin UI evidence, audit details, logs, or screenshots.
- **SC-008**: Usability validation shows an Owner/Admin can locate a user, locate that user's files, identify quota contribution, and inspect recent audit activity in under 3 minutes using seeded workspace data.

## Assumptions

- V1 is workspace-admin-first and does not include internal 2brain global superadmin tooling.
- V1 has no support incident triage or support role.
- V1 has no Analyst role.
- V1 balance means quota and usage visibility, not billing or credit accounting.
- V1 balance/limits is read-only monitoring; quota and limit editing is outside the v1 admin panel.
- V1 user onboarding uses admin-created invitations completed through allowed provider login.
- Workspace user invitations are membership onboarding, not public links or external meeting-recipient invitations.
- V1 admin deletion uses existing product deletion truth: whole-meeting deletion everywhere `2brain Rec` controls, not partial artifact deletion.
- V1 admin deletion requires a reason and normal destructive action confirmation, not typed confirmation text.
- V1 audit means a single product audit journal in the admin panel; external audit/log platform integration is future work.
- Local-only desktop files can be represented only through metadata-safe sync and purge state.
- Product metrics must be source-backed; new instrumentation, if needed, must remain metadata-only.

## Out Of Scope

- Support incident triage and support/break-glass access.
- Internal global superadmin UI.
- Analyst or read-only analytics role.
- Financial billing, tariffs, invoices, debt, payments, credit ledger, or credit top-up.
- Referral rewards, referral campaign management, and referral payout logic.
- Public meeting links and external meeting-recipient invitations.
- Quota or limit editing from the admin panel.
- External audit/log platform integration.
- Bulk export and bulk delete.
- Individual artifact deletion outside whole-meeting deletion lifecycle.
- Policy override, advanced retention editor, and legal-hold management.
- Desktop-embedded admin UI.
- New standalone frontend application or marketing-style landing page.
