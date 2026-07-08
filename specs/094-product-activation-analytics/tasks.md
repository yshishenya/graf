# Tasks: Product Activation Analytics

**Input**: Design documents from `/specs/094-product-activation-analytics/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[quickstart.md](./quickstart.md), [contracts/](./contracts/)

**Tests**: Required for this high-risk feature. Test and evidence tasks are
listed before implementation tasks inside each user-story phase.

**Organization**: Tasks are grouped by user story so each story can be
implemented and validated independently. Do not start implementation until
`$speckit-analyze`, GitHub issue sync, and separate implementation approval are
complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare traceability, evidence, and empty implementation surfaces.

- [ ] T001 Создать evidence-журнал 094 в `specs/094-product-activation-analytics/validation/implementation-evidence.md`
- [ ] T002 [P] Создать server contract test файл для analytics catalog в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T003 [P] Создать server unit test файл для analytics policy в `apps/server/tests/unit/test_product_activation_analytics.py`
- [ ] T004 [P] Создать server integration test файл для analytics rollout в `apps/server/tests/integration/test_product_activation_analytics_rollout.py`
- [ ] T005 [P] Создать macOS test файл для desktop analytics contract в `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift`
- [ ] T006 [P] Создать dashboard/readiness документ для 094 в `docs/analytics/product-activation-analytics.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core contracts, configuration, and gates that block all user
stories.

**CRITICAL**: No user story implementation can begin until this phase is
complete.

- [ ] T007 Закрыть или зафиксировать blockers из product analytics checklist в `specs/094-product-activation-analytics/checklists/product-analytics.md`
- [ ] T008 Добавить disabled-by-default product analytics settings в `apps/server/src/twobrain_rec_server/config.py`
- [ ] T009 Добавить disabled-by-default env placeholders для 094 в `infra/env/rec.production.env.example`
- [ ] T010 Пробросить runtime env placeholders для 094 только в нужные сервисы в `infra/docker-compose.yml`
- [ ] T011 Создать package skeleton для server analytics в `apps/server/src/twobrain_rec_server/product_analytics/__init__.py`
- [ ] T012 [P] Описать forbidden-field canon в `apps/server/src/twobrain_rec_server/product_analytics/forbidden_fields.py`
- [ ] T013 [P] Описать stable event catalog в `apps/server/src/twobrain_rec_server/product_analytics/event_catalog.py`
- [ ] T014 [P] Описать page-class inventory model в `apps/server/src/twobrain_rec_server/product_analytics/page_inventory.py`
- [ ] T015 [P] Описать telemetry gate state model в `apps/server/src/twobrain_rec_server/product_analytics/telemetry_gate.py`
- [ ] T016 [P] Описать safe identity model в `apps/server/src/twobrain_rec_server/product_analytics/identity.py`
- [ ] T017 Добавить no-live-secret validation для product analytics config в `apps/server/src/twobrain_rec_server/config.py`
- [ ] T018 Добавить compose/env regression tests для disabled defaults в `apps/server/tests/integration/test_product_activation_analytics_rollout.py`
- [ ] T019 Обновить quickstart implementation validation commands в `specs/094-product-activation-analytics/quickstart.md`

**Checkpoint**: Foundation ready. User story work may begin only after analyze
and implementation approval.

---

## Phase 3: User Story 1 - Understand Real Activation Funnel (Priority: P1) MVP

**Goal**: Product/growth owner can understand which sources produce real
activation, not only installer download intent.

**Independent Test**: Review contract tests and synthetic funnel evidence to
confirm that download intent, first open, account connection, auto-record,
first recording, first result view, and first value are distinct without unsafe
fields.

### Tests for User Story 1

- [ ] T020 [P] [US1] Добавить contract tests для activation event catalog в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T021 [P] [US1] Добавить unit tests для first-value и first-milestone rules в `apps/server/tests/unit/test_product_activation_analytics.py`
- [ ] T022 [P] [US1] Добавить macOS tests для desktop event payload allowlist в `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift`
- [ ] T023 [P] [US1] Добавить integration test для synthetic source-to-first-value funnel в `apps/server/tests/integration/test_product_activation_analytics_rollout.py`

