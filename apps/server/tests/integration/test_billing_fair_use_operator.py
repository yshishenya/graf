"""Real LOGIN/SQL boundary for the internal fair-use operator source."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scripts import bootstrap_runtime_database_roles as bootstrap
from tests.integration.test_rls_postgres_policies import _request_context, _seed_probe_rows
from twobrain_rec_server.auth.account_merge import _lock_merge_domain_rows
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.tenant_context import (
    AccountMergeTenantContext,
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_context_to_connection,
)

pytestmark = [pytest.mark.strict_rls, pytest.mark.asyncio]

CONTEXT = MaintenanceTenantContext(
    operation_name="billing_reconciliation", actor_id="test-fair-use",
    reason_category="fair_use_review", feature_area="billing",
)
OPERATOR = "op-" + "a" * 32
CREATE = """
    INSERT INTO public.fair_use_reviews
      (id, workspace_id, subject_user_id, capability, reason_code, evidence_ref,
       starts_at, review_by, state)
    VALUES (:id, :workspace, :subject, 'server_processing', 'resale', :evidence,
            :start, :deadline, 'notice')
    RETURNING *
"""
FORGE_AUDIT = """
    INSERT INTO public.billing_audit_events
      (id,workspace_id,actor_user_id,action,target_kind,target_ref,outcome,reason_code,
       metadata_json,created_at)
    VALUES (:audit,:workspace,NULL,'fair_use.review.created','fair_use_review',:target,
            'applied',NULL,CAST(:metadata AS json),:start)
"""


async def declare_operator(conn):
    await conn.execute(text("SELECT set_config('app.fair_use_operator_ref', :operator, true)"),
                       {"operator": OPERATOR})
    await conn.execute(text("SELECT set_config('app.fair_use_evidence_reviewed', 'true', true)"))


@pytest.fixture
async def operator_case(postgres_isolated_cluster_database_url, monkeypatch):
    url = make_url(postgres_isolated_cluster_database_url)
    passwords = {
        "TWOBRAIN_DB_OWNER_PASSWORD_FILE": url.password,
        "TWOBRAIN_DB_APP_PASSWORD_FILE": uuid4().hex,
        "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE": uuid4().hex,
        "TWOBRAIN_DB_MEDIA_PASSWORD_FILE": uuid4().hex,
    }
    monkeypatch.setattr(bootstrap, "_read_secret", passwords.__getitem__)
    for key, value in {"HOST": url.host, "PORT": str(url.port), "NAME": url.database}.items():
        monkeypatch.setenv(f"TWOBRAIN_DB_{key}", value)
    await bootstrap._bootstrap()
    owner = create_async_engine(url)
    app = create_async_engine(url.set(username="twobrain_rec_app",
                                     password=passwords["TWOBRAIN_DB_APP_PASSWORD_FILE"]))
    maintenance = create_async_engine(url.set(username="twobrain_rec_maintenance",
                                             password=passwords["TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE"]))
    try:
        ids = await _seed_probe_rows(owner)
        # This fixture seeds identities as schema owner, never the protected source.
        for engine, login in [(app, "twobrain_rec_app"), (maintenance, "twobrain_rec_maintenance")]:
            async with engine.connect() as conn:
                row = (await conn.execute(text("""
                    SELECT session_user,current_user,rolsuper,rolbypassrls,
                           current_setting('row_security')
                    FROM pg_roles WHERE rolname=current_user
                """))).one()
                assert tuple(row) == (login, login, False, False, "on")
        start = datetime(2026, 1, 1, tzinfo=UTC)
        values = {"id": uuid4(), "workspace": ids["workspace_a"], "subject": ids["user_a"],
                  "evidence": "incident:synthetic-operator", "start": start,
                  "deadline": start + timedelta(hours=24)}
        yield SimpleNamespace(owner=owner, app=app, maintenance=maintenance, ids=ids, values=values)
    finally:
        for engine in (app, maintenance, owner):
            await engine.dispose()


async def create_source(case):
    async with case.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        return (await conn.execute(text(CREATE), case.values)).mappings().one()


async def source_snapshot(case):
    async with case.owner.connect() as conn:
        review = (await conn.execute(text("SELECT * FROM public.fair_use_reviews WHERE id=:id"),
                                     case.values)).mappings().one_or_none()
        audits = (await conn.execute(text("""
            SELECT * FROM public.billing_audit_events WHERE workspace_id=:workspace
            ORDER BY id
        """), case.values)).mappings().all()
        queue = (await conn.execute(text("""
            SELECT * FROM public.billing_notification_deliveries WHERE workspace_id=:workspace
            ORDER BY id
        """), case.values)).mappings().all()
        return review, audits, queue


@pytest.mark.parametrize("damage", [
    "ALTER POLICY fair_use_review_read ON public.fair_use_reviews USING (true)",
    "ALTER POLICY fair_use_review_read ON public.fair_use_reviews TO twobrain_rec_media",
    "CREATE POLICY additional_read ON public.fair_use_reviews FOR SELECT USING (true)",
    "ALTER POLICY fair_use_audit_append ON public.billing_audit_events WITH CHECK (true)",
    "ALTER POLICY billing_audit_events_tenant_isolation ON public.billing_audit_events USING (true)",
    "DROP INDEX public.uq_fair_use_audit_transition",
    "DROP INDEX public.uq_fair_use_audit_transition; CREATE UNIQUE INDEX uq_fair_use_audit_transition ON public.billing_audit_events (workspace_id,target_ref,action)",
    "ALTER TABLE public.fair_use_reviews DISABLE TRIGGER fair_use_audit_append",
    "ALTER ROLE twobrain_rec_fair_use_audit_writer BYPASSRLS",
])
async def test_bootstrap_rejects_changed_policy_or_missing_index(operator_case, damage):
    c = operator_case
    async with c.owner.begin() as conn:
        for statement in damage.split(";"):
            await conn.execute(text(statement))
    with pytest.raises(RuntimeError, match="fair-use .* unsafe"):
        await bootstrap._bootstrap()
    # The broad grants preceding verification must roll back with the failure.
    async with c.app.connect() as conn:
        assert not await conn.scalar(text(
            "SELECT has_table_privilege(current_user,'public.fair_use_reviews','INSERT,UPDATE,DELETE')"
        ))


@pytest.mark.parametrize("attack", ["create", "classification", "first_deadline", "delete"])
async def test_app_cannot_write_operator_source_even_with_spoofed_declarations(operator_case, attack):
    c = operator_case
    if attack != "create":
        await create_source(c)
    before = await source_snapshot(c)
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        await declare_operator(conn)
        statements = {
            "create": CREATE,
            "classification": "UPDATE public.fair_use_reviews SET reason_code='security_abuse' WHERE id=:id",
            "first_deadline": "UPDATE public.fair_use_reviews SET review_by=starts_at WHERE id=:id",
            "delete": "DELETE FROM public.fair_use_reviews WHERE id=:id",
        }
        with pytest.raises(DBAPIError) as rejected:
            async with conn.begin_nested():
                await conn.execute(text(statements[attack]), c.values)
        assert rejected.value.orig.sqlstate == "42501"
    assert await source_snapshot(c) == before


@pytest.mark.parametrize("login", ["app", "maintenance"])
async def test_runtime_cannot_forge_reserved_audit_even_with_canonical_envelope(operator_case, login):
    c = operator_case
    source = await create_source(c)
    before = await source_snapshot(c)
    # A distinct target ensures a future unique index cannot substitute for authorization.
    values = {**c.values, "audit": uuid4(), "target": str(uuid4()),
              "start": source["starts_at"], "metadata": json.dumps({
                  "version": 1, "source": "maintenance", "previous_state": None, "state": "notice",
                  "db_login": "twobrain_rec_maintenance", "db_writer": "twobrain_rec_fair_use_audit_writer",
                  "declared_operator": OPERATOR, "external_evidence_reviewed": True,
              })}
    async with getattr(c, login).begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT if login == "maintenance" else _request_context(c.ids, "a"))
        await declare_operator(conn)
        with pytest.raises(DBAPIError) as rejected:
            async with conn.begin_nested():
                await conn.execute(text(FORGE_AUDIT), values)
        assert rejected.value.orig.sqlstate == "P0001"
        assert "fair_use_audit_rejected" in str(rejected.value.orig)
    async with c.owner.connect() as conn:
        assert not await conn.scalar(text("SELECT count(*) FROM billing_audit_events WHERE id=:audit"), values)
    assert await source_snapshot(c) == before


async def test_actual_operator_insert_writes_audit_before_commit_and_rolls_it_back(operator_case):
    c = operator_case
    values = {**c.values, "target": str(c.values["id"])}
    async with c.maintenance.connect() as conn, conn.begin():
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        await conn.execute(text(CREATE), values)
        assert await conn.scalar(text("SELECT count(*) FROM billing_audit_events WHERE target_ref=:target"), values) == 1
        async with c.owner.connect() as check:
            assert not await check.scalar(text("SELECT count(*) FROM fair_use_reviews WHERE id=:id"), values)
            assert not await check.scalar(text("SELECT count(*) FROM billing_audit_events WHERE target_ref=:target"), values)
        await conn.rollback()
    async with c.owner.connect() as conn:
        assert not await conn.scalar(text("SELECT count(*) FROM fair_use_reviews WHERE id=:id"), values)
        assert not await conn.scalar(text("SELECT count(*) FROM billing_audit_events WHERE target_ref=:target"), values)


async def test_actual_operator_transition_sets_db_clock_and_automatic_audit_atomically(operator_case):
    c = operator_case
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        db_start = await conn.scalar(text("SELECT transaction_timestamp()"))
        source = (await conn.execute(text(CREATE), c.values)).mappings().one()
        assert source["starts_at"] == source["created_at"] == source["updated_at"] == db_start
        assert source["review_by"] == db_start + timedelta(hours=24)
        audits = (await conn.execute(text("""
            SELECT * FROM billing_audit_events
            WHERE workspace_id=:workspace AND target_ref=:target
        """), {**c.values, "target": str(c.values["id"])})).mappings().all()
        assert len(audits) == 1 and audits[0]["action"] == "fair_use.review.created"
        assert audits[0]["actor_user_id"] is None and audits[0]["created_at"] == db_start
        assert audits[0]["metadata_json"] == {
            "version": 1, "source": "maintenance", "previous_state": None, "state": "notice",
            "db_login": "twobrain_rec_maintenance", "db_writer": "twobrain_rec_fair_use_audit_writer",
            "declared_operator": OPERATOR, "external_evidence_reviewed": True,
        }
        # Before commit a fresh connection sees neither protected source nor history.
        async with c.owner.connect() as check:
            assert not await check.scalar(text("SELECT count(*) FROM fair_use_reviews WHERE id=:id"), c.values)
            assert not await check.scalar(text("SELECT count(*) FROM billing_audit_events WHERE target_ref=:target"),
                                          {"target": str(c.values["id"])})
    # Dispose the pool so the read uses a new physical LOGIN after commit.
    await c.maintenance.dispose()
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        assert await conn.scalar(text("SELECT session_user")) == "twobrain_rec_maintenance"
        committed = (await conn.execute(text("SELECT * FROM public.fair_use_reviews WHERE id=:id"),
                                        c.values)).mappings().one()
        assert committed == source
        committed_audits = (await conn.execute(text("""
            SELECT * FROM public.billing_audit_events WHERE workspace_id=:workspace AND target_ref=:target
        """), {**c.values, "target": str(c.values["id"])})).mappings().all()
        assert committed_audits == audits


@pytest.mark.parametrize("state,reason", [("cleared", "not_substantiated"), ("confirmed", "basis_confirmed")])
async def test_committed_appeal_and_resolution_use_real_logins_after_second_bootstrap(operator_case, state, reason):
    c = operator_case
    await bootstrap._bootstrap()
    source = await create_source(c)
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        await declare_operator(conn)  # App declarations never become an operator actor.
        await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
    await c.maintenance.dispose()
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        appealed = (await conn.execute(text("SELECT * FROM public.fair_use_reviews WHERE id=:id"),
                                       c.values)).mappings().one()
        assert appealed["state"] == "appealed" and appealed["appealed_at"] is not None
        assert appealed["review_by"] == source["review_by"]
        await conn.execute(text("""
            UPDATE public.fair_use_reviews SET state=:state,resolution_code=:reason WHERE id=:id
        """), {**c.values, "state": state, "reason": reason})
    await c.app.dispose()
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        final = (await conn.execute(text("SELECT * FROM public.fair_use_reviews WHERE id=:id"),
                                    c.values)).mappings().one()
        assert final["state"] == state and final["resolution_code"] == reason
        assert final["resolved_at"] is not None and final["review_by"] == source["review_by"]
        assert final["appealed_at"] == appealed["appealed_at"]
        events = (await conn.execute(text("""
            SELECT * FROM public.billing_audit_events WHERE target_ref=:target ORDER BY created_at
        """), {"target": str(c.values["id"])})).mappings().all()
        assert [event["action"] for event in events] == [
            "fair_use.review.created", "fair_use.review.appealed", "fair_use.review.resolved",
        ]
        assert events[1]["actor_user_id"] == c.ids["user_a"]
        assert events[1]["metadata_json"]["declared_operator"] is None
        assert events[1]["metadata_json"]["external_evidence_reviewed"] is None


async def test_operator_declarations_reject_noncanonical_values_without_writes(operator_case):
    c = operator_case
    before = await source_snapshot(c)
    declarations = [(value, "true") for value in (
        None, "", "op-" + "a" * 31, OPERATOR + "a", OPERATOR.upper(),
        " " + OPERATOR, OPERATOR + " ", OPERATOR + "\n", "op-" + "а" * 32,
    )] + [(OPERATOR, value) for value in (None, "", "false", "TRUE", "1", "true ")]
    for operator, attestation in declarations:
        async with c.maintenance.begin() as conn:
            await apply_tenant_context_to_connection(conn, CONTEXT)
            await conn.execute(text("SELECT set_config('app.fair_use_operator_ref', :value, true)"),
                               {"value": operator})
            await conn.execute(text("SELECT set_config('app.fair_use_evidence_reviewed', :value, true)"),
                               {"value": attestation})
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text(CREATE), c.values)
            assert rejected.value.orig.sqlstate == "P0001"
            assert "fair_use_operator_declaration_rejected" in str(rejected.value.orig)
        assert await source_snapshot(c) == before


async def test_wrong_operator_context_and_set_role_do_not_grant_authority(operator_case):
    c = operator_case
    before = await source_snapshot(c)
    for engine, operation, feature in (
        (c.maintenance, "operator_diagnostics", "billing"),
        (c.maintenance, "billing_reconciliation", "security"),
        (c.app, "billing_reconciliation", "billing"),
        (c.owner, "billing_reconciliation", "billing"),
    ):
        async with engine.begin() as conn:
            if engine is c.owner:
                await conn.execute(text("SET LOCAL ROLE twobrain_rec_maintenance"))
                assert await conn.scalar(text("SELECT session_user <> current_user"))
            await apply_tenant_context_to_connection(conn, MaintenanceTenantContext(
                operation_name=operation, actor_id="test-fair-use", reason_category="fair_use_review",
                feature_area=feature,
            ))
            await declare_operator(conn)
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text(CREATE), c.values)
            assert rejected.value.orig.sqlstate == ("42501" if engine is c.app else "P0001")
            if engine is not c.app:
                assert "fair_use_authority_rejected" in str(rejected.value.orig)
        assert await source_snapshot(c) == before


async def test_appeal_and_resolution_replay_preserve_first_history_and_reject_conflict(operator_case):
    c = operator_case
    await create_source(c)
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        await conn.execute(text("UPDATE fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
    appealed = await source_snapshot(c)
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        await conn.execute(text("UPDATE fair_use_reviews SET state=state,updated_at=now() WHERE id=:id"), c.values)
    assert await source_snapshot(c) == appealed
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        await conn.execute(text("UPDATE fair_use_reviews SET state='cleared',resolution_code='no_longer_applicable' WHERE id=:id"), c.values)
    final = await source_snapshot(c)
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        await conn.execute(text("UPDATE fair_use_reviews SET state='cleared',resolution_code='no_longer_applicable',updated_at=now() WHERE id=:id"), c.values)
        with pytest.raises(DBAPIError) as rejected:
            async with conn.begin_nested():
                await conn.execute(text("UPDATE fair_use_reviews SET state='confirmed',resolution_code='basis_confirmed' WHERE id=:id"), c.values)
        assert rejected.value.orig.sqlstate == "P0001"
        assert "fair_use_transition_rejected" in str(rejected.value.orig)
    assert await source_snapshot(c) == final


@pytest.mark.parametrize("login", ["app", "maintenance"])
async def test_reserved_history_and_ordinary_laundering_are_rejected_atomically(operator_case, login):
    c = operator_case
    await create_source(c)
    ordinary = uuid4()
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await conn.execute(text("""
            INSERT INTO billing_audit_events (id,workspace_id,action,target_kind,target_ref,outcome,metadata_json)
            VALUES (:ordinary,:workspace,'ordinary.test','test','synthetic','applied','{}')
        """), {**c.values, "ordinary": ordinary})
    before = await source_snapshot(c)
    for sql in (
        "UPDATE billing_audit_events SET action='ordinary.test',target_kind='test' WHERE target_ref=:target",
        "UPDATE billing_audit_events SET actor_user_id=:subject WHERE target_ref=:target",
        "UPDATE billing_audit_events SET created_at=now(),metadata_json='{}' WHERE target_ref=:target",
        "DELETE FROM billing_audit_events WHERE target_ref=:target",
        "UPDATE billing_audit_events SET action='fair_use.future' WHERE id=:ordinary",
        "UPDATE billing_audit_events SET target_kind='fair_use_review' WHERE id=:ordinary",
    ):
        async with getattr(c, login).begin() as conn:
            await apply_tenant_context_to_connection(conn, CONTEXT if login == "maintenance" else _request_context(c.ids, "a"))
            await declare_operator(conn)
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text(sql), {**c.values, "target": str(c.values["id"]), "ordinary": ordinary})
            assert rejected.value.orig.sqlstate == "P0001"
            assert "fair_use_history_protected" in str(rejected.value.orig)
        assert await source_snapshot(c) == before


@pytest.mark.parametrize("login", ["app", "maintenance"])
async def test_runtime_cannot_disable_or_assume_history_writer(operator_case, login):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    for sql in (
        "SET LOCAL ROLE twobrain_rec_fair_use_audit_writer",
        "SET LOCAL session_replication_role=replica",
        "ALTER TABLE public.fair_use_reviews DISABLE TRIGGER fair_use_audit_append",
        "TRUNCATE public.fair_use_reviews",
        "TRUNCATE public.billing_audit_events",
        "SELECT public.rec_append_fair_use_audit()",
        "CREATE TRIGGER forged AFTER UPDATE ON public.fair_use_reviews FOR EACH ROW EXECUTE FUNCTION public.rec_append_fair_use_audit()",
        "CREATE OR REPLACE FUNCTION public.rec_append_fair_use_audit() RETURNS trigger LANGUAGE plpgsql AS 'BEGIN RETURN NULL; END'",
    ):
        async with getattr(c, login).begin() as conn:
            await apply_tenant_context_to_connection(conn, CONTEXT if login == "maintenance" else _request_context(c.ids, "a"))
            raw = await conn.get_raw_connection()
            # Simple-query protocol avoids preparing PostgreSQL's trigger pseudo-type.
            with pytest.raises(asyncpg.PostgresError) as rejected:
                async with conn.begin_nested():
                    await raw.driver_connection.execute(sql)
            assert rejected.value.sqlstate == "42501"
        assert await source_snapshot(c) == before


@pytest.mark.parametrize("login", ["app", "maintenance"])
async def test_copy_and_upsert_cannot_forge_reserved_history(operator_case, login):
    c = operator_case
    source = await create_source(c)
    before = await source_snapshot(c)
    metadata = json.dumps({
        "version": 1, "source": "maintenance", "previous_state": None, "state": "notice",
        "db_login": "twobrain_rec_maintenance", "db_writer": "twobrain_rec_fair_use_audit_writer",
        "declared_operator": OPERATOR, "external_evidence_reviewed": True,
    })
    values = {**c.values, "audit": uuid4(), "target": str(uuid4()),
              "metadata": metadata, "start": source["starts_at"]}
    async with getattr(c, login).begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT if login == "maintenance" else _request_context(c.ids, "a"))
        await declare_operator(conn)
        with pytest.raises(DBAPIError) as rejected:
            async with conn.begin_nested():
                await conn.execute(text(FORGE_AUDIT + " ON CONFLICT DO NOTHING"), values)
        assert rejected.value.orig.sqlstate == "P0001"
        assert "fair_use_audit_rejected" in str(rejected.value.orig)
        raw = await conn.get_raw_connection()
        with pytest.raises(asyncpg.PostgresError) as copied:
            async with conn.begin_nested():
                await raw.driver_connection.copy_records_to_table(
                    "billing_audit_events", schema_name="public",
                    columns=("id", "workspace_id", "action", "target_kind", "target_ref", "outcome", "metadata_json", "created_at"),
                    records=[(values["audit"], values["workspace"], "fair_use.review.created",
                              "fair_use_review", values["target"], "applied", metadata, values["start"])],
                )
        assert copied.value.sqlstate == "0A000"
        assert "COPY FROM not supported with row-level security" in str(copied.value)
    assert await source_snapshot(c) == before


async def test_actual_merge_domain_lock_holds_review_but_cannot_mutate_it(operator_case):
    c = operator_case
    intent, identity, callback = uuid4(), uuid4(), uuid4()
    values = {**c.values, **c.ids, "intent": intent, "identity": identity, "callback": callback}
    # Trusted setup creates authentication proofs, never a fair-use source or audit.
    async with c.owner.begin() as conn:
        for sql in (
            "UPDATE user_identities SET organization_id=:org_a WHERE id=:user_b",
            "UPDATE workspaces SET owner_user_id=:user_a,kind='personal' WHERE id=:workspace_a",
            "UPDATE workspaces SET organization_id=:org_a,owner_user_id=:user_b,kind='personal' WHERE id=:workspace_b",
            """INSERT INTO external_identities (id,user_id,provider,provider_subject,email,is_verified,is_active)
                VALUES (:identity,:user_b,'email',:evidence,:evidence,true,true)""",
            """INSERT INTO auth_callback_states (id,provider,state_nonce,workspace_id,expected_state,
                    expires_at,used_at,result,verified_external_identity_id)
                VALUES (:callback,'email',:evidence,:workspace_a,:evidence,
                    now()+interval '15 minutes',now(),'completed',:identity)""",
            """INSERT INTO account_merge_intents (id,workspace_id,survivor_user_id,source_user_id,
                    initiating_auth_session_id,source_external_identity_id,proof_callback_state_id,
                    email_proof_state,oauth_proof_state,status,expires_at)
                VALUES (:intent,:workspace_a,:user_a,:user_b,:session_a,:identity,:callback,
                    'verified','verified','preview_ready',now()+interval '15 minutes')""",
        ):
            await conn.execute(text(sql), values)
    c.values.update(workspace=c.ids["workspace_b"], subject=c.ids["user_b"])
    await create_source(c)
    before = await source_snapshot(c)
    merge_context = AccountMergeTenantContext(
        intent_id=intent, workspace_id=c.ids["workspace_a"],
        survivor_user_id=c.ids["user_a"], source_user_id=c.ids["user_b"],
    )
    async with async_sessionmaker(c.app)() as db:
        await apply_tenant_context(db, merge_context)
        assert await db.scalar(text("SELECT rec_account_merge_context_valid()")) is True
        assert await db.scalar(text("SELECT id FROM fair_use_reviews WHERE id=:id"), c.values) == c.values["id"]
        await _lock_merge_domain_rows(db, survivor_user_id=c.ids["user_a"], source_user_id=c.ids["user_b"])
        for sql, state in (
            ("UPDATE fair_use_reviews SET state='appealed' WHERE id=:id", "P0001"),
            ("UPDATE fair_use_reviews SET reason_code='security_abuse' WHERE id=:id", "42501"),
            ("UPDATE fair_use_reviews SET resolved_at=now() WHERE id=:id", "42501"),
        ):
            with pytest.raises(DBAPIError) as rejected:
                async with db.begin_nested():
                    await db.execute(text(sql), c.values)
            assert rejected.value.orig.sqlstate == state
        async with c.maintenance.begin() as contender:
            await apply_tenant_context_to_connection(contender, CONTEXT)
            await declare_operator(contender)
            with pytest.raises(DBAPIError) as blocked:
                async with contender.begin_nested():
                    # Lock only the review; an UPDATE could wait on the audit's workspace FK.
                    await contender.execute(text("SELECT id FROM public.fair_use_reviews WHERE id=:id FOR UPDATE NOWAIT"), c.values)
            assert blocked.value.orig.sqlstate == "55P03"
        assert await source_snapshot(c) == before
        await db.rollback()
    # Once the genuine merge transaction releases its locks, the same resolve commits.
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        assert await conn.scalar(text("SELECT id FROM public.fair_use_reviews WHERE id=:id FOR UPDATE NOWAIT"), c.values) == c.values["id"]
        await conn.execute(text("UPDATE fair_use_reviews SET state='cleared',resolution_code='not_substantiated' WHERE id=:id"), c.values)
    after = await source_snapshot(c)
    assert after[0]["state"] == "cleared"
    assert len(after[1]) == 2 and after[2] == before[2]


@pytest.mark.parametrize("phase", ["created", "appealed", "resolved"])
async def test_audit_v1_rejects_malformed_envelopes_under_minimal_writer(operator_case, phase):
    c = operator_case
    source = await create_source(c)
    before = await source_snapshot(c)
    request = phase == "appealed"
    login = "twobrain_rec_app" if request else "twobrain_rec_maintenance"
    envelope = {
        "id": str(uuid4()), "workspace_id": str(c.values["workspace"]),
        "actor_user_id": str(c.values["subject"]) if request else None,
        "action": f"fair_use.review.{phase}", "target_kind": "fair_use_review",
        "target_ref": str(uuid4()), "outcome": "applied",
        "reason_code": "basis_confirmed" if phase == "resolved" else None,
        "created_at": source["starts_at"].isoformat(),
        "metadata_json": {
            "version": 1, "source": "request" if request else "maintenance",
            "previous_state": None if phase == "created" else "notice",
            "state": {"created": "notice", "appealed": "appealed", "resolved": "confirmed"}[phase],
            "db_login": login, "db_writer": "twobrain_rec_fair_use_audit_writer",
            "declared_operator": None if request else OPERATOR,
            "external_evidence_reviewed": None if request else True,
        },
    }
    cases = []
    for key in envelope["metadata_json"]:
        missing = deepcopy(envelope)
        del missing["metadata_json"][key]
        cases.append((f"missing_{key}", missing))
    invalid = {
        "version": [None, True, False, "1", 0, 2, [], {}],
        "source": [None, True, 1, [], {}, "worker", "maintenance" if request else "request"],
        "previous_state": (["notice", False, 0, [], {}] if phase == "created"
                           else [None, False, 0, [], {}, "cleared", "unknown"]),
        "state": [None, True, 1, [], {}, "unknown", "notice" if request or phase == "resolved" else "cleared"],
        "db_login": [None, True, 1, [], {}, "owner", "twobrain_rec_maintenance" if request else "twobrain_rec_app"],
        "db_writer": [None, True, 1, [], {}, login],
        "declared_operator": ([OPERATOR, "", True, 1, [], {}] if request else
                              [None, True, 1, [], {}, "", OPERATOR.upper(), OPERATOR + "\n", "op-" + "а" * 32]),
        "external_evidence_reviewed": ([True, False, "true", 1, [], {}] if request else
                                      [None, False, "true", 1, [], {}]),
    }
    for key, values in invalid.items():
        for index, value in enumerate(values):
            bad = deepcopy(envelope)
            bad["metadata_json"][key] = value
            cases.append((f"type_or_enum_{key}_{index}", bad))
    for index, metadata in enumerate([None, [], "object", True, 1, {**envelope["metadata_json"], "unknown": None}]):
        cases.append((f"metadata_shape_{index}", {**envelope, "metadata_json": metadata}))
    for key, values in {
        "id": [None], "workspace_id": [None],
        "actor_user_id": [None, str(uuid4())] if request else [str(c.values["subject"])],
        "action": [None, "fair_use.future", "ordinary.test"],
        "target_kind": [None, "ordinary"],
        "target_ref": [None, "", str(uuid4()).upper(), "not-a-uuid"],
        "outcome": [None, "delivered"],
        "reason_code": [None, "not_substantiated", "unknown"] if phase == "resolved" else ["basis_confirmed"],
        "created_at": [None, "infinity", "-infinity"],
    }.items():
        for index, value in enumerate(values):
            cases.append((f"column_{key}_{index}", {**envelope, key: value}))
    missing_metadata = deepcopy(envelope)
    del missing_metadata["metadata_json"]
    cases.append(("metadata_sql_null", missing_metadata))

    # Trusted negative setup exposes the guard only; it is never an operator source.
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            CREATE FUNCTION public.test_only_fair_use_envelope(p jsonb) RETURNS text[]
            LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET row_security=on AS $$
            BEGIN
                INSERT INTO public.billing_audit_events
                    (id,workspace_id,actor_user_id,action,target_kind,target_ref,outcome,reason_code,metadata_json,created_at)
                VALUES ((p->>'id')::uuid,(p->>'workspace_id')::uuid,(p->>'actor_user_id')::uuid,
                    p->>'action',p->>'target_kind',p->>'target_ref',p->>'outcome',p->>'reason_code',
                    (p->'metadata_json')::json,(p->>'created_at')::timestamptz);
                RETURN ARRAY[session_user::text,current_user::text,current_setting('row_security')];
            END $$
        """))
        await conn.execute(text("ALTER FUNCTION public.test_only_fair_use_envelope(jsonb) OWNER TO twobrain_rec_fair_use_audit_writer"))
        await conn.execute(text("REVOKE ALL ON FUNCTION public.test_only_fair_use_envelope(jsonb) FROM PUBLIC"))
        await conn.execute(text(f"GRANT EXECUTE ON FUNCTION public.test_only_fair_use_envelope(jsonb) TO {login}"))
    try:
        engine = c.app if request else c.maintenance
        async with engine.begin() as conn:
            await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a") if request else CONTEXT)
            assert await conn.scalar(text("SELECT session_user=current_user AND current_user=:login"), {"login": login})
            assert not await conn.scalar(text("SELECT has_table_privilege('twobrain_rec_fair_use_audit_writer','public.billing_audit_events','SELECT,UPDATE,DELETE')"))
            # A rolled-back valid control proves failures below come from the envelope.
            savepoint = await conn.begin_nested()
            identities = await conn.scalar(text("SELECT public.test_only_fair_use_envelope(CAST(:p AS jsonb))"), {"p": json.dumps(envelope)})
            assert identities == [login, "twobrain_rec_fair_use_audit_writer", "on"]
            assert await conn.scalar(text("SELECT count(*) FROM public.billing_audit_events WHERE id=CAST(:id AS uuid)"), envelope) == 1
            await savepoint.rollback()
            for name, bad in cases:
                with pytest.raises(DBAPIError) as rejected:
                    async with conn.begin_nested():
                        await conn.execute(text("SELECT public.test_only_fair_use_envelope(CAST(:p AS jsonb))"), {"p": json.dumps(bad)})
                assert rejected.value.orig.sqlstate == "P0001", name
                assert "fair_use_audit_rejected" in str(rejected.value.orig), name
                assert await conn.scalar(text("SELECT count(*) FROM public.billing_audit_events WHERE workspace_id=:workspace"), c.values) == 1, name
                assert await source_snapshot(c) == before, name
        assert await source_snapshot(c) == before
    finally:
        async with c.owner.begin() as conn:
            await conn.execute(text("DROP FUNCTION public.test_only_fair_use_envelope(jsonb)"))


