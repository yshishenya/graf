from twobrain_rec_server.calendar.normalize import normalize_calendar_participants


def test_participant_normalization_classifies_roles_responses_and_candidates() -> None:
    participants = normalize_calendar_participants(
        [
            {
                "participant_kind": "organizer",
                "email": "owner@example.test",
                "response_status": "organizer",
            },
            {
                "participant_kind": "required_attendee",
                "email": "internal@example.test",
                "response_status": "accepted",
            },
            {
                "participant_kind": "optional_attendee",
                "email": "guest@external.test",
                "response_status": "tentative",
            },
            {
                "participant_kind": "required_attendee",
                "email": "declined@external.test",
                "response_status": "declined",
            },
            {"participant_kind": "resource", "email": "projector@example.test"},
            {"participant_kind": "room", "email": "room@example.test"},
            {"participant_kind": "group", "email": "team@example.test"},
            {
                "participant_kind": "required_attendee",
                "email": None,
                "display_name": "Hidden attendee",
            },
            {
                "participant_kind": "required_attendee",
                "email": "internal@example.test",
                "response_status": "accepted",
            },
        ]
    )

    by_kind = {(item["participant_kind"], item.get("email")): item for item in participants}

    assert len(participants) == 8
    assert by_kind[("organizer", "owner@example.test")]["recipient_candidate_class"] == "organizer"
    assert (
        by_kind[("required_attendee", "internal@example.test")]["workspace_relation"] == "internal"
    )
    assert (
        by_kind[("required_attendee", "internal@example.test")]["recipient_candidate_class"]
        == "internal_attendee"
    )
    assert (
        by_kind[("optional_attendee", "guest@external.test")]["recipient_candidate_class"]
        == "optional_attendee"
    )
    assert (
        by_kind[("required_attendee", "declined@external.test")]["recipient_candidate_class"]
        == "declined"
    )
    assert (
        by_kind[("resource", "projector@example.test")]["recipient_candidate_class"] == "resource"
    )
    assert by_kind[("room", "room@example.test")]["recipient_candidate_class"] == "room"
    assert by_kind[("group", "team@example.test")]["recipient_candidate_class"] == "group"
    assert by_kind[("required_attendee", None)]["recipient_candidate_class"] == "unavailable"


def test_us6_participant_normalization_keeps_calendar_people_as_roster_metadata_only() -> None:
    # T084; FR-020/FR-022; SC-008 (speaker-assignment slice): input hints cannot cross domains.
    participant = normalize_calendar_participants(
        [
            {
                "participant_kind": "required_attendee",
                "email": "person@example.test",
                "display_name": "Synthetic Calendar Person",
                "speaker_label": "SPEAKER_77",
                "transcript_speaker_label": "SPEAKER_77",
                "diarization_speaker_label": "SPEAKER_77",
                "access_grant": True,
                "share_grant": True,
                "send": True,
            }
        ]
    )[0]

    assert participant["display_name"] == "Synthetic Calendar Person"
    assert set(participant) == {
        "participant_kind",
        "response_status",
        "email",
        "email_hash",
        "display_name",
        "workspace_relation",
        "recipient_candidate_class",
    }
    assert {
        "speaker_label",
        "transcript_speaker_label",
        "diarization_speaker_label",
        "access_grant",
        "share_grant",
        "send",
    }.isdisjoint(participant)


def test_098_participant_normalization_rejects_email_like_display_name() -> None:
    # FR-030/SC-011: an email-shaped display label is presence metadata, not safe copy.
    participant = normalize_calendar_participants(
        [
            {
                "participant_kind": "required_attendee",
                "email": "person@example.test",
                "display_name": "person@example.test",
            }
        ]
    )[0]

    assert participant["email_hash"] is not None
    assert participant["display_name"] is None
