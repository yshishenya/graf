from uuid import uuid4

import pytest

from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    build_merge_preview,
    ensure_preview_confirmable,
)


@pytest.mark.parametrize(
    "field,code",
    (
        ("role_conflict", "workspace_role_conflict"),
        ("billing_conflict", "billing_conflict"),
        ("calendar_conflict", "calendar_ownership_conflict"),
        ("deletion_conflict", "deletion_state_conflict"),
    ),
)
def test_merge_blockers_are_deterministic_and_fail_closed(field: str, code: str) -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        counts=MergeEntityCounts(meetings=1),
        **{field: True},
    )

    assert preview.blocker_codes == (code,)
    with pytest.raises(AccountMergeError, match=code):
        ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)


def test_merge_preview_fingerprint_changes_when_preserved_counts_change() -> None:
    survivor = uuid4()
    source = uuid4()
    first = build_merge_preview(
        survivor_user_id=survivor,
        source_user_id=source,
        counts=MergeEntityCounts(meetings=1),
    )
    changed = build_merge_preview(
        survivor_user_id=survivor,
        source_user_id=source,
        counts=MergeEntityCounts(meetings=2),
    )

    assert first.fingerprint != changed.fingerprint
    with pytest.raises(AccountMergeError, match="merge_preview_stale"):
        ensure_preview_confirmable(changed, fingerprint=first.fingerprint)
