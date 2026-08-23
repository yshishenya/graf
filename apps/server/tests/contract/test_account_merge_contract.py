import re
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    MergePreview,
    build_merge_preview,
    ensure_preview_confirmable,
)
from twobrain_rec_server.cabinet.auth_rendering import (
    render_email_code_page,
    render_login_page,
)
from twobrain_rec_server.cabinet.rendering import (
    render_account_merge_page,
    render_provider_link_settings_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.view_models import provider_link_settings_surface
from twobrain_rec_server.cabinet.web_routes import account_merge as account_merge_routes


@pytest.mark.parametrize(
    "field,code",
    (
        ("role_conflict", "workspace_role_conflict"),
        ("billing_conflict", "billing_conflict"),
        ("calendar_conflict", "calendar_ownership_conflict"),
        ("deletion_conflict", "deletion_state_conflict"),
    ),
)
def test_merge_blockers_are_deterministic_and_fail_closed(field: str, code: str) -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        counts=MergeEntityCounts(meetings=1),
        **{field: True},
    )

    assert preview.blocker_codes == (code,)
    with pytest.raises(AccountMergeError, match=code):
        ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)


def test_merge_preview_fingerprint_changes_when_preserved_counts_change() -> None:
    survivor = uuid4()
    source = uuid4()
    first = build_merge_preview(
        survivor_user_id=survivor,
        source_user_id=source,
        counts=MergeEntityCounts(meetings=1),
    )
    changed = build_merge_preview(
        survivor_user_id=survivor,
        source_user_id=source,
        counts=MergeEntityCounts(meetings=2),
    )

    assert first.fingerprint != changed.fingerprint
    with pytest.raises(AccountMergeError, match="merge_preview_stale"):
        ensure_preview_confirmable(changed, fingerprint=first.fingerprint)


def test_merge_page_continues_email_task_with_compact_ia_and_actual_providers() -> None:
    preview = MergePreview(
        survivor_user_id=UUID("00000000-0000-0000-0000-000000000002"),
        source_user_id=UUID("00000000-0000-0000-0000-000000000003"),
        counts=MergeEntityCounts(meetings=2, recordings=3, artifacts=4, processing=5),
        blocker_codes=(),
        survivor_provider_ids=("yandex",),
        source_provider_ids=("email", "vk"),
        workspace_count_after=2,
    )

    page = render_account_merge_page(
        preview,
        intent_id=UUID("00000000-0000-0000-0000-000000000001"),
        csrf_token="safe-csrf",
        provider_id="email",
    )

    assert "<h1>Один профиль — все способы входа</h1>" in page
    assert '<h2 id="account-linking-result-title">Что изменится</h2>' in page
    assert page.count("<h2") == 1
    for copy in (
        "Сейчас",
        "После подключения",
        "Яндекс ID",
        "Email",
        "VK ID",
        "Одно личное пространство",
        "Личные встречи объединятся в одном списке",
        "Ничего не удаляется",
        "После подключения потребуется войти снова",
        "Настройки, устройства и сессии",
        "Подключить Email",
        "Оставить профили раздельными",
    ):
        assert copy in page
    assert "<details" in page
    assert "<summary" in page
    assert "Подтвердить объединение" not in page
    assert "Безопасное объединение аккаунтов" not in page
    assert "1 · Профиль" not in page
    assert "2 · Данные" not in page
    assert "3 · Безопасность" not in page
    visible_text = re.sub(r"<[^>]+>", " ", page).lower()
    for internal_term in (
        "merge intent",
        "survivor",
        "ownership conflict",
        "provider subject",
        "rls",
        "объединение аккаунтов",
    ):
        assert internal_term not in visible_text
    assert str(preview.survivor_user_id) not in page
    assert str(preview.source_user_id) not in page


@pytest.mark.parametrize(
    ("provider_id", "provider_label"),
    (("yandex", "Яндекс ID"), ("vk", "VK ID"), ("unknown", "способ входа")),
)
def test_merge_page_uses_the_proof_bound_provider_for_copy_and_primary_action(
    provider_id: str,
    provider_label: str,
) -> None:
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    page = render_account_merge_page(
        preview,
        intent_id=uuid4(),
        csrf_token="safe-csrf",
        provider_id=provider_id,
    )

    assert f"Подключить {provider_label}" in page
    assert "Подключить email" not in page
    assert "Этот email" not in page


