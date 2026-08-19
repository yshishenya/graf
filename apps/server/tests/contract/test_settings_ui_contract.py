import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.routing import APIRoute

from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import (
    AccountDeviceView,
    AccountProviderView,
    account_settings_surface,
)
from twobrain_rec_server.cabinet.web_routes.settings import router as settings_router
from twobrain_rec_server.db.models import ExternalIdentity


def test_settings_overview_exposes_supported_categories_in_primary_sidebar() -> None:
    browser = render_settings_page()
    embedded = render_settings_page(embedded=True)

    for page, prefix in ((browser, "/settings"), (embedded, "/desktop/settings")):
        assert "<h1>Настройки</h1>" in page
        assert f'href="{prefix}/recording"' in page
        assert f'href="{prefix}/summaries"' in page
        assert f'href="{prefix}/integrations/calendar"' in page
        assert f'href="{prefix}/workspace"' in page
        assert f'href="{prefix}/account"' in page
        assert page.count("data-settings-primary-nav>") == 1
        assert page.count("data-settings-primary-nav-item") == 9
        assert '<span class="cabinet-sidebar-nav__section-label">Настройки</span>' in page
        assert 'class="settings-navigation"' not in page
        assert "provider_subject" not in page
        assert "candidate_identity_subject" not in page


def test_settings_sidebar_exposes_canonical_links_and_active_state() -> None:
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
    expected_icons = {
        "recording": "video",
        "summaries": "transcript",
        "calendar": "calendar-days",
        "workspace": "users-round",
        "account": "settings",
        "billing": "activity",
    }
    expected_suffixes = {
        "recording": "/recording",
        "summaries": "/summaries",
        "calendar": "/integrations/calendar",
        "workspace": "/workspace",
        "account": "/account",
        "billing": "/billing",
    }

    for category in ("overview", "recording", "summaries", "workspace", "account"):
        for embedded, prefix in ((False, "/settings"), (True, "/desktop/settings")):
            page = render_settings_page(embedded=embedded, category=category)
            navigation = re.search(
                r'<nav class="cabinet-sidebar-nav cabinet-sidebar-nav--settings".*?</nav>',
                page,
                flags=re.DOTALL,
            )

            assert navigation is not None
            markup = navigation.group(0)
            assert (
                tuple(re.findall(r'data-settings-primary-nav-item="([^"]+)"', markup))
                == expected_ids
            )
            if category == "overview":
                assert markup.count('aria-current="page"') == 1
                assert 'data-settings-primary-nav-item="overview"' in markup
            else:
                assert markup.count('aria-current="page"') == 1
                assert f'data-settings-primary-nav-item="{category}"' in markup
            assert "<small>" not in markup
            assert 'class="settings-navigation"' not in markup
            for category_id, suffix in expected_suffixes.items():
                expected_href = (
                    "/billing" if embedded and category_id == "billing" else prefix + suffix
                )
                assert re.search(
                    rf'<a[^>]+href="{re.escape(expected_href)}"[^>]*'
                    rf'data-settings-primary-nav-item="{category_id}"[^>]*>',
                    markup,
                ) or re.search(
                    rf'<a[^>]+data-settings-primary-nav-item="{category_id}"[^>]*'
                    rf'href="{re.escape(expected_href)}"[^>]*>',
                    markup,
                )
                assert re.search(
                    rf'data-settings-primary-nav-item="{category_id}"[^>]*>.*?'
                    rf'data-icon="{expected_icons[category_id]}"',
                    markup,
                    flags=re.DOTALL,
                )


def test_settings_css_has_reduced_motion_and_narrow_reflow_guards() -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )
    reduced_motion = css[css.index("@media (prefers-reduced-motion: reduce)") :]
    narrow = css[css.index("@media (max-width: 640px)") :]

    assert "transition-duration: .01ms" in reduced_motion
    assert "animation-duration: .01ms" in reduced_motion
    assert "grid-template-columns: 1fr" in narrow
    desktop_reflow = css[css.index(".settings-page,") : css.index("@media (max-width: 640px)")]
    assert "overflow-x: auto" not in desktop_reflow


def test_settings_templates_use_primary_sidebar_and_single_content_column() -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )

    single_column_css = css[css.index(".settings-page,") : css.index(".settings-section {")]
    assert "grid-template-columns: minmax(0, 1fr)" in single_column_css
    assert "grid-column: 1" in single_column_css
    assert "gap: 0" in single_column_css
    assert ".settings-navigation" not in css
    assert ".settings-page {\n  grid-template-columns" not in css

    for page in (
        render_settings_page(category="summaries"),
        render_settings_page(category="recording", embedded=True),
    ):
        assert page.count('aria-label="Навигация кабинета"') == 1
        assert page.count('aria-current="page"') == 1
        assert 'class="settings-page__content"' in page

    templates = root / "src/twobrain_rec_server/cabinet/templates/cabinet"
    content_templates = [*templates.glob("pages/*_content.html")]
    content_templates.extend(
        templates / fragment
        for fragment in (
            "fragments/calendar_settings.html",
            "fragments/provider_link_settings.html",
        )
    )
    for template in content_templates:
        source = template.read_text(encoding="utf-8")
        assert "components/settings_navigation.html" not in source, template
        assert "settings_ui.navigation(" not in source, template

    calendar_template = content_templates[-2].read_text(encoding="utf-8")
    provider_template = content_templates[-1].read_text(encoding="utf-8")
    assert (
        'id="calendar-settings-region" data-cabinet-fragment="calendar-settings"'
        in calendar_template
    )
    assert 'class="calendar-settings__content"' in calendar_template
    assert '<main id="cabinet-main" class="cabinet-main" tabindex="-1">' in provider_template
    assert 'class="settings-page__content"' in provider_template
    assert not (templates / "components/settings_navigation.html").exists()
    assert "settings_mode=" not in (
        root / "src/twobrain_rec_server/cabinet/rendering_shared.py"
    ).read_text(encoding="utf-8")


