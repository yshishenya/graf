from twobrain_rec_server.cabinet import view_models


def test_cabinet_navigation_model_keeps_one_online_meetings_nav() -> None:
    navigation = view_models.cabinet_navigation(active="meetings", pending_actions=3)

    assert navigation.active == "meetings"
    assert navigation.workspace_title == "Личный"
    assert navigation.workspace_subtitle == ""
    meetings = next(item for item in navigation.items if item.id == "meetings")
    settings = next(item for item in navigation.items if item.id == "settings")
    assert meetings.href == "/meetings"
    assert meetings.enabled is True
    assert settings.href == "/settings/integrations/calendar"
    assert settings.enabled is True
    assert [item.id for item in navigation.items] == ["meetings", "settings"]
    assert all(item.enabled for item in navigation.items)
    assert all(item.count is None for item in navigation.items)
    assert all(item.icon for item in navigation.items)


def test_embedded_cabinet_navigation_targets_desktop_calendar_settings_route() -> None:
    navigation = view_models.cabinet_navigation(active="meetings", pending_actions=3, embedded=True)
    meetings = next(item for item in navigation.items if item.id == "meetings")
    settings = next(item for item in navigation.items if item.id == "settings")

    assert meetings.href == "/desktop/meetings"
    assert settings.href == "/desktop/settings/integrations/calendar"


def test_cabinet_navigation_can_activate_settings() -> None:
    navigation = view_models.cabinet_navigation(active="settings")

    assert navigation.active == "settings"
    assert next(item for item in navigation.items if item.id == "settings").label == "Настройки"


def test_cabinet_navigation_falls_back_to_enabled_destination() -> None:
    navigation = view_models.cabinet_navigation(active="search")
    meetings = next(item for item in navigation.items if item.id == "meetings")

    assert all(item.id != "search" for item in navigation.items)
    assert meetings.enabled is True
    assert navigation.active == "meetings"