@pytest.fixture
async def operator_migrations(operator_case, postgres_isolated_cluster_database_url, monkeypatch):
    server = Path(__file__).resolve().parents[2]
    config = Config(str(server / "alembic.ini"))
    config.set_main_option("script_location", str(server / "src/twobrain_rec_server/db/migrations"))
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_isolated_cluster_database_url)
    get_settings.cache_clear()

    async def migrate(direction, target):
        await asyncio.to_thread(getattr(command, direction), config, target)

    try:
        yield migrate
    finally:
        get_settings.cache_clear()


async def test_legacy_upgrade_preserves_all_states_without_backfill_and_keeps_appeal(
    operator_case, operator_migrations,
):
    c = operator_case
    await operator_migrations("downgrade", "0112_storage_notifications")
    states = ("notice", "restricted", "appealed", "cleared", "confirmed")
    ids = {state: uuid4() for state in states}
    # Trusted setup represents history from before 0113, never a new operator action.
    async with c.owner.begin() as conn:
        for state in states:
            await conn.execute(text("""
                INSERT INTO public.fair_use_reviews
                    (id,workspace_id,subject_user_id,capability,reason_code,evidence_ref,
                     starts_at,review_by,state,appealed_at,appeal_ref,resolved_at,resolution_code)
                VALUES (:id,:workspace,:subject,'server_processing','resale',:evidence,
                    :start,:deadline,:state,:appealed,:appeal,:resolved,:resolution)
            """), {**c.values, "id": ids[state], "state": state, "evidence": f"legacy:{state}",
                   "appealed": c.values["start"] + timedelta(hours=1) if state == "appealed" else None,
                   "appeal": "appeal:legacy" if state == "appealed" else None,
                   "resolved": c.values["start"] + timedelta(hours=2) if state in ("cleared", "confirmed") else None,
                   "resolution": "legacy_decision" if state in ("cleared", "confirmed") else None})
        before = (await conn.execute(text("SELECT * FROM public.fair_use_reviews ORDER BY id"))).mappings().all()
    await operator_migrations("upgrade", "head")
    async with c.owner.connect() as conn:
        assert (await conn.execute(text("SELECT * FROM public.fair_use_reviews ORDER BY id"))).mappings().all() == before
        assert await conn.scalar(text("SELECT count(*) FROM public.billing_audit_events")) == 0
        assert await conn.scalar(text("SELECT count(*) FROM public.billing_notification_deliveries")) == 0
    await bootstrap._bootstrap()
    for state in states:
        async with c.maintenance.begin() as conn:
            await apply_tenant_context_to_connection(conn, CONTEXT)
            await declare_operator(conn)
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text("UPDATE public.fair_use_reviews SET state='confirmed',resolution_code='basis_confirmed' WHERE id=:id"), {"id": ids[state]})
            assert rejected.value.orig.sqlstate == "P0001"
            assert "fair_use_transition_rejected" in str(rejected.value.orig)
    async with c.owner.connect() as conn:
        assert (await conn.execute(text("SELECT * FROM public.fair_use_reviews ORDER BY id"))).mappings().all() == before
    for state in ("notice", "restricted"):
        async with c.app.begin() as conn:
            await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
            await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), {"id": ids[state]})
    await c.maintenance.dispose()
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        events = (await conn.execute(text("SELECT action,target_ref,actor_user_id,metadata_json FROM public.billing_audit_events ORDER BY target_ref"))).mappings().all()
        assert len(events) == 2
        assert {event["target_ref"] for event in events} == {str(ids["notice"]), str(ids["restricted"])}
        assert all(event["action"] == "fair_use.review.appealed" and event["actor_user_id"] == c.ids["user_a"] for event in events)
        assert {event["metadata_json"]["previous_state"] for event in events} == {"notice", "restricted"}
        assert await conn.scalar(text("SELECT count(*) FROM public.billing_notification_deliveries")) == 0


async def test_nonempty_downgrade_refuses_without_losing_protection(operator_case, operator_migrations):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    with pytest.raises(DBAPIError) as rejected:
        await operator_migrations("downgrade", "0112_storage_notifications")
    assert rejected.value.orig.sqlstate == "P0001"
    assert "fair_use_downgrade_history_protected" in str(rejected.value.orig)
    assert await source_snapshot(c) == before
    await bootstrap._bootstrap()
    async with c.owner.connect() as conn:
        assert await conn.scalar(text("SELECT version_num FROM alembic_version")) == "0113_fair_use_operator_history"
        assert await conn.scalar(text("SELECT bool_and(tgenabled='A') FROM pg_trigger WHERE tgname IN ('fair_use_review_guard','fair_use_audit_append','fair_use_audit_guard')")) is True


