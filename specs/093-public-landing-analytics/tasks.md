# Tasks: Public Landing Analytics

**Input**: Design documents from `/specs/093-public-landing-analytics/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required because this is a high-risk privacy/egress/public UX feature.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Phase 1 release requires all P1 stories: US1, US2, and US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm context and prepare shared documentation/evidence surfaces.

- [X] T001 Review `specs/093-public-landing-analytics/spec.md`, `specs/093-public-landing-analytics/plan.md`, `specs/093-public-landing-analytics/research.md`, `specs/093-public-landing-analytics/data-model.md`, `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`, `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`, `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`, and `specs/093-public-landing-analytics/quickstart.md`
- [X] T002 [P] Review current public landing routes and template helpers in `apps/server/src/twobrain_rec_server/public/web.py`, `apps/server/src/twobrain_rec_server/public/templates.py`, `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`, and `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T003 [P] Review current public landing tests in `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T004 [P] Review production environment example patterns in `infra/env/rec.production.env.example` and config validation patterns in `apps/server/src/twobrain_rec_server/config.py`
- [X] T005 [P] Create implementation evidence placeholder in `specs/093-public-landing-analytics/validation/implementation-evidence.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared analytics configuration, event catalog, consent constants, and disabled-by-default rendering foundation.

**Critical**: No user story work can begin until this phase is complete.

- [X] T006 [P] Add analytics settings/default tests in `apps/server/tests/unit/test_public_analytics.py`
- [X] T007 [P] Add public analytics contract tests for disabled-by-default and safe config rendering in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T008 Add public analytics runtime settings to `apps/server/src/twobrain_rec_server/config.py`
- [X] T009 Create server-side public analytics catalog and config builder in `apps/server/src/twobrain_rec_server/public/analytics.py`
- [X] T010 Wire analytics context into public template rendering in `apps/server/src/twobrain_rec_server/public/templates.py` and `apps/server/src/twobrain_rec_server/public/web.py`
- [X] T011 Create empty-safe analytics include template in `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`
- [X] T012 Create local public analytics browser controller scaffold and self-hosted CookieConsent v3.1.0 asset paths with MIT attribution in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`, `apps/server/src/twobrain_rec_server/public/static/public/cookieconsent.umd.js`, and `apps/server/src/twobrain_rec_server/public/static/public/cookieconsent.css`
- [X] T013 Include analytics template and local controller on public pages only in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T014 Update public static asset contract expectations for analytics assets, pinned local CookieConsent v3.1.0 files, MIT attribution, and no consent-manager CDN URLs in `apps/server/tests/contract/test_public_landing_contract.py`

**Checkpoint**: Analytics is disabled by default, render-only config is safe, and public pages keep existing landing/download behavior.

---

## Phase 3: User Story 1 - See Where Visitors Come From (Priority: P1)

**Goal**: A product/growth owner can understand landing visits and download progression by traffic source and campaign when consent permits analytics.

**Independent Test**: Open synthetic UTM-tagged `/` URLs, grant consent in render-only validation, click toward `/download`, and confirm source/campaign metadata and conversion event intent are present in the event catalog without private values.

### Tests for User Story 1

- [X] T015 [P] [US1] Add UTM allowlist and normalization tests in `apps/server/tests/unit/test_public_analytics.py`
- [X] T016 [P] [US1] Add provider event payload safety tests for source, medium, campaign, content, term, direct, referral, and unknown traffic in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T017 [P] [US1] Add public landing route tests for synthetic UTM-tagged visits in `apps/server/tests/unit/test_public_landing.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement UTM normalization and unsafe campaign value dropping in `apps/server/src/twobrain_rec_server/public/analytics.py`
- [X] T019 [US1] Add safe campaign metadata rendering for `/` and `/download` in `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`
- [X] T020 [US1] Implement campaign attribution extraction and event field assembly in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T021 [US1] Implement analytics-category-granted provider initialization for Yandex Metrica source attribution in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T022 [US1] Document source/campaign dashboard caveats in `specs/093-public-landing-analytics/validation/implementation-evidence.md`

**Checkpoint**: Source/campaign attribution is available for consenting public visitors without custom analytics storage.

---

## Phase 4: User Story 2 - Understand Landing Behavior And Conversion (Priority: P1)

**Goal**: A product owner can see public page progression, CTA clicks, section reach, download page view, installer download intent, and login intent as distinct conversion steps.

**Independent Test**: Complete hero/header/final CTA, direct download, installer download, and login-intent paths in render-only validation and confirm each named event uses a stable label.

### Tests for User Story 2

- [X] T023 [P] [US2] Add event catalog tests for all public event names and stable label values in `apps/server/tests/unit/test_public_analytics.py`
- [X] T024 [P] [US2] Add landing/download CTA label contract tests in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T025 [P] [US2] Add public landing regression tests for analytics data attributes without changing CTA destinations in `apps/server/tests/unit/test_public_landing.py`

