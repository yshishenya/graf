import ast
import inspect
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from starlette.requests import Request

from tests.unit.test_cabinet_web_shell import _deletion_report
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.view_models import AccountProfileView
from twobrain_rec_server.cabinet.web_routes import (
    billing,
    deletion,
    desktop,
    fair_use,
    referrals,
    settings,
)
from twobrain_rec_server.db.models import TrialActivation, WorkspaceSubscription


@pytest.mark.asyncio
@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("fragment", [False, True])
async def test_deletion_full_page_loads_profile_but_fragment_does_not(
    monkeypatch, embedded, fragment
):
    module = desktop if embedded else deletion
    handler = (
        module.embedded_meeting_deletion_report_page
        if embedded
        else module.meeting_deletion_report_page
    )
    monkeypatch.setattr(
        module,
        "_authorized_lifecycle_meeting",
        AsyncMock(return_value=SimpleNamespace(title="Synthetic")),
    )
    monkeypatch.setattr(
        module, "deletion_report_response", AsyncMock(return_value=_deletion_report())
    )
    monkeypatch.setattr(module, "build_request_browser_provider_context", lambda *_a, **_k: {})
    user = SimpleNamespace(
        display_name="Synthetic Profile", locale="en-US", timezone="UTC", theme="dark"
    )
    db = SimpleNamespace(get=AsyncMock(return_value=user), scalars=AsyncMock(return_value=[]))
    request = Request({"type": "http", "headers": [(b"hx-request", b"true")] if fragment else []})
    response = await handler(
        request,
        UUID(int=4),
        db=db,
        principal=SimpleNamespace(user_id=UUID(int=2), session_id=None, auth_via_session=False),
        tenant_scope=SimpleNamespace(user_id=UUID(int=2), workspace_id=UUID(int=3)),
    )
    assert response.status_code == 200
    if fragment:
        db.get.assert_not_awaited()
    else:
        assert 'data-theme="dark"' in response.body.decode()
        assert "Synthetic Profile" in response.body.decode()
        db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_preferences_reject_other_organization(monkeypatch):
    user = SimpleNamespace(organization_id=UUID(int=1), theme="dark")
    db = SimpleNamespace(get=AsyncMock(return_value=user), commit=AsyncMock())
    audit = AsyncMock()
    monkeypatch.setattr(settings, "write_auth_audit_event", audit)
    with pytest.raises(ProblemDetail) as error:
        await settings._save_account_preferences(
            db,
            principal=SimpleNamespace(user_id=UUID(int=2)),
            tenant_scope=SimpleNamespace(organization_id=UUID(int=9), workspace_id=UUID(int=3)),
            request=SimpleNamespace(form=AsyncMock(return_value={"theme": "light"})),
        )
    assert error.value.status == 404 and user.theme == "dark"
    db.commit.assert_not_awaited()
    audit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("active_trial", [False, True])
