"""Owner publication and atomic delivery commands. Never sends mail or commits."""

import json
import secrets
from collections import Counter
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, text

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import (
    decide_meeting_access,
    enforce_share_rate_limit,
    hash_invitation_address,
    hash_share_token,
    lock_shareable_meeting,
    normalize_invitation_address,
)
from twobrain_rec_server.cabinet.queries import shared_meeting_display_metadata
from twobrain_rec_server.db.models import (
    DispatchIntent,
    MeetingOutcomeItem,
    MeetingShareGrant,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.models.summary_sharing import (
    PublishedMeetingSummary,
    SummaryDeliveryBatch,
    SummaryRecipientDelivery,
)
from twobrain_rec_server.outcomes.service import load_egress_default_outcome, load_summary_slot


async def audit(db, *, workspace_id, meeting_id, actor_user_id, device_id, action, metadata):
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type=action,
        outcome="allowed",
        policy_reason="summary_owner_authorized",
        metadata=metadata,
    )


def fail(code, status=409):
    raise ProblemDetail(status=status, code=code, title="Summary sharing unavailable")


def encryption_key(settings):
    path = settings.credential_encryption_key_file
    if path is None:
        fail("summary_sharing_unavailable", 503)
    try:
        key = path.read_bytes().strip()
        Fernet(key)
        return key
    except (OSError, ValueError):
        fail("summary_sharing_unavailable", 503)


def seal(value, key):
    return Fernet(key).encrypt(value.encode()).decode()


def open_sealed(value, key):
    try:
        return Fernet(key).decrypt(value.encode()).decode()
    except (ValueError, InvalidToken, UnicodeError):
        fail("summary_sharing_unavailable", 503)


def reader_protocol(value):
    """Construct schema-v1 content explicitly; unknown nested fields never escape."""
    if not isinstance(value, dict):
        return None

    def rows(values, keys=("text",)):
        return (
            [
                {k: row[k] if isinstance(row.get(k), str) else "" for k in keys}
                for row in values
                if isinstance(row, dict)
            ]
            if isinstance(values, list)
            else []
        )

    result = {
        key: value.get(key) if isinstance(value.get(key), str) else ""
        for key in ("title", "date_and_time", "input_type", "meeting_type")
    }
    result["participants"] = (
        [v for v in value.get("participants", []) if isinstance(v, str)]
        if isinstance(value.get("participants"), list)
        else []
    )
    for key in (
        "executive_summary",
        "objectives",
        "decisions",
        "open_questions",
        "next_steps",
        "notes",
    ):
        result[key] = rows(value.get(key))
    result["action_items"] = rows(
        value.get("action_items"), ("task", "owner_text", "due_date_text")
    )
    result["topics"] = []
    for topic in value.get("topics", []) if isinstance(value.get("topics"), list) else []:
        if isinstance(topic, dict):
            result["topics"].append(
                {
                    "title": topic.get("title") if isinstance(topic.get("title"), str) else "",
                    **{
                        key: rows(topic.get(key))
                        for key in ("context", "discussion", "proposals", "outcome")
                    },
                }
            )
    return result


def reader_projection(value):
    return {
        "meeting_label": str(value.get("meeting_label") or "Встреча")[:160],
        "occurred_at": value["occurred_at"],
        "duration_seconds": max(0, int(value.get("duration_seconds") or 0)),
        "summary_sections": [
            {"category": str(row.get("category") or "summary"), "text": str(row.get("text") or "")}
            for row in value.get("summary_sections", [])
            if isinstance(row, dict)
        ],
        "protocol": reader_protocol(value.get("protocol")),
    }


async def active_sender(db, *, workspace_id, actor_user_id):
    return (
        await db.scalar(
            select(UserIdentity.id)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                UserIdentity.id == actor_user_id,
                UserIdentity.status == "active",
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
                UserIdentity.organization_id == Workspace.organization_id,
            )
            .with_for_update(key_share=True, of=[UserIdentity, WorkspaceMembership])
        )
        is not None
    )


