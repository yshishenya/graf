from dataclasses import dataclass, field
from hashlib import sha256

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
        mic_bytes: bytes,
        incoming_bytes: bytes,
        diarize: bool,
        summarize: bool,
    ) -> MediaScribeSubmitResponse:
        self.submissions.append(
            {
                "mic_size": len(mic_bytes),
                "incoming_size": len(incoming_bytes),
                "mic_sha256": sha256(mic_bytes).hexdigest(),
                "incoming_sha256": sha256(incoming_bytes).hexdigest(),
                "diarize": diarize,
                "summarize": summarize,
            }
        )
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
