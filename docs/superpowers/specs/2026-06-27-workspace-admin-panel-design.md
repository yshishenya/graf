# Workspace Admin Panel Design

Date: 2026-06-27

## Decision Summary

Build a workspace-admin-first web admin panel for `2brain Rec`. The panel is a
server-owned browser surface for managing users, monitoring quotas and usage,
administering workspace files, reviewing product metrics, and inspecting audit
activity.

The v1 product shape is a hybrid control room: a summary overview for workspace
health plus focused pages for users, files, balance/limits, metrics, audit, and
settings. The architecture must leave room for a later internal 2brain
superadmin surface, but v1 does not include global support/admin tooling.

## Risk And Validation Lane

Selected lane: high-risk Spec Kit feature.

Rationale: the feature touches admin UX, RBAC, user management, file content
access, downloads, exports, deletion, quotas, product metrics, audit logs, and
privacy-sensitive data boundaries. Implementation must go through full Spec Kit:
specify, clarify, plan, checklist, tasks, analyze, task-to-issues, and implement.

## Product Goals

- Let a workspace owner/admin create and monitor users.
- Define the v1 user onboarding path explicitly. Current code supports identity,
  membership, auth policy, sessions, devices, and provider self-enrollment, but
  not a dedicated invitation entity.
- Show quota and usage health without introducing billing or payments in v1.
- Let authorized admins manage user files: review, download/export, and delete
  with confirmation, reason, deletion truth, and audit evidence.
- Make admin access to another user's meeting explicit and audited. Admin file
  access is not implied by workspace membership alone.
- Provide product metrics for adoption, usage, pipeline funnel, reliability,
  and governance.
- Keep metrics source-backed, fresh, and drillable to user/file/action evidence.
- Keep support incident triage, global superadmin, credit ledger, and billing
  out of v1.

## Navigation

Primary admin navigation:

- `Обзор`: workspace health, usage, reliability, quota risk, attention queue.
- `Пользователи`: create/invite, role, status, devices, usage, activity, files.
- `Файлы`: list, review, download/export, delete, deletion report, file states.
- `Баланс и лимиты`: quotas and usage only: minutes, storage, processing jobs,
  quota risk. No money or invoices.
- `Метрики`: adoption, usage, funnel, quality/reliability, governance metrics.
- `Журнал`: auth, user, file, export, delete, quota, and admin action audit.
- `Настройки`: workspace policy basics only where required by the admin flows.

## Roles And Permissions

V1 roles:

- `Owner`: full workspace administration. Can manage owners/admins/members,
  limits, files, exports/downloads, deletion, and workspace settings. The system
  must prevent removing or downgrading the last owner.
- `Admin`: can create users, manage member/admin user states within policy, view
  and manage files, download/export, and delete with audit. Cannot remove the
  last owner or change owner authority.
- `Member`: normal product user. Appears in admin views but has no admin panel
  access by default.

Out of v1:

- `Analyst` read-only role.
- Global 2brain superadmin role.
- Billing/payment roles.
- Break-glass support role.

Permission defaults:

- Deny by default.
- Role checks must use a canonical Owner/Admin/Member vocabulary while remaining
  compatible with the existing `WorkspaceMembership.role` string field.
- Any migration/backfill must preserve existing `owner`, `admin`, and `member`
  behavior and include last-owner protection.
- Admin pages must be hidden and blocked server-side for unauthorized users.
- Sensitive actions require current permission checks at execution time, not
  only at page render time.
- Export, download, and deletion must write metadata-only audit events.
- Deletion requires confirmation, reason, clear result state, and deletion
  report.

## Files

V1 file admin is full enough for real workspace administration, but bounded:

- Admins can search/list files by owner, file type, date, status, processing
  state, retention/deletion state, and size/duration.
- Admins can open the existing review surface only after an explicit admin file
  access decision allows it.
- Admins can download/export allowed artifacts through server-mediated egress.
- Admins can delete a whole meeting and its controlled artifacts with
  confirmation and reason.
- The UI must use deletion wording equivalent to "Delete everywhere 2brain Rec
  controls" and must not promise universal erasure.
- Deletion reports must distinguish server data, object storage, local desktop
  purge, dependency limits, backup expiry, diagnostics, and post-egress limits
  where those states are available.
- The admin surface can manage only server-known meetings/artifacts. Local-only
  desktop files can appear only as metadata-safe sync state, never as raw local
  paths, and local purge must go through existing lifecycle/local-purge tasks.

Out of v1:

- Bulk export.
- Bulk delete.
- Individual artifact deletion outside the existing whole-meeting deletion
  lifecycle.
- Policy override.
- Advanced retention editor.
- Raw object keys, raw local paths, signed URLs, tokens, or secrets in UI,
  logs, evidence, audit details, or screenshots.

## Balance And Limits

V1 balance means quotas and usage, not financial billing.

Include:

