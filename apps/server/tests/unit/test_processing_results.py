from __future__ import annotations

import sqlite3
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import sqlite

from twobrain_rec_server.db.models import ProcessingResult
from twobrain_rec_server.processing.results import effective_processing_result_query


def _compiled_id_query(*, workspace_id: UUID, meeting_id: UUID, media_revision_id: UUID) -> str:
    query = effective_processing_result_query(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    ).with_only_columns(ProcessingResult.id)
    return str(
        query.limit(1).compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    )


def _insert_result(
    db: sqlite3.Connection,
    *,
    result_id: UUID,
    workflow_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    result_version: int,
    state: str,
) -> None:
    complete = state == "complete"
    db.execute(
        """
        INSERT INTO processing_results (
            id, processing_workflow_id, workspace_id, meeting_id, media_revision_id,
            result_version, status, transcript_status, segment_count,
            diarization_status, diarization_segment_count, imported_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_id.hex,
            workflow_id.hex,
            workspace_id.hex,
            meeting_id.hex,
            media_revision_id.hex,
            result_version,
            "failed" if state == "terminal" else "imported",
            "available" if state in {"partial", "complete"} else "unavailable",
            1 if state in {"partial", "complete"} else 0,
            "available" if complete else "unavailable",
            1 if complete else 0,
            "2026-08-30T12:00:00+00:00",
            "2026-08-30T12:00:00+00:00",
        ),
    )


@pytest.mark.parametrize(
    ("new_attempt_state", "expected_attempt"),
    [
        ("active", "old"),
        ("partial", "old"),
        ("terminal", "old"),
        ("complete", "new"),
    ],
)
def test_effective_result_keeps_old_complete_until_new_attempt_is_complete(
    new_attempt_state: str,
    expected_attempt: str,
) -> None:
    workspace_id = uuid4()
    meeting_id = uuid4()
    media_revision_id = uuid4()
    old_workflow_id = uuid4()
    new_workflow_id = uuid4()
    old_result_id = uuid4()
    new_result_id = uuid4()
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE processing_workflows (id TEXT PRIMARY KEY, attempt_ordinal INTEGER NOT NULL);
        CREATE TABLE processing_results (
            id TEXT PRIMARY KEY,
            processing_workflow_id TEXT,
            workspace_id TEXT NOT NULL,
            meeting_id TEXT NOT NULL,
            media_revision_id TEXT,
            result_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            transcript_status TEXT NOT NULL,
            segment_count INTEGER NOT NULL,
            diarization_status TEXT NOT NULL,
            diarization_segment_count INTEGER NOT NULL,
            imported_at TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    db.executemany(
        "INSERT INTO processing_workflows (id, attempt_ordinal) VALUES (?, ?)",
        [(old_workflow_id.hex, 1), (new_workflow_id.hex, 2)],
    )
    _insert_result(
        db,
        result_id=old_result_id,
        workflow_id=old_workflow_id,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        result_version=2,
        state="complete",
    )
    if new_attempt_state != "active":
        _insert_result(
            db,
            result_id=new_result_id,
            workflow_id=new_workflow_id,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            result_version=1,
            state=new_attempt_state,
        )

    selected = db.execute(
        _compiled_id_query(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    ).fetchone()

    assert selected == ((new_result_id if expected_attempt == "new" else old_result_id).hex,)
    db.close()


def test_effective_result_query_has_workflow_order_and_deterministic_tie_breakers() -> None:
    query = effective_processing_result_query(
        workspace_id=uuid4(),
        meeting_id=uuid4(),
        media_revision_id=uuid4(),
    ).with_only_columns(ProcessingResult.id)
    sql = " ".join(str(query.compile(dialect=sqlite.dialect())).split())

    assert (
        "JOIN processing_workflows ON processing_workflows.id = "
        "processing_results.processing_workflow_id"
    ) in sql
    assert (
        "ORDER BY processing_workflows.attempt_ordinal DESC, "
        "processing_results.result_version DESC, processing_results.imported_at DESC NULLS LAST, "
        "processing_results.created_at DESC, processing_results.id DESC"
    ) in sql
