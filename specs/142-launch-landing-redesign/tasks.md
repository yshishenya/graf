# Tasks: Launch Landing Redesign

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/public-launch-experience.md`, `quickstart.md`

## Phase 1: Setup

- [X] T001 Record the selected visual checksum and asset inventory in `specs/142-launch-landing-redesign/design-qa.md`
- [X] T002 [P] Prepare privacy-cleared real GRAF product proof assets in `apps/server/src/twobrain_rec_server/public/static/public/landing-outcome-proof.png` and `apps/server/src/twobrain_rec_server/public/static/public/landing-recording-proof.png`

## Phase 2: Foundational Contracts

- [X] T003 Update public truth, real-asset, CTA and platform-status assertions before implementation in `apps/server/tests/unit/test_public_landing.py`
- [X] T004 [P] Update local asset, accessibility, reduced-motion and no-client-toolchain assertions in `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T005 [P] Reconcile the selected mock with product truth and record the final copy matrix in `specs/142-launch-landing-redesign/contracts/public-launch-experience.md`

## Phase 3: User Story 1 — Understand GRAF immediately (P1)

**Goal**: Deliver the platform-neutral editorial hero, accessible navigation and clear download path.

**Independent Test**: A first-time visitor can identify product purpose and reach `/download` in under 10 seconds at desktop and mobile widths.

- [X] T006 [US1] Replace the public header and hero with the selected editorial hierarchy in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T007 [US1] Implement the near-black violet design tokens, desktop grid, hero spacing, focus states and mobile header behavior in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T008 [US1] Update the public page title and metadata without universal capture claims in `apps/server/src/twobrain_rec_server/public/web.py`

## Phase 4: User Story 2 — Validate product promises (P1)

**Goal**: Present three focused proof chapters using truth-safe copy and real GRAF UI.

**Independent Test**: Each proof chapter has one clear promise, one matching real product state and synthetic/no-PII content.

- [X] T009 [US2] Implement the numbered `01 / В привычных сервисах` recording chapter and real proof image in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T010 [US2] Implement the numbered `02 / После встречи` outcome chapter and real accepted-outcome image in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T011 [US2] Implement the numbered `03 / Под контролем` visible Pause/Stop chapter in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T012 [US2] Implement alternating editorial chapter layout, screenshot treatment, readable captions and responsive proof stacking in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`

## Phase 5: User Story 3 — Reach the available platform (P2)

**Goal**: Make `/download` a clear, honest platform availability page.

**Independent Test**: macOS has the only download action; Windows and Linux are readable non-interactive planned statuses.

- [X] T013 [US3] Replace the download hero and platform availability structure in `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T014 [US3] Remove obsolete local-signing bypass copy, retain the runtime-mounted package URL and present release-policy-compatible macOS trust wording in `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T015 [US3] Add responsive platform rows, status labels and non-interactive future-platform styling in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`

## Phase 6: User Story 4 — Understand payment boundary (P2)

**Goal**: Preserve the ruble/YooKassa product decision without publishing an unapproved amount or checkout claim.

**Independent Test**: Public pages contain no price, payment action or YooKassa availability claim before the billing source of truth is active.

- [X] T016 [US4] Add contract assertions that public templates contain no hardcoded price, placeholder amount or premature YooKassa checkout claim in `apps/server/tests/unit/test_public_landing.py`
- [X] T017 [US4] Document the exact future billing-catalog handoff and reserved ruble-payment copy in `specs/142-launch-landing-redesign/contracts/public-launch-experience.md`

## Phase 7: Polish And Cross-Cutting Validation

- [X] T018 Run the focused public landing/analytics checks from `specs/142-launch-landing-redesign/quickstart.md` and record results in `specs/142-launch-landing-redesign/design-qa.md`
- [X] T019 Capture and compare the 1440, 390 and 320 CSS px landing/download states against `specs/142-launch-landing-redesign/design/selected-direction-3.png`, fix P0–P2 issues and set `final result: passed` in `specs/142-launch-landing-redesign/design-qa.md`
- [X] T020 Update launch-facing behavior notes in `CHANGELOG.md` and run `infra/scripts/ci-local.sh --fast`