@pytest.mark.parametrize("conflict", ["reserved_action", "reserved_target", "unsafe_writer_login"])
async def test_upgrade_conflict_rolls_back_schema_and_preserves_legacy(
    operator_case, operator_migrations, conflict,
):
    c = operator_case
    await operator_migrations("downgrade", "0112_storage_notifications")
    async with c.owner.begin() as conn:
        if conflict == "unsafe_writer_login":
            await conn.execute(text("ALTER ROLE twobrain_rec_fair_use_audit_writer LOGIN"))
        else:
            await conn.execute(text("""
                INSERT INTO public.billing_audit_events
                    (id,workspace_id,action,target_kind,target_ref,outcome,metadata_json)
                VALUES (:id,:workspace,:action,:kind,'legacy','applied','{}')
            """), {**c.values, "action": "fair_use.legacy" if conflict == "reserved_action" else "ordinary.test",
                   "kind": "fair_use_review" if conflict == "reserved_target" else "ordinary"})
        helper = await conn.scalar(text("SELECT pg_get_functiondef('public.rec_maintenance_allowed()'::regprocedure)"))
        policies = (await conn.execute(text("SELECT * FROM pg_policies WHERE schemaname='public' AND tablename IN ('fair_use_reviews','billing_audit_events') ORDER BY tablename,policyname"))).mappings().all()
    before = await source_snapshot(c)
    with pytest.raises(DBAPIError) as rejected:
        await operator_migrations("upgrade", "head")
    assert rejected.value.orig.sqlstate == "P0001"
    assert ("fair_use_writer_unsafe" if conflict == "unsafe_writer_login" else "fair_use_legacy_audit_conflict") in str(rejected.value.orig)
    assert await source_snapshot(c) == before
    async with c.owner.connect() as conn:
        assert await conn.scalar(text("SELECT version_num FROM alembic_version")) == "0112_storage_notifications"
        assert await conn.scalar(text("SELECT pg_get_functiondef('public.rec_maintenance_allowed()'::regprocedure)")) == helper
        assert (await conn.execute(text("SELECT * FROM pg_policies WHERE schemaname='public' AND tablename IN ('fair_use_reviews','billing_audit_events') ORDER BY tablename,policyname"))).mappings().all() == policies
        assert await conn.scalar(text("SELECT to_regprocedure('public.rec_guard_fair_use_review()') IS NULL")) is True
        assert await conn.scalar(text("SELECT to_regclass('public.uq_fair_use_audit_transition') IS NULL")) is True
        if conflict == "unsafe_writer_login":
            assert await conn.scalar(text("SELECT rolcanlogin FROM pg_roles WHERE rolname='twobrain_rec_fair_use_audit_writer'")) is True


async def test_media_login_has_no_review_or_audit_authority(operator_case):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    media = create_async_engine(c.owner.url.set(
        username="twobrain_rec_media",
        password=bootstrap._read_secret("TWOBRAIN_DB_MEDIA_PASSWORD_FILE"),
    ))
    try:
        async with media.begin() as conn:
            await apply_tenant_context_to_connection(conn, CONTEXT)
            await declare_operator(conn)
            assert (await conn.execute(text("SELECT session_user,current_user"))).one() == ("twobrain_rec_media", "twobrain_rec_media")
            for sql in (
                "SELECT * FROM public.fair_use_reviews",
                CREATE,
                "UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id",
                "SELECT * FROM public.billing_audit_events",
                "SET LOCAL ROLE twobrain_rec_maintenance",
            ):
                with pytest.raises(DBAPIError) as rejected:
                    async with conn.begin_nested():
                        await conn.execute(text(sql), c.values)
                assert rejected.value.orig.sqlstate == "42501"
                assert await source_snapshot(c) == before
    finally:
        await media.dispose()


async def test_cross_scope_and_distinct_owner_cannot_appeal_subject_history(operator_case):
    c = operator_case
    source = await create_source(c)
    owner = uuid4()
    async with c.owner.begin() as conn:
        await conn.execute(text("INSERT INTO public.user_identities (id,organization_id,external_subject,display_name) VALUES (:owner,:org_a,:external,'Synthetic distinct owner')"),
                           {**c.ids, "owner": owner, "external": "owner-" + owner.hex})
        await conn.execute(text("INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES (:workspace_a,:owner,'owner','active')"), {**c.ids, "owner": owner})
        await conn.execute(text("UPDATE public.workspaces SET owner_user_id=:owner WHERE id=:workspace_a"), {**c.ids, "owner": owner})
    before = await source_snapshot(c)
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "b"))
        assert await conn.scalar(text("SELECT count(*) FROM public.fair_use_reviews WHERE id=:id"), c.values) == 0
        result = await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
        assert result.rowcount == 0
    # A distinct workspace owner may read, but the original subject owns the appeal.
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context({**c.ids, "user_a": owner}, "a"))
        assert (await conn.execute(text("SELECT * FROM public.fair_use_reviews WHERE id=:id"), c.values)).mappings().one() == source
        with pytest.raises(DBAPIError) as rejected:
            async with conn.begin_nested():
                await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
        assert rejected.value.orig.sqlstate == "P0001"
        assert "fair_use_authority_rejected" in str(rejected.value.orig)
    assert await source_snapshot(c) == before
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
    after = await source_snapshot(c)
    assert after[0]["state"] == "appealed" and len(after[1]) == 2 and after[2] == before[2]


@pytest.mark.parametrize("login", ["app", "maintenance"])
async def test_row_security_off_is_not_an_operator_or_appeal_bypass(operator_case, login):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    async with getattr(c, login).begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT if login == "maintenance" else _request_context(c.ids, "a"))
        await declare_operator(conn)
        await conn.execute(text("SET LOCAL row_security=off"))
        for sql in (
            "SELECT * FROM public.fair_use_reviews WHERE id=:id",
            "UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id",
            "SELECT * FROM public.billing_audit_events WHERE workspace_id=:workspace",
        ):
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text(sql), c.values)
            assert rejected.value.orig.sqlstate == "42501"
            assert "row-level security policy" in str(rejected.value.orig)
    assert await source_snapshot(c) == before


async def test_temp_shadowing_cannot_redirect_transition_or_automatic_history(operator_case):
    c = operator_case
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        for sql in (
            "CREATE TEMP TABLE fair_use_reviews (id uuid)",
            "CREATE TEMP TABLE billing_audit_events (id uuid)",
            "CREATE FUNCTION pg_temp.rec_setting(name text) RETURNS text LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'shadow_reached'; END $$",
            "CREATE FUNCTION pg_temp.rec_context_kind() RETURNS text LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'shadow_reached'; END $$",
            "SET LOCAL search_path=pg_temp,public",
        ):
            await conn.execute(text(sql))
        await conn.execute(text(CREATE), c.values)
        assert await conn.scalar(text("SELECT count(*) FROM pg_temp.fair_use_reviews")) == 0
        assert await conn.scalar(text("SELECT count(*) FROM pg_temp.billing_audit_events")) == 0
        assert await conn.scalar(text("SELECT count(*) FROM public.fair_use_reviews WHERE id=:id"), c.values) == 1
        assert await conn.scalar(text("SELECT count(*) FROM public.billing_audit_events WHERE workspace_id=:workspace"), c.values) == 1
    after = await source_snapshot(c)
    assert after[0]["state"] == "notice" and len(after[1]) == 1 and after[2] == []


@pytest.mark.parametrize("decision,code", [("cleared", "not_substantiated"), ("confirmed", "basis_confirmed")])
async def test_operator_cli_commits_source_audit_and_original_recipient_once(operator_case, decision, code):
    from twobrain_rec_server.cli import billing_fair_use as cli

    c = operator_case
    async with c.owner.begin() as conn:
        await conn.execute(text("UPDATE workspaces SET owner_user_id=:subject WHERE id=:workspace"), c.values)
    settings = SimpleNamespace(database_url=c.maintenance.url.render_as_string(hide_password=False))
    base = ["--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed"]
    create = ["create", *base, "--subject", str(c.values["subject"]),
              "--capability", "server_processing", "--reason", "resale"]
    resolve = ["resolve", *base, "--decision", decision, "--resolution-code", code]

    async def snapshot():
        async with c.owner.connect() as conn:
            return [(await conn.execute(text(f"SELECT to_jsonb(t) FROM public.{table} t WHERE workspace_id=:workspace ORDER BY id"), c.values)).scalars().all()
                    for table in ("fair_use_reviews", "billing_audit_events", "billing_notification_deliveries")]

    assert await snapshot() == [[], [], []]
    assert await cli.run(cli.parse_args(create), settings=settings) == (
        {"result_code": "validated", "dry_run": True, "status": "notice"}, 0)
    assert await snapshot() == [[], [], []]
    assert await cli.run(cli.parse_args(create + ["--execute"]), settings=settings) == (
        {"result_code": "applied", "dry_run": False, "status": "notice"}, 0)
    initial = await snapshot()
    review, audit, queue = initial
    assert len(review) == len(audit) == len(queue) == 1
    assert audit[0]["action"] == "fair_use.review.created"
    assert queue[0]["recipient_id"] == str(c.values["subject"])
    assert queue[0]["safe_payload"]["phase"] == "notice"
    assert queue[0]["safe_payload"]["fair_use_review_id"] == review[0]["id"]
    assert datetime.fromisoformat(review[0]["review_by"]) - datetime.fromisoformat(review[0]["starts_at"]) == timedelta(hours=24)
    assert await cli.run(cli.parse_args(create + ["--execute"]), settings=settings) == (
        {"result_code": "unchanged", "dry_run": False, "status": "notice"}, 0)
    assert await snapshot() == initial
    conflict = create.copy()
    conflict[conflict.index("--reason") + 1] = "security_abuse"
    result, exit_code = await cli.run(cli.parse_args(conflict + ["--execute"]), settings=settings)
    assert exit_code == 1 and result == {"result_code": "review_rejected"}
    assert await snapshot() == initial
    assert await cli.run(cli.parse_args(resolve), settings=settings) == (
        {"result_code": "validated", "dry_run": True, "status": decision}, 0)
    assert await snapshot() == initial
    assert await cli.run(cli.parse_args(resolve + ["--execute"]), settings=settings) == (
        {"result_code": "applied", "dry_run": False, "status": decision}, 0)
    final = await snapshot()
    assert final[0][0]["state"] == decision and final[0][0]["resolution_code"] == code
    assert final[0][0]["starts_at"] == review[0]["starts_at"] and final[0][0]["review_by"] == review[0]["review_by"]
    assert len(final[1]) == len(final[2]) == 2
    assert {item["safe_payload"]["phase"] for item in final[2]} == {"notice", decision}
    assert await cli.run(cli.parse_args(resolve + ["--execute"]), settings=settings) == (
        {"result_code": "unchanged", "dry_run": False, "status": decision}, 0)
    assert await cli.run(cli.parse_args(create + ["--execute"]), settings=settings) == (
        {"result_code": "unchanged", "dry_run": False, "status": decision}, 0)
    assert await snapshot() == final
    opposite = ["resolve", *base, "--decision", "confirmed" if decision == "cleared" else "cleared",
                "--resolution-code", "basis_confirmed" if decision == "cleared" else "not_substantiated", "--execute"]
    result, exit_code = await cli.run(cli.parse_args(opposite), settings=settings)
    assert exit_code == 1 and result == {"result_code": "review_rejected"}
    assert await snapshot() == final


async def history_catalog(case):
    async with case.owner.connect() as conn:
        return [list((await conn.execute(text(sql))).mappings().all()) for sql in (
            "SELECT relname,relowner,relacl::text,relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid IN ('public.fair_use_reviews'::regclass,'public.billing_audit_events'::regclass) ORDER BY relname",
            "SELECT attrelid,attname,attacl::text FROM pg_attribute WHERE attrelid IN ('public.fair_use_reviews'::regclass,'public.billing_audit_events'::regclass) AND attnum>0 AND NOT attisdropped ORDER BY attrelid,attnum",
            "SELECT proname,pg_get_functiondef(oid),proacl::text,proowner FROM pg_proc WHERE pronamespace='public'::regnamespace AND (proname LIKE '%fair_use%' OR proname='rec_context_kind') ORDER BY proname,oid",
            "SELECT * FROM pg_policies WHERE schemaname='public' AND tablename IN ('fair_use_reviews','billing_audit_events') ORDER BY tablename,policyname",
            "SELECT tgrelid,tgname,tgenabled,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN ('public.fair_use_reviews'::regclass,'public.billing_audit_events'::regclass) ORDER BY tgrelid,tgname",
        )]


@pytest.mark.parametrize("damage", [
    "ALTER FUNCTION public.rec_append_fair_use_audit() OWNER TO twobrain_rec",
    "ALTER FUNCTION public.rec_guard_fair_use_audit() SECURITY DEFINER",
    "ALTER FUNCTION public.rec_guard_fair_use_audit() SET search_path=public,pg_temp",
    "CREATE OR REPLACE FUNCTION public.rec_context_kind() RETURNS text LANGUAGE sql STABLE AS 'SELECT NULL::text'",
    "GRANT SELECT ON public.billing_audit_events TO twobrain_rec_fair_use_audit_writer",
    "GRANT INSERT ON public.fair_use_reviews TO twobrain_rec_fair_use_audit_writer",
    "GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO twobrain_rec_fair_use_audit_writer",
    "GRANT twobrain_rec_fair_use_audit_writer TO twobrain_rec_maintenance",
    "GRANT twobrain_rec_app TO twobrain_rec_fair_use_audit_writer",
    "ALTER TABLE public.fair_use_reviews NO FORCE ROW LEVEL SECURITY",
    "DROP FUNCTION public.rec_guard_fair_use_review() CASCADE",
    "DROP FUNCTION public.rec_guard_fair_use_review(),public.rec_append_fair_use_audit(),public.rec_guard_fair_use_audit(),public.rec_guard_fair_use_truncate() CASCADE",
    "REVOKE INSERT (metadata_json) ON public.billing_audit_events FROM twobrain_rec_fair_use_audit_writer",
])
async def test_bootstrap_rejects_owner_acl_helper_and_partial_schema_drift(operator_case, damage):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    async with c.owner.begin() as conn:
        await conn.execute(text(damage))
    damaged_catalog = await history_catalog(c)
    with pytest.raises(RuntimeError, match="fair-use .* (unsafe|incomplete)"):
        await bootstrap._bootstrap()
    assert await source_snapshot(c) == before
    assert await history_catalog(c) == damaged_catalog
    async with c.app.connect() as conn:
        assert not await conn.scalar(text("SELECT has_table_privilege(current_user,'public.fair_use_reviews','INSERT,UPDATE,DELETE')"))


async def test_repeated_bootstrap_removes_runtime_and_public_function_privilege_drift(operator_case):
    c = operator_case
    await create_source(c)
    async with c.owner.begin() as conn:
        for sql in (
            "GRANT ALL ON public.fair_use_reviews TO twobrain_rec_app,twobrain_rec_maintenance,twobrain_rec_media",
            "GRANT UPDATE (reason_code),INSERT (id) ON public.fair_use_reviews TO twobrain_rec_app,twobrain_rec_media",
            "GRANT EXECUTE ON FUNCTION public.rec_append_fair_use_audit() TO PUBLIC,twobrain_rec_app,twobrain_rec_maintenance",
            "GRANT SET ON PARAMETER session_replication_role TO PUBLIC,twobrain_rec_app,twobrain_rec_maintenance",
        ):
            await conn.execute(text(sql))
    await bootstrap._bootstrap()
    await bootstrap._bootstrap()
    await c.app.dispose()
    async with c.app.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(c.ids, "a"))
        assert await conn.scalar(text("SELECT session_user=current_user AND session_user='twobrain_rec_app'"))
        for sql in (CREATE, "UPDATE public.fair_use_reviews SET reason_code='security_abuse' WHERE id=:id"):
            with pytest.raises(DBAPIError) as rejected:
                async with conn.begin_nested():
                    await conn.execute(text(sql), c.values)
            assert rejected.value.orig.sqlstate == "42501"
        assert not await conn.scalar(text("SELECT has_function_privilege(current_user,'public.rec_append_fair_use_audit()','EXECUTE') OR has_parameter_privilege(current_user,'session_replication_role','SET')"))
        await conn.execute(text("UPDATE public.fair_use_reviews SET state='appealed' WHERE id=:id"), c.values)
    await c.maintenance.dispose()
    async with c.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        await conn.execute(text("UPDATE public.fair_use_reviews SET state='cleared',resolution_code='not_substantiated' WHERE id=:id"), c.values)
    after = await source_snapshot(c)
    assert after[0]["state"] == "cleared" and len(after[1]) == 3 and after[2] == []


async def test_public_review_privilege_contamination_refuses_atomically(operator_case):
    c = operator_case
    await create_source(c)
    before = await source_snapshot(c)
    async with c.owner.begin() as conn:
        await conn.execute(text("GRANT ALL ON public.fair_use_reviews TO PUBLIC"))
        await conn.execute(text("GRANT UPDATE (reason_code),INSERT (id) ON public.fair_use_reviews TO PUBLIC"))
    contaminated = await history_catalog(c)
    # PUBLIC also grants unrelated writers access; refusing this state is intentional.
    with pytest.raises(RuntimeError, match="^receipt observation writer role is unsafe$"):
        await bootstrap._bootstrap()
    assert await history_catalog(c) == contaminated
    assert await source_snapshot(c) == before


@pytest.mark.parametrize("failure", ["audit_insert", "deferred_commit"])
async def test_audit_and_commit_errors_roll_back_actual_source_and_history(operator_case, failure):
    c = operator_case
    before = await source_snapshot(c)
    # Trusted fault injection rejects storage/commit, without weakening the guards.
    async with c.owner.begin() as conn:
        await conn.execute(text("CREATE FUNCTION public.test_only_fair_use_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic_fair_use_failure'; END $$"))
        if failure == "audit_insert":
            await conn.execute(text("CREATE TRIGGER zz_test_fair_use_failure BEFORE INSERT ON public.billing_audit_events FOR EACH ROW EXECUTE FUNCTION public.test_only_fair_use_failure()"))
        else:
            await conn.execute(text("CREATE CONSTRAINT TRIGGER zz_test_fair_use_failure AFTER INSERT ON public.fair_use_reviews DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.test_only_fair_use_failure()"))
    try:
        with pytest.raises(DBAPIError) as rejected:
            async with c.maintenance.begin() as conn:
                await apply_tenant_context_to_connection(conn, CONTEXT)
                await declare_operator(conn)
                await conn.execute(text(CREATE), c.values)
                if failure == "deferred_commit":
                    assert await conn.scalar(text("SELECT count(*) FROM public.billing_audit_events WHERE workspace_id=:workspace"), c.values) == 1
                    assert await source_snapshot(c) == before
        assert rejected.value.orig.sqlstate == "P0001"
        assert "synthetic_fair_use_failure" in str(rejected.value.orig)
        assert await source_snapshot(c) == before
    finally:
        async with c.owner.begin() as conn:
            table = "billing_audit_events" if failure == "audit_insert" else "fair_use_reviews"
            await conn.execute(text(f"DROP TRIGGER zz_test_fair_use_failure ON public.{table}"))
            await conn.execute(text("DROP FUNCTION public.test_only_fair_use_failure()"))
    await create_source(c)
    after = await source_snapshot(c)
    assert after[0]["state"] == "notice" and len(after[1]) == 1 and after[2] == []


