# Tasks: Product Analytics Provider Rollout

**Input**: Design documents from `/specs/096-product-analytics-provider-rollout/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md), [checklists/provider-rollout.md](./checklists/provider-rollout.md)

**Tests**: Included because this is a high-risk provider/infrastructure rollout touching Docker, production runtime, deploy dry-run orchestration, provider egress, secrets, RBAC/audit, privacy, authenticated pages, retention/deletion lifecycle truth, offline conversions, evidence, and rollback.

**Organization**: Tasks are grouped by user story so each story can be implemented, reviewed, and validated independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or depends only on completed earlier phases.
- **[Story]**: User story label from [spec.md](./spec.md).
- Every task includes exact file paths.

## Phase 1: Setup (Shared Documentation And Infra Shape)

**Purpose**: Create durable provider operations locations before code changes.

- [ ] T001 Create the PostHog operations runbook shell in `docs/analytics/product-analytics-posthog-runbook.md` from `specs/096-product-analytics-provider-rollout/contracts/posthog-provider-runbook.md`.
- [ ] T002 [P] Create the Yandex provider runbook shell in `docs/analytics/product-analytics-yandex-runbook.md` from `specs/096-product-analytics-provider-rollout/contracts/yandex-provider-runbook.md`.
- [ ] T003 [P] Create the provider rollback runbook shell in `docs/analytics/product-analytics-provider-rollback.md` from `specs/096-product-analytics-provider-rollout/contracts/rollback-plan.md`.
- [ ] T004 [P] Create the self-hosted PostHog infra notes file in `infra/posthog/README.md`.
- [ ] T005 [P] Create the placeholder PostHog Compose file in `infra/posthog/docker-compose.posthog.yml` with no live secrets.
- [ ] T006 [P] Create the placeholder PostHog runtime env example in `infra/posthog/posthog.production.env.example` with empty/redacted values only.
- [ ] T007 [P] Create the PostHog backup and restore procedure shell in `infra/posthog/backup-restore.md`.
- [ ] T008 Record task-generation status and no-deploy state in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared config, inventory, secret, retention/deletion, deploy-handoff, and evidence controls that MUST be complete before any provider story becomes live-capable.

**Critical**: No user story implementation should claim readiness until this phase is complete.

- [ ] T009 [P] Add provider config validation tests in `apps/server/tests/unit/test_product_analytics_provider_config.py`.
- [ ] T010 [P] Add provider env propagation and secret inventory owner/rotation tests in `apps/server/tests/integration/test_product_analytics_provider_env.py`.
- [ ] T011 [P] Add provider secret redaction, owner-role, rotation-note, and redacted-evidence tests in `apps/server/tests/unit/test_product_analytics_provider_secrets.py`.
- [ ] T012 [P] Add 096 page inventory and provider retention/deletion lifecycle contract tests in `apps/server/tests/contract/test_product_analytics_page_inventory_096.py` and `apps/server/tests/contract/test_product_analytics_provider_retention.py`.
- [ ] T013 Extend 096 runtime flags, validation modes, and production fail-closed checks in `apps/server/src/twobrain_rec_server/config.py`.
- [ ] T014 Create provider config value objects for PostHog/Yandex/rollback modes in `apps/server/src/twobrain_rec_server/product_analytics/provider_config.py`.
- [ ] T015 Create provider secret-file redaction helpers in `apps/server/src/twobrain_rec_server/product_analytics/provider_secrets.py`.
- [ ] T016 Extend credential and content suppression coverage in `apps/server/src/twobrain_rec_server/product_analytics/forbidden_fields.py`.
- [ ] T017 Update 096 page-class inventory states, future-page defaults, and provider retention/deletion lifecycle states in `apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py` and `apps/server/src/twobrain_rec_server/product_analytics/retention.py`.
- [ ] T018 Update product analytics catalog output with 096 provider config and page states in `apps/server/src/twobrain_rec_server/api/product_analytics.py`.
- [ ] T019 Update rec-api-only provider env wiring, Docker secret mounts, and separate PostHog stack deploy dry-run handoff in `infra/docker-compose.yml` and `infra/scripts/cd-remote.sh`.
- [ ] T020 Update provider env placeholders, owner-role notes, rotation notes, and redacted secret inventory comments in `infra/env/rec.production.env.example`.
- [ ] T021 Update no-live-secret scans to include 096 artifacts and provider infra files in `apps/server/tests/unit/test_product_activation_analytics.py`.
- [ ] T022 Record foundational validation commands, owner/rotation inventory status, redacted evidence status, and remaining blockers in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.

**Checkpoint**: Foundation ready. Provider story work can proceed without changing the shared trust boundary.

---

## Phase 3: User Story 1 - Operate Primary Product Analytics Workspace (Priority: P1) MVP

**Goal**: Self-hosted PostHog is configured as the first-party primary product analytics workspace with same-server isolation, secret-file wiring, smoke, rollback, retention, and later move-out proof.

**Independent Test**: Review/run the PostHog runbook, Compose config, focused tests, provider smoke output, and metadata-only evidence to prove PostHog can be operated without PostHog Cloud, live secrets in git, or private payload evidence.

### Tests For User Story 1

- [ ] T023 [P] [US1] Add PostHog provider contract tests for delivery routes, RBAC/audit/access model, retention/deletion truth, and dashboard caveats in `apps/server/tests/contract/test_product_analytics_posthog_provider_contract.py`.
- [ ] T024 [P] [US1] Add PostHog client unit tests for dry-run, live-safe delivery, secret redaction, retry/loss, and no raw payload logging in `apps/server/tests/unit/test_product_analytics_posthog_provider.py`.
- [ ] T025 [P] [US1] Add PostHog Compose, secret-file, resource-threshold, and deploy dry-run handoff integration tests in `apps/server/tests/integration/test_product_analytics_posthog_stack.py`.
- [ ] T026 [P] [US1] Add PostHog provider smoke contract tests for stack health, access-model metadata, delivery, lifecycle, rollback, and no private payload output in `apps/server/tests/contract/test_product_analytics_provider_smoke_contract.py`.

### Implementation For User Story 1

- [ ] T027 [US1] Complete the self-hosted PostHog Compose stack with separate project boundary, volumes, health checks, logging, resource limits, deploy labels/metadata, and no live secrets in `infra/posthog/docker-compose.posthog.yml`.
- [ ] T028 [US1] Complete the PostHog runtime env example with placeholders, resource thresholds, retention notes, and secret-file references in `infra/posthog/posthog.production.env.example`.
- [ ] T029 [US1] Document DNS, TLS, same-server placement, resource thresholds, 90-day retention, backup/restore, disk-full behavior, RBAC/audit/access model, deploy dry-run handoff, monitoring, rollback, and move-out in `docs/analytics/product-analytics-posthog-runbook.md`.
- [ ] T030 [US1] Document PostHog volume inventory and restore rehearsal steps in `infra/posthog/backup-restore.md`.
- [ ] T031 [US1] Implement PostHog workspace readiness, RBAC/audit/access-model, retention/deletion lifecycle, deploy-handoff, and resource-threshold metadata in `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py`.
- [ ] T032 [US1] Implement PostHog project-key secret-file reading without logging values in `apps/server/src/twobrain_rec_server/product_analytics/provider_secrets.py`.
- [ ] T033 [US1] Replace the 094 blocked wrapper with 096 dry-run/live-safe PostHog delivery behavior in `apps/server/src/twobrain_rec_server/product_analytics/posthog_client.py`.
- [ ] T034 [US1] Route server-mediated PostHog delivery and delivery-gap metadata through the existing router in `apps/server/src/twobrain_rec_server/product_analytics/router.py`.
- [ ] T035 [US1] Add PostHog stack, secret, RBAC/audit access-model, server delivery, resource pressure, deploy dry-run, dashboard, lifecycle, and rollback scenarios to `infra/scripts/run-product-analytics-provider-smoke.sh`.
- [ ] T036 [US1] Fill metadata-only PostHog dashboard evidence, including RBAC/audit, retention/deletion, backup/export, and delivery-gap caveats, in `specs/096-product-analytics-provider-rollout/validation/dashboard-evidence.md`.
- [ ] T037 [US1] Record PostHog implementation evidence and validation command summaries in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.

**Checkpoint**: US1 independently proves PostHog primary workspace readiness without enabling Yandex expansion, replay, paid campaigns, or production deploy execute.

---

## Phase 4: User Story 2 - Extend Yandex Measurement Without Breaking 093 Boundaries (Priority: P1)

**Goal**: Preserve the 093 public Yandex scope, reuse the existing production counter as the expandable surface, and enable live offline upload readiness for exactly two approved product milestones.

**Independent Test**: Review/run the Yandex runbook, page inventory, offline conversion tests, rendered-page scope checks, provider smoke, and metadata-only dashboard evidence without exposing counter IDs, OAuth tokens, ClientIDs, Yclids, cookies, or raw CSV rows.

### Tests For User Story 2

- [ ] T038 [P] [US2] Add Yandex provider contract tests in `apps/server/tests/contract/test_product_analytics_yandex_provider_contract.py`.
- [ ] T039 [P] [US2] Add Yandex offline conversion unit tests for exact event subset, identity-source rules, dedupe, retry, and redacted provider status in `apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py`.
- [ ] T040 [P] [US2] Add Yandex rendered-page scope integration tests for approved public pages and blocked authenticated/admin/detail pages in `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py`.
- [ ] T041 [P] [US2] Add Yandex env/secret propagation tests in `apps/server/tests/integration/test_product_analytics_yandex_env.py`.

### Implementation For User Story 2

- [ ] T042 [US2] Implement Yandex offline conversion row building, dedupe keys, batch metadata, retry state, and raw-identifier redaction in `apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py`.
- [ ] T043 [US2] Implement Yandex OAuth secret-file loading and token redaction in `apps/server/src/twobrain_rec_server/product_analytics/provider_secrets.py`.
- [ ] T044 [US2] Update attribution bridge fields for Yandex `UserId`, `ClientId`, and `Yclid` presence without raw committed values in `apps/server/src/twobrain_rec_server/product_analytics/attribution.py`.
- [ ] T045 [US2] Update Yandex page inventory states, future-page blocking, and Webvisor/map/form proof states in `apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py`.
- [ ] T046 [US2] Preserve 093 public `/` and `/download` behavior while adding 096 inventory-aware product page decisions in `apps/server/src/twobrain_rec_server/public/analytics.py`.
- [ ] T047 [US2] Update browser Yandex gating so blocked page classes do not initialize Yandex collection in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`.
- [ ] T048 [US2] Document counter reuse, offline conversions, OAuth secret handling, all-pages inventory, Webvisor/map/form blockers, retention/deletion caveats, and rollback in `docs/analytics/product-analytics-yandex-runbook.md`.
- [ ] T049 [US2] Add Yandex counter, public baseline, blocked-page, OAuth, duplicate, dashboard, and rollback scenarios to `infra/scripts/run-product-analytics-provider-smoke.sh`.
- [ ] T050 [US2] Fill metadata-only Yandex dashboard evidence, including offline conversion retention/deletion and campaign caveats, in `specs/096-product-analytics-provider-rollout/validation/dashboard-evidence.md`.
- [ ] T051 [US2] Record Yandex implementation evidence and validation command summaries in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.

