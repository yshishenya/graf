from tests.contract.test_ingest_openapi_contract import auth_headers


def test_readiness_excludes_temporal_and_mediascribe_dependencies(client) -> None:
    response = client.get(
        "/api/v1/health/ready/internal",
        headers=auth_headers() | {"X-Internal-Health-Check": "true"},
    )
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert checks["temporal"] == "not_required"
    assert checks["mediascribe"] == "not_required"
