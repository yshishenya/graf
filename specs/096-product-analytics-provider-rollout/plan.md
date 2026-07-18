# Implementation Plan: Product Analytics Provider Rollout

**Branch**: `096-product-analytics-provider-rollout` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/096-product-analytics-provider-rollout/spec.md`

## Summary

Roll out the live provider layer after the completed `094-product-activation-analytics` scaffold. The implementation will keep `094` as the safe event/config foundation, then add production-ready provider operations:

- self-hosted PostHog as the first-party primary product analytics workspace;
- broad PostHog autocapture enabled for every browser-rendered GRAF page because the workspace is owner-controlled;
- PostHog deployed first on the existing production server under a separate analytics domain, with service/secret/volume/resource isolation and a documented later move-out path;
- the existing `093` production Yandex Metrica counter reused as the expandable all-pages/ad/offline-conversion surface;
- live Yandex offline conversion upload for exactly `desktop_account_connected` and `first_value_session_completed`;
- runtime-only secret/config wiring, provider smoke, dashboard evidence, rollback, and legal/campaign blocker records.

This plan does not treat provider setup as paid campaign launch or product rollout readiness. Production execution remains behind later implementation, checklist, analyze, task-to-issue, review, and release gates.

## Technical Context

**Language/Version**: Python `>=3.13` for the server/provider scripts, Swift tools `6.0` for macOS direct-route checks, browser JavaScript for web PostHog/Yandex controllers, shell for Docker/remote smoke, Markdown/YAML for runbooks/evidence.

**Primary Dependencies**: Existing FastAPI/Jinja/Pydantic server stack; existing `twobrain_rec_server.product_analytics` scaffold from `094`; existing macOS analytics payload/client shell from `094`; Docker Compose production runtime; production deploy/dry-run orchestration through `infra/scripts/cd-remote.sh`; self-hosted PostHog open-source Docker Compose deployment; PostHog workspace RBAC/audit controls; Yandex Metrica Management API for offline conversions; existing public Yandex counter/goals from `093`.

**Storage**: PostHog-owned stack storage on the same production server at first rollout, isolated from GRAF service volumes and designed for later move-out. PostHog must include its own volumes/backups/restore path and at least 90-day analytics retention. Yandex stores approved page/ad/offline-conversion data in the existing production counter. Provider-held aggregates, backups, dashboard exports, offline conversion records, delivery-gap records, and deletion/retention caveats must have truthful lifecycle statements. GRAF may keep metadata-only provider readiness, smoke, delivery-gap, secret-inventory, lifecycle, and rollback evidence in docs/log-safe outputs; no raw provider payloads are committed.

**Testing**: Focused server pytest for product analytics config/router/offline/export/readiness, PostHog RBAC/audit/access model, provider retention/deletion lifecycle, browser rendered-page/provider-scope tests, macOS SwiftPM analytics/direct-egress tests, Docker Compose config/env propagation tests, PostHog deploy dry-run handoff tests, provider smoke scripts, no-secret/evidence scans, quickstart validation, and `infra/scripts/ci-local.sh` before implementation closeout.

**Risk / Validation Lane**: `high-risk-feature` plus release/deploy-gated provider infrastructure. The feature touches secrets, provider egress, Docker, production runtime, privacy, auth/cabinet/admin pages, meeting/result pages, content-bearing first-party analytics, offline conversions, dashboard evidence, rollback, legal blockers, and campaign interpretation. Full Spec Kit clarify, plan, checklist, tasks, analyze, task-to-issues, and implementation gates are required.

**Release Gate**: Planning pass is `no deploy`. Future implementation must run local/focused gates, then `infra/scripts/cd-remote.sh --dry-run`. `--execute` requires explicit release approval. Paid campaign launch remains blocked even if provider smoke passes.

**Target Platform**: GRAF production service on Docker at `2brain.dev` / `rec.2brain.pro`, a new separate analytics domain for self-hosted PostHog, browser-rendered public/auth/cabinet/product/admin surfaces, embedded desktop webview surfaces, and the native macOS desktop app for direct PostHog product analytics routing.

**Project Type**: Multi-surface provider infrastructure rollout for a FastAPI web service, native macOS app, Docker production operations, and external analytics provider configuration.

**Performance Goals**: Provider delivery must not block normal product workflows. PostHog co-location must have concrete initial CPU, memory, disk, network, log-retention, backup-retention, disk-full, and alert/review thresholds, plus rollback behavior so analytics load degrades measurement before it can starve GRAF. Provider smoke must show runtime propagation and delivery/readiness without private payload samples. Offline conversion upload must avoid duplicate product milestones.

**Constraints**: No live provider IDs, PostHog project keys, OAuth tokens, cookies, client IDs, visitor IDs, raw payloads, screenshots with visitor/account data, local paths, signed URLs, raw audio, transcript text, or content-bearing PostHog exports in git. Security credential material must be suppressed everywhere, including first-party PostHog autocapture. Yandex remains external/ad-facing and does not inherit PostHog's broader first-party allowance. Evidence stays metadata-only. Retention baseline is at least 90 days unless a category needs a shorter legal/security retention.

**Scale/Scope**: One self-hosted PostHog workspace; one reused Yandex production counter; all current browser-rendered GRAF page classes plus future-page inventory rules; all six `094` activation events; two live Yandex offline conversions; three PostHog delivery routes (server, web-direct, desktop-direct); dashboard/readiness/rollback artifacts; no paid campaign launch.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS for planning. Implementation remains blocked until later gates.

- Capture-first MVP integrity: PASS. This feature does not change recording start/stop, system-audio capture, microphone capture, routing, local package truth, or capture acceptance.
- Visible consent and user control: PASS with required disclosure artifacts. Product telemetry remains bounded by the 094 telemetry gate; active capture indicators and one-action stop are unchanged.
- Data boundary and secret discipline: PASS with strict evidence controls. PostHog is owner-controlled first-party analytics, but credential material is still forbidden everywhere. Yandex OAuth, PostHog project keys, internal secrets, counter IDs, client IDs, cookies, signed URLs, raw payloads, and content-bearing exports must not enter git or evidence.
- Deletion truth and lifecycle accounting: PASS with required retention/deletion contracts. PostHog first-party data, Yandex counter/offline conversions, provider aggregates, exported dashboards, delivery gaps, and backups must have truthful deletion statements.
- Spec-driven delivery with testable gates: PASS. Specify and clarify are complete; this plan creates research, data model, contracts, and quickstart; high-risk checklists, tasks, analyze, GitHub issue sync, and implementation remain required.
- Deployment gates: PASS with no deploy in planning. Future implementation requires Docker secrets, health checks, backups, restore, rollback, log redaction, disk/resource behavior, `cd-remote.sh --dry-run`, and explicit deploy approval before execution.

## Validation Plan

Planning validation for this pass:

- `git diff --check`
- Review [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md), [contracts/](./contracts/), and [validation/](./validation/)
- Confirm no `[NEEDS CLARIFICATION]` remains in 096 artifacts
- Confirm `AGENTS.md` managed Spec Kit marker points to this plan

Future implementation validation from the generated tasks:

- Focused server tests for config, no-live-secret validation, PostHog routing, PostHog RBAC/audit/access model, provider retention/deletion lifecycle, Yandex offline upload, page inventory, dashboard readiness, rollback, delivery gaps, and OpenAPI drift if routes change
- Browser/rendered-page tests proving PostHog autocapture configuration appears across current browser-rendered GRAF pages, while credential suppression is present and Yandex remains blocked where required
- macOS SwiftPM tests proving direct PostHog route disclosure/config/no-secret behavior and direct Yandex desktop route blocking
- Docker Compose/env/deploy-dry-run tests proving secret files, provider settings, and the separate PostHog stack handoff reach only intended services and release scripts
- Provider smoke scripts proving PostHog delivery/autocapture readiness and Yandex live offline conversion readiness with synthetic/internal metadata only
- No-secret/evidence scan across specs, docs, env templates, scripts, logs, screenshots, and generated evidence
- `infra/scripts/ci-local.sh`
- `infra/scripts/cd-remote.sh --dry-run`; `--execute` only after explicit release approval

## Project Structure

### Documentation (this feature)

```text
specs/096-product-analytics-provider-rollout/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── posthog-provider-runbook.md
│   ├── yandex-provider-runbook.md
│   ├── page-provider-inventory.md
│   ├── secret-inventory-env-propagation.md
│   ├── provider-smoke-contract.md
│   └── rollback-plan.md
├── validation/
│   ├── dashboard-evidence.md
│   └── implementation-evidence.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── config.py
│   ├── api/product_analytics.py
│   ├── public/analytics.py
│   ├── public/static/public/analytics.js
│   ├── cabinet/web.py
│   └── product_analytics/
│       ├── attribution.py
│       ├── delivery_gap.py
│       ├── event_catalog.py
│       ├── forbidden_fields.py
│       ├── identity.py
│       ├── ingest.py
│       ├── page_inventory.py
│       ├── posthog_client.py
│       ├── provider_readiness.py
│       ├── readiness.py
│       ├── replay_masking.py
│       ├── retention.py
│       ├── router.py
│       ├── telemetry_gate.py
│       └── yandex_offline.py
└── tests/
    ├── contract/test_product_activation_analytics_contract.py
    ├── integration/test_product_activation_analytics_rollout.py
    └── unit/test_product_activation_analytics.py

