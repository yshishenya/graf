# Contract: Meeting Sharing

**Feature**: 125
**Status**: exact-email external invitations enabled behind the operator flag;
public/contact/referral operations remain gated

## 1. Server capability projection

The Share fragment and JSON meeting review expose the same capability projection.
The projection is informational and must be derived from current server policy.

```json
{
  "internal_grant": {"state": "available", "reason": null},
  "external_invitation": {"state": "blocked", "reason": "Внешние приглашения пока недоступны."},
  "recipient_bound_link": {"state": "available", "reason": null},
  "public_link": {"state": "blocked", "reason": "Публичные ссылки выключены политикой."},
  "calendar_suggestions": {"state": "available", "reason": null},
  "address_book": {"state": "blocked", "reason": "Выбор из адресной книги доступен только в поддерживаемом приложении."}
}
```

The exact JSON names may follow the existing snake_case API convention. Browser
and embedded views must receive the same values and Russian copy.

## 2. Recipient search

```http
GET /api/v1/cabinet/meetings/{meeting_id}/share-recipients?query={text}
```

Authorization:

- authenticated principal and active device/session;
- current tenant workspace;
- server-side meeting lookup;
- current actor `can_share == true`;
- bounded source query and rate-limit bucket.

Response:

```json
{
  "items": [
    {
      "user_id": "synthetic-user-id",
      "display_label": "Синтетический получатель",
      "source": "workspace_calendar",
      "recipient_type": "workspace_member",
      "freshness": "current"
    }
  ]
}
```

Contract rules:

- the meeting-bound route always carries `meeting_id`; the legacy
  `/cabinet/share-recipients` route remains inert without it;
- no share authorization means bounded empty/denied response;
- query length is at least 2/3 characters according to the rollout policy;
- wildcard characters are treated as text, not as search operators;
- maximum result count is 20;
- results are limited to active current-workspace identities;
- `source` is one of `workspace`, `calendar` or `workspace_calendar`; it is an
  explanatory hint and does not mutate access;
- unknown external attendees are not emitted as internal GRAF identities;
- private identity existence is not confirmed by an error message.

## 3. Create internal grant

```http
POST /api/v1/cabinet/meetings/{meeting_id}/shares
Idempotency-Key: opaque-client-request-id
```

Default request:

```json
{
  "audience_type": "user",
  "audience_id": "synthetic-user-id",
  "content_scope": "summary_only",
  "can_download": false,
  "can_export": false
}
```

The domain service rechecks meeting access, active membership, audience
identity, deletion state, scope and action capability. API schema validation is
not the only policy boundary.

Success response includes the updated grant and a recipient-bound `share_url`.
The client may offer Copy link only for that returned URL; it must not invent or
broaden a URL.

The key is required for mutating share operations once the endpoint is used by
the participant/distribution UI. The server stores only a keyed fingerprint and
canonical payload fingerprint. Same key + same payload replays the same logical
result without token rotation; same key + different payload returns
`409 idempotency_conflict`. If the endpoint cannot safely replay the returned
bearer URL, the retry response must omit a new URL and direct the owner to the
existing access row/explicit Rotate action. A network retry is never an implicit
rotation.

Expected errors:

| Code | User-facing behavior |
|---|---|
| `grantee_not_found` | Neutral “Не удалось найти получателя.” |
| `grantee_already_has_access` | “У этого человека уже есть доступ.” |
| `share_policy_blocked` | Explain unavailable capability, no retry loop |
| `meeting_not_found` | Generic unavailable state |
| `429` | Show bounded retry time if supplied |

## 4. Recipient-bound link rotation

```http
POST /api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}/rotate
```

For a user grant, rotation preserves the audience, scope, expiry and view-only
limits and returns a new recipient-bound URL. For a public/link grant, the
existing public policy and TTL gates continue to apply. Rotation is owner-only,
audited and rate-limited. Revoke invalidates both old and new tokens according
to the current grant status.

## 5. External invitation (operator-gated exact-email path)

```http
POST /api/v1/cabinet/meetings/{meeting_id}/share-invitations
```

This endpoint remains blocked while `share_external_invitations_enabled` is
false. The UI must not call it in that state. The current controlled rollout
sets the flag true only with Postal delivery, the public base URL, the
credential-encryption key and the generated share-identity HMAC secret
available to `rec-api`; public links remain false.

Request is limited to normalized address + summary-only, view-only scope. The
domain service must enforce that restriction, invitation TTL, duplicate fence,
deletion state and rate limits regardless of caller.

Lifecycle response is one of `pending`, `sending`, `sent`, `accepted`,
`expired`, `revoked`, `failed`, or bounded `outcome_unknown`. `sent` means the
mail service accepted the request, not that it reached the inbox. A committed
post-egress timeout is `outcome_unknown` and is not automatically retried.

Acceptance requires the exact invited address to be verified. The resulting
grant inherits a bounded expiry and never creates workspace membership. The
invitation token and grant token are different. Acceptance stores the grant
token only encrypted-at-rest so a lost response can be replayed for the same
verified recipient without rotating the grant; a different identity receives a
privacy-preserving not-found response.

For an anonymous recipient, the landing page exposes only an explicit
`Открыть GRAF и итоги` POST action. The action uses the one-time continuation
nonce plus a double-submit CSRF cookie; the bearer invitation token is not
placed in the form, login `next` path, referrer or analytics. The server
consumes the continuation, resolves the invited address from encrypted
server-side data, creates or reuses the recipient's personal account, issues
the browser session and opens the summary in one transaction. Preview alone
creates neither an account nor a grant. Existing standard email login remains
code-based; the invitation magic link is the automatic bootstrap path.

