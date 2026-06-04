from twobrain_rec_server.domain.statuses import UploadSessionStatus

TERMINAL_UPLOAD_STATUSES = {
    UploadSessionStatus.FINALIZED,
    UploadSessionStatus.DEGRADED,
    UploadSessionStatus.FAILED,
    UploadSessionStatus.ABORTED,
    UploadSessionStatus.EXPIRED,
}


def is_terminal_upload_status(status: UploadSessionStatus) -> bool:
    return status in TERMINAL_UPLOAD_STATUSES


def ensure_can_accept_part(status: UploadSessionStatus) -> None:
    if is_terminal_upload_status(status):
        raise ValueError(f"upload session is terminal: {status.value}")
