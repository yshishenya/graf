# Contract: Account-linking journey

## Entry points

| Surface | Start | Callback | Confirm |
|---|---|---|---|
| Web | `POST /settings/provider-links/{provider}/start` | existing provider callback | `POST /settings/provider-links/{id}/confirm` |
| macOS embedded | `POST /desktop/settings/provider-links/{provider}/start` | existing provider callback | `POST /desktop/settings/provider-links/{id}/confirm` |
| API | `POST /api/v1/auth/providers/{provider}/link/start` | existing provider callback | `POST /api/v1/auth/provider-links/{id}/confirm` |
| Email web/embedded | existing email-link start/verify routes | email code verification | shared merge confirm |

## Start contract

- Require active exact session and active membership.
- Validate configured/enabled provider under request scope.
- Switch to bounded `auth_bootstrap` before callback-state creation.
- Create callback and provider-link states in one transaction.
- Return redirect/authorization URL; expected auth errors are typed, never 500.

## Confirm outcomes

| Outcome | Mutation | User action |
|---|---|---|
| direct confirmed | identity linked atomically | return to settings |
| merge preview ready | no account merge yet | review and confirm/cancel |
| merge blocked | no merge | resolve named blocker or support/back |
| proof required/stale/expired | no account mutation | start fresh flow |
| denied/conflict/unavailable | no transfer | provider-aware recovery/back |
| completed | sessions revoked, identities/access preserved | sign in again |

## Presentation contract

- Provider label is derived from the proof-bound source identity.
- Email copy remains email-specific; Yandex/VK/other use their label or neutral
  fallback.
- One primary action per state; cancel/back remains available.
- No raw IDs, subjects, nonce, tokens or customer data in HTML or errors.
