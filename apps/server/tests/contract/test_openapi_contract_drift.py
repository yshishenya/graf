from pathlib import Path

import yaml

CONTRACT_PATH = Path(__file__).parents[4] / "specs/012-server-ingest-foundation/contracts/openapi.yaml"


def test_runtime_openapi_matches_committed_contract(client) -> None:
    runtime = client.get("/openapi.json").json()
    committed = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert runtime == committed


def test_problem_schema_uses_request_id_not_trace_id(client) -> None:
    schema = client.get("/openapi.json").json()
    problem = schema["components"]["schemas"]["Problem"]["properties"]

    assert "request_id" in problem
    assert "trace_id" not in problem


def test_readiness_contract_has_public_503_and_internal_detail(client) -> None:
    schema = client.get("/openapi.json").json()

    public_ready = schema["paths"]["/api/v1/health/ready"]["get"]["responses"]
    internal_ready = schema["paths"]["/api/v1/health/ready/internal"]["get"]["responses"]
    assert "200" in public_ready
    assert "503" in public_ready
    assert "checks" not in schema["components"]["schemas"]["ReadyResponse"]["properties"]
    assert "checks" in schema["components"]["schemas"]["ReadyDetailResponse"]["properties"]
    assert "200" in internal_ready
    assert "503" in internal_ready