def cli_create_arguments(case):
    return ["create", "--workspace", str(case.values["workspace"]),
            "--subject", str(case.values["subject"]), "--evidence-ref", case.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed",
            "--capability", "server_processing", "--reason", "resale"]


async def cli_snapshot(case):
    async with case.owner.connect() as conn:
        return [(await conn.execute(text(f"SELECT to_jsonb(t) FROM public.{table} t WHERE workspace_id=:workspace ORDER BY id"), case.values)).scalars().all()
                for table in ("fair_use_reviews", "billing_audit_events", "billing_notification_deliveries")]


async def prepare_cli_owner(case):
    async with case.owner.begin() as conn:
        await conn.execute(text("UPDATE workspaces SET owner_user_id=:subject WHERE id=:workspace"), case.values)


async def invoke_cli(case, argv, *, engine=None):
    from twobrain_rec_server.cli import billing_fair_use as cli

    settings = SimpleNamespace(database_url=(engine or case.maintenance).url.render_as_string(hide_password=False))
    return await cli.run(cli.parse_args(argv), settings=settings)


async def test_operator_cli_new_process_preserves_original_distinct_recipients(operator_case, tmp_path):
    c = operator_case
    original_owner, replacement_owner = uuid4(), uuid4()
    async with c.owner.begin() as conn:
        for user in (original_owner, replacement_owner):
            await conn.execute(text("INSERT INTO user_identities(id,organization_id,external_subject,status) VALUES (:user,:org,:subject,'active')"),
                               {"user": user, "org": c.ids["org_a"], "subject": "synthetic-" + user.hex})
            await conn.execute(text("INSERT INTO workspace_memberships(workspace_id,user_id,role,status) VALUES (:workspace,:user,'owner','active')"),
                               {**c.values, "user": user})
        await conn.execute(text("UPDATE workspaces SET owner_user_id=:user WHERE id=:workspace"), {**c.values, "user": original_owner})
    # Empty cwd and a minimal environment exclude the checkout's .env and real secrets.
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
           "TWOBRAIN_DATABASE_URL": c.maintenance.url.render_as_string(hide_password=False)}

    async def process(argv, expected):
        child = await asyncio.create_subprocess_exec(sys.executable, "-m", "twobrain_rec_server.cli.billing_fair_use",
                                                      *argv, env=env, cwd=tmp_path,
                                                      stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(child.communicate(), timeout=30)
        finally:
            if child.returncode is None:
                child.kill()
                await child.wait()
        assert child.returncode == 0 and stderr == b"", "operator CLI process failed safely"
        assert json.loads(stdout) == expected
        for private in (str(c.values["workspace"]), str(c.values["subject"]), c.values["evidence"], OPERATOR,
                        str(original_owner), str(replacement_owner), env["TWOBRAIN_DATABASE_URL"]):
            assert private not in stdout.decode()

    create = cli_create_arguments(c)
    await process(create, {"result_code": "validated", "dry_run": True, "status": "notice"})
    assert await cli_snapshot(c) == [[], [], []]
    await process(create + ["--execute"], {"result_code": "applied", "dry_run": False, "status": "notice"})
    first = await cli_snapshot(c)
    assert len(first[0]) == len(first[1]) == 1 and len(first[2]) == 2
    recipients = {str(c.values["subject"]), str(original_owner)}
    assert {q["recipient_id"] for q in first[2]} == recipients
    resolve = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
               "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", "cleared",
               "--resolution-code", "no_longer_applicable", "--execute"]
    await process(resolve, {"result_code": "applied", "dry_run": False, "status": "cleared"})
    final = await cli_snapshot(c)
    assert len(final[0]) == 1 and len(final[1]) == 2 and len(final[2]) == 4
    assert final[0][0]["resolved_at"] is not None
    for phase in ("notice", "cleared"):
        assert {q["recipient_id"] for q in final[2] if q["safe_payload"]["phase"] == phase} == recipients
    async with c.owner.begin() as conn:
        await conn.execute(text("UPDATE workspaces SET owner_user_id=:user WHERE id=:workspace"), {**c.values, "user": replacement_owner})
    await process(create + ["--execute"], {"result_code": "unchanged", "dry_run": False, "status": "cleared"})
    await process(resolve, {"result_code": "unchanged", "dry_run": False, "status": "cleared"})
    assert await cli_snapshot(c) == final


@pytest.mark.parametrize("login", ["app", "media", "owner"])
async def test_operator_cli_rejects_actual_other_logins_without_writes(operator_case, login):
    c = operator_case
    await prepare_cli_owner(c)
    engine = getattr(c, login, None)
    if login == "media":
        engine = create_async_engine(c.maintenance.url.set(username="twobrain_rec_media",
                                   password=bootstrap._read_secret("TWOBRAIN_DB_MEDIA_PASSWORD_FILE")))
    try:
        for execute in ([], ["--execute"]):
            assert await invoke_cli(c, cli_create_arguments(c) + execute, engine=engine) == (
                {"result_code": "database_identity_rejected"}, 1)
            assert await cli_snapshot(c) == [[], [], []]
    finally:
        if login == "media":
            await engine.dispose()


@pytest.mark.parametrize("damage", ["foreign_subject", "missing_workspace", "missing_owner", "inactive_identity",
                                      "merged_identity", "inactive_membership", "wrong_owner_role",
                                      "finalizing", "completed", "blocked"])
async def test_operator_cli_refuses_ineligible_scope_in_dry_run_and_execute(operator_case, damage):
    c = operator_case
    await prepare_cli_owner(c)
    argv = cli_create_arguments(c)
    async with c.owner.begin() as conn:
        if damage == "foreign_subject":
            argv[argv.index("--subject") + 1] = str(c.ids["user_b"])
        elif damage == "missing_workspace":
            argv[argv.index("--workspace") + 1] = str(uuid4())
        elif damage == "missing_owner":
            await conn.execute(text("UPDATE workspaces SET owner_user_id=NULL WHERE id=:workspace"), c.values)
        elif damage == "inactive_identity":
            await conn.execute(text("UPDATE user_identities SET status='closed' WHERE id=:subject"), c.values)
        elif damage == "merged_identity":
            await conn.execute(text("UPDATE user_identities SET merged_into_user_id=:other WHERE id=:subject"), {**c.values, "other": c.ids["user_b"]})
        elif damage == "inactive_membership":
            await conn.execute(text("UPDATE workspace_memberships SET status='inactive' WHERE workspace_id=:workspace AND user_id=:subject"), c.values)
        elif damage == "wrong_owner_role":
            await conn.execute(text("UPDATE workspace_memberships SET role='member' WHERE workspace_id=:workspace AND user_id=:subject"), c.values)
        else:
            await conn.execute(text("""INSERT INTO account_closure_requests
                (id,workspace_id,requested_by_user_id,request_key,state,finalize_at,metadata_json)
                VALUES (:id,:workspace,:subject,'synthetic-cli-closure',:state,now(),CAST(:metadata AS json))"""),
                               {**c.values, "state": damage, "metadata": json.dumps({"content_workspace_ids": []})})
    before = await cli_snapshot(c)
    for execute in ([], ["--execute"]):
        assert await invoke_cli(c, argv + execute) == ({"result_code": "review_rejected"}, 1)
        assert await cli_snapshot(c) == before == [[], [], []]


@pytest.mark.parametrize("locked", ["workspace", "identity", "membership", "closure"])
async def test_operator_cli_nowait_rolls_back_then_retries_after_lock_release(operator_case, locked):
    c = operator_case
    await prepare_cli_owner(c)
    if locked == "closure":
        async with c.owner.begin() as conn:
            await conn.execute(text("""INSERT INTO account_closure_requests
                (id,workspace_id,requested_by_user_id,request_key,state,finalize_at,metadata_json)
                VALUES (:id,:workspace,:subject,'synthetic-cli-lock','scheduled',now(),'{}')"""), c.values)
    sql = {"workspace": "SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE",
           "identity": "SELECT id FROM user_identities WHERE id=:subject FOR UPDATE",
           "membership": "SELECT user_id FROM workspace_memberships WHERE workspace_id=:workspace AND user_id=:subject FOR UPDATE",
           "closure": "SELECT id FROM account_closure_requests WHERE id=:id FOR UPDATE"}[locked]
    async with c.owner.connect() as holder, holder.begin():
        assert await holder.scalar(text(sql), c.values) is not None
        assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == ({"result_code": "database_unavailable"}, 1)
        assert await cli_snapshot(c) == [[], [], []]
        # A separate connection can acquire the root: failed NOWAIT released it.
        if locked != "workspace":
            async with c.owner.begin() as probe:
                assert await probe.scalar(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)
    assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == (
        {"result_code": "applied", "dry_run": False, "status": "notice"}, 0)
    after = await cli_snapshot(c)
    assert len(after[0]) == len(after[1]) == len(after[2]) == 1


@pytest.mark.parametrize("failure", ["queue", "audit", "commit"])
async def test_operator_cli_database_fault_rolls_back_source_audit_and_queue(operator_case, failure):
    c = operator_case
    await prepare_cli_owner(c)
    table = {"queue": "billing_notification_deliveries", "audit": "billing_audit_events", "commit": "fair_use_reviews"}[failure]
    async with c.owner.begin() as conn:
        await conn.execute(text("CREATE FUNCTION public.test_only_cli_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic_cli_failure'; END $$"))
        if failure == "commit":
            await conn.execute(text(f"CREATE CONSTRAINT TRIGGER zz_test_cli_failure AFTER INSERT ON public.{table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.test_only_cli_failure()"))
        else:
            await conn.execute(text(f"CREATE TRIGGER zz_test_cli_failure BEFORE INSERT ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.test_only_cli_failure()"))
    try:
        assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == ({"result_code": "database_unavailable"}, 1)
        assert await cli_snapshot(c) == [[], [], []]
    finally:
        async with c.owner.begin() as conn:
            await conn.execute(text(f"DROP TRIGGER zz_test_cli_failure ON public.{table}"))
            await conn.execute(text("DROP FUNCTION public.test_only_cli_failure()"))
    assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == (
        {"result_code": "applied", "dry_run": False, "status": "notice"}, 0)
    after = await cli_snapshot(c)
    assert len(after[0]) == len(after[1]) == len(after[2]) == 1


@pytest.mark.parametrize("command", ["create", "resolve"])
@pytest.mark.parametrize("conflicting", [False, True])
async def test_operator_cli_competing_intents_preserve_one_committed_transition(operator_case, monkeypatch, command, conflicting):
    from twobrain_rec_server.cli import billing_fair_use as cli

    c = operator_case
    await prepare_cli_owner(c)
    create = cli_create_arguments(c) + ["--execute"]
    if command == "create":
        first_argv = create
        helper_name = "create_operator_review"
    else:
        assert await invoke_cli(c, create) == ({"result_code": "applied", "dry_run": False, "status": "notice"}, 0)
        first_argv = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
                      "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", "cleared",
                      "--resolution-code", "not_substantiated", "--execute"]
        helper_name = "resolve_persisted_review"
    competitor = first_argv.copy()
    if conflicting:
        if command == "create":
            competitor[competitor.index("--reason") + 1] = "security_abuse"
        else:
            competitor[competitor.index("--decision") + 1] = "confirmed"
            competitor[competitor.index("--resolution-code") + 1] = "basis_confirmed"
    before = await cli_snapshot(c)
    entered, release = asyncio.Event(), asyncio.Event()
    actual_helper = getattr(cli, helper_name)

    async def hold_before_commit(*args, **kwargs):
        # Execute the actual producer; only delay its return before CLI commit.
        result = await actual_helper(*args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(cli, helper_name, hold_before_commit)
    first = asyncio.create_task(invoke_cli(c, first_argv))
    try:
        await asyncio.wait_for(entered.wait(), timeout=10)
        assert await cli_snapshot(c) == before
        assert await asyncio.wait_for(invoke_cli(c, competitor), timeout=10) == ({"result_code": "database_unavailable"}, 1)
        assert await cli_snapshot(c) == before
    finally:
        release.set()
        first_result = await asyncio.wait_for(first, timeout=10)
    state = "notice" if command == "create" else "cleared"
    assert first_result == ({"result_code": "applied", "dry_run": False, "status": state}, 0)
    committed = await cli_snapshot(c)
    count = 1 if command == "create" else 2
    assert len(committed[0]) == 1 and len(committed[1]) == len(committed[2]) == count
    expected = ({"result_code": "review_rejected"}, 1) if conflicting else (
        {"result_code": "unchanged", "dry_run": False, "status": state}, 0)
    assert await invoke_cli(c, competitor) == expected
    assert await cli_snapshot(c) == committed


@pytest.mark.parametrize("command", ["create", "resolve"])
@pytest.mark.parametrize("dates", ["finite", "future", "infinity", "-infinity"])
async def test_operator_cli_legacy_dates_preserve_history_without_backfill(
    operator_case, operator_migrations, command, dates,
):
    c = operator_case
    await prepare_cli_owner(c)
    await operator_migrations("downgrade", "0112_storage_notifications")
    # Actual pre-0113 history, without disabling protection or fabricating audit.
    start = {
        "finite": "transaction_timestamp() - interval '2 days'",
        "future": "transaction_timestamp() + interval '1 day'",
        "infinity": "'infinity'::timestamptz",
        "-infinity": "'-infinity'::timestamptz",
    }[dates]
    async with c.owner.begin() as conn:
        await conn.execute(text(f"""
            INSERT INTO public.fair_use_reviews
                (id,workspace_id,subject_user_id,capability,reason_code,evidence_ref,
                 starts_at,review_by,state)
            VALUES (:id,:workspace,:subject,'server_processing','resale',:evidence,
                    {start},({start}) + interval '24 hours','notice')
        """), c.values)
        assert await conn.scalar(text("SELECT isfinite(starts_at) AND isfinite(review_by) FROM fair_use_reviews WHERE id=:id"), c.values) is (dates in {"finite", "future"})
    before = await cli_snapshot(c)
    assert len(before[0]) == 1 and before[1:] == [[], []]
    await operator_migrations("upgrade", "head")
    assert await cli_snapshot(c) == before
    await bootstrap._bootstrap()
    argv = cli_create_arguments(c) if command == "create" else [
        "resolve", "--workspace", str(c.values["workspace"]),
        "--evidence-ref", c.values["evidence"], "--operator-ref", OPERATOR,
        "--evidence-reviewed", "--decision", "cleared", "--resolution-code", "not_substantiated",
    ]
    observed, expected = [], []
    for execute in (False, True):
        expected.append(({"result_code": "validated" if not execute else "unchanged",
                          "dry_run": not execute, "status": "notice"}, 0) if (
            dates == "finite" and command == "create"
        ) else ({"result_code": "review_rejected"}, 1))
        observed.append(await invoke_cli(c, argv + (["--execute"] if execute else [])))
        assert await cli_snapshot(c) == before
    assert observed == expected


async def test_operator_cli_legacy_appeal_resolution_dates_refuse_contradictions(
    operator_case, operator_migrations,
):
    c = operator_case
    await prepare_cli_owner(c)
    await operator_migrations("downgrade", "0112_storage_notifications")
    cases = {
        "appeal_late_valid": ("appealed", "base + interval '2 days'", "NULL", True),
        "resolution_late_valid": ("cleared", "base + interval '2 days'", "base + interval '3 days'", True),
        "appeal_before_start": ("appealed", "base - interval '1 minute'", "NULL", False),
        "appeal_future": ("appealed", "transaction_timestamp() + interval '1 day'", "NULL", False),
        "appeal_infinity": ("appealed", "'infinity'::timestamptz", "NULL", False),
        "appeal_negative_infinity": ("appealed", "'-infinity'::timestamptz", "NULL", False),
        "resolution_before_start": ("cleared", "NULL", "base - interval '1 minute'", False),
        "resolution_future": ("cleared", "NULL", "transaction_timestamp() + interval '1 day'", False),
        "resolution_infinity": ("cleared", "NULL", "'infinity'::timestamptz", False),
        "resolution_negative_infinity": ("cleared", "NULL", "'-infinity'::timestamptz", False),
        "resolution_before_appeal": ("cleared", "base + interval '2 days'", "base + interval '1 day'", False),
    }
    async with c.owner.begin() as conn:
        for name, (state, appealed, resolved, _) in cases.items():
            await conn.execute(text(f"""
                WITH times AS (SELECT CAST(:start AS timestamptz) AS base)
                INSERT INTO public.fair_use_reviews
                    (id,workspace_id,subject_user_id,capability,reason_code,evidence_ref,
                     starts_at,review_by,state,appealed_at,appeal_ref,resolved_at,resolution_code)
                SELECT :id,:workspace,:subject,'server_processing','resale',:evidence,
                       base,base + interval '24 hours',:state,{appealed},
                       CASE WHEN {appealed} IS NULL THEN NULL ELSE 'appeal:legacy' END,
                       {resolved},:resolution
                FROM times
            """), {**c.values, "id": uuid4(), "evidence": "legacy:" + name, "state": state,
                   "resolution": "not_substantiated" if state == "cleared" else None})
    before = await cli_snapshot(c)
    assert len(before[0]) == 11 and before[1:] == [[], []]
    await operator_migrations("upgrade", "head")
    assert await cli_snapshot(c) == before
    await bootstrap._bootstrap()
    observed, expected = {}, {}
    for name, (state, _, _, valid) in cases.items():
        argv = cli_create_arguments(c)
        argv[argv.index("--evidence-ref") + 1] = "legacy:" + name
        for execute in (False, True):
            key = (name, execute)
            observed[key] = await invoke_cli(c, argv + (["--execute"] if execute else []))
            expected[key] = ({"result_code": "validated" if not execute else "unchanged",
                              "dry_run": not execute, "status": state}, 0) if valid else (
                {"result_code": "review_rejected"}, 1)
            assert await cli_snapshot(c) == before
    assert observed == expected
@pytest.fixture
async def cabinet_case(operator_case, request):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from twobrain_rec_server.api.problems import ProblemDetail, problem_exception_handler
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
    from twobrain_rec_server.auth.sessions import hash_token
    from twobrain_rec_server.cabinet.web_routes.fair_use import router

    c = operator_case
    history = getattr(request, "param", "subject")
    await prepare_cli_owner(c)
    if history == "distinct_owner":
        owner = uuid4()
        async with c.owner.begin() as conn:
            await conn.execute(text("INSERT INTO user_identities(id,organization_id,external_subject) VALUES (:owner,:org_a,:external)"),
                               {**c.ids, "owner": owner, "external": "synthetic-" + owner.hex})
            await conn.execute(text("INSERT INTO workspace_memberships(workspace_id,user_id,role,status) VALUES (:workspace_a,:owner,'owner','active')"),
                               {**c.ids, "owner": owner})
            await conn.execute(text("UPDATE workspaces SET owner_user_id=:owner WHERE id=:workspace_a"), {**c.ids, "owner": owner})
    else:
        owner = c.ids["user_a"]
    assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == (
        {"result_code": "applied", "dry_run": False, "status": "notice"}, 0,
    )
    before = await cli_snapshot(c)
    review_id = before[0][0]["id"]
    token = "synthetic-fair-use-session-" + uuid4().hex
    async with c.owner.begin() as conn:
        if history == "lineage":
            await conn.execute(text("UPDATE user_identities SET organization_id=:org_a WHERE id=:user_b"), c.ids)
            await conn.execute(text("UPDATE user_identities SET status='merged',merged_into_user_id=:user_b,merged_at=now() WHERE id=:user_a"), c.ids)
            await conn.execute(text("UPDATE workspaces SET owner_user_id=:user_b,kind='linked' WHERE id=:workspace_a"), c.ids)
            await conn.execute(text("UPDATE workspaces SET organization_id=:org_a,owner_user_id=:user_b WHERE id=:workspace_b"), c.ids)
            await conn.execute(text("UPDATE workspace_memberships SET user_id=:user_b WHERE workspace_id=:workspace_a AND user_id=:user_a"), c.ids)
            actor, workspace, device, owner = c.ids["user_b"], c.ids["workspace_b"], c.ids["device_b"], c.ids["user_b"]
        else:
            actor, workspace, device = c.ids["user_a"], c.ids["workspace_a"], c.ids["device_a"]
        await conn.execute(text("UPDATE auth_sessions SET session_token_hash=:hash,user_id=:actor,workspace_id=:workspace,device_id=:device WHERE id=:session_a"),
                           {**c.ids, "hash": hash_token(token), "actor": actor, "workspace": workspace, "device": device})
        await conn.execute(text("""
            INSERT INTO auth_session_device_bindings
                (id,auth_session_id,registered_device_id,device_state)
            VALUES (:id,:session_a,:device,'trusted')
        """), {**c.ids, "id": uuid4(), "device": device})
    assert await cli_snapshot(c) == before
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(ProblemDetail, problem_exception_handler)
    app.state.db_sessionmaker = async_sessionmaker(c.app, expire_on_commit=False)
    app.state.web_csrf_secret = uuid4().hex
    app.state.settings = SimpleNamespace(
        env="production", legacy_header_auth_enabled=False,
        web_login_workspace_id=uuid4(), billing_support_email=None,
    )
    csrf = issue_csrf_token(session_id=c.ids["session_a"], secret=app.state.web_csrf_secret)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://synthetic.invalid",
                           cookies={AUTH_SESSION_COOKIE_NAME: token}) as client:
        yield SimpleNamespace(case=c, client=client, csrf=csrf, review_id=review_id, before=before,
                              actor=actor, workspace=workspace, recipients=sorted({str(c.ids["user_a"]), str(owner)}))


