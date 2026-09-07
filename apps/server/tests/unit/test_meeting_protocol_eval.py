from __future__ import annotations

import asyncio
import inspect
import json
import os
import stat
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.cli import meeting_protocol_eval as evaluator
from twobrain_rec_server.outcomes.ai_service import OutcomeGenerationTerminalError


def test_snapshot_bridge_has_no_write_or_limit_and_uses_canonical_helpers():
    source = inspect.getsource(evaluator.snapshot_source)
    assert "latest_processing_result_query" in source
    assert "load_outcome_transcript_segments" in source
    assert "canonical_transcript" in source
    assert ".limit(" not in source
    for operation in (".commit(", ".flush(", ".add(", ".delete(", "downloads_json"):
        assert operation not in source
    assert "UserIdentity.status" in source and "WorkspaceMembership.status" in source


@pytest.mark.parametrize("target", ["-evil", "host;true", "host$(true)", "host\nother"])
def test_bridge_rejects_remote_shell_arguments(target):
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_source_target_invalid"):
        evaluator.SourceReader(target, "api")


def test_bridge_captures_content_and_discards_failure_details(monkeypatch, capsys):
    calls = []

    class Process:
        returncode = 1

        async def communicate(self, script):
            calls.append(script.decode())
            return b"PRIVATE TRANSCRIPT", b"PRIVATE DSN"

    async def spawn(*args, **kwargs):
        assert args[:4] == ("ssh", "-o", "BatchMode=yes", "-o")
        assert args[-6:] == ("docker", "exec", "-i", "api", "python", "-")
        assert kwargs["stdout"] == kwargs["stderr"] == asyncio.subprocess.PIPE
        assert "shell" not in kwargs
        return Process()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(OutcomeGenerationTerminalError, match="^evaluation_source_read_failed$"):
        asyncio.run(evaluator.SourceReader("host", "api").inventory())
    assert "default_transaction_read_only" in calls[0]
    assert "SHOW transaction_read_only" in calls[0]
    assert "SHOW default_transaction_read_only" in calls[0]
    assert "select current_user, session_user" in calls[0]
    assert "select rec_maintenance_allowed()" in calls[0]
    assert "operator_diagnostics" in calls[0]
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "response", [[], {"result": []}, {"error": "evaluation_source_role_required"}]
)
def test_empty_inventory_cannot_bypass_role_and_context_gate(monkeypatch, response):
    class Process:
        returncode = 0

        async def communicate(self, _script):
            return json.dumps(response).encode(), b""

    async def spawn(*args, **kwargs):
        return Process()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    reader = evaluator.SourceReader("host", "maintenance")
    with pytest.raises(OutcomeGenerationTerminalError):
        asyncio.run(reader.inventory())
    assert reader.source_gate is None


def test_check_rejects_changed_or_unavailable_source(monkeypatch):
    reader = evaluator.SourceReader("host", "api")
    snapshot = {"source_hash": "a" * 64, "selection_status": "available"}

    async def read(_meeting_id):
        return snapshot

    monkeypatch.setattr(reader, "read", read)
    asyncio.run(reader.check(uuid4(), "a" * 64))
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_source_changed"):
        asyncio.run(reader.check(uuid4(), "b" * 64))
    snapshot["selection_status"] = "deleted"
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_source_unavailable"):
        asyncio.run(reader.check(uuid4(), "a" * 64))


def test_private_files_are_exclusive_restricted_and_outside_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_private_path_invalid"):
        evaluator.PrivateWorkdir.create(checkout, checkout)
    work = evaluator.PrivateWorkdir.create(tmp_path, checkout)
    assert stat.S_IMODE(work.path.stat().st_mode) == 0o700
    path = work.write_json("review.json", {"text": "Синтетический пример"})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text())["text"] == "Синтетический пример"
    assert work.read_json("review.json")["text"] == "Синтетический пример"
    for name in ("../escape.json", "/escape.json", "nested/a.json", "review.json"):
        with pytest.raises(OutcomeGenerationTerminalError):
            work.write_json(name, {})
    work.discard("review.json")
    assert not path.exists()


