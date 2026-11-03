"""Durability/concurrency/failure proofs on disposable PostgreSQL, without providers."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.auth_contexts import USER_ID
from twobrain_rec_server.db.models import ProductActivationMilestone
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.milestones import (
    admit_account_milestone,
    claim_milestone_delivery,
    finish_milestone_delivery,
    quarantine_milestone_deliveries,
)


def event(name="first_result_viewed", **kwargs):
    return build_activation_event(
        name,
        stable_pseudonymous_user_id=build_safe_identity(
            user_source_id=str(USER_ID)
        ).stable_pseudonymous_user_id,
        **kwargs,
    )


async def admit(sessions, value=None, **kwargs):
    async with sessions() as db:
        row, created = await admit_account_milestone(
            db,
            value or event(),
            account_id=USER_ID,
            source_kind="browser",
            requested_providers=("posthog", "yandex"),
            **kwargs,
        )
        await db.commit()
        return row, created


def run(url, scenario):
    async def execute():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            await scenario(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    asyncio.run(execute())


def test_two_connections_restart_and_reload_keep_one_decision(postgres_seeded_database_url):
    async def scenario(sessions):
        value = event()
        results = await asyncio.gather(*(admit(sessions, value) for _ in range(8)))
        assert sum(created for _, created in results) == 1
        assert len({row.id for row, _ in results}) == 1
        original = results[0][0]
        repeated, created = await admit(
            sessions, event(occurred_at=datetime.now(UTC) - timedelta(days=1))
        )
        assert not created
        assert repeated.event_id == original.event_id
        assert repeated.safe_payload == original.safe_payload
        assert repeated.occurred_at == original.occurred_at
        assert repeated.posthog_state == repeated.yandex_state == "pending"
        async with sessions() as db:
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 1
            )

    run(postgres_seeded_database_url, scenario)


def test_failed_transaction_does_not_accept_or_deliver(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await admit_account_milestone(db, event(), account_id=USER_ID, source_kind="browser")
            await db.rollback()
        _, created = await admit(sessions)
        assert created

    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("technical_pre_send", "pre_send_retry"),
        ("http_accepted", "submitted"),
        ("transport_ambiguous", "ambiguous"),
        ("http_ambiguous", "ambiguous"),
        ("purpose_withdrawn", "cancelled"),
        ("payload_rejected", "rejected"),
    ],
)
def test_attempt_owner_independent_providers_and_retry_boundary(
    postgres_seeded_database_url, outcome, expected
):
    async def scenario(sessions):
        original, _ = await admit(sessions)

        async def claim():
            async with sessions() as db:
                row = await claim_milestone_delivery(
                    db, milestone_id=original.id, provider="posthog"
                )
                await db.commit()
                return row

        claims = await asyncio.gather(claim(), claim())
        assert sum(row is not None for row in claims) == 1
        row = next(row for row in claims if row is not None)
        async with sessions() as db:
            assert not await finish_milestone_delivery(
                db, milestone_id=row.id, provider="posthog", attempt_id=uuid4(), outcome=outcome
            )
            assert await finish_milestone_delivery(
                db,
                milestone_id=row.id,
                provider="posthog",
                attempt_id=row.posthog_attempt_id,
                outcome=outcome,
            )
            await db.commit()
        async with sessions() as db:
            saved = await db.get(ProductActivationMilestone, row.id)
            assert saved.posthog_state == expected
            assert saved.yandex_state == "pending"
            again = await claim_milestone_delivery(db, milestone_id=row.id, provider="posthog")
            assert (again is not None) == (outcome == "technical_pre_send")
            await db.commit()

    run(postgres_seeded_database_url, scenario)


def test_restore_and_interrupted_dispatch_never_enable_retry(postgres_seeded_database_url):
    async def scenario(sessions):
        original, _ = await admit(sessions)
        async with sessions() as db:
            await claim_milestone_delivery(db, milestone_id=original.id, provider="posthog")
            await db.execute(
                update(ProductActivationMilestone).values(
                    posthog_attempted_at=datetime.now(UTC) - timedelta(minutes=2)
                )
            )
            await db.commit()
        async with sessions() as db:
            assert await quarantine_milestone_deliveries(db) == 1
            await db.commit()
        async with sessions() as db:
            assert (
                await claim_milestone_delivery(db, milestone_id=original.id, provider="posthog")
                is None
            )
            assert await quarantine_milestone_deliveries(db, after_restore=True) == 1
            await db.commit()
        async with sessions() as db:
            saved = await db.get(ProductActivationMilestone, original.id)
            assert saved.posthog_state == saved.yandex_state == "ambiguous"
            assert (
                await claim_milestone_delivery(db, milestone_id=original.id, provider="yandex")
                is None
            )

    run(postgres_seeded_database_url, scenario)


def test_storage_rejects_forged_identity_unsafe_event_and_mutation(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            forged = build_activation_event(
                "first_result_viewed",
                stable_pseudonymous_user_id=build_safe_identity(
                    user_source_id=str(uuid4())
                ).stable_pseudonymous_user_id,
            )
            with pytest.raises(ValueError, match="trusted account"):
                await admit_account_milestone(db, forged, account_id=USER_ID, source_kind="browser")
            with pytest.raises(ValueError, match="account milestone"):
                await admit_account_milestone(
                    db, event("desktop_first_opened"), account_id=USER_ID, source_kind="desktop"
                )
        row, _ = await admit(sessions)
        async with sessions() as db:
            with pytest.raises(Exception, match="immutable"):
                await db.execute(
                    update(ProductActivationMilestone)
                    .where(ProductActivationMilestone.id == row.id)
                    .values(source_kind="desktop")
                )
            await db.rollback()
        async with sessions() as db:
            with pytest.raises(Exception, match="activation_posthog_reason"):
                await db.execute(
                    text(
                        "UPDATE product_activation_milestones SET posthog_reason='arbitrary_response_body'"
                    )
                )
            await db.rollback()

    run(postgres_seeded_database_url, scenario)


def test_different_accounts_and_each_of_five_events_are_independent(postgres_seeded_database_url):
    from tests.fakes.auth_contexts import ORG_ID
    from twobrain_rec_server.db.models import UserIdentity
    from twobrain_rec_server.db.models.product_analytics import ACCOUNT_ACTIVATION_EVENTS

    async def scenario(sessions):
        other_id = uuid4()
        async with sessions() as db:
            db.add(
                UserIdentity(
                    id=other_id, organization_id=ORG_ID, external_subject="synthetic-ledger"
                )
            )
            await db.commit()
        for account in (USER_ID, other_id):
            for name in ACCOUNT_ACTIVATION_EVENTS:
                value = build_activation_event(
                    name,
                    stable_pseudonymous_user_id=build_safe_identity(
                        user_source_id=str(account)
                    ).stable_pseudonymous_user_id,
                )
                async with sessions() as db:
                    row, created = await admit_account_milestone(
                        db, value, account_id=account, source_kind="server"
                    )
                    assert created and row.posthog_state == row.yandex_state == "not_requested"
                    await db.commit()
        async with sessions() as db:
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 10
            )

    run(postgres_seeded_database_url, scenario)


def test_size_time_catalog_and_provider_bounds_fail_before_insert(postgres_seeded_database_url):
    from dataclasses import replace

    async def scenario(sessions):
        invalid = (
            replace(event(), properties={"source_bucket": "x" * 17000}),
            replace(event(), properties={"private_payload": "synthetic"}),
            event(occurred_at=datetime.now(UTC) + timedelta(days=1)),
            event(occurred_at=datetime.now()),
        )
        async with sessions() as db:
            for value in invalid:
                with pytest.raises(ValueError):
                    await admit_account_milestone(
                        db, value, account_id=USER_ID, source_kind="browser"
                    )
            with pytest.raises(ValueError, match="source"):
                await admit_account_milestone(
                    db, event(), account_id=USER_ID, source_kind="client_json"
                )
            with pytest.raises(ValueError, match="provider"):
                await admit_account_milestone(
                    db,
                    event(),
                    account_id=USER_ID,
                    source_kind="browser",
                    requested_providers=("other",),
                )
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
            )

    run(postgres_seeded_database_url, scenario)


def test_rls_requires_exact_account_and_rejects_fake_maintenance(postgres_seeded_database_url):
    async def scenario(sessions):
        await admit(sessions)
        role = "graf_ledger_test_" + uuid4().hex
        async with sessions() as db:
            await db.execute(text(f"CREATE ROLE {role} NOLOGIN"))
            await db.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
            await db.execute(text(f"GRANT SELECT ON product_activation_milestones TO {role}"))
            await db.commit()
            try:
                await db.execute(text(f"SET LOCAL ROLE {role}"))
                assert (
                    await db.scalar(select(func.count()).select_from(ProductActivationMilestone))
                    == 0
                )
                await db.execute(
                    text(
                        "SELECT set_config('app.context_kind','request',true), set_config('app.user_id',:id,true)"
                    ),
                    {"id": str(USER_ID)},
                )
                assert (
                    await db.scalar(select(func.count()).select_from(ProductActivationMilestone))
                    == 1
                )
                await db.execute(
                    text("SELECT set_config('app.user_id',:id,true)"), {"id": str(uuid4())}
                )
                assert (
                    await db.scalar(select(func.count()).select_from(ProductActivationMilestone))
                    == 0
                )
                await db.execute(
                    text(
                        "SELECT set_config('app.context_kind','maintenance',true),set_config('app.maintenance_operation','activation_milestone_delivery',true),set_config('app.maintenance_feature_area','product_analytics',true),set_config('app.maintenance_actor','synthetic',true),set_config('app.maintenance_reason','test',true)"
                    )
                )
                assert (
                    await db.scalar(select(func.count()).select_from(ProductActivationMilestone))
                    == 0
                )
            finally:
                await db.rollback()
                await db.execute(text(f"DROP OWNED BY {role}"))
                await db.execute(text(f"DROP ROLE {role}"))
                await db.commit()

    run(postgres_seeded_database_url, scenario)


def test_account_close_purges_only_its_decisions_and_blocks_late_admission(
    postgres_seeded_database_url,
):
    from tests.fakes.auth_contexts import ORG_ID, PERSONAL_WORKSPACE_ID
    from twobrain_rec_server.auth.account_closure import (
        finalize_account_close,
        schedule_account_close,
    )
    from twobrain_rec_server.db.models import AccountClosureRequest, UserIdentity

    async def scenario(sessions):
        original, _ = await admit(sessions)
        other_id = uuid4()
        now = datetime.now(UTC)
        async with sessions() as db:
            db.add(
                UserIdentity(
                    id=other_id, organization_id=ORG_ID, external_subject="synthetic-other-account"
                )
            )
            await db.flush()
            value = build_activation_event(
                "first_result_viewed",
                stable_pseudonymous_user_id=build_safe_identity(
                    user_source_id=str(other_id)
                ).stable_pseudonymous_user_id,
            )
            other, _ = await admit_account_milestone(
                db, value, account_id=other_id, source_kind="server"
            )
            await schedule_account_close(
                db, workspace_id=PERSONAL_WORKSPACE_ID, user_id=USER_ID, now=now - timedelta(days=8)
            )
            await db.commit()
        async with sessions() as db:
            request = await db.scalar(
                select(AccountClosureRequest).where(
                    AccountClosureRequest.requested_by_user_id == USER_ID
                )
            )
            view = await finalize_account_close(db, request_id=request.id, now=now)
            assert view.state == "completed"
            assert request.metadata_json["activation_decisions_purged_count"] == 1
            assert await db.get(ProductActivationMilestone, original.id) is None
            assert await db.get(ProductActivationMilestone, other.id) is not None
            await db.commit()
        async with sessions() as db:
            with pytest.raises(ValueError, match="not active"):
                await admit_account_milestone(db, event(), account_id=USER_ID, source_kind="server")

    run(postgres_seeded_database_url, scenario)


def test_category_erasure_requires_separate_deadline(postgres_seeded_database_url):
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        ATTRIBUTION_PROFILES_LEVEL,
        LegalBasisLifecycleError,
        apply_basis_loss_disposition,
        plan_processing_stop,
    )
    from twobrain_rec_server.product_analytics.retention import retention_rule

    async def scenario(sessions):
        await admit(sessions)
        now = datetime.now(UTC)
        category = "activation_milestone_decisions"
        assert retention_rule(category).retention_mode == "until_decision"
        async with sessions() as db:
            incomplete = plan_processing_stop(
                level_key=ATTRIBUTION_PROFILES_LEVEL,
                basis_lost_at=now,
                reason="synthetic_case",
                affected_categories=(category,),
            )
            with pytest.raises(LegalBasisLifecycleError, match="deadline"):
                await apply_basis_loss_disposition(db, incomplete)
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 1
            )
            complete = plan_processing_stop(
                level_key=ATTRIBUTION_PROFILES_LEVEL,
                basis_lost_at=now,
                reason="synthetic_case",
                affected_categories=(category,),
                deletion_deadlines={category: now + timedelta(days=1)},
            )
            (result,) = await apply_basis_loss_disposition(db, complete, erased_at=now)
            assert (
                result.category == category and result.rows_affected == 1 and result.within_deadline
            )
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
            )

    run(postgres_seeded_database_url, scenario)


def test_empty_migration_round_trip_and_populated_downgrade_guard(
    postgres_clean_database_url,
):
    from sqlalchemy.exc import DBAPIError

    from tests.conftest import _seed_database
    from tests.contract.test_product_analytics_anonymous_aggregate_contract import _run_alembic

    empty = postgres_clean_database_url
    _run_alembic(empty, upgrade_to="0106_activation_milestones")
    _run_alembic(
        empty,
        upgrade_to="0106_activation_milestones",
        downgrade_to="0105_anonymous_aggregate_region",
    )
    _run_alembic(empty, upgrade_to="0106_activation_milestones")
    asyncio.run(_seed_database(empty))

    async def scenario(sessions):
        async with sessions() as db:
            assert (
                await db.scalar(text("SELECT version_num FROM alembic_version"))
                == "0106_activation_milestones"
            )
        await admit(sessions)

    run(empty, scenario)
    with pytest.raises(DBAPIError, match="activation decisions exist"):
        _run_alembic(
            empty,
            upgrade_to="0106_activation_milestones",
            downgrade_to="0105_anonymous_aggregate_region",
        )

    async def still_present(sessions):
        async with sessions() as db:
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 1
            )
            assert (
                await db.scalar(text("SELECT version_num FROM alembic_version"))
                == "0106_activation_milestones"
            )

    run(empty, still_present)


def test_real_runtime_logins_and_rls_owner_cannot_erase_hidden_history(
    postgres_isolated_cluster_database_url,
):
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError

    from tests.conftest import _seed_database
    from tests.contract.test_product_analytics_anonymous_aggregate_contract import _run_alembic

    url = postgres_isolated_cluster_database_url
    _run_alembic(
        url,
        upgrade_to="0106_activation_milestones",
        downgrade_to="0106_activation_milestones",
    )
    asyncio.run(_seed_database(url))
    password = uuid4().hex
    owner_role = "graf_ledger_owner_" + uuid4().hex
    other_id = uuid4()

    async def setup(sessions):
        async with sessions() as db:
            assert (
                await db.scalar(text("SELECT version_num FROM alembic_version"))
                == "0106_activation_milestones"
            )
        await admit(sessions)
        async with sessions() as db:
            from tests.fakes.auth_contexts import ORG_ID
            from twobrain_rec_server.db.models import UserIdentity

            db.add(
                UserIdentity(
                    id=other_id, organization_id=ORG_ID, external_subject="synthetic-rls-other"
                )
            )
            await db.flush()
            await admit_account_milestone(
                db,
                build_activation_event(
                    "first_result_viewed",
                    stable_pseudonymous_user_id=build_safe_identity(
                        user_source_id=str(other_id)
                    ).stable_pseudonymous_user_id,
                ),
                account_id=other_id,
                source_kind="server",
            )
            for role in ("twobrain_rec_app", "twobrain_rec_maintenance", owner_role):
                await db.execute(
                    text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS")
                )
                await db.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                await db.execute(
                    text(
                        f"GRANT SELECT,INSERT,UPDATE,DELETE ON product_activation_milestones TO {role}"
                    )
                )
                for function in (
                    "rec_context_kind",
                    "rec_current_user_id",
                    "rec_setting",
                    "rec_maintenance_allowed",
                ):
                    arguments = "text" if function == "rec_setting" else ""
                    await db.execute(
                        text(f"GRANT EXECUTE ON FUNCTION {function}({arguments}) TO {role}")
                    )
            await db.commit()

    run(url, setup)

    def login_url(role):
        return (
            make_url(url)
            .set(username=role, password=password)
            .render_as_string(hide_password=False)
        )

    for role, allowed in (("twobrain_rec_app", False), ("twobrain_rec_maintenance", True)):

        async def check(sessions, role=role, allowed=allowed):
            async with sessions() as db:
                assert await db.scalar(text("SELECT session_user")) == role
                assert (
                    await db.scalar(select(func.count()).select_from(ProductActivationMilestone))
                    == 0
                )
                for operation, area in (
                    ("activation_milestone_delivery", "product_analytics"),
                    ("account_merge", "account_merge"),
                ):
                    await db.execute(
                        text(
                            "SELECT set_config('app.context_kind','maintenance',true),"
                            "set_config('app.maintenance_operation',:operation,true),"
                            "set_config('app.maintenance_feature_area',:area,true),"
                            "set_config('app.maintenance_actor','synthetic',true),"
                            "set_config('app.maintenance_reason','test',true)"
                        ),
                        {"operation": operation, "area": area},
                    )
                    assert await db.scalar(
                        select(func.count()).select_from(ProductActivationMilestone)
                    ) == 2 * int(allowed)

        run(login_url(role), check)

    async def app_writes(sessions):
        from sqlalchemy import delete

        async with sessions() as db:
            await db.execute(
                text(
                    "SELECT set_config('app.context_kind','request',true),set_config('app.user_id',:id,true)"
                ),
                {"id": str(USER_ID)},
            )
            # Only the authenticated account can read or change its decision.
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 1
            )
            own = await db.execute(
                update(ProductActivationMilestone)
                .where(ProductActivationMilestone.account_id == USER_ID)
                .values(posthog_state="cancelled")
            )
            assert own.rowcount == 1
            foreign = await db.execute(
                update(ProductActivationMilestone)
                .where(ProductActivationMilestone.account_id == other_id)
                .values(posthog_state="cancelled")
            )
            assert foreign.rowcount == 0
            foreign_delete = await db.execute(
                delete(ProductActivationMilestone).where(
                    ProductActivationMilestone.account_id == other_id
                )
            )
            assert foreign_delete.rowcount == 0
            with pytest.raises(DBAPIError, match="row.level security"):
                await db.execute(
                    text(
                        "INSERT INTO product_activation_milestones "
                        "(id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind) "
                        "SELECT :id,:other,event_name,:event,occurred_at,accepted_at,safe_payload,source_kind "
                        "FROM product_activation_milestones WHERE account_id=:own"
                    ),
                    {"id": uuid4(), "other": other_id, "event": uuid4(), "own": USER_ID},
                )
            await db.rollback()

    run(login_url("twobrain_rec_app"), app_writes)

    async def change_owner(sessions):
        async with sessions() as db:
            await db.execute(text(f"GRANT CREATE ON SCHEMA public TO {owner_role}"))
            await db.execute(text(f"GRANT SELECT,UPDATE,DELETE ON alembic_version TO {owner_role}"))
            await db.execute(
                text(f"ALTER TABLE product_activation_milestones OWNER TO {owner_role}")
            )
            await db.commit()

    run(url, change_owner)

    async def hidden_from_owner(sessions):
        async with sessions() as db:
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
            )

    run(login_url(owner_role), hidden_from_owner)
    with pytest.raises(DBAPIError, match="row.level security"):
        _run_alembic(
            login_url(owner_role),
            upgrade_to="0106_activation_milestones",
            downgrade_to="0105_anonymous_aggregate_region",
        )

    async def preserved(sessions):
        async with sessions() as db:
            assert (
                await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 2
            )
            assert (
                await db.scalar(text("SELECT version_num FROM alembic_version"))
                == "0106_activation_milestones"
            )

    run(url, preserved)