**Checkpoint**: US2 independently proves Yandex can expand only through inventory gates and upload exactly two offline conversions without approving paid campaign launch.

---

## Phase 5: User Story 3 - Govern Broad PostHog Autocapture And High-Risk Surfaces (Priority: P1)

**Goal**: Enable broad first-party PostHog autocapture for all current browser-rendered pages and future pages while preserving credential suppression, replay separation, Yandex separation, desktop direct PostHog-only egress controls, and metadata-only evidence.

**Independent Test**: Review/run page inventory tests, rendered-page tests, macOS contract tests, smoke output, and no-secret scans proving PostHog autocapture is broad, intentional, disclosed, reversible, and not confused with replay/Yandex/Webvisor/maps/forms.

### Tests For User Story 3

- [ ] T052 [P] [US3] Add rendered-page PostHog autocapture scope tests for every current browser-rendered page class and the future-page default rule in `apps/server/tests/contract/test_product_analytics_posthog_autocapture_contract.py`.
- [ ] T053 [P] [US3] Add credential suppression and private DOM masking tests for legal, login/signup, auth callback, cabinet, admin, meeting detail, upload, deletion, embedded, and error page classes in `apps/server/tests/integration/test_product_analytics_autocapture_pages.py`.
- [ ] T054 [P] [US3] Add replay/Webvisor separation tests in `apps/server/tests/contract/test_product_analytics_replay_webvisor_boundaries.py`.
- [ ] T055 [P] [US3] Add macOS direct PostHog-only egress contract tests in `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift`.

