from dataclasses import dataclass

from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus


@dataclass(frozen=True, slots=True)
class DesktopStatus:
    api_status: str
    label: str
    truth_rule: str


def upload_session_desktop_status(status: UploadSessionStatus) -> DesktopStatus:
    if status == UploadSessionStatus.FINALIZED:
        return DesktopStatus(
            api_status=status.value,
            label="uploaded",
            truth_rule="Upload succeeded; processing has not necessarily started.",
        )
    return DesktopStatus(
        api_status=status.value,
        label=status.value,
        truth_rule="This is post-capture upload lifecycle, not active recording truth.",
    )


def meeting_desktop_status(status: MeetingStatus) -> DesktopStatus:
    if status == MeetingStatus.INGESTED_PENDING_PROCESSING:
        return DesktopStatus(
            api_status=status.value,
            label="uploaded",
            truth_rule="Backend ingest succeeded; no transcript, summary, or dashboard readiness is implied.",
        )
    return DesktopStatus(api_status=status.value, label=status.value, truth_rule="Meeting lifecycle state.")