- Recording minutes used vs workspace limit.
- Storage used vs workspace limit.
- Processing jobs and processing success/failure counts.
- Usage by user and period.
- Quota risk and top consumers.
- A clear source of truth for quota policy. If v1 is display-only, the UI must
  say so; if admins can edit limits, changes must be audited and the upload /
  processing enforcement path must read the same policy.

Later:

- Credit balance and ledger.
- Manual credit top-up.
- Plans, payments, invoices, debt, external billing integrations.

## Metrics

All five metric families are in v1:

1. Adoption and activity: active users, new users, inactive users, devices seen.
2. Usage and quotas: recording minutes, storage bytes, recordings, processing
   jobs, consumption by user.
3. Recording to upload to processing funnel: recorded, uploaded, accepted,
   processing, review-ready, failed, deleted.
4. Quality and reliability: upload success, processing success, playback
   availability, failure reasons, retry classes.
5. Governance: shares, downloads, exports, deletes, retention events, sensitive
   admin actions, audit outcomes.

Metric quality requirements:

- Every metric must define grain, denominator, date window, source table/query,
  and freshness.
- Recent partitions must be marked incomplete when ingestion or processing can
  lag.
- Each KPI must drill down to trend, segment, source table, and relevant
  user/file/action evidence.
- V1 must classify each metric as derived from existing product tables, derived
  from existing audit events, or requiring new metadata-only instrumentation.
- Do not ship fake or sample-only metrics as production dashboard numbers.
- Do not add third-party product analytics for v1. Any new product-event stream
  must follow the same metadata-only and no-private-content rules as current
  audit/evidence.

## Core Workflows

1. Create or invite a user:
   - Owner/Admin creates or invites a user.
   - Role is one of Owner/Admin/Member.
   - UI shows pending, active, blocked, or inactive state.
   - Spec Kit must decide whether this is provider self-enrollment, provider
     allowlist, manual membership creation, or a new `WorkspaceInvitation` /
     pending-membership model.

2. Inspect a user:
   - User detail shows role, devices, sessions, files, usage, latest actions,
     quota contribution, and audit timeline.

3. Manage files:
   - Admin opens review, downloads or exports allowed artifacts, or deletes with
     confirmation, reason, deletion report, and audit event.
   - Admin review/download/export of a non-owned meeting must write a
     metadata-only admin access/egress audit event.

4. Monitor quotas:
   - Admin sees usage by user and period, quota risk, and top consumers by
     storage/minutes.

5. Drill into metrics:
   - KPI opens trend, segment breakdown, source table, and the relevant
     user/file/action evidence.

## Architecture

Do not add this feature to `apps/server/src/twobrain_rec_server/cabinet/web.py`.
That file already owns current meeting-cabinet presentation routes and should
not become the admin monolith.

Add a separate admin package:

```text
apps/server/src/twobrain_rec_server/admin/
├── __init__.py
├── web.py
├── api.py
├── audit.py
├── files.py
├── metrics.py
├── permissions.py
├── queries.py
├── usage.py
├── view_models.py
└── templates/
    └── admin/
        ├── base.html
        ├── pages/
        ├── fragments/
        └── components/
```

Reuse shared foundations:

- FastAPI auth, tenant, device, session, and CSRF dependencies.
- Existing server-owned web/cabinet visual system where reusable.
- Existing static CSS tokens, local icons, and template helpers where practical.
- Existing access, egress, export, deletion, lifecycle, and audit services where
  they already own the behavior.
- Existing meeting deletion must remain whole-meeting deletion unless a separate
  future feature adds a safe individual-artifact lifecycle.

Keep separate:

- Admin routes and admin navigation.
- Admin permission matrix.
- Admin user-management queries.
- Admin file access decisions for workspace administrators.
- Quota/usage read models.
- Admin metrics read models.
- Admin audit timeline/read model that can union existing auth, ingest,
  processing, egress, lifecycle, and future admin-action events.
- Admin-specific templates and fragments.

Route boundaries:

- Register admin routers separately from cabinet routers in `main.py`.
- Browser routes should live under `/admin/*`.
- JSON/HTMX action routes should live under `/api/v1/admin/*`.
- Future internal 2brain superadmin should use a separate package or route
  namespace, not a hidden mode inside workspace admin.

The admin browser surface should not be embedded into the macOS desktop app by
default. Desktop remains the native trust shell for capture-critical behavior.

## Current Source Fit

Existing source domains that can power v1:

- Identity and membership: `Organization`, `Workspace`, `UserIdentity`,
  `WorkspaceMembership`, `RegisteredDevice`.
- Auth/session/audit: `ExternalIdentity`, `AuthSession`,
  `AuthSessionDeviceBinding`, `AuthAuditEvent`.
- Files and meetings: `Meeting`, `MediaRevision`, `UploadSession`,
  `TrackArtifact`, `ManifestSnapshot`, `TemporaryUploadObject`.
- Processing: `ProcessingWorkflow`, `MediaScribeJob`, `ProcessingResult`,
  `ProcessingAuditEvent`, `ProcessingDependencyState`.
