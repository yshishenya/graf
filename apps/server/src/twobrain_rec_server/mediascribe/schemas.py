from pydantic import BaseModel, Field

from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, SummaryStatus


class MediaScribeSubmitRequest(BaseModel):
    mic_object_key: str
    incoming_object_key: str
    diarize: bool = True
    summarize: bool = False
    speaker_count_mode: str | None = None
    num_speakers: int | None = Field(default=None, ge=1)


class MediaScribeSubmitResponse(BaseModel):
    external_job_id: str = Field(min_length=1)
    status: MediaScribeJobStatus = MediaScribeJobStatus.UPLOADED


class MediaScribePollResponse(BaseModel):
    external_job_id: str
    status: MediaScribeJobStatus
    reason_code: str | None = None


class MediaScribeSegment(BaseModel):
    sequence: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str
    source_role: str
    source_role_original: str | None = None


class MediaScribeDiarizationSegment(MediaScribeSegment):
    speaker_label: str


class MediaScribeResult(BaseModel):
    external_job_id: str
    language: str | None = None
    transcript: list[MediaScribeSegment] = Field(default_factory=list)
    diarization: list[MediaScribeDiarizationSegment] = Field(default_factory=list)
    summary_status: SummaryStatus = SummaryStatus.NOT_REQUESTED
    result_version: int = Field(default=1, ge=1)
