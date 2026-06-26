from twobrain_rec_server.cabinet import view_models


def test_cabinet_navigation_model_keeps_one_online_meetings_nav() -> None:
    navigation = view_models.cabinet_navigation(active="meetings", pending_actions=3)

    assert navigation.active == "meetings"
    assert navigation.workspace_title == "Личный"
    meetings = next(item for item in navigation.items if item.id == "meetings")
    actions = next(item for item in navigation.items if item.id == "actions")
    disabled = [item for item in navigation.items if not item.enabled]

    assert meetings.href == "/meetings"
    assert meetings.enabled is True
    assert actions.count == 3
    assert {item.id for item in disabled} >= {"search", "shared", "actions", "activity", "settings"}
    assert all(item.icon for item in navigation.items)