def test_private_reads_reject_links_permissions_and_nonfiles(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    work = evaluator.PrivateWorkdir.create(tmp_path, checkout)
    original = work.write_json("original.json", {"safe": "synthetic"})
    (work.path / "symlink.json").symlink_to(original)
    os.link(original, work.path / "hardlink.json")
    (work.path / "directory.json").mkdir()
    for name in ("symlink.json", "hardlink.json", "original.json", "directory.json"):
        with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_private_read_failed"):
            work.read_json(name)
    work.discard("hardlink.json")
    original.chmod(0o644)
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_private_read_failed"):
        work.read_json("original.json")
    with pytest.raises(OutcomeGenerationTerminalError):
        work.write_json("invalid.json", {"nan": float("nan")})
    assert not (work.path / "invalid.json").exists()


def test_private_constructor_and_reopened_directory_reject_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir(mode=0o700)
    (checkout / ".git").mkdir()
    workdir = checkout / "private"
    workdir.mkdir(mode=0o700)
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_private_path_invalid"):
        evaluator.PrivateWorkdir(workdir)
    outside = evaluator.PrivateWorkdir.create(tmp_path, checkout)
    outside.write_json("synthetic.json", {})
    # Recheck at read time too, even if the directory became a checkout later.
    (outside.path / ".git").mkdir()
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_private_path_invalid"):
        outside.read_json("synthetic.json")


def test_mirror_rejects_nonshadow_database_before_writes():
    class DB:
        async def scalar(self, query):
            assert str(query) == "select current_database()"
            return "production"

        def get_bind(self):
            return SimpleNamespace(url=SimpleNamespace(host="localhost"))

    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_shadow_database_required"):
        asyncio.run(evaluator.mirror_source(DB(), {}, uuid4()))
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_shadow_database_required"):
        asyncio.run(evaluator.purge_shadow_source(DB(), uuid4()))


@pytest.mark.parametrize("failure", ["timeout", "cancelled"])
def test_bridge_cleans_up_timed_out_or_cancelled_process(monkeypatch, failure):
    stopped = []

    class Process:
        returncode = None

        async def communicate(self, _script):
            raise asyncio.CancelledError if failure == "cancelled" else TimeoutError

        def kill(self):
            stopped.append("killed")

        async def wait(self):
            stopped.append("waited")

    async def spawn(*args, **kwargs):
        return Process()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(
        asyncio.CancelledError if failure == "cancelled" else OutcomeGenerationTerminalError
    ):
        asyncio.run(evaluator.SourceReader("host", "api").inventory())
    assert stopped == ["killed", "waited"]


def review_fixture():
    meeting_id, run_id, segment_id = str(uuid4()), str(uuid4()), str(uuid4())
    ref = {"transcript_segment_id": segment_id, "sequence": 1}
    snapshot = {
        "meeting_id": meeting_id,
        "source_hash": "a" * 64,
        "selection_status": "available",
        "canonical_transcript": json.dumps(
            [{**ref, "text": "Синтетическая содержательная реплика"}]
        ),
    }
    review = {
        "run_id": run_id,
        "meeting_id": meeting_id,
        "source_hash": "a" * 64,
        "root_hash": "b" * 64,
        "output_hash": "c" * 64,
        "reviewer": "Codex",
        "meeting_type": "work",
        "full_transcript_read": True,
        "independent_inventory": [{"text": "Обсудили синтетический пример", "source_refs": [ref]}],
        "summary_answers": {
            key: {"text": f"Проверено: {key}", "source_refs": [ref]}
            for key in ("subject", "result", "next_step")
        },
        "criteria": {
            key: {
                "verdict": "pass",
                "assessment": f"Проверка {key}: по исходной реплике",
                "source_refs": [ref],
                "errors": [],
            }
            for key in evaluator.REVIEW_CRITERIA
        },
    }
    return snapshot, review


def validate(snapshot, review):
    return evaluator.validate_review(
        review, snapshot=snapshot, run_id=review["run_id"], root_hash="b" * 64, output_hash="c" * 64
    )


@pytest.mark.parametrize(
    "mutation",
    ["missing", "blanket", "empty_refs", "bad_refs", "errors", "stale", "extra", "not_read"],
)
def test_review_fails_closed_without_per_criterion_evidence(mutation):
    snapshot, review = review_fixture()
    key = evaluator.REVIEW_CRITERIA[0]
    if mutation == "missing":
        del review["criteria"][key]
    elif mutation == "blanket":
        for criterion in review["criteria"].values():
            criterion["assessment"] = "Все хорошо"
    elif mutation == "empty_refs":
        review["criteria"][key]["source_refs"] = []
    elif mutation == "bad_refs":
        review["criteria"][key]["source_refs"][0]["sequence"] = 100
    elif mutation == "errors":
        review["criteria"][key]["errors"] = ["Пропущено решение"]
    elif mutation == "stale":
        review["source_hash"] = "d" * 64
    elif mutation == "extra":
        review["auto_pass"] = True
    else:
        review["full_transcript_read"] = False
    with pytest.raises(OutcomeGenerationTerminalError, match="^evaluation_review_invalid$"):
        validate(snapshot, review)


def test_report_contains_only_aggregates_and_missing_review_blocks_pass():
    snapshot, review = review_fixture()
    checked = validate(snapshot, deepcopy(review))
    report = evaluator.aggregate_report(
        [snapshot], [checked], run_id=review["run_id"], root_hash="b" * 64,
        review_bindings={snapshot["meeting_id"]: (snapshot, "c" * 64)},
    )
    assert report["passed"] == 1 and report["complete"] is True
    serialized = json.dumps(report)
    assert snapshot["meeting_id"] not in serialized and "Синтет" not in serialized
    assert all(report["criteria"][key]["pass"] == 1 for key in evaluator.REVIEW_CRITERIA)
    assert (
        evaluator.aggregate_report([snapshot], [], run_id=review["run_id"], root_hash="b" * 64)[
            "complete"
        ]
        is False
    )


@pytest.mark.parametrize("mutation", ["output_hash", "refs"])
def test_report_revalidates_mutated_previously_validated_review(mutation):
    snapshot, review = review_fixture()
    checked = validate(snapshot, review)
    if mutation == "output_hash":
        checked.output_hash = "d" * 64
    else:
        checked.criteria[evaluator.REVIEW_CRITERIA[0]].source_refs[0].sequence = 999
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_report_invalid"):
        evaluator.aggregate_report(
            [snapshot], [checked], run_id=review["run_id"], root_hash="b" * 64,
            review_bindings={snapshot["meeting_id"]: (snapshot, "c" * 64)},
        )


@pytest.mark.parametrize("mutation", ["duplicate", "stale", "run", "root", "failed"])
def test_report_rejects_old_duplicate_or_failed_reviews(mutation):
    snapshot, review = review_fixture()
    checked = validate(snapshot, review)
    reviews = [checked]
    if mutation == "duplicate":
        reviews *= 2
    elif mutation == "stale":
        snapshot["source_hash"] = "d" * 64
    elif mutation == "run":
        checked.run_id = str(uuid4())
    elif mutation == "root":
        checked.root_hash = "d" * 64
    else:
        criterion = checked.criteria[evaluator.REVIEW_CRITERIA[0]]
        criterion.verdict = "fail"
        criterion.errors = ["Синтетическая ошибка"]
        report = evaluator.aggregate_report(
            [snapshot], reviews, run_id=review["run_id"], root_hash="b" * 64,
            review_bindings={snapshot["meeting_id"]: (snapshot, "c" * 64)},
        )
        assert report["failed"] == 1 and report["complete"] is False
        return
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_report_invalid"):
        evaluator.aggregate_report(
            [snapshot], reviews, run_id=review["run_id"], root_hash="b" * 64,
            review_bindings={snapshot["meeting_id"]: (snapshot, "c" * 64)},
        )


def test_report_refuses_review_without_current_output_binding():
    snapshot, review = review_fixture()
    with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_report_invalid"):
        evaluator.aggregate_report(
            [snapshot], [validate(snapshot, review)], run_id=review["run_id"], root_hash="b" * 64,
        )


def test_exclusions_require_full_read_and_safe_reason_not_generation_error():
    snapshot, review = review_fixture()
    exclusion = {
        "meeting_id": snapshot["meeting_id"],
        "run_id": review["run_id"],
        "source_hash": snapshot["source_hash"],
        "reason": "no_meaningful_speech",
        "reviewer": "Codex",
        "full_transcript_read": True,
        "rationale": "Синтетическая проверка связи",
    }
    report = evaluator.aggregate_report(
        [snapshot], [], run_id=review["run_id"], root_hash="b" * 64, exclusions=[exclusion]
    )
    assert report["excluded"] == 1 and report["complete"] is True
    assert "Синтет" not in json.dumps(report)
    for reason in ("generation_failed", "private reason", "source_unavailable"):
        exclusion["reason"] = reason
        with pytest.raises(OutcomeGenerationTerminalError, match="evaluation_report_invalid"):
            evaluator.aggregate_report(
                [snapshot], [], run_id=review["run_id"], root_hash="b" * 64, exclusions=[exclusion]
            )
