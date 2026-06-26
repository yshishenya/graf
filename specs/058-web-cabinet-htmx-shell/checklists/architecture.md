# Architecture Requirements Checklist: Web Cabinet HTMX Shell

**Purpose**: Validate that the feature 058 requirements and plan fix the cabinet architecture clearly enough before task generation.
**Created**: 2026-06-26
**Feature**: [spec.md](../spec.md)
**Audience**: PR reviewer and implementation author
**Depth**: Standard architecture gate

## Requirement Completeness

- [x] CHK001 Are the browser and desktop embedded cabinet shell ownership requirements defined for current and future online pages? [Completeness, Spec FR-001, FR-006, FR-024]
- [x] CHK002 Are the native-only desktop responsibilities fully documented after the product sidebar moves into the WebView? [Completeness, Spec FR-002, FR-018, FR-022]
- [x] CHK003 Are reusable primitive controls, composed sections, and full page templates all covered by the component catalog requirements? [Completeness, Spec FR-025, FR-031, Contract Component Contract]
- [x] CHK004 Are progressive interaction requirements defined for both enhanced and non-enhanced cabinet flows? [Completeness, Spec FR-009, FR-009A, FR-023]
- [x] CHK005 Are security requirements documented for unsafe cookie-authenticated actions, authorization, lifecycle gates, and evidence hygiene? [Completeness, Spec FR-012 through FR-017]
- [x] CHK006 Are compatibility requirements documented for existing browser URLs, desktop embedded URLs, and machine-readable API contracts? [Completeness, Spec FR-016, FR-024A]

## Requirement Clarity

- [x] CHK007 Is the selected frontend foundation stated as a fixed decision rather than a future option? [Clarity, Spec Architecture Decision, FR-010]
- [x] CHK008 Are excluded frontend frameworks, UI kits, CDN assets, and build pipelines named explicitly enough to avoid implementation drift? [Clarity, Spec FR-027 through FR-029, Contract Fixed Frontend Foundation]
- [x] CHK009 Is HTMX scope bounded to opt-in server-owned regions instead of global navigation takeover? [Clarity, Spec FR-009A, Contract Response Mode Rules]
- [x] CHK010 Is browser-side state limited clearly enough to prevent moving meeting truth or lifecycle truth into client code? [Clarity, Spec FR-009B]
- [x] CHK011 Are template responsibilities separated clearly from database access, tenant selection, authorization, deletion lifecycle, and egress policy? [Clarity, Spec FR-034, Contract Template Data Contract]
- [x] CHK012 Is route-policy classification specified as exact approved route kinds rather than broad substring matching? [Clarity, Spec FR-014A, Contract Desktop WebView Boundary]

## Requirement Consistency

- [x] CHK013 Are the spec, plan, research, and contract consistent on Jinja templates, one static CSS layer, centralized Lucide-style icons, and local HTMX 2.x? [Consistency, Spec FR-010, Plan Technical Context, Research Decisions]
- [x] CHK014 Are the Tailwind and ready UI-kit exclusions consistent across the spec, plan, research, contract, and quickstart? [Consistency, Spec FR-027, FR-027A, Plan Constraints, Quickstart Static Source Guard]
- [x] CHK015 Are native offline recording requirements consistent with the future web-owned sidebar direction? [Consistency, Spec User Story 2, Plan Summary, Contract Desktop WebView Boundary]
- [x] CHK016 Are deletion, lifecycle, and unsafe action requirements consistent between user scenarios, functional requirements, and contracts? [Consistency, Spec User Story 6, FR-012 through FR-017, Contract CSRF Contract]
- [x] CHK017 Are component state requirements consistent between success criteria and component contract expectations? [Consistency, Spec FR-032, FR-033, SC-014, SC-015, Contract Component Contract]

## Acceptance Criteria Quality

- [x] CHK018 Are success criteria measurable for shared navigation, offline desktop truth, active recording reachability, CSRF protection, and URL compatibility? [Acceptance Criteria, Spec SC-001 through SC-006]
- [x] CHK019 Are success criteria measurable for enhanced interactions, responsive layouts, evidence scans, stable dependency checks, and migration steps? [Acceptance Criteria, Spec SC-007 through SC-011]
- [x] CHK020 Are success criteria measurable for brand-distance review, fixed UI foundation, component catalog size, state coverage, and forbidden asset checks? [Acceptance Criteria, Spec SC-012 through SC-018]
- [x] CHK021 Can the plan's validation commands be traced back to the success criteria without relying on private meeting content? [Traceability, Plan Testing, Quickstart Sections 1 through 5, Spec SC-009]

## Scenario Coverage

- [x] CHK022 Are primary browser, desktop WebView, offline, auth-expired, deletion, and future-page scenarios addressed in user stories and edge cases? [Coverage, Spec User Stories 1 through 7, Edge Cases]
- [x] CHK023 Are exception flows documented for server offline, timeout, malformed response, auth redirect, validation error, unavailable state, and blocked routes? [Coverage, Spec Edge Cases, Contract Response Mode Rules]
- [x] CHK024 Are recovery and fallback requirements defined for JavaScript-disabled flows, failed enhanced requests, and local recording during cabinet failures? [Coverage, Spec FR-003, FR-004, FR-023]
- [x] CHK025 Are multi-window or stale-link lifecycle scenarios included enough to protect deletion/session truth? [Coverage, Spec Edge Cases]

## Non-Functional Requirements

- [x] CHK026 Are accessibility requirements specified for focus visibility, keyboard operation, target size, long labels, and WebView focus boundaries? [Non-Functional, Spec FR-018, FR-019, FR-032A]
- [x] CHK027 Are localization and visual consistency requirements specified for Russian copy, spacing, radius, typography, icons, and state vocabulary? [Non-Functional, Spec FR-008, FR-032]
- [x] CHK028 Are performance expectations bounded without introducing a frontend build pipeline or client-side application shell? [Non-Functional, Spec SC-007, Plan Performance Goals]
- [x] CHK029 Are privacy and metadata-only evidence requirements specific enough for screenshots, logs, traces, reports, and issue comments? [Non-Functional, Spec FR-017, SC-009, Contract Evidence Contract]

## Dependencies And Assumptions

- [x] CHK030 Are stable dependency decisions and excluded unstable/prerelease lines documented before implementation tasks are generated? [Dependency, Spec FR-011, Plan Technical Context, Research Decisions]
- [x] CHK031 Are no-database-schema-change and existing service-boundary assumptions documented clearly enough for implementation planning? [Assumption, Plan Storage, Data Model]
- [x] CHK032 Are future account, settings, activity, access, export, deletion, and retention pages assigned to the online cabinet unless a later spec proves otherwise? [Assumption, Spec FR-024, Assumptions]

## Ambiguities And Conflicts

- [x] CHK033 Are there no remaining open alternatives that would let tasks choose Tailwind, a ready UI kit, SPA framework, or separate frontend build pipeline inside 058? [Ambiguity, Spec Architecture Decision, FR-027 through FR-029]
- [x] CHK034 Are there no conflicts between Spec Kit's product-facing requirements and the user's request to lock architecture decisions early? [Conflict, Spec Architecture Decision, Plan Structure Decision]
- [x] CHK035 Are rollback and independently verifiable migration expectations documented enough to prevent a single risky rewrite task? [Ambiguity, Spec FR-020, SC-011]
