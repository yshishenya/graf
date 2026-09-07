"""Synthetic protocol and exact root snapshots shared by protocol boundary tests."""

import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from tests.fixtures.outcome_prompts import desired_prompts, pin_model_settings
from twobrain_rec_server.db.models import MeetingOutcomeSet
from twobrain_rec_server.outcomes.ai_service import _content_hash, _enrich_protocol
from twobrain_rec_server.outcomes.models import (
    PROTOCOL_SCHEMA_VERSION,
    PROTOCOL_SECTIONS,
    OutcomeTranscriptSegment,
)
from twobrain_rec_server.outcomes.prompt_bundle import (
    OUTCOME_PROMPT_NAMES,
    ResolvedPromptBundle,
    build_root_bundle_document,
    build_root_export,
    load_root_export_bytes,
    snapshot_bundle_metadata,
    validate_root_bundle_document,
)
from twobrain_rec_server.outcomes.prompts import (
    EXTRACTOR_PROMPT_NAME,
    VERIFIER_PROMPT_NAME,
    validate_prompt_snapshot,
)


def extraction_result(segments):
    return {"facts": [
        {"kind": "context", "text": segment.text, "status": "stated", "acceptance_source_refs": [],
         "source_refs": [{"sequence": segment.sequence, "quote": None}]}
        for segment in segments
    ], "actions": []}


def protocol_result(segments):
    segment = segments[0]
    ref = {"sequence": segment.sequence, "quote": None}
    statement = {"text": segment.text, "source_refs": [ref]}
    return {
        "meeting_type": "work", "executive_summary": [statement], "objectives": [],
        "topics": [{
            "title": "Синтетическая тема", "context": [], "discussion": [statement],
            "proposals_and_alternatives": [], "outcome": [],
        }],
        "decisions": [], "action_items": [], "open_questions": [],
        "next_steps": [], "risks_and_constraints": [], "notes": [], "uncertain_sections": [],
    }


def protocol_outcome():
    source = OutcomeTranscriptSegment(
        segment_id=uuid4(), sequence=0, start_seconds=Decimal("12.5"), end_seconds=Decimal("18"),
        speaker_label="Участник 1", source_role="incoming_system", text="Обсудили ограничения пилота.",
    )
    header = {
        "title": "Проверка пилота", "started_at": None, "ended_at": None,
        "timezone_offset_minutes": None, "input_type": "transcript", "participants": [],
        "output_language": "ru", "detail_level": "detailed", "template_key": "graf-auto-v1",
        "template_version": 2, "template_name": "Авто", "sections": list(PROTOCOL_SECTIONS),
        "source_result_id": str(uuid4()),
    }
    document = _enrich_protocol(protocol_result([source]), header, [source])
    return MeetingOutcomeSet(
        id=uuid4(), workspace_id=uuid4(), meeting_id=uuid4(), media_revision_id=uuid4(),
        processing_result_id=uuid4(), status="available", lifecycle_state="active",
        protocol_state="available", protocol_schema_version=PROTOCOL_SCHEMA_VERSION,
        protocol_json=document, content_hash=_content_hash(document), source_kind="litellm", generator_kind="litellm",
        generator_version="meeting-protocol-v2", generated_at=datetime(2026, 9, 6, tzinfo=UTC), latency_ms=800,
    )


def protocol_bundle():
    definitions = desired_prompts()
    children = {}
    for name in OUTCOME_PROMPT_NAMES:
        prompt_type, prompt, config = definitions[name]
        children[name] = validate_prompt_snapshot(
            name=name, version=1, prompt_type=prompt_type, prompt=prompt, config=config,
        )
    root = validate_root_bundle_document(build_root_bundle_document(children), root_prompt_version=1)
    _, payload, _ = build_root_export(ResolvedPromptBundle(root, children, "langfuse_production"))
    return load_root_export_bytes(payload)