### Implementation for User Story 2

- [X] T026 [US2] Add stable section and CTA metadata to `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T027 [US2] Add stable installer and login intent metadata to `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T028 [US2] Implement public page view, section seen, CTA click, installer download click, and login intent event dispatch in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T029 [US2] Implement one-event-per-action deduplication in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T030 [US2] Add Yandex goal mapping notes to `specs/093-public-landing-analytics/validation/implementation-evidence.md`

**Checkpoint**: The complete public web conversion funnel is measurable after consent.

---

## Phase 5: User Story 3 - Keep Analytics Privacy-Safe And Consentful (Priority: P1)

**Goal**: A privacy/product owner can prove public analytics is consentful, metadata-only, replay-scoped, and absent from product/content-bearing surfaces.

**Independent Test**: Run disabled, unknown, accept-all, necessary-only, customized, revoked, negative-route, and forbidden-content scenarios; confirm no unauthorized provider scripts, replay, or unsafe event fields appear.

### Tests for User Story 3

- [X] T031 [P] [US3] Add consent state machine tests for unknown, accept-all, necessary-only, customized, revoked, and copy-version changes in `apps/server/tests/unit/test_public_analytics.py`
- [X] T032 [P] [US3] Add negative-scope tests proving no public analytics on login, cabinet, admin, and API surfaces in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T033 [P] [US3] Add forbidden event field and unsafe UTM regression tests in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T034 [P] [US3] Add public consent markup, legal-link, legal-page route, category-choice, and accessibility assertions in `apps/server/tests/unit/test_public_landing.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement Russian self-hosted CookieConsent v3.1.0 copy, accept-all/necessary-only/customize/change controls, privacy/cookies/terms/analytics-consent routes, and footer/cookie-settings links in `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`, `apps/server/src/twobrain_rec_server/public/web.py`, `apps/server/src/twobrain_rec_server/public/templates.py`, `apps/server/src/twobrain_rec_server/public/templates/public/privacy.html`, `apps/server/src/twobrain_rec_server/public/templates/public/cookies.html`, `apps/server/src/twobrain_rec_server/public/templates/public/terms.html`, and `apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html`
- [X] T036 [US3] Add consent UI styling that fits the public landing and mobile layouts in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T037 [US3] Implement local consent persistence and strict no-provider-before-consent load order in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T038 [US3] Gate Yandex Session Replay and behavior recording to public pages with `behavior_replay` consent in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T039 [US3] Harden event allowlists and forbidden-data drops in `apps/server/src/twobrain_rec_server/public/analytics.py` and `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T040 [US3] Record privacy/egress/replay evidence in `specs/093-public-landing-analytics/validation/implementation-evidence.md`

**Checkpoint**: Privacy and consent gates are complete; Phase 1 cannot ship without this P1 story.

---

## Phase 6: User Story 4 - Prepare Product Activation Attribution (Priority: P2)

**Goal**: Phase 2 has a clear activation analytics contract without adding product tracking in Phase 1.

**Independent Test**: Review the Phase 2 contract and confirm the implementation includes no PostHog/product analytics code while documenting the future activation funnel and identity boundary.

### Tests for User Story 4

- [X] T041 [P] [US4] Add contract tests proving no GA4, Google Analytics, Google Ads tags, GTM, PostHog, Clarity, Amplitude, Mixpanel, Matomo, or product activation script is present in public Phase 1 assets in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T042 [P] [US4] Add documentation contract checks for Phase 2 activation event names and forbidden fields in `apps/server/tests/contract/test_public_analytics_contract.py`

### Implementation for User Story 4

- [X] T043 [US4] Refine Phase 2 activation event owner, identity, consent, and deletion-truth notes in `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- [X] T044 [US4] Record Phase 2 out-of-scope evidence in `specs/093-public-landing-analytics/validation/implementation-evidence.md`

**Checkpoint**: Product activation attribution is planned but not implemented in Phase 1.

---

## Phase 7: User Story 5 - Operate And Validate Analytics Reliably (Priority: P2)

**Goal**: Operators can safely configure, validate, and launch analytics without committing live IDs or breaking the landing.

**Independent Test**: Run local render-only and disabled validation, review env examples, and follow provider setup checklist without live credentials or committed provider identifiers.

### Tests for User Story 5

- [X] T045 [P] [US5] Add config validation tests for production-like Yandex analytics settings, Google-disabled settings, and placeholder prevention in `apps/server/tests/unit/test_public_analytics.py`
- [X] T046 [P] [US5] Add production env example contract tests for analytics variables and no live IDs in `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T047 [P] [US5] Add provider failure and duplicate initialization contract tests in `apps/server/tests/contract/test_public_analytics_contract.py`