### Implementation For User Story 3

- [ ] T056 [US3] Create browser provider context helpers for PostHog autocapture, Yandex gating, replay state, disclosure, retention/deletion truth, and private attributes in `apps/server/src/twobrain_rec_server/product_analytics/browser_context.py`.
- [ ] T057 [US3] Add PostHog autocapture config and credential-suppression metadata to public analytics context in `apps/server/src/twobrain_rec_server/public/analytics.py`.
- [ ] T058 [US3] Initialize PostHog autocapture separately from Yandex and replay in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`.
- [ ] T059 [US3] Create a reusable product analytics template partial for PostHog/Yandex config with no private payloads in `apps/server/src/twobrain_rec_server/public/templates/public/_product_analytics_provider.html`.
- [ ] T060 [US3] Include the product analytics provider partial on public pages while preserving 093 public Yandex behavior in `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`.
- [ ] T061 [US3] Include product analytics provider context and private attributes in the cabinet shell in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`.
- [ ] T062 [US3] Include product analytics provider context and Yandex-blocked/admin-private attributes in `apps/server/src/twobrain_rec_server/admin/templates/admin/base.html`.
- [ ] T063 [US3] Extend private analytics attributes for PostHog/Yandex suppression in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html`.
- [ ] T064 [US3] Update replay masking decisions so broad PostHog autocapture remains distinct from PostHog replay and Yandex Webvisor/maps/forms in `apps/server/src/twobrain_rec_server/product_analytics/replay_masking.py`.
- [ ] T065 [US3] Extend macOS analytics models with first-party PostHog direct route disclosure/config fields and Yandex direct-route blocking in `apps/macos/Shared/Sources/Models/ProductActivationAnalyticsModels.swift`.
- [ ] T066 [US3] Extend the macOS analytics client with PostHog-only direct provider request construction and no-secret validation in `apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift`.
- [ ] T067 [US3] Add PostHog autocapture page validation and direct desktop route checks to `infra/scripts/validate-product-analytics-provider-pages.sh`.
- [ ] T068 [US3] Update product analytics docs for broad first-party PostHog autocapture, replay separation, and Yandex separation in `docs/analytics/product-activation-analytics.md`.

**Checkpoint**: US3 independently proves broad PostHog autocapture is governed and reversible, while Yandex/Webvisor/replay remain separately gated.

---

## Phase 6: User Story 4 - Prove Rollback, Dashboards, And Blockers Before Rollout Claims (Priority: P2)

**Goal**: Produce metadata-only provider smoke, dashboard readiness, rollback, legal/campaign blocker, and implementation evidence so provider setup is not misread as product rollout readiness or paid campaign launch readiness.

**Independent Test**: Review/run smoke scripts, rollback scripts, dashboard evidence checks, no-secret scans, and implementation evidence to prove measurement can be disabled without blocking normal product workflows.

### Tests For User Story 4

- [ ] T069 [P] [US4] Add provider smoke output contract tests in `apps/server/tests/contract/test_product_analytics_provider_smoke_output.py`.
- [ ] T070 [P] [US4] Add rollback contract tests for provider disable modes, PostHog stack stop, deploy dry-run/move-out rollback, and measurement-gap-only impact in `apps/server/tests/contract/test_product_analytics_provider_rollback.py`.
- [ ] T071 [P] [US4] Add dashboard evidence metadata-only tests for RBAC/audit, retention/deletion, provider-gap, campaign, and no-export caveats in `apps/server/tests/contract/test_product_analytics_dashboard_evidence.py`.
- [ ] T072 [P] [US4] Add release/blocker separation tests for legal, privacy, security, QA, RBAC/audit, lifecycle, deploy dry-run, product rollout, and campaign launch states in `apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py`.

### Implementation For User Story 4

- [ ] T073 [US4] Complete unified provider smoke output for PostHog, Yandex, dashboards, no-secret status, and rollback status in `infra/scripts/run-product-analytics-provider-smoke.sh`.
- [ ] T074 [US4] Complete page/provider validation output for PostHog autocapture, Yandex blocked classes, replay state, and private attributes in `infra/scripts/validate-product-analytics-provider-pages.sh`.
- [ ] T075 [US4] Implement provider rollback switches and metadata-only verification output in `infra/scripts/rollback-product-analytics-providers.sh`.
- [ ] T076 [US4] Document rollback targets, product-impact rules, restoration, PostHog stack stop, deploy dry-run rollback, move-out failure handling, and evidence boundaries in `docs/analytics/product-analytics-provider-rollback.md`.
- [ ] T077 [US4] Extend readiness/blocker reporting for legal, privacy, security, QA, disclosure, dashboard, RBAC/audit, retention/deletion lifecycle, deploy dry-run, provider smoke, product rollout, and campaign launch states in `apps/server/src/twobrain_rec_server/product_analytics/readiness.py`.
- [ ] T078 [US4] Update dashboard evidence with provider owner, purpose, caveats, blocker status, and rollback state in `specs/096-product-analytics-provider-rollout/validation/dashboard-evidence.md`.
- [ ] T079 [US4] Update implementation evidence with smoke, rollback, dashboard, blocker, and no-secret scan status in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T080 [US4] Update quickstart with final 096 validation command order and explicit no-paid-campaign/no-product-rollout statements in `specs/096-product-analytics-provider-rollout/quickstart.md`.

**Checkpoint**: US4 independently proves provider setup has reviewable evidence, rollback, and blockers before any rollout or campaign claims.

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Final quality gates, evidence, changelog, and release/deploy dry-run. No paid campaign launch and no `cd-remote.sh --execute` without separate explicit approval.

- [ ] T081 [P] Run focused server product analytics tests and record results in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T082 [P] Run focused macOS product analytics tests and record results in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T083 [P] Run `infra/scripts/run-product-analytics-provider-smoke.sh` and record metadata-only output in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T084 [P] Run `infra/scripts/validate-product-analytics-provider-pages.sh` and record metadata-only output in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T085 [P] Run `infra/scripts/rollback-product-analytics-providers.sh` and record metadata-only output in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T086 Run no-secret/evidence scans across `specs/096-product-analytics-provider-rollout/`, `docs/analytics/`, `infra/`, `apps/server/src/twobrain_rec_server/product_analytics/`, and `apps/macos/`.
- [ ] T087 Run `infra/scripts/ci-local.sh` and record summary evidence in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T088 Run `infra/scripts/cd-remote.sh --dry-run`, including separate PostHog stack packaging/routing/secret checks, and record summary evidence in `specs/096-product-analytics-provider-rollout/validation/implementation-evidence.md`.
- [ ] T089 Update behavior/ops/release notes for 096 in `CHANGELOG.md`.
- [ ] T090 Verify final task completion states, dependency order, and selected risk/validation lane in `specs/096-product-analytics-provider-rollout/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies. Can start immediately.
- **Phase 2 Foundational**: Depends on Phase 1. Blocks every user story.
- **US1 PostHog**: Depends on Phase 2.
- **US2 Yandex**: Depends on Phase 2.
- **US3 Autocapture/Governance**: Depends on Phase 2; can proceed in parallel with US1/US2 after shared browser context decisions are stable.
- **US4 Rollback/Dashboards/Blockers**: Depends on Phase 2 and should consume outputs from US1, US2, and US3 before final evidence is marked complete.
- **Phase 7 Polish**: Depends on all implemented user stories selected for the release slice.

