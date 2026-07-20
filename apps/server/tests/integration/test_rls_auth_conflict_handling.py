from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from twobrain_rec_server.auth.callbacks import CallbackFlowError, _create_scoped_user
from twobrain_rec_server.db.models import (
    ExternalIdentity,
    Organization,
    UserIdentity,
    Workspace,
)

OTHER_ORG_ID = UUID("90000000-0000-0000-0000-000000000001")
OTHER_WORKSPACE_ID = UUID("91000000-0000-0000-0000-000000000001")


async def _seed_global_identity_conflict(db, *, provider: str, provider_subject: str) -> None:
    other_user_id = uuid4()
    db.add_all(
        [
            Organization(id=OTHER_ORG_ID, slug=f"other-org-{provider_subject}", name="Other Org"),
            Workspace(
                id=OTHER_WORKSPACE_ID,
                organization_id=OTHER_ORG_ID,
                slug=f"other-workspace-{provider_subject}",
                name="Other Workspace",
            ),
            UserIdentity(
                id=other_user_id,
                organization_id=OTHER_ORG_ID,
                external_subject=f"other-{provider_subject}",
                display_name="Other User",
            ),
        ]
    )
    await db.flush()
    db.add(
        ExternalIdentity(
            user_id=other_user_id,
            provider=provider,
            provider_subject=provider_subject,
            is_verified=True,
        )
    )
    await db.commit()


def test_callback_create_scoped_user_maps_hidden_unique_identity_conflict(client) -> None:
    provider_subject = f"hidden-callback-conflict-{uuid4().hex}"

    async def exercise() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_global_identity_conflict(db, provider="yandex", provider_subject=provider_subject)
        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(CallbackFlowError) as exc_info:
                await _create_scoped_user(
                    db,
                    ORG_ID,
                    WORKSPACE_ID,
                    provider="yandex",
                    provider_subject=provider_subject,
                    profile={"provider_username": None, "email": None, "phone": None, "display_name": "Hidden"},
                )
            leaked_users = await db.scalar(
                select(UserIdentity).where(UserIdentity.external_subject == provider_subject)
            )
            return exc_info.value.code, 0 if leaked_users is None else 1

    code, leaked_user_count = asyncio.run(exercise())

    assert code == "identity_subject_conflict"
    assert leaked_user_count == 0