## Phase 8: User Feedback Refinement

- [X] T021 Re-audit the shipped composition against the selected direction, current product references and 2026 interface guidance; record evidence in `specs/142-launch-landing-redesign/evidence/ux-audit-v2/` and reopen `specs/142-launch-landing-redesign/design-qa.md`
- [X] T022 Self-host the Cyrillic variable font and rebuild the type scale, line lengths, controlled wrapping and vertical rhythm in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T023 Recompose the landing IA so each product proof supports one USP and the managed Russian/local model contour becomes chapter 03 in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T024 Refine CTA geometry, VKS rail, responsive states, reduced-motion behavior and download copy in `apps/server/src/twobrain_rec_server/public/templates/public/download.html` and `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T025 Capture and compare landing/download at 1440, 1024, 768, 390, 320 and 280 CSS px; fix every actionable P0–P2 finding and update `specs/142-launch-landing-redesign/design-qa.md`
- [X] T026 Run focused public checks and `infra/scripts/ci-local.sh --fast`, update `CHANGELOG.md`, and record the passed visual result separately from the unsigned-package release blocker

## Phase 9: Release Sync And Atmospheric Refinement

- [X] T027 Fast-forward the feature worktree to current `origin/master`, preserve the active Feature 142 changes, and replace the stale local installer with the checksum-matched `v2026.08.07.2` Developer ID/notarized/stapled package
- [X] T028 Add one optimized local atmospheric raster and compositor-safe CSS motion in `apps/server/src/twobrain_rec_server/public/static/public/landing.css` without adding a frontend runtime or animation dependency
- [X] T029 Recompose the real hero, recording and outcome proofs in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` so they feel integrated and remain readable on desktop and mobile
- [X] T030 Refine landing wording, punctuation, manual heading wraps and responsive type behavior in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T031 Repeat current-source audit, combined visual QA, reduced-motion/interaction checks, focused public tests and `infra/scripts/ci-local.sh --fast`; update `design-qa.md` and `CHANGELOG.md`

## Phase 10: Product Screenshot Refinement

- [X] T032 Capture fresh current GRAF transcript and accepted-outcome states with synthetic, role-based content in `specs/142-launch-landing-redesign/evidence/screenshot-refinement-v6/`
- [X] T033 Replace repeated technical crops with separate transcript, recording-control and outcome proofs in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T034 Rebuild desktop and mobile screenshot framing, readable mobile close-ups and full-width outcome hierarchy in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T035 Update local-asset contracts for the current product proof inventory in `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T036 Complete combined source/implementation QA, independent screenshot reviews, focused public checks and `infra/scripts/ci-local.sh --fast`; record results in `specs/142-launch-landing-redesign/design-qa.md` and `CHANGELOG.md`

## Phase 11: Linked Outcomes And Auto-record Proof

- [X] T037 Capture a current GRAF transcript and accepted-outcome pair for one synthetic role-based dialogue, with action and decision source timestamps aligned, in `apps/server/src/twobrain_rec_server/public/static/public/landing-transcript-proof.png`, `apps/server/src/twobrain_rec_server/public/static/public/landing-transcript-proof-mobile.png`, `apps/server/src/twobrain_rec_server/public/static/public/landing-outcome-proof.png` and `apps/server/src/twobrain_rec_server/public/static/public/landing-outcome-proof-mobile.png`
- [X] T038 Render and focus the current target-scoped auto-record settings with synthetic selections in `apps/server/src/twobrain_rec_server/public/static/public/landing-autorecord-proof-focus.png`
- [X] T039 Implement the native `Расшифровка / Итоги` hero switch, auto-record flow and truth-safe calendar placement in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T040 Update local proof, wording and interaction contracts in `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T041 Complete combined source/implementation QA, responsive overflow checks, focused public tests and `infra/scripts/ci-local.sh --fast`; record the closeout in `specs/142-launch-landing-redesign/design-qa.md` and `CHANGELOG.md`