async def test_billing_routes_render_real_profile_and_persisted_trial_dates(
    monkeypatch, active_trial
):
    now = datetime.now(UTC)
    trial = SimpleNamespace(starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=6))
    subscription = SimpleNamespace(
        plan_code="trial",
        state="trial",
        paid_through=None,
        trial_ends_at=trial.ends_at,
        capacity_bytes=500_000_000,
        billing_owner_id=UUID(int=2),
        cycle=None,
        renewal_resolution=None,
    )
    user = SimpleNamespace(
        display_name="Synthetic Profile", locale="en-US", timezone="UTC", theme="dark"
    )

    async def scalar(statement):
        entity = statement.column_descriptions[0].get("entity")
        if entity is WorkspaceSubscription:
            return subscription if active_trial else None
        if entity is TrialActivation:
            assert str(statement).count("trial_activations.workspace_id") >= 1
            return trial
        return None

    db = SimpleNamespace(
        scalar=scalar, scalars=AsyncMock(return_value=[]), get=AsyncMock(return_value=user)
    )
    monkeypatch.setattr(billing, "_billing_role", AsyncMock(return_value="owner"))
    monkeypatch.setattr(billing, "_approved_personal_catalog", AsyncMock(return_value={}))
    monkeypatch.setattr(
        billing,
        "project_active_playback_storage",
        AsyncMock(return_value=SimpleNamespace(used_bytes=1_500_000)),
    )
    monkeypatch.setattr(billing, "build_request_browser_provider_context", lambda *_a, **_k: {})
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/billing",
            "headers": [],
            "query_string": b"",
            "app": SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(
                        billing_checkout_enabled=False, billing_support_email=None
                    )
                )
            ),
        }
    )
    principal = SimpleNamespace(user_id=UUID(int=2), session_id=None, auth_via_session=False)
    scope = SimpleNamespace(user_id=principal.user_id, workspace_id=UUID(int=3), device_id=None)
    route = billing.billing_overview_page if active_trial else billing.billing_history_page
    response = await route(request, tenant_scope=scope, principal=principal, db=db)
    html = response.body.decode()
    assert response.status_code == 200
    assert "Synthetic Profile" in html and 'data-theme="dark"' in html
    assert 'name="locale"' not in html and 'name="timezone"' not in html
    if active_trial:
        assert "Пробный период: с " in html
        assert billing._billing_datetime_label(trial.starts_at, seconds=True) in html
        assert billing._billing_datetime_label(trial.ends_at, seconds=True) in html
        assert "1,5 MB" in html
    else:
        assert "Контакт поддержки пока не настроен" in html


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "form",
    [{"theme": "light"}, {"locale": "ru-RU", "timezone": "Europe/Moscow", "theme": "system"}],
)
async def test_preferences_preserve_omitted_fields(monkeypatch, form):
    user = SimpleNamespace(
        organization_id=UUID(int=1), locale="en-US", timezone="UTC", theme="dark"
    )
    original = vars(user).copy()
    db = SimpleNamespace(get=AsyncMock(return_value=user), commit=AsyncMock())
    audit = AsyncMock()
    monkeypatch.setattr(settings, "write_auth_audit_event", audit)
    await settings._save_account_preferences(
        db,
        principal=SimpleNamespace(user_id=UUID(int=2)),
        tenant_scope=SimpleNamespace(
            organization_id=user.organization_id, workspace_id=UUID(int=3)
        ),
        request=SimpleNamespace(form=AsyncMock(return_value=form)),
    )
    assert vars(user) == original | form
    assert audit.await_args.kwargs["metadata"]["fields"] == list(form)
    assert db.get.await_args.kwargs["with_for_update"] is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "form",
    [
        {},
        {"locale": "ru-RU", "timezone": "invalid", "theme": "light"},
        {"theme": ""},
        {"theme": "invalid"},
    ],
)
async def test_preferences_reject_entire_invalid_update(monkeypatch, form):
    user = SimpleNamespace(
        organization_id=UUID(int=1), locale="en-US", timezone="UTC", theme="dark"
    )
    original = vars(user).copy()
    db = SimpleNamespace(get=AsyncMock(return_value=user), commit=AsyncMock())
    audit = AsyncMock()
    monkeypatch.setattr(settings, "write_auth_audit_event", audit)
    with pytest.raises(ProblemDetail) as error:
        await settings._save_account_preferences(
            db,
            principal=SimpleNamespace(user_id=UUID(int=2)),
            tenant_scope=SimpleNamespace(
                organization_id=user.organization_id, workspace_id=UUID(int=3)
            ),
            request=SimpleNamespace(form=AsyncMock(return_value=form)),
        )
    assert error.value.status == 422
    assert vars(user) == original
    db.commit.assert_not_awaited()
    audit.assert_not_awaited()


