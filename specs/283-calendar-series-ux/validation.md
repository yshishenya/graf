# F283 validation

2026-10-02: specify→clarify→plan→checklist→tasks→analyze. Independent requirements review UX8/8/security6/6 PASS. Read-only analyze: FR10+SC4, tasks9, coverage100%, CRITICAL0/HIGH0, no unmapped tasks. Optional agent-context hooks skipped to keep stable root; auto-commit disabled. Branch allocated once by repository hook, Feature283 umbrella7420. Task issues synchronised before product edits.

Implementation/runtime/PR evidence pending; no production release claimed. Synthetic-only browser evidence. VoiceOver deliberately not repeated per user instruction.

## Implementation and review

2026-10-02 local working diff on base95be4e117dc2403e5388abe04a9aab9a475f4ca2. T001–T008 implemented and locally verified. High-risk-feature; no unrelated original dbeb checkout changes touched. Self code review via code-reviewer: temporal query/cursor guards, additive compatibility, DOM text/attributes, switch/close/refresh cancellation, timeout, focus restore and ACL refresh reviewed. Fixed focus before releasing inert; refresh request immediately makes old actions inert, even during pagination. No unresolved source findings.

## Focused checks

- PostgreSQL isolated runner: tests/unit/test_calendar_series.py + tests/contract/test_calendar_join_series_contract.py —23 PASS,0 skips, including2 new temporal/cursor checks. Initial red verification:2 failures/21 PASS before implementation.
- Chromium151 production renderer/assets and exact native documentScript browser harness —PASS. Trusted Join, duplicate suppression, session/CSRF/HTTPS popup isolation, pagehide, real calendar refresh, view switching/pagination, late abort, error/retry/expiry, failed rights refresh, masks, ongoing, all-day, long title,320px/200%, keyboard.
- Direct WebKit26.5 final production harness —PASS including descriptive accessible recording/Join names, privacy-masked renderer, DST transition and computed text contrast≥4.5 in dark/light. Not an installed app proof.
- Visual screenshots inspected: actual production upcoming dark, history light and long-title320px. Two-line exception title + full permitted tooltip; controls wrap without overflow. Synthetic data only; screenshots outside git. Initial fixture timezone disagreement corrected by existing apply_user_time_preference, not a product workaround.
- Ruff check PASS; focused formatter applied only changed API/query/test files; JS syntax PASS; git diff --check PASS; Spec Kit governance PASS.

## Coverage and convergence

FR-001→T004/T007; FR-002→T002/T003/T004; FR-003→T004/T006; FR-004→T004/T005; FR-005→T005; FR-006→T006/T007; FR-007→T002/T003/T006; FR-008→T006/T007; FR-009→T004/T007/T008; FR-010→T001/T008. SC-001→T004/T005/T007; SC-002→T004/T005/T007; SC-003→T007/T008/T009; SC-004→T002/T006/T007/T009.

Converge checks implementation against10 FR,4 buildable SC,3 stories and plan boundaries: no missing build work, no feature-introduced unrequested behavior. tasks unchanged by converge; T009 delivery/Dev/exact-SHA PR evidence remains pending. All local results above bind to working diff, not a released source SHA. No production release, deploy or VoiceOver claimed.

Final local profile:87 PostgreSQL tests PASS/0 skips; Chromium151 and WebKit26.5 harness PASS. WebKit Join max32ms, series p95 50ms;30 samples/3warm-up, nearest-rank p95. All code changes validated before implementation commit. Previously granted user approval to commit and continue the calendar task through GRAF Dev is retained; no new production authorization inferred.

## Delivery checks

GRAF Dev build/promote and live smoke PASS for source0186a7b96c45bfaf1003dbdda7ab4dade926c0c2:13 checks, including installed app identity, API/frontend, database/migration, storage, Temporal/workers and exact component SHA. This is runtime readiness, not manual UI acceptance. Manual check stopped at the macOS lock screen; user asked to unlock. No bypass, VoiceOver repetition or production action.

CI identified a missing required Legacy Impact section in the feature specification. Added the existing PR classification to spec.md without changing product behavior or weakening validation. Branch rebased without conflict onto202855acbb751c9a6f3d2b3bbeae64ddf91cbe9c; final SHA-bound CI and Dev checks must be repeated. T009 remains open until required evidence is complete.