### Implementation for User Story 1

- [ ] T024 [P] [US1] Реализовать activation event builder в `apps/server/src/twobrain_rec_server/product_analytics/events.py`
- [ ] T025 [P] [US1] Реализовать first milestone dedupe rules в `apps/server/src/twobrain_rec_server/product_analytics/milestones.py`
- [ ] T026 [US1] Реализовать server-mediated ingestion service в `apps/server/src/twobrain_rec_server/product_analytics/ingest.py`
- [ ] T027 [US1] Добавить product analytics API router в `apps/server/src/twobrain_rec_server/api/product_analytics.py`
- [ ] T028 [US1] Подключить product analytics API router в `apps/server/src/twobrain_rec_server/main.py`
- [ ] T029 [P] [US1] Добавить desktop analytics payload models в `apps/macos/Shared/Sources/Models/ProductActivationAnalyticsModels.swift`
- [ ] T030 [US1] Добавить desktop analytics client shell в `apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift`
- [ ] T031 [US1] Добавить account-connected event handoff в `apps/server/src/twobrain_rec_server/api/auth.py`
- [ ] T032 [US1] Добавить first-result-viewed hook без content fields в `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T033 [US1] Обновить dashboard/readiness notes для funnel в `docs/analytics/product-activation-analytics.md`

**Checkpoint**: US1 can be validated independently as a safe activation funnel.

---

## Phase 4: User Story 2 - Preserve Privacy And Consent Boundaries (Priority: P1)

**Goal**: Privacy/product owner can prove analytics cannot silently capture
meeting content, raw identity, desktop identifiers, or unapproved cross-surface
links.

**Independent Test**: Review telemetry-gate, forbidden-field, replay masking,
retention/deletion, withdrawal/refusal, and direct desktop egress evidence.

### Tests for User Story 2

- [ ] T034 [P] [US2] Добавить tests для forbidden-field rejection в `apps/server/tests/unit/test_product_activation_analytics.py`
- [ ] T035 [P] [US2] Добавить tests для telemetry gate state transitions в `apps/server/tests/unit/test_product_activation_analytics.py`
- [ ] T036 [P] [US2] Добавить rendered-page tests для replay-disabled states в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T037 [P] [US2] Добавить macOS tests для direct desktop egress gate в `apps/macos/Shared/Tests/ProductActivationAnalyticsContractTests.swift`

### Implementation for User Story 2

- [ ] T038 [US2] Реализовать forbidden-field validator в `apps/server/src/twobrain_rec_server/product_analytics/forbidden_fields.py`
- [ ] T039 [US2] Реализовать telemetry gate service в `apps/server/src/twobrain_rec_server/product_analytics/telemetry_gate.py`
- [ ] T040 [US2] Добавить telemetry gate API endpoints в `apps/server/src/twobrain_rec_server/api/product_analytics.py`
- [ ] T041 [US2] Добавить cabinet telemetry gate rendering в `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T042 [US2] Добавить desktop telemetry gate view model в `apps/macos/RecApp/Sources/Cabinet/ProductTelemetryGateViewModel.swift`
- [ ] T043 [US2] Добавить replay masking helpers в `apps/server/src/twobrain_rec_server/product_analytics/replay_masking.py`
- [ ] T044 [US2] Добавить safe CSS/classes for replay masking в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html`
- [ ] T045 [US2] Реализовать retention/deletion truth records в `apps/server/src/twobrain_rec_server/product_analytics/retention.py`
- [ ] T046 [US2] Обновить deletion/reporting copy for analytics limits в `apps/server/src/twobrain_rec_server/cabinet/deletion_rendering.py`
- [ ] T047 [US2] Обновить privacy/legal planning notes в `docs/analytics/product-activation-analytics.md`

**Checkpoint**: US2 can be validated independently as privacy/consent gate
coverage without provider rollout.

---

## Phase 5: User Story 3 - Choose A Product Analytics Provider Safely (Priority: P1)

**Goal**: Operator/product owner can approve or reject provider setup with clear
egress, hosting, retention, identity, replay, and dashboard boundaries.

**Independent Test**: Review provider decision record, PostHog/Yandex
configuration tests, offline-conversion subset tests, and provider-disabled
fallback behavior.

### Tests for User Story 3

- [ ] T048 [P] [US3] Добавить tests для PostHog disabled-by-default config в `apps/server/tests/unit/test_product_activation_analytics.py`
- [ ] T049 [P] [US3] Добавить tests для Yandex offline conversion subset в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T050 [P] [US3] Добавить tests для Yandex all-pages inventory policy в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T051 [P] [US3] Добавить tests для provider failure delivery gaps в `apps/server/tests/integration/test_product_activation_analytics_rollout.py`

### Implementation for User Story 3

- [ ] T052 [US3] Реализовать provider readiness record в `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py`
- [ ] T053 [US3] Реализовать PostHog client wrapper disabled by default в `apps/server/src/twobrain_rec_server/product_analytics/posthog_client.py`
- [ ] T054 [US3] Реализовать Yandex offline conversion exporter shell в `apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py`
- [ ] T055 [US3] Реализовать parallel measurement router в `apps/server/src/twobrain_rec_server/product_analytics/router.py`
- [ ] T056 [US3] Реализовать attribution bridge service в `apps/server/src/twobrain_rec_server/product_analytics/attribution.py`
- [ ] T057 [US3] Добавить analytics delivery gap service в `apps/server/src/twobrain_rec_server/product_analytics/delivery_gap.py`
- [ ] T058 [US3] Обновить public analytics bridge handoff в `apps/server/src/twobrain_rec_server/public/analytics.py`
- [ ] T059 [US3] Обновить public analytics browser bridge payload в `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [ ] T060 [US3] Обновить provider setup docs в `docs/analytics/product-activation-analytics.md`

