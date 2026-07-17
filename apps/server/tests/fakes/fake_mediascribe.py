from dataclasses import dataclass, field
from hashlib import sha256
from typing import BinaryIO

from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribePollResponse,
    MediaScribeResult,
    MediaScribeSubmitResponse,
)


@dataclass
class FakeMediaScribeClient:
    external_job_id: str = "job_fake_001"
    status_sequence: list[MediaScribeJobStatus] = field(
        default_factory=lambda: [MediaScribeJobStatus.UPLOADED, MediaScribeJobStatus.READY]
    )
    result: MediaScribeResult | None = None
    submissions: list[dict[str, object]] = field(default_factory=list)
    poll_count: int = 0

    async def submit_dual_track(
        self,
        *,
        mic_file: BinaryIO,
        incoming_file: BinaryIO,
        diarize: bool,
        summarize: bool,
    ) -> MediaScribeSubmitResponse:
        mic_size, mic_hash = _stream_digest(mic_file)
        incoming_size, incoming_hash = _stream_digest(incoming_file)
        self.submissions.append(
            {
                "mic_size": mic_size,
                "incoming_size": incoming_size,
                "mic_sha256": mic_hash,
                "incoming_sha256": incoming_hash,
                "diarize": diarize,
                "summarize": summarize,
            }
        )
        return MediaScribeSubmitResponse(
            external_job_id=self.external_job_id,
            status=self.status_sequence[0],
        )

    async def submit_single_track(
        self,
        *,
        media_file: BinaryIO,
        diarize: bool,
        summarize: bool,
        media_content_type: str | None = None,
        media_filename: str | None = None,
    ) -> MediaScribeSubmitResponse:
        media_size, media_hash = _stream_digest(media_file)
        submission = {
            "request_mode": "single_track",
            "media_size": media_size,
            "media_sha256": media_hash,
            "media_content_type": media_content_type,
            "diarize": diarize,
            "summarize": summarize,
        }
        if media_filename is not None:
            submission["media_filename"] = media_filename
        self.submissions.append(submission)
        return MediaScribeSubmitResponse(
            external_job_id=self.external_job_id,
            status=self.status_sequence[0],
        )

    async def poll_job(self, external_job_id: str) -> MediaScribePollResponse:
        status = self.status_sequence[min(self.poll_count, len(self.status_sequence) - 1)]
        self.poll_count += 1
        return MediaScribePollResponse(external_job_id=external_job_id, status=status)

    async def fetch_result(self, external_job_id: str) -> MediaScribeResult:
        if self.result is not None:
            return self.result
        return MediaScribeResult(external_job_id=external_job_id)


def _stream_digest(stream: BinaryIO) -> tuple[int, str]:
    digest = sha256()
    total = 0
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        digest.update(chunk)
    return total, digest.hexdigest()
