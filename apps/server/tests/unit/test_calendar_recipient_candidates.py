from twobrain_rec_server.calendar.normalize import normalize_calendar_participants


def test_recipient_candidate_classes_prepare_future_delivery_without_sending() -> None:
    participants = normalize_calendar_participants(
        [
            {"participant_kind": "organizer", "email": "owner@example.test", "response_status": "organizer"},
            {"participant_kind": "required_attendee", "email": "internal@example.test", "response_status": "accepted"},
            {"participant_kind": "optional_attendee", "email": "optional@external.test", "response_status": "needs_action"},
            {"participant_kind": "required_attendee", "email": "declined@external.test", "response_status": "declined"},
            {"participant_kind": "room", "email": "room@example.test"},
            {"participant_kind": "group", "email": "team@example.test"},
            {"participant_kind": "required_attendee", "email": None},
        ]
    )

    classes = {participant["recipient_candidate_class"] for participant in participants}

    assert {
        "organizer",
        "internal_attendee",
        "optional_attendee",
        "declined",
        "room",
        "group",
        "unavailable",
    } <= classes
    assert all("send" not in participant for participant in participants)
    assert all("share_grant" not in participant for participant in participants)
    assert all("access_grant" not in participant for participant in participants)
