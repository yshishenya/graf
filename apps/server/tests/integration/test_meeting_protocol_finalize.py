"""Synthetic final-cutoff checks against the real three-call ledger in an exact eval DB."""

import asyncio
import threading
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    pin_evaluation_prompts,
    protocol_bundle,
    protocol_evaluation_runtime,
    protocol_gateway_response,
    protocol_result,
)
from tests.unit.test_meeting_protocol_eval import review_fixture
from twobrain_rec_server.cli import meeting_protocol_eval as evaluator
from twobrain_rec_server.db.models import (
    GenerationCall,
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    PromptRootPromotion,
    TranscriptSegment,
    UserIdentity,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME


@pytest.fixture
def final_case(client, tmp_path, monkeypatch, request):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-final-report")
    with protocol_evaluation_runtime(tmp_path) as runtime:
        run_id, engine, sessions, settings, workdir = (
            runtime.run_id, runtime.engine, runtime.sessions, runtime.settings, runtime.workdir,
        )
        representative = getattr(request, "param", None) == "representative"
        real_ids = [meeting_id]
        controls = {name: str(create_outcome_ready_meeting(client, f"synthetic-control-{name}"))
                    for name in evaluator.CONTROL_CASES}
        if representative:
            from twobrain_rec_server.outcomes.prompt_bundle import (
                build_evaluation_snapshot,
                build_root_export,
            )
            real_ids += [create_outcome_ready_meeting(client, f"synthetic-sample-{n}") for n in range(2)]
            create_outcome_ready_meeting(client, "synthetic-not-evaluated")

            async def sample_inventory():
                async with client.app_state["sessionmaker"]() as db:
                    media = await db.scalar(select(MediaRevision).where(MediaRevision.meeting_id == meeting_id))
                    media.duration_seconds = 3600
                    await db.commit()
                    return [row for row in await evaluator.snapshot_source(db)
                            if row["meeting_id"] not in controls.values()]

            inventory = {"run_id": str(run_id), "meetings": asyncio.run(sample_inventory())}
            workdir.write_json("inventory.json", inventory)
            bundle = protocol_bundle()
            _, _, export_hash = build_root_export(bundle)
            sample = {
                "schema_version": "graf-outcome-sample-v1", "run_id": str(run_id),
                "root_export_hash": export_hash,
                "inventory_hash": evaluator.sha256(evaluator.canonical_json(inventory).encode()).hexdigest(),
                "real_sources": [row for row in inventory["meetings"] if row["meeting_id"] in {str(i) for i in real_ids}],
                "long_meeting_id": str(meeting_id), "controls": controls,
            }
            workdir.write_json("sample-manifest.json", sample)
            workdir.write_json("root-authority.json", build_evaluation_snapshot(
                bundle, project_id=settings.langfuse_project_id, run_id=run_id, sample_manifest=sample,
            ))

        async def setup(meeting_id, *, corpus=True):
            async with client.app_state["sessionmaker"]() as db:
                snapshot = await evaluator.snapshot_source(db, meeting_id)
            async with sessions() as db:
                attempt = await evaluator.mirror_source(db, snapshot, run_id)
                pin_evaluation_prompts(attempt, settings=settings, workdir=workdir, run_id=run_id)
                segments = await ai_service._candidate_segments(db, attempt)
                attempt.temporal_transcript_hash = ai_service.sha256(canonical_transcript(segments).encode()).hexdigest()
                await db.commit()

            retry = getattr(request, "param", None) if corpus and not representative else None
            failed_once = False

            async def generate(_self, *, snapshot, messages, **_kwargs):
                nonlocal failed_once
                stage = 1 if snapshot.name == EXTRACTOR_PROMPT_NAME else 3 if snapshot.name == VERIFIER_PROMPT_NAME else 2
                if retry is not None and stage == retry[0] and not failed_once:
                    failed_once = True
                    raise ai_service.LiteLLMError(
                        "litellm_transport_error", retryable=True, egress_state=retry[1],
                        raw_response={"error": "synthetic temporary failure"}
                        if retry[1] == "response_received" else None,
                    )
                result = (extraction_result(segments) if stage == 1 else
                          {"verdict": "pass", "findings": []} if stage == 3 else protocol_result(segments))
                return protocol_gateway_response(snapshot, messages, result)

            async def guard():
                if representative:
                    async with client.app_state["sessionmaker"]() as db:
                        current = await evaluator.snapshot_source(db, meeting_id)
                    evaluator.validate_sample_source(evaluator.evaluation_sample(workdir, run_id), current)

            monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")
            monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
            async def execute():
                return await ai_service.execute_candidate_generation(
                    sessions, settings=settings, workspace_id=attempt.workspace_id,
                    candidate_id=attempt.candidate_id, expected_snapshot_hash=attempt.temporal_transcript_hash,
                    evaluation_source_guard=guard,
                )

            if retry is not None:
                with pytest.raises(ai_service.OutcomeGenerationDependencyError, match="litellm_transport_error"):
                    await execute()
            for _ in range(2):
                await execute()
            async with sessions() as db:
                attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
                outcome = await db.get(MeetingOutcomeSet, attempt.outcome_set_id)
                calls = (await db.scalars(select(GenerationCall).where(
                    GenerationCall.candidate_id == attempt.candidate_id,
                ).order_by(GenerationCall.call_sequence))).all()
                for call in calls:
                    if ai_service._generation_call_is_publishable(call):
                        call.export_status = "confirmed"
                await db.commit()
                root_hash = attempt.metadata_json["prompt_bundle"]["root_bundle_hash"]
                output = {
                    "run_id": str(run_id), "meeting_id": str(meeting_id),
                    "candidate_id": str(attempt.candidate_id), "source_hash": snapshot["source_hash"],
                    "root_hash": root_hash, "output_hash": outcome.content_hash,
                    "state": attempt.status, "failure_code": attempt.failure_code,
                    "protocol": outcome.protocol_json,
                }
                _, review = review_fixture()
                review.update({key: output[key] for key in ("run_id", "meeting_id", "source_hash", "root_hash", "output_hash")})
                ref = {"transcript_segment_id": str(segments[0].segment_id), "sequence": segments[0].sequence}
                for entry in [*review["independent_inventory"], *review["summary_answers"].values(), *review["criteria"].values()]:
                    entry["source_refs"] = [deepcopy(ref)]
                if corpus and not representative:
                    workdir.write_json("inventory.json", {"run_id": str(run_id), "meetings": [
                        {key: snapshot[key] for key in ("meeting_id", "source_hash", "selection_status")}
                    ]})
                elif not corpus:
                    workdir.write_json(f"control-source-{meeting_id}.json", snapshot)
                for prefix, value in (("source", snapshot), ("output", output), ("review", review), ("inventory-notes", {"synthetic": True})):
                    workdir.write_json(f"{prefix}-{meeting_id}.json", value)
                return snapshot, attempt.id, outcome.id, [call.id for call in calls]

        snapshot, attempt_id, outcome_id, call_ids = asyncio.run(setup(meeting_id))
        for identifier in real_ids[1:]:
            asyncio.run(setup(identifier))
        # Contract fixtures exercise real durable calls; these are not model-quality evidence.
        for identifier in controls.values():
            asyncio.run(setup(identifier, corpus=False))
        workdir.write_json("controls.json", {"run_id": str(run_id), "cases": controls})
        workdir.write_json("privacy.json", {
            "run_id": str(run_id), "root_hash": workdir.read_json(f"output-{meeting_id}.json")["root_hash"],
            "checked_at": datetime.now(UTC).isoformat(), "reviewer": "Codex", "verdict": "pass",
            "checks": {key: f"Synthetic {key} evidence" for key in ("git", "logs", "workdir", "observability")},
        })
        reads = []
        inventories = []

        async def read(identifier):
            reads.append(str(identifier))
            async with client.app_state["sessionmaker"]() as db:
                return await evaluator.snapshot_source(db, identifier)

        async def inventory():
            inventories.append(True)
            async with client.app_state["sessionmaker"]() as db:
                return [row for row in await evaluator.snapshot_source(db)
                        if row["meeting_id"] not in controls.values()]

        reader = SimpleNamespace(read=read, inventory=inventory)
        case = SimpleNamespace(
            meeting_id=meeting_id, run_id=run_id, sessions=sessions, settings=settings,
            reader=reader, workdir=workdir, snapshot=snapshot, attempt_id=attempt_id,
            outcome_id=outcome_id, call_ids=call_ids, reads=reads, inventories=inventories,
            source_sessions=client.app_state["sessionmaker"], engine=engine,
            controls=controls,
        )
        yield case


def finalize(case):
    return asyncio.run(evaluator.finalize_run(case.settings, case.sessions, case.reader, case.workdir, case.run_id))


@pytest.mark.parametrize("final_case", ["representative"], indirect=True)
def test_representative_qualification_keeps_full_inventory_and_rejects_changes(final_case):
    from twobrain_rec_server.outcomes.prompt_bundle import FinalCorpusReport

    case = final_case
    result = finalize(case)
    assert result["complete"] is True, result
    assert result["reviewed"] == 3 and result["controls_passed"] == 7
    assert result["inventory_total"] == 4 and result["not_evaluated"] == 1
    report = FinalCorpusReport.model_validate(result["qualification_report"])
    assert report.evaluation_scope == "representative" and len(report.inventory) == 4
    assert len(report.not_evaluated) == 1 and report.sample_long_duration_seconds == 3600
    tampered = report.model_dump(mode="json")
    tampered["reviews"].pop()
    with pytest.raises(ValueError):
        FinalCorpusReport.model_validate(tampered)
    original_read = case.reader.read

    async def changed(identifier):
        value = await original_read(identifier)
        if identifier == str(case.meeting_id):
            value["selection_status"] = "deleted"
        return value

    case.reader.read = changed
    failed = finalize(case)
    assert failed["complete"] is False and failed["excluded"] == 0
    assert failed["errors"]["evaluation_source_changed"]


def test_qualification_requires_seven_controls_and_privacy(final_case):
    final_case.workdir.discard("controls.json")
    final_case.workdir.discard("privacy.json")
    result = finalize(final_case)
    assert result["complete"] is False
    assert "qualification_report" not in result
    assert result["errors"]["evaluation_controls_missing"] == 1
    assert result["errors"]["evaluation_privacy_missing"] == 1


def test_final_report_uses_current_source_and_ledger_without_mutation(final_case):
    case = final_case
    statements = []
    event.listen(case.engine.sync_engine, "before_cursor_execute", lambda _c, _cu, stmt, _p, _ct, _m: statements.append(stmt))
    result = finalize(case)
    assert result["complete"] is True and result["passed"] == 1
    assert result["cutoff_at"] and len(case.inventories) >= 2
    assert case.reads == [str(case.meeting_id)]
    assert not any(stmt.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for stmt in statements)
    public = {key: value for key, value in result.items() if key != "qualification_report"}
    assert "Синтет" not in str(public) and str(case.meeting_id) not in str(public)
    from twobrain_rec_server.outcomes.prompt_bundle import FinalCorpusReport
    proof = FinalCorpusReport.model_validate(result["qualification_report"])
    assert proof.reviews[0].meeting_id == str(case.meeting_id)
    assert len(proof.controls) == 7 and all(len(row.calls) == 3 for row in proof.controls)
    assert "Синтет" not in str(proof)


def test_qualification_rechecks_each_control_and_privacy(final_case):
    case = final_case
    identifier = case.controls["informal_commitment"]
    name = f"review-{identifier}.json"
    original = case.workdir.read_json(name)
    for field in ("output_hash", "run_id"):
        changed = deepcopy(original)
        changed[field] = "0" * 64 if field == "output_hash" else "00000000-0000-0000-0000-000000000000"
        case.workdir.discard(name)
        case.workdir.write_json(name, changed)
        result = finalize(case)
        assert not result["complete"] and "qualification_report" not in result
        assert result["errors"]["evaluation_control_invalid"] == 1
    case.workdir.discard(name)
    case.workdir.write_json(name, original)
    privacy = case.workdir.read_json("privacy.json")
    case.workdir.discard("privacy.json")
    case.workdir.write_json("privacy.json", {**privacy, "root_hash": "0" * 64})
    result = finalize(case)
    assert not result["complete"] and result["errors"]["evaluation_privacy_invalid"] == 1
    case.workdir.discard("privacy.json")
    case.workdir.write_json("privacy.json", privacy)
    assert finalize(case)["complete"]


def test_operator_writer_uses_finalizer_and_retains_one_event(final_case):
    from twobrain_rec_server.db.models import PromptRootPromotion
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import (
        MaintenanceTenantContext,
        maintenance_context_settings,
    )
    from twobrain_rec_server.outcomes.prompt_bundle import (
        ROOT_BUNDLE_PROMPT_NAME,
        PromptBundleError,
        promote_root_bundle,
        validate_evaluation_snapshot,
    )
    from twobrain_rec_server.outcomes.prompts import canonical_json

    case = final_case
    bundle, _ = validate_evaluation_snapshot(case.workdir.read_json("root-authority.json"))
    export = case.workdir.read_json("root-authority.json")["export"]
    owner_engine = case.source_sessions.kw["bind"]
    assert owner_engine.url.database.startswith("twobrain_rec_test_")
    assert owner_engine.url.host in {"127.0.0.1", "localhost", "::1"}

    async def run():
        async with case.source_sessions() as db:
            await db.execute(text("""do $$ begin
                if not exists(select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
                    create role twobrain_rec_maintenance nologin;
                end if;
            end $$"""))
            await db.execute(text("grant select, insert, update on prompt_root_promotions to twobrain_rec_maintenance"))
            await db.commit()
        engine = create_async_engine(owner_engine.url, poolclass=NullPool)

        @event.listens_for(engine.sync_engine, "connect")
        def identity(connection, _record):
            cursor = connection.cursor()
            cursor.execute("set session authorization twobrain_rec_maintenance")
            cursor.execute("set row_security = on")
            cursor.close()

        base_sessions = create_sessionmaker(engine)

        def sessions():
            db = base_sessions()
            db.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="prompt_optimization", actor_id="synthetic-operator",
                reason_category="prompt_optimization", feature_area="prompt_optimization",
            ))
            return db

        active_version, mutations = 99, []
        started, release = threading.Event(), threading.Event()
        ambiguous = False
        loop = asyncio.get_running_loop()
        operation_id = uuid4()

        async def prepared():
            async with sessions() as db:
                row = await db.get(PromptRootPromotion, operation_id)
                assert row.state == "prepared" and row.event_json is None
                assert row.qualification_json["report"]["complete"] is True

        def update(**kwargs):
            nonlocal active_version
            asyncio.run_coroutine_threadsafe(prepared(), loop).result(10)
            assert kwargs["request_options"]["max_retries"] == 0
            mutations.append(kwargs)
            active_version = kwargs["version"]
            started.set()
            if not release.wait(10):
                raise TimeoutError("synthetic test release timeout")
            if ambiguous:
                raise OSError("synthetic lost update response")

        def get_prompt(name, **kwargs):
            if name == ROOT_BUNDLE_PROMPT_NAME:
                return SimpleNamespace(version=active_version if "label" in kwargs else bundle.root.root_prompt_version,
                                       prompt=canonical_json({key: value for key, value in export["bundle"].items()
                                                              if key != "root_prompt_version"}))
            child = bundle.children[name]
            return SimpleNamespace(version=child.version, prompt=child.prompt, config=child.config)

        client = SimpleNamespace(get_prompt=get_prompt, api=SimpleNamespace(
            projects=SimpleNamespace(get=lambda **_kw: SimpleNamespace(data=[SimpleNamespace(id=case.settings.langfuse_project_id)])),
            prompt_version=SimpleNamespace(update=update),
        ))
        timestamp = datetime.now(UTC).isoformat()
        check = dict(method="synthetic independently inspected policy", checked_at=timestamp,
                     checked_by="synthetic-operator", result="pass")
        kwargs = dict(
            settings=case.settings.model_copy(update={"env": "test"}), client=client,
            operation_id=operation_id, expected_source_version=99, operator_actor="synthetic-operator",
            approved_at=timestamp, protected_label=check, sole_mutation_credential=check,
            evaluation_settings=case.settings, evaluation_sessionmaker=case.sessions,
            source_reader=case.reader, workdir=case.workdir, run_id=case.run_id,
        )
        try:
            # No arbitrary report can replace the real finalizer's missing review.
            privacy = case.workdir.read_json("privacy.json")
            case.workdir.discard("privacy.json")
            with pytest.raises(PromptBundleError, match="qualification_incomplete"):
                await promote_root_bundle(sessions, **kwargs)
            assert mutations == []
            case.workdir.write_json("privacy.json", privacy)
            first = asyncio.create_task(promote_root_bundle(sessions, **kwargs))
            try:
                assert await asyncio.to_thread(started.wait, 15)
                duplicate = asyncio.create_task(promote_root_bundle(sessions, **kwargs))
                first.cancel()
                await asyncio.sleep(0.02)
                assert not first.done() and not duplicate.done()
            finally:
                release.set()
            result = await first
            assert await duplicate == result
            assert len(mutations) == 1 and result.operation_id == str(operation_id)
            async with sessions() as db:
                row = await db.get(PromptRootPromotion, operation_id)
                assert row.is_current and row.state == "succeeded"
                assert row.qualification_json["previous_event"] is None
                assert row.qualification_json["safe_exit"] == "disable_new_ai"
            active_version = 500  # A later external movement must not make replay move it back.
            case.workdir.discard("privacy.json")
            assert await promote_root_bundle(sessions, **kwargs) == result
            assert active_version == 500 and len(mutations) == 1
            case.workdir.write_json("privacy.json", privacy)
            original_kwargs = dict(kwargs)
            operation_id = uuid4()
            kwargs.update(operation_id=operation_id, expected_source_version=bundle.root.root_prompt_version)
            with pytest.raises(PromptBundleError, match="source_conflict"):
                await promote_root_bundle(sessions, **kwargs)
            assert len(mutations) == 1
            active_version = bundle.root.root_prompt_version
            ambiguous = True
            with pytest.raises(PromptBundleError, match="reconciliation_required"):
                await promote_root_bundle(sessions, **kwargs)
            async with sessions() as db:
                row = await db.get(PromptRootPromotion, operation_id)
                assert row.state == "reconciliation_required" and row.event_json is None
                assert not row.is_current
            for retry_id in (operation_id, uuid4()):
                with pytest.raises(PromptBundleError, match="reconciliation_required"):
                    await promote_root_bundle(sessions, **{**kwargs, "operation_id": retry_id})
            assert len(mutations) == 2
            assert await promote_root_bundle(sessions, **original_kwargs) == result
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_final_report_rejects_review_output_and_call_tampering(final_case):
    case = final_case
    name = f"review-{case.meeting_id}.json"
    original = case.workdir.read_json(name)
    for mutation in ("output_hash", "refs"):
        review = deepcopy(original)
        if mutation == "output_hash":
            review["output_hash"] = "d" * 64
        else:
            review["criteria"][evaluator.REVIEW_CRITERIA[0]]["source_refs"][0]["sequence"] = 999
        case.workdir.discard(name)
        case.workdir.write_json(name, review)
        report = finalize(case)
        assert report["complete"] is False and report["passed"] == 0
    case.workdir.discard(name)
    case.workdir.write_json(name, original)
    output_name = f"output-{case.meeting_id}.json"
    original_output = case.workdir.read_json(output_name)
    changed_output = deepcopy(original_output)
    changed_output["protocol"]["executive_summary"][0]["text"] = "Синтетическая подмена"
    case.workdir.discard(output_name)
    case.workdir.write_json(output_name, changed_output)
    assert finalize(case)["complete"] is False
    case.workdir.discard(output_name)
    case.workdir.write_json(output_name, original_output)
    case.settings.outcome_root_prompt_version = 2
    assert finalize(case)["complete"] is False
    case.settings.outcome_root_prompt_version = 1

    async def change(model, identifier, **values):
        async with case.sessions() as db:
            row = await db.get(model, identifier)
            previous = {key: getattr(row, key) for key in values}
            for key, value in values.items():
                setattr(row, key, value)
            await db.commit()
            return previous

    for model, identifier, changes in (
        (MeetingOutcomeGenerationAttempt, case.attempt_id, {"status": "failed"}),
        (MeetingOutcomeGenerationAttempt, case.attempt_id, {"status": "generating"}),
        (MeetingOutcomeSet, case.outcome_id, {"content_hash": "d" * 64}),
        (GenerationCall, case.call_ids[1], {"call_state": "ambiguous"}),
        (GenerationCall, case.call_ids[1], {"export_status": "pending"}),
        (GenerationCall, case.call_ids[1], {"validated_result_hash": "d" * 64}),
    ):
        previous = asyncio.run(change(model, identifier, **changes))
        report = finalize(case)
        assert report["complete"] is False and report["passed"] == 0, changes
        asyncio.run(change(model, identifier, **previous))
    assert finalize(case)["complete"] is True


