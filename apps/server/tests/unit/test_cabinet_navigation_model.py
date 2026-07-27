from twobrain_rec_server.cabinet import view_models


def test_cabinet_navigation_model_keeps_one_online_meetings_nav() -> None:
    navigation = view_models.cabinet_navigation(active="meetings")

    assert navigation.active == "meetings"
    meetings = next(item for item in navigation.items if item.id == "meetings")
    shared_with_me = next(item for item in navigation.items if item.id == "shared-with-me")
    settings = next(item for item in navigation.items if item.id == "settings")
    assert meetings.href == "/meetings"
    assert shared_with_me.href == "/shared-with-me"
    assert settings.href == "/settings"
    assert [item.id for item in navigation.items] == ["meetings", "shared-with-me", "settings"]
    assert all(item.icon for item in navigation.items)


def test_embedded_cabinet_navigation_targets_desktop_settings_overview() -> None:
    navigation = view_models.cabinet_navigation(active="meetings", embedded=True)
    meetings = next(item for item in navigation.items if item.id == "meetings")
    shared_with_me = next(item for item in navigation.items if item.id == "shared-with-me")
    settings = next(item for item in navigation.items if item.id == "settings")

    assert meetings.href == "/desktop/meetings"
    assert shared_with_me.href == "/desktop/shared-with-me"
    assert settings.href == "/desktop/settings"


def test_cabinet_navigation_can_activate_settings() -> None:
    navigation = view_models.cabinet_navigation(active="settings")

    assert navigation.active == "settings"
    assert next(item for item in navigation.items if item.id == "settings").label == "Настройки"
    assert next(item for item in navigation.items if item.id == "settings").href == "/settings"


def test_cabinet_navigation_falls_back_to_available_destination() -> None:
    navigation = view_models.cabinet_navigation(active="search")

    assert all(item.id != "search" for item in navigation.items)
    assert navigation.active == "meetings"
