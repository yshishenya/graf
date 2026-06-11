from uuid import UUID

import pytest

from twobrain_rec_server.workflows.temporal_client import (
    processing_workflow_id,
    validate_processing_workflow_id,
)


def test_workflow_id_rejects_titles_paths_and_secrets() -> None:
    meeting_id = UUID("11111111-2222-3333-4444-555555555555")
    validate_processing_workflow_id(processing_workflow_id(meeting_id))
    unsafe_ids = [
        "processing/11111111-2222-3333-4444-555555555555/customer-title",
        "processing//Users/person/recording.wav",
        "processing/token-secret",
        "processing/11111111-2222-3333-4444-555555555555@example.com",
    ]
    for unsafe in unsafe_ids:
        with pytest.raises(ValueError):
            validate_processing_workflow_id(unsafe)