async def owner_meeting(db, *, workspace_id, meeting_id, actor_user_id):
    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting_id)
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if (
        not decision.can_share
        or meeting.created_by_user_id != actor_user_id
        or not await active_sender(db, workspace_id=workspace_id, actor_user_id=actor_user_id)
    ):
        fail("meeting_not_found", 404)
    return meeting


async def preview_summary(db, *, meeting, template_key):
    slot = await load_summary_slot(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id, template_key=template_key
    )
    outcome = await load_egress_default_outcome(db, meeting=meeting, slot=slot)
    if outcome is None:
        fail("summary_default_missing")
    items = (
        await db.scalars(
            select(MeetingOutcomeItem)
            .where(
                MeetingOutcomeItem.workspace_id == meeting.workspace_id,
                MeetingOutcomeItem.outcome_set_id == outcome.id,
                MeetingOutcomeItem.state == "available",
            )
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
        )
    ).all()
    label, occurred, _uploaded = await shared_meeting_display_metadata(db, meeting=meeting)
    return outcome, reader_projection(
        {
            "meeting_label": label,
            "occurred_at": occurred.isoformat(),
            "duration_seconds": meeting.duration_seconds,
            "summary_sections": [{"category": item.category, "text": item.text} for item in items],
            "protocol": outcome.protocol_json,
        }
    )


async def create_summary_snapshot(db, *, workspace_id, meeting, template_key, owner_user_id):
    if meeting.workspace_id != workspace_id:
        fail("meeting_not_found", 404)
    outcome, projection = await preview_summary(db, meeting=meeting, template_key=template_key)
    snapshot = PublishedMeetingSummary(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        owner_user_id=owner_user_id,
        source_outcome_id=outcome.id,
        template_key=template_key,
        schema_version=1,
        projection_json=projection,
        published_at=datetime.now(UTC),
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def snapshot_view(snapshot):
    if snapshot.schema_version != 1:
        fail("share_not_found", 404)
    return {
        "published_summary_id": str(snapshot.id),
        "source_outcome_id": str(snapshot.source_outcome_id),
        "template_key": snapshot.template_key,
        "published_at": snapshot.published_at.isoformat(),
        "projection": reader_projection(snapshot.projection_json),
    }


async def load_shared_summary_projection(db, *, workspace_id, meeting, grant):
    publication_id = getattr(grant, "_shared_publication_override", None) or (
        grant.published_summary_id if grant else None
    )
    if publication_id is None:
        return None
    snapshot = await db.scalar(
        select(PublishedMeetingSummary).where(
            PublishedMeetingSummary.id == publication_id,
            PublishedMeetingSummary.workspace_id == workspace_id,
            PublishedMeetingSummary.meeting_id == meeting.id,
        )
    )
    if snapshot is None or snapshot.schema_version != 1:
        fail("share_not_found", 404)
    return reader_projection(snapshot.projection_json)


async def current_link(db, *, workspace_id, meeting_id):
    return await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.status == "active",
        )
    )


async def link_view(db, *, grant, settings):
    if grant is None:
        return {
            "state": "absent",
            "grant_id": None,
            "version": 0,
            "expires_at": None,
            "share_url": None,
            "summary": None,
        }
    snapshot = (
        await db.get(PublishedMeetingSummary, grant.published_summary_id)
        if grant.published_summary_id
        else None
    )
    expired = grant.expires_at is not None and grant.expires_at <= datetime.now(UTC)
    available = bool(grant.share_token_ciphertext and snapshot and not expired)
    token = (
        open_sealed(grant.share_token_ciphertext, encryption_key(settings)) if available else None
    )
    if token and hash_share_token(token) != grant.share_token_hash:
        fail("summary_sharing_unavailable", 503)
    return {
        "state": "expired" if expired else "active" if available else "replacement_required",
        "grant_id": str(grant.id),
        "version": grant.publication_version,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "share_url": f"{str(settings.public_base_url).rstrip('/')}/api/v1/cabinet/public-shares/{token}?workspace_id={grant.workspace_id}"
        if token
        else None,
        "summary": snapshot_view(snapshot) if snapshot else None,
    }