@pytest.mark.parametrize("final_case", [(1, "not_sent"), (2, "not_sent"), (3, "not_sent"), (3, "response_received")], indirect=True)
def test_final_report_accepts_completed_stages_after_allowed_retry(final_case):
    case = final_case

    async def ledger():
        async with case.sessions() as db:
            return [{column.name: deepcopy(getattr(row, column.name)) for column in row.__table__.columns}
                    for row in (await db.scalars(select(GenerationCall).where(
                        GenerationCall.meeting_id == case.meeting_id,
                    ).order_by(GenerationCall.id))).all()]

    before = asyncio.run(ledger())
    assert len(before) == 4
    prior = next(row for row in before if row["call_state"] == "failed")
    assert prior["export_status"] == ("not_required" if prior["raw_response_json"] is None else "confirmed")
    assert sorted(row["call_sequence"] for row in before if row["call_state"] == "completed") == [1, 2, 3]
    report = finalize(case)
    assert report["complete"] is True and report["passed"] == 1
    assert asyncio.run(ledger()) == before

    async def update_prior(**fields):
        async with case.sessions() as db:
            call = await db.get(GenerationCall, prior["id"])
            # Restore the timestamp changed by this test's deliberate SQL updates too.
            previous = {key: deepcopy(getattr(call, key)) for key in (*fields, "updated_at")}
            for key, value in fields.items():
                setattr(call, key, value)
            await db.commit()
            return previous

    bad_error = deepcopy(prior["validated_result_json"])
    bad_error["generation_error"]["egress_state"] = "unknown"
    for changes in (
        {"call_state": "ambiguous"},
        {"call_state": "reserved"},
        {"completed_at": None},
        {"export_status": "pending"},
        {"call_sequence": 999},
        {"validated_result_json": bad_error, "validated_result_hash": ai_service._content_hash(bad_error)},
    ):
        previous = asyncio.run(update_prior(**changes))
        mutated = asyncio.run(ledger())
        rejected = finalize(case)
        assert rejected["complete"] is False and rejected["passed"] == 0, changes.keys()
        assert asyncio.run(ledger()) == mutated
        asyncio.run(update_prior(**previous))
    assert asyncio.run(ledger()) == before
    assert finalize(case)["complete"] is True


