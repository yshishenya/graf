import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.routing import APIRoute

from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import (
    AccountDeviceView,
    AccountProviderView,
)
from twobrain_rec_server.cabinet.web_routes.settings import router as settings_router


def test_settings_overview_exposes_supported_categories_and_group_labels() -> None:
    browser = render_settings_page()
    embedded = render_settings_page(embedded=True)

    for page, prefix in ((browser, "/settings"), (embedded, "/desktop/settings")):
        assert "<h1>Настройки</h1>" in page
        assert f'href="{prefix}/recording"' in page
        assert f'href="{prefix}/summaries"' in page
        assert f'href="{prefix}/integrations/calendar"' in page
        assert f'href="{prefix}/workspace"' in page
        assert f'href="{prefix}/account"' in page
        assert 'class="settings-navigation__group-label"' in page
        assert ">Встречи</h2>" in page
        assert ">Рабочее пространство</h2>" in page
        assert ">Аккаунт</h2>" in page
        assert "provider_subject" not in page
        assert "candidate_identity_subject" not in page


def test_settings_sidebar_exposes_grouped_canonical_links_and_active_state() -> None:
    expected_ids = ("recording", "summaries", "calendar", "workspace", "account")
    expected_groups = ("Встречи", "Рабочее пространство", "Аккаунт")
    expected_icons = {
        "recording": "video",
        "summaries": "transcript",
        "calendar": "calendar-days",
        "workspace": "users-round",
        "account": "settings",
    }
    expected_suffixes = {
        "recording": "/recording",
        "summaries": "/summaries",
        "calendar": "/integrations/calendar",
        "workspace": "/workspace",
        "account": "/account",
    }

    for category in ("overview", "recording", "summaries", "workspace", "account"):
        for embedded, prefix in ((False, "/settings"), (True, "/desktop/settings")):
            page = render_settings_page(embedded=embedded, category=category)
            navigation = re.search(
                r'<nav class="settings-navigation".*?</nav>', page, flags=re.DOTALL
            )

            assert navigation is not None
            markup = navigation.group(0)
            assert tuple(re.findall(r'data-settings-nav="([^"]+)"', markup)) == expected_ids
            assert tuple(
                re.findall(r'class="settings-navigation__group-label"[^>]*>([^<]+)', markup)
            ) == expected_groups
            if category == "overview":
                assert markup.count('aria-current="page"') == 0
            else:
                assert markup.count('aria-current="page"') == 1
                assert f'data-settings-nav="{category}"' in markup
            assert "settings-navigation__item-icon" in markup
            assert "<small>" not in markup
            assert 'role="group"' in markup
            assert f'href="{"/desktop" if embedded else ""}/meetings"' in markup
            for category_id, suffix in expected_suffixes.items():
                assert re.search(
                    rf'<a[^>]+href="{re.escape(prefix + suffix)}"[^>]*'
                    rf'data-settings-nav="{category_id}"[^>]*>',
                    markup,
                ) or re.search(
                    rf'<a[^>]+data-settings-nav="{category_id}"[^>]*'
                    rf'href="{re.escape(prefix + suffix)}"[^>]*>',
                    markup,
                )
                assert re.search(
                    rf'data-settings-nav="{category_id}"[^>]*>.*?data-icon="{expected_icons[category_id]}"',
                    markup,
                    flags=re.DOTALL,
                )


def test_settings_sidebar_uses_vertical_accessible_layout_without_horizontal_only_menu() -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )
    navigation_css = css[css.index(".settings-navigation {") : css.index(".settings-scope-badge")]

    assert "overflow-x: auto" not in navigation_css
    assert "min-height: 44px" in navigation_css
    assert ".settings-navigation__item:focus-visible" in navigation_css
    assert ".settings-navigation__item-icon" in navigation_css
    assert ".settings-navigation__back" in navigation_css
    assert "color: var(--muted)" in navigation_css
    assert "grid-template-columns: 1fr" in css[css.index("@media (max-width: 640px)") :]


