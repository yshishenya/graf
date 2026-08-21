# Release Requirements Checklist: Production Landing Refresh

**Purpose**: Validate that public UX, paid claims, analytics, legal and deployment requirements are complete and unambiguous before implementation and release review
**Created**: 2026-08-21
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are the exact landing sections, order and removal boundaries documented for both desktop and mobile? [Completeness, Spec §FR-001–FR-007]
- [x] CHK002 Are requirements defined for every public route retained or changed by the release, including `/download`, all legal pages, discovery files and login handoff? [Completeness, Spec §FR-012, FR-015–FR-016, FR-021]
- [x] CHK003 Are the three product-screen content, provenance and synthetic-data requirements complete enough to reject fictional or private assets? [Completeness, Spec §FR-007–FR-010]
- [x] CHK004 Are commercial requirements complete across visible price, trial, cadence, annual saving, catalog, checkout, offer, renewal, cancellation and refund boundaries? [Completeness, Spec §FR-013–FR-016]
- [x] CHK005 Are all nine funnel events, their allowed surfaces, triggers, labels and forbidden data classes documented? [Completeness, Contract yandex-goals]

## Requirement Clarity

- [x] CHK006 Is the permitted meaning of “в любом приложении” explicitly limited so it cannot be read as automatic recording or universal compatibility certification? [Clarity, Spec §FR-005]
- [x] CHK007 Is “дизайн 1:1” bounded by named truth, legal, accessibility and responsive exceptions rather than subjective similarity? [Clarity, Spec §FR-001]
- [x] CHK008 Are sale-ready and fail-closed public states defined with objective catalog, checkout, offer and launch-gate predicates? [Clarity, Data Model §PublicOfferView]
- [x] CHK009 Is annual value expressed by exact arithmetic without the previously conflicting `-20%` claim? [Clarity, Research §Decision 4]
- [x] CHK010 Are the immediate Metrica mode and the fact that it uses cookies/localStorage stated without consent-gated or cookie-free wording elsewhere? [Clarity, Spec §FR-017–FR-018a]

## Requirement Consistency

- [x] CHK011 Are platform requirements consistent between hero copy, FAQ, download page, metadata and the current universal-package contract? [Consistency, Spec §FR-011, Contract public-funnel §Download handoff]
- [x] CHK012 Are the 1,000/10,000 RUB values consistent across specification, public-offer model, catalog, checkout and offer requirements? [Consistency, Spec §FR-013–FR-016]
- [x] CHK013 Are analytics requirements consistent between immediate provider loading, legal disclosure, restricted page inventory and forbidden data fields? [Consistency, Spec §FR-017–FR-018a, Contract yandex-goals]
- [x] CHK014 Are no-JavaScript requirements consistent with the single-visible-panel enhanced tab design and accessibility requirements? [Consistency, Spec §FR-007, FR-019–FR-020]
- [x] CHK015 Are footer/legal requirements consistent with sitemap indexing decisions, especially inclusion or intentional exclusion of `/offer`? [Consistency, Spec §FR-015–FR-016, FR-021]

## Acceptance Criteria Quality

- [x] CHK016 Can visual fidelity, responsive behavior and overflow be objectively assessed at every named viewport without relying on “красиво” or “качественно”? [Measurability, Spec §SC-003]
- [x] CHK017 Can product-tab keyboard, focus and accessible-state requirements be evaluated with explicit expected keys and states? [Measurability, Contract public-funnel §Accessibility]
- [x] CHK018 Can pricing truth be evaluated against one authoritative catalog and offer version with zero tolerated mismatch? [Measurability, Spec §SC-005]
- [x] CHK019 Can analytics data minimization be evaluated from an explicit allowlist and forbidden-field list rather than a broad “безопасно” claim? [Measurability, Data Model §PublicAnalyticsEvent]
- [x] CHK020 Is the 95% confidence request translated into concrete technical, content, interaction, visual, external-provider and deployment evidence rather than a subjective score? [Acceptance Criteria, Plan §Validation Plan]

## Scenario And Edge Coverage

- [x] CHK021 Are degraded scenarios documented for disabled JavaScript, failed images, failed Metrica, missing catalog, unavailable checkout and missing installer? [Coverage, Spec §Edge Cases]
- [x] CHK022 Are recovery and rollback requirements defined for failed migration, unhealthy deploy, wrong price, duplicate goal delivery and package-link regression? [Coverage, Recovery, Spec §FR-023]
- [x] CHK023 Are legal and analytics behavior requirements defined for query/hash URLs, private-looking UTM values and non-public product surfaces? [Coverage, Edge Case, Spec §FR-018, SC-008]
- [x] CHK024 Are mobile, 200% zoom, reduced-motion, keyboard-only and assistive-technology scenarios all represented? [Coverage, Non-Functional, Spec §FR-019–FR-020]
- [x] CHK025 Are planned Windows/Linux states explicitly non-actionable while the macOS artifact has one stable handoff? [Coverage, Alternate Flow, Contract public-funnel §Download handoff]

## Dependencies And Release Gates

- [x] CHK026 Are authenticated Yandex counter access, goal replacement and synthetic receipt evidence identified as external dependencies rather than source-code assumptions? [Dependency, Research §Decision 8]
- [x] CHK027 Are external legal approval for immediate Metrica and the separate billing finance/legal/security/infrastructure/release approvals explicitly distinguished? [Dependency, Spec §FR-018a, Plan §Release Gate]
- [x] CHK028 Are production catalog provisioning, test-shop, controlled canary and four-eyes approval requirements documented as blockers rather than optional follow-ups? [Dependency, Plan §Constitution Check]
- [x] CHK029 Are exact-SHA, backup, dry-run, explicit execute authorization, post-deploy smoke and rollback criteria all documented? [Completeness, Spec §FR-023]
- [x] CHK030 Is the scope boundary clear that desktop capture, account auth, meeting processing and package construction are unchanged? [Scope, Spec §Assumptions]

## Notes

- This is a formal PR and production-release requirement-quality gate.
- Unchecked items indicate a requirement gap, not an implementation failure.
- Implementation may start only after every material gap is resolved or explicitly blocked with an owner.