apps/macos/
├── RecApp/Sources/Cabinet/ProductTelemetryGateViewModel.swift
├── RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift
├── Shared/Sources/Models/ProductActivationAnalyticsModels.swift
└── Shared/Tests/ProductActivationAnalyticsContractTests.swift

infra/
├── docker-compose.yml
├── posthog/
│   ├── README.md
│   ├── docker-compose.posthog.yml
│   ├── posthog.production.env.example
│   └── backup-restore.md
├── env/rec.production.env.example
└── scripts/
    ├── run-product-analytics-smoke.sh
    ├── validate-product-analytics-pages.sh
    ├── run-product-analytics-provider-smoke.sh
    ├── validate-product-analytics-provider-pages.sh
    └── rollback-product-analytics-providers.sh

docs/
├── analytics/product-activation-analytics.md
├── analytics/product-analytics-posthog-runbook.md
├── analytics/product-analytics-yandex-runbook.md
└── analytics/product-analytics-provider-rollback.md
```

**Structure Decision**: 096 extends the existing 094 analytics package, env settings, scripts, and tests instead of introducing a parallel analytics subsystem. Provider operations/runbooks live under the 096 spec first, then implementation tasks may publish durable docs under `docs/analytics/` or `docs/deployments/` while keeping live secrets out of git.

## Phase 0 Research Output

See [research.md](./research.md). All planning unknowns are resolved for this pass.

## Phase 1 Design Output

Generated artifacts:

- [data-model.md](./data-model.md)
- [contracts/posthog-provider-runbook.md](./contracts/posthog-provider-runbook.md)
- [contracts/yandex-provider-runbook.md](./contracts/yandex-provider-runbook.md)
- [contracts/page-provider-inventory.md](./contracts/page-provider-inventory.md)
- [contracts/secret-inventory-env-propagation.md](./contracts/secret-inventory-env-propagation.md)
- [contracts/provider-smoke-contract.md](./contracts/provider-smoke-contract.md)
- [contracts/rollback-plan.md](./contracts/rollback-plan.md)
- [validation/dashboard-evidence.md](./validation/dashboard-evidence.md)
- [validation/implementation-evidence.md](./validation/implementation-evidence.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

**Status**: PASS after Phase 0/Phase 1 artifacts.

- PostHog broad autocapture is explicitly scoped as owner-controlled first-party analytics with RBAC, retention/deletion truth, disclosure, no-secret gates, metadata-only evidence, and rollback. This is not extended to Yandex.
- Yandex live offline conversion upload is limited to two milestones and requires OAuth secret-file handling, duplicate protection, provider smoke, legal/security/QA approval, and rollback.
- PostHog deployment is same-server initially but isolated by separate domain/TLS/service/volumes/secrets/resource limits/backups, linked to deploy dry-run orchestration, and includes a later move-out runbook.
- Evidence artifacts are metadata-only and include no live IDs, tokens, screenshots, private payloads, or content-bearing PostHog exports.
- Checklist, tasks, and analyze are complete for this planning pass. Implementation remains blocked until `$speckit-taskstoissues`, issue sync validation, and explicit implementation/release approvals.

## Complexity Tracking

No constitution violations are accepted in this plan. The broad PostHog autocapture posture is a product-approved first-party analytics requirement from clarification, not an exception to evidence, secret, or Yandex boundaries.