@pytest.mark.parametrize("late", [False, True])
@pytest.mark.parametrize("mutation", ["deletion", "revoke", "source"])
def test_final_report_source_invalidation_purges_both_copies_but_not_ledger(final_case, late, mutation):
    case = final_case

    async def calls():
        async with case.sessions() as db:
            return [{column.name: deepcopy(getattr(row, column.name)) for column in row.__table__.columns}
                    for row in (await db.scalars(select(GenerationCall).order_by(GenerationCall.id))).all()]

    async def revoke():
        async with case.source_sessions() as db:
            meeting = await db.get(Meeting, case.meeting_id)
            if mutation == "deletion":
                meeting.deletion_state = "deleted"
                meeting.deletion_epoch += 1
            elif mutation == "revoke":
                owner = await db.get(UserIdentity, meeting.created_by_user_id)
                owner.status = "disabled"
            else:
                segment = await db.scalar(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id))
                segment.text += " Синтетическая поправка."
            await db.commit()

    retained = asyncio.run(calls())
    if late:
        original_inventory = case.reader.inventory
        async def inventory():
            if case.inventories:
                await revoke()
            return await original_inventory()
        case.reader.inventory = inventory
    else:
        asyncio.run(revoke())
    report = finalize(case)
    assert report["passed"] == 0
    assert all(not (case.workdir.path / f"{prefix}-{case.meeting_id}.json").exists()
               for prefix in ("source", "output", "review", "inventory-notes", "exclusion"))
    async def check():
        async with case.sessions() as db:
            assert (await db.get(Meeting, case.meeting_id)).deleted_at is not None
            assert (await db.get(MeetingOutcomeSet, case.outcome_id)).protocol_json is None
    asyncio.run(check())
    assert asyncio.run(calls()) == retained


