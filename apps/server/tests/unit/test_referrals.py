import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.billing.referral_binding import referral_attribution_exists_for_lineage
from twobrain_rec_server.billing.referral_rewards import mature_credit, payment_source_ref
from twobrain_rec_server.billing.referrals import (
    ReferralRiskSignals,
    classify_referral_risk,
    create_referral_token,
    first_payment_reward,
    referral_token_hash,
    validate_referral_token,
)
from twobrain_rec_server.cabinet.web_routes import billing as billing_routes
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _bind_referral_attribution
from twobrain_rec_server.cabinet.web_routes.billing import _referral_attribution_for_lineage
from twobrain_rec_server.db.tenant_context import AuthReferralUserLookupContext


def test_referral_reward_is_discount_plus_bounded_mature_credit() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    reward = first_payment_reward(paid_at=paid_at, cycle="month")
    assert reward.invitee_discount_percent == 10
    credit = mature_credit(reward=reward, source_ref="payment-1", granted_rolling_days=0, now=paid_at + timedelta(days=15))
    assert credit is not None and credit.days == 7


def test_referral_token_is_opaque_and_stable_for_inviter() -> None:
    user_id = UUID("11111111-1111-1111-1111-111111111111")
    first = create_referral_token(user_id=user_id, secret="a" * 32)
    assert first == create_referral_token(user_id=user_id, secret="a" * 32)
    assert first.startswith("r1_") and len(first) == 67
    assert referral_token_hash(first) != referral_token_hash(create_referral_token(user_id=user_id, secret="b" * 32))


def test_referral_token_is_scoped_when_workspace_is_known() -> None:
    user_id = UUID("11111111-1111-1111-1111-111111111111")
    first_workspace = UUID("33333333-3333-3333-3333-333333333333")
    second_workspace = UUID("66666666-6666-6666-6666-666666666666")
    first = create_referral_token(user_id=user_id, workspace_id=first_workspace, secret="a" * 32)
    second = create_referral_token(user_id=user_id, workspace_id=second_workspace, secret="a" * 32)
    assert first != second


def test_first_touch_binding_supports_multiple_invitees() -> None:
    class FakeDb:
        def __init__(self, link) -> None:
            self.link = link
            self.calls = 0
            self.info = {}
            self.added = []

        def get_bind(self):
            class Bind:
                dialect = type("Dialect", (), {"name": "sqli" + "te"})()
            return Bind()

        async def scalar(self, _query):
            self.calls += 1
            if self.calls % 3 == 1:
                return self.link
            return None

        async def get(self, _model, workspace_id):
            return type(
                "Workspace",
                (),
                {
                    "id": workspace_id,
                    "kind": "personal",
                    "owner_user_id": self.link.inviter_user_id,
                },
            )()

        def begin_nested(self):
            class Nested:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_args):
                    return None

            return Nested()

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    inviter = UUID("11111111-1111-1111-1111-111111111111")
    token = create_referral_token(user_id=inviter, secret="a" * 32)
    link = type("Link", (), {
        "id": UUID("44444444-4444-4444-4444-444444444444"),
        "inviter_user_id": inviter,
        "workspace_id": UUID("33333333-3333-3333-3333-333333333333"),
        "token_hash": referral_token_hash(token),
        "campaign_version": "referral-v1",
        "expires_at": None,
        "state": "active",
    })()
    db = FakeDb(link)
    invitees = (
        UUID("22222222-2222-2222-2222-222222222222"),
        UUID("55555555-5555-5555-5555-555555555555"),
    )
    for invitee in invitees:
        assert asyncio.run(
            _bind_referral_attribution(
                db,
                enabled=True,
                workspace_id=link.workspace_id,
                user_id=invitee,
                token=token,
                now=datetime(2026, 8, 7, tzinfo=UTC),
            )
        ) is True
    assert len(db.added) == 2
    assert {row.invitee_user_id for row in db.added} == set(invitees)


