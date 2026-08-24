# Infrastructure checklist: Feature 195

**Статус**: частично закрыт локальными contract/unit checks; live и production
пункты остаются незакрытыми.

## MediaScribe boundary

- [ ] Target runtime `/version` and `/v1/capabilities` captured in metadata-only evidence.
- [x] Adapter uses `/v1` only; no new `/jobs` or `/auth/login` call remains.
- [x] API key is server-side, secret-mounted and absent from desktop/browser config.
- [x] Connect/upload/request timeouts, maximum body size and proxy limits are explicit.
- [x] `Retry-After`, `Location`, `X-Request-ID`, `Idempotency-Replayed` and job headers are preserved safely.
- [x] Provider active-job and upload limits are mapped to GRAF admission.
- [x] Single/dual track choice is proven against canonical audio artifacts and capabilities.

## Temporal

- [ ] Worker and server use a compatible Temporal SDK/server version.
- [ ] New workflow task queue, worker deployment and worker versioning are defined.
- [x] Workflow uses durable timers; no workflow-level `asyncio.sleep` or wall-clock nondeterminism.
- [x] Activities have bounded timeouts, heartbeat, cancellation and safe retry policy.
- [x] Manual command Update/Signal compatibility is verified with the installed SDK.
- [x] Old histories replay under the new workflow version; migration plan covers running legacy workflows.
- [x] Payload/history size budget is tested; audio/transcript/raw provider JSON never enters history.
- [x] Worker restart and task-queue backlog recovery are tested with Postgres projection.
- [ ] Fairness/active-job limits are observed before adding priority or per-tenant queues.

## PostgreSQL and storage

- [x] Schema change is additive or has a tested migration/rollback boundary.
- [x] Active attempt/provider job uniqueness and same-key tombstone retention are enforced in DB.
- [x] RLS/tenant authorization covers every new field/table and every retry command.
- [x] Result import is hash/idempotent and deletion epoch prevents late writes.
- [x] Object storage references are owner-controlled; signed URLs are never persisted in user projection or logs.
- [ ] Existing backup/restore and processing migration checks pass.

## Operations and rollout

- [ ] Dashboards cover first usable result, retryable failures, manual retry and unknown-outcome reconciliation.
- [ ] Alerts cover stale workflows, exhausted deadlines, duplicate-job invariant and queue starvation.
- [ ] Rollout starts with synthetic fixture/canary; production migration and deploy require separate approval.
- [ ] Rollback preserves old workflow histories and does not issue blind new provider jobs.
- [ ] Release evidence follows `release-and-validation.md`; this planning slice performs no deploy.

Локально подтверждены adapter contract, Temporal workflow tests, migration
upgrade/downgrade, worker restart projection, full local CI и isolated
PostgreSQL matrix. Не подтверждены live cluster compatibility, capabilities/
version against the deployed MediaScribe, dashboards/alerts, backup/restore и
rollout/rollback.
