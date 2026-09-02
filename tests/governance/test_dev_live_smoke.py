from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_live_smoke_contains_all_required_named_checks():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    for check in ("backend_health", "frontend_reachability", "auth_session_bootstrap", "representative_api", "temporal_readiness", "processing_worker_readiness", "media_worker_readiness", "database_readiness", "storage_readiness", "migration_readiness", "app_identity", "app_presentation", "exact_source_sha"):
        assert f'"{check}"' in source


def test_fixture_smoke_is_explicitly_non_authoritative():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert '"authoritative": "false"' in source