**Checkpoint**: US3 can be validated independently as provider-ready but not
campaign-launched.

---

## Phase 6: User Story 4 - Prepare Rollout And Dashboard Readiness (Priority: P2)

**Goal**: Operator can launch product analytics only after dashboards, QA,
provider smoke, legal readiness, and campaign caveats are clear.

**Independent Test**: Review rollout checklist, rendered-page scope evidence,
provider smoke evidence, dashboard ownership, and campaign interpretation
caveats.

### Tests for User Story 4

- [ ] T061 [P] [US4] Добавить tests для runtime env propagation в `apps/server/tests/integration/test_product_activation_analytics_rollout.py`
- [ ] T062 [P] [US4] Добавить tests для rendered approved/blocked page classes в `apps/server/tests/contract/test_product_activation_analytics_contract.py`
- [ ] T063 [P] [US4] Добавить no-secret evidence scan coverage в `apps/server/tests/unit/test_product_activation_analytics.py`

### Implementation for User Story 4

- [ ] T064 [US4] Реализовать rollout readiness report builder в `apps/server/src/twobrain_rec_server/product_analytics/readiness.py`
- [ ] T065 [US4] Добавить product analytics smoke script в `infra/scripts/run-product-analytics-smoke.sh`
- [ ] T066 [US4] Добавить rendered-page scope validation script в `infra/scripts/validate-product-analytics-pages.sh`
- [ ] T067 [US4] Добавить dashboard owner/caveat evidence template в `specs/094-product-activation-analytics/validation/dashboard-evidence-template.md`
- [ ] T068 [US4] Обновить production env documentation for 094 в `infra/env/rec.production.env.example`
- [ ] T069 [US4] Обновить rollout section в `docs/analytics/product-activation-analytics.md`

**Checkpoint**: US4 can be validated independently as rollout-ready evidence
without paid campaign launch.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story cleanup, evidence, and release-readiness boundaries.