async def seed_accepted_protocol(db, meeting_id, *, text=None, make_default=True):
    """Use the fixture's canonical transcript; bypass inference only in UI tests."""
    from sqlalchemy import select

    from twobrain_rec_server.db.models import Meeting, MeetingSummarySlot, ProcessingResult
    from twobrain_rec_server.outcomes.service import load_outcome_transcript_segments

    meeting = await db.get(Meeting, meeting_id)
    result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
    segments = await load_outcome_transcript_segments(db, result=result)
    outcome = protocol_outcome()
    outcome.workspace_id = meeting.workspace_id
    outcome.meeting_id = meeting.id
    outcome.processing_result_id = result.id
    outcome.media_revision_id = result.media_revision_id
    outcome.template_key = "graf-auto-v1"
    outcome.template_version = 2
    outcome.revision_state = "accepted"
    outcome.accepted_at = datetime.now(UTC)
    outcome.deletion_epoch_at_start = meeting.deletion_epoch or 0
    outcome.source_result_hash = result.source_result_hash
    header = {**outcome.protocol_json["header"], "source_result_id": str(result.id)}
    outcome.protocol_json = _enrich_protocol(protocol_result(segments), header, segments)
    if text is not None:
        outcome.protocol_json["executive_summary"][0]["text"] = text
    outcome.content_hash = _content_hash(outcome.protocol_json)
    db.add(outcome)
    await db.flush()
    if make_default:
        slot = await db.scalar(select(MeetingSummarySlot).where(
            MeetingSummarySlot.meeting_id == meeting.id, MeetingSummarySlot.template_key == outcome.template_key,
        ))
        if slot is None:
            slot = MeetingSummarySlot(
                workspace_id=meeting.workspace_id, meeting_id=meeting.id, template_key=outcome.template_key,
                is_meeting_default=True, default_resolution_source="explicit_meeting",
                default_resolution_version="synthetic:1", default_resolved_at=datetime.now(UTC),
            )
            db.add(slot)
        slot.current_outcome_set_id = outcome.id
        slot.current_binding_class = "verified_complete"
        meeting.current_outcome_set_id = outcome.id
    await db.commit()
    return outcome, segments


async def prepare_protocol_candidate(db, meeting_id, *, template_key="graf-auto-v1"):
    from hashlib import sha256

    from twobrain_rec_server.db.models import Meeting
    from twobrain_rec_server.outcomes import ai_service
    from twobrain_rec_server.outcomes.generator import canonical_transcript
    from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY

    meeting = await db.get(Meeting, meeting_id)
    attempt = await ai_service.create_summary_candidate(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
        requested_by_user_id=meeting.created_by_user_id, template_key=template_key,
        template_id=None, template_version=BUILT_IN_BY_KEY[template_key].version,
        expected_current_outcome_set_id=None,
    )
    await pin_protocol_authority(db, attempt)
    segments = await ai_service._candidate_segments(db, attempt)
    transcript = canonical_transcript(segments)
    attempt.temporal_transcript_hash = sha256(transcript.encode()).hexdigest()
    await db.commit()
    return attempt, segments


def protocol_gateway_response(snapshot, messages, result):
    from twobrain_rec_server.outcomes.generator import LiteLLMGenerationResult
    from twobrain_rec_server.outcomes.prompts import canonical_json

    return LiteLLMGenerationResult(
        request=snapshot.litellm_request(messages),
        raw_response={"model": snapshot.model, "provider": "synthetic", "choices": [{"finish_reason": "stop", "message": {"content": canonical_json(result)}}]},
        parsed_content=result, actual_model=snapshot.model, actual_provider="synthetic",
        provider_request_id="synthetic", token_usage={}, cost_details=None,
    )


async def pin_protocol_authority(db, attempt):
    from sqlalchemy import select

    from tests.fixtures.prompt_authority import promotion_row
    from twobrain_rec_server.db.models import PromptRootPromotion
    from twobrain_rec_server.outcomes.prompt_bundle import validate_promotion_row

    row = await db.scalar(select(PromptRootPromotion).where(
        PromptRootPromotion.project_id == "synthetic-project", PromptRootPromotion.is_current.is_(True),
    ))
    if row is None:
        row = promotion_row(root_version=1)
        db.add(row)
        await db.flush()
    bundle, authority = validate_promotion_row(row)
    pin_protocol_prompts(attempt, bundle=bundle)
    attempt.metadata_json = {**attempt.metadata_json, "execution_authority": authority}


