from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from importlib import import_module
from math import ceil
from time import perf_counter_ns
from uuid import UUID

from tests.fixtures.calendar_auto_match import (
    FIXTURE_EVALUATED_AT,
    FIXTURE_RECORDING_STARTED_AT,
    calendar_auto_match_event_fixture,
    calendar_auto_match_source_fixture,
    clear_match_fixture,
    private_free_busy_match_fixture,
    stale_latest_failed_match_fixture,
)

MATCHED_EVENT_ID = UUID("00000000-0000-0000-0000-000000000011")
SECOND_EVENT_ID = UUID("00000000-0000-0000-0000-000000000012")


def _matching_api():
    module = import_module("twobrain_rec_server.calendar.matching")
    return module.evaluate_calendar_match, module.finalize_provisional_match


def _evaluate(scenario: dict):
    evaluate_calendar_match, _ = _matching_api()
    return evaluate_calendar_match(
        sources=scenario["sources"],
        events=scenario["events"],
        recording_started_at=scenario["recording_started_at"],
        evaluated_at=scenario["evaluated_at"],
    )


def _with_event_ids(scenario: dict) -> dict:
    owned = deepcopy(scenario)
    for index, event in enumerate(owned["events"], start=1):
        event["id"] = UUID(f"00000000-0000-0000-0000-{index:012d}")
    return owned


def _p95_ms(samples_ns: list[int]) -> float:
    ordered = sorted(samples_ns)
    return ordered[ceil(len(ordered) * 0.95) - 1] / 1_000_000


def test_us1_current_clear_event_is_one_high_confidence_match() -> None:
    # FR-001, FR-005, FR-011: one current, safe, strong event is deterministic.
    scenario = _with_event_ids(clear_match_fixture())

    decision = _evaluate(scenario)

    assert decision.attempt_state == "matched_auto"
    assert decision.safe_reason_code == "single_fresh_candidate"
    assert decision.context_confidence == "high"
    assert decision.candidate_count == 1
    assert decision.candidate_event_ids == ()
    assert decision.matched_event_id == scenario["events"][0]["id"]
    assert decision.matched_title == "Synthetic Planning Sync"
    assert len(decision.matched_roster) == 2
    assert all("email" not in participant for participant in decision.matched_roster)


def test_us1_participants_only_event_matches_with_safe_title_and_roster() -> None:
    # FR-006/FR-020, SC-001/SC-002: participants alone are a strong, roster-safe signal.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        conference_link_hash=None,
    )
    event["id"] = MATCHED_EVENT_ID

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "matched_auto"
    assert decision.matched_event_id == MATCHED_EVENT_ID
    assert decision.matched_title == "Synthetic Planning Sync"
    assert decision.matched_roster_state == "available"
    assert decision.matched_roster_count == 2
    assert len(decision.matched_roster) == 2
    assert all("email" not in participant for participant in decision.matched_roster)


def test_us1_link_or_location_only_event_matches_with_roster_unavailable() -> None:
    # FR-007, SC-001: link/location-only events provide title context, never a fake roster.
    source = calendar_auto_match_source_fixture()
    signal_cases = (
        ("sha256:link-only-signal", None),
        (None, "Synthetic Meeting Room"),
    )

    for conference_link_hash, location in signal_cases:
        event = calendar_auto_match_event_fixture(
            source=source,
            participants=[],
            conference_link_hash=conference_link_hash,
        )
        event["id"] = MATCHED_EVENT_ID
        event["location"] = location

        decision = _evaluate(
            {
                "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
                "evaluated_at": FIXTURE_EVALUATED_AT,
                "sources": [source],
                "events": [event],
            }
        )

        assert decision.attempt_state == "matched_auto"
        assert decision.matched_event_id == MATCHED_EVENT_ID
        assert decision.matched_title == "Synthetic Planning Sync"
        assert decision.matched_roster == ()
        assert decision.matched_roster_state == "not_available"
        assert decision.matched_roster_count == 0


