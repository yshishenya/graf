import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from tests.fixtures.meeting_protocol import protocol_bundle
from twobrain_rec_server.cli import meeting_protocol_eval_runtime as runtime
from twobrain_rec_server.cli.meeting_protocol_eval import PrivateWorkdir
from twobrain_rec_server.config import Settings
from twobrain_rec_server.outcomes.ai_service import OutcomeGenerationTerminalError


@pytest.mark.parametrize("selector", ["dev", "numeric"])
def test_whole_run_pins_once_and_resumes_without_langfuse(tmp_path, monkeypatch, selector):
    run_id = uuid4()
    workdir = PrivateWorkdir.create(tmp_path, tmp_path / "checkout")
    settings = Settings(
        env="protocol-evaluation", langfuse_environment="protocol-evaluation",
        langfuse_project_id="synthetic-project", outcome_prompt_label="dev",
        outcome_root_prompt_version=1 if selector == "numeric" else None,
        temporal_task_queue=f"graf-protocol-eval-{run_id.hex}",
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def scalar(self, _query):
            return f"graf_protocol_eval_{run_id.hex}"

    client = SimpleNamespace(api=SimpleNamespace(projects=SimpleNamespace(
        get=Mock(return_value=SimpleNamespace(data=[SimpleNamespace(id="synthetic-project")])),
    )))
    monkeypatch.setattr(runtime, "create_langfuse_client", Mock(return_value=client))
    monkeypatch.setattr(runtime, "shutdown_langfuse", Mock())
    fetch = Mock(return_value=protocol_bundle())
    unused = Mock(side_effect=AssertionError("wrong selector"))
    monkeypatch.setattr(runtime, "fetch_root_bundle_by_label", fetch if selector == "dev" else unused)
    monkeypatch.setattr(runtime, "fetch_root_bundle_by_version", fetch if selector == "numeric" else unused)

    async def run():
        pinned = await runtime.pin_evaluation_run(settings, Session, workdir, run_id)
        assert pinned.outcome_root_prompt_version == 1
        assert pinned.outcome_evaluation_workdir == workdir.path
        saved = workdir.read_json("root-authority.json")
        assert saved["authority"]["run_id"] == str(run_id)
        runtime.create_langfuse_client.side_effect = AssertionError("resume must not fetch dev")
        assert await runtime.pin_evaluation_run(settings, Session, workdir, run_id) == pinned
        assert workdir.read_json("root-authority.json") == saved
        fetch.assert_called_once()
        with pytest.raises(OutcomeGenerationTerminalError):
            await runtime.pin_evaluation_run(settings, Session, workdir, uuid4())

    asyncio.run(run())