- Access/egress: `MeetingShareGrant`, `MeetingArtifactPolicy`,
  `MeetingEgressAuditEvent`, `ExportPackage`.
- Deletion/lifecycle: `MeetingDeletionRequest`,
  `MeetingDeletionArtifactState`, `MeetingDeletionReport`,
  `RetentionPolicySnapshot`, `MeetingLifecycleAuditEvent`.

Likely new models/read models:

- Workspace quota/limit configuration, for example `WorkspaceQuotaPolicy`.
- Daily workspace usage rollup.
- Daily per-user usage rollup.
- A user onboarding model if v1 chooses invitations or pending membership
  instead of existing provider self-enrollment.
- Admin file access decision/audit records when an admin views or exports a
  non-owned meeting.
- Admin action audit event if existing audit tables do not cover a given action.
- Admin audit read model/view that normalizes existing domain audit tables for
  list/search/drill-down.
- Admin metric snapshot or materialized read model if direct queries become too
  expensive.

Known code gaps to resolve before implementation:

- No dedicated invitation table exists today; auth has provider
  self-enrollment and pre-existing membership checks.
- No quota/balance/billing model exists today. Quota references are mostly
  custody/problem states and product docs, not an enforcement data model.
- Roles are strings on `WorkspaceMembership`, with existing `owner`/`admin`
  checks in auth and cabinet code.
- Current access decisions are owner/team/shared/denied. A workspace-admin view
  of another user's non-team-visible meeting needs an explicit access state.
- Current deletion implementation is whole-meeting lifecycle with bounded
  reports, not arbitrary per-file deletion.
- Audit is spread across domain tables. The admin panel needs a normalized read
  model without weakening fail-closed writes for sensitive actions.

## Validation Requirements

- RBAC matrix tests for Owner/Admin/Member across every admin page and action.
- Last-owner invariant tests for role downgrade, removal, deactivation, and
  transfer flows.
- Cross-workspace isolation tests for users, files, metrics, quota, and audit.
- CSRF tests for every unsafe browser/admin action.
- Admin access tests proving non-owned meeting review/download/export is denied
  unless the admin file-access rule allows it and an audit event is persisted.
- Whole-meeting deletion tests proving admin deletion reuses the bounded deletion
  report and does not promise universal erasure.
- Evidence/privacy tests proving no raw object key, signed URL, local path,
  token, secret, raw audio, transcript text, or private meeting content appears
  in admin UI snapshots, logs, audit details, docs, or evidence.
- Metric reconciliation tests that compare dashboard numbers to their source
  queries and show freshness/incomplete-period state.
- Route-boundary tests proving the admin package is registered separately and
  `cabinet/web.py` is not expanded into the admin monolith.
- Desktop route guard tests proving admin routes remain browser-only or handoff
  states unless a future desktop spec explicitly changes that.

## UX Principles

- Operational and dense, not marketing-like.
- Summary first, then trend, then drill-down.
- Tables remain first-class for users/files/audit.
- Filters are few and meaningful: date range, user, status, file type, action.
- Every destructive or privacy-sensitive action explains what will happen before
  it runs.
- Every chart shows source freshness and enough definition to avoid misleading
  decisions.
- Russian-first labels and copy.

## Best Practice Anchors

Use these as design and validation references, not as product copy:

- OWASP Authorization Cheat Sheet for deny-by-default, least privilege, and
  server-side authorization checks:
  https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP Logging Cheat Sheet for security-relevant audit logging:
  https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Google SRE monitoring guidance for monitoring useful symptoms, causes, and
  reliability signals:
  https://sre.google/sre-book/monitoring-distributed-systems/
- Microsoft Entra role best practices for least-privilege admin assignment:
  https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/best-practices

## Out Of Scope

- Support incident triage.
- Internal 2brain global superadmin UI.
- Analyst role.
- Credit ledger.
- Payments, tariffs, invoices, billing provider integration.
- Bulk file actions.
- Policy override.
- Advanced retention/legal-hold editor.
- Desktop-embedded admin UI.
- New frontend framework or separate frontend app.

## Open Questions For Spec Kit

- How should workspace quotas be configured before billing exists: static config,
  database table, deployment seed, or admin-editable setting?
- Does user creation mean invite-by-email, provider allowlist, local password
  account, or a manual identity record in v1?
- Which file content access should be allowed to Admin versus Owner when a
  meeting is not owned by that admin?
- Should delete require a typed confirmation for all files or only multi-source
  recordings with retained audio/transcript?
- What is the exact latest-complete-data rule for daily usage metrics?
- Should admin action audit reuse existing audit tables or introduce one
  unified `admin_audit_events` table?

## Approval State

Approved during brainstorming:

- Workspace-admin-first v1 with future superadmin-ready architecture.
- Hybrid control room approach.
- Roles: Owner, Admin, Member only.
- Balance v1 means quotas and usage.
- File admin v1 includes review, download/export, and delete.
- All five product metric families are in v1.
- Admin implementation should use a separate `admin` package, not
  `cabinet/web.py`.
