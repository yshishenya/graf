"""Private corpus support; orchestration and model calls live in the shared runtime.

SourceReader never accepts or returns a production DSN. Its one-shot SSH bridge
uses the maintenance container's configuration inside a verified read-only transaction.
Snapshots/reviews are private data, NOT suitable for repr, logging or CLI output.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import stat
import tempfile
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import DateTime, Numeric, Uuid, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    create_summary_candidate,
)
from twobrain_rec_server.outcomes.prompts import canonical_json
from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY


async def _require_shadow_database(db, run_id=None):
    database = await db.scalar(text("select current_database()"))
    local_test = database.startswith("twobrain_rec_test_") and db.get_bind().url.host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    expected = (
        database == f"graf_protocol_eval_{run_id.hex}"
        if run_id
        else bool(re.fullmatch(r"graf_protocol_eval_[a-f0-9]{32}", database))
    )
    if not (expected or local_test):
        raise OutcomeGenerationTerminalError("evaluation_shadow_database_required")


async def snapshot_source(db, meeting_id=None):
    """Self-contained production-compatible function sent over stdin, never installed.

    No semantic exclusions: available/partial requires the reviewer's full read.
    Recheck owner activity and membership before private content. No user rows
    leave the source. Missing rows are also an access-revocation signal.
    """
    from datetime import datetime
    from decimal import Decimal
    from hashlib import sha256
    from uuid import UUID

    from sqlalchemy import select
    from sqlalchemy.orm import load_only

    from twobrain_rec_server.db.models import (
        DiarizationSegment,
        MediaRevision,
        Meeting,
        MeetingSpeakerName,
        ProcessingResult,
        TranscriptSegment,
        UserIdentity,
        WorkspaceMembership,
    )
    from twobrain_rec_server.outcomes.generator import canonical_transcript
    from twobrain_rec_server.outcomes.prompts import canonical_json
    from twobrain_rec_server.outcomes.service import load_outcome_transcript_segments
    from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting
    from twobrain_rec_server.processing.results import (
        latest_processing_result_query,
        result_is_complete,
    )

    fields = {
        Meeting: (
            "id",
            "workspace_id",
            "created_by_user_id",
            "title",
            "title_source",
            "title_updated_at",
            "started_at",
            "ended_at",
            "duration_seconds",
            "recording_display_timezone_offset_minutes",
            "status",
            "processing_status",
            "visibility",
            "share_policy_state",
            "download_policy_state",
            "deletion_state",
            "deletion_epoch",
            "deletion_requested_at",
            "deleted_at",
            "updated_at",
        ),
        MediaRevision: (
            "id",
            "revision_number",
            "source_kind",
            "status",
            "manifest_sha256",
            "track_sha256_by_role",
            "duration_seconds",
            "immutable",
            "accepted_at",
            "updated_at",
        ),
        ProcessingResult: (
            "id",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_workflow_id",
            "deletion_epoch_at_start",
            "result_version",
            "status",
            "transcript_status",
            "diarization_status",
            "language",
            "segment_count",
            "diarization_segment_count",
            "failure_reason",
            "source_result_hash",
            "imported_at",
            "created_at",
            "updated_at",
        ),
        TranscriptSegment: (
            "id",
            "sequence",
            "start_seconds",
            "end_seconds",
            "text",
            "source_role",
            "source_role_original",
        ),
        DiarizationSegment: (
            "id",
            "sequence",
            "start_seconds",
            "end_seconds",
            "text",
            "source_role",
            "speaker_label",
            "words_json",
        ),
        MeetingSpeakerName: ("id", "speaker_key", "display_name", "updated_at"),
    }
    if db is None:
        return {model.__name__: names for model, names in fields.items()}

    def serial(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID | Decimal):
            return str(value)
        return value

    def record(model, row):
        return {name: serial(getattr(row, name)) for name in fields[model]} if row else None

    def columns(model):
        return load_only(*(getattr(model, name) for name in fields[model]), raiseload=True)

    fence_fields = (
        "id",
        "workspace_id",
        "created_by_user_id",
        "deletion_state",
        "deleted_at",
        "deletion_epoch",
        "deletion_requested_at",
        "updated_at",
    )
    query = (
        select(Meeting)
        .options(load_only(*(getattr(Meeting, name) for name in fence_fields), raiseload=True))
        .order_by(Meeting.id)
    )
    if meeting_id is not None:
        query = query.where(Meeting.id == UUID(str(meeting_id)))
    meetings = (await db.scalars(query)).all()
    snapshots = []
    for meeting in meetings:
        access = {
            "owner_active": bool(
                await db.scalar(
                    select(
                        select(UserIdentity.id)
                        .where(
                            UserIdentity.id == meeting.created_by_user_id,
                            UserIdentity.status == "active",
                        )
                        .exists()
                    )
                )
            ),
            "membership_active": bool(
                await db.scalar(
                    select(
                        select(WorkspaceMembership.user_id)
                        .where(
                            WorkspaceMembership.workspace_id == meeting.workspace_id,
                            WorkspaceMembership.user_id == meeting.created_by_user_id,
                            WorkspaceMembership.status == "active",
                        )
                        .exists()
                    )
                )
            ),
        }
        rows = {model.__name__: [] for model in fields}
        rows["Meeting"] = [{name: serial(getattr(meeting, name)) for name in fence_fields}]
        status = "deleted" if meeting_is_deleted_or_deleting(meeting) else "source_unavailable"
        if status != "deleted" and not all(access.values()):
            status = "inaccessible"
        transcript = "[]"
        if status not in {"deleted", "inaccessible"}:
            meeting = await db.scalar(
                select(Meeting).options(columns(Meeting)).where(Meeting.id == meeting.id)
            )
            rows["Meeting"] = [record(Meeting, meeting)]
            revision = await db.scalar(
                select(MediaRevision)
                .options(columns(MediaRevision))
                .where(
                    MediaRevision.workspace_id == meeting.workspace_id,
                    MediaRevision.meeting_id == meeting.id,
                    MediaRevision.status == "accepted",
                    MediaRevision.immutable.is_(True),
                )
                .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
            )
            if revision is not None:
                rows["MediaRevision"] = [record(MediaRevision, revision)]
            result = await db.scalar(
                latest_processing_result_query(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=revision.id if revision else None,
                ).options(columns(ProcessingResult))
            )
            if result is not None:
                rows["ProcessingResult"] = [record(ProcessingResult, result)]
                for model in (TranscriptSegment, DiarizationSegment, MeetingSpeakerName):
                    query = (
                        select(model)
                        .options(columns(model))
                        .where(
                            model.workspace_id == meeting.workspace_id,
                            model.meeting_id == meeting.id,
                        )
                    )
                    if model is MeetingSpeakerName:
                        query = query.order_by(model.speaker_key, model.id)
                    else:
                        query = query.where(model.processing_result_id == result.id).order_by(
                            model.sequence, model.id
                        )
                    rows[model.__name__] = [
                        record(model, row) for row in (await db.scalars(query)).all()
                    ]
                # Reuse the production speaker/compiler path, never reconstruct turns here.
                segments = await load_outcome_transcript_segments(db, result=result)
                transcript = canonical_transcript(segments)
                status = (
                    ("available" if result_is_complete(result) else "partial")
                    if segments
                    else "transcript_unavailable"
                )
        snapshot = {
            "meeting_id": str(meeting.id),
            "selection_status": status,
            "rows": rows,
            "canonical_transcript": transcript,
            "access": access,
        }
        snapshot["source_hash"] = sha256(canonical_json(snapshot).encode()).hexdigest()
        snapshots.append(
            {key: snapshot[key] for key in ("meeting_id", "selection_status", "source_hash")}
            if meeting_id is None
            else snapshot
        )
    if meeting_id is None:
        return snapshots
    if snapshots:
        return snapshots[0]
    snapshot = {
        "meeting_id": str(UUID(str(meeting_id))),
        "selection_status": "inaccessible",
        "rows": {model.__name__: [] for model in fields},
        "canonical_transcript": "[]",
        "access": {"owner_active": False, "membership_active": False},
    }
    snapshot["source_hash"] = sha256(canonical_json(snapshot).encode()).hexdigest()
    return snapshot


class SourceReader:
    def __init__(self, host: str, container: str, *, timeout_seconds: float = 120):
        # SSH joins remote arguments through a remote shell even though the local
        # subprocess is exec-only. Reject metacharacters and option injection.
        if not all(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) for value in (host, container)
        ):
            raise OutcomeGenerationTerminalError("evaluation_source_target_invalid")
        self.host, self.container, self.timeout_seconds = host, container, timeout_seconds
        self.source_gate = None

    async def _fetch(self, meeting_id):
        script = (
            inspect.getsource(snapshot_source)
            + "\n"
            + """
