# Data Model: Обмен встречами

**Feature**: [125-meeting-sharing](spec.md)
**Source of truth**: existing access, invitation, calendar, deletion and audit authorities

## Design rule

Share does not create a parallel authorization system. Existing
`MeetingShareGrant`, `MeetingShareInvitation`, `RecordingCalendarContextLink`,
`CalendarParticipant`, workspace membership, audit and deletion lifecycle remain
authoritative. New UI models are projections and cannot grant access.

## 1. Share capabilities

Ephemeral server projection for the current actor and meeting. It is derived from
meeting authorization plus operator settings and is not persisted.

| Field | Shape | Meaning |
|---|---|---|
| `internal_grant` | `available/blocked + reason` | Authenticated active workspace identity grant |
| `external_invitation` | `available/blocked + reason` | Email delivery and verified-address onboarding |
| `recipient_bound_link` | `available/blocked + reason` | Link that preserves one recipient and scope |
| `public_link` | `available/blocked + reason` | Anonymous/link audience; off by default |
| `calendar_suggestions` | `available/blocked + reason` | Current owner-authorized calendar context |
| `address_book` | `available/blocked + reason` | Native/least-privilege picker only |

Rules:

- `blocked` is rendered as absent or explanatory unavailable state; it is never
  converted to a client-side authorization decision.
- A direct mutation always re-evaluates the same policy on the server.
- Defaults are internal authenticated, summary-only, view-only, invite-only.
  Exact-email invitations use an explicit `full_meeting` recording preset in
  the current rollout; it remains view-only and carries download/export
  capabilities without creating workspace membership.

## 2. Meeting access grant

Existing table: `meeting_share_grants`.

Relevant fields:

- tenant: `workspace_id`, `meeting_id`;
- audience: `audience_type`, `audience_id`, `grantee_user_id`;
- scope: `content_scope`, `can_download`, `can_export`;
- lifecycle: `status`, `expires_at`, `rotated_at`, `revoked_at`, `last_used_at`;
- bearer material: only `share_token_hash`, never raw token;
- audit ownership: `created_by_user_id`, `revoked_by_user_id`, metadata-only
  `metadata_json`.

Allowed internal default invariant:

```text
audience_type = user
content_scope = summary_only
can_download = false
can_export = false
status = active
```

For an accepted invitation, `grant.expires_at` MUST be no later than the
invitation expiry. A revoked/expired/deleting meeting grant is ineffective even
if an old URL still exists.

## 3. Share invitation

Existing table: `meeting_share_invitations`.

State machine:

```text
pending → sending → sent → accepted
   │          │        │
   ├──────────┴────────┴→ failed
   └────────────────────→ expired/revoked
```

`outcome-unknown` is represented by the delivery workflow/failure code when the
provider boundary may have been crossed without confirmation; it must not be
blindly retried.

Fields and rules:

- `normalized_address_hash`: lookup pseudonym; never display as an email;
- `encrypted_delivery_address`: bounded server-side delivery secret, cleared at
  terminal delivery/expiry/revoke;
- `token_hash`: invitation exchange material, raw token returned only in the
  delivery URL and never logged;
- `grant_token_ciphertext`: nullable encrypted-at-rest material for the separate
  recipient-bound grant token after acceptance. It is used only to replay the
  same successful exchange for the same verified recipient after a lost HTTP
  response; raw grant token is never written to logs, analytics or metadata
  audit;
- `content_scope`, `can_download`, `can_export`: domain service must enforce
  either summary-only view or the explicit full-recording preset for external
  invitations, independently of request schema. `full_meeting` requires both
  `can_download` and `can_export`;
- `expires_at`: required bounded TTL;
- `resolved_user_id`: identity created/located only after exact verified-address
  acceptance.

An accepted invitation does not create membership. It creates or updates a user
grant with a separate recipient-bound token, the invitation scope and bounded
expiry. The invitation exchange is idempotent for the same exact verified
recipient until expiry: it returns the same grant URL without rotating it. A
different verified identity cannot replay the exchange. A full external grant
is rendered through an owner-workspace-scoped recipient page and rechecks
identity, grant lifecycle and egress policy for every page/playback/download/
export request; no calendar/service/revision metadata is added to that page.

## 4. Recipient suggestion

Ephemeral response model; no table and no grant side effect.

| Field | Rule |
|---|---|
| `user_id` | present only for active identity in current workspace |
| `display_label` | safe bounded name, never private meeting content |
| `email` | optional, only when current owner may see the identity and policy permits |
| `source` | one of `workspace`, `calendar`, `workspace_calendar`; future address-book results remain gated |
| `freshness` | `current`, `stale`, `unavailable`; stale is not an authorization |
| `recipient_type` | `workspace_member` in the first rollout; external remains gated |

Deterministic merge key is verified GRAF `user_id`; email is only a lookup hint
and is normalized before comparison. Calendar `participant.email` is never
shown to an unrelated viewer and never becomes a grant without an explicit
owner action.

Search is bound to `(workspace_id, meeting_id, actor_user_id)` and only runs
after `decide_meeting_access(...).can_share`. It uses a minimum query length,
escaped pattern matching, bounded result count and source throttling.

## 5. Calendar source

