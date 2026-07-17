from uuid import uuid4

from fastapi.routing import APIRoute

from twobrain_rec_server.cabinet.rendering import (
    render_provider_link_settings_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.view_models import (
    ProviderLinkSettingsSurface,
    ProviderLinkStartOption,
)
from twobrain_rec_server.cabinet.web_routes.provider_links import router as provider_link_router


def test_settings_provider_link_actions_share_browser_and_embedded_contract() -> None:
    options = (
        ProviderLinkStartOption(provider="yandex", label="Яндекс"),
        ProviderLinkStartOption(provider="vk", label="VK"),
    )

    browser = render_settings_page(csrf_token="safe-csrf", provider_link_options=options)
    embedded = render_settings_page(
        embedded=True,
        csrf_token="safe-csrf",
        provider_link_options=options,
    )

    assert 'action="/settings/provider-links/yandex/start"' in browser
    assert 'action="/desktop/settings/provider-links/yandex/start"' in embedded
    assert 'name="csrf_token" value="safe-csrf"' in browser
    assert 'name="csrf_token" value="safe-csrf"' in embedded
    for page in (browser, embedded):
        assert "Способы входа" in page
        assert "Добавьте ещё один способ входа" in page
        assert "provider_subject" not in page
        assert "candidate_email" not in page
        assert "candidate_phone" not in page


def test_pending_provider_link_confirmation_renders_safe_copy_only() -> None:
    surface = ProviderLinkSettingsSurface(
        link_state_id=uuid4(),
        provider_label="VK",
        status="callback_verified",
        status_label="Провайдер подтверждён — подтвердите подключение в GRAF",
        can_confirm=True,
    )

    page = render_provider_link_settings_page(surface, csrf_token="safe-csrf")

    assert "Подтвердить подключение" in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    assert f'action="/settings/provider-links/{surface.link_state_id}/confirm"' in page
    assert "email" not in page.lower()
    assert "phone" not in page.lower()
    assert "subject" not in page.lower()
    assert 'id="cabinet-main" class="cabinet-main" tabindex="-1"' in page
    assert 'role="status" aria-live="polite"' in page
    assert '<button class="button primary" type="submit">Подтвердить подключение</button>' in page


def test_provider_link_settings_mutations_require_csrf_on_both_surfaces() -> None:
    csrf_routes = {
        "/settings/provider-links/{provider}/start",
        "/desktop/settings/provider-links/{provider}/start",
        "/settings/provider-links/{link_state_id}/confirm",
        "/desktop/settings/provider-links/{link_state_id}/confirm",
    }
    dependencies = {
        route.path: {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }
        for route in provider_link_router.routes
        if isinstance(route, APIRoute) and route.path in csrf_routes
    }

    assert set(dependencies) == csrf_routes
    assert all("require_web_csrf" in route_dependencies for route_dependencies in dependencies.values())


def test_terminal_provider_link_settings_states_render_only_safe_generic_copy() -> None:
    cases = {
        "expired": "Срок подключения истёк. Начните заново.",
        "rejected": "Подключение не завершено. Начните заново.",
        "unknown": "Подключение недоступно. Начните заново.",
    }

    for status, status_label in cases.items():
        page = render_provider_link_settings_page(
            ProviderLinkSettingsSurface(
                link_state_id=uuid4(),
                provider_label="VK",
                status=status,
                status_label=status_label,
                can_confirm=False,
            ),
            csrf_token="safe-csrf",
            result="provider_link_conflict",
        )
        assert status_label in page
        assert "provider_link_conflict" not in page
        assert "candidate" not in page.lower()
        assert "Подтвердить подключение" not in page