def test_us1_prestart_event_is_provisional_until_recording_overlaps_event_start() -> None:
    # FR-002: the five-minute grace is provisional, not an eager durable match.
    scenario = _with_event_ids(clear_match_fixture())
    event = scenario["events"][0]
    event["starts_at"] = FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=4)
    event["ends_at"] = FIXTURE_RECORDING_STARTED_AT + timedelta(hours=1)

    decision = _evaluate(scenario)

    assert decision.attempt_state == "provisional_prestart"
    assert decision.matched_event_starts_at == event["starts_at"]


def test_us1_later_overlap_confirms_prestart_but_an_early_stop_rejects_it() -> None:
    # FR-002/FR-052: consumption proves actual overlap; no retrospective rematch occurs.
    scenario = _with_event_ids(clear_match_fixture())
    event = scenario["events"][0]
    event["starts_at"] = FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=4)
    event["ends_at"] = FIXTURE_RECORDING_STARTED_AT + timedelta(hours=1)
    decision = _evaluate(scenario)
    _, finalize_provisional_match = _matching_api()

    confirmed = finalize_provisional_match(
        decision,
        meeting_started_at=FIXTURE_RECORDING_STARTED_AT,
        meeting_ended_at=FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=20),
    )
    rejected = finalize_provisional_match(
        decision,
        meeting_started_at=FIXTURE_RECORDING_STARTED_AT,
        meeting_ended_at=FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=3),
    )

    assert confirmed.attempt_state == "matched_auto"
    assert confirmed.safe_reason_code == "single_fresh_candidate"
    assert rejected.attempt_state == "no_context"
    assert rejected.safe_reason_code == "prestart_not_reached"
    assert rejected.matched_event_id is None


def test_us1_strong_conference_identity_dedupes_cross_source_rows() -> None:
    # FR-047: only stable link/source identity may collapse provider duplicates.
    first_source = calendar_auto_match_source_fixture(
        source_id="source-a",
        external_calendar_id="calendar-a",
        provider_family="caldav_yandex",
    )
    second_source = calendar_auto_match_source_fixture(
        source_id="source-b",
        external_calendar_id="calendar-b",
        provider_family="caldav_mail_ru",
    )
    first = calendar_auto_match_event_fixture(
        source=first_source,
        provider_event_id="event-provider-a",
        title="Synthetic Cross Source Planning",
        conference_link_hash="sha256:shared-strong-identity",
    )
    second = calendar_auto_match_event_fixture(
        source=second_source,
        provider_event_id="event-provider-b",
        title="Synthetic Cross Source Planning",
        conference_link_hash="sha256:shared-strong-identity",
    )
    first["id"] = MATCHED_EVENT_ID
    second["id"] = SECOND_EVENT_ID

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [first_source, second_source],
            "events": [first, second],
        }
    )

    assert decision.attempt_state == "matched_auto"
    assert decision.candidate_count == 1
    assert decision.matched_event_id == MATCHED_EVENT_ID


def test_us1_same_source_provider_event_identity_dedupes_duplicate_rows() -> None:
    # FR-027/FR-047, SC-001: stable same-source provider identity is one effective candidate.
    source = calendar_auto_match_source_fixture()
    first = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="same-source-provider-event",
        title="Synthetic Provider Duplicate First",
        conference_link_hash="sha256:provider-duplicate-first",
    )
    second = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="same-source-provider-event",
        title="Synthetic Provider Duplicate Second",
        conference_link_hash="sha256:provider-duplicate-second",
    )
    first["id"] = MATCHED_EVENT_ID
    second["id"] = SECOND_EVENT_ID

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [first, second],
        }
    )

    assert decision.attempt_state == "matched_auto"
    assert decision.candidate_count == 1
    assert decision.matched_event_id == MATCHED_EVENT_ID
    assert decision.matched_title == "Synthetic Provider Duplicate First"


