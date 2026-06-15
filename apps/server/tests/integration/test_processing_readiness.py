from twobrain_rec_server.config import Settings


def test_processing_dependency_detail_is_non_blocking_when_processing_disabled(client) -> None:
    ready = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert ready.status_code == 200
    assert ready.json()["checks"]["processing"] == "disabled"
    assert ready.json()["checks"]["temporal"] == "not_required"


def test_production_processing_enabled_requires_temporal_and_mediascribe_secret(tmp_path) -> None:
    api_key_file = tmp_path / "mediascribe_api_key"
    api_key_file.write_text("test-key", encoding="utf-8")
    settings = Settings(
        env="production",
        database_url="postgresql+asyncpg://twobrain_rec:prod-pass@rec-postgres:5432/twobrain_rec",
        minio_endpoint="rec-minio:9000",
        minio_access_key="twobrain_rec_api",
        minio_secret_key="prod-minio-secret",
        smoke_identity_class="internal_smoke",
        auth_ru_local_storage_attested=True,
        processing_enabled=True,
        temporal_address="rec-temporal:7233",
        mediascribe_base_url="https://mediascribe.2brain.pro",
        mediascribe_api_key_file=api_key_file,
    )
    assert settings.processing_enabled is True
