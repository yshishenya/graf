from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaScribeJob,
    ProcessingAuditEvent,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)


def test_processing_models_are_registered_in_metadata() -> None:
    assert ProcessingWorkflow.__tablename__ == "processing_workflows"
    assert MediaScribeJob.__tablename__ == "mediascribe_jobs"
    assert ProcessingResult.__tablename__ == "processing_results"
    assert TranscriptSegment.__tablename__ == "transcript_segments"
    assert DiarizationSegment.__tablename__ == "diarization_segments"
    assert ProcessingAuditEvent.__tablename__ == "processing_audit_events"
    assert ProcessingDependencyState.__tablename__ == "processing_dependency_states"