async def create_link(
    db,
    *,
    settings,
    workspace_id,
    meeting_id,
    actor_user_id,
    device_id,
    template_key,
    expires_in_days=30,
):
    if (
        not settings.share_public_links_enabled
        or not settings.share_public_links_abuse_gate_approved
    ):
        fail("share_not_found", 404)
    if expires_in_days not in (7, 30, 90):
        fail("invalid_share_expiry", 422)
    meeting = await owner_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting_id, actor_user_id=actor_user_id
    )
    existing = await current_link(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if existing:
        return await link_view(db, grant=existing, settings=settings)
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="grant",
    )
    snapshot = await create_summary_snapshot(
        db,
        workspace_id=workspace_id,
        meeting=meeting,
        template_key=template_key,
        owner_user_id=actor_user_id,
    )
    token = secrets.token_urlsafe(32)
    grant = MeetingShareGrant(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        grant_type="link",
        audience_type="link",
        content_scope="summary_only",
        can_download=False,
        can_export=False,
        created_by_user_id=actor_user_id,
        status="active",
        share_token_hash=hash_share_token(token),
        share_token_ciphertext=seal(token, encryption_key(settings)),
        published_summary_id=snapshot.id,
        publication_version=1,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        metadata_json={},
    )
    db.add(grant)
    await db.flush()
    await audit(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        action="summary_link_published",
        metadata={"share_grant_id": str(grant.id), "published_summary_id": str(snapshot.id)},
    )
    return await link_view(db, grant=grant, settings=settings)


async def change_link(
    db,
    *,
    settings,
    workspace_id,
    meeting_id,
    actor_user_id,
    device_id,
    grant_id,
    expected_version,
    operation,
    template_key=None,
    expires_in_days=30,
):
    meeting = await owner_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting_id, actor_user_id=actor_user_id
    )
    grant = await current_link(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if grant is None or grant.id != grant_id or grant.publication_version != expected_version:
        fail("summary_link_changed")
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="rotate" if operation == "rotate" else "revoke",
    )
    if operation == "revoke":
        grant.status, grant.revoked_at, grant.revoked_by_user_id = (
            "revoked",
            datetime.now(UTC),
            actor_user_id,
        )
        grant.share_token_ciphertext = None
    elif operation in ("update", "rotate", "expiry"):
        if operation == "update":
            if not template_key:
                fail("invalid_summary_template", 422)
            snapshot = await create_summary_snapshot(
                db,
                workspace_id=workspace_id,
                meeting=meeting,
                template_key=template_key,
                owner_user_id=actor_user_id,
            )
            grant.published_summary_id = snapshot.id
        if operation == "rotate":
            token = secrets.token_urlsafe(32)
            grant.share_token_hash, grant.share_token_ciphertext = (
                hash_share_token(token),
                seal(token, encryption_key(settings)),
            )
            grant.rotated_at = datetime.now(UTC)
            # Explicit replacement of a legacy link publishes the selected current format.
            if grant.published_summary_id is None:
                if not template_key:
                    fail("invalid_summary_template", 422)
                snapshot = await create_summary_snapshot(
                    db,
                    workspace_id=workspace_id,
                    meeting=meeting,
                    template_key=template_key,
                    owner_user_id=actor_user_id,
                )
                grant.published_summary_id = snapshot.id
                grant.content_scope = "summary_only"
                grant.can_download = grant.can_export = grant.can_edit = grant.can_comment = False
        if operation == "expiry":
            if expires_in_days not in (7, 30, 90):
                fail("invalid_share_expiry", 422)
            grant.expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    else:
        fail("invalid_share_operation", 422)
    grant.publication_version += 1
    await db.flush()
    await audit(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        action=f"summary_link_{operation}",
        metadata={
            "share_grant_id": str(grant.id),
            "publication_version": grant.publication_version,
        },
    )
    return await link_view(db, grant=None if operation == "revoke" else grant, settings=settings)


