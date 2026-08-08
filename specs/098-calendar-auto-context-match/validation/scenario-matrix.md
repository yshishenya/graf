# Feature 098 Final Scenario Matrix

**Recorded**: 2026-07-13 (Europe/Moscow)
**Task**: T095
**Base**: `3b62270c2b6c8e236444d521759b682323aa80bf`
**Data rule**: synthetic `.test` identities and generated IDs only

## Result

All 29 required quickstart scenarios have an executable receipt in the final
`145` unit, `99` contract and `162` integration suites. No row relies on a
manual claim or a provider network call.

| # | Required scenario | FR / SC | Primary executable receipt | Outcome |
|---:|---|---|---|---|
| 1 | One current eligible event | FR-001, FR-005; SC-001 | `test_us1_current_clear_event_is_one_high_confidence_match`; `test_us1_clear_match_consumes_atomically_and_preserves_safe_title_roster_idempotency` | `matched_auto`; immutable safe context |
| 2 | Starts within five minutes and reaches event | FR-002, FR-052 | `test_us1_us2_persisted_provisional_prestart_is_finalized_when_consumed[reaches_event_start]` | provisional becomes `matched_auto` |
| 3 | Pre-start recording stops early | FR-002, FR-052 | same parameterized persisted test with `stops_before_event_start` | `no_context/prestart_not_reached` |
| 4 | Participants, no link/location | FR-006, FR-020; SC-002 | `test_us1_participants_only_event_matches_with_safe_title_and_roster` | title plus bounded roster |
| 5 | Link/location, no participants | FR-007 | `test_us1_link_or_location_only_event_matches_with_roster_unavailable` | title; roster unavailable |
| 6 | No participants/link/location | FR-008 | `test_us2_event_without_participants_link_or_location_is_not_eligible`; description-only companion | `weak_event_signal`, no match |
| 7 | Overlapping events | FR-014–FR-015 | `test_us3_ambiguous_boundaries_never_attach_an_arbitrary_event` | ambiguous; no title/roster |
| 8 | Exact/near back-to-back | FR-014, FR-047 | same boundary test plus unit boundary cases | never arbitrary choice |
| 9 | Duplicate provider/link rows | FR-027, FR-047 | same-source provider duplicate; shared conference identity; distinct-source negative | collapse only on strong identity |
| 10 | Private/free-busy | FR-010, FR-030; SC-011 | private/free-busy unit tests, private contract audit and cabinet access tests | protected generic state; no details |
| 11 | All-day | FR-009 | `test_us2_all_day_event_is_ignored_for_automatic_context` | skipped/no context |
| 12 | Stale/latest-failed source | FR-028 | freshness boundary, latest-failed and stale-source veto tests | no partial-source match |
| 13 | No connected/selected calendar | FR-003, FR-032 | `test_us2_no_connected_or_selected_calendar_resolve_then_create_is_non_blocking` | ordinary meeting creation; local title kept |
| 14 | Manual upload | FR-011, FR-036 | `test_us2_manual_upload_persists_skip_without_replacing_upload_title` | `skipped_manual_upload` |
| 15 | Recovered/offline queue | FR-012, FR-049 | `test_us2_recovered_meeting_without_live_attempt_skips_calendar_and_keeps_title`; Swift recovery queue test | `skipped_offline_or_unknown`; no fabricated attempt |
| 16 | Generated/app title | FR-017–FR-018 | `test_us4_automatic_match_obeys_desktop_title_precedence` | safe calendar title may replace |
| 17 | User/upload/file/legacy title | FR-017–FR-019 | same precedence test and ingest title tests | never auto-overwritten |
| 18 | Provider rename/move/cancel/delete after match | FR-016, FR-019 | `test_matched_auto_calendar_context_stays_stable_after_provider_mutation` | title/roster/time unchanged |
| 19 | Explicit ambiguity selection | FR-015, FR-038 | `test_us3_explicit_selection_and_retry_replace_ambiguity_once` | `matched_user`; retry stable |
| 20 | Explicit continue without calendar | FR-014, FR-051 | `test_us3_start_decline_and_later_clear_remain_distinct_terminal_states`; direct prompt closure test | `declined_by_user`; no auto-attach |
| 21 | Clear matched context later | FR-018–FR-019, FR-039 | correction/clear integration and cabinet HTMX tests | `cleared_by_user`; title stable |
| 22 | Exact 24-hour attempt boundary | FR-052 | `test_us1_consumption_accepts_before_expiry_and_rejects_exact_boundary`; disconnect purge boundary | exact-boundary rejection and purge eligibility |
| 23 | Cross-user/workspace event or attempt | FR-003–FR-004; SC-004 | foreign attempt test plus access policy owner checks | not found/no existence leak |
| 24 | Authorized recurring predecessor | FR-024–FR-026 | `test_us5_authorized_recurring_pointer_uses_latest_earlier_same_series_only` plus access contract | safe pointer visible |
| 25 | Deleted/inaccessible/cross-space predecessor | FR-025–FR-026, FR-045 | deleted and cross-workspace/space predecessor tests | no pointer or placeholder |
| 26 | Concurrent/repeated resolve/create | FR-027 | resolve idempotency contract, first-consume idempotency, one-row DB uniqueness and concurrent owner selection | one attempt/context authority |
| 27 | Provider failure | FR-032; SC-010 | `test_us2_latest_provider_failure_resolves_and_consumes_fail_soft` | meeting/upload path remains available |
| 28 | Calendar attendees | FR-020–FR-023, FR-040, FR-044; SC-008 | roster-heavy access/share/delivery/speaker tests | zero grants, recipients, delivery or speaker rename |
| 29 | Meeting deletion/source disconnect | FR-041 | deletion lifecycle, deletion workflow and disconnect tests | context accounted; attempts purged/scrubbed |

## Additional Trust-Boundary Receipts

- Unsafe URL-like title and email-like display name are hidden at normalization,
  matcher projection and cabinet egress (`FR-017`, `FR-030`, `SC-011`).
- A consumed attempt immediately drops duplicated candidate/title/roster/time/
  fingerprint content while the authoritative context keeps its immutable copy.
- Strong-looking description text never contributes to match eligibility.
- Freshness is current through exactly 24 hours and stale at `24h + 1µs`.
- Automatic matching still rejects a stale selected source, while the owner may
  explicitly choose a safe stale snapshot; the resulting context retains the
  stale freshness class for audit.
- Same-source provider identity deduplicates even when link hashes differ;
  identical provider IDs from distinct sources do not weakly deduplicate.
- Matched owner review exposes only a bounded safe title and valid event
  interval; correction and clear responses return deterministic focus targets.
- macOS enqueue begins upload processing immediately; a late calendar result
  cannot change the create payload after upload starts.

## Concurrency Clarification

A literal resolve-versus-create race cannot give create an attempt ID before
resolve returns. Racing create without that ID would only test order-dependent
offline fallback, not atomic same-attempt consumption. The required invariant
is therefore covered by idempotent resolve, repeated create/consume receipts,
database uniqueness on attempt/local identity and meeting/context identity, and
the existing deterministic concurrent owner-selection test.

## Exit Decision

Scenario coverage and the user-approved Chrome web/embedded visual QA are
complete for pre-commit PR readiness. The deferred standalone security scan and
production release/deploy evidence remain separate gates and are not inferred
from this matrix.