## Phase 12: Product-proof Depth And Application Breadth

- [X] T042 Re-capture the current transcript and outcome states as one 18-minute synthetic meeting with three role-based participants in `apps/server/src/twobrain_rec_server/public/static/public/landing-transcript-proof.png`, `apps/server/src/twobrain_rec_server/public/static/public/landing-transcript-proof-mobile.png`, `apps/server/src/twobrain_rec_server/public/static/public/landing-outcome-proof.png` and `apps/server/src/twobrain_rec_server/public/static/public/landing-outcome-proof-mobile.png`
- [X] T043 Re-render the current native auto-record settings at a readable high resolution in `apps/server/src/twobrain_rec_server/public/static/public/landing-autorecord-proof-focus.png`
- [X] T044 Replace the generic recording stepper, benefit chips and outcome categories with the current registry proof, truth-safe calendar context and meeting-specific outcome ledger in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- [X] T045 Refine the responsive framing, application rail, chapter labels and outcome ledger in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T046 Link the public application count to the current target registry and update public landing contracts in `apps/server/tests/contract/test_public_landing_contract.py` and `apps/server/tests/unit/test_public_landing.py`
- [X] T047 Complete desktop/mobile visual QA, overflow checks, focused public tests and independent UX/visual review; record evidence in `specs/142-launch-landing-redesign/evidence/screenshot-refinement-v8/`, `specs/142-launch-landing-redesign/design-qa.md` and `CHANGELOG.md`

## Phase 13: Compact Hero Proof Carousel

- [X] T048 [US1] Recompose the hero product proof as a side-by-side viewport with an automatic transcript-to-outcome slide in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/static/public/landing.css`
- [X] T049 [US1] Update landing markup and CSS contracts for the non-interactive progress rail, reduced-motion fallback and removal of manual hero tabs in `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_public_landing_contract.py`
- [X] T050 [US1] Capture desktop/mobile hero states and run focused public checks; record evidence in `specs/142-launch-landing-redesign/evidence/hero-carousel-v1/`

## Phase 14: Final Legal, Consent And Responsive Hardening

- [X] T051 [P] Extend public legal, consent, platform-truth, SEO and responsive contracts in `apps/server/tests/unit/test_public_landing.py`, `apps/server/tests/contract/test_public_landing_contract.py` and `apps/server/tests/contract/test_public_analytics_contract.py`
- [X] T052 Replace draft public privacy, cookies, product terms, payment conditions and analytics consent with final plain-Russian editions in `apps/server/src/twobrain_rec_server/public/templates/public/privacy.html`, `apps/server/src/twobrain_rec_server/public/templates/public/cookies.html`, `apps/server/src/twobrain_rec_server/public/templates/public/terms.html`, `apps/server/src/twobrain_rec_server/public/templates/public/offer.html` and `apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html`
- [X] T053 Enforce category-scoped attribution, query-safe Yandex page hits and provider disable-on-revoke in `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`
- [X] T054 Fix cookie-category contrast, hero/download/legal overflow, legal typography and mobile proof selection in `apps/server/src/twobrain_rec_server/public/static/public/landing.css`, `apps/server/src/twobrain_rec_server/public/templates/public/landing.html` and `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- [X] T055 Add public response hardening, canonical/social metadata, `robots.txt`, `sitemap.xml` and versioned static cache policy in `apps/server/src/twobrain_rec_server/public/templates.py`, `apps/server/src/twobrain_rec_server/public/web.py` and `apps/server/src/twobrain_rec_server/main.py`
- [X] T056 Reconcile launch wording with current capture, calendar, AI-egress, installer and billing truth in `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`, `apps/server/src/twobrain_rec_server/public/templates/public/download.html` and `apps/server/src/twobrain_rec_server/public/templates/public/_analytics.html`
- [X] T057 Run focused public tests, the Feature 142 quickstart, responsive browser QA, reduced-motion/no-JS/consent interaction checks and `infra/scripts/ci-local.sh --fast`; record evidence in `specs/142-launch-landing-redesign/design-qa.md` and `CHANGELOG.md`