- [ ] T070 [P] Обновить `CHANGELOG.md` с 094 implementation scope and no-launch caveats
- [ ] T071 [P] Обновить `docs/current-product-status.md` с 094 implementation status
- [ ] T072 Запустить focused server tests for 094 и записать результат в `specs/094-product-activation-analytics/validation/implementation-evidence.md`
- [ ] T073 Запустить focused macOS tests for 094 и записать результат в `specs/094-product-activation-analytics/validation/implementation-evidence.md`
- [ ] T074 Запустить `infra/scripts/ci-local.sh` и записать результат в `specs/094-product-activation-analytics/validation/implementation-evidence.md`
- [ ] T075 Запустить no-secret/evidence scan и записать результат в `specs/094-product-activation-analytics/validation/implementation-evidence.md`
- [ ] T076 Зафиксировать selected risk/validation lane closeout в `specs/094-product-activation-analytics/validation/implementation-evidence.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies.
- **Phase 2 Foundational**: depends on Phase 1 and blocks all user stories.
- **US1, US2, US3**: depend on Phase 2 and may start in parallel after
  implementation approval, but must preserve shared contracts.
- **US4**: depends on enough of US1-US3 to produce rollout evidence.
- **Final Phase**: depends on selected story scope being implemented.

### User Story Dependencies

- **US1 (P1)**: MVP activation funnel; can be implemented after foundation.
- **US2 (P1)**: Privacy/consent boundary; can be implemented after foundation
  and may run in parallel with US1.
- **US3 (P1)**: Provider decision/setup; can be implemented after foundation
  and may run in parallel with US1/US2.
- **US4 (P2)**: Rollout readiness; depends on provider/page/event surfaces
  from US1-US3.

### Parallel Opportunities

- T002-T006 can run in parallel.
- T012-T016 can run in parallel.
- T020-T023, T034-T037, T048-T051, and T061-T063 can run in parallel within
  their stories.
- US1, US2, and US3 can be staffed in parallel after Phase 2, with coordination
  on `apps/server/src/twobrain_rec_server/product_analytics/`.

---

## Parallel Examples

### US1

```text
Task: "T020 Добавить contract tests для activation event catalog"
Task: "T021 Добавить unit tests для first-value и first-milestone rules"
Task: "T022 Добавить macOS tests для desktop event payload allowlist"
Task: "T023 Добавить integration test для synthetic source-to-first-value funnel"
```

### US2

```text
Task: "T034 Добавить tests для forbidden-field rejection"
Task: "T035 Добавить tests для telemetry gate state transitions"
Task: "T036 Добавить rendered-page tests для replay-disabled states"
Task: "T037 Добавить macOS tests для direct desktop egress gate"
```

### US3

```text
Task: "T048 Добавить tests для PostHog disabled-by-default config"
Task: "T049 Добавить tests для Yandex offline conversion subset"
Task: "T050 Добавить tests для Yandex all-pages inventory policy"
Task: "T051 Добавить tests для provider failure delivery gaps"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US2 privacy/consent blockers that are required before telemetry can
   leave GRAF-controlled surfaces.
3. Complete US1 activation funnel with server-mediated delivery first.
4. Stop and validate focused tests and evidence before enabling any provider in
   production.

### Incremental Delivery

1. Foundation: disabled-by-default config, contracts, forbidden fields, and
   event catalog.
2. US1: source-to-first-value product funnel in PostHog-ready form.
3. US2: telemetry gate, privacy, replay-unavailable, and retention/deletion
   truth.
4. US3: PostHog/Yandex provider readiness and offline conversion subset.
5. US4: rollout smoke, dashboards, and campaign-readiness caveats.

### Stop Conditions

- Stop if `$speckit-analyze` reports critical blockers.
- Stop if legal/privacy review rejects telemetry gate or provider egress.
- Stop if replay masking proof fails for a page class; use
  `replay_unavailable` instead of best-effort replay.
- Stop if runtime smoke cannot prove host env, compose config, live container
  env, rendered HTML/JS, provider reachability, and dashboard visibility.

## Notes

- `[P]` tasks use different files or can be done without waiting for incomplete
  task outputs.
- `[US#]` labels map tasks to user stories in [spec.md](./spec.md).
- Do not mark tasks `[X]` until implementation and validation evidence exist.
- Do not create provider accounts, live IDs, production deploys, or paid
  campaign changes without separate approval.
