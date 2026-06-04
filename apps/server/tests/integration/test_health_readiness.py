def test_ready_reports_not_ready_when_database_probe_fails(client) -> None:
    client.app.state.db_sessionmaker = None

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

    blocked_internal = client.get("/api/v1/health/ready/internal")
    assert blocked_internal.status_code == 403
    assert blocked_internal.json() == {"status": "forbidden"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 503
    assert internal.json()["checks"]["postgres"] == "unreachable"


def test_ready_reports_not_ready_when_minio_probe_fails(client) -> None:
    class FailingStorage:
        def ensure_bucket(self) -> None:
            raise RuntimeError("minio unavailable")

    client.app.state.storage = FailingStorage()

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 503
    assert internal.json()["checks"]["minio"] == "unreachable"


def test_ready_reports_ready_without_dependency_detail(client) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 200
    assert internal.json()["status"] == "ready"
    assert internal.json()["checks"]["postgres"] == "ok"
    assert internal.json()["checks"]["minio"] == "ok"