@pytest.mark.parametrize("base", ["/account/fair-use", "/desktop/account/fair-use"])
@pytest.mark.parametrize("cabinet_case", ["subject", "distinct_owner", "lineage"], indirect=True)
async def test_cabinet_first_appeal_uses_db_time_and_atomic_queue(cabinet_case, base):
    x = cabinet_case
    c, before = x.case, x.before
    path = f"{base}/{x.review_id}/appeal"
    for form, code in [({}, "csrf_token_missing"), ({"csrf_token": "invalid"}, "csrf_token_invalid")]:
        rejected = await x.client.post(path, data=form)
        assert rejected.status_code == 403 and rejected.json()["code"] == code
        assert await cli_snapshot(c) == before
    first = await x.client.post(path, data={"csrf_token": x.csrf})
    after = await cli_snapshot(c)
    repeat = await x.client.post(path, data={"csrf_token": x.csrf})
    assert await cli_snapshot(c) == after
    assert first.status_code == repeat.status_code == 303
    assert after[0][0]["state"] == "appealed"
    assert after[0][0]["starts_at"] == before[0][0]["starts_at"]
    assert after[0][0]["review_by"] == before[0][0]["review_by"]
    appeals = [a for a in after[1] if a["action"] == "fair_use.review.appealed"]
    assert len(appeals) == 1 and appeals[0]["created_at"] == after[0][0]["appealed_at"]
    assert appeals[0]["actor_user_id"] == str(x.actor)
    assert appeals[0]["metadata_json"]["source"] == "request"
    assert {
        "first": first.headers["location"], "repeat": repeat.headers["location"],
        "appeal_recipients": sorted(q["recipient_id"] for q in after[2] if q["safe_payload"].get("phase") == "appealed"),
        "queue_count": len(after[2]),
    } == {
        "first": f"{base}?result=appealed", "repeat": f"{base}?result=already_appealed",
        "appeal_recipients": x.recipients, "queue_count": len(before[2]) + len(x.recipients),
    }


@pytest.mark.parametrize("failure", ["queue", "audit", "commit"])
async def test_cabinet_appeal_rolls_back_source_audit_queue_and_refuses_success(cabinet_case, failure):
    x = cabinet_case
    c = x.case
    table, timing = {
        "queue": ("billing_notification_deliveries", "BEFORE INSERT"),
        "audit": ("billing_audit_events", "BEFORE INSERT"),
        "commit": ("fair_use_reviews", "AFTER UPDATE"),
    }[failure]
    deferred = "CONSTRAINT" if failure == "commit" else ""
    delay = "DEFERRABLE INITIALLY DEFERRED" if failure == "commit" else ""
    async with c.owner.begin() as conn:
        await conn.execute(text("CREATE FUNCTION public.test_only_appeal_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic_appeal_failure'; END $$"))
        await conn.execute(text(f"CREATE {deferred} TRIGGER zz_test_appeal_failure {timing} ON public.{table} {delay} FOR EACH ROW EXECUTE FUNCTION public.test_only_appeal_failure()"))
    path = f"/account/fair-use/{x.review_id}/appeal"
    try:
        rejected = await x.client.post(path, data={"csrf_token": x.csrf})
        assert rejected.status_code == 303 and rejected.headers["location"] == "/account/fair-use?result=unavailable"
        assert await cli_snapshot(c) == x.before
    finally:
        async with c.owner.begin() as conn:
            await conn.execute(text(f"DROP TRIGGER zz_test_appeal_failure ON public.{table}"))
            await conn.execute(text("DROP FUNCTION public.test_only_appeal_failure()"))
    applied = await x.client.post(path, data={"csrf_token": x.csrf})
    assert applied.headers["location"] == "/account/fair-use?result=appealed"
    after = await cli_snapshot(c)
    assert after[0][0]["state"] == "appealed" and len(after[1]) == len(after[2]) == 2


@pytest.mark.parametrize("cabinet_case", ["lineage"], indirect=True)
@pytest.mark.parametrize("failure", [False, True])
async def test_lineage_appeal_restores_exact_request_context_after_success_and_sql_error(cabinet_case, failure):
    from twobrain_rec_server.billing.fair_use import appeal_persisted_review
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext

    x = cabinet_case
    c = x.case
    if failure:
        async with c.owner.begin() as conn:
            await conn.execute(text("CREATE FUNCTION public.test_only_context_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic_context_failure'; END $$"))
            await conn.execute(text("CREATE TRIGGER zz_test_context_failure BEFORE INSERT ON public.billing_notification_deliveries FOR EACH ROW EXECUTE FUNCTION public.test_only_context_failure()"))
    try:
        async with async_sessionmaker(c.app, expire_on_commit=False)() as db:
            await apply_tenant_context(db, TenantDatabaseContext(
                organization_id=c.ids["org_a"], workspace_id=x.workspace, user_id=x.actor,
                device_id=c.ids["device_b"], auth_session_id=c.ids["session_a"],
            ))
            original = dict(db.info["tenant_context"])
            if failure:
                with pytest.raises(DBAPIError):
                    await appeal_persisted_review(db, review_id=x.review_id, subject_user_id=x.actor)
                assert await cli_snapshot(c) == x.before
            else:
                row, changed = await appeal_persisted_review(db, review_id=x.review_id, subject_user_id=x.actor)
                assert changed and row.workspace_id == c.ids["workspace_a"] and row.state == "appealed"
                assert await cli_snapshot(c) == x.before
            assert db.info["tenant_context"] == original
            assert (await db.execute(text("SELECT current_setting('app.workspace_id'),current_setting('app.user_id'),current_setting('app.context_kind'),session_user,current_user"))).one() == (
                str(x.workspace), str(x.actor), "request", "twobrain_rec_app", "twobrain_rec_app",
            )
            await db.rollback() if failure else await db.commit()
    finally:
        if failure:
            async with c.owner.begin() as conn:
                await conn.execute(text("DROP TRIGGER zz_test_context_failure ON public.billing_notification_deliveries"))
                await conn.execute(text("DROP FUNCTION public.test_only_context_failure()"))
    if not failure:
        after = await cli_snapshot(c)
        assert after[0][0]["state"] == "appealed" and len(after[1]) == 2 and len(after[2]) == 3
        assert sorted(q["recipient_id"] for q in after[2] if q["safe_payload"]["phase"] == "appealed") == x.recipients


async def test_cabinet_appeal_root_lock_refuses_without_partial_changes_then_retries(cabinet_case):
    x = cabinet_case
    c = x.case
    path = f"/account/fair-use/{x.review_id}/appeal"
    async with c.owner.begin() as holder:
        await holder.execute(text("SELECT id FROM public.workspaces WHERE id=:workspace FOR UPDATE"), c.values)
        rejected = await asyncio.wait_for(x.client.post(path, data={"csrf_token": x.csrf}), timeout=5)
        assert rejected.status_code == 303 and rejected.headers["location"] == "/account/fair-use?result=unavailable"
        assert await cli_snapshot(c) == x.before
    applied = await x.client.post(path, data={"csrf_token": x.csrf})
    assert applied.status_code == 303 and applied.headers["location"] == "/account/fair-use?result=appealed"
    after = await cli_snapshot(c)
    assert after[0][0]["state"] == "appealed" and len(after[1]) == len(after[2]) == 2


@pytest.mark.parametrize("decision,code", [("cleared", "not_substantiated"), ("confirmed", "basis_confirmed")])
@pytest.mark.parametrize("base", ["/account/fair-use", "/desktop/account/fair-use"])
async def test_cabinet_terminal_appeal_preserves_entire_committed_history(cabinet_case, decision, code, base):
    x = cabinet_case
    c = x.case
    argv = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", decision,
            "--resolution-code", code, "--execute"]
    assert await invoke_cli(c, argv) == ({"result_code": "applied", "dry_run": False, "status": decision}, 0)
    before = await cli_snapshot(c)
    assert before[0][0]["state"] == decision and len(before[1]) == len(before[2]) == 2
    for _ in range(2):
        result = await x.client.post(f"{base}/{x.review_id}/appeal", data={"csrf_token": x.csrf})
        assert result.status_code == 303 and result.headers["location"] == f"{base}?result=unavailable"
        assert await cli_snapshot(c) == before


@pytest.mark.parametrize("target", ["malformed", "missing", "foreign"])
async def test_cabinet_appeal_rejects_unavailable_source_without_changes(cabinet_case, target):
    x = cabinet_case
    c = x.case
    review_id = "invalid" if target == "malformed" else str(uuid4()) if target == "missing" else x.review_id
    if target == "foreign":
        async with c.owner.begin() as conn:
            await conn.execute(text("UPDATE auth_sessions SET user_id=:user_b,workspace_id=:workspace_b,device_id=:device_b WHERE id=:session_a"), c.ids)
            await conn.execute(text("UPDATE auth_session_device_bindings SET registered_device_id=:device_b WHERE auth_session_id=:session_a"), c.ids)
    result = await x.client.post(f"/account/fair-use/{review_id}/appeal", data={"csrf_token": x.csrf})
    assert result.status_code == 303 and result.headers["location"] == "/account/fair-use?result=unavailable"
    assert await cli_snapshot(c) == x.before


@pytest.mark.parametrize("locked", ["identity", "membership", "closure"])
async def test_cabinet_appeal_member_lock_rolls_back_root_then_retries(cabinet_case, locked):
    x = cabinet_case
    c = x.case
    if locked == "closure":
        async with c.owner.begin() as conn:
            await conn.execute(text("""INSERT INTO account_closure_requests
                (id,workspace_id,requested_by_user_id,request_key,state,finalize_at,metadata_json)
                VALUES (:id,:workspace,:subject,'synthetic-appeal-lock','scheduled',now(),'{}')"""), c.values)
    sql = {"identity": "SELECT id FROM user_identities WHERE id=:subject FOR UPDATE",
           "membership": "SELECT user_id FROM workspace_memberships WHERE workspace_id=:workspace AND user_id=:subject FOR UPDATE",
           "closure": "SELECT id FROM account_closure_requests WHERE id=:id FOR UPDATE"}[locked]
    path = f"/account/fair-use/{x.review_id}/appeal"
    async with c.owner.begin() as holder:
        assert await holder.scalar(text(sql), c.values) is not None
        result = await asyncio.wait_for(x.client.post(path, data={"csrf_token": x.csrf}), timeout=5)
        assert result.status_code == 303 and result.headers["location"] == "/account/fair-use?result=unavailable"
        assert await cli_snapshot(c) == x.before
        async with c.owner.begin() as probe:
            assert await probe.scalar(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)
    result = await x.client.post(path, data={"csrf_token": x.csrf})
    assert result.status_code == 303 and result.headers["location"] == "/account/fair-use?result=appealed"
    after = await cli_snapshot(c)
    assert after[0][0]["state"] == "appealed" and len(after[1]) == len(after[2]) == 2


@pytest.mark.parametrize("state", ["finalizing", "completed", "blocked"])
async def test_cabinet_appeal_refuses_account_finalization_without_changes(cabinet_case, state):
    x = cabinet_case
    c = x.case
    async with c.owner.begin() as conn:
        await conn.execute(text("""INSERT INTO account_closure_requests
            (id,workspace_id,requested_by_user_id,request_key,state,finalize_at,metadata_json)
            VALUES (:id,:workspace,:subject,'synthetic-appeal-close',:state,now(),CAST(:metadata AS json))"""),
                           {**c.values, "state": state, "metadata": json.dumps({"content_workspace_ids": []})})
    result = await x.client.post(f"/account/fair-use/{x.review_id}/appeal", data={"csrf_token": x.csrf})
    assert result.status_code == 303 and result.headers["location"] == "/account/fair-use?result=unavailable"
    assert await cli_snapshot(c) == x.before


@pytest.mark.parametrize("competitor", ["appeal", "resolve"])
async def test_cabinet_concurrent_appeal_preserves_one_transition_before_retry(cabinet_case, monkeypatch, competitor):
    from twobrain_rec_server.cabinet.web_routes import fair_use as routes

    x = cabinet_case
    c = x.case
    entered, release = asyncio.Event(), asyncio.Event()
    actual = routes.appeal_persisted_review

    async def hold_before_commit(*args, **kwargs):
        result = await actual(*args, **kwargs)
        if result[1]:
            entered.set()
            await release.wait()
        return result

    monkeypatch.setattr(routes, "appeal_persisted_review", hold_before_commit)
    path = f"/account/fair-use/{x.review_id}/appeal"
    argv = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", "cleared",
            "--resolution-code", "not_substantiated", "--execute"]
    first = asyncio.create_task(x.client.post(path, data={"csrf_token": x.csrf}))
    try:
        await asyncio.wait_for(entered.wait(), timeout=10)
        assert await cli_snapshot(c) == x.before
        if competitor == "appeal":
            rejected = await asyncio.wait_for(x.client.post(path, data={"csrf_token": x.csrf}), timeout=5)
            assert rejected.status_code == 303 and rejected.headers["location"] == "/account/fair-use?result=unavailable"
        else:
            assert await asyncio.wait_for(invoke_cli(c, argv), timeout=5) == ({"result_code": "database_unavailable"}, 1)
        assert await cli_snapshot(c) == x.before
    finally:
        release.set()
        applied = await asyncio.wait_for(first, timeout=10)
    assert applied.status_code == 303 and applied.headers["location"] == "/account/fair-use?result=appealed"
    committed = await cli_snapshot(c)
    assert committed[0][0]["state"] == "appealed" and len(committed[1]) == len(committed[2]) == 2
    if competitor == "appeal":
        repeated = await x.client.post(path, data={"csrf_token": x.csrf})
        assert repeated.headers["location"] == "/account/fair-use?result=already_appealed"
        assert await cli_snapshot(c) == committed
    else:
        assert await invoke_cli(c, argv) == ({"result_code": "applied", "dry_run": False, "status": "cleared"}, 0)
        resolved = await cli_snapshot(c)
        assert resolved[0][0]["state"] == "cleared" and len(resolved[1]) == len(resolved[2]) == 3
        assert resolved[0][0]["appealed_at"] == committed[0][0]["appealed_at"]
        assert resolved[0][0]["review_by"] == committed[0][0]["review_by"]