def test_final_report_new_inventory_meeting_stays_pending(final_case, client):
    case = final_case
    added = create_outcome_ready_meeting(client, "synthetic-added-at-final-cutoff")
    report = finalize(case)
    assert report["found"] == 2 and report["passed"] == 1
    assert report["pending"] == 1 and report["complete"] is False
    assert set(case.reads) == {str(case.meeting_id), str(added)}


def test_final_report_rechecks_durable_state_after_source_cutoff(final_case):
    case = final_case
    original_inventory = case.reader.inventory

    async def inventory():
        rows = await original_inventory()
        if len(case.inventories) == 2:
            async with case.sessions() as db:
                call = await db.get(GenerationCall, case.call_ids[1])
                call.call_state = "ambiguous"
                await db.commit()
        return rows

    case.reader.inventory = inventory
    result = finalize(case)
    assert result["complete"] is False and result["passed"] == 0


def test_final_inventory_revoke_purges_even_when_individual_source_read_fails(final_case):
    case = final_case
    original_inventory = case.reader.inventory

    async def read(_identifier):
        raise OSError("synthetic source read failure")

    async def inventory():
        if case.inventories:
            async with case.source_sessions() as db:
                meeting = await db.get(Meeting, case.meeting_id)
                owner = await db.get(UserIdentity, meeting.created_by_user_id)
                owner.status = "disabled"
                await db.commit()
        return await original_inventory()

    async def ledger():
        async with case.sessions() as db:
            return [{column.name: deepcopy(getattr(row, column.name)) for column in row.__table__.columns}
                    for row in (await db.scalars(select(GenerationCall).order_by(GenerationCall.id))).all()]

    retained = asyncio.run(ledger())
    case.reader.read, case.reader.inventory = read, inventory
    result = finalize(case)
    assert result["complete"] is False and result["passed"] == 0
    assert result["errors"]["evaluation_source_read_failed"] == 1
    assert all(not (case.workdir.path / f"{prefix}-{case.meeting_id}.json").exists()
               for prefix in ("source", "output", "review", "inventory-notes", "exclusion"))

    async def check():
        async with case.sessions() as db:
            assert (await db.get(Meeting, case.meeting_id)).deleted_at is not None
            assert (await db.get(MeetingOutcomeSet, case.outcome_id)).protocol_json is None

    asyncio.run(check())
    assert asyncio.run(ledger()) == retained


