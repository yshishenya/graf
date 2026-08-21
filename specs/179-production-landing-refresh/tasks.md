# Tasks: Production Landing Refresh

**Input**: Design documents from `specs/179-production-landing-refresh/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required because the selected lane is high-risk public UX, billing, privacy, analytics and release-deploy.

## Phase 1: Setup And Baseline

**Purpose**: Preserve the approved source and establish exact pre-change behavior.

- [X] T001 Record the local approved landing source and asset inventory in `specs/179-production-landing-refresh/validation/source-inventory.md`
- [X] T002 Capture the current focused test, route, package and production-health baseline in `specs/179-production-landing-refresh/validation/baseline.md`
- [X] T003 [P] Copy only approved brand/font/product assets into `apps/server/src/twobrain_rec_server/public/static/public/` without overwriting source media

---

## Phase 2: Foundational Public Truth

**Purpose**: Create shared pricing, asset and interaction boundaries before changing page content.

- [X] T004 Add failing public-offer/catalog truth tests to `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_checkout.py`
- [X] T005 Implement a read-only, fail-closed public offer view from effective catalog rows and the exact environment/shop `billing_launch_gates` in `apps/server/src/twobrain_rec_server/public/offers.py`
- [X] T006 Integrate the public offer view with `/` while keeping checkout settings, catalog and active launch-gate state authoritative in `apps/server/src/twobrain_rec_server/public/web.py`
- [X] T007 [P] Add the progressive-enhancement script asset and static fingerprint contract in `apps/server/src/twobrain_rec_server/public/static/public/landing.js` and `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T008 Run foundational catalog/public-route tests from `specs/179-production-landing-refresh/quickstart.md`

**Checkpoint**: Public pricing can no longer diverge silently from checkout truth.

---

## Phase 3: User Story 1 — Understand GRAF And Download (Priority: P1) 🎯 MVP

**Goal**: A new visitor understands the product immediately and reaches one stable platform download page.

**Independent Test**: The hero explains recording and outputs in five seconds; every primary CTA reaches `/download`; the page exposes one working macOS universal package and non-clickable Windows/Linux states.

### Tests for User Story 1

- [X] T009 [P] [US1] Replace hero, CTA, metadata and route assertions in `apps/server/tests/unit/test_public_landing.py`
- [X] T010 [P] [US1] Add download-page and universal-installer contracts in `apps/server/tests/contract/test_public_landing_contract.py`

### Implementation for User Story 1

- [X] T011 [US1] Port the approved header and visual-free hero into `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T012 [US1] Rebuild `/download` in the new visual language while preserving one universal package in `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T013 [US1] Port the approved global typography, hero, responsive and download styles into `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T014 [US1] Update canonical/social/structured product copy in `apps/server/src/twobrain_rec_server/public/web.py` and `apps/server/src/twobrain_rec_server/public/templates/public/_meta.html`
- [X] T015 [US1] Run the independent US1 route, package and responsive smoke from `specs/179-production-landing-refresh/quickstart.md`

**Checkpoint**: Hero and download journey are independently usable without analytics or pricing interaction.

---

## Phase 4: User Story 2 — Recognize The Use Case And See The Result (Priority: P1)

**Goal**: Visitors recognize their workload and inspect recording, transcript, and meeting outcome in one accessible tabbed product stage.

**Independent Test**: The audience section clearly separates three pains and three user types; mouse and keyboard select all three product panels; all screens are current and public-safe.

### Tests for User Story 2

- [X] T016 [P] [US2] Add audience, tab semantics, no-JavaScript and synthetic-asset assertions in `apps/server/tests/unit/test_public_landing.py`
- [X] T017 [P] [US2] Add asset provenance, dimensions, responsive sources and privacy contracts in `apps/server/tests/contract/test_public_landing_contract.py`

### Implementation for User Story 2

- [X] T018 [US2] Port the approved audience/pain hierarchy and three product panels into `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T019 [US2] Implement accessible tab, pricing-switch and FAQ enhancement in `apps/server/src/twobrain_rec_server/public/static/public/landing.js`
- [X] T020 [US2] Complete audience, product-stage, screenshot and focus styles in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T021 [US2] Create or regenerate only the recording screen from current UI evidence and document provenance in `specs/179-production-landing-refresh/validation/asset-provenance.md`
- [X] T022 [US2] Run keyboard, no-JavaScript and screenshot privacy validation from `specs/179-production-landing-refresh/quickstart.md`