@pytest.mark.parametrize("lost", [None, "closed", "email"])
async def test_operator_cabinet_resolution_sender_rechecks_recipient(cabinet_case, monkeypatch, lost):
    from uuid import UUID

    from twobrain_rec_server.workflows import worker

    x, calls, claims = cabinet_case, [], []
    c = x.case
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
            VALUES (:id,:subject,'email',:provider,'original@example.test',true,true)
        """), {**c.values, "id": uuid4(), "provider": uuid4().hex})
        await conn.execute(text("""
            INSERT INTO billing_notification_preferences(user_id,optional_email_enabled)
            VALUES (:subject,false)
        """), c.values)
    appealed = await x.client.post(f"/account/fair-use/{x.review_id}/appeal", data={"csrf_token": x.csrf})
    assert appealed.status_code == 303 and appealed.headers["location"].endswith("?result=appealed")
    argv = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", "cleared",
            "--resolution-code", "not_substantiated", "--execute"]
    assert await invoke_cli(c, argv) == ({"result_code": "applied", "dry_run": False, "status": "cleared"}, 0)
    committed = await cli_snapshot(c)
    assert len(committed[0]) == 1 and len(committed[1]) == len(committed[2]) == 3
    assert {row["safe_payload"]["phase"] for row in committed[2]} == {"notice", "appealed", "cleared"}
    async with c.owner.begin() as conn:
        if lost == "closed":
            await conn.execute(text("UPDATE user_identities SET status='closed' WHERE id=:subject"), c.values)
        elif lost == "email":
            await conn.execute(text("UPDATE external_identities SET is_active=false WHERE user_id=:subject"), c.values)

    async def send(**kwargs):
        calls.append(kwargs)
        # A new transaction must see the durable claim before any transport call.
        async with c.owner.begin() as conn:
            claim = (await conn.execute(text("""
                SELECT state,last_error_code,attempts FROM billing_notification_deliveries WHERE id=:id
            """), {"id": UUID(kwargs["delivery_key"].partition(":")[2])})).one()
            claims.append(tuple(claim))
            await conn.execute(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)

    async def stop(_seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "create_engine", lambda _: c.maintenance)
    monkeypatch.setattr(worker, "send_billing_notification", send)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(SimpleNamespace(
                billing_support_email=None, public_base_url="https://graf.example.test"))
    after = await cli_snapshot(c)
    assert after[:2] == committed[:2]
    if lost is not None:
        assert calls == []
        assert {row["state"] for row in after[2]} == {"suppressed"}
        assert {row["attempts"] for row in after[2]} == {0}
    else:
        assert len(calls) == len({row["delivery_key"] for row in calls}) == 3
        assert claims == [("failed", "postal_outcome_unknown", 1)] * 3
        assert {row["state"] for row in after[2]} == {"delivered"}
        for call in calls:
            assert call["recipient_email"] == "original@example.test"
            content = call["subject"] + call["plain_body"] + call["html_body"]
            assert "https://graf.example.test/account/fair-use" in content
            for private in (str(x.review_id), c.values["evidence"], OPERATOR, "fair_use_review_id"):
                assert private not in content


@pytest.fixture
async def fair_use_sender_case(cabinet_case, monkeypatch):
    from twobrain_rec_server.workflows import worker

    c = cabinet_case.case
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
            VALUES (:id,:subject,'email',:provider,'original@example.test',true,true)
        """), {**c.values, "id": uuid4(), "provider": uuid4().hex})
    state = SimpleNamespace(case=c, cabinet=cabinet_case, calls=[], failure=None, now=datetime.now(UTC))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return state.now.astimezone(tz) if tz else state.now.replace(tzinfo=None)

    async def send(**kwargs):
        state.calls.append(kwargs)
        if state.failure is not None:
            raise state.failure

    async def stop(_seconds):
        raise asyncio.CancelledError

    async def dispatch():
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(SimpleNamespace(
                billing_support_email=None, public_base_url="https://graf.example.test"))

    state.dispatch = dispatch
    monkeypatch.setattr(worker, "create_engine", lambda _: c.maintenance)
    monkeypatch.setattr(worker, "send_billing_notification", send)
    monkeypatch.setattr(worker, "datetime", Clock)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    return state


@pytest.mark.parametrize("lost", [
    "membership", "merged", "unverified", "empty_email", "source", "phase", "capability",
    "deadline", "event", "unrecorded_result", "phase_type", "payload_type",
])
async def test_fair_use_sender_suppresses_unavailable_source_or_original_rights(fair_use_sender_case, lost):
    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    async with c.owner.begin() as conn:
        if lost == "membership":
            await conn.execute(text("UPDATE workspace_memberships SET status='removed' WHERE user_id=:subject AND workspace_id=:workspace"), c.values)
        elif lost == "merged":
            await conn.execute(text("UPDATE user_identities SET status='merged',merged_into_user_id=:user_b,merged_at=now() WHERE id=:user_a"), c.ids)
        elif lost == "unverified":
            await conn.execute(text("UPDATE external_identities SET is_verified=false WHERE user_id=:subject"), c.values)
        elif lost == "empty_email":
            await conn.execute(text("UPDATE external_identities SET email='' WHERE user_id=:subject"), c.values)
        else:
            payload, event = deepcopy(before[2][0]["safe_payload"]), before[2][0]["event_id"]
            if lost == "source":
                missing = uuid4()
                payload["fair_use_review_id"], event = str(missing), f"fair_use.review:{missing.hex}:notice"
            elif lost == "phase":
                payload["phase"] = "unconfirmed"
            elif lost == "capability":
                payload["capability"] = "storage"
            elif lost == "deadline":
                payload["review_by"] = "01.01.2020 12:00"
            elif lost == "event":
                event = "fair_use.review:unbound"
            elif lost == "unrecorded_result":
                payload["phase"], event = "confirmed", f"fair_use.review:{x.cabinet.review_id.replace('-', '')}:confirmed"
            elif lost == "phase_type":
                payload["phase"] = []
            else:
                payload = ["unbound"]
            await conn.execute(text("UPDATE billing_notification_deliveries SET safe_payload=CAST(:payload AS json),event_id=:event WHERE workspace_id=:workspace"),
                               {**c.values, "payload": json.dumps(payload), "event": event})
    await x.dispatch()
    after = await cli_snapshot(c)
    assert after[:2] == before[:2] and x.calls == []
    assert len(after[2]) == 1 and after[2][0]["state"] == "suppressed"
    assert after[2][0]["attempts"] == 0


@pytest.mark.parametrize("outcome", ["known_retry", "unknown", "read_error"])
async def test_fair_use_sender_preserves_bounded_delay_and_unknown_policy(fair_use_sender_case, monkeypatch, outcome):
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
    from twobrain_rec_server.workflows import worker

    x, reads = fair_use_sender_case, []
    c = x.case
    before = await cli_snapshot(c)
    real_recipient = worker.fair_use_notice_recipient

    async def unavailable(db, delivery):
        await real_recipient(db, delivery)
        reads.append(True)
        # A genuine SQL read error rolls back the claim and its held locks.
        await db.execute(text("SELECT 1/0"))

    if outcome == "read_error":
        monkeypatch.setattr(worker, "fair_use_notice_recipient", unavailable)
    else:
        x.failure = EmailLoginDeliveryError("synthetic", retryable=True, outcome_unknown=outcome == "unknown")
    await x.dispatch()
    first = await cli_snapshot(c)
    assert first[:2] == before[:2]
    row = first[2][0]
    assert row["attempts"] == 1
    if outcome == "unknown":
        assert row["state"] == "failed" and row["last_error_code"] == "postal_outcome_unknown"
        x.now += timedelta(days=1)
        await x.dispatch()
        assert await cli_snapshot(c) == first and len(x.calls) == 1
        return
    assert row["state"] == "retry"
    due = row["safe_payload"]["_retry_not_before"]
    assert type(due) is int and due >= x.now.timestamp() + 60
    await x.dispatch()
    x.now = datetime.fromtimestamp(due - 1, UTC)
    await x.dispatch()
    assert await cli_snapshot(c) == first
    assert len(reads) == (1 if outcome == "read_error" else 0)
    assert len(x.calls) == (1 if outcome == "known_retry" else 0)
    for attempt in range(2, 6):
        x.now = datetime.fromtimestamp(due, UTC)
        await x.dispatch()
        after = await cli_snapshot(c)
        row = after[2][0]
        assert after[:2] == before[:2] and row["attempts"] == attempt
        assert row["state"] == ("retry" if attempt < 5 else "failed")
        due = row["safe_payload"]["_retry_not_before"]
        if attempt < 5:
            assert due >= x.now.timestamp() + 60
    final = await cli_snapshot(c)
    x.now += timedelta(days=1)
    await x.dispatch()
    assert await cli_snapshot(c) == final
    assert len(reads) == (5 if outcome == "read_error" else 0)
    assert len(x.calls) == (5 if outcome == "known_retry" else 0)


async def test_fair_use_confirmed_source_reaches_sender_once(fair_use_sender_case):
    x = fair_use_sender_case
    c = x.case
    response = await x.cabinet.client.post(f"/account/fair-use/{x.cabinet.review_id}/appeal",
                                          data={"csrf_token": x.cabinet.csrf})
    assert response.headers["location"].endswith("?result=appealed")
    argv = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
            "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", "confirmed",
            "--resolution-code", "basis_confirmed", "--execute"]
    assert await invoke_cli(c, argv) == ({"result_code": "applied", "dry_run": False, "status": "confirmed"}, 0)
    before = await cli_snapshot(c)
    await x.dispatch()
    await x.dispatch()
    after = await cli_snapshot(c)
    assert after[:2] == before[:2] and len(x.calls) == 3
    assert {row["safe_payload"]["phase"] for row in after[2]} == {"notice", "appealed", "confirmed"}
    assert {row["state"] for row in after[2]} == {"delivered"}
    assert len({call["delivery_key"] for call in x.calls}) == 3
    results = [call for call in x.calls if "Основание подтверждено по результатам рассмотрения." in call["plain_body"]]
    assert len(results) == 1 and "не подтверждает фактическое включение или снятие ограничения" in results[0]["plain_body"]


@pytest.mark.parametrize("cabinet_case", ["distinct_owner"], indirect=True)
@pytest.mark.parametrize("change", ["keep", "switch", "unlink"])
async def test_fair_use_sender_keeps_original_distinct_owner(fair_use_sender_case, change):
    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    owner = next(row["recipient_id"] for row in before[2] if row["recipient_id"] != str(c.values["subject"]))
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
            VALUES (:id,CAST(:owner AS uuid),'email',:provider,'owner@example.test',true,true)
        """), {"id": uuid4(), "owner": owner, "provider": uuid4().hex})
        if change == "switch":
            # The replacement owner is eligible but has no row in this old event.
            await conn.execute(text("UPDATE user_identities SET organization_id=:org_a WHERE id=:user_b"), c.ids)
            await conn.execute(text("INSERT INTO workspace_memberships(workspace_id,user_id,role,status) VALUES (:workspace_a,:user_b,'owner','active')"), c.ids)
            await conn.execute(text("UPDATE workspaces SET owner_user_id=:user_b WHERE id=:workspace_a"), c.ids)
            await conn.execute(text("""
                INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
                VALUES (:id,:user_b,'email',:provider,'replacement@example.test',true,true)
            """), {**c.ids, "id": uuid4(), "provider": uuid4().hex})
        elif change == "unlink":
            await conn.execute(text("DELETE FROM workspace_memberships WHERE workspace_id=:workspace AND user_id=CAST(:owner AS uuid)"),
                               {**c.values, "owner": owner})
    await x.dispatch()
    await x.dispatch()
    after = await cli_snapshot(c)
    assert after[:2] == before[:2]
    assert {row["recipient_id"] for row in after[2]} == {row["recipient_id"] for row in before[2]}
    assert {call["recipient_email"] for call in x.calls} == (
        {"original@example.test", "owner@example.test"} if change == "keep" else {"original@example.test"})
    by_recipient = {row["recipient_id"]: row for row in after[2]}
    assert by_recipient[str(c.values["subject"])]["state"] == "delivered"
    assert by_recipient[owner]["state"] == ("delivered" if change == "keep" else "suppressed")


@pytest.mark.parametrize("change", ["closed", "membership", "email_lost", "email_changed"])
async def test_fair_use_claim_rechecks_changes_after_selection(fair_use_sender_case, monkeypatch, change):
    from twobrain_rec_server.workflows import worker

    x, checks = fair_use_sender_case, []
    c = x.case
    before = await cli_snapshot(c)
    real_recipient = worker.fair_use_notice_recipient

    async def change_after_poll(db, delivery):
        checks.append(True)
        async with c.owner.begin() as conn:
            statement = {
                "closed": "UPDATE user_identities SET status='closed' WHERE id=:subject",
                "membership": "UPDATE workspace_memberships SET status='removed' WHERE user_id=:subject AND workspace_id=:workspace",
                "email_lost": "UPDATE external_identities SET is_active=false WHERE user_id=:subject",
                "email_changed": "UPDATE external_identities SET email='current@example.test' WHERE user_id=:subject",
            }[change]
            await conn.execute(text(statement), c.values)
        return await real_recipient(db, delivery)

    monkeypatch.setattr(worker, "fair_use_notice_recipient", change_after_poll)
    await x.dispatch()
    after = await cli_snapshot(c)
    assert checks == [True] and after[:2] == before[:2]
    assert after[2][0]["state"] == ("delivered" if change == "email_changed" else "suppressed")
    assert [call["recipient_email"] for call in x.calls] == (["current@example.test"] if change == "email_changed" else [])


async def test_fair_use_claim_rechecks_due_after_poll(fair_use_sender_case, monkeypatch):
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
    from twobrain_rec_server.workflows import worker

    x, checks = fair_use_sender_case, []
    x.failure = EmailLoginDeliveryError("synthetic", retryable=True, outcome_unknown=False)
    await x.dispatch()
    first = await cli_snapshot(x.case)
    due = first[2][0]["safe_payload"]["_retry_not_before"]
    x.now = datetime.fromtimestamp(due, UTC)
    real_recipient = worker.fair_use_notice_recipient

    async def earlier_claim_clock(db, delivery):
        result = await real_recipient(db, delivery)
        checks.append(True)
        x.now = datetime.fromtimestamp(due - 1, UTC)
        return result

    monkeypatch.setattr(worker, "fair_use_notice_recipient", earlier_claim_clock)
    await x.dispatch()
    assert checks == [True] and await cli_snapshot(x.case) == first and len(x.calls) == 1
    monkeypatch.setattr(worker, "fair_use_notice_recipient", real_recipient)
    x.failure, x.now = None, datetime.fromtimestamp(due, UTC)
    await x.dispatch()
    final = await cli_snapshot(x.case)
    assert final[:2] == first[:2] and final[2][0]["state"] == "delivered"
    assert final[2][0]["attempts"] == 2 and len(x.calls) == 2


@pytest.mark.parametrize("outcome", ["rejected", "ack_lost"])
async def test_fair_use_claim_commit_failure_never_calls_transport(fair_use_sender_case, monkeypatch, outcome):
    from sqlalchemy.ext.asyncio import AsyncSession

    from twobrain_rec_server.db.models import BillingNotificationDelivery
    from twobrain_rec_server.workflows import worker

    x, faults = fair_use_sender_case, []
    c = x.case
    before = await cli_snapshot(c)
    if outcome == "rejected":
        async with c.owner.begin() as conn:
            await conn.execute(text("""
                CREATE FUNCTION public.test_only_fair_use_claim_failure() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.template_key='fair_use_review' AND NEW.state='failed'
                       AND NEW.last_error_code='postal_outcome_unknown' THEN
                        RAISE EXCEPTION 'synthetic_fair_use_claim_failure';
                    END IF;
                    RETURN NEW;
                END $$
            """))
            await conn.execute(text("""
                CREATE CONSTRAINT TRIGGER zz_test_fair_use_claim_failure AFTER UPDATE
                ON public.billing_notification_deliveries DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION public.test_only_fair_use_claim_failure()
            """))
    else:
        class MissingAckSession(AsyncSession):
            async def commit(self):
                claim = any(isinstance(item, BillingNotificationDelivery) and item.state == "failed"
                            and item.last_error_code == "postal_outcome_unknown" for item in self.dirty)
                await super().commit()
                if claim and not faults:
                    faults.append(True)
                    # The real COMMIT succeeded; only its acknowledgement is withheld.
                    raise DBAPIError(None, None, Exception("synthetic_commit_ack_lost"), connection_invalidated=True)

        monkeypatch.setattr(worker, "create_sessionmaker", lambda engine: async_sessionmaker(
            engine, class_=MissingAckSession, expire_on_commit=False))
    try:
        await x.dispatch()
    finally:
        if outcome == "rejected":
            async with c.owner.begin() as conn:
                await conn.execute(text("DROP TRIGGER zz_test_fair_use_claim_failure ON public.billing_notification_deliveries"))
                await conn.execute(text("DROP FUNCTION public.test_only_fair_use_claim_failure()"))
    after = await cli_snapshot(c)
    assert after[:2] == before[:2] and x.calls == []
    assert after[2][0]["attempts"] == 1
    if outcome == "ack_lost":
        assert faults == [True] and after[2][0]["state"] == "failed"
        assert after[2][0]["last_error_code"] == "postal_outcome_unknown"
        x.now += timedelta(days=1)
        await x.dispatch()
        assert await cli_snapshot(c) == after and x.calls == []
    else:
        assert after[2][0]["state"] == "retry"
        x.now = datetime.fromtimestamp(after[2][0]["safe_payload"]["_retry_not_before"], UTC)
        await x.dispatch()
        final = await cli_snapshot(c)
        assert final[:2] == before[:2] and final[2][0]["state"] == "delivered"
        assert final[2][0]["attempts"] == 2 and len(x.calls) == 1


@pytest.mark.parametrize("pause", ["before_claim", "after_claim"])
async def test_fair_use_concurrent_senders_never_duplicate_transport(fair_use_sender_case, monkeypatch, pause):
    from twobrain_rec_server.workflows import worker

    x = fair_use_sender_case
    before = await cli_snapshot(x.case)
    entered, release = asyncio.Event(), asyncio.Event()
    real_recipient = worker.fair_use_notice_recipient
    blocked = False

    async def held_recipient(db, delivery):
        nonlocal blocked
        result = await real_recipient(db, delivery)
        if not blocked:
            blocked = True
            entered.set()
            await release.wait()
        return result

    async def held_transport(**kwargs):
        x.calls.append(kwargs)
        entered.set()
        await release.wait()

    monkeypatch.setattr(worker, "fair_use_notice_recipient", held_recipient if pause == "before_claim" else real_recipient)
    if pause == "after_claim":
        monkeypatch.setattr(worker, "send_billing_notification", held_transport)
    first = asyncio.create_task(x.dispatch())
    try:
        await asyncio.wait_for(entered.wait(), timeout=10)
        await asyncio.wait_for(x.dispatch(), timeout=5)
        mid = await cli_snapshot(x.case)
        assert mid[:2] == before[:2]
        assert len(x.calls) == (0 if pause == "before_claim" else 1)
        assert mid[2][0]["state"] == ("retry" if pause == "before_claim" else "failed")
    finally:
        release.set()
        await asyncio.wait_for(first, timeout=10)
    if pause == "before_claim":
        x.now = datetime.fromtimestamp(mid[2][0]["safe_payload"]["_retry_not_before"], UTC)
        await x.dispatch()
    await x.dispatch()
    final = await cli_snapshot(x.case)
    assert final[:2] == before[:2] and final[2][0]["state"] == "delivered"
    assert len(x.calls) == 1


async def test_fair_use_unbound_old_queue_is_suppressed_without_backfill(fair_use_sender_case):
    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    legacy = {key: value for key, value in before[2][0]["safe_payload"].items()
              if key not in {"phase", "fair_use_review_id"}}
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            UPDATE billing_notification_deliveries SET event_id='fair_use.review:legacy:review:opaque',
                safe_payload=CAST(:payload AS json) WHERE workspace_id=:workspace
        """), {**c.values, "payload": json.dumps(legacy)})
    await x.dispatch()
    await x.dispatch()
    after = await cli_snapshot(c)
    assert after[:2] == before[:2] and x.calls == []
    assert after[2][0]["safe_payload"] == legacy and after[2][0]["state"] == "suppressed"
    assert after[2][0]["attempts"] == 0