def test_us1_same_provider_id_in_distinct_calendars_of_one_source_stays_ambiguous() -> None:
    # FR-005/FR-047: provider IDs are not assumed global across calendars in one account.
    source = calendar_auto_match_source_fixture()
    first = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="calendar-scoped-provider-event",
        title="Synthetic First Calendar Event",
        conference_link_hash="sha256:first-calendar-only",
    )
    second = deepcopy(first)
    first["id"] = MATCHED_EVENT_ID
    second["id"] = SECOND_EVENT_ID
    second["external_calendar_id"] = "calendar-secondary"
    second["title"] = "Synthetic Second Calendar Event"
    second["conference_link_hashes"] = ["sha256:second-calendar-only"]
    second["conference_summary_json"] = {}
    second["conference_links"] = [
        {
            "provider_family": "generic",
            "source_field": "location",
            "url_hash": "sha256:second-calendar-only",
        }
    ]

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [first, second],
        }
    )

    assert decision.attempt_state == "ambiguous"
    assert decision.safe_reason_code == "multiple_time_candidates"
    assert decision.candidate_count == 2
    assert decision.matched_event_id is None


def test_us1_same_provider_id_from_distinct_sources_does_not_weakly_dedupe() -> None:
    first_source = calendar_auto_match_source_fixture(
        source_id="source-a",
        external_calendar_id="calendar-a",
        provider_family="caldav_yandex",
    )
    second_source = calendar_auto_match_source_fixture(
        source_id="source-b",
        external_calendar_id="calendar-b",
        provider_family="caldav_mail_ru",
    )
    first = calendar_auto_match_event_fixture(
        source=first_source,
        provider_event_id="same-provider-id",
        title="Synthetic First Provider Event",
        conference_link_hash="sha256:provider-a-only",
    )
    second = calendar_auto_match_event_fixture(
        source=second_source,
        provider_event_id="same-provider-id",
        title="Synthetic Second Provider Event",
        conference_link_hash="sha256:provider-b-only",
    )
    first["id"] = MATCHED_EVENT_ID
    second["id"] = SECOND_EVENT_ID

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [first_source, second_source],
            "events": [first, second],
        }
    )

    assert decision.attempt_state == "ambiguous"
    assert decision.safe_reason_code == "multiple_time_candidates"
    assert decision.context_confidence == "ambiguous"
    assert decision.candidate_count == 2
    assert decision.matched_event_id is None


def test_us2_event_without_participants_link_or_location_is_not_eligible() -> None:
    # FR-008: weak title/time similarity alone cannot create calendar context.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        participants=[],
        conference_link_hash=None,
    )

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "no_context"
    assert decision.safe_reason_code == "weak_event_signal"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_description_alone_does_not_make_an_event_eligible() -> None:
    # FR-008/FR-030/FR-046, SC-011: even strong-looking synthetic description text is inert.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        participants=[],
        conference_link_hash=None,
    )
    event["description"] = "Synthetic video meeting with invited participants"
    event["description_state"] = "available"

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "no_context"
    assert decision.safe_reason_code == "weak_event_signal"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None
    assert decision.matched_title is None
    assert decision.matched_roster == ()


def test_us2_unsafe_title_and_roster_name_fail_closed_at_match_projection() -> None:
    # FR-017/FR-030, SC-001/SC-002/SC-011: URL/email-like text cannot cross metadata egress.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(source=source)
    event["id"] = MATCHED_EVENT_ID
    event["title"] = "Join https://meet.example.test/private?passcode=123"
    event["participants"][0]["display_name"] = "alice@example.test"

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "matched_auto"
    assert decision.matched_title is None
    assert decision.matched_title_state == "policy_hidden"
    assert decision.matched_roster[0]["display_name"] is None
    assert "alice@example.test" not in str(decision.matched_roster)


