# Security Requirements Quality Checklist: Обмен встречами

**Purpose**: Validate that the security/privacy requirements are complete and
testable before implementation and rollout
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Authorization and isolation

- [x] Meeting search is explicitly bound to the actor, workspace and meeting
- [x] Internal identity results are limited to authorized active membership
- [x] Every content and mutation surface rechecks server authorization
- [x] Wrong-recipient, expired, revoked, deleted and missing states are privacy-preserving
- [x] Calendar/contact suggestions are explicitly separated from grants and consent

## Tokens, egress and lifecycle

- [x] Scope, audience, download and export invariants are defined independently
- [x] Accepted invitation expiry is explicitly bounded by invitation expiry
- [x] Revoke, rotation, deletion and stale-link behavior are specified
- [x] Raw tokens, email addresses and meeting content are excluded from audit/analytics/evidence
- [x] URL/log/referrer/autocapture token leakage controls are explicitly required
- [x] Delivery `sent`, `failed` and `outcome-unknown` meanings are distinct
- [x] Anonymous invitation acceptance uses a one-time continuation, a
  double-submit CSRF check and no bearer token in the form/login target
- [x] The invited address is encrypted at rest, cleared after acceptance/revoke/
  expiry, and is never reconstructed from client-controlled identity input
- [x] Automatic personal-account bootstrap and account-created notification are
  separate post-commit operations with deterministic, replay-safe delivery

## Abuse, privacy and rollback

- [x] Search, invite, acceptance, rotation and link-resolution rate-limit domains are named
- [x] Public-link abuse approval is required both for creation and resolution
- [x] Contact permission, source freshness and disconnect behavior are bounded
- [x] Referral attribution is opaque, idempotent and separate from access credentials
- [x] External/public/contact/referral rollout and rollback gates are independent
- [x] Deletion copy is bounded to GRAF-controlled systems and retained observability is named

## Rollout gate evidence — 2026-07-24

- Exact-email external delivery is enabled only through the operator flag and
  requires Postal, public URL, credential-encryption key and a generated
  persistent share-identity HMAC secret. The browser and macOS client receive
  none of these secrets.
- The delivery fence commits `sending` before egress; accepted provider
  response is `sent`, pre-egress configuration failure is `failed`, and a
  timeout/5xx/malformed response is `outcome_unknown` with no automatic resend.
- The anonymous magic-link action consumes the opaque continuation once, binds
  the invited address from encrypted server state, creates only a personal
  account, and commits the summary grant/session before starting the account-
  created notification workflow. The notification stores only status/failure
  metadata and masks the address in the email body.
- Durable actor/device rate limiting allows at most 10 invitation attempts per
  hour; duplicate active invitations are fenced by normalized identity hash,
  meeting and a partial unique index.
- Contract/integration evidence covers token URL/log/referrer scrubbing,
  metadata-only email and pre-auth landing content, exact verified-recipient
  acceptance, the full recording page/egress rechecks, bounded expiry, revoke
  and deletion. Public links, contacts and referral attribution remain
  disabled.

## Notes

All items pass as requirement-quality checks. The evidence above approves only
the bounded exact-email rollout; public links, contacts and referral remain
separate gates.