@pytest.fixture
async def fair_use_cleanup_case(operator_case, monkeypatch):
    from sqlalchemy import event

    from scripts import cleanup_smoke_artifacts as cleanup
    from scripts.seed_smoke_identity import seed_identity
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.deployment import build_smoke_identity_seed

    c = operator_case
    run_id = "fair-use-smoke-" + uuid4().hex
    seed = build_smoke_identity_seed(run_id)
    settings = Settings(database_url=c.maintenance.url.render_as_string(hide_password=False))
    assert (await seed_identity(settings, run_id, execute=True))["seed_result"] == "pass"
    values = {**c.values, "workspace": seed.workspace_id, "subject": seed.user_id}
    scoped = SimpleNamespace(owner=c.owner, maintenance=c.maintenance, values=values)
    x = SimpleNamespace(case=scoped, original=c, run_id=run_id, seed=seed, settings=settings,
                        statements=[], storage=[], read_failure=None, faults=[], server_settings={})

    def engine_factory(url):
        engine = create_async_engine(url, connect_args={"server_settings": x.server_settings})

        def capture(_conn, _cursor, statement, parameters, _context, _many):
            x.statements.append(statement)
            if (x.read_failure and statement.lstrip().lower().startswith("select")
                    and f"public.{x.read_failure}" in statement):
                x.faults.append(True)
                return "SELECT 1/0", ()
            return statement, parameters

        event.listen(engine.sync_engine, "before_cursor_execute", capture, retval=True)
        return engine

    class SyntheticStorage:
        def list_objects(self, _bucket, *, prefix, recursive):
            assert prefix.endswith(f"workspaces/{seed.workspace_id}/") and recursive
            x.storage.append("list")
            return [SimpleNamespace(object_name=prefix + "synthetic")] if "remove" not in x.storage else []

        def remove_object(self, _bucket, _name):
            x.storage.append("remove")

    monkeypatch.setattr(cleanup, "Settings", lambda: x.settings)
    monkeypatch.setattr(cleanup, "create_async_engine", engine_factory)
    monkeypatch.setattr(cleanup, "Minio", lambda *_a, **_kw: SyntheticStorage())
    x.cleanup = lambda: cleanup.cleanup_smoke_artifacts(run_id)

    async def snapshot():
        async with c.owner.connect() as conn:
            return [(await conn.execute(text(f"SELECT to_jsonb(t) FROM public.{table} t ORDER BY 1"))).scalars().all()
                    for table in ("organizations", "workspaces", "user_identities", "registered_devices",
                                  "workspace_memberships", "fair_use_reviews", "billing_audit_events",
                                  "billing_notification_deliveries")]

    x.snapshot = snapshot
    return x


@pytest.mark.parametrize("history", ["source", "legacy", "audit_action", "audit_target", "read_review", "read_audit", "none", "other_scope"])
async def test_fair_use_cleanup_preflight_preserves_history_before_any_mutation(fair_use_cleanup_case, history):
    x = fair_use_cleanup_case
    c = x.case
    if history in {"source", "other_scope"}:
        source = c if history == "source" else x.original
        await prepare_cli_owner(source)
        argv = ["create", "--workspace", str(source.values["workspace"]), "--subject", str(source.values["subject"]),
                "--capability", "server_processing", "--reason", "resale", "--evidence-ref", source.values["evidence"],
                "--operator-ref", OPERATOR, "--evidence-reviewed", "--execute"]
        assert await invoke_cli(source, argv) == ({"result_code": "applied", "dry_run": False, "status": "notice"}, 0)
    elif history == "legacy":
        # Trusted historical setup has no canonical audit; runtime cannot use this bypass.
        async with c.owner.begin() as conn:
            await conn.execute(text("ALTER TABLE fair_use_reviews DISABLE TRIGGER fair_use_review_guard"))
            await conn.execute(text("ALTER TABLE fair_use_reviews DISABLE TRIGGER fair_use_audit_append"))
            await conn.execute(text(CREATE), c.values)
            await conn.execute(text("ALTER TABLE fair_use_reviews ENABLE ALWAYS TRIGGER fair_use_review_guard"))
            await conn.execute(text("ALTER TABLE fair_use_reviews ENABLE ALWAYS TRIGGER fair_use_audit_append"))
    elif history in {"audit_action", "audit_target"}:
        # Negative legacy shape: either reserved namespace must stop cleanup without a review.
        async with c.owner.begin() as conn:
            await conn.execute(text("ALTER TABLE billing_audit_events DISABLE TRIGGER fair_use_audit_guard"))
            await conn.execute(text("""
                INSERT INTO billing_audit_events(id,workspace_id,action,target_kind,outcome,metadata_json)
                VALUES (:id,:workspace,:action,:target,'applied','{}')
            """), {**c.values, "action": "fair_use.legacy" if history == "audit_action" else "ordinary",
                   "target": "other" if history == "audit_action" else "fair_use_review"})
            await conn.execute(text("ALTER TABLE billing_audit_events ENABLE ALWAYS TRIGGER fair_use_audit_guard"))
    elif history.startswith("read_"):
        x.read_failure = "fair_use_reviews" if history == "read_review" else "billing_audit_events"
    before = await x.snapshot()
    result = await x.cleanup()
    if history in {"none", "other_scope"}:
        assert result == (5, 1, []) and x.storage == ["list", "remove", "list"]
        after = await x.snapshot()
        assert after[5:] == before[5:]
        for index in range(5):
            assert len(after[index]) == len(before[index]) - 1
        assert not any("delete from fair_use_reviews" in sql.lower() for sql in x.statements)
    else:
        assert result == (0, 0, ["protected_fair_use_history"])
        assert await x.snapshot() == before and x.storage == []
        assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)
        assert x.faults == ([True] if history.startswith("read_") else [])


@pytest.mark.parametrize("authority", ["app", "owner", "set_role", "row_security", "operation", "feature", "actor", "reason"])
async def test_fair_use_cleanup_requires_actual_login_and_exact_context(fair_use_cleanup_case, monkeypatch, authority):
    from dataclasses import replace

    from scripts import cleanup_smoke_artifacts as cleanup

    x = fair_use_cleanup_case
    if authority in {"app", "owner", "set_role"}:
        engine = x.original.app if authority == "app" else x.original.owner
        x.settings = x.settings.model_copy(update={"database_url": engine.url.render_as_string(hide_password=False)})
    if authority in {"operation", "feature", "actor", "reason"}:
        ctx = cleanup._maintenance_context()
        changes = {"operation": {"operation_name": "migration_verification"},
                   "feature": {"feature_area": "billing"}, "actor": {"actor_id": "other"},
                   "reason": {"reason_category": "other"}}[authority]
        monkeypatch.setattr(cleanup, "_maintenance_context", lambda: replace(ctx, **changes))
    if authority in {"set_role", "row_security"}:
        original = cleanup._preflight_fair_use_history

        async def change_connection(conn, identity):
            await conn.execute(text("SET LOCAL ROLE twobrain_rec_maintenance" if authority == "set_role" else "SET LOCAL row_security=off"))
            await original(conn, identity)

        monkeypatch.setattr(cleanup, "_preflight_fair_use_history", change_connection)
    before = await x.snapshot()
    assert await x.cleanup() == (0, 0, ["protected_fair_use_history"])
    assert await x.snapshot() == before and x.storage == []
    assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)


@pytest.mark.parametrize("first", ["source", "cleanup"])
async def test_fair_use_cleanup_root_serializes_concurrent_source(fair_use_cleanup_case, monkeypatch, first):
    from scripts import cleanup_smoke_artifacts as cleanup

    x = fair_use_cleanup_case
    c = x.case
    entered, release = asyncio.Event(), asyncio.Event()
    pids = []
    original = cleanup._preflight_fair_use_history

    async def held_preflight(conn, identity):
        pids.append(await conn.scalar(text("SELECT pg_backend_pid()")))
        if first == "source":
            entered.set()
        await original(conn, identity)
        if first == "cleanup":
            entered.set()
            await release.wait()

    monkeypatch.setattr(cleanup, "_preflight_fair_use_history", held_preflight)

    async def wait_for_blocked(pid):
        async with c.owner.connect() as probe:
            for _ in range(100):
                if await probe.scalar(text("SELECT cardinality(pg_blocking_pids(:pid))>0"), {"pid": pid}):
                    return
                await asyncio.sleep(0.02)
        raise AssertionError("expected a real PostgreSQL lock wait")

    before = await x.snapshot()
    if first == "source":
        async with c.maintenance.begin() as source:
            await apply_tenant_context_to_connection(source, CONTEXT)
            await declare_operator(source)
            await source.execute(text(CREATE), c.values)
            task = asyncio.create_task(x.cleanup())
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                await asyncio.wait_for(wait_for_blocked(pids[0]), timeout=5)
                assert not task.done() and await x.snapshot() == before and x.storage == []
            finally:
                await source.commit()
        result = await asyncio.wait_for(task, timeout=10)
        assert result == (0, 0, ["protected_fair_use_history"]) and x.storage == []
        after = await x.snapshot()
        assert after[:5] == before[:5] and len(after[5]) == len(after[6]) == 1 and after[7] == []
        assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)
    else:
        task = asyncio.create_task(x.cleanup())
        source_task = None
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            assert await x.snapshot() == before and x.storage == []
            async with c.maintenance.begin() as source:
                await apply_tenant_context_to_connection(source, CONTEXT)
                await declare_operator(source)
                pid = await source.scalar(text("SELECT pg_backend_pid()"))
                source_task = asyncio.create_task(source.execute(text(CREATE), c.values))
                await asyncio.wait_for(wait_for_blocked(pid), timeout=5)
                assert not source_task.done()
                release.set()
                assert await asyncio.wait_for(task, timeout=10) == (5, 1, [])
                with pytest.raises(DBAPIError) as rejected:
                    await asyncio.wait_for(source_task, timeout=5)
                assert rejected.value.orig.sqlstate == "23503"
                await source.rollback()
        finally:
            release.set()
            await asyncio.wait_for(task, timeout=10)
            if source_task is not None and not source_task.done():
                await asyncio.wait_for(source_task, timeout=5)
        after = await x.snapshot()
        assert after[5:] == before[5:]
        assert x.storage == ["list", "remove", "list"]


async def test_fair_use_cleanup_refuses_concurrent_foreign_workspace_subject(fair_use_cleanup_case):
    x = fair_use_cleanup_case
    c = x.case
    before = await x.snapshot()
    # The same subject can be referenced from a different workspace under DB authority.
    foreign = {**c.values, "workspace": x.original.values["workspace"]}
    async with c.maintenance.begin() as source:
        await apply_tenant_context_to_connection(source, CONTEXT)
        await declare_operator(source)
        await source.execute(text(CREATE), foreign)
        assert await x.snapshot() == before
        assert await asyncio.wait_for(x.cleanup(), timeout=3) == (0, 0, ["protected_fair_use_history"])
        assert await x.snapshot() == before and x.storage == []
        async with c.owner.begin() as probe:
            assert await probe.scalar(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)
    committed = await x.snapshot()
    assert committed[:5] == before[:5] and len(committed[5]) == len(committed[6]) == 1
    assert await x.cleanup() == (0, 0, ["protected_fair_use_history"])
    assert await x.snapshot() == committed and x.storage == []
    assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)


@pytest.mark.parametrize("isolation", ["repeatable read", "serializable"])
async def test_fair_use_cleanup_refuses_inherited_snapshot_isolation(fair_use_cleanup_case, monkeypatch, isolation):
    from scripts import cleanup_smoke_artifacts as cleanup

    x = fair_use_cleanup_case
    c = x.case
    x.server_settings = {"default_transaction_isolation": isolation}
    entered, release = asyncio.Event(), asyncio.Event()
    original = cleanup._preflight_fair_use_history

    async def observed_preflight(conn, identity):
        actual = (await conn.execute(text("""
            SELECT current_setting('default_transaction_isolation'),
                   current_setting('transaction_isolation'), session_user, current_user,
                   rolsuper, rolbypassrls, current_setting('row_security')
            FROM pg_roles WHERE rolname=current_user
        """))).one()
        assert tuple(actual) == (isolation, isolation, "twobrain_rec_maintenance",
                                 "twobrain_rec_maintenance", False, False, "on")
        assert not await conn.scalar(text("SELECT EXISTS (SELECT 1 FROM fair_use_reviews WHERE workspace_id=:workspace)"), c.values)
        entered.set()
        await release.wait()
        await original(conn, identity)

    monkeypatch.setattr(cleanup, "_preflight_fair_use_history", observed_preflight)
    before = await x.snapshot()
    task = None
    try:
        async with c.maintenance.begin() as source:
            await apply_tenant_context_to_connection(source, CONTEXT)
            await declare_operator(source)
            await source.execute(text(CREATE), c.values)
            task = asyncio.create_task(x.cleanup())
            await asyncio.wait_for(entered.wait(), timeout=5)
            assert await x.snapshot() == before and x.storage == []
        # The source commits after cleanup's inherited snapshot, before its root lock.
        release.set()
        try:
            result = await asyncio.wait_for(task, timeout=10)
        except DBAPIError as error:
            result = ("database_error", error.orig.sqlstate)
        after = await x.snapshot()
        assert after[:5] == before[:5] and len(after[5]) == len(after[6]) == 1 and after[7] == []
        assert x.storage == []
        assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)
        assert result == (0, 0, ["protected_fair_use_history"])
        async with c.owner.begin() as probe:
            assert await probe.scalar(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)
            assert await probe.scalar(text("SELECT id FROM user_identities WHERE id=:subject FOR UPDATE NOWAIT"), c.values)
    finally:
        release.set()
        if task is not None:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("cabinet_case", ["distinct_owner"], indirect=True)
@pytest.mark.parametrize("decision,code", [("cleared", "not_substantiated"), ("confirmed", "basis_confirmed")])
@pytest.mark.parametrize("change_owner", [False, True])
async def test_fair_use_distinct_owner_full_chain_preserves_phase_recipients(fair_use_sender_case, monkeypatch, decision, code, change_owner):
    from uuid import UUID

    from twobrain_rec_server.workflows import worker

    x = fair_use_sender_case
    c = x.case
    subject = str(c.values["subject"])
    initial = await cli_snapshot(c)
    original_owner = next(row["recipient_id"] for row in initial[2] if row["recipient_id"] != subject)
    current_owner = str(c.ids["user_b"]) if change_owner else original_owner
    emails = {subject: "original@example.test", original_owner: "owner@example.test"}
    async with c.owner.begin() as conn:
        if change_owner:
            await conn.execute(text("UPDATE user_identities SET organization_id=:org_a WHERE id=:user_b"), c.ids)
            await conn.execute(text("INSERT INTO workspace_memberships(workspace_id,user_id,role,status) VALUES (:workspace_a,:user_b,'owner','active')"), c.ids)
            await conn.execute(text("UPDATE workspaces SET owner_user_id=:user_b WHERE id=:workspace_a"), c.ids)
            emails[current_owner] = "replacement@example.test"
        for recipient, email in emails.items():
            if recipient != subject:
                await conn.execute(text("""
                    INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
                    VALUES (:id,CAST(:recipient AS uuid),'email',:provider,:email,true,true)
                """), {"id": uuid4(), "recipient": recipient, "provider": uuid4().hex, "email": email})
            await conn.execute(text("INSERT INTO billing_notification_preferences(user_id,optional_email_enabled) VALUES (CAST(:recipient AS uuid),false)"),
                               {"recipient": recipient})
    assert await cli_snapshot(c) == initial
    claims = []
    transport = worker.send_billing_notification

    async def observe_claim(**kwargs):
        async with c.owner.begin() as conn:
            claim = (await conn.execute(text("""
                SELECT state,last_error_code,attempts,recipient_id,safe_payload
                FROM billing_notification_deliveries WHERE id=:id
            """), {"id": UUID(kwargs["delivery_key"].partition(":")[2])})).one()
            assert tuple(claim[:3]) == ("failed", "postal_outcome_unknown", 1)
            assert kwargs["recipient_email"] == emails[str(claim.recipient_id)]
            assert await conn.scalar(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)
            claims.append((str(claim.recipient_id), claim.safe_payload["phase"]))
        await transport(**kwargs)

    monkeypatch.setattr(worker, "send_billing_notification", observe_claim)

    async def check_phase(phase, count, recipients):
        committed = await cli_snapshot(c)
        assert len(committed[0]) == 1 and len(committed[1]) == count and len(committed[2]) == 2 * count
        assert committed[0][0]["starts_at"] == initial[0][0]["starts_at"]
        assert committed[0][0]["review_by"] == initial[0][0]["review_by"]
        assert {row["recipient_id"] for row in committed[2] if row["safe_payload"]["phase"] == phase} == recipients
        await x.dispatch()
        after = await cli_snapshot(c)
        await x.dispatch()
        assert await cli_snapshot(c) == after and after[:2] == committed[:2]
        for row in after[2]:
            suppressed = change_owner and row["safe_payload"]["phase"] == "notice" and row["recipient_id"] == original_owner
            assert row["state"] == ("suppressed" if suppressed else "delivered")
            assert row["attempts"] == (0 if suppressed else 1)
        assert len(x.calls) == len({call["delivery_key"] for call in x.calls}) == 2 * count - int(change_owner)

    await check_phase("notice", 1, {subject, original_owner})
    for result in ("appealed", "already_appealed"):
        response = await x.cabinet.client.post(f"/account/fair-use/{x.cabinet.review_id}/appeal", data={"csrf_token": x.cabinet.csrf})
        assert response.status_code == 303 and response.headers["location"].endswith("?result=" + result)
    await check_phase("appealed", 2, {subject, current_owner})
    resolve = ["resolve", "--workspace", str(c.values["workspace"]), "--evidence-ref", c.values["evidence"],
               "--operator-ref", OPERATOR, "--evidence-reviewed", "--decision", decision, "--resolution-code", code, "--execute"]
    assert await invoke_cli(c, resolve) == ({"result_code": "applied", "dry_run": False, "status": decision}, 0)
    terminal = await cli_snapshot(c)
    assert terminal[0][0]["state"] == decision and terminal[0][0]["resolved_at"] is not None
    assert await invoke_cli(c, resolve) == ({"result_code": "unchanged", "dry_run": False, "status": decision}, 0)
    assert await invoke_cli(c, cli_create_arguments(c) + ["--execute"]) == ({"result_code": "unchanged", "dry_run": False, "status": decision}, 0)
    response = await x.cabinet.client.post(f"/account/fair-use/{x.cabinet.review_id}/appeal", data={"csrf_token": x.cabinet.csrf})
    assert response.status_code == 303 and response.headers["location"].endswith("?result=unavailable")
    assert await cli_snapshot(c) == terminal
    await check_phase(decision, 3, {subject, current_owner})
    expected = {(subject, phase) for phase in ("notice", "appealed", decision)}
    expected |= {(current_owner, phase) for phase in ("appealed", decision)}
    if not change_owner:
        expected.add((original_owner, "notice"))
    assert set(claims) == expected and len(claims) == len(expected)
    for call in x.calls:
        content = call["subject"] + call["plain_body"] + call["html_body"]
        assert "https://graf.example.test/account/fair-use" in content
        for private in (*emails, x.cabinet.review_id, c.values["evidence"], OPERATOR, "fair_use_review_id"):
            assert private not in content