### User Story Dependencies

- **US1 (P1)**: MVP provider workspace. No dependency on US2/US3 after foundation.
- **US2 (P1)**: Yandex expansion/offline conversions. No dependency on US1 after foundation, but final smoke should run with parallel provider mode.
- **US3 (P1)**: Broad PostHog autocapture governance. No dependency on US2 after foundation; should align with US1 PostHog config and Yandex blocked-page states.
- **US4 (P2)**: Evidence/rollback/blockers. Depends on the story slices whose readiness it records.

### Within Each User Story

- Tests come first and should fail before implementation.
- Config/secret/retention/access helpers precede provider clients.
- Provider clients precede router/smoke integration.
- PostHog Compose/env/runbook changes precede `infra/scripts/cd-remote.sh --dry-run` handoff and provider smoke.
- RBAC/audit access model and retention/deletion lifecycle truth precede dashboard evidence pass status.
- Page inventory precedes rendered-page provider snippets.
- Yandex inventory, identity-source rules, and duplicate protection precede offline dashboard readiness.
- Smoke/rollback scripts precede final dashboard/evidence completion.

---

## Parallel Execution Examples

### User Story 1

```text
T023 PostHog provider contract tests with RBAC/audit/lifecycle coverage in apps/server/tests/contract/test_product_analytics_posthog_provider_contract.py
T024 PostHog client unit tests in apps/server/tests/unit/test_product_analytics_posthog_provider.py
T025 PostHog Compose/deploy handoff integration tests in apps/server/tests/integration/test_product_analytics_posthog_stack.py
T026 PostHog smoke contract tests with access/lifecycle coverage in apps/server/tests/contract/test_product_analytics_provider_smoke_contract.py
```