def pin_protocol_prompts(attempt, *, bundle=None):
    bundle = bundle or protocol_bundle()
    draft = bundle.child(attempt.prompt_name)
    verifier = bundle.child(VERIFIER_PROMPT_NAME)
    extractor = bundle.child(EXTRACTOR_PROMPT_NAME)
    attempt.prompt_version = draft.version
    attempt.prompt_definition = draft.prompt
    attempt.prompt_config = draft.config
    attempt.prompt_hash = draft.canonical_hash
    attempt.prompt_source = draft.source
    attempt.metadata_json = {
        **attempt.metadata_json,
        "pipeline": "extract-synthesize-verify-v1",
        "prompt_bundle": snapshot_bundle_metadata(draft),
        "verifier_prompt": {
            "name": verifier.name, "version": verifier.version, "prompt": verifier.prompt,
            "config": verifier.config, "hash": verifier.canonical_hash, "source": verifier.source,
        },
        "extractor_prompt": {
            "name": extractor.name, "version": extractor.version, "prompt": extractor.prompt,
            "config": extractor.config, "hash": extractor.canonical_hash, "source": extractor.source,
        },
    }
    pin_model_settings(attempt)
    attempt.status = "generating"


def pin_evaluation_prompts(attempt, *, settings, workdir, run_id):
    from twobrain_rec_server.outcomes.prompt_bundle import (
        build_evaluation_snapshot,
        validate_evaluation_snapshot,
    )

    name = "root-authority.json"
    if not (workdir.path / name).exists():
        workdir.write_json(name, build_evaluation_snapshot(
            protocol_bundle(), project_id=settings.langfuse_project_id, run_id=run_id,
        ))
    bundle, authority = validate_evaluation_snapshot(workdir.read_json(name))
    pin_protocol_prompts(attempt, bundle=bundle)
    attempt.metadata_json = {
        **attempt.metadata_json, "evaluation_only": True, "evaluation_run_id": str(run_id),
        "execution_authority": authority,
    }


async def prepare_evaluation_candidate(source_sessions, runtime, meeting_id):
    from twobrain_rec_server.cli.meeting_protocol_eval import mirror_source, snapshot_source
    from twobrain_rec_server.outcomes import ai_service
    from twobrain_rec_server.outcomes.generator import canonical_transcript

    async with source_sessions() as db:
        source = await snapshot_source(db, meeting_id)
    async with runtime.sessions() as db:
        attempt = await mirror_source(db, source, runtime.run_id)
        pin_evaluation_prompts(attempt, settings=runtime.settings, workdir=runtime.workdir, run_id=runtime.run_id)
        segments = await ai_service._candidate_segments(db, attempt)
        attempt.temporal_transcript_hash = ai_service.sha256(canonical_transcript(segments).encode()).hexdigest()
        await db.commit()
        return attempt, segments


@contextmanager
def protocol_evaluation_runtime(tmp_path):
    """Reuse the final-cutoff test's exact, disposable evaluation database and workdir."""
    from types import SimpleNamespace

    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from tests.fixtures.postgres_test_database import disposable_postgres_admin_url, prepare_schema
    from twobrain_rec_server.cli.meeting_protocol_eval import PrivateWorkdir
    from twobrain_rec_server.config import Settings

    run_id = uuid4()
    database = f"graf_protocol_eval_{run_id.hex}"
    admin_url = disposable_postgres_admin_url()
    database_url = make_url(admin_url).set(database=database).render_as_string(hide_password=False)

    async def ddl(operation):
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                # Both the endpoint and this fresh UUID-only name belong to the test runner.
                await connection.execute(text(f'{operation} database "{database}"'))
        finally:
            await engine.dispose()

    asyncio.run(ddl("create"))
    engine = None
    try:
        prepare_schema(database_url)
        engine = create_async_engine(database_url, poolclass=NullPool, hide_parameters=True)
        workdir = PrivateWorkdir.create(tmp_path, tmp_path / "checkout")
        settings = Settings(
            env="protocol-evaluation", langfuse_environment="protocol-evaluation", outcome_root_prompt_version=1,
            temporal_task_queue=f"graf-protocol-eval-{run_id.hex}", langfuse_project_id="synthetic-project",
            litellm_base_url="https://example.invalid", outcome_evaluation_workdir=workdir.path,
        )
        yield SimpleNamespace(
            run_id=run_id, engine=engine, sessions=async_sessionmaker(engine, expire_on_commit=False),
            settings=settings, workdir=workdir,
        )
    finally:
        if engine is not None:
            asyncio.run(engine.dispose())
        asyncio.run(ddl("drop"))