@pytest.mark.parametrize("failed_channel", ["file", "database"])
def test_final_revoke_attempts_both_cleanup_channels(final_case, monkeypatch, failed_channel):
    case = final_case

    async def revoke():
        async with case.source_sessions() as db:
            meeting = await db.get(Meeting, case.meeting_id)
            meeting.deletion_state = "deleted"
            await db.commit()

    asyncio.run(revoke())
    discarded = []
    original_discard = case.workdir.discard
    original_purge = evaluator.purge_shadow_source
    purged = []

    def discard(name):
        discarded.append(name)
        if failed_channel == "file" and name.startswith("source-"):
            raise OSError("synthetic failure")
        original_discard(name)

    async def purge(db, identifier):
        purged.append(identifier)
        if failed_channel == "database":
            raise OSError("synthetic failure")
        await original_purge(db, identifier)

    monkeypatch.setattr(case.workdir, "discard", discard)
    monkeypatch.setattr(evaluator, "purge_shadow_source", purge)
    result = finalize(case)
    assert result["complete"] is False
    assert result["errors"]["evaluation_private_cleanup_failed"] == 1
    assert len(discarded) == 5 and purged == [str(case.meeting_id)]
    assert all(not (case.workdir.path / f"{prefix}-{case.meeting_id}.json").exists()
               for prefix in ("output", "review", "inventory-notes", "exclusion"))
    if failed_channel == "file":
        async def check():
            async with case.sessions() as db:
                assert (await db.get(Meeting, case.meeting_id)).deleted_at is not None
        asyncio.run(check())


