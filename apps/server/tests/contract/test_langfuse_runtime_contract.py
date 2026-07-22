from __future__ import annotations

from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.observability.langfuse import create_langfuse_client


def test_langfuse_runtime_is_private_full_content_and_secret_file_backed(
    tmp_path: Path, monkeypatch
) -> None:
    public_key = tmp_path / "public-key"
    secret_key = tmp_path / "secret-key"
    public_key.write_text("pk-test", encoding="utf-8")
    secret_key.write_text("sk-test", encoding="utf-8")
    captured: dict[str, object] = {}

    class _Langfuse:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("langfuse.Langfuse", _Langfuse)
    settings = Settings(
        langfuse_public_key_file=public_key,
        langfuse_secret_key_file=secret_key,
        langfuse_base_url="https://cloud.langfuse.com",
        langfuse_environment="production",
    )

    create_langfuse_client(settings)

    assert captured["public_key"] == "pk-test"
    assert captured["secret_key"] == "sk-test"
    assert captured["environment"] == "production"
    assert captured["tracing_enabled"] is True
    assert captured["mask"] is None
    assert set(captured["blocked_instrumentation_scopes"]) == {
        "opentelemetry.instrumentation.fastapi",
        "opentelemetry.instrumentation.httpx",
        "opentelemetry.instrumentation.sqlalchemy",
    }
    assert not hasattr(settings, "langfuse_public_trace_url")


def test_full_content_publisher_has_one_explicit_generation_owner() -> None:
    source = Path(
        "src/twobrain_rec_server/observability/langfuse.py"
    ).read_text(encoding="utf-8")
    workflow_source = Path(
        "src/twobrain_rec_server/workflows/outcome_generation_workflow.py"
    ).read_text(encoding="utf-8")

    assert source.count('as_type="generation"') == 1
    assert 'input={"request": call.request_json}' in source
    assert '"transcript": call.transcript_text' not in source
    assert '"raw_response": call.raw_response_json' in source
    assert '"validated_result": call.validated_result_json' in source
    assert "mask=None" in source
    assert '"publish_outcome_observability_activity"' in workflow_source
    assert workflow_source.count('"execute_outcome_generation_activity"') == 1


def test_temporal_topology_uses_dedicated_traced_ai_workers() -> None:
    temporal_source = Path(
        "src/twobrain_rec_server/workflows/temporal_client.py"
    ).read_text(encoding="utf-8")
    worker_source = Path("src/twobrain_rec_server/workflows/worker.py").read_text(
        encoding="utf-8"
    )

    assert 'f"{settings.temporal_task_queue}-outcomes"' in temporal_source
    assert "langfuse_otel_tracer(langfuse_client)" in temporal_source
    assert "TraceContextTextMapPropagator()" in temporal_source
    assert "W3CBaggagePropagator" not in temporal_source
    assert "workflows=[OutcomeGenerationWorkflow]" in worker_source
    assert "task_queue=outcome_generation_task_queue(settings)" in worker_source
