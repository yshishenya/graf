from __future__ import annotations

import asyncio

from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.audit import write_onboarding_audit_event


def test_onboarding_audit_keeps_only_metadata_safe_for_persistence(client) -> None:
    async def exercise() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await write_onboarding_audit_event(
                db,
                workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                event_type="workspace_join_offer_created",
                metadata={
                    "offer_id": "opaque-offer-id",
                    "status": "offered",
                    "target_contact": "private@example.test",
                    "provider_claim": "private-claim",
                },
            )
            await db.commit()
            return event.metadata_json

    metadata = asyncio.run(exercise())

    assert metadata == {"offer_id": "opaque-offer-id", "status": "offered"}