def test_settings_overview_keeps_navigation_primary_and_copy_compact() -> None:
    page = render_settings_page()

    assert "Выберите раздел. Область действия указана в каждой карточке." in page
    assert page.count('data-settings-category="') == 7
    assert "Разрешения, автозапись и приложения настраиваются в GRAF для macOS." in page
    assert "Текущий тариф, использование, хранилище и платежные состояния." in page
    assert page.count('data-settings-primary-nav-item="') == 9


def test_settings_overview_matches_product_reference_geometry() -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )
    redesign = css[css.index("/* Additional settings redesign styles */") :]

    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in redesign
    assert "max-width: 780px;" in redesign
    assert "min-height: 138px;" in redesign
    assert "border-radius: 8px;" in redesign
    assert "background: transparent;" in redesign
    assert ".settings-scope-badge," in redesign
    assert ".settings-scope-badge {" in redesign
    assert "min-height: 24px;" in redesign
    assert "padding: 2px 7px;" in redesign
    assert "font: 600 11px ui-monospace" in redesign


def test_recording_settings_keep_native_boundary_copy_compact() -> None:
    page = render_settings_page(category="recording")
    embedded_page = render_settings_page(category="recording", embedded=True)

    assert "Настройка записи находится в приложении GRAF" in page
    assert "Старт и стоп доступны всегда" in page
    assert "Здесь нельзя включить запись для всех встреч" not in page
    assert "Веб-интерфейс показывает результат записи" not in page
    assert "/desktop/settings/meeting-detection" not in page
    assert 'data-sidebar-download href="/download"' in page
    assert page.count("data-sidebar-download") == 1
    assert "data-sidebar-download" not in embedded_page
    assert (
        '/desktop/settings/meeting-detection">Открыть настройки записи в приложении'
        in embedded_page
    )


def test_settings_account_close_phrase_is_described_to_confirmation_field() -> None:
    page = render_settings_page(category="account")

    assert 'id="account-close-confirmation"' in page
    assert 'aria-describedby="account-close-confirmation account-close-help"' in page


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
    paths = {route.path for route in settings_router.routes if isinstance(route, APIRoute)}

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


def test_account_profile_and_session_mutations_are_csrf_protected() -> None:
    expected = {
        "/settings/account/profile",
        "/desktop/settings/account/profile",
        "/settings/account/sessions/{session_id}/revoke",
        "/desktop/settings/account/sessions/{session_id}/revoke",
    }
    routes = {route.path: route for route in settings_router.routes if isinstance(route, APIRoute)}
    assert expected <= routes.keys()
    for path in expected:
        dependencies = {
            getattr(dependency.call, "__name__", "")
            for dependency in routes[path].dependant.dependencies
            if dependency.call is not None
        }
        assert "require_web_csrf" in dependencies


def test_account_preferences_and_provider_unlink_are_csrf_protected() -> None:
    expected = {
        "/settings/account/preferences",
        "/desktop/settings/account/preferences",
        "/settings/account/providers/{identity_id}/unlink",
        "/desktop/settings/account/providers/{identity_id}/unlink",
    }
    routes = {route.path: route for route in settings_router.routes if isinstance(route, APIRoute)}
    assert expected <= routes.keys()
    for path in expected:
        dependencies = {
            getattr(dependency.call, "__name__", "")
            for dependency in routes[path].dependant.dependencies
            if dependency.call is not None
        }
        assert "require_web_csrf" in dependencies


def test_account_surface_template_contains_profile_preference_and_session_controls() -> None:
    page = render_settings_page(category="account")
    for label in ("Профиль", "Язык интерфейса", "Часовой пояс", "Системная", "Активные сессии"):
        assert label in page
    assert "data-account-preferences" in page
    assert "session_token_hash" not in page
    assert 'method="post"' in page
    assert "/settings/account/preferences" in page


def test_account_surface_exposes_unlink_only_for_recovery_safe_provider() -> None:
    first = ExternalIdentity(
        id=uuid4(), user_id=uuid4(), provider="yandex", provider_subject="one", is_verified=True
    )
    second = ExternalIdentity(
        id=uuid4(), user_id=first.user_id, provider="vk", provider_subject="two", is_verified=True
    )
    surface = account_settings_surface(
        identities=(first, second),
        can_unlink_provider=lambda identity: identity.is_verified,
    )
    page = render_settings_page(category="account", account_surface=surface)
    assert page.count("/settings/account/providers/") == 2


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
    for path in root.glob(
        "src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings*_content.html"
    ):
        source = path.read_text(encoding="utf-8")
        assert "provider_subject" not in source
        assert "candidate_identity_subject" not in source


def test_settings_accessibility_contract_preserves_dialog_focus_and_form_state() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text(
        encoding="utf-8"
    )
    calendar = (
        root / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html"
    ).read_text(encoding="utf-8")

    assert "dialogOpeners" in script
    assert 'dialog.addEventListener("close"' in script
    assert "initSettingsFormState" in script
    assert 'form.dataset.state = dirty ? "dirty" : "pristine"' in script
    assert "data-settings-form-status" in calendar
    assert "data-settings-form" in calendar