When bootstrap created a new account, the server commits the access result
first and then starts the deterministic
`share-account-created/{invitation_id}` notification workflow. Notification
status is independent from access and is one of `pending`, `sending`, `sent`,
`failed` or `outcome_unknown`. Its body contains only the safe meeting title,
masked recipient address, GRAF/settings links and revoke/support copy; it never
contains raw email, invitation/grant tokens, transcript, audio, participants or
summary text.

## 6. Share fragment UI contract

The fragment must be rendered only after an explicit Share action. It contains:

1. title and one-sentence summary-only explanation;
2. recipient field with combobox/listbox semantics;
3. typed-search action and result rows with source labels;
4. blocked external state when applicable;
5. collapsed “Что увидят: только итоги” disclosure;
6. current active grants with scope, expiry when available, create-and-copy a
   rotated recipient-bound link and Revoke;
7. live-region status for loading, success, empty, blocked, rate-limit and
   generic privacy-preserving failure;
8. focus return to the opener and Escape/overlay close behavior.

The button does not claim “sent” when it only searched. A result row owns the
explicit “Открыть доступ” action. After a successful grant the row is rendered
without a full fragment reload and Copy link uses the API-returned URL.

## 7. Recipient surface and viral CTA (gated)

The invitation landing page and email may contain only safe metadata: inviter
label, bounded meeting label/time, scope, expiry, action to sign in/create GRAF
and notification/privacy links. No transcript, audio, participant list,
summary text, tracking pixel, raw email or token is placed in content.

After successful authorized summary view, an optional CTA explains one concrete
GRAF value and links to explicit onboarding. It never blocks the summary, joins
the workspace, creates an account or sends another invitation.

The anonymous invitation action is the exception to the general onboarding
rule: account creation happens only after the recipient explicitly submits the
one-time magic-link action, and only as a personal account needed to open this
summary. The follow-up account-created notification is post-commit and does
not widen access.

### 7.1. Effective access and provenance

The owner view must distinguish independent access sources when they overlap:
direct grant, participant distribution, team policy and accepted external
invitation. Revoking one source does not claim to revoke access supplied by
another active source. Internal sources require active membership at every
request; external accepted access uses exact verified identity and bounded
expiry. `grant_origin` is explanatory provenance and does not replace the
server-side access decision.

### 7.2. Participant distribution and team adoption (gated)

The strongest viral action is an explicit owner action, not a hidden default:

```text
POST /api/v1/cabinet/meetings/{meeting_id}/share-participants
```

The server resolves the current authorized meeting roster and returns individual
grant results. It MUST exclude the owner, declined/hidden participants,
unmatched external addresses and unknown identities. Each result is equivalent
to the internal grant contract: `summary_only`, view-only, bounded expiry and
individual revoke. Partial success is explicit; one bad participant must not
turn the whole action into a generic error.

An optional owner policy may apply the same action to future owned meetings only
after opt-in. The UI must show the recipient preview and a per-meeting private
override. Enabling the policy does not authorize external delivery or full
meeting scope.

`Shared with me` is a presentation of existing grants. A notification, calendar
pointer, Slack/Teams message or action-item link may point to that view, but it
cannot create or widen a grant. Recurring pre-read resolves the current event
roster for each instance; it does not grant access retroactively and does not
put transcript/audio in the notification.

Workspace team access is a separate admin-gated policy. Its contract is
summary/view-only, role-scoped and non-retroactive unless an administrator
confirms the migration. It never grants edit, share, download or export.

The onboarding CTA is shown after the recipient can see the permitted value:
`Подключить GRAF к моим встречам`. It leads to explicit sign-in/setup and never
starts capture, creates membership or creates an account silently.

Participant batch should primarily create individual grants and update `Shared
with me`; it should not return a bearer URL per recipient. Its operation must
have a durable/idempotent run authority, bounded per-recipient outcomes and a
replay-safe result. One bad or stale attendee yields `skipped`/`failed` for that
item, not an all-or-nothing generic error.

## 8. Calendar and address-book source contract

Calendar suggestions use the owner-selected current meeting context and show
`Календарь` plus freshness. A stale/disconnected/denied source is an honest
empty/degraded state. A selected attendee must still go through the grant or
gated invitation action.

Address-book suggestions are future native-client input. The native surface asks
for limited selection permission and returns only the chosen address to the
typed-recipient flow. It does not upload the whole book. Browser-only clients do
not request desktop Contacts permission.

## 9. Token, header and analytics contract

Share/invitation URL responses use `Cache-Control: no-store`,
`Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex` and clickjacking
protection where the existing shell allows it. Raw bearer tokens are not
written to application logs, audit metadata, analytics payloads or browser
autocapture. A later URL exchange may scrub the token from the visible address.

Invitation acceptance is an exact-identity exchange: the invitation token is
never used as the long-lived grant token. The exchange is replay-safe only for
the same verified recipient and returns the same encrypted-at-rest grant token;
it does not rotate on retry. Delivery timeout after provider egress is a
first-class `outcome_unknown` state and must not trigger an automatic duplicate
send without provider idempotency/reconciliation. Runtime limits apply
independently to search, grant, rotation, acceptance and distribution. The
account-created notification has its own durable at-most-once reservation; an
ambiguous provider result is recorded and not silently resent.

Allowed metadata-only event names are bounded and do not contain meeting content:

```text
share_opened
share_recipient_selected
share_grant_created
share_invitation_requested
share_invitation_opened
share_summary_viewed
share_cta_clicked
share_signup_completed
share_revoked
```

Referral conversion is idempotent per invitation/grant and is not implemented
until its storage and retention gate is approved.
