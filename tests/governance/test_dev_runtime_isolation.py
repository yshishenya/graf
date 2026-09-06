from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_old_local_adapter_is_not_called_by_active_startup():
    harness = (ROOT / "scripts/dev-harness.py").read_text()
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    assert "docker-compose.dev.yml" in harness
    assert "start-local.sh" not in startup
    assert startup.count("--force-recreate") == 2


def test_dev_state_and_origins_are_bounded():
    harness = (ROOT / "scripts/dev-harness.py").read_text()
    assert "production-looking Dev state path" in harness
    assert "loopback" in harness
    assert "GRAF_DEV_COMPOSE_PROJECT" in harness


def test_credentials_are_placed_under_machine_local_state_not_checkout():
    harness = (ROOT / "scripts/dev-harness.py").read_text()
    assert 'self.state / "secrets"' in harness
    assert 'self.root / "infra" / "secrets"' not in harness