### Implementation for User Story 5

- [X] T048 [US5] Add commented analytics environment variables to `infra/env/rec.production.env.example`
- [X] T049 [US5] Add provider setup, structured legal readiness evidence fields, and campaign readiness closeout notes to `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- [X] T050 [US5] Implement provider blocked/failure-safe browser handling in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T051 [US5] Record operations and campaign-readiness evidence in `specs/093-public-landing-analytics/validation/implementation-evidence.md`

**Checkpoint**: Analytics can be configured and validated safely, with live provider smoke deferred to an approved campaign/release gate.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Close documentation, validation, and release-readiness evidence.

- [X] T052 [P] Run focused public analytics tests from `specs/093-public-landing-analytics/quickstart.md`
- [X] T053 [P] Run `cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .`
- [X] T054 [P] Run forbidden-content scan from `specs/093-public-landing-analytics/quickstart.md`
- [X] T055 Update `[Unreleased]` in `CHANGELOG.md` for feature `093-public-landing-analytics`
- [X] T056 Run `infra/scripts/ci-local.sh` and record result in `specs/093-public-landing-analytics/validation/implementation-evidence.md`
- [X] T057 Review `specs/093-public-landing-analytics/checklists/requirements.md`, `specs/093-public-landing-analytics/checklists/privacy.md`, `specs/093-public-landing-analytics/checklists/ux.md`, and `specs/093-public-landing-analytics/checklists/operations.md` against final implementation
- [X] T058 Record high-risk validation lane, quickstart evidence, CI evidence, structured legal readiness status, no-deploy status, live-provider-smoke deferral, and campaign-readiness boundary in `specs/093-public-landing-analytics/validation/implementation-evidence.md`
- [X] T059 Mark completed tasks `[X]` only after implementation and validation evidence pass in `specs/093-public-landing-analytics/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **US1, US2, US3**: All depend on Phase 2. All are P1 and required before any release/campaign readiness claim.
- **US4, US5**: Depend on Phase 2; can proceed after P1 foundation but should not delay P1 implementation unless validation reveals gaps.
- **Phase 8 Polish**: Depends on all desired user stories and must run before closeout.

### User Story Dependencies

- **US1**: Can start after Phase 2.
- **US2**: Can start after Phase 2; complements US1 but remains independently testable.
- **US3**: Can start after Phase 2; required before any release because it owns privacy/consent/replay boundaries.
- **US4**: Can start after Phase 2; documentation and negative-contract work only.
- **US5**: Can start after Phase 2; operations validation and env readiness.

### Parallel Opportunities

- T002-T005 can run in parallel.
- T006-T007 can run in parallel before T008-T014.
- Test tasks inside each user story can run in parallel.
- US1, US2, and US3 implementation can be split by file only after shared `analytics.js` edit coordination.
- US4 documentation tasks can run in parallel with US1-US3 code tasks.
- US5 env/docs tasks can run in parallel with US4 after Phase 2.

## Parallel Example: US1

```text
Task: T015 Add UTM allowlist and normalization tests in apps/server/tests/unit/test_public_analytics.py
Task: T016 Add provider event payload safety tests in apps/server/tests/contract/test_public_analytics_contract.py
Task: T017 Add public landing route tests for synthetic UTM-tagged visits in apps/server/tests/unit/test_public_landing.py
```

## Parallel Example: US3

```text
Task: T031 Add consent state machine tests in apps/server/tests/unit/test_public_analytics.py
Task: T032 Add negative-scope tests in apps/server/tests/contract/test_public_analytics_contract.py
Task: T034 Add public consent markup, legal page routes, legal links, category choices, and accessibility assertions in apps/server/tests/unit/test_public_landing.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Implement US1, US2, and US3 as the minimum shippable Phase 1. Do not release US1/US2 without US3.
3. Validate focused quickstart scenarios and privacy gates.
4. Add US4 and US5 before closeout so future activation and operations are not ambiguous.

### Closeout

1. Run focused tests and ruff.
2. Run forbidden-content scan.
3. Run `infra/scripts/ci-local.sh`.
4. Record evidence and no-deploy/live-provider-smoke deferral.
5. Sync tasks to GitHub issues only when implementation is approved to proceed.

## Notes

- Do not commit live provider IDs, ad account IDs, cookies, visitor IDs, raw network payloads, or screenshots with provider account data.
- Do not add GA4, Google Analytics, Google Ads tags, GTM, PostHog, Clarity, Amplitude, Mixpanel, Matomo, or custom analytics storage in Phase 1.
- Do not change landing CTA destinations or product claims except for consent UI and analytics metadata.
- Do not run production deploy or live provider smoke without explicit approval.
