# UX Checklist: Public Landing Analytics

**Purpose**: Validate consent UI, public funnel, accessibility, localization, and non-disruptive landing UX requirement quality before task generation
**Created**: 2026-07-08
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are public user-visible changes limited to consent control and approved analytics metadata so the install-first landing path remains intact? [Completeness, Spec §FR-022, Plan §Summary]
- [x] CHK002 Are CTA locations and target kinds defined with stable labels for header, hero, final, download, installer, and login paths? [Completeness, Public Analytics Contract §Event Contract]
- [x] CHK003 Are direct `/download` entry and login intent paths covered separately from landing CTA conversion? [Completeness, Spec §US2, Spec §FR-016]
- [x] CHK004 Are user-facing consent copy requirements specified as Russian and non-overpromising? [Completeness, Spec §FR-006, Spec §Assumptions]
- [x] CHK005 Are accessibility requirements present for accept-all, necessary-only, customize controls, and later consent change? [Completeness, Quickstart §Configured But Consent Unknown, Spec §FR-007]

## Requirement Clarity

- [x] CHK006 Are "primary web conversion", "secondary conversion", and "product activation" defined clearly enough for dashboard and campaign readers? [Clarity, Spec §FR-016, Spec §FR-027, Data Model §Public Conversion Goal]
- [x] CHK007 Are section IDs defined as stable product labels instead of visible marketing text? [Clarity, Public Analytics Contract §Event Contract]
- [x] CHK008 Is the measurement caveat for consent undercount visible enough to avoid misleading "total visitor" claims? [Clarity, Research §Strict Consent Gating, Spec §FR-019]
- [x] CHK009 Is provider failure UX specified as non-blocking for page navigation, CTAs, and installer download? [Clarity, Spec §FR-021, Quickstart §Provider Failure]

## Requirement Consistency

- [x] CHK010 Are CTA measurement requirements consistent with the current public landing brief and install-first conversion path? [Consistency, Spec §Assumptions, Plan §Summary]
- [x] CHK011 Are consent UI requirements consistent with the existing local-asset, no-framework public landing constraints? [Consistency, Plan §Technical Context, Plan §Structure Decision]
- [x] CHK012 Are public replay requirements consistent with no form/input capture on the current landing and a future review if inputs are added? [Consistency, Public Analytics Contract §Replay Contract]

## Acceptance Criteria Quality

- [x] CHK013 Can UX acceptance be measured for disabled analytics, consent unknown, accept-all, necessary-only, customized, revoked, and provider blocked states? [Acceptance Criteria, Quickstart §Focused Validation Scenarios]
- [x] CHK014 Can duplicate event prevention be measured from one user action without relying on subjective interpretation? [Acceptance Criteria, SC-005]
- [x] CHK015 Can campaign launch readiness be evaluated by a non-engineer within a bounded time? [Acceptance Criteria, SC-008]

## Scenario Coverage

- [x] CHK016 Are mobile/desktop browser, private browsing, multiple tabs, reload, and repeat click cases represented in requirements or edge cases? [Coverage, Spec §Edge Cases]
- [x] CHK017 Are missing and unsafe UTM cases covered from a user acquisition reporting perspective? [Coverage, Spec §Edge Cases, Contract §UTM Contract]
- [x] CHK018 Are public pages required to remain useful when provider scripts are blocked or slow? [Coverage, Spec §FR-021, SC-007]

## Ambiguities & Conflicts

- [x] CHK019 Is there no remaining conflict between wanting detailed analytics and choosing consent-first undercount caveats for privacy? [Conflict Review, Research §Strict Consent Gating, Spec §FR-019]
- [x] CHK020 Is there no remaining ambiguity about whether this slice redesigns the landing page? [Ambiguity Review, Spec §FR-022, Plan §Structure Decision]
