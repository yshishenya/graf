# Security/privacy/deletion checklist: Feature 168

- [x] OAuth state is random, session-bound and validated before callback exchange.
- [x] Redirect URIs are exact; production uses HTTPS and no open redirect.
- [x] Client secret/refresh token remain server-owned and encrypted.
- [x] Minimal approved Google scopes are documented and verified in source, contract tests and the successful local OAuth grant.
- [x] No desktop/browser result contains credentials or raw provider payload.
- [x] Tenant, owner, CSRF and RLS checks cover every mutation and worker read.
- [x] 401/revoked/unknown provider state fails closed and requires reconnect.
- [x] Disconnect stops new job claims before cache cleanup.
- [x] Future snapshots/participants/link candidates/reminders are purged per contract.
- [x] Matched context and meeting deletion follow explicit retention truth.
- [x] Audit/analytics fields are allow-listed metadata only.
- [x] Forbidden-content scan is clean and manually reviewed for detector-only matches.

**Audit result:** exact local redirect, approved scopes, server-owned
credentials, tenant/RLS, deletion and real local disconnect boundaries pass
local evidence. Rotation of the previously exposed client secret and production
OAuth verification remain launch gates.