def test_first_touch_binding_rejects_expired_link() -> None:
    class FakeDb:
        info = {}

        def get_bind(self):
            class Bind:
                dialect = type("Dialect", (), {"name": "sqli" + "te"})()
            return Bind()

        async def scalar(self, _query):
            return type("Link", (), {
                "inviter_user_id": UUID("11111111-1111-1111-1111-111111111111"),
                "expires_at": datetime(2026, 7, 1, tzinfo=UTC),
            })()

    token = create_referral_token(user_id=UUID("11111111-1111-1111-1111-111111111111"), secret="a" * 32)
    assert asyncio.run(
        _bind_referral_attribution(
            FakeDb(),
            enabled=True,
            workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
            user_id=UUID("22222222-2222-2222-2222-222222222222"),
            token=token,
            now=datetime(2026, 8, 7, tzinfo=UTC),
        )
    ) is False


def test_referral_binding_is_disabled_with_checkout() -> None:
    class FailIfUsedDb:
        info = {}

        async def scalar(self, _query):
            raise AssertionError("disabled referral binding must not query the database")

    assert asyncio.run(
        _bind_referral_attribution(
            FailIfUsedDb(),
            enabled=False,
            workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
            user_id=UUID("22222222-2222-2222-2222-222222222222"),
            token="r1_" + "a" * 64,
            now=datetime(2026, 8, 7, tzinfo=UTC),
        )
    ) is False


def test_public_referral_binding_rechecks_inviter_workspace_is_personal() -> None:
    inviter = UUID("11111111-1111-1111-1111-111111111111")
    token = create_referral_token(user_id=inviter, secret="a" * 32)
    link = type(
        "Link",
        (),
        {
            "id": UUID("44444444-4444-4444-4444-444444444444"),
            "inviter_user_id": inviter,
            "workspace_id": UUID("33333333-3333-3333-3333-333333333333"),
            "token_hash": referral_token_hash(token),
            "campaign_version": "referral-v1",
            "expires_at": None,
            "state": "active",
        },
    )()

    class FakeDb:
        info = {}

        def get_bind(self):
            return type("Bind", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()

        async def scalar(self, statement):
            return link if "referral_links" in str(statement) else None

        async def get(self, _model, workspace_id):
            return type(
                "Workspace",
                (),
                {
                    "id": workspace_id,
                    "kind": "linked",
                    "owner_user_id": inviter,
                },
            )()

        def begin_nested(self):
            class Nested:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_args):
                    return None

            return Nested()

        def add(self, _value):
            return None

        async def flush(self):
            return None

    assert asyncio.run(
        _bind_referral_attribution(
            FakeDb(),
            enabled=True,
            workspace_id=link.workspace_id,
            user_id=UUID("22222222-2222-2222-2222-222222222222"),
            token=token,
            now=datetime(2026, 8, 7, tzinfo=UTC),
        )
    ) is False


def test_referral_attribution_usage_follows_recursive_merged_user_lineage() -> None:
    class FakeDb:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

        async def scalar(self, statement):
            compiled = str(statement)
            assert "WITH RECURSIVE" in compiled
            assert "merged_into_user_id" in compiled
            return UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    assert asyncio.run(
        referral_attribution_exists_for_lineage(
            FakeDb(), user_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        )
    ) is True


