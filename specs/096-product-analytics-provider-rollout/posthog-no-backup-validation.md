# Проверки FR-034a / T110 — 2026-10-04

High-risk-product, owner-approved narrow backup exception, Constitution8.0.0; independent requirement checklist6/0. Production backup/offsite plans cancelled, existing copies untouched; product backup/release gates unchanged.

Python3.13.3, shared existing venv, PYTHONPATH=apps/server/src.71PASS focused unit suites: provider_delivery_gate, posthog_provider, explicit_funnel, provider_config.16PASS existing integration suites provider_env/provider_readiness_blockers; policy propagated only to rec-api with required default. Ruff/whitespace/agent-context/development-process PASS. Synthetic temporary evidence/transport, not production proof. Earlier fixture used unsupported legal-basis version; corrected, all suites rerun successfully.

Independent code review found actual early secret reads in factory/readiness for rejected generic calls. Fixed by deferring key validation in loss-mode client construction and placing explicit UUID/event/closed-properties admission before readiness/secret reads. Test intercepts both provider_secrets.read_secret_file and posthog_client.read_secret_file before construction and requires zero secret reads/network for generic calls. Repeated71PASS. Actual explicit path still validates key/gates before delivery.

Default/invalid policy,11scope expansions, other providers/campaign, raw missing/stale/failed proofs, return to required, retention/access/legal/withdrawn/smoke/rollback blockers verified. Server-derived UUID remains stable across503 retry, payload carries $ip:null/$geoip_disable:true, successful retry/deduped API receipt remains ingestion_verified=false. This does not prove persisted no-IP, ClickHouse ingestion or actual provider dedupe.

## Production read-only boundary

Checked UTC: 2026-10-04T00:39:19.068782+00:00. Checkout SHA 0d4283e02a657beba8a971e7c6023cc69fef39ba; running API image SHA is separate, no claim that draft is deployed. PostHog health HTTP200; management API without existing operator session HTTP401. Flags/host/keyfile presence read without secret values, credential extraction or user-event rows. Runtime mutations0 / capture0.

New policy is not deployed. Live product/PostHog flags remain off, host/keyfile not configured. No existing operator session available for supported project changes/readback. Prior project anonymize_ips=false and84-month/noTTL report is historical, not freshly revalidated. Exact365/noIP/access/MFA/legal/delivery proofs and protected existing-key wiring remain blockers, plus ordinary frozen release candidate/full CI/deploy dry-run. No new keys/grants, cookies, DB authentication bypass, TTL/purge, browser/VoiceOver or public policy changes.

T110 implementation checks passed; exact PR CI pending before task completion. T109 remains open. No PostHog ingestion success claimed from HTTP health or mock transport.
