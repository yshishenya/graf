from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from twobrain_rec_server.db.models import (
    AuthAuditEvent,
    ExternalIdentity,
    WorkspaceProviderLinkState,
)

from scripts.cleanup_expired_provider_links import cleanup_expired_provider_links
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID


def test_expired_provider_link_cleanup_is_idempotent_and_redacts_candidate(client) -> None:
    link_id = uuid4()

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            source = ExternalIdentity(
                user_id=USER_ID,
                provider="yandex",
                provider_subject="cleanup-source",
                is_verified=True,
            )
            db.add(source)
            await db.flush()
            db.add(
                WorkspaceProviderLinkState(
                    id=link_id,
                    workspace_id=WORKSPACE_ID,
                    initiating_user_id=USER_ID,
                    source_provider_identity_id=source.id,
                    candidate_provider="vk",
                    candidate_identity_subject="cleanup-candidate",
                    candidate_email="candidate@example.test",
                    candidate_phone="+79990000000",
                    candidate_display_name="Candidate",
                    status="callback_verified",
                    expires_at=datetime(2020, 1, 1, tzinfo=UTC),
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed())
    dry_run = asyncio.run(cleanup_expired_provider_links(client.app.state.settings, execute=False))
    first = asyncio.run(cleanup_expired_provider_links(client.app.state.settings, execute=True))
    second = asyncio.run(cleanup_expired_provider_links(client.app.state.settings, execute=True))

    assert dry_run == {"provider_link_cleanup_result": "dry_run", "expired_links": 0}
    assert first == {"provider_link_cleanup_result": "pass", "expired_links": 1}
    assert second == {"provider_link_cleanup_result": "pass", "expired_links": 0}

    async def load() -> tuple[WorkspaceProviderLinkState, list[AuthAuditEvent]]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            events = list(
                await db.scalars(
                    select(AuthAuditEvent).where(AuthAuditEvent.event_type == "provider_link_expired")
                )
            )
            return link, events

    link, events = asyncio.run(load())
    assert link.status == "expired"
    assert link.candidate_identity_subject is None
    assert link.candidate_email is None
    assert link.candidate_phone is None
    assert link.candidate_display_name is None
    assert len(events) == 1
    assert events[0].metadata_json == {"error_code": "provider_link_expired"}
