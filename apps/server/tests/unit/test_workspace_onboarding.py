from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from twobrain_rec_server.auth.workspace_onboarding import can_transition_join_offer
from twobrain_rec_server.db.models import Workspace, WorkspaceJoinOffer


def test_personal_workspace_carries_its_owner_marker() -> None:
    owner_id = uuid4()

    workspace = Workspace(
        organization_id=uuid4(),
        slug="personal-owner",
        name="Личное пространство",
        kind="personal",
        owner_user_id=owner_id,
    )

    assert workspace.kind == "personal"
    assert workspace.owner_user_id == owner_id


def test_join_offer_is_bound_to_one_user_and_invitation() -> None:
    now = datetime.now(UTC)
    offer = WorkspaceJoinOffer(
        workspace_id=uuid4(),
        user_id=uuid4(),
        invitation_id=uuid4(),
        status="offered",
        expires_at=now + timedelta(days=1),
    )

    assert offer.status == "offered"
    assert offer.expires_at > now


def test_join_offer_transition_is_terminal_after_acceptance_or_rejection() -> None:
    assert can_transition_join_offer("offered", "accepted")
    assert can_transition_join_offer("offered", "rejected")
    assert not can_transition_join_offer("accepted", "offered")
    assert not can_transition_join_offer("rejected", "accepted")
