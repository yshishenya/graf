from uuid import uuid4

from twobrain_rec_server.cabinet.rendering import (
    render_provider_link_settings_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.view_models import (
    ProviderLinkSettingsSurface,
    ProviderLinkStartOption,
)


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
