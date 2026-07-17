# Requirements Checklist: Update Safety and UX

**Purpose**: Validate that update trust, capture safety, permission retention, failure recovery, and reminder UX are fully specified before implementation
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md)
**Depth**: Formal pre-implementation gate
**Audience**: PR reviewer, release operator, macOS QA

## Requirement Completeness

- [x] CHK001 Are both scheduled and user-initiated update discovery requirements defined? [Completeness, Spec §FR-002–FR-009]
- [x] CHK002 Are install, defer, dismiss, skip, current, incompatible, unavailable, and retryable-failure outcomes covered? [Completeness, Spec §US1–US3, FR-008–FR-015]
- [x] CHK003 Is the bootstrap behavior for versions that do not yet contain the updater explicit? [Completeness, Spec §FR-028]
- [x] CHK004 Are public release-operator requirements included rather than assuming a client alone can create a trustworthy update? [Completeness, Spec §US4, FR-021–FR-023]
- [x] CHK005 Are connected-cabinet and local-only sidebar modes both covered? [Completeness, Spec §FR-012, US3]

## Requirement Clarity

- [x] CHK006 Is “periodic” quantified with a precise interval and closed-app boundary? [Clarity, Spec §FR-002–FR-003]
- [x] CHK007 Is “preserve permissions” defined through stable application and signing identity rather than only visible app name? [Clarity, Spec §FR-019–FR-020]
- [x] CHK008 Is “do not interrupt recording” expanded to cover capture transitions, finalization, persistence, and termination cleanup? [Clarity, Spec §FR-010–FR-011]
- [x] CHK009 Is the sidebar marker’s visibility rule unambiguous for available, current, withdrawn, skipped, failed, and untrusted states? [Clarity, Spec §FR-012–FR-015]
- [x] CHK010 Is the distinction between automatic checking and automatic/silent installation explicit? [Clarity, Spec §FR-002, FR-005–FR-006]

## Requirement Consistency

- [x] CHK011 Do scheduled offer requirements remain consistent with capture deferral and one-action stop requirements? [Consistency, Spec §US1, FR-004–FR-011]
- [x] CHK012 Do menu and sidebar actions converge on one update offer and one safety gate? [Consistency, Spec §FR-007, FR-014]
- [x] CHK013 Do failure/rollback requirements align with fail-closed trust configuration and rejection requirements? [Consistency, Spec §FR-016–FR-018, FR-027]
- [x] CHK014 Do initial installer and update requirements consistently prohibit privileged audio/Core Audio mutation? [Consistency, Spec §FR-026]
- [x] CHK015 Do privacy requirements align with the project’s metadata-only evidence and no-secret rules? [Consistency, Spec §FR-024–FR-025]

## Acceptance Criteria Quality

- [x] CHK016 Can update discovery timing be objectively measured without naming an implementation mechanism? [Measurability, Spec §SC-001–SC-002]
- [x] CHK017 Can capture continuity and post-capture offer timing be objectively verified? [Measurability, Spec §SC-003–SC-004]
- [x] CHK018 Can sidebar appearance/disappearance and accessibility be objectively verified? [Measurability, Spec §SC-005, SC-010]
- [x] CHK019 Can permission retention be proven without resetting or editing macOS privacy state? [Measurability, Spec §SC-006]
- [x] CHK020 Can invalid update rejection and prior-version launchability be objectively verified? [Measurability, Spec §SC-007]
- [x] CHK021 Is public publication gated by measurable signing, notarization, catalog, update, rollback, and relaunch evidence? [Measurability, Spec §SC-008]

## Scenario Coverage

- [x] CHK022 Are primary, alternate, exception, recovery, and non-functional update scenarios all represented? [Coverage, Spec §US1–US4, Edge Cases]
- [x] CHK023 Are concurrent scheduled/manual checks and an already-running update session addressed? [Coverage, Spec §FR-009, Edge Cases]
- [x] CHK024 Are offline start, later reconnection, timeout, invalid response, and withdrawn-release scenarios addressed? [Coverage, Spec §Edge Cases]
- [x] CHK025 Are read-only, translocated, and otherwise non-updatable installation locations included? [Coverage, Spec §Edge Cases]
- [x] CHK026 Are incompatible macOS, architecture, downgrade, and malformed-version cases included? [Coverage, Spec §FR-017, FR-022–FR-023, Edge Cases]

## Security, Privacy, and Supply Chain

- [x] CHK027 Are HTTPS transport and independent cryptographic authenticity both required? [Security, Spec §FR-016]
- [x] CHK028 Are archive, feed/release description, signing lineage, nested code, hardened runtime, notarization, and Gatekeeper trust boundaries specified? [Security, Spec §FR-017, FR-019, FR-021–FR-023]
- [x] CHK029 Are private release keys and credentials explicitly excluded from the app, repository, host, logs, and evidence? [Security, Spec §FR-024–FR-025, Assumptions]
- [x] CHK030 Is insecure fallback behavior prohibited when trusted configuration is incomplete? [Security, Spec §FR-027]
- [x] CHK031 Is update request data bounded so system profiling, account identifiers, and meeting content are excluded? [Privacy, Spec §FR-024]

## Accessibility and Product UX

- [x] CHK032 Are the menu command and sidebar marker both keyboard-reachable and screen-reader-labeled? [Accessibility, Spec §FR-007, FR-013, SC-010]
- [x] CHK033 Is the marker defined as informational and subordinate to capture state rather than an alarming error badge? [UX, Spec §FR-013, Assumptions]
- [x] CHK034 Is the marker required not to obscure navigation, logout, recording controls, or one-action stop? [UX, Spec §FR-013, SC-010]
- [x] CHK035 Are manual checks guaranteed an explicit result while scheduled failures remain low-noise? [UX, Spec §FR-004, FR-008]

## Dependencies and Assumptions

- [x] CHK036 Is the dependency on an external Apple Developer signing/notarization gate explicit? [Dependency, Spec §FR-021, Assumptions]
- [x] CHK037 Is the public, credential-free HTTPS update origin assumption documented? [Assumption, Spec §FR-016, FR-024, Assumptions]
- [x] CHK038 Are intentionally deferred channels, mandatory updates, enterprise rollout, and phased rollout boundaries explicit? [Scope, Spec §Assumptions]

## Notes

- 38/38 requirement-quality checks pass. No unresolved requirement gap blocks task generation or implementation.