def test_settings_overview_keeps_navigation_primary_and_copy_compact() -> None:
    page = render_settings_page()

    assert "Здесь собраны только доступные сейчас настройки" not in page
    assert "Что можно настроить" not in page
    assert "data-settings-category=" not in page
    assert page.count('data-settings-nav="') == 5


def test_recording_settings_keep_native_boundary_copy_compact() -> None:
    page = render_settings_page(category="recording")
    embedded_page = render_settings_page(category="recording", embedded=True)

    assert "Настройка записи находится в приложении GRAF" in page
    assert "Старт и стоп доступны всегда" in page
    assert "Здесь нельзя включить запись для всех встреч" not in page
    assert "Веб-интерфейс показывает результат записи" not in page
    assert "/desktop/settings/meeting-detection" not in page
    assert '/desktop/settings/meeting-detection">Открыть настройки записи в приложении' in embedded_page


def test_calendar_settings_keeps_sidebar_content_gap_after_late_rules() -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )

    calendar_rules = re.findall(r"\.calendar-settings\s*\{([^}]*)\}", css)

    assert calendar_rules
    assert any("gap: var(--settings-gap);" in rule for rule in calendar_rules)
    assert "--settings-gap: 24px" in css


def test_calendar_provider_anchor_preserves_keyboard_focus_target() -> None:
    root = Path(__file__).resolve().parents[2]
    template = (
        root / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html"
    ).read_text(encoding="utf-8")
    assert 'id="calendar-providers-title" tabindex="-1"' in template
    assert "scroll-margin-block-start" in (
        root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
    ).read_text(encoding="utf-8")


def test_settings_route_map_has_no_arbitrary_category_redirect() -> None:
    paths = {
        route.path
        for route in settings_router.routes
        if isinstance(route, APIRoute)
    }

    assert paths >= {
        "/settings",
        "/settings/recording",
        "/settings/summaries",
        "/settings/workspace",
        "/settings/account",
        "/desktop/settings",
        "/desktop/settings/recording",
        "/desktop/settings/summaries",
        "/desktop/settings/workspace",
        "/desktop/settings/account",
    }
    assert "/settings/{path}" not in paths


def test_settings_device_mutation_requires_web_csrf() -> None:
    paths = {
        "/settings/account/devices/{device_id}/revoke",
        "/desktop/settings/account/devices/{device_id}/revoke",
    }
    dependencies = {
        route.path: {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }
        for route in settings_router.routes
        if isinstance(route, APIRoute) and route.path in paths
    }

    assert set(dependencies) == paths
    assert all("require_web_csrf" in values for values in dependencies.values())


def test_account_markup_accepts_only_safe_presentation_fields() -> None:
    provider = AccountProviderView(
        provider="yandex",
        label="Яндекс",
        status_label="Подключён",
        primary=True,
        connected_at=datetime(2026, 7, 25, tzinfo=UTC),
    )
    device = AccountDeviceView(
        device_id=uuid4(),
        platform_label="Mac",
        version_label="1.2.3",
        status_label="Активно",
        last_seen_at=datetime(2026, 7, 25, tzinfo=UTC),
        current=True,
        can_revoke=False,
    )

    assert provider.provider == "yandex"
    assert provider.label == "Яндекс"
    assert device.platform_label == "Mac"
    assert "subject" not in provider.__dataclass_fields__
    assert "secret" not in device.__dataclass_fields__


def test_settings_templates_keep_security_copy_metadata_only() -> None:
    root = Path(__file__).resolve().parents[2]
    for path in root.glob("src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings*_content.html"):
        source = path.read_text(encoding="utf-8")
        assert "provider_subject" not in source
        assert "candidate_identity_subject" not in source


def test_settings_accessibility_contract_preserves_dialog_focus_and_form_state() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text(
        encoding="utf-8"
    )
    calendar = (
        root
        / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html"
    ).read_text(encoding="utf-8")

    assert "dialogOpeners" in script
    assert 'dialog.addEventListener("close"' in script
    assert "initSettingsFormState" in script
    assert 'form.dataset.state = dirty ? "dirty" : "pristine"' in script
    assert "data-settings-form-status" in calendar
    assert "data-settings-form" in calendar