def test_email_code_is_a_real_no_javascript_form_control() -> None:
    page = render_email_code_page(
        email="person@example.test",
        state_nonce="fresh-state",
        next_path="/settings/account",
        flow="link",
        csrf_token="safe-csrf",
    )

    assert page.count('name="code"') == 1
    assert 'name="code" type="text"' in page
    assert 'inputmode="numeric"' in page
    assert 'autocomplete="one-time-code"' in page
    assert 'pattern="[0-9]{6}"' in page
    assert 'maxlength="6"' in page
    assert "required" in page
    assert "data-code-slot" not in page
    assert "data-code-hidden" not in page


@pytest.mark.parametrize(
    ("status", "can_confirm", "can_restart"),
    (
        ("initiated", False, False),
        ("callback_verified", True, False),
        ("confirmed", False, False),
        ("rejected", False, True),
        ("expired", False, True),
        ("unavailable", False, True),
    ),
)
def test_provider_link_restart_is_only_available_for_terminal_recovery_states(
    status: str,
    can_confirm: bool,
    can_restart: bool,
) -> None:
    surface = provider_link_settings_surface(
        SimpleNamespace(
            id=uuid4(),
            candidate_provider="yandex",
            status=status,
        )
    )
    page = render_provider_link_settings_page(surface, csrf_token="safe-csrf")

    assert surface.can_confirm is can_confirm
    assert surface.can_restart is can_restart
    assert ("Подключить Яндекс ID заново" in page) is can_restart


@pytest.mark.parametrize(
    ("result", "title", "role"),
    (
        ("callback_verified", "Вход подтверждён", "status"),
        ("provider_link_denied", "Подключение отклонено", "alert"),
        ("provider_link_invalid", "Ссылка недействительна", "alert"),
        ("provider_link_expired", "Срок подключения истёк", "alert"),
        ("provider_link_reused", "Подтверждение уже использовано", "alert"),
        ("provider_link_unavailable", "Подключение временно недоступно", "alert"),
    ),
)
def test_provider_link_callback_outcomes_are_bounded_and_focusable(
    result: str,
    title: str,
    role: str,
) -> None:
    surface = provider_link_settings_surface(
        SimpleNamespace(
            id=uuid4(),
            candidate_provider="vk",
            status="callback_verified" if result == "callback_verified" else "rejected",
        )
    )

    page = render_provider_link_settings_page(surface, result=result)

    assert title in page
    assert f'role="{role}"' in page
    assert page.count("data-outcome-focus") == 1
    assert 'tabindex="-1"' in page
    assert result not in page


def test_merge_errors_have_one_focusable_outcome_region() -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        billing_conflict=True,
    )
    blockers = account_merge_routes.account_merge_blockers(
        preview.blocker_codes,
        intent_id=uuid4(),
        embedded=False,
        support_email=None,
    )

    page = render_account_merge_page(
        preview,
        intent_id=uuid4(),
        blockers=blockers,
        error_message="Данные не изменены.",
    )

    assert page.count('role="alert"') == 1
    assert page.count("data-outcome-focus") == 1
    assert page.count('aria-live="assertive"') == 0


def test_settings_and_login_results_share_the_focusable_outcome_contract() -> None:
    settings = render_settings_page(
        category="account",
        provider_link_result="provider_link_reused",
    )
    login = render_login_page(
        workspace_id=uuid4(),
        providers=[],
        error="yandex_connected_relogin_required",
    )

    for page in (settings, login):
        assert page.count("data-outcome-focus") == 1
        assert re.search(r'tabindex="-1"[^>]*data-outcome-focus', page)
    assert settings.count('role="alert"') == 1
    assert login.count('role="status"') == 1
    assert "Яндекс ID подключён" in login


def test_stale_email_merge_can_start_a_fresh_code_flow_inline() -> None:
    page = render_account_merge_page(
        None,
        intent_id=uuid4(),
        csrf_token="safe-csrf",
        provider_id="email_link",
        requires_restart=True,
    )

    assert 'action="/settings/account/email-link/start"' in page
    assert 'name="email" type="email"' in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    for stale_field in ("state", "nonce", "proof", "preview_fingerprint", "idempotency_key"):
        assert f'name="{stale_field}"' not in page


def test_mobile_browser_shell_keeps_server_rendered_navigation_without_javascript() -> None:
    page = render_settings_page(category="account")

    assert '<noscript><nav class="cabinet-mobile-noscript-nav"' in page
    assert 'aria-label="Навигация кабинета без JavaScript"' in page
    assert 'href="/meetings"' in page
    assert 'href="/settings"' in page
    assert 'href="/settings/account"' in page


