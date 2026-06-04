import pytest
from twobrain_rec_server.domain.statuses import UploadSessionStatus
from twobrain_rec_server.ingest.state_machine import (
    ensure_can_accept_part,
    is_terminal_upload_status,
)


def test_terminal_upload_statuses_do_not_accept_parts() -> None:
    assert is_terminal_upload_status(UploadSessionStatus.ABORTED)
    with pytest.raises(ValueError):
        ensure_can_accept_part(UploadSessionStatus.FINALIZED)


def test_active_upload_statuses_accept_parts() -> None:
    ensure_can_accept_part(UploadSessionStatus.PENDING)
    ensure_can_accept_part(UploadSessionStatus.UPLOADING)
