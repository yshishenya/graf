# Operations Checklist: Public Landing Analytics

**Purpose**: Validate provider setup, environment, validation, release, and campaign-readiness requirement quality before task generation
**Created**: 2026-07-08
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are environment gating requirements defined for local, test, CI, production-like, and provider-smoke states? [Completeness, Spec §FR-004, Data Model §Public Analytics Runtime Configuration]
- [x] CHK002 Are provider setup requirements documented for Yandex Metrica while explicitly deferring GA4/Google setup? [Completeness, Provider Setup §Yandex Metrica, Provider Setup §Google Deferred Scope]
- [x] CHK003 Are external ad-platform linking requirements covered for Yandex Direct without committing live account identifiers? [Completeness, Spec §FR-020, Provider Setup §Shared Campaign Readiness]
- [x] CHK004 Are dashboard requirements defined for source, campaign, event, funnel, key event, and replay/scroll review? [Completeness, Spec §FR-017-FR-018, Provider Setup §Dashboard requirements]
- [x] CHK005 Are release/campaign launch readiness requirements defined separately from local implementation closeout? [Completeness, Spec §FR-028, Plan §Release Gate]
- [x] CHK005A Are legal readiness requirements present for privacy/cookie/terms/analytics-consent links, operator notice review, and foreign-provider deferral? [Completeness, Spec §FR-029-FR-031, Provider Setup §Shared Campaign Readiness]

## Requirement Clarity

- [x] CHK006 Is it clear which validation can run locally without live provider contact and which needs explicit production/campaign approval? [Clarity, Plan §Validation Plan, Quickstart §Provider Dashboard Smoke]
- [x] CHK007 Is the no-new-dependency/no-tag-manager decision clear enough for implementation task boundaries? [Clarity, Plan §Primary Dependencies, Research §Direct provider snippets]
- [x] CHK008 Are provider failure and blocker caveats clear enough for operations and campaign reporting? [Clarity, Spec §FR-019, Quickstart §Provider Failure]
- [x] CHK009 Is evidence safety clear enough for provider dashboard screenshots, IDs, cookies, raw network payloads, and account identifiers? [Clarity, Provider Setup §Evidence Safety, Spec §FR-024]
- [x] CHK009A Is self-hosted CookieConsent version pinning, MIT attribution, and no-CDN validation explicit enough for implementation? [Clarity, Spec §FR-032, Plan §Primary Dependencies, Tasks §T012-T014]

## Requirement Consistency

- [x] CHK010 Are local CI and focused validation expectations consistent with the high-risk validation lane? [Consistency, Plan §Validation Plan, Constitution §V]
- [x] CHK011 Are no-deploy and no-live-provider-smoke boundaries consistent across plan and quickstart? [Consistency, Plan §Release Gate, Quickstart §Closeout Gate]
- [x] CHK012 Are UTM governance requirements consistent with dashboard interpretation and ad campaign readiness? [Consistency, Spec §FR-014-FR-015, Contract §UTM Contract]

## Acceptance Criteria Quality

- [x] CHK013 Are operations success criteria measurable for provider dashboard readiness, conversion visibility, and campaign launch checklist completion? [Acceptance Criteria, SC-001, SC-008]
- [x] CHK014 Are duplicate event and provider initialization expectations measurable enough for automated tests? [Acceptance Criteria, SC-005, Spec §US5]
- [x] CHK015 Are blocked-script and provider-outage cases measurable without live provider credentials? [Acceptance Criteria, SC-007, Quickstart §Provider Failure]

## Scenario Coverage

- [x] CHK016 Are missing IDs, disabled flags, non-production environments, and render-only validation states covered? [Coverage, Spec §FR-004-FR-005, Quickstart §Analytics Disabled By Default]
- [x] CHK017 Are bot/crawler/direct/referral attribution caveats covered for report interpretation? [Coverage, Spec §Edge Cases, Spec §FR-019]
- [x] CHK018 Are installer asset URL changes and repeated installer downloads covered as campaign reporting edge cases? [Coverage, Spec §Edge Cases]
- [x] CHK019 Are future campaign launch blockers listed before paid traffic is sent? [Coverage, Provider Setup §Shared Campaign Readiness]