@pytest.mark.parametrize(
    ("code", "browser_next", "desktop_next"),
    (
        ("billing_conflict", "/billing", "/billing"),
        (
            "calendar_ownership_conflict",
            "/settings/integrations/calendar",
            "/desktop/settings/integrations/calendar",
        ),
        (
            "deletion_state_conflict",
            "/settings/account",
            "/desktop/settings/account",
        ),
        ("settings_conflict", "/settings/summaries", "/desktop/settings/summaries"),
        ("upload_in_progress", "/meetings", "/desktop/meetings"),
        ("export_in_progress", "/meetings", "/desktop/meetings"),
        ("fair_use_conflict", "/account/fair-use", "/desktop/account/fair-use"),
    ),
)
def test_self_service_blockers_have_real_browser_and_desktop_actions(
    code: str,
    browser_next: str,
    desktop_next: str,
) -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")

    browser = account_merge_routes.account_merge_blockers(
        (code,), intent_id=intent_id, embedded=False, support_email=None
    )
    desktop = account_merge_routes.account_merge_blockers(
        (code,), intent_id=intent_id, embedded=True, support_email=None
    )

    assert browser[0].action_label == "Войти во второй профиль"
    assert browser[0].action_href == "/logout"
    assert browser[0].action_next == f"/login?next={browser_next.replace('/', '%2F')}&error=account_linking_other_profile_required"
    assert desktop[0].action_label == "Войти во второй профиль"
    assert desktop[0].action_href == "/desktop/meetings"
    assert desktop[0].action_next == f"/login?next={desktop_next.replace('/', '%2F')}&error=account_linking_other_profile_required"
    assert "вернитесь в основной профиль" in browser[0].detail


@pytest.mark.parametrize(
    "code",
    (
        "workspace_role_conflict",
        "workspace_ownership_conflict",
        "meeting_owner_conflict",
        "referral_conflict",
    ),
)
def test_non_self_service_blockers_use_configured_support_with_metadata_only_reference(
    code: str,
) -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")

    blockers = account_merge_routes.account_merge_blockers(
        (code,),
        intent_id=intent_id,
        embedded=False,
        support_email="support@example.test",
    )

    assert len(blockers) == 1
    blocker = blockers[0]
    assert blocker.action_label == "Получить помощь"
    assert blocker.action_href.startswith("mailto:support@example.test?")
    assert blocker.support_reference.startswith("AM-")
    assert str(intent_id) not in blocker.action_href
    assert str(intent_id) not in blocker.support_reference
    assert "заявка создана" not in blocker.detail.lower()


def test_blocker_without_configured_support_is_truthful_and_keeps_safe_return() -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")

    blocker = account_merge_routes.account_merge_blockers(
        ("meeting_owner_conflict",),
        intent_id=intent_id,
        embedded=True,
        support_email=None,
    )[0]

    assert blocker.action_label == "Вернуться в настройки"
    assert blocker.action_href == "/desktop/settings/account"
    assert "Поддержка на этом сервере не настроена" in blocker.detail
    assert "заявка" not in blocker.detail.lower()


def test_source_profile_recovery_is_a_csrf_protected_logout_not_a_wrong_profile_link() -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")
    preview = build_merge_preview(
        survivor_user_id=UUID("00000000-0000-0000-0000-000000000002"),
        source_user_id=UUID("00000000-0000-0000-0000-000000000003"),
        billing_conflict=True,
    )
    blockers = account_merge_routes.account_merge_blockers(
        preview.blocker_codes,
        intent_id=intent_id,
        embedded=False,
        support_email=None,
    )

    page = render_account_merge_page(
        preview,
        intent_id=intent_id,
        csrf_token="safe-csrf",
        blockers=blockers,
    )

    assert '<form action="/logout" method="post">' in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    assert 'name="next" value="/login?next=%2Fbilling&amp;error=account_linking_other_profile_required"' in page
    assert 'href="/billing"' not in page


@pytest.mark.parametrize(
    "value",
    (
        "Display <support@example.test>",
        "support@example.test\r\nBcc:evil@example.test",
        "not-email",
    ),
)
def test_support_email_rejects_display_names_headers_and_invalid_values(value: str) -> None:
    assert account_merge_routes._configured_support_email(value) is None
