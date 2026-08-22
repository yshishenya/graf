# Security Requirements Checklist

- [X] RLS boundary and exact allowed contexts are explicit.
- [X] Ordinary request context is explicitly forbidden for callback-state access.
- [X] Initiating session, survivor, source identity, callback and provider-link bindings are explicit.
- [X] Invalid, stale, expired, reused and concurrent proofs fail closed without account mutation.
- [X] Cross-profile transfer requires explicit preview and confirmation.
- [X] Atomicity, idempotency, session revocation and blocker re-checks are specified.
- [X] Error/audit/evidence content is metadata-only.
- [X] Production-equivalent app-role RLS validation is required.
- [X] No policy broadening, bypass, secret handling or customer-data fixture is allowed.