def test_us2_private_event_is_skipped_without_visible_event_details() -> None:
    # FR-010/FR-030: private content never becomes title, roster, or a candidate.
    decision = _evaluate(private_free_busy_match_fixture(privacy_class="private"))

    assert decision.attempt_state == "skipped_private"
    assert decision.safe_reason_code == "private_free_busy_skipped"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.candidate_event_ids == ()
    assert decision.matched_event_id is None
    assert decision.matched_title is None
    assert decision.matched_roster == ()


def test_us2_free_busy_event_is_skipped_without_visible_event_details() -> None:
    # FR-010/FR-030: free/busy-only rows reveal no title, roster, or candidate.
    decision = _evaluate(private_free_busy_match_fixture(privacy_class="free_busy_only"))

    assert decision.attempt_state == "skipped_private"
    assert decision.safe_reason_code == "private_free_busy_skipped"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.candidate_event_ids == ()
    assert decision.matched_event_id is None
    assert decision.matched_title is None
    assert decision.matched_roster == ()


def test_us2_all_day_event_is_ignored_for_automatic_context() -> None:
    # FR-003/FR-009: all-day rows never become automatic calendar context.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(source=source, all_day=True)

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "skipped_all_day"
    assert decision.safe_reason_code == "all_day_skipped"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_cancelled_event_is_not_eligible() -> None:
    # FR-003: a cancelled source snapshot is not a match candidate.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        source_status="cancelled",
    )

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "no_context"
    assert decision.safe_reason_code == "no_matching_event"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_source_deleted_event_is_not_eligible() -> None:
    # FR-003: provider-deleted source rows cannot become automatic context.
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(source=source)
    event["source_deleted_at"] = FIXTURE_EVALUATED_AT - timedelta(seconds=1)

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "no_context"
    assert decision.safe_reason_code == "no_matching_event"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_zero_duration_event_is_not_eligible() -> None:
    # FR-003: eligible timed events require a positive interval (end > start).
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        starts_at=FIXTURE_RECORDING_STARTED_AT,
        ends_at=FIXTURE_RECORDING_STARTED_AT,
    )

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [source],
            "events": [event],
        }
    )

    assert decision.attempt_state == "no_context"
    assert decision.safe_reason_code == "no_matching_event"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_stale_selected_source_vetoes_automatic_matching() -> None:
    # FR-028: a source older than the 24-hour freshness boundary is fail-closed.
    decision = _evaluate(stale_latest_failed_match_fixture(freshness_class="stale"))

    assert decision.attempt_state == "skipped_stale_calendar"
    assert decision.safe_reason_code == "selected_source_stale"
    assert decision.freshness_class == "stale"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_source_freshness_boundary_is_current_only_through_exactly_24_hours() -> None:
    # FR-028, SC-010: exact 24h is current; any later source snapshot fails closed as stale.
    exact_source = calendar_auto_match_source_fixture(
        last_successful_sync_at=FIXTURE_EVALUATED_AT - timedelta(hours=24),
    )
    stale_source = calendar_auto_match_source_fixture(
        source_id="source-stale-epsilon",
        external_calendar_id="calendar-stale-epsilon",
        last_successful_sync_at=(FIXTURE_EVALUATED_AT - timedelta(hours=24, microseconds=1)),
    )
    exact_event = calendar_auto_match_event_fixture(source=exact_source)
    stale_event = calendar_auto_match_event_fixture(source=stale_source)

    exact_decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [exact_source],
            "events": [exact_event],
        }
    )
    stale_decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [stale_source],
            "events": [stale_event],
        }
    )

    assert exact_decision.attempt_state == "matched_auto"
    assert exact_decision.freshness_class == "current"
    assert stale_decision.attempt_state == "skipped_stale_calendar"
    assert stale_decision.safe_reason_code == "selected_source_stale"
    assert stale_decision.freshness_class == "stale"


