from uuid import uuid4

import pytest

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.deletion.service import fanout_account_close_deletions


class _DbWithMeetingIds:
    async def scalars(self, *_args, **_kwargs):
        return (uuid4(),)


class _EmptyDb:
    async def scalars(self, *_args, **_kwargs):
        return ()


@pytest.mark.asyncio
async def test_account_close_fanout_requires_storage_when_content_exists() -> None:
    with pytest.raises(ProblemDetail) as error:
        await fanout_account_close_deletions(
            _DbWithMeetingIds(),
            workspace_id=uuid4(),
            storage=object(),
        )
    assert error.value.code == "deletion_storage_unavailable"


@pytest.mark.asyncio
async def test_account_close_fanout_does_not_require_storage_for_empty_workspace() -> None:
    assert (
        await fanout_account_close_deletions(
            _EmptyDb(),
            workspace_id=uuid4(),
            storage=None,
        )
        == ()
    )