### User Story 2

```text
T038 Yandex provider contract tests in apps/server/tests/contract/test_product_analytics_yandex_provider_contract.py
T039 Yandex offline unit tests in apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py
T040 Yandex page scope integration tests in apps/server/tests/integration/test_product_analytics_yandex_page_scope.py
T041 Yandex env propagation tests in apps/server/tests/integration/test_product_analytics_yandex_env.py
```

### User Story 3

```text
T052 PostHog autocapture contract tests for all current pages/future defaults in apps/server/tests/contract/test_product_analytics_posthog_autocapture_contract.py
T053 Autocapture credential suppression page integration tests in apps/server/tests/integration/test_product_analytics_autocapture_pages.py
T054 Replay/Webvisor boundary tests in apps/server/tests/contract/test_product_analytics_replay_webvisor_boundaries.py
T055 macOS direct PostHog-only tests in apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift
```

### User Story 4

```text
T069 Smoke output contract tests in apps/server/tests/contract/test_product_analytics_provider_smoke_output.py
T070 Rollback contract tests in apps/server/tests/contract/test_product_analytics_provider_rollback.py
T071 Dashboard evidence tests with RBAC/audit/lifecycle caveats in apps/server/tests/contract/test_product_analytics_dashboard_evidence.py
T072 Readiness blocker tests with deploy/lifecycle/campaign separation in apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to make self-hosted PostHog operationally ready, including RBAC/audit, lifecycle truth, and deploy dry-run handoff.
3. Stop and validate US1 independently before enabling Yandex expansion or broad page wiring claims.

### Required P1 Rollout Slice

1. Complete US1, US2, and US3.
2. Validate each story independently.
3. Complete US4 to prove rollback, dashboards, blockers, and metadata-only evidence.

### Release Gate

1. Complete Phase 7 through `infra/scripts/cd-remote.sh --dry-run`.
2. Do not run `infra/scripts/cd-remote.sh --execute` without separate explicit approval.
3. Do not mark paid campaign launch or product rollout readiness approved in 096.

## Notes

- `[P]` tasks are safe to parallelize only after their phase dependencies are complete.
- `tasks.md` is the source of truth for implementation status.
- Mark a task `[X]` only after implementation and validation evidence are recorded.
- Do not commit live provider IDs, tokens, cookies, client IDs, raw payloads, screenshots with visitor/account data, local paths, signed URLs, meeting content, transcripts, or audio.
