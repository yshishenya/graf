import re

from sqlalchemy import exists, select

from twobrain_rec_server.db.models import PurgeJournal

STRICT_UPLOAD_ATTEMPT = "strict_upload_attempt"

# Reserve the whole prefix, including malformed or partially restored attempt keys.
_MEETING = r"^organizations/[^/]+/workspaces/[^/]+/meetings/[^/]+/"
STRICT_UPLOAD_NAMESPACE = (
    _MEETING + r"(artifacts/media-revisions/[^/]+/attempts/|"
    r"sessions/[^/]+/tracks/[^/]+/parts/[^/]+/calendar-attempts/)"
)
_RESERVED_KEY = re.compile(STRICT_UPLOAD_NAMESPACE)


def is_strict_upload_key(key: str) -> bool:
    return _RESERVED_KEY.match(key) is not None


def strict_upload_read_blocked(artifact):
    return exists(select(PurgeJournal.id).where(
        PurgeJournal.workspace_id == artifact.workspace_id,
        PurgeJournal.meeting_id == artifact.meeting_id,
        PurgeJournal.object_key == artifact.storage_object_key,
        PurgeJournal.artifact_class == STRICT_UPLOAD_ATTEMPT,
        PurgeJournal.write_state == "accepted",
        PurgeJournal.state != "retained",
    ))


def strict_upload_attempt_query(workspace_id, meeting_id, key):
    return select(
        PurgeJournal.id, PurgeJournal.storage_epoch, PurgeJournal.storage_scope,
        PurgeJournal.media_revision_id, PurgeJournal.deletion_epoch,
        PurgeJournal.state, PurgeJournal.write_state,
    ).where(
        PurgeJournal.workspace_id == workspace_id,
        PurgeJournal.meeting_id == meeting_id,
        PurgeJournal.artifact_class == STRICT_UPLOAD_ATTEMPT,
        PurgeJournal.object_key == key,
    )