def test_us2_latest_failed_selected_source_vetoes_automatic_matching() -> None:
    # FR-028: a failure newer than the last success makes the snapshot set incomplete.
    decision = _evaluate(stale_latest_failed_match_fixture(freshness_class="latest_sync_failed"))

    assert decision.attempt_state == "skipped_stale_calendar"
    assert decision.safe_reason_code == "latest_sync_failed"
    assert decision.freshness_class == "latest_sync_failed"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.matched_event_id is None


def test_us2_one_stale_source_vetoes_a_clear_candidate_from_another_source() -> None:
    # FR-005/FR-028: no partial-source winner when any selected source is stale.
    current_source = calendar_auto_match_source_fixture(
        source_id="source-current",
        external_calendar_id="calendar-current",
    )
    stale_source = calendar_auto_match_source_fixture(
        source_id="source-stale",
        external_calendar_id="calendar-stale",
        last_successful_sync_at=FIXTURE_EVALUATED_AT - timedelta(hours=24, seconds=1),
    )
    current_event = calendar_auto_match_event_fixture(source=current_source)
    current_event["id"] = MATCHED_EVENT_ID

    decision = _evaluate(
        {
            "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
            "evaluated_at": FIXTURE_EVALUATED_AT,
            "sources": [current_source, stale_source],
            "events": [current_event],
        }
    )

    assert decision.attempt_state == "skipped_stale_calendar"
    assert decision.safe_reason_code == "selected_source_stale"
    assert decision.freshness_class == "stale"
    assert decision.context_confidence == "none"
    assert decision.candidate_count == 0
    assert decision.candidate_event_ids == ()
    assert decision.matched_event_id is None


def test_us5_provider_series_key_is_hashed_and_scoped_to_workspace_and_source() -> None:
    # FR-024/FR-030: recurrence continuity uses a scoped hash, never a raw provider ID.
    module = import_module("twobrain_rec_server.calendar.matching")
    fingerprint = module.calendar_event_recurring_series_fingerprint
    source = calendar_auto_match_source_fixture()
    first = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="event-recurring-first",
        recurring_series_id="synthetic-series-098",
        recurrence_instance_id="synthetic-instance-first",
    )
    second = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="event-recurring-second",
        recurring_series_id="synthetic-series-098",
        recurrence_instance_id="synthetic-instance-second",
    )
    expected = sha256(b"workspace-098|source-primary|synthetic-series-098").hexdigest()

    assert fingerprint(first) == expected
    assert fingerprint(second) == expected
    assert "synthetic-series-098" not in expected

    different_workspace = deepcopy(first)
    different_workspace["workspace_id"] = "workspace-098-other"
    different_source = deepcopy(first)
    different_source["calendar_source_id"] = "source-secondary"
    different_series = deepcopy(first)
    different_series["recurring_series_id"] = "synthetic-series-098-other"

    assert fingerprint(different_workspace) != expected
    assert fingerprint(different_source) != expected
    assert fingerprint(different_series) != expected


def test_us5_ical_uid_is_a_stable_fallback_for_recurring_occurrences() -> None:
    # FR-024: providers without a series ID may reuse iCalendar UID with recurrence evidence.
    module = import_module("twobrain_rec_server.calendar.matching")
    fingerprint = module.calendar_event_recurring_series_fingerprint
    source = calendar_auto_match_source_fixture()
    first = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="event-uid-fallback-first",
        recurring_series_id=None,
        recurrence_instance_id="synthetic-instance-first",
    )
    first["ical_uid"] = "synthetic-recurring-uid@example.test"
    second = deepcopy(first)
    second["provider_event_id"] = "event-uid-fallback-second"
    second["recurrence_instance_id"] = "synthetic-instance-second"
    expected = sha256(
        b"workspace-098|source-primary|synthetic-recurring-uid@example.test"
    ).hexdigest()

    assert fingerprint(first) == expected
    assert fingerprint(second) == expected


