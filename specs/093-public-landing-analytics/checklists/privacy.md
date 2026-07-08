# Privacy Checklist: Public Landing Analytics

**Purpose**: Validate privacy, consent, egress, replay, and forbidden-data requirement quality before task generation
**Created**: 2026-07-08
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are third-party analytics egress requirements complete for the approved Phase 1 provider and explicitly limited to Yandex Metrica, with Google/GA4 excluded? [Completeness, Spec §FR-002, Spec §FR-003, Plan §Constraints]
- [x] CHK002 Are out-of-scope product surfaces named clearly enough to prevent analytics or replay from reaching login, cabinet, meeting, upload, playback, deletion, admin, and desktop embedded pages? [Completeness, Spec §FR-001, Spec §FR-010]
- [x] CHK003 Are consent requirements complete for unknown, accept-all, necessary-only, customized, and revoked states? [Completeness, Spec §FR-006-FR-009, Data Model §Public Analytics Consent Preference]
- [x] CHK004 Are requirements explicit that analytics is disabled by default without enabled config, production-like environment, and provider IDs? [Completeness, Spec §FR-004-FR-005, Data Model §Public Analytics Runtime Configuration]
- [x] CHK005 Are replay/behavior recording requirements complete for scope, consent, and forbidden surfaces? [Completeness, Spec §FR-010, Contract §Replay Contract]
- [x] CHK006 Are provider ID, ad account, cookie, visitor ID, and raw network payload evidence restrictions specified? [Completeness, Spec §FR-020, Spec §FR-024, Provider Setup §Evidence Safety]

## Requirement Clarity

- [x] CHK007 Is "non-essential analytics" bounded enough to distinguish provider scripts, cookies/storage, advertising identifiers, replay, and future events? [Clarity, Spec §FR-006-FR-009, Research §Strict Consent Gating]
- [x] CHK008 Is the strict no-provider-before-consent decision explicit enough to avoid accidentally sending pre-consent provider pings? [Clarity, Research §Strict Consent Gating, Contract §Consent Contract]
- [x] CHK009 Are safe event fields listed as an allowlist rather than relying on a vague metadata-only claim? [Clarity, Spec §FR-012, Data Model §Public Landing Analytics Event]
- [x] CHK010 Are forbidden event/UTM/evidence values specific enough to catch private data, credentials, raw paths, object keys, signed URLs, and content-bearing meeting data? [Clarity, Spec §FR-013, Contract §UTM Contract]
- [x] CHK011 Is the difference between web conversion and product activation clear enough to prevent misleading campaign claims? [Clarity, Spec §FR-016, Spec §FR-027, SC-009]

## Requirement Consistency

- [x] CHK012 Are consent defaults consistent between spec, plan, research, data model, and public analytics contract? [Consistency, Spec §Clarifications, Plan §Technical Context, Research §Strict Consent Gating]
- [x] CHK013 Is PostHog consistently treated as Phase 2 contract-only work across all artifacts? [Consistency, Spec §FR-003, Plan §Constraints, Research §PostHog, Phase2 Contract]
- [x] CHK014 Are replay requirements consistent with the selected provider strategy and the no-Clarity decision? [Consistency, Research §Replay, Contract §Replay Contract]
- [x] CHK015 Are provider configuration requirements consistent with repository hygiene rules forbidding committed live IDs/secrets? [Consistency, Spec §Assumptions, Plan §Constraints, Provider Setup §Evidence Safety]

## Acceptance Criteria Quality

- [x] CHK016 Are privacy success criteria measurable for disabled, unknown, accept-all, necessary-only, customized, and revoked consent states? [Acceptance Criteria, SC-003, SC-004]
- [x] CHK017 Are no-replay-on-product-surface criteria measurable without inspecting private meeting/account content? [Acceptance Criteria, SC-006]
- [x] CHK018 Are no-forbidden-data criteria measurable through event allowlists and forbidden-content scans? [Acceptance Criteria, SC-002, Quickstart §Focused Test Commands]

## Scenario Coverage

- [x] CHK019 Are consent-change scenarios covered, including grant after page load and later revocation? [Coverage, Spec §Edge Cases]
- [x] CHK020 Are blocked provider, privacy extension, third-party cookie restriction, and provider outage scenarios covered? [Coverage, Spec §Edge Cases, Quickstart §Provider Failure]
- [x] CHK021 Are unsafe UTM values and personally identifying campaign tags covered as privacy scenarios? [Coverage, Spec §Edge Cases, Contract §UTM Contract]
- [x] CHK022 Is the future Phase 2 identity boundary specified before any authenticated or desktop product analytics can begin? [Coverage, Spec §FR-025-FR-026, Phase2 Contract §Identity Boundary]

## Dependencies & Assumptions

- [x] CHK023 Are external provider assumptions and reporting caveats documented without turning them into unsupported guarantees? [Assumption, Spec §FR-019, Research §Yandex Metrica]
- [x] CHK024 Are live dashboard validation and production smoke requirements separated from local test evidence? [Dependency, Plan §Validation Plan, Quickstart §Provider Dashboard Smoke]
