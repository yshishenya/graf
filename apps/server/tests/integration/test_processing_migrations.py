from twobrain_rec_server.db.base import Base
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


def test_processing_constraint_names_are_unique_per_table() -> None:
    for table in Base.metadata.sorted_tables:
        named_constraints = [constraint.name for constraint in table.constraints if constraint.name]

        assert len(named_constraints) == len(set(named_constraints)), table.name
