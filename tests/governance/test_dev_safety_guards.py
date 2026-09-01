from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_active_runtime_has_no_destructive_migration_repair():
    source = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text() + (ROOT / "infra/scripts/dev-migration-preflight.py").read_text()
    assert "alembic stamp" not in source
    assert "down -v" not in source
    assert "alembic_version" not in source or "never mutates" in source


def test_provider_egress_is_disabled_by_default():
    compose = (ROOT / "infra/docker-compose.dev.yml").read_text()
    assert 'TWOBRAIN_MEDIASCRIBE_BASE_URL: ""' in compose
    assert 'TWOBRAIN_LITELLM_BASE_URL: ""' in compose
    assert 'TWOBRAIN_LANGFUSE_BASE_URL: ""' in compose