def test_p2_finalizer_and_completed_reuse_share_lock_order(final_case, monkeypatch):
    """Real PG locks: a completed replay must not deadlock with qualification."""
    case = final_case

    async def run():
        held, finalizer_waiting = asyncio.Event(), asyncio.Event()
        original_lock = ai_service._lock_candidate_meeting_and_attempt
        lock_errors = []

        async def lock(*args, **kwargs):
            name = asyncio.current_task().get_name()
            if name == "p2-finalizer":
                finalizer_waiting.set()
            try:
                result = await original_lock(*args, **kwargs)
            except DBAPIError as exc:
                lock_errors.append(getattr(exc.orig, "sqlstate", None))
                raise
            if name == "p2-reuse":
                held.set()
                await asyncio.wait_for(finalizer_waiting.wait(), 10)
            return result

        monkeypatch.setattr(ai_service, "_lock_candidate_meeting_and_attempt", lock)
        gateway = AsyncMock(side_effect=AssertionError("completed replay attempted inference"))
        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", gateway)
        async with case.sessions() as db:
            attempt = await db.get(MeetingOutcomeGenerationAttempt, case.attempt_id)

        async def source_guard():
            assert (await case.reader.read(case.meeting_id))["source_hash"] == case.snapshot["source_hash"]

        reuse = asyncio.create_task(ai_service.execute_candidate_generation(
            case.sessions, settings=case.settings, workspace_id=attempt.workspace_id,
            candidate_id=attempt.candidate_id, expected_snapshot_hash=attempt.temporal_transcript_hash,
            evaluation_source_guard=source_guard,
        ), name="p2-reuse")
        tasks = [reuse]
        try:
            await asyncio.wait_for(held.wait(), 10)
            finalizer = asyncio.create_task(evaluator.finalize_run(
                case.settings, case.sessions, case.reader, case.workdir, case.run_id,
            ), name="p2-finalizer")
            tasks.append(finalizer)
            reused, report = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), 20,
            )
            assert not isinstance(reused, BaseException), "completed reuse lost the PG lock-order race"
            assert not isinstance(report, BaseException), "finalizer lost the PG lock-order race"
            assert reused["reused"] is True
            assert report["complete"] is True, {"errors": report["errors"], "lock_sqlstates": lock_errors}
            gateway.assert_not_awaited()
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run())


@pytest.mark.parametrize("foreign_run", [False, True])
def test_p2_finalizer_rechecks_attempt_inventory_at_cutoff(final_case, foreign_run):
    case = final_case
    original_inventory = case.reader.inventory
    added = []

    async def inventory():
        rows = await original_inventory()
        if len(case.inventories) == 2:
            async with case.sessions() as db:
                previous = await db.get(MeetingOutcomeGenerationAttempt, case.attempt_id)
                definition = next(value for key, value in evaluator.BUILT_IN_BY_KEY.items()
                                  if key != previous.template_key)
                pending = await ai_service.create_summary_candidate(
                    db, workspace_id=previous.workspace_id, meeting_id=previous.meeting_id,
                    requested_by_user_id=previous.requested_by_user_id,
                    template_key=definition.key, template_id=None, template_version=definition.version,
                    expected_current_outcome_set_id=None, request_intent="manual_refresh",
                    request_intent_id=uuid4(),
                )
                pending.metadata_json = {**pending.metadata_json, "evaluation_only": True,
                                         "evaluation_run_id": str(uuid4() if foreign_run else case.run_id),
                                         "evaluation_source": previous.metadata_json["evaluation_source"]}
                await db.commit()
                assert pending.id != previous.id and pending.status == "queued"
                added.append(pending.id)
        return rows

    case.reader.inventory = inventory
    report = finalize(case)
    assert len(added) == 1
    assert report["complete"] is False, "a new unreviewed attempt disappeared from qualification"
    assert "qualification_report" not in report


