from datetime import UTC, datetime

import pytest

from twobrain_rec_server.billing.fair_use import appeal_review, create_review, resolve_review


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