@pytest.mark.parametrize("held", ["workspace", "review", "identity", "membership", "email"])
async def test_fair_use_sender_retries_genuine_held_row_locks(fair_use_sender_case, held):
    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    statement = {
        "workspace": "SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE",
        "review": "SELECT id FROM fair_use_reviews WHERE workspace_id=:workspace AND subject_user_id=:subject FOR UPDATE",
        "identity": "SELECT id FROM user_identities WHERE id=:subject FOR UPDATE",
        "membership": "SELECT user_id FROM workspace_memberships WHERE workspace_id=:workspace AND user_id=:subject FOR UPDATE",
        "email": "SELECT id FROM external_identities WHERE user_id=:subject AND provider='email' FOR UPDATE",
    }[held]
    async with c.maintenance.begin() as holder:
        await apply_tenant_context_to_connection(holder, CONTEXT)
        assert (await holder.execute(text(statement), c.values)).one()
        await asyncio.wait_for(x.dispatch(), timeout=3)
        blocked = await cli_snapshot(c)
        assert blocked[:2] == before[:2] and x.calls == []
        row = blocked[2][0]
        assert row["state"] == "retry" and row["attempts"] == 1
        assert row["last_error_code"] == "fair_use_authorization_unavailable"
        due = row["safe_payload"]["_retry_not_before"]
        assert type(due) is int and due >= x.now.timestamp() + 60
    await x.dispatch()
    assert await cli_snapshot(c) == blocked and x.calls == []
    x.now = datetime.fromtimestamp(due, UTC)
    await x.dispatch()
    delivered = await cli_snapshot(c)
    assert delivered[:2] == before[:2] and len(x.calls) == 1
    assert delivered[2][0]["state"] == "delivered" and delivered[2][0]["attempts"] == 2
    assert x.calls[0]["recipient_email"] == "original@example.test"
    await x.dispatch()
    assert await cli_snapshot(c) == delivered and len(x.calls) == 1


@pytest.mark.parametrize("outcome", ["rejected", "ack_lost"])
async def test_fair_use_final_save_failure_never_repeats_transport(fair_use_sender_case, monkeypatch, outcome):
    from sqlalchemy.ext.asyncio import AsyncSession

    from twobrain_rec_server.db.models import BillingNotificationDelivery
    from twobrain_rec_server.workflows import worker

    x, faults, claims = fair_use_sender_case, [], []
    c = x.case
    before = await cli_snapshot(c)

    async def send(**kwargs):
        x.calls.append(kwargs)
        async with c.owner.begin() as conn:
            claim = (await conn.execute(text("""
                SELECT state,last_error_code,attempts FROM billing_notification_deliveries
                WHERE workspace_id=:workspace
            """), c.values)).one()
            claims.append(tuple(claim))
            await conn.execute(text("SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE NOWAIT"), c.values)

    monkeypatch.setattr(worker, "send_billing_notification", send)
    if outcome == "rejected":
        async with c.owner.begin() as conn:
            await conn.execute(text("""
                CREATE FUNCTION public.test_only_fair_use_final_save_failure() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.template_key='fair_use_review' AND NEW.state='delivered' THEN
                        RAISE EXCEPTION 'synthetic_fair_use_final_save_failure';
                    END IF;
                    RETURN NEW;
                END $$
            """))
            await conn.execute(text("""
                CREATE CONSTRAINT TRIGGER zz_test_fair_use_final_save_failure AFTER UPDATE
                ON public.billing_notification_deliveries DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION public.test_only_fair_use_final_save_failure()
            """))
    else:
        class MissingAckSession(AsyncSession):
            async def commit(self):
                delivered = any(isinstance(item, BillingNotificationDelivery) and item.state == "delivered"
                                for item in self.dirty)
                await super().commit()
                if delivered and not faults:
                    faults.append(True)
                    # The real final COMMIT succeeded; only its acknowledgement is withheld.
                    raise DBAPIError(None, None, Exception("synthetic_final_save_ack_lost"), connection_invalidated=True)

        monkeypatch.setattr(worker, "create_sessionmaker", lambda engine: async_sessionmaker(
            engine, class_=MissingAckSession, expire_on_commit=False))
    try:
        await x.dispatch()
    finally:
        if outcome == "rejected":
            async with c.owner.begin() as conn:
                await conn.execute(text("DROP TRIGGER zz_test_fair_use_final_save_failure ON public.billing_notification_deliveries"))
                await conn.execute(text("DROP FUNCTION public.test_only_fair_use_final_save_failure()"))
    after = await cli_snapshot(c)
    assert after[:2] == before[:2]
    assert claims == [("failed", "postal_outcome_unknown", 1)] and len(x.calls) == 1
    row = after[2][0]
    assert row["attempts"] == 1
    if outcome == "rejected":
        assert faults == [] and row["state"] == "failed"
        assert row["last_error_code"] == "postal_outcome_unknown" and row["delivered_at"] is None
    else:
        assert faults == [True] and row["state"] == "delivered"
        assert row["last_error_code"] is None and row["delivered_at"] == x.now.isoformat()
    x.now += timedelta(days=1)
    await x.dispatch()
    assert await cli_snapshot(c) == after and len(x.calls) == 1


@pytest.mark.parametrize("changed", ["template", "channel"])
async def test_fair_use_claim_refuses_changed_queue_delivery_kind(fair_use_sender_case, monkeypatch, changed):
    from twobrain_rec_server.workflows import worker

    x, mutations = fair_use_sender_case, []
    c = x.case
    before = await cli_snapshot(c)
    real_recipient = worker.fair_use_notice_recipient

    async def change_after_source_check(db, delivery):
        recipient = await real_recipient(db, delivery)
        async with c.owner.begin() as conn:
            statement = (
                "UPDATE billing_notification_deliveries SET template_key='trial_started' WHERE workspace_id=:workspace"
                if changed == "template" else
                "UPDATE billing_notification_deliveries SET channel='in_app' WHERE workspace_id=:workspace"
            )
            await conn.execute(text(statement), c.values)
        mutations.append(await cli_snapshot(c))
        return recipient

    monkeypatch.setattr(worker, "fair_use_notice_recipient", change_after_source_check)
    await x.dispatch()
    assert len(mutations) == 1 and mutations[0][:2] == before[:2]
    assert await cli_snapshot(c) == mutations[0] and x.calls == []
    assert mutations[0][2][0]["state"] == "pending" and mutations[0][2][0]["attempts"] == 0
    monkeypatch.setattr(worker, "fair_use_notice_recipient", real_recipient)
    async with c.owner.begin() as conn:
        await conn.execute(text("""
            UPDATE billing_notification_deliveries SET template_key='fair_use_review',channel='email'
            WHERE workspace_id=:workspace
        """), c.values)
    assert await cli_snapshot(c) == before
    await x.dispatch()
    delivered = await cli_snapshot(c)
    assert delivered[:2] == before[:2] and len(x.calls) == 1
    assert delivered[2][0]["state"] == "delivered" and delivered[2][0]["attempts"] == 1
    await x.dispatch()
    assert await cli_snapshot(c) == delivered and len(x.calls) == 1


@pytest.mark.parametrize("due", [None, True, "0", 0.5, -1, 9223372036854775808, {}, []])
async def test_fair_use_sender_suppresses_invalid_retry_metadata(fair_use_sender_case, due):
    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    payload = {**before[2][0]["safe_payload"], "_retry_not_before": due}
    async with c.owner.begin() as conn:
        await conn.execute(text("UPDATE billing_notification_deliveries SET safe_payload=CAST(:payload AS json) WHERE workspace_id=:workspace"),
                           {**c.values, "payload": json.dumps(payload)})
    await x.dispatch()
    after = await cli_snapshot(c)
    assert after[:2] == before[:2] and x.calls == []
    assert len(after[2]) == 1 and after[2][0]["safe_payload"] == payload
    assert after[2][0]["state"] == "suppressed" and after[2][0]["attempts"] == 0
    assert after[2][0]["last_error_code"] == "fair_use_snapshot_invalid"
    await x.dispatch()
    assert await cli_snapshot(c) == after and x.calls == []


async def test_fair_use_claim_refuses_changed_payload(fair_use_sender_case, monkeypatch):
    from twobrain_rec_server.workflows import worker

    x = fair_use_sender_case
    c = x.case
    before = await cli_snapshot(c)
    original = worker.fair_use_notice_recipient
    mutations = []

    async def change_after_source_check(db, delivery):
        recipient = await original(db, delivery)
        async with c.owner.begin() as conn:
            payload = {**delivery.safe_payload, "reason": "security_abuse"}
            await conn.execute(text("UPDATE billing_notification_deliveries SET safe_payload=CAST(:payload AS json) WHERE id=:id"),
                               {"id": delivery.id, "payload": json.dumps(payload)})
        mutations.append(await cli_snapshot(c))
        return recipient

    monkeypatch.setattr(worker, "fair_use_notice_recipient", change_after_source_check)
    await x.dispatch()
    assert len(mutations) == 1 and mutations[0][:2] == before[:2]
    assert await cli_snapshot(c) == mutations[0] and x.calls == []
    assert mutations[0][2][0]["state"] == "pending" and mutations[0][2][0]["attempts"] == 0
    monkeypatch.setattr(worker, "fair_use_notice_recipient", original)
    async with c.owner.begin() as conn:
        await conn.execute(text("UPDATE billing_notification_deliveries SET safe_payload=CAST(:payload AS json) WHERE workspace_id=:workspace"),
                           {**c.values, "payload": json.dumps(before[2][0]["safe_payload"])})
    assert await cli_snapshot(c) == before
    await x.dispatch()
    delivered = await cli_snapshot(c)
    assert delivered[:2] == before[:2] and len(x.calls) == 1
    assert delivered[2][0]["state"] == "delivered" and delivered[2][0]["attempts"] == 1
    await x.dispatch()
    assert await cli_snapshot(c) == delivered and len(x.calls) == 1


async def test_migrated_legacy_queue_preserves_history_without_delivery(
    operator_case, operator_migrations, monkeypatch,
):
    import hashlib

    from twobrain_rec_server.workflows import worker

    c = operator_case
    await operator_migrations("downgrade", "0112_storage_notifications")
    await prepare_cli_owner(c)
    # Trusted setup represents the old producer's shape before 0113, not a new intake.
    digest = hashlib.sha256(c.values["evidence"].encode("ascii")).hexdigest()[:32]
    payload = {"action_path": "/account/fair-use", "capability": "server_processing",
               "reason": "resale", "review_by": "02.01.2026 03:00"}
    async with c.owner.begin() as conn:
        await conn.execute(text(CREATE), c.values)
        await conn.execute(text("""
            INSERT INTO billing_notification_deliveries
              (id,workspace_id,recipient_id,event_id,channel,template_key,state,safe_payload,attempts)
            VALUES (:queue,:workspace,:subject,:event,'email','fair_use_review','pending',CAST(:payload AS json),0)
        """), {**c.values, "queue": uuid4(), "event": f"fair_use.review:server_processing:review:{digest}",
               "payload": json.dumps(payload)})
        await conn.execute(text("""
            INSERT INTO billing_audit_events(id,workspace_id,action,target_kind,outcome,metadata_json)
            VALUES (:audit,:workspace,'ordinary.synthetic','workspace','applied','{}')
        """), {**c.values, "audit": uuid4()})
        await conn.execute(text("""
            INSERT INTO external_identities(id,user_id,provider,provider_subject,email,is_verified,is_active)
            VALUES (:email,:subject,'email',:provider,'legacy@example.test',true,true)
        """), {**c.values, "email": uuid4(), "provider": uuid4().hex})
    before = await cli_snapshot(c)
    await operator_migrations("upgrade", "head")
    await bootstrap._bootstrap()
    assert await cli_snapshot(c) == before
    calls = []

    async def send(**kwargs):
        calls.append(kwargs)

    async def stop(_seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "create_engine", lambda _: c.maintenance)
    monkeypatch.setattr(worker, "send_billing_notification", send)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(SimpleNamespace(
                billing_support_email=None, public_base_url="https://graf.example.test"))
        after = await cli_snapshot(c)
        assert after[:2] == before[:2] and calls == []
        expected = {**before[2][0], "state": "suppressed"}
        assert after[2] == [expected]


@pytest.mark.parametrize("reserved", ["action", "target"])
async def test_cleanup_preserves_foreign_actor_only_history(fair_use_cleanup_case, reserved):
    x = fair_use_cleanup_case
    c = x.case
    before = await x.snapshot()
    # Negative historical shape only: the trusted owner prepares an orphan audit.
    async with c.owner.begin() as source:
        await source.execute(text("ALTER TABLE billing_audit_events DISABLE TRIGGER fair_use_audit_guard"))
        await source.execute(text("""
            INSERT INTO billing_audit_events(id,workspace_id,actor_user_id,action,target_kind,outcome,metadata_json)
            VALUES (:id,:foreign,:subject,:action,:kind,'applied','{}')
        """), {**c.values, "foreign": x.original.values["workspace"],
               "action": "fair_use.legacy" if reserved == "action" else "ordinary.synthetic",
               "kind": "ordinary" if reserved == "action" else "fair_use_review"})
        await source.execute(text("ALTER TABLE billing_audit_events ENABLE ALWAYS TRIGGER fair_use_audit_guard"))
        assert await x.snapshot() == before
        assert await asyncio.wait_for(x.cleanup(), timeout=3) == (0, 0, ["protected_fair_use_history"])
        assert await x.snapshot() == before and x.storage == []
    committed = await x.snapshot()
    assert committed[:6] == before[:6] and committed[7] == before[7]
    assert len(committed[6]) == len(before[6]) + 1
    assert committed[6][-1]["actor_user_id"] == str(c.values["subject"])
    assert committed[6][-1]["workspace_id"] != str(c.values["workspace"])
    assert await x.cleanup() == (0, 0, ["protected_fair_use_history"])
    assert await x.snapshot() == committed and x.storage == []
    assert not any(sql.lstrip().lower().startswith(("delete", "update", "insert", "truncate")) for sql in x.statements)


@pytest.mark.parametrize("state,blocked", [
    ("notice", False), ("restricted", True), ("appealed", True),
    ("cleared", False), ("confirmed", False),
])
async def test_merge_filter_preserves_all_legacy_states(operator_case, operator_migrations, state, blocked):
    from twobrain_rec_server.billing.fair_use import fair_use_restricted_for_lineage

    c = operator_case
    await operator_migrations("downgrade", "0112_storage_notifications")
    # Trusted pre-0113 history exercises the existing consumer, not a new operator intake.
    async with c.owner.begin() as conn:
        await conn.execute(text(CREATE), c.values)
        await conn.execute(text("UPDATE public.fair_use_reviews SET state=:state WHERE id=:id"),
                           {**c.values, "state": state})
    before = await source_snapshot(c)
    await operator_migrations("upgrade", "head")
    await bootstrap._bootstrap()
    assert await source_snapshot(c) == before
    await c.app.dispose()
    async with async_sessionmaker(c.app, expire_on_commit=False)() as db, db.begin():
        await apply_tenant_context(db, _request_context(c.ids, "a"))
        assert await db.scalar(text("SELECT session_user")) == "twobrain_rec_app"
        assert await fair_use_restricted_for_lineage(
            db, user_id=c.ids["user_a"], include_confirmed=False,
        ) is blocked
        assert await fair_use_restricted_for_lineage(
            db, user_id=c.ids["user_a"], include_confirmed=True,
        ) is (state in {"restricted", "appealed", "confirmed"})
        assert await fair_use_restricted_for_lineage(
            db, user_id=c.ids["user_a"], capability="storage", include_confirmed=False,
        ) is False
    assert await source_snapshot(c) == before
