# Infrastructure/release checklist: Feature 168

- [x] Google API client configuration exists per environment without committed secrets.
- [x] Known local/production redirect contracts and current Google verification status are recorded without credential values.
- [ ] Cloud-side client redirect inventory, consent/brand publication and Google verification are approved and proven for production.
- [x] Provider timeout, bounded retry/backoff, pagination budget and terminal states are configured and covered synthetically.
- [x] Sync job claim/lock and stale/dead-letter behavior use the existing runtime.
- [x] Postgres migration/RLS inventory and rollback are validated if schema changes.
- [x] Disposable Postgres integration run has a recorded `TWOBRAIN_DATABASE_URL` outside evidence.
- [x] Browser/embedded runtime can reach the same server truth.
- [x] Feature flag supports the approved all-users launch and global rollback.
- [x] `infra/scripts/ci-local.sh --fast` passes before implementation closeout.
- [x] Release/notarization/deploy gates are run only with separate approval.

**Audit result:** implementation/runtime foundations, browser/embedded parity,
RLS rollback evidence, real local Google provider evidence and fast CI pass.
The local callback is runtime-proven and the repository records the exact HTTPS
production callback contract. Google Cloud audience is External/In production
and the exact approved scopes are configured, but branding is not shown and
Calendar data access remains unverified. Cloud-side production redirect
inventory, secret rotation and rollout approval remain gates.