@pytest.mark.parametrize("embedded", [False, True])
def test_profile_menu_submits_only_theme_and_enables_existing_autosave(embedded):
    page = _page_shell(
        "Synthetic",
        "",
        embedded=embedded,
        profile=AccountProfileView("Synthetic", "local@graf.test", "en-US", "UTC", "dark"),
    )
    form = re.search(r"<form[^>]*data-account-preferences.*?</form>", page, re.S).group()
    assert 'data-account-preferences-auto-save="true"' in form
    assert 'name="locale"' not in form and 'name="timezone"' not in form
    assert 'value="dark" checked' in form


def test_all_billing_and_deletion_shell_callers_supply_profile():
    for module, target in (
        (billing, "_page_shell"),
        (fair_use, "_page_shell"),
        (referrals, "_page_shell"),
        (deletion, "render_deletion_report_page"),
        (desktop, "render_deletion_report_page"),
    ):
        calls = [
            node
            for node in ast.walk(ast.parse(inspect.getsource(module)))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == target
        ]
        assert calls
        for call in calls:
            assert "profile" in {kw.arg for kw in call.keywords}, (module.__name__, call.lineno)


def test_shell_without_profile_does_not_offer_unsourced_theme_autosave():
    page = _page_shell("Synthetic shared view", "", embedded=False)
    assert "data-account-preferences-auto-save" not in page


@pytest.mark.parametrize("page_name", ["billing_overview_content", "billing_plans_content"])
def test_trial_discloses_terms_before_separate_confirmation(page_name):
    page = render_template(
        f"cabinet/pages/{page_name}.html",
        plan=plan_descriptor("free"),
        plan_code="free",
        plans=[
            SimpleNamespace(
                code="trial",
                label="Пробный",
                is_current=False,
                processing_mode="unlimited",
                storage_label="500 MB",
                annual_saving_label=None,
            )
        ],
        billing_owner=True,
        billing_enabled=False,
        trial_state="eligible",
        csrf_token="synthetic-csrf",
        processing_used_label="0 минут",
        free_processing_limit_label="300 минут",
        storage_used=0,
        storage_capacity=250_000_000,
        storage_threshold="normal",
        processing_used=0,
        processing_threshold="normal",
        latest_invoice=None,
        payment_method_label=None,
        next_charge_label=None,
        support_email=None,
        trial_preview_starts_at_label="06.09.2026, 12:00:00 (МСК)",
        trial_preview_ends_at_label="13.09.2026, 12:00:00 (МСК)",
    )
    disclosure = re.search(r"<details[^>]*data-trial-confirmation.*?</details>", page, re.S)
    assert disclosure
    html = disclosure.group()
    for text in (
        "Карта не нужна",
        "Автосписания не будет",
        "Free",
        "06.09.2026",
        "13.09.2026",
        "Подтвердить запуск на 7 дней",
        "предварительный",
    ):
        assert text in html
    assert "<summary" in html and 'type="submit"' in html
    assert 'name="confirmation" value="start_trial"' in html


@pytest.mark.parametrize("email", [None, "support@graf.test"])
def test_empty_history_has_real_help_or_honest_unavailable(email):
    page = render_template(
        "cabinet/pages/billing_history_content.html", invoices=[], support_email=email
    )
    assert 'href="#billing-help"' in page and 'id="billing-help"' in page
    if email:
        assert f'href="mailto:{email}"' in page
    else:
        assert "Контакт поддержки пока не настроен" in page
        assert 'href="/billing"' in page
        assert "Напишите в поддержку" not in page


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0 байт"),
        (999, "999 байт"),
        (1000, "1 KB"),
        (1_500_000, "1,5 MB"),
        (123_456_789, "123,46 MB"),
        (250_000_000, "250 MB"),
        (999_999_999, "1 GB"),
        (1_500_000_000_000, "1,5 TB"),
    ],
)
def test_capacity_labels_are_readable_without_changing_exact_bytes(value, expected):
    assert billing._capacity_label(value) == expected
    assert billing._exact_bytes_label(value).replace(" ", "") == str(value)