**Checkpoint**: Product proof is independently understandable and accessible.

---

## Phase 5: User Story 3 — Honest Commercial And Legal Conditions (Priority: P1)

**Goal**: Visitors see 1,000/10,000 RUB only when the same sale is payable and can read all relevant legal conditions.

**Independent Test**: Exact price/trial/annual-saving values agree across catalog, landing, checkout and offer; missing catalog/gates fail closed; every legal route and sitemap entry is valid.

### Tests for User Story 3

- [X] T023 [P] [US3] Update price, annual-saving and checkout-preview contracts in `apps/server/tests/contract/test_checkout.py`
- [X] T024 [P] [US3] Add sale-ready/fail-closed pricing and legal-copy tests in `apps/server/tests/unit/test_public_landing.py`
- [X] T025 [P] [US3] Add offer/sitemap/legal-link contracts in `apps/server/tests/contract/test_public_landing_contract.py`

### Implementation for User Story 3

- [X] T026 [US3] Change the approved personal descriptor to 100,000/1,000,000 minor units in `apps/server/src/twobrain_rec_server/billing/catalog.py`
- [X] T027 [US3] Add the truthful pricing block, exact 2,000 RUB annual saving, seven-day trial and FAQ into `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T028 [US3] Update payment, renewal, cancellation and refund truth in `apps/server/src/twobrain_rec_server/public/templates/public/offer.html`
- [X] T029 [P] [US3] Update product/privacy/cookies/analytics disclosures and revision dates in `apps/server/src/twobrain_rec_server/public/templates/public/privacy.html`, `apps/server/src/twobrain_rec_server/public/templates/public/cookies.html`, and `apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html`
- [X] T030 [US3] Add `/offer` to paid-launch discovery truth in `apps/server/src/twobrain_rec_server/public/web.py`
- [X] T031 [US3] Run billing/catalog/legal focused tests, query the exact environment/shop catalog and `billing_launch_gates` read-only, and record remaining operational gates in `specs/179-production-landing-refresh/validation/commercial-readiness.md`

**Checkpoint**: Source is ready for paid truth, while production checkout remains blocked until real external gates exist.

---

## Phase 6: User Story 4 — Measure The New Funnel (Priority: P2)

**Goal**: Yandex Metrica measures the new public funnel with exact safe goals and no access to product-private surfaces.

**Independent Test**: A clean public session initializes Metrica once before cookie acceptance, sends each documented goal once with safe payloads, and the provider is absent from legal/auth/cabinet/admin/meeting pages.

### Tests for User Story 4

- [X] T032 [P] [US4] Replace consent-gated context/event tests with the immediate narrow-mode contract in `apps/server/tests/unit/test_public_analytics.py`
- [X] T033 [P] [US4] Update controller, page-scope, forbidden-field and goal contracts in `apps/server/tests/contract/test_public_analytics_contract.py` and `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py`

### Implementation for User Story 4

- [X] T034 [US4] Extend the nine-event catalog and stable label allowlists in `apps/server/src/twobrain_rec_server/public/analytics.py`
- [X] T035 [US4] Implement immediate one-time Yandex initialization, safe hit and explicit goals in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T036 [US4] Remove misleading consent controls and expose accurate analytics disclosure links in `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`
- [X] T037 [US4] Wire tabs, pricing, FAQ and all CTA labels in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [ ] T038 [US4] Intercept `window.ym`, exercise all nine goals and record safe payload evidence in `specs/179-production-landing-refresh/validation/analytics-browser.md`
- [X] T039 [US4] Configure the exact nine goals in the existing Yandex counter and record redacted goal-receipt evidence in `specs/179-production-landing-refresh/validation/yandex-goals.md`

**Checkpoint**: Local and external measurement contracts match, subject to explicit legal production approval.

---

## Phase 7: Visual, Technical And Release Closeout

**Purpose**: Prove the complete integrated release and move it through review without bypassing production safeguards.

- [ ] T040 Run full focused and repository CI from `specs/179-production-landing-refresh/quickstart.md`
- [ ] T041 Run the six-viewport Browser visual/accessibility matrix, including 200% text zoom, reduced motion and disabled images, and save redacted screenshots plus findings in `specs/179-production-landing-refresh/validation/visual-qa.md`
- [X] T042 Crawl and click every internal/external link, validate every public/legal/auth/package route and record results in `specs/179-production-landing-refresh/validation/link-and-copy-review.md`
- [X] T043 Read every public text against product truth and record owner/legal blockers in `specs/179-production-landing-refresh/validation/content-review.md`
- [X] T044 Run no-secret, personal-data, asset-provenance, CSP and forbidden-provider scans and record results in `specs/179-production-landing-refresh/validation/security-privacy.md`
- [ ] T045 Run `infra/scripts/cd-remote.sh --dry-run` and record exact-SHA/backup/rollback readiness in `specs/179-production-landing-refresh/validation/deploy-dry-run.md`
- [ ] T046 Run the five-person, five-second hero-comprehension and download-finding check with owner-approved neutral participants and record anonymized outcomes in `specs/179-production-landing-refresh/validation/comprehension-test.md`
- [X] T047 Obtain explicit implementation commit approval, record it in `specs/179-production-landing-refresh/validation/release-approval.md`, then commit and push `codex/179-production-landing-refresh`
- [ ] T048 Create the PR, run checks, perform independent review, resolve findings, merge only the reviewed exact SHA and record the result in `specs/179-production-landing-refresh/validation/pr-review.md`
- [ ] T049 Create a version tag and GitHub Release with plain-language notes in `docs/releases/`
- [ ] T050 Record the owner's 2026-08-21 confirmation of external legal approval for immediate Metrica and every required billing canary/four-eyes gate in `specs/179-production-landing-refresh/validation/operational-approvals.md`
- [ ] T051 Provision or verify the production `billing_plan_versions` rows for 100,000/1,000,000 minor RUB units and the approved offer version using the documented billing runbook, then record redacted evidence in `specs/179-production-landing-refresh/validation/production-catalog.md`
- [ ] T052 Enable and verify the production public-analytics runtime flags for the approved Yandex counter without enabling private product analytics, then record redacted evidence in `specs/179-production-landing-refresh/validation/production-analytics.md`
- [ ] T053 Obtain explicit production execute approval, deploy the exact release SHA, run health/route/package/goal/container/log/rollback smoke and record it in `specs/179-production-landing-refresh/validation/production-smoke.md`
- [ ] T054 Record the live deployed SHA and post-release evidence in `docs/deployments/2brain-rec/` and update `docs/current-product-status.md`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 blocks all story implementation.
- US1 and US2 can proceed after Phase 2; both share `landing.html` and should be serialized in one checkout.
- US3 depends on the public-offer foundation and final landing structure.
- US4 depends on final interaction labels from US1–US3.
- Release closeout depends on all desired stories and zero unresolved analyze blockers.
- T039 requires authenticated Yandex counter access.
- T046 requires five neutral human participants and cannot be synthesized from automated tests.
- T050 requires external human approvals and cannot be synthesized.
- T051 requires the approved catalog/offer values plus the independent billing approvals and provider canary required by the runbook.
- T052 changes production runtime configuration and therefore runs only after the release candidate is validated and production execution is explicitly approved.
- T047 and T053 require separate explicit user approvals.

## Parallel Opportunities

- T003 can run while baseline evidence is prepared.
- Test tasks touching distinct files inside each story can be prepared together.
- Legal templates in T029 can be updated together after the commercial contract is fixed.
- Visual, content and security evidence can be collected in separate passes after implementation, but final conclusions must use the same candidate SHA.

## Implementation Strategy

1. Build the server-owned truth boundary first.
2. Port the approved visual design and download route.
3. Add product tabs and verified assets.
4. Add paid/legal truth and verify the production catalog and launch gates without inventing approvals.
5. Rewire and externally configure analytics.
6. Validate every route, text, viewport and provider payload.
7. Stop for commit approval, then PR/review/merge/release.
8. Stop again for production execute approval; deploy only if legal and billing gates are genuinely complete.

## Format Validation

All tasks use the required checkbox, sequential ID, optional parallel marker, user-story label where applicable and exact file path.
