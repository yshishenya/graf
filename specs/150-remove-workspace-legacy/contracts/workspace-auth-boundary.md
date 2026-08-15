# Contract: Workspace/Auth Boundary

## Signup and login

- Public forms do not accept a workspace identifier.
- Server may use internal login workspace for policy/callback state.
- Callback on internal anchor selects the user's personal workspace regardless of stale internal membership.
- Repeated and concurrent signup/login reuse one personal workspace.

## Corporate access

- Corporate membership requires explicit identity-verified enrollment; initial owner uses separate operator provisioning.
- Pending invitation, domain or provider claim never creates membership.
- Invitation/offer customer target may not be personal or internal bootstrap.

## Listing and activation

- Internal anchor is excluded before response construction.
- Only active server-verified customer memberships are returned.
- Direct activation of internal anchor is denied.
- Personal display: `Моё пространство`, `Личное · Владелец`.
- Corporate display: real name, `Рабочее пространство · <роль>`.

## Tenant and billing authorization

- Shared tenant validation rejects internal ID even if stale membership/device/session exists.
- Rejected internal scope cannot read/write meetings, uploads, settings, usage or billing.
- Self-serve billing requires validated personal owner scope; corporate and internal scopes are denied.

## Recovery

- Revoked corporate session is invalidated; valid personal session remains recovery path.
- Missing personal workspace is repaired idempotently; ambiguous repair fails closed.
