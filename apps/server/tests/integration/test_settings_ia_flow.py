import re

from tests.contract.test_ingest_openapi_contract import auth_headers


def test_settings_overview_and_categories_are_reachable_in_browser_and_embedded_modes(
    client,
) -> None:
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
        assert response.text.count('aria-label="Навигация кабинета"') == 1
        primary_sidebar = re.search(
            r'<nav class="cabinet-sidebar-nav cabinet-sidebar-nav--settings".*?</nav>',
            response.text,
            flags=re.DOTALL,
        )
        assert primary_sidebar is not None
        assert primary_sidebar.group(0).count('aria-current="page"') == 1
        content_class = (
            "calendar-settings__content"
            if "integrations/calendar" in path
            else "settings-page__content"
        )
        assert f'class="{content_class}"' in response.text
        if "/settings/account" in path:
            assert "account-navigation__logout" not in response.text


def test_calendar_htmx_response_preserves_fragment_boundary_without_sidebar(client) -> None:
    for path in ("/settings/integrations/calendar", "/desktop/settings/integrations/calendar"):
        response = client.get(path, headers={**auth_headers(), "HX-Request": "true"})

        assert response.status_code == 200
        assert response.text.count('id="calendar-settings-region"') == 1
        assert 'data-cabinet-fragment="calendar-settings"' in response.text
        assert 'class="calendar-settings__content"' in response.text
        assert 'aria-label="Навигация кабинета"' not in response.text
        assert "<!doctype html>" not in response.text


def test_settings_related_surfaces_keep_one_outer_navigation(client) -> None:
    for path in ("/billing", "/referrals", "/account/fair-use", "/desktop/account/fair-use"):
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, path
        assert response.text.count('aria-label="Навигация кабинета"') == 1
        assert response.text.count('aria-current="page"') == 1
        assert 'class="settings-page__content"' in response.text
        assert 'class="settings-navigation"' not in response.text


def test_account_center_aliases_are_reachable_from_cabinet_navigation(client) -> None:
    for path in (
        "/account",
        "/account/profile",
        "/account/security",
        "/account/notifications",
        "/desktop/account",
        "/desktop/account/profile",
        "/desktop/account/security",
        "/desktop/account/notifications",
    ):
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200, path
        if "notifications" in path:
            assert "Дополнительные уведомления" in response.text
        else:
            assert 'data-settings-primary-nav-item="account"' in response.text
            assert "Аккаунт и безопасность" in response.text
            assert "account-navigation__logout" in response.text
            account_group = re.search(
                r'<div class="account-navigation" role="group".*?</div>',
                response.text,
                flags=re.DOTALL,
            )
            assert account_group is not None
            assert account_group.group(0).count('aria-current="page"') == 1
        assert response.text.count('aria-label="Навигация кабинета"') == 1
        primary_sidebar = re.search(
            r'<nav class="cabinet-sidebar-nav cabinet-sidebar-nav--settings".*?</nav>',
            response.text,
            flags=re.DOTALL,
        )
        assert primary_sidebar is not None
        assert primary_sidebar.group(0).count('aria-current="page"') == 1


def test_settings_sidebar_is_present_and_calendar_maps_to_parent_category(client) -> None:
    expected_ids = (
        "meetings",
        "overview",
        "recording",
        "summaries",
        "calendar",
        "workspace",
        "account",
        "notifications",
        "billing",
    )

    for path in ("/settings/integrations/calendar", "/desktop/settings/integrations/calendar"):
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200
        for category_id in expected_ids:
            assert response.text.count(f'data-settings-primary-nav-item="{category_id}"') == 1
        assert response.text.count('aria-label="Навигация кабинета"') == 1
        assert 'aria-label="Разделы настроек"' not in response.text
        assert response.text.count('aria-current="page"') == 1
        calendar_link = re.search(
            r'<a[^>]+data-settings-primary-nav-item="calendar"[^>]*>', response.text
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
