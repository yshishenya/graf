from twobrain_rec_server.db.rls_validation import RLS_DIRECT_WORKSPACE_TABLES


def test_calendar_tables_are_in_rls_workspace_inventory() -> None:
    expected = {
        "calendar_sources",
        "calendar_credential_envelopes",
        "external_calendars",
        "calendar_event_snapshots",
        "calendar_participants",
        "conference_link_candidates",
        "recording_calendar_context_links",
        "calendar_reminder_states",
        "calendar_settings_preferences",
        "calendar_audit_events",
    }

    assert expected <= RLS_DIRECT_WORKSPACE_TABLES