def test_us5_missing_or_ambiguous_recurrence_metadata_does_not_invent_a_series() -> None:
    # FR-026: an ordinary event UID alone is not proof of recurring continuity.
    module = import_module("twobrain_rec_server.calendar.matching")
    fingerprint = module.calendar_event_recurring_series_fingerprint
    source = calendar_auto_match_source_fixture()
    ordinary_event = calendar_auto_match_event_fixture(
        source=source,
        recurring_series_id=None,
        recurrence_instance_id=None,
    )
    recurring_without_identity = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id="event-missing-series-identity",
        recurring_series_id=None,
        recurrence_instance_id="synthetic-instance-without-uid",
    )
    recurring_without_identity["ical_uid"] = None

    assert fingerprint(ordinary_event) is None
    assert fingerprint(recurring_without_identity) is None


def test_us5_previous_occurrences_are_strictly_earlier_and_deterministically_ordered() -> None:
    # FR-024/FR-026: latest earlier wins; equal starts use stable UUID descending.
    module = import_module("twobrain_rec_server.calendar.matching")
    order_previous = module.order_previous_recurring_occurrences
    current_starts_at = FIXTURE_RECORDING_STARTED_AT
    latest_lower_id = UUID("00000000-0000-0000-0005-000000000001")
    latest_higher_id = UUID("00000000-0000-0000-0005-000000000002")
    older_id = UUID("00000000-0000-0000-0005-000000000003")
    current_id = UUID("00000000-0000-0000-0005-000000000004")
    future_id = UUID("00000000-0000-0000-0005-000000000005")
    missing_start_id = UUID("00000000-0000-0000-0005-000000000006")
    latest_earlier_start = current_starts_at - timedelta(days=7)
    occurrences = [
        {"id": older_id, "matched_event_starts_at": current_starts_at - timedelta(days=14)},
        {"id": current_id, "matched_event_starts_at": current_starts_at},
        {"id": latest_lower_id, "matched_event_starts_at": latest_earlier_start},
        {"id": future_id, "matched_event_starts_at": current_starts_at + timedelta(days=7)},
        {"id": missing_start_id, "matched_event_starts_at": None},
        {"id": latest_higher_id, "matched_event_starts_at": latest_earlier_start},
    ]

    ordered = order_previous(occurrences, before=current_starts_at)

    assert [occurrence["id"] for occurrence in ordered] == [
        latest_higher_id,
        latest_lower_id,
        older_id,
    ]


def test_sc017_one_hundred_warmed_resolves_are_within_200ms_p95() -> None:
    # SC-017: exactly four selected sources and 50 candidate rows, all synthetic.
    sources = [
        calendar_auto_match_source_fixture(
            source_id=f"source-{index}",
            external_calendar_id=f"calendar-{index}",
            provider_family=(
                "caldav_yandex",
                "caldav_mail_ru",
                "exchange_ews",
                "custom_caldav",
            )[index],
        )
        for index in range(4)
    ]
    events = []
    for index in range(50):
        event = calendar_auto_match_event_fixture(
            source=sources[index % len(sources)],
            provider_event_id=f"event-performance-{index}",
            title="Synthetic Performance Planning",
            conference_link_hash="sha256:shared-performance-meeting",
        )
        event["id"] = UUID(f"00000000-0000-0000-0001-{index + 1:012d}")
        events.append(event)
    scenario = {
        "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
        "evaluated_at": FIXTURE_EVALUATED_AT,
        "sources": sources,
        "events": events,
    }

    for _ in range(10):
        assert _evaluate(scenario).attempt_state == "matched_auto"

    samples_ns = []
    for _ in range(100):
        started = perf_counter_ns()
        decision = _evaluate(scenario)
        samples_ns.append(perf_counter_ns() - started)
        assert decision.attempt_state == "matched_auto"
        assert decision.candidate_count == 1

    p95_ms = _p95_ms(samples_ns)
    assert len(sources) == 4
    assert len(events) == 50
    assert len(samples_ns) == 100
    assert p95_ms <= 200
