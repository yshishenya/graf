from pathlib import Path

ROOT = Path(__file__).parents[4]


def test_server_image_contains_alembic_migration_artifacts() -> None:
    dockerfile = (ROOT / "infra/server/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/server/alembic.ini /app/alembic.ini" in dockerfile
    assert "COPY apps/server/src /app/src" in dockerfile


def test_alembic_migration_files_exist_for_clean_database_path() -> None:
    assert (ROOT / "apps/server/alembic.ini").exists()
    versions = ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions"
    assert (versions / "0001_ingest_foundation.py").exists()
    assert (versions / "0002_access_placeholders.py").exists()
