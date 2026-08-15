# Data Model: Remove Workspace Legacy

Новых таблиц feature не добавляет.

## Internal auth anchor

- Identified by deployment-owned login workspace configuration.
- May own provider/auth policy and callback state required by current RLS flow.
- Has zero customer memberships, sessions, devices, invitations/offers, meetings/uploads/recordings, usage, referrals, subscriptions, invoices and payment operations.
- Never appears as customer session context or selector item.

## Personal workspace

- `kind = personal`.
- Exactly one per `(organization_id, owner_user_id)` through existing unique index.
- Owner has one active `owner` membership.
- Canonical visible name: `Моё пространство`.
- Default customer target for signup and login through internal anchor.

## Corporate workspace

- `kind = corporate`, real visible name.
- Access requires active membership from explicit enrollment.
- Initial owner is provisioned only through separate operator/admin flow.

## Invariants

1. Internal auth anchor has no customer membership or product data.
2. Every active customer session references personal or explicitly joined corporate workspace.
3. Canonical user has one personal owner workspace.
4. Pending offers do not imply membership.
5. Revoked corporate access does not affect personal ownership and never retargets queued work.
6. Self-serve billing mutations require active personal owner scope.

## Pre-launch cleanup gate

Backup and aggregate counts precede cleanup. Any meeting, upload, recording, usage, referral, subscription, invoice or payment row stops cleanup. Evidence contains counts only. The one-shot inventory is release evidence, not a permanent runtime CLI.
