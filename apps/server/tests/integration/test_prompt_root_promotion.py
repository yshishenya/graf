"""Synthetic operator journal integrity; no Langfuse or production writes."""

import asyncio
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from tests.fixtures.prompt_authority import promotion_row


def test_root_writer_has_no_imported_pass_or_boolean_authority():
    import inspect

    from twobrain_rec_server.outcomes.prompt_bundle import promote_root_bundle

    parameters = inspect.signature(promote_root_bundle).parameters
    assert "report" not in parameters and "qualification" not in parameters
    assert "protected_label_capability_verified" not in parameters
    assert {"evaluation_sessionmaker", "source_reader", "workdir", "run_id"} <= parameters.keys()


def _row():
    from twobrain_rec_server.db.models import PromptRootPromotion

    return PromptRootPromotion(
        id=uuid4(), project_id="synthetic-project", root_name="synthetic-root",
        operation_kind="initial_activation", expected_source_version=1,
        root_export_json={"synthetic": True}, root_export_hash="a" * 64,
        activation_json={"synthetic": True}, activation_hash="b" * 64,
        qualification_json={"synthetic": True}, qualification_hash="c" * 64,
        state="prepared", is_current=False,
    )


def test_journal_is_immutable_and_allows_only_one_unfinished_operation(client):
    async def run():
        sessions = client.app_state["sessionmaker"]
        first = _row()
        async with sessions() as db:
            db.add(first)
            await db.commit()
        async with sessions() as db:
            row = await db.get(type(first), first.id)
            row.qualification_json = {"changed": True}
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()
        async with sessions() as db:
            db.add(_row())
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()
        async with sessions() as db:
            row = await db.get(type(first), first.id)
            await db.delete(row)
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()

    asyncio.run(run())


def test_successful_event_cannot_be_replaced_and_current_is_unique(client):
    async def run():
        sessions = client.app_state["sessionmaker"]
        first = _row()
        first_id = first.id
        async with sessions() as db:
            db.add(first)
            await db.commit()
            first.state = "succeeded"
            first.event_json = {"synthetic_event": str(first.id)}
            first.event_hash = "d" * 64
            first.is_current = True
            await db.commit()
            stable = deepcopy(first.event_json)
            first.event_json = {"replaced": True}
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()
        async with sessions() as db:
            first = await db.get(type(first), first_id)
            assert first.event_json == stable
            second = _row()
            db.add(second)
            await db.commit()
            second.state = "succeeded"
            second.event_json = {"synthetic_event": str(second.id)}
            second.event_hash = "e" * 64
            second.is_current = True
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()

    asyncio.run(run())


def test_generation_call_authority_columns_and_journal_rls_are_present(client):
    from twobrain_rec_server.db.models import GenerationCall, PromptRootPromotion

    assert {"execution_authority_json", "execution_authority_hash"} <= set(GenerationCall.__table__.columns.keys())

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            policies = (await db.execute(text(
                "select policyname, cmd, qual, with_check from pg_policies where tablename = 'prompt_root_promotions'"
            ))).all()
            assert policies
            writes = [row for row in policies if row.cmd in {"ALL", "INSERT", "UPDATE", "DELETE"}]
            assert writes and all("twobrain_rec_maintenance" in str(row) for row in writes)
            assert await db.scalar(select(PromptRootPromotion.id).limit(1)) is None

    asyncio.run(run())


@pytest.mark.parametrize("state", ["prepared", "reconciliation_required", "cancelled"])
@pytest.mark.parametrize("present_field", ["event_json", "event_hash"])
@pytest.mark.parametrize("write", ["insert", "update"])
def test_partial_event_is_rejected_at_first_write(client, state, present_field, write):
    async def run():
        complete = promotion_row()
        async with client.app_state["sessionmaker"]() as db:
            row = _row()
            if write == "update":
                db.add(row)
                await db.commit()
            row.state = state
            setattr(row, present_field, getattr(complete, present_field))
            if write == "insert":
                db.add(row)
            with pytest.raises(DBAPIError, match="event_success"):
                await db.commit()
            await db.rollback()

    asyncio.run(run())


def test_complete_synthetic_admission_round_trips(client):
    from twobrain_rec_server.outcomes.prompt_bundle import validate_promotion_row

    async def run():
        row = promotion_row()
        row_id = row.id
        expected = validate_promotion_row(row)[1]
        async with client.app_state["sessionmaker"]() as db:
            db.add(row)
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            saved = await db.get(type(row), row_id)
            assert validate_promotion_row(saved)[1] == expected

    asyncio.run(run())