async def create_batch(
    db,
    *,
    settings,
    workspace_id,
    meeting_id,
    actor_user_id,
    template_key,
    recipients,
    idempotency_key,
    device_id=None,
    automatic_authority=None,
    scheduled_at=None,
    deadline_at=None,
):
    addresses = sorted({normalize_invitation_address(v) for v in recipients})
    if not 1 <= len(addresses) <= 50 or not 1 <= len(idempotency_key) <= 128:
        fail("invalid_summary_recipients", 422)
    if not settings.share_external_invitations_enabled:
        fail("summary_email_unavailable", 503)
    meeting = await owner_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting_id, actor_user_id=actor_user_id
    )
    fingerprint = sha256(
        json.dumps(
            {"meeting": str(meeting_id), "template": template_key, "addresses": addresses},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = await db.scalar(
        select(SummaryDeliveryBatch).where(
            SummaryDeliveryBatch.workspace_id == workspace_id,
            SummaryDeliveryBatch.owner_user_id == actor_user_id,
            SummaryDeliveryBatch.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.request_fingerprint != fingerprint:
            fail("summary_operation_conflict")
        return existing
    now = datetime.now(UTC)
    if automatic_authority is not None:
        from twobrain_rec_server.cabinet.summary_autosend import validate_auto_authority

        guard = await validate_auto_authority(
            db,
            meeting=meeting,
            authority=automatic_authority,
            recipients=addresses,
            template_key=template_key,
            settings=settings,
        )
        if not guard.allowed:
            fail(guard.reason_code or "summary_auto_requires_review")
        occurrence = automatic_authority["occurrence_key"]
        if db.get_bind().dialect.name == "postgresql":
            # The provider occurrence is shared across recorders and rule owners.
            lock_key = int.from_bytes(
                sha256(f"{workspace_id}:{occurrence}".encode()).digest()[:8], "big", signed=True
            )
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        if await db.scalar(
            select(SummaryDeliveryBatch.id).where(
                SummaryDeliveryBatch.workspace_id == workspace_id,
                SummaryDeliveryBatch.automatic.is_(True),
                SummaryDeliveryBatch.auto_occurrence_key == occurrence,
            )
        ):
            fail("summary_auto_occurrence_already_sent")
    else:
        if device_id is None:
            fail("summary_device_required", 403)
        await enforce_share_rate_limit(
            db,
            workspace_id=workspace_id,
            user_id=actor_user_id,
            device_id=device_id,
            action_key="summary_batch",
        )
    snapshot = await create_summary_snapshot(
        db,
        workspace_id=workspace_id,
        meeting=meeting,
        template_key=template_key,
        owner_user_id=actor_user_id,
    )
    authority = automatic_authority or {}
    batch = SummaryDeliveryBatch(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        owner_user_id=actor_user_id,
        published_summary_id=snapshot.id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        state="pending",
        automatic=automatic_authority is not None,
        auto_authority_json=automatic_authority,
        auto_rule_id=UUID(authority["rule_id"]) if authority.get("rule_id") else None,
        auto_rule_version=authority.get("rule_version"),
        auto_occurrence_key=authority.get("occurrence_key"),
        ready_at=datetime.fromisoformat(authority["ready_at"])
        if authority.get("ready_at")
        else None,
        scheduled_at=scheduled_at or now,
        deadline_at=deadline_at or now + timedelta(hours=24),
    )
    db.add(batch)
    await db.flush()
    key = encryption_key(settings)
    for address in addresses:
        db.add(
            SummaryRecipientDelivery(
                id=uuid4(),
                workspace_id=workspace_id,
                batch_id=batch.id,
                normalized_address_hash=hash_invitation_address(address),
                encrypted_address=seal(address, key),
                state="pending",
                attempt_count=0,
            )
        )
    db.add(
        DispatchIntent(
            id=uuid4(),
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            intent_kind="summary_delivery",
            idempotency_key=f"summary-delivery:{batch.id}",
            state="created",
            reconciliation_state="pending",
            payload_json={"batch_id": str(batch.id)},
            next_attempt_at=batch.scheduled_at,
            deletion_epoch=0,
            attempt_count=0,
        )
    )
    await db.flush()
    await audit(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        action="summary_batch_created",
        metadata={
            "batch_id": str(batch.id),
            "published_summary_id": str(snapshot.id),
            "recipient_count": len(addresses),
            "automatic": batch.automatic,
        },
    )
    return batch


async def get_batch(db, *, workspace_id, meeting_id, actor_user_id, batch_id):
    await owner_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting_id, actor_user_id=actor_user_id
    )
    batch = await db.scalar(
        select(SummaryDeliveryBatch).where(
            SummaryDeliveryBatch.id == batch_id,
            SummaryDeliveryBatch.workspace_id == workspace_id,
            SummaryDeliveryBatch.meeting_id == meeting_id,
            SummaryDeliveryBatch.owner_user_id == actor_user_id,
        )
    )
    if batch is None:
        fail("summary_batch_not_found", 404)
    return batch


async def batch_view(db, batch, *, settings):
    snapshot = await db.get(PublishedMeetingSummary, batch.published_summary_id)
    rows = (
        await db.scalars(
            select(SummaryRecipientDelivery)
            .where(
                SummaryRecipientDelivery.batch_id == batch.id,
                SummaryRecipientDelivery.workspace_id == batch.workspace_id,
            )
            .order_by(SummaryRecipientDelivery.id)
        )
    ).all()
    counts = dict(Counter(row.state for row in rows))
    return {
        "batch_id": str(batch.id),
        "state": batch.state,
        "automatic": batch.automatic,
        "scheduled_at": batch.scheduled_at.isoformat(),
        "deadline_at": batch.deadline_at.isoformat(),
        "summary": snapshot_view(snapshot),
        "counts": counts,
        "can_cancel": bool(counts.get("pending")),
        "recipients": [
            {
                "recipient_id": str(row.id),
                "email": open_sealed(row.encrypted_address, encryption_key(settings)),
                "state": row.state,
                "failure_code": row.failure_code,
                "can_retry": row.state == "failed"
                and batch.state not in ("cancelled", "requires_review")
                and batch.deadline_at > datetime.now(UTC),
            }
            for row in rows
        ],
    }


async def cancel_batch(db, *, batch):
    batch.cancelled_at = datetime.now(UTC)
    batch.state = "cancelled"
    rows = (
        await db.scalars(
            select(SummaryRecipientDelivery)
            .where(
                SummaryRecipientDelivery.batch_id == batch.id,
                SummaryRecipientDelivery.workspace_id == batch.workspace_id,
                SummaryRecipientDelivery.state.in_(("pending", "failed")),
            )
            .with_for_update()
        )
    ).all()
    for row in rows:
        row.state = "cancelled"
    await db.flush()


async def retry_recipient(db, *, batch, recipient_id, settings):
    now = datetime.now(UTC)
    if batch.automatic:
        from twobrain_rec_server.cabinet.summary_autosend import guard_auto_batch

        guard = await guard_auto_batch(db, batch=batch, now=now, settings=settings)
        if not guard.allowed:
            fail(guard.reason_code or "summary_auto_requires_review")
    if batch.state in ("cancelled", "requires_review") or batch.deadline_at <= now:
        fail("summary_retry_unavailable")
    row = await db.scalar(
        select(SummaryRecipientDelivery)
        .where(
            SummaryRecipientDelivery.id == recipient_id,
            SummaryRecipientDelivery.workspace_id == batch.workspace_id,
            SummaryRecipientDelivery.batch_id == batch.id,
        )
        .with_for_update()
    )
    if row is None or row.state != "failed":
        fail("summary_retry_unavailable")
    row.state, row.failure_code = "pending", None
    batch.state = "pending"
    # A new dispatch identity starts a workflow for this authorized known-failure retry.
    db.add(
        DispatchIntent(
            id=uuid4(),
            workspace_id=batch.workspace_id,
            meeting_id=batch.meeting_id,
            intent_kind="summary_delivery",
            idempotency_key=f"summary-retry:{row.id}:{row.attempt_count}",
            state="created",
            reconciliation_state="pending",
            payload_json={"batch_id": str(batch.id)},
            next_attempt_at=now,
            deletion_epoch=0,
            attempt_count=0,
        )
    )
    await db.flush()