import asyncio, json, logging, sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
logging.disable(logging.CRITICAL)
class SourceGateError(RuntimeError):
    pass
async def main():
    engine = create_async_engine(
        get_settings().database_url, echo=False, hide_parameters=True,
        isolation_level="REPEATABLE READ",
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    try:
        async with async_sessionmaker(engine, autoflush=False)() as db:
            if await db.scalar(text("SHOW default_transaction_read_only")) != "on":
                raise SourceGateError("evaluation_source_readonly_required")
            if await db.scalar(text("SHOW transaction_read_only")) != "on":
                raise SourceGateError("evaluation_source_readonly_required")
            identity = (await db.execute(text("select current_user, session_user"))).one()
            if tuple(identity) != ("twobrain_rec_maintenance", "twobrain_rec_maintenance"):
                raise SourceGateError("evaluation_source_role_required")
            await apply_tenant_context(db, MaintenanceTenantContext(
                operation_name="operator_diagnostics", actor_id="graf-protocol-evaluator",
                reason_category="protocol_evaluation", feature_area="meeting_protocol",
            ))
            if await db.scalar(text("select rec_maintenance_allowed()")) is not True:
                raise SourceGateError("evaluation_source_context_required")
            if await db.scalar(text("SHOW row_security")) != "on":
                raise SourceGateError("evaluation_source_context_required")
            result = await snapshot_source(db, MEETING_ID)
            await db.rollback()
            return {"source_gate": {"role": "twobrain_rec_maintenance",
                    "context": "operator_diagnostics", "read_only": True, "rls": True},
                    "result": result}
    finally:
        await engine.dispose()
try:
    result = asyncio.run(main())
except SourceGateError as exc:
    result = {"error": str(exc)}
except BaseException:
    sys.exit(1)
sys.stdout.write(json.dumps(result, ensure_ascii=False))
""".replace("MEETING_ID", repr(meeting_id))
        )
        process = None
        self.source_gate = None
        try:
            process = await asyncio.create_subprocess_exec(
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=15",
                "--",
                self.host,
                "docker",
                "exec",
                "-i",
                self.container,
                "python",
                "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(script.encode()), self.timeout_seconds
            )
            if process.returncode != 0:
                raise ValueError
            response = json.loads(stdout)
            if response.get("error") in {
                "evaluation_source_readonly_required",
                "evaluation_source_role_required",
                "evaluation_source_context_required",
            }:
                raise OutcomeGenerationTerminalError(response["error"])
            gate = response.get("source_gate")
            if gate != {
                "role": "twobrain_rec_maintenance",
                "context": "operator_diagnostics",
                "read_only": True,
                "rls": True,
            }:
                raise OutcomeGenerationTerminalError("evaluation_source_context_required")
            self.source_gate = gate
            return response["result"]
        except OutcomeGenerationTerminalError:
            raise
        except asyncio.CancelledError:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            raise
        except Exception:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            raise OutcomeGenerationTerminalError("evaluation_source_read_failed") from None

    async def inventory(self) -> list[dict]:
        rows = await self._fetch(None)
        if not isinstance(rows, list):
            raise OutcomeGenerationTerminalError("evaluation_source_read_failed")
        return rows

    async def read(self, meeting_id: UUID | str) -> dict:
        try:
            identifier = str(UUID(str(meeting_id)))
        except (ValueError, TypeError):
            raise OutcomeGenerationTerminalError("evaluation_source_id_invalid") from None
        snapshot = await self._fetch(identifier)
        try:
            body = {key: value for key, value in snapshot.items() if key != "source_hash"}
            valid = (
                snapshot["meeting_id"] == identifier
                and snapshot["source_hash"] == sha256(canonical_json(body).encode()).hexdigest()
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise OutcomeGenerationTerminalError("evaluation_source_read_failed")
        return snapshot

    async def check(self, meeting_id: UUID | str, expected_hash: str) -> None:
        snapshot = await self.read(meeting_id)
        if snapshot["selection_status"] not in {"available", "partial"}:
            raise OutcomeGenerationTerminalError("evaluation_source_unavailable")
        if snapshot["source_hash"] != expected_hash:
            raise OutcomeGenerationTerminalError("evaluation_source_changed")


async def mirror_source(
    db: AsyncSession, snapshot: dict, run_id: UUID | str, *, create_attempt: bool = True
):
    """Insert once in a dedicated migrated shadow DB; caller owns commit/rollback.

    Keep source/segment UUIDs so canonical references remain exact; synthetic
    identities/jobs never reuse production accounts. A new run needs a fresh DB.
    With create_attempt=False return the meeting so the real HTTP route can
    create and dispatch the attempt; the evaluation worker still guards egress.
    """
    from twobrain_rec_server.db.models import (
        DiarizationSegment,
        MediaRevision,
        MediaScribeJob,
        Meeting,
        MeetingSpeakerName,
        Organization,
        ProcessingResult,
        ProcessingWorkflow,
        RegisteredDevice,
        TranscriptSegment,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
    )
    from twobrain_rec_server.outcomes.generator import canonical_transcript
    from twobrain_rec_server.outcomes.service import load_outcome_transcript_segments

    try:
        run_id = UUID(str(run_id))
        await _require_shadow_database(db, run_id)
        body = {key: value for key, value in snapshot.items() if key != "source_hash"}
        if snapshot["source_hash"] != sha256(canonical_json(body).encode()).hexdigest():
            raise OutcomeGenerationTerminalError("evaluation_source_changed")
        if snapshot["selection_status"] not in {"available", "partial"}:
            raise OutcomeGenerationTerminalError("evaluation_source_unavailable")
        meeting_id = UUID(snapshot["meeting_id"])
        rows = snapshot["rows"]
        allowed = await snapshot_source(None)
        if (
            set(rows) != set(allowed)
            or any(set(row) != set(allowed[model]) for model in rows for row in rows[model])
            or any(
                len(rows[model]) != 1 for model in ("Meeting", "MediaRevision", "ProcessingResult")
            )
        ):
            raise OutcomeGenerationTerminalError("evaluation_source_invalid")
        if rows["Meeting"][0]["id"] != str(meeting_id):
            raise OutcomeGenerationTerminalError("evaluation_source_invalid")
        existing = await db.get(Meeting, meeting_id)
        if existing is not None:
            raise OutcomeGenerationTerminalError("evaluation_shadow_source_exists")
        # Fresh synthetic FK graph per meeting, no source user/device/workspace rows.
        org_id, workspace_id, user_id, device_id, workflow_id, job_id = (uuid4() for _ in range(6))
        db.add(Organization(id=org_id, slug=f"eval-{org_id.hex}", name="Protocol evaluation"))
        await db.flush()
        db.add_all(
            [
                Workspace(
                    id=workspace_id,
                    organization_id=org_id,
                    slug=f"eval-{workspace_id.hex}",
                    name="Protocol evaluation",
                ),
                UserIdentity(
                    id=user_id,
                    organization_id=org_id,
                    external_subject=f"evaluation:{run_id}:{user_id}",
                    display_name="Evaluation",
                ),
            ]
        )
        await db.flush()
        db.add(
            WorkspaceMembership(
                workspace_id=workspace_id, user_id=user_id, role="owner", status="active"
            )
        )
        db.add(
            RegisteredDevice(
                id=device_id,
                workspace_id=workspace_id,
                user_id=user_id,
                device_public_id=f"eval-{device_id.hex}",
            )
        )
        await db.flush()

        def clone(model, source, **overrides):
            values = {**source, **overrides}
            for key, value in values.items():
                column = model.__table__.columns[key]
                if value is not None:
                    if isinstance(column.type, Uuid):
                        values[key] = UUID(str(value))
                    elif isinstance(column.type, DateTime):
                        values[key] = (
                            datetime.fromisoformat(value) if isinstance(value, str) else value
                        )
                    elif isinstance(column.type, Numeric):
                        values[key] = Decimal(str(value))
            return model(**values)

        meeting = clone(
            Meeting,
            rows["Meeting"][0],
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            device_id=device_id,
            local_recording_id=f"evaluation:{run_id}:{meeting_id}",
        )
        db.add(meeting)
        await db.flush()
        revision = clone(
            MediaRevision,
            rows["MediaRevision"][0],
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            local_media_revision_id=f"evaluation:{meeting_id}",
        )
        db.add(revision)
        await db.flush()
        db.add(
            ProcessingWorkflow(
                id=workflow_id,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"evaluation:{workflow_id}",
                status="processed",
            )
        )
        await db.flush()
        db.add(
            MediaScribeJob(
                id=job_id,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow_id,
                status="ready",
                external_job_id=f"evaluation:{job_id}",
            )
        )
        await db.flush()
        result = clone(
            ProcessingResult,
            rows["ProcessingResult"][0],
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=revision.id,
            processing_workflow_id=workflow_id,
            mediascribe_job_id=job_id,
        )
        db.add(result)
        await db.flush()
        for model in (TranscriptSegment, DiarizationSegment, MeetingSpeakerName):
            links = {"workspace_id": workspace_id, "meeting_id": meeting_id}
            links.update(
                {"updated_by_user_id": user_id}
                if model is MeetingSpeakerName
                else {"processing_result_id": result.id}
            )
            db.add_all(clone(model, row, **links) for row in rows[model.__name__])
        await db.flush()
        transcript = canonical_transcript(await load_outcome_transcript_segments(db, result=result))
        if transcript != snapshot["canonical_transcript"]:
            raise OutcomeGenerationTerminalError("evaluation_shadow_transcript_mismatch")
        if not create_attempt:
            return meeting
        attempt = await create_summary_candidate(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            requested_by_user_id=user_id,
            template_key="graf-auto-v1",
            template_id=None,
            template_version=BUILT_IN_BY_KEY["graf-auto-v1"].version,
            expected_current_outcome_set_id=None,
            request_intent="manual_refresh",
            request_intent_id=uuid5(run_id, str(meeting_id)),
        )
        attempt.metadata_json = {
            **attempt.metadata_json,
            "evaluation_only": True,
            "evaluation_run_id": str(run_id),
            "evaluation_source": {
                "meeting_id": str(meeting_id),
                "snapshot_hash": snapshot["source_hash"],
            },
        }
        await db.flush()
        return attempt
    except OutcomeGenerationTerminalError:
        raise
    except Exception:
        # SQL/validation exceptions can carry private parameter values.
        raise OutcomeGenerationTerminalError("evaluation_shadow_mirror_failed") from None


async def purge_shadow_source(db: AsyncSession, meeting_id: UUID | str) -> None:
    """Idempotent local purge; never calls storage, production or observability.

    Caller commits. The existing outcome purge owns protocol/header cleanup;
    retain evaluation/prompt metadata and every GenerationCall for the observer.
    """
    from sqlalchemy import delete, select

    from twobrain_rec_server.db.models import (
        DiarizationSegment,
        Meeting,
        MeetingOutcomeGenerationAttempt,
        MeetingSpeakerName,
        MeetingSummarySlot,
        ProcessingResult,
        TranscriptSegment,
    )
    from twobrain_rec_server.deletion.service import _purge_meeting_outcomes

    try:
        await _require_shadow_database(db)
        meeting = await db.scalar(
            select(Meeting).where(Meeting.id == UUID(str(meeting_id))).with_for_update()
        )
        if meeting is None:
            return
        marker = meeting.local_recording_id.split(":")
        if len(marker) != 3 or marker[0] != "evaluation" or marker[2] != str(meeting.id):
            raise OutcomeGenerationTerminalError("evaluation_shadow_source_invalid")
        await _require_shadow_database(db, UUID(marker[1]))
        attempts = (
            await db.scalars(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.meeting_id == meeting.id,
                    MeetingOutcomeGenerationAttempt.workspace_id == meeting.workspace_id,
                )
            )
        ).all()
        if any(
            (attempt.metadata_json or {}).get("evaluation_only") is not True for attempt in attempts
        ):
            raise OutcomeGenerationTerminalError("evaluation_shadow_source_invalid")
        metadata = {attempt.id: dict(attempt.metadata_json) for attempt in attempts}
        if meeting.deleted_at is None:
            meeting.deletion_epoch += 1
            meeting.deleted_at = datetime.now(UTC)
        meeting.deletion_state = "deleted"
        meeting.deletion_requested_at = meeting.deletion_requested_at or meeting.deleted_at
        meeting.title = None
        meeting.current_outcome_set_id = None
        for model in (TranscriptSegment, DiarizationSegment, MeetingSpeakerName):
            await db.execute(
                delete(model).where(
                    model.meeting_id == meeting.id, model.workspace_id == meeting.workspace_id
                )
            )
        for result in (
            await db.scalars(
                select(ProcessingResult).where(
                    ProcessingResult.meeting_id == meeting.id,
                    ProcessingResult.workspace_id == meeting.workspace_id,
                )
            )
        ).all():
            result.transcript_status = result.diarization_status = "unavailable"
            result.segment_count = result.diarization_segment_count = 0
            result.failure_reason = "meeting_deleted"
        for slot in (
            await db.scalars(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.workspace_id == meeting.workspace_id,
                )
            )
        ).all():
            slot.current_outcome_set_id = None
        await _purge_meeting_outcomes(db, meeting=meeting)
        for attempt in attempts:
            attempt.metadata_json = {**metadata[attempt.id], "purged_for_deletion": True}
        await db.flush()
    except OutcomeGenerationTerminalError:
        raise
    except Exception:
        raise OutcomeGenerationTerminalError("evaluation_shadow_purge_failed") from None


class PrivateWorkdir:
    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        try:
            os.close(self._directory())
        except OSError:
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid") from None

    @staticmethod
    def _outside_checkout(path: Path):
        resolved = path.resolve()
        if any((parent / ".git").exists() for parent in (resolved, *resolved.parents)):
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid")

    @classmethod
    def create(cls, parent: Path, checkout: Path):
        parent, checkout = Path(parent).resolve(), Path(checkout).resolve()
        if parent == checkout or parent.is_relative_to(checkout):
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid")
        cls._outside_checkout(parent)
        try:
            path = Path(tempfile.mkdtemp(prefix="graf-protocol-eval-", dir=parent))
            os.chmod(path, 0o700)
            return cls(path)
        except OSError:
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid") from None

    def _directory(self):
        self._outside_checkout(self.path)
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info = os.fstat(fd)
        if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
            os.close(fd)
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid")
        return fd

    @staticmethod
    def _name(name):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", name):
            raise OutcomeGenerationTerminalError("evaluation_private_path_invalid")

    def write_json(self, name: str, value) -> Path:
        self._name(name)
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            fd = self._directory()
            try:
                output = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd
                )
                try:
                    with os.fdopen(output, "w", encoding="utf-8") as stream:
                        os.fchmod(stream.fileno(), 0o600)
                        stream.write(encoded)
                except OSError:
                    os.unlink(name, dir_fd=fd)
                    raise
            finally:
                os.close(fd)
        except (OSError, ValueError, TypeError):
            raise OutcomeGenerationTerminalError("evaluation_private_write_failed") from None
        return self.path / name

    def discard(self, name: str) -> None:
        self._name(name)
        try:
            fd = self._directory()
            try:
                os.unlink(name, dir_fd=fd)
            finally:
                os.close(fd)
        except FileNotFoundError:
            pass
        except OSError:
            raise OutcomeGenerationTerminalError("evaluation_private_cleanup_failed") from None

    def read_json(self, name: str):
        self._name(name)
        try:
            fd = self._directory()
            try:
                source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                with os.fdopen(source, "r", encoding="utf-8") as stream:
                    info = os.fstat(stream.fileno())
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or stat.S_IMODE(info.st_mode) != 0o600
                        or info.st_uid != os.getuid()
                        or info.st_nlink != 1
                    ):
                        raise ValueError
                    return json.load(stream)
            finally:
                os.close(fd)
        except (OSError, ValueError, TypeError):
            raise OutcomeGenerationTerminalError("evaluation_private_read_failed") from None


REVIEW_CRITERIA = (
    "topic_completeness",
    "factual_accuracy",
    "decisions",
    "actions",
    "owners",
    "deadlines",
    "objections",
    "constraints",
    "alternatives",
    "late_corrections",
    "speakers",
    "timestamps",
    "coherence",
    "practical_usefulness",
)
MEETING_TYPES = (
    "work",
    "official",
    "customer",
    "hr",
    "brainstorm",
    "retro_or_incident",
    "interview",
    "personal",
    "high_risk",
    "mixed_or_unknown",
)
EXCLUSION_REASONS = (
    "deleted",
    "inaccessible",
    "source_unavailable",
    "transcript_unavailable",
    "no_meaningful_speech",
    "unintelligible_speech",
)
Nonempty = Annotated[str, Field(min_length=1)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class ReviewRef(ReviewModel):
    transcript_segment_id: Nonempty
    sequence: int


class ReviewEvidence(ReviewModel):
    text: Nonempty
    source_refs: Annotated[list[ReviewRef], Field(min_length=1)]

    @model_validator(mode="after")
    def check_text(self):
        if not self.text.strip():
            raise ValueError("evaluation_review_invalid")
        return self


class CriterionReview(ReviewModel):
    verdict: Literal["pass", "fail"]
    assessment: Nonempty
    source_refs: Annotated[list[ReviewRef], Field(min_length=1)]
    errors: list[Nonempty]

    @model_validator(mode="after")
    def check_verdict(self):
        if not self.assessment.strip() or (self.verdict == "pass") == bool(self.errors):
            raise ValueError("evaluation_review_invalid")
        return self


class MeetingReview(ReviewModel):
    run_id: Nonempty
    meeting_id: Nonempty
    source_hash: Digest
    root_hash: Digest
    output_hash: Digest
    reviewer: Literal["Codex"]
    meeting_type: Nonempty
    full_transcript_read: bool
    independent_inventory: Annotated[list[ReviewEvidence], Field(min_length=1)]
    summary_answers: dict[str, ReviewEvidence]
    criteria: dict[str, CriterionReview]

    @model_validator(mode="after")
    def check_completeness(self):
        UUID(self.run_id)
        UUID(self.meeting_id)
        if (
            self.full_transcript_read is not True
            or set(self.criteria) != set(REVIEW_CRITERIA)
            or set(self.summary_answers) != {"subject", "result", "next_step"}
            or self.meeting_type not in MEETING_TYPES
            or len({item.assessment.strip() for item in self.criteria.values()})
            != len(REVIEW_CRITERIA)
        ):
            raise ValueError("evaluation_review_invalid")
        return self


CONTROL_CASES = (
    "informal_commitment", "conditional_commitment", "refused_commitment",
    "third_party_guess", "later_correction", "prompt_injection", "unknown_owner_and_due",
)


class ControlManifest(ReviewModel):
    run_id: Nonempty
    cases: dict[str, Nonempty]

    @model_validator(mode="after")
    def check_cases(self):
        UUID(self.run_id)
        if set(self.cases) != set(CONTROL_CASES) or len(set(self.cases.values())) != 7:
            raise ValueError("evaluation_controls_invalid")
        for identifier in self.cases.values():
            if str(UUID(identifier)) != identifier:
                raise ValueError("evaluation_controls_invalid")
        return self


class PrivatePrivacyReview(ReviewModel):
    run_id: Nonempty
    root_hash: Digest
    checked_at: Nonempty
    reviewer: Literal["Codex"]
    verdict: Literal["pass", "fail"]
    checks: dict[str, Nonempty]

    @model_validator(mode="after")
    def check_evidence(self):
        UUID(self.run_id)
        checked_at = datetime.fromisoformat(self.checked_at)
        if (checked_at.tzinfo is None or checked_at > datetime.now(UTC)
                or set(self.checks) != {"git", "logs", "workdir", "observability"}
                or any(not value.strip() for value in self.checks.values())):
            raise ValueError("evaluation_privacy_invalid")
        return self


def validate_review(
    value: dict, *, snapshot: dict, run_id: UUID | str, root_hash: str, output_hash: str
) -> MeetingReview:
    """Check structure/binding, not semantic truth; no automatic blanket PASS."""
    try:
        review = MeetingReview.model_validate(value)
        if (
            review.run_id != str(run_id)
            or review.meeting_id != snapshot["meeting_id"]
            or review.source_hash != snapshot["source_hash"]
            or review.root_hash != root_hash
            or review.output_hash != output_hash
            or snapshot["selection_status"] not in {"available", "partial"}
        ):
            raise ValueError
        known = {
            (row["transcript_segment_id"], row["sequence"])
            for row in json.loads(snapshot["canonical_transcript"])
        }
        evidence = [
            *review.independent_inventory,
            *review.summary_answers.values(),
            *review.criteria.values(),
        ]
        if any(
            (ref.transcript_segment_id, ref.sequence) not in known
            for item in evidence
            for ref in item.source_refs
        ):
            raise ValueError
        return review
    except (ValidationError, ValueError, TypeError, KeyError):
        raise OutcomeGenerationTerminalError("evaluation_review_invalid") from None


def aggregate_report(
    inventory: list[dict],
    reviews: list[MeetingReview],
    *,
    run_id: UUID | str,
    root_hash: str,
    review_bindings: dict[str, tuple[dict, str]] | None = None,
    exclusions: list[dict] = (),
) -> dict:
    """Only fixed-key counts leave the private boundary. Technical errors aren't exclusions.

    Caller re-inventories/rechecks sources before invoking this final gate.
    Exclusions require a current source hash and private reviewer rationale.
    """
    try:
        sources = {row["meeting_id"]: row for row in inventory}
        if len(sources) != len(inventory):
            raise ValueError
        seen, counts, types, reasons = set(), Counter(), Counter(), Counter()
        criteria = {key: {"pass": 0, "fail": 0} for key in REVIEW_CRITERIA}
        for review in reviews:
            snapshot, output_hash = (review_bindings or {})[review.meeting_id]
            review = validate_review(
                review.model_dump(), snapshot=snapshot, run_id=run_id,
                root_hash=root_hash, output_hash=output_hash,
            )
            current = sources[review.meeting_id]
            if (
                review.meeting_id in seen
                or review.run_id != str(run_id)
                or review.root_hash != root_hash
                or review.source_hash != current["source_hash"]
                or current["selection_status"] not in {"available", "partial"}
            ):
                raise ValueError
            seen.add(review.meeting_id)
            passed = all(item.verdict == "pass" for item in review.criteria.values())
            counts["passed" if passed else "failed"] += 1
            types[review.meeting_type] += 1
            for key, item in review.criteria.items():
                criteria[key][item.verdict] += 1
        for exclusion in exclusions:
            current = sources[exclusion["meeting_id"]]
            reason = exclusion["reason"]
            if (
                exclusion["meeting_id"] in seen
                or exclusion["run_id"] != str(run_id)
                or exclusion["source_hash"] != current["source_hash"]
                or reason not in EXCLUSION_REASONS
                or exclusion["reviewer"] != "Codex"
                or not exclusion["rationale"].strip()
            ):
                raise ValueError
            if reason in {"no_meaningful_speech", "unintelligible_speech"}:
                if exclusion["full_transcript_read"] is not True or current[
                    "selection_status"
                ] not in {"available", "partial"}:
                    raise ValueError
            elif reason != current["selection_status"]:
                raise ValueError
            seen.add(exclusion["meeting_id"])
            reasons[reason] += 1
        pending = len(sources) - len(seen)
        return {
            "found": len(sources),
            "reviewed": len(reviews),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "excluded": len(exclusions),
            "pending": pending,
            "complete": bool(sources) and pending == 0 and counts["failed"] == 0,
            "meeting_types": dict(types),
            "criteria": criteria,
            "exclusion_reasons": dict(reasons),
        }
    except (ValidationError, ValueError, KeyError, TypeError, AttributeError, OutcomeGenerationTerminalError):
        raise OutcomeGenerationTerminalError("evaluation_report_invalid") from None


async def _final_output(db, attempt, settings, run_id, snapshot, output):
    """Reuse publication proof validation without publishing or committing anything."""
    from sqlalchemy import select

    from twobrain_rec_server.db.models import GenerationCall
    from twobrain_rec_server.outcomes import ai_service

    _, attempt = await ai_service._lock_candidate_meeting_and_attempt(
        db, workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
    )
    metadata = attempt.metadata_json or {}
    if (
        metadata.get("evaluation_only") is not True
        or metadata.get("evaluation_run_id") != str(run_id)
        or metadata.get("evaluation_source") != {
            "meeting_id": snapshot["meeting_id"], "snapshot_hash": snapshot["source_hash"],
        }
        or attempt.status != "candidate" or attempt.failure_code is not None
    ):
        raise OutcomeGenerationTerminalError("evaluation_result_not_ready")
    prompt = ai_service._stored_prompt_snapshot(attempt)
    if prompt is None or prompt.root_prompt_version != settings.outcome_root_prompt_version:
        raise OutcomeGenerationTerminalError("evaluation_root_mismatch")
    calls = (await db.scalars(select(GenerationCall).where(
        GenerationCall.workspace_id == attempt.workspace_id,
        GenerationCall.meeting_id == attempt.meeting_id,
        GenerationCall.candidate_id == attempt.candidate_id,
    ).order_by(GenerationCall.call_sequence, GenerationCall.provider_attempt))).all()
    stages = [await ai_service._latest_protocol_call(db, attempt, sequence) for sequence in (1, 2, 3)]
    if any(call is None or call.call_state != "completed" for call in stages):
        raise OutcomeGenerationTerminalError("evaluation_calls_not_ready")
    stage_ids = {call.id for call in stages}
    if any(
        call.call_sequence not in {1, 2, 3} or call.completed_at is None
        or call.export_status != (
            "confirmed" if ai_service._generation_call_is_publishable(call) else "not_required"
        )
        or (call.id not in stage_ids and (
            call.call_state != "failed" or not ai_service._generation_call_is_retryable(call)
        ))
        or call.transcript_text != snapshot["canonical_transcript"] for call in calls
    ):
        raise OutcomeGenerationTerminalError("evaluation_calls_not_ready")
    outcome = await ai_service.publish_model_generated_outcome(
        db, workspace_id=attempt.workspace_id, meeting_id=attempt.meeting_id,
        candidate_id=attempt.candidate_id, expected_current_outcome_set_id=None,
        publication_proof=ai_service._protocol_publication_proof(attempt, *stages),
        validate_only=True, settings=settings,
    )
    expected = {
        "run_id": str(run_id), "meeting_id": snapshot["meeting_id"],
        "candidate_id": str(attempt.candidate_id), "source_hash": snapshot["source_hash"],
        "root_hash": prompt.root_bundle_hash, "output_hash": outcome.content_hash,
        "state": "candidate", "failure_code": None, "protocol": outcome.protocol_json,
    }
    if outcome.status != "available" or any(output.get(key) != value for key, value in expected.items()):
        raise OutcomeGenerationTerminalError("evaluation_output_mismatch")
    return prompt.root_bundle_hash, {
        "meeting_id": snapshot["meeting_id"], "source_hash": snapshot["source_hash"],
        "candidate_id": str(attempt.candidate_id), "output_hash": outcome.content_hash,
        "calls": [{"call_id": str(call.id), "validated_result_hash": call.validated_result_hash}
                  for call in stages],
    }


def evaluation_sample(workdir, run_id):
    """Read the sample pinned in authority, never a late selection of passing outputs."""
    from twobrain_rec_server.outcomes.prompt_bundle import (
        RepresentativeSample,
        validate_evaluation_snapshot,
    )

    try:
        saved = workdir.read_json("root-authority.json")
        _, authority = validate_evaluation_snapshot(saved)
        if authority["run_id"] != str(run_id):
            raise ValueError
        sample = saved.get("sample_manifest")
        path = workdir.path / "sample-manifest.json"
        if sample is None:
            if path.exists():
                raise ValueError
            return None
        if workdir.read_json("sample-manifest.json") != sample:
            raise ValueError
        result = RepresentativeSample.model_validate(sample)
        inventory = workdir.read_json("inventory.json")
        if inventory.get("run_id") != str(run_id) or sha256(canonical_json(inventory).encode()).hexdigest() != result.inventory_hash:
            raise ValueError
        return result
    except Exception:
        raise OutcomeGenerationTerminalError("evaluation_sample_invalid") from None


def validate_sample_source(sample, snapshot):
    if sample is None:
        return
    identifier = snapshot["meeting_id"]
    selected = {row.meeting_id: row for row in sample.real_sources}
    if identifier not in selected and identifier not in sample.controls.values():
        raise OutcomeGenerationTerminalError("evaluation_sample_source_invalid")
    if identifier in selected and (snapshot["source_hash"] != selected[identifier].source_hash
                                   or snapshot["selection_status"] not in {"available", "partial"}):
        raise OutcomeGenerationTerminalError("evaluation_source_changed")
    if identifier == sample.long_meeting_id:
        try:
            duration = float(snapshot["rows"]["MediaRevision"][0]["duration_seconds"])
            if not 3600 <= duration < float("inf"):
                raise ValueError
        except (KeyError, TypeError, ValueError, IndexError, OverflowError):
            raise OutcomeGenerationTerminalError("evaluation_sample_long_required") from None


async def finalize_run(settings, sessionmaker, reader, workdir, run_id) -> dict:
    """Revalidate the complete live corpus and durable results at a fresh cutoff.

    The source is read-only. Only invalidated *evaluation* working copies may
    be purged; GenerationCall and observability are never modified. No inference,
    prompt fetch, accepted publication or automatic semantic PASS happens here.
    """
    from sqlalchemy import select

    from twobrain_rec_server.cli.meeting_protocol_eval_runtime import verify_isolated_runtime
    from twobrain_rec_server.db.models import MeetingOutcomeGenerationAttempt
    from twobrain_rec_server.outcomes.prompt_bundle import (
        FinalCorpusReport,
        validate_evaluation_snapshot,
    )

    run_id = UUID(str(run_id))
    try:
        await verify_isolated_runtime(settings, sessionmaker, run_id)
    except OutcomeGenerationTerminalError:
        raise
    except Exception:
        raise OutcomeGenerationTerminalError("evaluation_report_invalid") from None
    if type(settings.outcome_root_prompt_version) is not int:
        raise OutcomeGenerationTerminalError("evaluation_root_mismatch")
    saved = workdir.read_json("inventory.json")
    if not isinstance(saved, dict) or not isinstance(saved.get("meetings"), list):
        raise OutcomeGenerationTerminalError("evaluation_inventory_invalid")
    if saved.get("run_id") != str(run_id):
        raise OutcomeGenerationTerminalError("evaluation_run_mismatch")

    def indexed(rows):
        try:
            result = {}
            for row in rows:
                identifier = str(UUID(row["meeting_id"]))
                if identifier in result or not re.fullmatch(r"[a-f0-9]{64}", row["source_hash"]):
                    raise ValueError
                result[identifier] = row
            return result
        except (ValueError, TypeError, KeyError, AttributeError):
            raise OutcomeGenerationTerminalError("evaluation_inventory_invalid") from None

    async def inventory():
        try:
            return indexed(await reader.inventory())
        except Exception:
            raise OutcomeGenerationTerminalError("evaluation_inventory_unavailable") from None

    original, current = indexed(saved["meetings"]), await inventory()
    sample = evaluation_sample(workdir, run_id)
    selected = {row.meeting_id for row in sample.real_sources} if sample else None
    errors, snapshots, reviews, bindings, exclusions = Counter(), {}, {}, {}, {}
    pending_reviews, receipts, controls = {}, {}, []
    root_hash = None
    manifest = None
    try:
        manifest = ControlManifest.model_validate(workdir.read_json("controls.json"))
        if manifest.run_id != str(run_id) or set(manifest.cases.values()) & (original.keys() | current.keys()):
            raise ValueError
        if sample is not None and manifest.cases != sample.controls:
            raise ValueError
    except Exception:
        errors["evaluation_controls_invalid" if (workdir.path / "controls.json").exists()
               else "evaluation_controls_missing"] += 1
        manifest = None
    control_ids = set(manifest.cases.values()) if manifest else set()
    async def attempt_index():
        try:
            async with sessionmaker() as db:
                attempts = (await db.scalars(select(MeetingOutcomeGenerationAttempt).order_by(
                    MeetingOutcomeGenerationAttempt.id,
                ))).all()
            result = {}
            for attempt in attempts:
                metadata = attempt.metadata_json or {}
                if metadata.get("evaluation_run_id") != str(run_id) or metadata.get("evaluation_only") is not True:
                    raise OutcomeGenerationTerminalError("evaluation_run_mismatch")
                result.setdefault(str(attempt.meeting_id), []).append(attempt.id)
            return result
        except OutcomeGenerationTerminalError:
            raise
        except Exception:
            raise OutcomeGenerationTerminalError("evaluation_report_invalid") from None

    by_meeting = await attempt_index()
    if selected is not None and set(by_meeting) - selected - control_ids:
        errors["evaluation_sample_source_invalid"] += 1

    async def invalidate(identifier):
        # Both cleanup channels must run even if one file/channel fails.
        failed = False
        for prefix in ("source", "output", "review", "inventory-notes", "exclusion"):
            try:
                workdir.discard(f"{prefix}-{identifier}.json")
            except Exception:
                failed = True
        try:
            async with sessionmaker() as db:
                await purge_shadow_source(db, identifier)
                await db.commit()
        except Exception:
            failed = True
        if failed:
            errors["evaluation_private_cleanup_failed"] += 1
        reviews.pop(identifier, None)
        pending_reviews.pop(identifier, None)
        bindings.pop(identifier, None)
        exclusions.pop(identifier, None)

    def excluded_source(identifier, snapshot):
        exclusions[identifier] = {
            "meeting_id": identifier, "run_id": str(run_id), "source_hash": snapshot["source_hash"],
            "reason": snapshot["selection_status"], "reviewer": "Codex",
            "rationale": "Текущее состояние источника подтверждено повторным чтением.",
        }

    for identifier in sorted(selected if selected is not None else (current.keys() | original.keys() | by_meeting.keys()) - control_ids):
        try:
            snapshot = await reader.read(identifier)
            if snapshot["meeting_id"] != identifier:
                raise ValueError
            snapshots[identifier] = snapshot
        except Exception:
            errors["evaluation_source_read_failed"] += 1
            continue
        if snapshot["selection_status"] in {"deleted", "inaccessible"}:
            await invalidate(identifier)
            if sample:
                errors["evaluation_source_changed"] += 1
            else:
                excluded_source(identifier, snapshot)
            continue
        try:
            validate_sample_source(sample, snapshot)
        except OutcomeGenerationTerminalError as exc:
            errors[str(exc)] += 1
            continue
        if any(row["source_hash"] != snapshot["source_hash"] for row in (
            original.get(identifier), current.get(identifier),
        ) if row is not None):
            await invalidate(identifier)
            errors["evaluation_source_changed"] += 1
            continue
        try:
            exclusion_name = f"exclusion-{identifier}.json"
            if (workdir.path / exclusion_name).exists():
                if sample:
                    raise ValueError
                exclusions[identifier] = workdir.read_json(exclusion_name)
                continue
            names = [f"{prefix}-{identifier}.json" for prefix in ("source", "output", "review")]
            if not all((workdir.path / name).exists() for name in names) or identifier not in by_meeting:
                continue  # New/unreviewed meetings remain in the final denominator.
            if len(by_meeting[identifier]) != 1 or snapshot.get("access") != {
                "owner_active": True, "membership_active": True,
            }:
                raise ValueError
            source, output, review = (workdir.read_json(name) for name in names)
            if source != snapshot:
                await invalidate(identifier)
                errors["evaluation_source_changed"] += 1
                continue
            pending_reviews[identifier] = (snapshot, output, review)
        except Exception:
            errors["evaluation_result_invalid"] += 1

    # One final read-only inventory supplies the cutoff for every earlier read,
    # including revocations during validation and newly created meetings.
    cutoff = await inventory()
    cutoff_at = datetime.now(UTC).isoformat()
    for identifier in sorted(selected if selected is not None else snapshots.keys() | cutoff.keys()):
        before, after = snapshots.get(identifier), cutoff.get(identifier)
        if before is None:
            if after is not None and after["selection_status"] in {"deleted", "inaccessible"}:
                await invalidate(identifier)
                if sample:
                    errors["evaluation_source_changed"] += 1
                else:
                    excluded_source(identifier, after)
            continue
        if after is None or after["source_hash"] != before["source_hash"]:
            await invalidate(identifier)
            if sample:
                errors["evaluation_source_changed"] += 1
            elif after is not None and after["selection_status"] in {"deleted", "inaccessible"}:
                excluded_source(identifier, after)
            else:
                errors["evaluation_source_changed"] += 1
        if after is None:
            # An entry disappearing from the source cannot erase an unfinished review.
            cutoff[identifier] = {key: before[key] for key in ("meeting_id", "source_hash", "selection_status")}
    for identifier, (snapshot, output, review) in pending_reviews.items():
        try:
            async with sessionmaker() as db:
                attempt = await db.get(MeetingOutcomeGenerationAttempt, by_meeting[identifier][0])
                current_root, receipt = await _final_output(db, attempt, settings, run_id, snapshot, output)
            if root_hash is not None and root_hash != current_root:
                raise ValueError
            root_hash = current_root
            reviews[identifier] = validate_review(
                review, snapshot=snapshot, run_id=run_id, root_hash=root_hash, output_hash=receipt["output_hash"],
            )
            bindings[identifier] = (snapshot, receipt["output_hash"])
            receipts[identifier] = {**receipt, "criteria": {
                key: item.verdict for key, item in reviews[identifier].criteria.items()
            }}
        except Exception:
            errors["evaluation_result_invalid"] += 1
    report_inventory = [row for identifier, row in cutoff.items() if selected is None or identifier in selected]
    try:
        report = aggregate_report(
            report_inventory, list(reviews.values()), run_id=run_id, root_hash=root_hash or "",
            review_bindings=bindings, exclusions=list(exclusions.values()),
        )
    except OutcomeGenerationTerminalError:
        errors["evaluation_report_invalid"] += 1
        report = aggregate_report(report_inventory, [], run_id=run_id, root_hash=root_hash or "")
    if manifest:
        for case_id, identifier in manifest.cases.items():
            try:
                # Controls are synthetic run-owned sources, never production meetings.
                # Reuse the full ledger/source/publication proof, not a supplied PASS.
                if identifier in cutoff or len(by_meeting.get(identifier, [])) != 1:
                    raise ValueError
                snapshot = workdir.read_json(f"control-source-{identifier}.json")
                if (snapshot["meeting_id"] != identifier or snapshot["source_hash"] != sha256(
                    canonical_json({key: value for key, value in snapshot.items() if key != "source_hash"}).encode()
                ).hexdigest() or workdir.read_json(f"source-{identifier}.json") != snapshot):
                    raise ValueError
                output = workdir.read_json(f"output-{identifier}.json")
                async with sessionmaker() as db:
                    attempt = await db.get(MeetingOutcomeGenerationAttempt, by_meeting[identifier][0])
                    current_root, receipt = await _final_output(db, attempt, settings, run_id, snapshot, output)
                if current_root != root_hash:
                    raise ValueError
                review = validate_review(
                    workdir.read_json(f"review-{identifier}.json"), snapshot=snapshot,
                    run_id=run_id, root_hash=root_hash, output_hash=receipt["output_hash"],
                )
                if any(item.verdict != "pass" for item in review.criteria.values()):
                    raise ValueError
                controls.append({key: value for key, value in receipt.items() if key != "meeting_id"}
                                | {"case_id": case_id, "verdict": "pass"})
            except Exception:
                errors["evaluation_control_invalid"] += 1
    # Recheck the run denominator too, not only previously selected candidate IDs.
    try:
        if await attempt_index() != by_meeting:
            errors["evaluation_result_invalid"] += 1
    except OutcomeGenerationTerminalError:
        errors["evaluation_result_invalid"] += 1
    privacy = None
    try:
        privacy = PrivatePrivacyReview.model_validate(workdir.read_json("privacy.json"))
        if privacy.run_id != str(run_id) or privacy.root_hash != root_hash or privacy.verdict != "pass":
            raise ValueError
    except Exception:
        errors["evaluation_privacy_invalid" if (workdir.path / "privacy.json").exists()
               else "evaluation_privacy_missing"] += 1
    result = {**report, "complete": report["complete"] and not errors,
              "errors": dict(errors), "cutoff_at": cutoff_at, "controls_passed": len(controls),
              "evaluation_scope": "representative" if sample else "full",
              "inventory_total": len(cutoff), "not_evaluated": len(cutoff) - len(report_inventory)}
    if result["complete"]:
        try:
            bundle, authority = validate_evaluation_snapshot(workdir.read_json("root-authority.json"))
            if (bundle.root.bundle_hash != root_hash or authority["run_id"] != str(run_id)
                    or authority["project_id"] != settings.langfuse_project_id
                    or authority["root_version"] != settings.outcome_root_prompt_version):
                raise ValueError
            qualified = FinalCorpusReport.model_validate({
                "schema_version": "graf-outcome-corpus-report-v1",
                **{key: authority[key] for key in ("run_id", "project_id", "root_name", "root_version",
                                                  "root_export_hash", "activation_hash", "runtime_hash")},
                "cutoff_at": cutoff_at, "inventory": list(cutoff.values()),
                "reviews": list(receipts.values()),
                "exclusions": [{key: row[key] for key in ("meeting_id", "source_hash", "reason")}
                               for row in exclusions.values()],
                "controls": controls, "privacy": privacy.model_dump(include={"checked_at", "reviewer", "verdict"}),
                "complete": True, "errors": {},
                "evaluation_scope": result["evaluation_scope"],
                "sample_manifest": sample.model_dump(mode="json") if sample else None,
                "sample_long_duration_seconds": float(snapshots[sample.long_meeting_id]["rows"]["MediaRevision"][0]["duration_seconds"]) if sample else None,
                "not_evaluated": [row for identifier, row in cutoff.items() if selected is not None and identifier not in selected],
            })
            result["qualification_report"] = qualified.model_dump(mode="json")
        except Exception:
            result["complete"] = False
            result["errors"]["evaluation_qualification_invalid"] = 1
    return result