Existing `RecordingCalendarContextLink` points from a meeting to the selected
calendar event snapshot. `CalendarParticipant` is a source projection with
response status, display name, email/email hash, workspace relation and
candidate class.

Only current owner-authorized, non-deleted context may produce suggestions.
Private/free-busy/hidden/declined/stale states are either omitted or surfaced as
an honest source state. The presence of an attendee never mutates grants,
recording consent, workspace membership or delivery.

## 6. Address-book source

No server-side address-book entity in the first delivery.

Native clients may request a limited selection from the platform picker and send
only the selected, typed recipient action. Browser-only surfaces keep the typed
email path. If a future provider search is approved, its source record must have
owner scope, delegated read-only permission, freshness, bounded cache expiry and
disconnect purge behavior; it must not become a permanent global contact index.

## 7. Referral attribution

Future gated entity, separate from access tokens:

- opaque attribution id;
- invitation/grant relation;
- one-time conversion state;
- created/converted/invalidated timestamps;
- bounded source channel, never raw email/title/transcript.

Clicks are not conversions. A conversion requires an explicit auth completion
(including the invite flow's one-step account bootstrap) plus a permitted value
event, is idempotent, and cannot create another grant or account.
Until its storage/retention contract is approved, only aggregate metadata events
through the existing analytics gate may be used.

## 7.1. Distribution policy and adoption loop

Future gated policy projection; no new persistence in the first delivery.

| Policy | Authority | Safe behavior |
|---|---|---|
| `share_with_meeting_participants` | Meeting owner + current calendar/workspace context | Resolve a bounded recipient snapshot for this meeting instance and create individual summary-only grants only after explicit owner action. |
| `auto_share_internal_summary` | Owner preference, optionally recommended by workspace policy | Apply only to future owned meetings after opt-in; private/1:1 override wins; external and declined/hidden attendees are excluded. |
| `pre_read_recurring_summary` | Owner preference + current recurring event roster | Deliver a pointer to an already-authorized summary/action-item view; do not grant access from the notification and do not include transcript/audio. |
| `team_report_access` | Workspace admin policy | Role-scoped summary viewer only; no edit/share/export and no retroactive access without explicit confirmation. |

Each policy resolves to existing `MeetingShareGrant` rows or an existing
notification/delivery authority. A group or channel label is never treated as a
new authorization primitive. Calendar pointers, Slack/Teams messages and action
items are distribution surfaces; they must reference an already authorized
grant and cannot widen it.

### 7.2. Effective access and source provenance

Access is the union of independently valid sources, not a single mutable role.
The read model should be able to explain why a recipient currently has access:

```text
direct_user_grant
participant_distribution
team_policy
accepted_external_invitation
```

`grant_origin`/source provenance is metadata-only and is not itself an
authorization decision. A revoke operation targets one source. If another
active source remains, the recipient continues to see the meeting and the UI
must say so. Every source still rechecks current meeting policy, active
membership (for internal sources), scope, expiry and deletion at egress.

Internal grants must not survive loss of workspace membership. Accepted external
grants are a distinct origin: they require exact verified identity and bounded
expiry, and they must not be silently treated as internal membership.

### 7.3. Distribution operation/idempotency authority

The current single-recipient fix does not justify a mass-distribution rollout.
Before adding participant batch or auto-share, reuse an existing idempotency
authority if one exists. Otherwise add one narrow bounded operation record rather
than separate outbox, notification, referral and retry tables.

Minimum fields are:

- workspace/meeting/actor scope;
- HMAC/fingerprint of `Idempotency-Key` and canonical request payload;
- policy version and roster snapshot version;
- operation state: `requested`, `resolving`, `planned`, `applying`,
  `completed|partial|failed|cancelled`;
- per-recipient outcome and stable grant reference;
- created/finished/expiry timestamps.

The record must not store raw bearer tokens, email, meeting content or provider
payload. A participant batch should normally return no bearer URLs: its primary
distribution surface is `Shared with me`. If a single-recipient operation
returns a URL, replay semantics must be explicit and must not rotate the token
on network retry.

The adoption funnel is an aggregate projection, not a meeting-content entity:

```text
eligible_recipient → summary_viewed → cta_clicked → graf_setup → first_capture
```

One invitation/grant may have at most one bounded setup attribution. Repeated
opens, forwarding and channel reposts must not create new grants, accounts or
unlimited credit. The existing analytics gate records only stable operation
types, bounded source and pseudonymous grant/invitation references.

## 8. Audit and deletion

Existing `MeetingEgressAuditEvent` remains metadata-only. New event types may
record operation, outcome, policy reason, stable grant/invitation id and bounded
source; no token, address, calendar payload, transcript, audio or summary text.

Meeting deletion locks the shareable meeting, blocks new grants/invitations and
invalidates controlled access. Product copy distinguishes GRAF-controlled
purge from mailbox copies, forwarded links and operator-managed observability
retention.

## 9. Persistence and migration decision

Phase 0/1 uses existing tables and no migration. The only required behavior
change to existing persistence is copying invitation expiry to an accepted grant
and enforcing policy invariants in the domain service. New referral/contact
tables require a later approved retention/deletion contract and are explicitly
out of the first code delivery.
