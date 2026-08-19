from uuid import uuid4

import pytest

from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    build_merge_preview,
    ensure_preview_confirmable,
)


def test_dataful_merge_preview_preserves_fingerprint() -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        counts=MergeEntityCounts(meetings=2, recordings=2),
    )

    ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)


def test_empty_duplicate_preview_has_no_blockers() -> None:
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    assert preview.blocker_codes == ()


def test_blocker_and_stale_preview_fail_closed() -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        billing_conflict=True,
    )

    with pytest.raises(AccountMergeError, match="billing_conflict"):
        ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)
    clear = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())
    with pytest.raises(AccountMergeError, match="merge_preview_stale"):
        ensure_preview_confirmable(clear, fingerprint="0" * 64)
