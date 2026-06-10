# Checklist: UX and onboarding quality for feature 013

- [X] CHK001 - Are one-click sign-in options clearly scoped per workspace policy and discoverable for first-time users? [Usability, Spec §US1]
- [X] CHK002 - Are disabled providers hidden consistently in both desktop entry points and any auth callback entry path? [Consistency, Spec §US4]
- [X] CHK003 - Does first-run flow include deterministic fallback when provider flow fails or is canceled? [Coverage, Spec §US5]
- [X] CHK004 - Are user-visible messages for failed states actionable and specific (outage, timeout, conflict, denied)? [Clarity, Spec §US5, FR-016, FR-018, FR-023]
- [X] CHK005 - Are explicit confirmation steps for account linking described as first-party user actions and not hidden behind automatic behavior? [Clarity, Spec §US2]
- [X] CHK006 - Is there a clear path to remove/refresh linked providers without data loss? [Completeness, Spec §FR-005, FR-006]
- [X] CHK007 - Are consent texts defined so RU users understand what provider and local data fields are used? [Measurability, Spec §US6, NFR-005]
- [X] CHK008 - Are success and failure states mapped to user-level copy for all main flows (login, linking, revoke, re-login)? [Coverage, Spec §FR-007, FR-009, SC-007]
- [X] CHK009 - Are device trust state transitions visible to user in a predictable and minimal way? [Usability, Spec §US3]
- [X] CHK010 - Are policy settings in admin flow tied to workspace context and not global-only assumptions? [Consistency, Spec §FR-002, FR-004]
- [X] CHK011 - Are error paths preventing account takeover communicated without revealing provider token-level details? [Safety, Spec §FR-006, FR-023]
- [X] CHK012 - Are links between workspace context, provider choice, and legal text consistent across all onboarding screens? [Consistency, Spec §US1, US6]
