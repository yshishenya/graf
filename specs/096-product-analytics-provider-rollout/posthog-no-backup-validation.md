# Проверки FR-034a / T110 — 2026-10-04

High-risk-product, owner-approved narrow backup exception, Constitution8.0.0; independent requirement checklist6/0. Production backup/offsite plans cancelled, existing copies untouched; product backup/release gates unchanged.

Python3.13.3, shared existing venv, PYTHONPATH=apps/server/src.71PASS focused unit suites: provider_delivery_gate, posthog_provider, explicit_funnel, provider_config.16PASS existing integration suites provider_env/provider_readiness_blockers; policy propagated only to rec-api with required default. Ruff/whitespace/agent-context/development-process PASS. Synthetic temporary evidence/transport, not production proof. Earlier fixture used unsupported legal-basis version; corrected, all suites rerun successfully.

Independent code review found actual early secret reads in factory/readiness for rejected generic calls. Fixed by deferring key validation in loss-mode client construction and placing explicit UUID/event/closed-properties admission before readiness/secret reads. Test intercepts both provider_secrets.read_secret_file and posthog_client.read_secret_file before construction and requires zero secret reads/network for generic calls. Repeated71PASS. Actual explicit path still validates key/gates before delivery.

Default/invalid policy,11scope expansions, other providers/campaign, raw missing/stale/failed proofs, return to required, retention/access/legal/withdrawn/smoke/rollback blockers verified. Server-derived UUID remains stable across503 retry, payload carries $ip:null/$geoip_disable:true, successful retry/deduped API receipt remains ingestion_verified=false. This does not prove persisted no-IP, ClickHouse ingestion or actual provider dedupe.

## Production read-only boundary

Checked UTC: 2026-10-04T00:39:19.068782+00:00. Checkout SHA 0d4283e02a657beba8a971e7c6023cc69fef39ba; running API image SHA is separate, no claim that draft is deployed. PostHog health HTTP200; management API without existing operator session HTTP401. Flags/host/keyfile presence read without secret values, credential extraction or user-event rows. Runtime mutations0 / capture0.

New policy is not deployed. Live product/PostHog flags remain off, host/keyfile not configured. No existing operator session available for supported project changes/readback. Prior project anonymize_ips=false and84-month/noTTL report is historical, not freshly revalidated. Exact365/noIP/access/MFA/legal/delivery proofs and protected existing-key wiring remain blockers, plus ordinary frozen release candidate/full CI/deploy dry-run. No new keys/grants, cookies, DB authentication bypass, TTL/purge, browser/VoiceOver or public policy changes.

Штатный infra/scripts/cd-remote.sh --dry-run --branch master выполнен: deploy_result=dry_run, candidate_gates=not_supplied, authoritative_full_required. Это metadata handoff, не проверка готового frozen candidate и не запуск. Основные product backup/deploy gates сохраняются.

T110 implementation/test завершена. Все обязательные exact PR checks подтверждены scripts/validate-pr-checks.py на implementation SHA40861900b2899b403be14ff792d249193033a102. Immutable receipt: validation/posthog-no-backup-code-ci.json. Финальная docs-only revision проверяется отдельно тем же validator; reuse source artifacts не выдаются за новые тесты. T109 remains open. No PostHog ingestion success claimed from HTTP health or mock transport.


## Exact CI provenance

Implementation source: `40861900b2899b403be14ff792d249193033a102`; checked base: `f3ec4dd95c3aa68fc7246338bd7c58908d24aee2`. Это CI-проверяемая база, не текущий production release candidate.

- governance-fast: run37165772817, attempt1, proof `sha256:51c2e74972c01c1a6cf0b760e4fe90dfc23a80b6f0cf1caa977f87434131de9c`.
- macos-pr: run37165772821, attempt1, proof `sha256:b39834888eb02d247dbd158d83e918f004df910476e0fa513a2d497372171392`.
- pr-metadata: run37165772162, attempt1, proof `sha256:7e929f09db477b952b9c87ecf6024bd819cb4f04c42b8ad6885e456cb7e893fc`.

Governance source37165772817 завершён PASS; расширенные suites836/101/2321/180/29/188 PASS (группы могут перекрываться, не суммируются),2skip. Native source37165772821PASS, metadata37165772162PASS. Text-only gate runs могут ссылаться на эти actual sources.
