from pathlib import Path

TEMPLATE_PATH = Path(__file__).parents[4] / "infra/env/rec.production.env.example"


def test_production_env_template_lists_required_secret_sources_without_live_values() -> None:
    text = TEMPLATE_PATH.read_text()

    for variable in [
        "TWOBRAIN_POSTGRES_PASSWORD",
        "TWOBRAIN_MINIO_ROOT_USER",
        "TWOBRAIN_MINIO_ROOT_PASSWORD",
        "TWOBRAIN_MINIO_API_ACCESS_KEY",
        "TWOBRAIN_MINIO_API_SECRET_KEY",
        "TWOBRAIN_SMOKE_CREDENTIAL_FILE",
    ]:
        assert variable in text

    forbidden_values = [
        "twobrain_rec_dev_secret",
        "minioadmin",
        "changeme",
        "password123",
        "Bearer ",
        "X-Amz-Signature",
    ]
    for value in forbidden_values:
        assert value not in text


def test_production_env_template_documents_owner_rotation_and_failure_behavior() -> None:
    text = TEMPLATE_PATH.read_text().lower()

    assert "owner:" in text
    assert "rotation:" in text
    assert "fail closed" in text