## Phase 15: Convergence

- [ ] T058 CRITICAL Block public launch until the operator confirms Russian primary database/object-storage location, current Roskomnadzor operator notification and Article 12 cross-border notification/assessment evidence per FR-022 and FR-026 (partial). Current operator input: PostgreSQL, MinIO and backups are reported on HOSTKEY in Russia; Langfuse Cloud EU remains an approved content-bearing external dependency, so the public copy MUST disclose the resulting cross-border processing and MUST NOT claim that all data stays in Russia. Roskomнадзор notification preparation is explicitly deferred to backlog by product-owner decision.
- [ ] T059 Keep payment publication disabled until the approved catalog, YooKassa acquiring, 54-FZ receipt/tax configuration, renewal/refund rules and effective checkout terms are verified together per FR-013, FR-014 and FR-022 (partial)

## Phase 16: Legal Trust UX Closeout

- [X] T060 Add focused auth/legal trust contracts in `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T061 Link login/signup to the current product terms and privacy notice in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/login.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/signup.html`
- [X] T062 Make analytics opt-out instructions truthful when public analytics is disabled in `apps/server/src/twobrain_rec_server/public/templates/public/cookies.html` and `apps/server/src/twobrain_rec_server/public/templates/public/analytics_consent.html`
- [X] T063 Bump the changed consent edition to `2026-08-13.1` in `apps/server/src/twobrain_rec_server/config.py`, `infra/docker-compose.yml`, `infra/env/rec.production.env.example` and their focused contracts
- [X] T064 Run focused auth/public contracts, browser QA and `infra/scripts/ci-local.sh --fast`; record the final trust-UX closeout in `CHANGELOG.md`

## Dependencies

- T001–T005 are foundational.
- US1 (T006–T008) establishes the page shell and can be validated independently.
- US2 (T009–T012) depends on T002 and the US1 shell.
- US3 (T013–T015) is independent of US2 after T003–T004.
- US4 (T016–T017) is documentation/test-only and can run in parallel with US3.
- T018–T020 depend on all implemented user stories.
- T021–T026 are a feedback-driven refinement sequence; T025–T026 depend on T022–T024.
- T027 must finish before T028–T030. T031 depends on the complete visual and wording refinement.
- T032–T035 form the screenshot-refinement sequence. T036 depends on all four and on fresh desktop/mobile evidence.
- T037–T040 form the linked-proof sequence. T041 depends on all four and on fresh desktop/mobile comparison evidence.
- T042–T046 form the product-depth sequence. T047 depends on all five and fresh desktop/mobile evidence.
- T048–T050 are the compact-hero follow-up; T049 depends on T048 and T050 depends on both plus focused validation.
- T051 is test-first. T052–T056 depend on it and may proceed in parallel only when touching separate files. T057 depends on T051–T056.
- T060 is test-first. T061–T062 depend on it and touch separate templates. T063 depends on the T062 copy decision. T064 validates the completed implementation while T058–T059 remain external release gates.

## Parallel Opportunities

- T002, T004 and T005 touch different files and can run in parallel.
- After the shared stylesheet skeleton exists, US2 template work and US3 template work can proceed independently.
- T016–T017 can run while `/download` styling is implemented.

## Implementation Strategy

1. Lock public truth and real assets before visual implementation.
2. Ship the hero/shell as the first independently testable slice.
3. Add one proof chapter at a time, preserving readable HTML without screenshots.
4. Finish `/download`, then perform visual/accessibility QA across all required widths.

Format validation: all tasks use checkbox, sequential ID, story label where required and exact repository paths.