@asynccontextmanager
async def _p2_operator(case):
    """Same maintenance/RLS path as the writer integration test; fake only Langfuse."""
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import (
        MaintenanceTenantContext,
        maintenance_context_settings,
    )
    from twobrain_rec_server.outcomes.prompt_bundle import (
        ROOT_BUNDLE_PROMPT_NAME,
        promote_root_bundle,
        validate_evaluation_snapshot,
    )
    from twobrain_rec_server.outcomes.prompts import canonical_json

    owner_engine = case.source_sessions.kw["bind"]
    assert owner_engine.url.database.startswith("twobrain_rec_test_")
    assert owner_engine.url.host in {"127.0.0.1", "localhost", "::1"}
    async with case.source_sessions() as db:
        await db.execute(text("""do $$ begin
            if not exists(select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
                create role twobrain_rec_maintenance nologin;
            end if;
        end $$"""))
        await db.execute(text("grant select, insert, update on prompt_root_promotions to twobrain_rec_maintenance"))
        await db.commit()
    engine = create_async_engine(owner_engine.url, poolclass=NullPool)

    @event.listens_for(engine.sync_engine, "connect")
    def identity(connection, _record):
        cursor = connection.cursor()
        cursor.execute("set session authorization twobrain_rec_maintenance")
        cursor.execute("set row_security = on")
        cursor.close()

    base_sessions = create_sessionmaker(engine)

    def sessions():
        db = base_sessions()
        db.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
            operation_name="prompt_optimization", actor_id="synthetic-operator",
            reason_category="prompt_optimization", feature_area="prompt_optimization",
        ))
        return db

    saved = case.workdir.read_json("root-authority.json")
    bundle, _ = validate_evaluation_snapshot(saved)
    state = SimpleNamespace(version=99, reads=0, mutations=[], conflict=False, update_error=None)

    def get_prompt(name, **kwargs):
        if name == ROOT_BUNDLE_PROMPT_NAME:
            if "label" in kwargs:
                state.reads += 1
                if state.conflict and state.reads == 2:
                    state.version = 999
            return SimpleNamespace(
                version=state.version if "label" in kwargs else bundle.root.root_prompt_version,
                prompt=canonical_json({key: value for key, value in saved["export"]["bundle"].items()
                                       if key != "root_prompt_version"}),
            )
        child = bundle.children[name]
        return SimpleNamespace(version=child.version, prompt=child.prompt, config=child.config)

    def update(**kwargs):
        assert kwargs["new_labels"] == ["production"]
        assert kwargs["request_options"]["max_retries"] == 0
        state.mutations.append(kwargs)
        state.version = kwargs["version"]
        if state.update_error is not None:
            raise state.update_error

    client = SimpleNamespace(get_prompt=get_prompt, api=SimpleNamespace(
        projects=SimpleNamespace(get=lambda **_kwargs: SimpleNamespace(
            data=[SimpleNamespace(id=case.settings.langfuse_project_id)],
        )), prompt_version=SimpleNamespace(update=update),
    ))
    approved_at = datetime.now(UTC).isoformat()
    check = dict(method="synthetic independent policy check", checked_at=approved_at,
                 checked_by="synthetic-operator", result="pass")
    kwargs = dict(settings=case.settings.model_copy(update={"env": "test"}), client=client,
                  operation_id=uuid4(), expected_source_version=99, operator_actor="synthetic-operator",
                  approved_at=approved_at, protected_label=check, sole_mutation_credential=dict(check),
                  evaluation_settings=case.settings, evaluation_sessionmaker=case.sessions,
                  source_reader=case.reader, workdir=case.workdir, run_id=case.run_id)
    try:
        yield SimpleNamespace(promote=promote_root_bundle, sessions=sessions, kwargs=kwargs, state=state)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("replay", [False, True])
