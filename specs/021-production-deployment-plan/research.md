# Research: Production Deployment Plan

## Decision: Scope first production smoke to accepted `012` ingest boundary

**Rationale**: `012-server-ingest-foundation` is the accepted backend foundation and explicitly excludes MediaScribe processing, Temporal workflow starts, desktop uploader, dashboard, sharing, retention, and deletion execution. Keeping 021 smoke at this boundary prevents false product readiness claims while still proving the production stack can accept and persist a safe ingest artifact.

**Alternatives considered**:

- Include MediaScribe submit/poll/import: rejected because `015-mediascribe-processing-pipeline` owns this behavior.
- Include dashboard visibility: rejected because `016-meeting-dashboard-review` owns dashboard surfaces.
- Delay all smoke until auth/uploader: rejected because infrastructure readiness can be proven safely with a dedicated internal smoke identity/device.

## Decision: Public endpoint can be reachable, but verdict is `infra_smoke_ready`

**Rationale**: The clarified spec allows `https://rec.2brain.dev` to be publicly reachable during first smoke. Public reachability creates product-risk ambiguity, so the plan uses a strict verdict vocabulary: successful 021 can only produce `infra_smoke_ready`; it must not be called `production_ready`, `user_rollout_ready`, or `internal_user_pilot_ready`.

**Alternatives considered**:

- Keep endpoint allowlisted until smoke passes: safer, but rejected by clarification.
- Call successful smoke `production_ready`: rejected because user auth, uploader, processing, dashboard, retention, and deletion are not implemented.

## Decision: Docker secrets plus env templates for production secrets

**Rationale**: The constitution forbids committed secrets and requires owner-controlled deployment boundaries. Docker secrets plus committed env templates provide a concrete MVP path without introducing a separate secret manager before the first infra smoke. Runtime validation must fail closed when required secrets are missing or set to local/dev defaults.

**Alternatives considered**:

- External secret manager only: stronger for later customer deployments, but heavier than needed for this MVP smoke.
- Host env vars as primary source: rejected as too easy to drift and harder to audit.
- Committed `.env` values: rejected because live values must never be committed.

## Decision: Restore/rollback rehearsal blocks readiness

**Rationale**: Deployment features are constitutionally required to include backups, restore, rollback, log redaction, and disk-full behavior. A backup that has never been restored is not enough for first production readiness. The deployment evidence must show a successful production-like restore/rollback rehearsal or a blocked verdict.

**Alternatives considered**:

- Backup only: rejected because it does not prove recovery.
- Document-only rollback: rejected because the slice owns deploy-ready implementation.

## Decision: Dedicated internal smoke identity/device

**Rationale**: `013-federated-auth-foundation` is not implemented, but 021 still needs a safe way to exercise the 012 tenant/device ingest boundary. A dedicated internal smoke identity/device avoids using real user accounts, desktop uploader credentials, or local dev seed credentials.

**Alternatives considered**:

- Wait for 013 auth: rejected because infrastructure smoke can be decoupled from user login.
- Use a real admin/user: rejected because it blurs smoke artifacts with user data.
- Reuse dev seed: rejected because production validation must not depend on development defaults.

## Decision: Store committed evidence summaries under `docs/deployments/2brain-rec/`

**Rationale**: Deployment evidence belongs in a shared ops documentation area rather than inside only the feature spec directory. This keeps production records discoverable while allowing the evidence contract to forbid raw logs, live secrets, raw audio, transcript text, and credentials.

**Alternatives considered**:

- Store all evidence under the spec directory: rejected by clarification.
- Store all evidence outside the repo: rejected because a safe summary should be reviewable with the implementation.
- Commit full raw logs: rejected because evidence must be redacted and metadata-only.

## Decision: Treat MediaScribe and Langfuse as degraded-awareness checks

**Rationale**: MediaScribe and Langfuse are owner-controlled dependencies for internal MVP, but they are not required to prove the accepted `012` ingest boundary. 021 should confirm their configured/degraded status without creating MediaScribe jobs, content traces, or content egress.

**Alternatives considered**:

- Ignore them until 015: rejected because deployment evidence should show dependency awareness.
- Make them required for readiness: rejected because it would incorrectly block the 012-only smoke.

## Decision: Smoke artifacts require cleanup or residue accounting

**Rationale**: The constitution requires deletion truth and lifecycle accounting. Smoke artifacts create real database/object-storage rows, so each run must either clean them up or record what remains, why, and who owns follow-up.

**Alternatives considered**:

- Keep smoke artifacts indefinitely for audit: rejected because it increases lifecycle burden.
- Delete only MinIO objects and keep DB rows: rejected unless a residue record explicitly says so.
