import re

from tests.contract.test_ingest_openapi_contract import auth_headers


def test_settings_overview_and_categories_are_reachable_in_browser_and_embedded_modes(client) -> None:
    paths = (
        "/settings",
        "/settings/recording",
        "/settings/summaries",
        "/settings/workspace",
        "/settings/account",
        "/settings/integrations/calendar",
        "/desktop/settings",
        "/desktop/settings/recording",
        "/desktop/settings/summaries",
        "/desktop/settings/workspace",
        "/desktop/settings/account",
        "/desktop/settings/integrations/calendar",
    )

    for path in paths:
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200, path
        main_id = "calendar-settings-region" if "integrations/calendar" in path else "cabinet-main"
        assert f'id="{main_id}"' in response.text
        assert "Настройки" in response.text


def test_settings_sidebar_is_present_and_calendar_maps_to_parent_category(client) -> None:
    expected_ids = ("overview", "recording", "summaries", "calendar", "workspace", "account")

    for path in ("/settings/integrations/calendar", "/desktop/settings/integrations/calendar"):
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200
        for category_id in expected_ids:
            assert response.text.count(f'data-settings-nav="{category_id}"') == 1
        assert response.text.count('aria-label="Разделы настроек"') == 1
        assert response.text.count('data-settings-nav="calendar"') == 1
        assert response.text.count('aria-current="page"') == 2
        calendar_link = re.search(
            r'<a[^>]+data-settings-nav="calendar"[^>]*>', response.text
        )
        assert calendar_link is not None
        assert 'aria-current="page"' in calendar_link.group(0)


def test_settings_overview_does_not_expose_auth_or_capture_policy_details(client) -> None:
    response = client.get("/settings", headers=auth_headers())

    assert response.status_code == 200
    assert "provider_subject" not in response.text
    assert "candidate_identity_subject" not in response.text
    assert "record all" not in response.text.lower()
    assert "audio routing" not in response.text.lower()
