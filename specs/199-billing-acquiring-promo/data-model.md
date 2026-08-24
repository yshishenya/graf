# Data Model: billing acquiring and promo closeout

## Reused entities

### PromotionCampaign

Global row from Feature 140. `code_hash` is the normalized SHA-256 lookup key;
`campaign_version`, plan/cycle scope, percentage, cap, dates and enabled state
define the offer. `redeemed_count` and `reserved_count` remain the concurrency
authority. Raw code is never a column.

### PromotionRedemption

Workspace-scoped row bound to one invoice and reservation key. It stores the
hashed code and immutable list/payable amounts, then moves from `reserved` to
`redeemed`, `released` or `expired` according to provider truth.

### CheckoutPreview (ephemeral)

The browser view contains normalized-safe display fields only: cycle, list
amount, discount percent/amount, payable amount and next-period amount. It is
not persisted and has no provider identifier.

## Persistence decision

No migration is needed. The operator command writes the existing global campaign
table through the existing maintenance RLS context. A create command refuses a
duplicate hash; disable changes only `enabled` and never rewrites invoice or
redemption snapshots.
