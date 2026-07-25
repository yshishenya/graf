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


def test_settings_overview_exposes_supported_categories_and_scope_labels() -> None:
    browser = render_settings_page()
    embedded = render_settings_page(embedded=True)

    for page, prefix in ((browser, "/settings"), (embedded, "/desktop/settings")):
        assert "<h1>Настройки</h1>" in page
        assert f'href="{prefix}/recording"' in page
        assert f'href="{prefix}/summaries"' in page
        assert f'href="{prefix}/workspace"' in page
        assert f'href="{prefix}/account"' in page
        assert "Личная настройка" in page
        assert "В этом пространстве" in page
        assert "На этом Mac" in page
        assert "provider_subject" not in page
        assert "candidate_identity_subject" not in page


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
