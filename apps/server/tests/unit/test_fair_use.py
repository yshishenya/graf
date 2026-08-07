import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.events import BillingEvent, event_id_for, notification_kind_for
from twobrain_rec_server.billing.fair_use import (
    appeal_review,
    create_review,
    enqueue_review_notification,
    resolve_review,
    review_subject_ref,
)
from twobrain_rec_server.billing.notifications import BillingNotification


def test_fair_use_review_is_bounded_and_appealable() -> None:
    starts_at = datetime(2026, 8, 7, 10, tzinfo=UTC)
    review = create_review(
        capability="server_processing",
        reason="automated_bulk",
        evidence_ref="incident:123",
        starts_at=starts_at,
    )
    assert review.review_by == datetime(2026, 8, 8, 10, tzinfo=UTC)
    assert appeal_review(review, at=starts_at).state == "appealed"
    assert resolve_review(review, state="cleared").state == "cleared"


def test_fair_use_review_rejects_unbounded_reason_or_time() -> None:
    with pytest.raises(ValueError):
        create_review(
            capability="server_processing",
            reason="volume_only",
            evidence_ref="incident:123",
            starts_at=datetime(2026, 8, 7, tzinfo=UTC),
        )
    with pytest.raises(ValueError):
        create_review(
            capability="server_processing",
            reason="automated_bulk",
            evidence_ref="meeting-content",
            starts_at=datetime(2026, 8, 7),
        )


def test_billing_event_taxonomy_is_closed_and_refund_free() -> None:
    assert notification_kind_for(BillingEvent.FAIR_USE_REVIEW) == BillingNotification.FAIR_USE_REVIEW
    assert event_id_for(event_type="payment.succeeded", subject_ref="INV-123") == "payment.succeeded:INV-123"
    with pytest.raises(ValueError, match="allowlisted"):
        notification_kind_for("refund.succeeded")
    with pytest.raises(ValueError, match="allowlisted"):
        notification_kind_for("payment.refund")


def test_fair_use_notification_subject_is_bounded_metadata() -> None:
    review = create_review(
        capability="server_processing",
        reason="security_abuse",
        evidence_ref="incident:123",
        starts_at=datetime(2026, 8, 7, 10, tzinfo=UTC),
    )
    assert review_subject_ref(review).startswith("server_processing:review:")
    assert len(review_subject_ref(review)) == len("server_processing:review:") + 32
    with pytest.raises(ValueError):
        event_id_for(event_type="fair_use.review", subject_ref="x" * 121)


def test_fair_use_notification_never_sends_evidence_payload() -> None:
    review = create_review(
        capability="server_processing",
        reason="security_abuse",
        evidence_ref="incident:123",
        starts_at=datetime(2026, 8, 7, 10, tzinfo=UTC),
    )
    enqueue = AsyncMock(return_value=True)
    with patch("twobrain_rec_server.billing.fair_use.enqueue_billing_event", enqueue):
        result = asyncio.run(
            enqueue_review_notification(
                object(),
                workspace_id=uuid4(),
                recipient_id=uuid4(),
                review=review,
            )
        )
    assert result is True
    payload = enqueue.call_args.kwargs["payload"]
    assert payload == {"action_path": "/account/fair-use"}
    assert review.evidence_ref not in str(enqueue.call_args.kwargs)
