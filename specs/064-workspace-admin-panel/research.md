# Phase 0 Research: Workspace Admin Panel

## Decision 1: Build a Separate Server Admin Module

**Decision**: Implement the admin panel as `twobrain_rec_server.admin` plus
`twobrain_rec_server.api.admin`, with its own templates, view models,
permissions, queries, audit helpers, usage, metrics, and invitation services.
Register routers/static assets from `main.py`.

**Rationale**: The current cabinet already has domain seams:
`cabinet/access.py`, `cabinet/queries.py`, `cabinet/view_models.py`,
`cabinet/egress.py`, and `deletion/service.py`. Extending `cabinet/web.py` for
workspace administration would mix meeting review, user management, quota
monitoring, and audit governance in one large route file. A separate admin
package keeps the browser admin control room clear while still reusing existing
cabinet and deletion services.

**Alternatives Considered**:

- Extend `cabinet/web.py`: rejected because the file already owns browser
  meeting review and embedded cabinet behavior. Admin needs users, metrics,
  audit, usage, and destructive governance boundaries.
- New standalone frontend app: rejected by the spec. V1 is server-owned and
  browser-rendered, consistent with existing cabinet patterns.

## Decision 2: Reuse Existing File Governance Services

**Decision**: Admin file review, download, export, deletion, lifecycle, and
activity must call existing cabinet/deletion service boundaries with a new
admin permission decision that allows active Owner/Admin access to same
workspace meetings. Admin access must still honor egress policy,
artifact availability, deletion lifecycle, retention blocks, post-egress
limits, and audit persistence.

**Rationale**: Existing code already records egress audit events and deletion
reports, and deletion service fails closed when lifecycle evidence cannot be
persisted. Admin capability changes who can act within a workspace; it should
not fork artifact safety, storage, or deletion truth.

**Alternatives Considered**:

- Direct storage/object access from admin routes: rejected because it risks
  leaking object keys, signed URLs, local paths, or bypassing deletion and
  egress policy.
- Separate admin deletion workflow: rejected because whole-meeting deletion
  truth should remain one product lifecycle.

## Decision 3: Workspace Invitations Are a Generic Onboarding Primitive

**Decision**: Add a `WorkspaceInvitation` model/service for pending, completed,
expired, and revoked workspace membership requests. Invitations have a source
field that starts with `admin` and can later support referral origins without
adding referral rewards, campaigns, or payout logic in v1.

**Rationale**: Current auth has provider-based login and workspace membership,
but no dedicated invite state. The admin flow needs pending state, expiry,
revocation, duplicate prevention, completion identity matching, invited role,
creator, and audit trail. A source field is enough to keep the primitive
reusable for future referral onboarding while keeping referral product logic
out of this slice.

**Alternatives Considered**:

- Create members directly without login: rejected because the user must complete
  login through an allowed provider before becoming active.
- Encode invite state in `WorkspaceMembership.status`: rejected because pending
  invites may exist before a user identity or membership exists.

## Decision 4: Quota/Balance Is Read-Only Monitoring

**Decision**: V1 should expose read-only quota and usage health. Add or derive
`WorkspaceQuotaPolicy` for display-only limits and `WorkspaceUsageDaily` /
`UserUsageDaily` rollups when bounded on-demand queries are insufficient.
No admin route may edit quota policy, billing, tariffs, invoices, debt,
payments, credits, or external billing integrations.

**Rationale**: The spec uses "balance" as operational quota visibility, not
financial balance. The codebase has ingest limits and storage/processing data,
but no durable billing ledger or quota-management domain. Read-only monitoring
lets admins find problems without inventing a billing system.

**Alternatives Considered**:

- Build billing/credits now: rejected as explicit out of scope.
- Let admins edit limits now: rejected by the user and spec; v1 must say where
  limits are managed instead of offering controls.

## Decision 5: Product Audit Journal Stays In-Product

**Decision**: Build a single product audit journal in the admin panel from a
normalized read model over existing auth, cabinet egress, deletion lifecycle,
ingest/processing, and new admin audit events. Add `AdminAuditEvent` only for
admin-specific actions that are not already covered. Do not connect an external
audit/log platform in v1.

**Rationale**: Admins need an accountable product view for user, file, export,
deletion, quota, and admin-action events. External observability/log export is
future work and cannot replace product accountability. Audit entries must keep
metadata only, preserve evidence after meeting deletion, and avoid retaining
private meeting content.

**Alternatives Considered**:

- Ready-made audit/log platform integration: rejected for v1. It adds data
  boundary, retention, ownership, and deletion complexity before the product
  audit journal exists.
- Use only raw technical logs: rejected because they are not a product-facing
  accountability surface and may include unsafe implementation detail.

## Decision 6: Browser-Owned Admin With Desktop Handoff

**Decision**: `/admin` routes are browser-owned. Desktop attempts to open admin
pages should show handoff or access-denied state, not hidden full admin UI.

**Rationale**: The existing product route matrix keeps team, billing, audit, and
full deletion reports as browser governance surfaces. Admin panel workflows are
too broad and sensitive for the native capture shell.

**Alternatives Considered**:

- Embed full admin in desktop: rejected by the spec and route matrix.
- Native-only admin: rejected because user/file/metrics/audit surfaces already
  live in the server-owned browser/cabinet world.

## Decision 7: Metrics Must Be Source-Backed And Freshness-Labeled

**Decision**: Every displayed metric must have a definition, source category,
date window, denominator, freshness state, and drill-down. Current or lagging
periods must be marked incomplete. If source-backed data does not exist, the
metric is absent or explicitly unavailable.

**Rationale**: The admin panel is for solving real workspace problems. Fake,
sample-only, or unlabeled production metrics would erode trust and break the
spec success criteria.

**Alternatives Considered**:

- Seed demo/sample production numbers: rejected by FR-021.
- Show charts without definitions: rejected because admins need to diagnose
  problems and reconcile displayed totals to source data.