@pytest.mark.parametrize("attribution_owner", ("current", "merged_source"))
def test_checkout_retry_finds_attributed_referral_in_user_lineage(
    monkeypatch: pytest.MonkeyPatch,
    attribution_owner: str,
) -> None:
    survivor_id = UUID("11111111-1111-4111-8111-111111111111")
    source_id = UUID("22222222-2222-4222-8222-222222222222")
    workspace_id = UUID("33333333-3333-4333-8333-333333333333")
    row = type(
        "Attribution",
        (),
        {
            "id": UUID("44444444-4444-4444-8444-444444444444"),
            "invitee_user_id": source_id,
            "inviter_user_id": UUID("55555555-5555-4555-8555-555555555555"),
            "state": "attributed",
        },
    )()
    current_lookup_user_id: UUID | None = None
    visited: list[UUID] = []

    async def apply_context(_db, context) -> None:
        nonlocal current_lookup_user_id
        assert isinstance(context, AuthReferralUserLookupContext)
        current_lookup_user_id = context.user_id
        visited.append(context.user_id)

    class FakeDb:
        async def scalar(self, statement):
            assert ["bound", "registered", "attributed"] in statement.compile().params.values()
            expected_user_id = survivor_id if attribution_owner == "current" else source_id
            return row if current_lookup_user_id == expected_user_id else None

    monkeypatch.setattr(billing_routes, "apply_tenant_context", apply_context)

    found = asyncio.run(
        _referral_attribution_for_lineage(
            FakeDb(),
            workspace_id=workspace_id,
            lineage_user_ids=(survivor_id, source_id),
        )
    )

    assert found is row
    assert visited == (
        [survivor_id] if attribution_owner == "current" else [survivor_id, source_id]
    )


def test_annual_credit_waits_for_maturity_and_cap_is_bounded() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    reward = first_payment_reward(paid_at=paid_at, cycle="year")
    assert mature_credit(reward=reward, source_ref="payment-1", granted_rolling_days=179, now=paid_at + timedelta(days=15)).days == 1
    assert mature_credit(reward=reward, source_ref="payment-2", granted_rolling_days=180, now=paid_at + timedelta(days=15)) is None
    assert mature_credit(reward=reward, source_ref="payment-3", granted_rolling_days=0, now=paid_at + timedelta(days=13)) is None
    with pytest.raises(ValueError):
        payment_source_ref("provider id with spaces")


def test_referral_risk_is_a_review_signal_and_token_shape_is_strict() -> None:
    token = create_referral_token(user_id=UUID("11111111-1111-1111-1111-111111111111"), secret="a" * 32)
    assert validate_referral_token(token) == token
    assert classify_referral_risk(ReferralRiskSignals(same_device=True)) == "none"
    assert classify_referral_risk(ReferralRiskSignals(same_device=True, same_payment_profile=True)) == "review"
    with pytest.raises(ValueError):
        validate_referral_token(token[:-1])
    with pytest.raises(ValueError):
        validate_referral_token(token.replace("r1_", "r1-", 1))


def test_referral_links_use_configured_public_origin_not_request_host() -> None:
    source = (Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/web_routes/referrals.py").read_text(encoding="utf-8")
    assert "request.base_url" not in source
    assert "public_base_url" in source


def test_referral_routes_keep_contract_alias_and_gate_unissued_link() -> None:
    route_source = (Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/web_routes/referrals.py").read_text(encoding="utf-8")
    template_source = (Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/referrals_content.html").read_text(encoding="utf-8")
    assert '@router.get("/r/{token}"' in route_source
    assert 'f"{str(public_base_url).rstrip(\'/\')}/r/{token}"' in route_source
    assert "referral_issue_result" in template_source
    assert "{% if referral_issued|default(False) %}" in template_source
    assert "REFERRAL_TOKEN_MAX_AGE_DAYS" in route_source
    assert '"expires_at": expires_at' in route_source
    assert "PublicDbDependency" in route_source
    assert "ReferralLandingLookupContext" in route_source
    assert "referral_expires_at_label" in template_source
    assert "Поделиться" in template_source
    assert "Обратиться в поддержку" in template_source
    assert "referral_history" in route_source
    assert "existing_valid" in route_source
    assert "response.delete_cookie(\"graf_referral_token\")" in route_source
    assert "expires_at > landing_now" in route_source
    assert "if not request.app.state.settings.billing_checkout_enabled" in route_source
    assert "referral_enabled and secret_path" in route_source
    assert "Одна ссылка может использоваться несколькими приглашёнными" in template_source
    landing_template = (Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/templates/cabinet/auth/referral_landing.html").read_text(encoding="utf-8")
    assert "Создать аккаунт" in landing_template
    assert "Продолжить без бонуса" in landing_template
    assert "referral/skip" in route_source
