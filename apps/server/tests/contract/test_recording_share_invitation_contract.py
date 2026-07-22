from pathlib import Path

from cryptography.fernet import Fernet

from twobrain_rec_server.cabinet.access import (
    open_invitation_delivery,
    seal_invitation_delivery,
)


def test_invitation_delivery_payload_is_encrypted_and_round_trips() -> None:
    key = Fernet.generate_key()
    sealed = seal_invitation_delivery(
        address="recipient@example.test",
        raw_token="synthetic-one-time-token",
        key=key,
    )

    assert "recipient@example.test" not in sealed
    assert "synthetic-one-time-token" not in sealed
    assert open_invitation_delivery(sealed, key=key) == (
        "recipient@example.test",
        "synthetic-one-time-token",
    )


def test_logged_out_invitation_redirects_to_login_and_preserves_target(client) -> None:
    response = client.get(
        "/share-invitations/synthetic-token?workspace_id="
        "20000000-0000-0000-0000-000000000001",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?")
    assert "share-invitations%2Fsynthetic-token" in response.headers["location"]
    assert "workspace_id%3D20000000-0000-0000-0000-000000000001" in response.headers[
        "location"
    ]


def test_postal_delivery_commits_at_most_once_fence_before_network_egress() -> None:
    source = Path(
        "src/twobrain_rec_server/workflows/worker.py"
    ).read_text(encoding="utf-8")
    activity = source.split(
        "async def deliver_meeting_invitation_activity", 1
    )[1].split("\ndef _processing_status_for_client_error", 1)[0]

    reserved = activity.index('invitation.status = "sending"')
    committed = activity.index("await db.commit()", reserved)
    sent = activity.index(".send_meeting_invitation(", committed)
    assert reserved < committed < sent

    recovery = activity.split('if invitation.status == "sending":', 1)[1].split(
        'if invitation.status != "pending":', 1
    )[0]
    assert 'invitation.status = "failed"' in recovery
    assert 'invitation.failure_code = "postal_delivery_outcome_unknown"' in recovery
    assert ".send_meeting_invitation(" not in recovery
