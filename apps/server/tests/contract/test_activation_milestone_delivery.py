"""Disposable SQL decisions and fake transports; never contact a provider."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import ProductActivationMilestone, UserIdentity
from twobrain_rec_server.db.tenant_context import apply_tenant_context
from twobrain_rec_server.product_analytics import router
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.milestones import admit_account_milestone
from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse

REQUIRE_DELIVERY_DATABASE = router._require_delivery_database
TRANSFER_DECISION = router.YandexOfflineConversionExporter.transfer_decision


def run(url, scenario):
    async def execute():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            await scenario(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()
    asyncio.run(execute())


async def seed(sessions, *, count=1, providers=("posthog", "yandex")):
    rows = []
    for index in range(count):
        account = USER_ID if index == 0 else uuid4()
        async with sessions() as db:
            if index:
                db.add(UserIdentity(id=account, organization_id=ORG_ID,
                                    external_subject=f"synthetic-delivery-{index}"))
                await db.flush()
            event = build_activation_event(
                "desktop_account_connected",
                stable_pseudonymous_user_id=build_safe_identity(
                    user_source_id=str(account)
                ).stable_pseudonymous_user_id,
                properties={"yandex_user_id_present": True},
            )
            row, _ = await admit_account_milestone(
                db, event, account_id=account, source_kind="server",
                requested_providers=providers,
            )
            await db.commit()
            rows.append(row)
    return rows


@pytest.fixture
def delivery(monkeypatch, tmp_path):
    # Only isolated operating/role receipts are replaced. Production has no
    # bypass flag; a separate test exercises actual login identities.
    monkeypatch.setattr(router, "activation_milestone_write_blockers", lambda _: ())
    monkeypatch.setattr(router, "resolve_provider_delivery_gate",
                        lambda *a, **kw: SimpleNamespace(allowed=True, blockers=()))
    async def role(db):
        pass
    monkeypatch.setattr(router, "_require_delivery_database", role)
    for name in ("posthog_client", "yandex_offline"):
        monkeypatch.setattr(
            f"twobrain_rec_server.product_analytics.{name}.resolve_provider_delivery_gate",
            lambda *a, **kw: SimpleNamespace(allowed=True, blockers=()),
        )
    monkeypatch.setattr(router.YandexOfflineConversionExporter, "transfer_decision",
                        lambda *a, **kw: SimpleNamespace(allowed=True, status="allowed"))
    key = tmp_path / "synthetic-key"
    key.write_text("synthetic-provider-key")
    settings = Settings(
        product_analytics_enabled=True, product_analytics_validation_mode="live_safe",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key,
        product_analytics_yandex_offline_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_yandex_oauth_token_file=key,
        product_analytics_legal_approved=True, product_analytics_privacy_approved=True,
        product_analytics_security_approved=True, product_analytics_qa_approved=True,
        product_analytics_disclosure_approved=True, product_analytics_dashboard_ready=True,
        product_analytics_provider_smoke_approved=True, product_analytics_rollback_approved=True,
        product_analytics_live_provider_delivery_approved=True,
    )
    calls = []
    async def transport(url, headers, body, timeout):
        assert timeout <= 5
        calls.append((url, body))
        return ProviderTransportResponse(200)
    monkeypatch.setattr(router, "_milestone_http_transport", transport)
    return settings, calls, key


def test_delivery_keeps_one_decision_and_never_confirms_from_2xx(
    postgres_seeded_database_url, delivery,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions)
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 1
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 0
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == row.yandex_state == "submitted"
            assert row.posthog_confirmation_ref is row.yandex_confirmation_ref is None
            assert row.safe_payload == original.safe_payload
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 1
        assert len(calls) == 2
        assert json.loads(calls[0][1])["uuid"] == str(original.event_id)
        assert ("graf_yandex_dedupe_" + original.event_id.hex).encode() in calls[1][1]
        assert str(USER_ID).encode() not in b"".join(body for _, body in calls)
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("failure", ["timeout", "network", 429, 500, 400])
def test_transport_failure_is_ambiguous_and_other_provider_is_independent(
    postgres_seeded_database_url, delivery, monkeypatch, failure,
):
    settings, calls, _ = delivery
    async def transport(url, headers, body, timeout):
        calls.append((url, body))
        if "analytics.example.test" in url:
            if failure == "timeout":
                raise TimeoutError("synthetic")
            if failure == "network":
                raise OSError("synthetic")
            return ProviderTransportResponse(failure)
        return ProviderTransportResponse(200)
    monkeypatch.setattr(router, "_milestone_http_transport", transport)
    async def scenario(sessions):
        (original,) = await seed(sessions)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == "ambiguous" and row.yandex_state == "submitted"
        assert len(calls) == 2
    run(postgres_seeded_database_url, scenario)


def test_proven_pre_send_failure_retries_same_identity_without_second_count(
    postgres_seeded_database_url, delivery,
):
    settings, calls, key = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        key.unlink()
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert not calls
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == "pre_send_retry"
        key.write_text("synthetic-provider-key")
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(calls) == 1 and json.loads(calls[0][1])["uuid"] == str(original.event_id)
    run(postgres_seeded_database_url, scenario)


def test_two_workers_share_one_provider_slot_and_release_sql_locks_before_network(
    postgres_seeded_database_url, delivery, monkeypatch,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        rows = await seed(sessions, count=2, providers=("posthog",))
        entered, release = asyncio.Event(), asyncio.Event()
        async def transport(url, headers, body, timeout):
            calls.append((url, body))
            if len(calls) == 1:
                entered.set()
                await release.wait()
            return ProviderTransportResponse(200)
        monkeypatch.setattr(router, "_milestone_http_transport", transport)
        first = asyncio.create_task(router.reconcile_activation_milestones_once(sessions, settings=settings))
        await asyncio.wait_for(entered.wait(), 2)
        # A second connection can update the claimed row while HTTP is waiting:
        # there is no retained row/transaction/advisory lock during transport.
        async with sessions() as db:
            await db.execute(update(ProductActivationMilestone).where(
                ProductActivationMilestone.id == rows[0].id
            ).values(updated_at=datetime.now(UTC)))
            await asyncio.wait_for(db.commit(), 1)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(calls) == 1
        release.set()
        await first
        assert len(calls) == 2
    run(postgres_seeded_database_url, scenario)


def test_scan_bound_and_no_hidden_backfill(postgres_seeded_database_url, delivery):
    settings, calls, _ = delivery
    async def scenario(sessions):
        await seed(sessions, count=23, providers=("posthog",))
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 20
        assert len(calls) == 20
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 3
        assert len(calls) == 23
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone).where(
                ProductActivationMilestone.yandex_state != "not_requested"
            )) == 0
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("blocked_provider", ["posthog", "yandex"])
@pytest.mark.parametrize("reason", ["basis_unavailable", "provider_disabled", "technical_pre_send"])
def test_blocked_old_batch_rotates_and_other_provider_delivers_newer_milestones(
    postgres_seeded_database_url, delivery, monkeypatch, tmp_path, blocked_provider, reason,
):
    settings, calls, _ = delivery
    blocked = {"active": True}
    missing_key = tmp_path / "temporarily-unavailable-key"
    if reason == "technical_pre_send":
        field = ("product_analytics_posthog_project_key_file" if blocked_provider == "posthog"
                 else "product_analytics_yandex_oauth_token_file")
        setattr(settings, field, missing_key)
    else:
        def gate(*args, provider, **kwargs):
            refused = blocked["active"] and provider == blocked_provider
            blocker = f"{provider}_disabled" if reason == "provider_disabled" else "basis_unknown"
            return SimpleNamespace(allowed=not refused, blockers=(blocker,) if refused else ())
        monkeypatch.setattr(router, "resolve_provider_delivery_gate", gate)

    def provider_calls(provider):
        return [body for url, body in calls
                if ("analytics.example.test" in url) == (provider == "posthog")]

    async def scenario(sessions):
        originals = await seed(sessions, count=23)
        healthy = "yandex" if blocked_provider == "posthog" else "posthog"
        for _ in range(2):
            assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 20
        assert len(provider_calls(healthy)) == 23
        assert not provider_calls(blocked_provider)
        async with sessions() as db:
            for original in originals:
                row = await db.get(ProductActivationMilestone, original.id)
                assert getattr(row, f"{healthy}_state") == "submitted"
                assert getattr(row, f"{blocked_provider}_state") == (
                    "pre_send_retry" if reason == "technical_pre_send" else "pending"
                )
        blocked["active"] = False
        if reason == "technical_pre_send":
            missing_key.write_text("synthetic-provider-key")
        for _ in range(2):
            await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(provider_calls("posthog")) == len(provider_calls("yandex")) == 23
        async with sessions() as db:
            for original in originals:
                row = await db.get(ProductActivationMilestone, original.id)
                assert row.posthog_state == row.yandex_state == "submitted"
                assert (row.event_id, row.accepted_at, row.safe_payload) == (
                    original.event_id, original.accepted_at, original.safe_payload,
                )
                assert sum(str(row.event_id).encode() in body for body in provider_calls("posthog")) == 1
                assert sum(row.event_id.hex.encode() in body for body in provider_calls("yandex")) == 1
    run(postgres_seeded_database_url, scenario)


def test_delete_before_transport_and_late_finish_do_not_recreate_decision(
    postgres_seeded_database_url, delivery, monkeypatch,
):
    settings, calls, _ = delivery
    original_claim = router.claim_milestone_delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        async def claim(db, **kwargs):
            row = await original_claim(db, **kwargs)
            if row is not None:
                await db.execute(delete(ProductActivationMilestone).where(
                    ProductActivationMilestone.id == row.id
                ))
            return row
        monkeypatch.setattr(router, "claim_milestone_delivery", claim)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert not calls
        async with sessions() as db:
            assert await db.get(ProductActivationMilestone, original.id) is None
    run(postgres_seeded_database_url, scenario)


def test_stale_dispatch_is_quarantined_never_resent(postgres_seeded_database_url, delivery):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        async with sessions() as db:
            await db.execute(update(ProductActivationMilestone).where(
                ProductActivationMilestone.id == original.id
            ).values(posthog_state="dispatching", posthog_attempt_id=uuid4(),
                     posthog_attempted_at=datetime.now(UTC) - timedelta(minutes=2)))
            await db.commit()
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert not calls
        async with sessions() as db:
            assert (await db.get(ProductActivationMilestone, original.id)).posthog_state == "ambiguous"
    run(postgres_seeded_database_url, scenario)


def test_stale_claim_precedes_older_pending_rows_in_bounded_scan(postgres_seeded_database_url, delivery):
    settings, calls, _ = delivery
    async def scenario(sessions):
        rows = await seed(sessions, count=23, providers=("posthog",))
        stale = rows[-1]
        async with sessions() as db:
            await db.execute(update(ProductActivationMilestone).where(
                ProductActivationMilestone.id == stale.id
            ).values(posthog_state="dispatching", posthog_attempt_id=uuid4(),
                     posthog_attempted_at=datetime.now(UTC) - timedelta(minutes=2),
                     updated_at=datetime.now(UTC)))
            await db.commit()
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 20
        assert len(calls) == 19
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, stale.id)
            assert row.posthog_state == "ambiguous" and row.posthog_reason == "interrupted_dispatch"
        assert all(str(stale.event_id).encode() not in body for _, body in calls)
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("withdrawn", [True, False])
def test_fresh_basis_after_preparation_stops_transport(
    postgres_seeded_database_url, delivery, monkeypatch, withdrawn,
):
    from twobrain_rec_server.product_analytics import posthog_client
    settings, calls, _ = delivery
    state = {"changed": False}
    read = posthog_client.read_secret_file
    def after_preparation(*args, **kwargs):
        value = read(*args, **kwargs)
        state["changed"] = True
        return value
    monkeypatch.setattr(posthog_client, "read_secret_file", after_preparation)
    monkeypatch.setattr(router, "activation_milestone_write_blockers", lambda _: (
        ("legal_basis_withdrawn" if withdrawn else "basis_unavailable",)
        if state["changed"] else ()
    ))
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert state["changed"] and not calls
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == ("cancelled" if withdrawn else "pending")
            assert row.posthog_reason == ("purpose_withdrawn" if withdrawn else "basis_unavailable")
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("withdrawn", [False, True])
def test_provider_register_error_is_not_proof_of_withdrawal(delivery, monkeypatch, withdrawn):
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        BasisWithdrawal,
        BasisWithdrawalRegister,
    )
    settings, calls, _ = delivery
    register = BasisWithdrawalRegister(
        available=True, state_path="synthetic",
        file_errors=("legal_basis_record_invalid",),
        withdrawals=((BasisWithdrawal("provider_analytics", "2026-10-28", "synthetic"),)
                     if withdrawn else ()),
    )
    monkeypatch.setattr(router, "resolve_provider_delivery_gate", lambda *a, **kw: SimpleNamespace(
        allowed=False, blockers=("legal_basis_withdrawn",), withdrawals=register,
        level_key="provider_analytics",
    ))
    assert router._delivery_blocker(settings, "posthog", None) == (
        "purpose_withdrawn" if withdrawn else "basis_unavailable"
    )
    assert not calls


def test_exact_yandex_refusal_read_after_preparation_stops_durable_delivery(
    postgres_seeded_database_url, delivery, monkeypatch, tmp_path,
):
    from tests.unit.test_product_analytics_yandex_offline_provider import (
        BASIS_LINE,
        DISCLOSED_PAGES,
    )
    from twobrain_rec_server.product_analytics import yandex_offline
    from twobrain_rec_server.product_analytics.advertising_transfer import (
        OptionalMeasurementConsent,
    )

    settings, calls, _ = delivery
    register = tmp_path / "fresh-transfer-register"
    header = "advertising_transfer_state_version=1\n" + BASIS_LINE + "\n"
    register.write_text(header)
    monkeypatch.setenv("GRAF_PRODUCT_ANALYTICS_ADVERTISING_TRANSFER_STATE_FILE", str(register))
    monkeypatch.setattr(router.YandexOfflineConversionExporter, "transfer_decision", TRANSFER_DECISION)
    monkeypatch.setattr(yandex_offline, "packaged_visitor_disclosure_pages", lambda: DISCLOSED_PAGES)
    monkeypatch.setattr(yandex_offline, "optional_measurement_consent_from_event",
                        lambda _: OptionalMeasurementConsent(state="granted"))
    read = yandex_offline.read_secret_file
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("yandex",))
        reference = "graf_yandex_dedupe_" + original.event_id.hex
        def refuse(*args, **kwargs):
            result = read(*args, **kwargs)
            register.write_text(header + (
                "revocation_refusal recipient=yandex_metrica purpose=yandex_offline_conversions "
                f"transfer_ref={reference} refused_at=2026-10-28 reason=recipient_revocation_recorded\n"
            ))
            return result
        monkeypatch.setattr(yandex_offline, "read_secret_file", refuse)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert not calls
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.yandex_state == "cancelled" and row.yandex_reason == "purpose_withdrawn"
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("blocker,expected", [
    ("recipient_revocation_recorded", "cancelled"),
    ("retransfer_of_revoked_data_refused", "cancelled"),
    ("advertising_attribution_consent_revoked", "cancelled"),
    ("advertising_legal_basis_missing", "pending"),
    ("visitor_disclosure_outdated", "pending"),
])
def test_fresh_advertising_decision_changes_only_yandex(
    postgres_seeded_database_url, delivery, monkeypatch, blocker, expected,
):
    from twobrain_rec_server.product_analytics import yandex_offline
    from twobrain_rec_server.product_analytics.advertising_transfer import (
        AdvertisingTransferDecision,
    )
    settings, calls, _ = delivery
    revoked = False
    read = yandex_offline.read_secret_file
    def withdraw(*args, **kwargs):
        nonlocal revoked
        value = read(*args, **kwargs)
        revoked = True
        return value
    monkeypatch.setattr(yandex_offline, "read_secret_file", withdraw)
    monkeypatch.setattr(router.YandexOfflineConversionExporter, "transfer_decision",
                        lambda *a, **kw: AdvertisingTransferDecision(
                            purpose="yandex_offline_conversions", recipient="yandex_metrica",
                            allowed=not revoked, blockers=(blocker,) if revoked else (),
                        ))
    async def scenario(sessions):
        (original,) = await seed(sessions)
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(calls) == 1 and "analytics.example.test" in calls[0][0]
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == "submitted" and row.yandex_state == expected
    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("commit_number,after_commit", [(2, False), (2, True), (3, False)])
def test_unknown_claim_or_finish_commit_never_permits_resend(
    postgres_seeded_database_url, delivery, commit_number, after_commit,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        commits = 0
        class Fault(AsyncSession):
            async def commit(self):
                nonlocal commits
                commits += 1
                if commits == commit_number:
                    if after_commit:
                        await super().commit()
                    raise OSError("synthetic lost commit result")
                await super().commit()
        faulty = async_sessionmaker(sessions.kw["bind"], class_=Fault, expire_on_commit=False)
        with pytest.raises(OSError):
            await router.reconcile_activation_milestones_once(faulty, settings=settings)
        assert len(calls) == int(commit_number == 3)
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == ("pending" if commit_number == 2 and not after_commit else "dispatching")
            if row.posthog_state == "pending":
                return  # Proven rollback before claim, a future attempt is safe.
            await db.execute(update(ProductActivationMilestone).where(
                ProductActivationMilestone.id == original.id
            ).values(posthog_attempted_at=datetime.now(UTC) - timedelta(minutes=2)))
            await db.commit()
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(calls) == int(commit_number == 3)
        async with sessions() as db:
            assert (await db.get(ProductActivationMilestone, original.id)).posthog_state == "ambiguous"
    run(postgres_seeded_database_url, scenario)


def test_cancel_waits_for_real_transport_and_keeps_slot_closed(
    postgres_seeded_database_url, delivery, monkeypatch,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        entered, release = asyncio.Event(), asyncio.Event()
        async def transport(url, headers, body, timeout):
            calls.append((url, body))
            entered.set()
            await release.wait()
            return ProviderTransportResponse(200)
        monkeypatch.setattr(router, "_milestone_http_transport", transport)
        task = asyncio.create_task(router.reconcile_activation_milestones_once(sessions, settings=settings))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        assert len(calls) == 1
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with sessions() as db:
            assert (await db.get(ProductActivationMilestone, original.id)).posthog_state == "dispatching"
    run(postgres_seeded_database_url, scenario)


def test_hanging_transport_is_bounded_and_other_async_tasks_continue(
    postgres_seeded_database_url, delivery, monkeypatch,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        entered = asyncio.Event()
        stopped = asyncio.Event()
        async def transport(*args):
            calls.append(args)
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        monkeypatch.setattr(router, "_milestone_http_transport", transport)
        started = asyncio.get_running_loop().time()
        task = asyncio.create_task(router.reconcile_activation_milestones_once(sessions, settings=settings))
        await asyncio.wait_for(entered.wait(), 2)
        await asyncio.sleep(0.01)
        assert not task.done()  # The event loop remains available during HTTP.
        await asyncio.wait_for(task, 7)
        assert stopped.is_set() and 4.5 <= asyncio.get_running_loop().time() - started < 7
        await router.reconcile_activation_milestones_once(sessions, settings=settings)
        async with sessions() as db:
            assert (await db.get(ProductActivationMilestone, original.id)).posthog_state == "ambiguous"
        assert len(calls) == 1
    run(postgres_seeded_database_url, scenario)


def test_unverified_recovery_and_unsafe_snapshot_never_reach_transport(
    postgres_seeded_database_url, delivery, monkeypatch,
):
    settings, calls, _ = delivery
    async def scenario(sessions):
        (original,) = await seed(sessions, providers=("posthog",))
        monkeypatch.setattr(router, "activation_milestone_write_blockers",
                            lambda _: ("activation_recovery_unverified",))
        assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 0
        async with sessions() as db:
            row = await db.get(ProductActivationMilestone, original.id)
            assert row.posthog_state == "pending"
        # Simulate a corrupt caller snapshot without defeating the SQL
        # immutable-decision trigger, which independently prevents this update.
        row.safe_payload = {**row.safe_payload, "properties": {"transcript": "synthetic forbidden"}}
        monkeypatch.setattr(router, "activation_milestone_write_blockers", lambda _: ())
        assert await router._deliver_claim(sessions, settings, row, "posthog") == "payload_rejected"
        assert not calls
    run(postgres_seeded_database_url, scenario)


def test_actual_maintenance_login_sends_and_app_superuser_or_wrong_context_refuse(
    postgres_isolated_cluster_database_url, delivery, monkeypatch,
):
    from sqlalchemy.engine import make_url

    from tests.conftest import _seed_database
    settings, calls, _ = delivery
    monkeypatch.setattr(router, "_require_delivery_database", REQUIRE_DELIVERY_DATABASE)
    url = postgres_isolated_cluster_database_url
    asyncio.run(_seed_database(url))
    password = uuid4().hex
    async def setup(sessions):
        await seed(sessions, count=2, providers=("posthog",))
        async with sessions() as db:
            for role in ("twobrain_rec_app", "twobrain_rec_maintenance"):
                await db.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS"))
                await db.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                await db.execute(text(f"GRANT SELECT,UPDATE ON product_activation_milestones TO {role}"))
            await db.commit()
        with pytest.raises(PermissionError):
            await router.reconcile_activation_milestones_once(sessions, settings=settings)
    run(url, setup)
    for role in ("twobrain_rec_app", "twobrain_rec_maintenance"):
        role_url = make_url(url).set(username=role, password=password).render_as_string(hide_password=False)
        async def proof(sessions, role=role):
            if role == "twobrain_rec_app":
                with pytest.raises(PermissionError):
                    await router.reconcile_activation_milestones_once(sessions, settings=settings)
                return
            async with sessions() as db:
                with pytest.raises(PermissionError):
                    await REQUIRE_DELIVERY_DATABASE(db)
                await apply_tenant_context(db, router.DELIVERY_CONTEXT)
                await REQUIRE_DELIVERY_DATABASE(db)
            assert await router.reconcile_activation_milestones_once(sessions, settings=settings) == 2
        run(role_url, proof)
    assert len(calls) == 2

    async def bypass(sessions):
        async with sessions() as db:
            await db.execute(text("ALTER ROLE twobrain_rec_maintenance BYPASSRLS"))
            await db.commit()
    run(url, bypass)
    async def reject_bypass(sessions):
        with pytest.raises(PermissionError):
            await router.reconcile_activation_milestones_once(sessions, settings=settings)
    run(role_url, reject_bypass)
    assert len(calls) == 2


def test_account_close_commit_cancels_queued_attempt_before_fanout(
    postgres_isolated_cluster_database_url, delivery, monkeypatch,
):
    from sqlalchemy.engine import make_url

    from tests.conftest import _seed_database
    from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID
    from twobrain_rec_server.auth.account_closure import begin_account_close_finalization
    from twobrain_rec_server.db.models import AccountClosureRequest
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext

    settings, calls, _ = delivery
    monkeypatch.setattr(router, "_require_delivery_database", REQUIRE_DELIVERY_DATABASE)
    url = postgres_isolated_cluster_database_url
    asyncio.run(_seed_database(url))
    password = uuid4().hex
    stored = {}
    async def setup(sessions):
        original, other = await seed(sessions, count=2)
        stored.update(original=original, other=other)
        async with sessions() as db:
            claim = await router.claim_milestone_delivery(db, milestone_id=original.id, provider="posthog")
            stored["claim"] = claim
            request = AccountClosureRequest(
                workspace_id=PERSONAL_WORKSPACE_ID, requested_by_user_id=USER_ID,
                request_key=uuid4().hex, state="scheduled", policy_version="account-close-v1",
                requested_at=datetime.now(UTC) - timedelta(days=8),
                finalize_at=datetime.now(UTC) - timedelta(days=1),
                metadata_json={"content_workspace_ids": [str(PERSONAL_WORKSPACE_ID)]},
            )
            db.add(request)
            await db.flush()
            stored["request_id"] = request.id
            await db.execute(text(f"CREATE ROLE twobrain_rec_maintenance LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS"))
            await db.execute(text("GRANT USAGE ON SCHEMA public TO twobrain_rec_maintenance"))
            await db.execute(text("GRANT SELECT,UPDATE ON ALL TABLES IN SCHEMA public TO twobrain_rec_maintenance"))
            await db.commit()
    run(url, setup)
    role_url = make_url(url).set(username="twobrain_rec_maintenance", password=password).render_as_string(hide_password=False)
    async def close(sessions):
        context = MaintenanceTenantContext(
            operation_name="billing_reconciliation", actor_id="graf-maintenance",
            reason_category="account_close_finalization", feature_area="account",
        )
        for _ in range(2):
            async with sessions() as db:
                await apply_tenant_context(db, context)
                await begin_account_close_finalization(db, request_id=stored["request_id"], now=datetime.now(UTC))
                await db.commit()  # Deliberately stop here; no deletion fanout/purge.
        assert await router._deliver_claim(sessions, settings, stored["claim"], "posthog") == "purpose_withdrawn"
        assert not calls
        async with sessions() as db:
            await apply_tenant_context(db, router.DELIVERY_CONTEXT)
            original = await db.get(ProductActivationMilestone, stored["original"].id)
            other = await db.get(ProductActivationMilestone, stored["other"].id)
            assert original.posthog_state == original.yandex_state == "cancelled"
            assert other.posthog_state == other.yandex_state == "pending"
            assert not await router.finish_milestone_delivery(
                db, milestone_id=original.id, provider="posthog",
                attempt_id=stored["claim"].posthog_attempt_id, outcome="http_accepted",
            )
            await db.commit()
    run(role_url, close)