def test_p2_writer_reports_cancelled_source_conflict(final_case, replay):
    from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

    async def run():
        async with _p2_operator(final_case) as writer:
            writer.state.conflict = True
            with pytest.raises(PromptBundleError) as first:
                await writer.promote(writer.sessions, **writer.kwargs)
            async with writer.sessions() as db:
                row = await db.get(PromptRootPromotion, writer.kwargs["operation_id"])
                assert row.state == "cancelled" and row.failure_code == "root_bundle_source_conflict"
                assert row.event_json is None and not row.is_current
            error = first.value
            if replay:
                with pytest.raises(PromptBundleError) as repeated:
                    await writer.promote(writer.sessions, **writer.kwargs)
                error = repeated.value
            assert writer.state.mutations == []
            assert writer.state.reads == 2
            assert str(error) == "root_bundle_source_conflict"

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["approval", "check", "provider"])
def test_p2_writer_bounds_prepared_boundary_errors(final_case, fault):
    from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

    marker = "synthetic-private-operator-input"

    async def run():
        async with _p2_operator(final_case) as writer:
            if fault == "approval":
                writer.kwargs["approved_at"] = marker
            elif fault == "check":
                writer.kwargs["protected_label"] = {**writer.kwargs["protected_label"], "result": marker}
            else:
                def unavailable(**_kwargs):
                    raise OSError(marker)
                writer.kwargs["client"].api.projects.get = unavailable
            with pytest.raises(Exception) as caught:
                await writer.promote(writer.sessions, **writer.kwargs)
            assert writer.state.mutations == []
            async with writer.sessions() as db:
                assert await db.get(PromptRootPromotion, writer.kwargs["operation_id"]) is None
            assert isinstance(caught.value, PromptBundleError)
            assert str(caught.value) == ("root_promotion_unavailable" if fault == "provider"
                                         else "root_operator_evidence_invalid")
            assert marker not in str(caught.value) and caught.value.__suppress_context__

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["prepared", "prepared_response", "event", "event_response", "reconciliation"])
def test_p2_writer_bounds_database_errors_without_repeating_mutation(final_case, monkeypatch, fault):
    from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

    marker = "synthetic-private-sql-input"

    async def run():
        async with _p2_operator(final_case) as writer:
            original_commit = AsyncSession.commit
            injected = []

            async def commit(db):
                rows = [row for row in (*db.new, *db.dirty) if isinstance(row, PromptRootPromotion)]
                expected_state = ("prepared" if fault.startswith("prepared") else
                                  "succeeded" if fault.startswith("event") else "reconciliation_required")
                if not injected and any(row.state == expected_state for row in rows):
                    injected.append(expected_state)
                    if fault.endswith("response"):
                        await original_commit(db)
                    raise DBAPIError("synthetic journal commit", {"evidence": marker}, OSError(marker), False)
                await original_commit(db)

            monkeypatch.setattr(AsyncSession, "commit", commit)
            if fault == "reconciliation":
                writer.state.update_error = OSError("synthetic lost mutation response")
            with pytest.raises(Exception) as caught:
                await writer.promote(writer.sessions, **writer.kwargs)
            assert injected == ["prepared" if fault.startswith("prepared") else
                                "succeeded" if fault.startswith("event") else "reconciliation_required"]
            expected_mutations = 0 if fault.startswith("prepared") else 1
            assert len(writer.state.mutations) == expected_mutations
            async with writer.sessions() as db:
                row = await db.get(PromptRootPromotion, writer.kwargs["operation_id"])
                if fault == "event_response":
                    assert row.state == "succeeded" and row.is_current and row.event_json is not None
                elif row is not None:
                    assert row.state in {"prepared", "reconciliation_required"}
                    assert row.event_json is None and not row.is_current
            if row is not None:
                if fault == "event_response":
                    result = await writer.promote(writer.sessions, **writer.kwargs)
                    assert result.operation_id == str(writer.kwargs["operation_id"])
                else:
                    for operation_id in (writer.kwargs["operation_id"], uuid4()):
                        with pytest.raises(PromptBundleError, match="^root_promotion_reconciliation_required$"):
                            await writer.promote(writer.sessions, **{**writer.kwargs, "operation_id": operation_id})
            assert len(writer.state.mutations) == expected_mutations
            assert isinstance(caught.value, PromptBundleError)
            assert str(caught.value) == "root_promotion_reconciliation_required"
            assert marker not in str(caught.value) and caught.value.__suppress_context__

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["shape", "identifier"])
def test_p2_finalizer_bounds_initial_inventory_errors(final_case, fault):
    case = final_case
    saved = case.workdir.read_json("inventory.json")
    if fault == "shape":
        saved = ["synthetic-private-inventory-input"]
    else:
        saved["meetings"][0]["meeting_id"] = "synthetic-private-inventory-input"
    case.workdir.discard("inventory.json")
    case.workdir.write_json("inventory.json", saved)
    with pytest.raises(evaluator.OutcomeGenerationTerminalError, match="^evaluation_inventory_invalid$"):
        finalize(case)


def test_p2_finalizer_bounds_initial_database_error(final_case):
    case = final_case
    injected = []

    def fail_query(_connection, _cursor, statement, _parameters, _context, _many):
        if not injected and "FROM meeting_outcome_generation_attempts" in statement:
            injected.append(True)
            raise DBAPIError("synthetic attempt inventory", {"private": "synthetic-private-db-input"},
                             OSError("synthetic-private-db-input"), False)

    event.listen(case.engine.sync_engine, "before_cursor_execute", fail_query)
    try:
        with pytest.raises(evaluator.OutcomeGenerationTerminalError, match="^evaluation_report_invalid$"):
            finalize(case)
    finally:
        event.remove(case.engine.sync_engine, "before_cursor_execute", fail_query)
    assert injected == [True]


def test_p2_writer_bounds_lock_cleanup_error_and_replays_event(final_case, monkeypatch):
    from twobrain_rec_server.outcomes import prompt_optimization
    from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

    async def run():
        async with _p2_operator(final_case) as writer:
            original_scope = prompt_optimization._quiescent_session_scope
            injected = []

            @asynccontextmanager
            async def failed_close(*args, **kwargs):
                async with original_scope(*args, **kwargs) as db:
                    yield db
                if not injected:
                    injected.append(True)
                    raise OSError("synthetic-private-cleanup-input")

            monkeypatch.setattr(prompt_optimization, "_quiescent_session_scope", failed_close)
            with pytest.raises(Exception) as caught:
                await writer.promote(writer.sessions, **writer.kwargs)
            assert injected == [True]
            async with writer.sessions() as db:
                row = await db.get(PromptRootPromotion, writer.kwargs["operation_id"])
                assert row.state == "succeeded" and row.event_json is not None and row.is_current
            result = await writer.promote(writer.sessions, **writer.kwargs)
            assert result.operation_id == str(writer.kwargs["operation_id"])
            assert len(writer.state.mutations) == 1
            assert isinstance(caught.value, PromptBundleError)
            assert str(caught.value) == "root_promotion_reconciliation_required"
            assert "synthetic-private-cleanup-input" not in str(caught.value)
            assert caught.value.__suppress_context__

    asyncio.run(run())
