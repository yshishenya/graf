import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]
SMOKE_PATH = REPO_ROOT / "infra/scripts/run-product-analytics-provider-smoke.sh"


def test_provider_smoke_output_covers_dashboard_blockers_and_no_secret_status() -> None:
    result = subprocess.run(
        [str(SMOKE_PATH)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    expected_lines = {
        "provider_smoke_result=pass",
        "posthog_stack=config_valid",
        "posthog_stack_contract=handoff_valid",
        "posthog_runtime_source=official_posthog_hobby_generated_compose_required",
        "posthog_delivery=dry_run",
        "posthog_live_safe_delivery=transport_verified",
        "provider_transport_evidence=synthetic_test_process_only",
        "restore_gate=blocked_before_and_after_transport_test",
        "posthog_web_direct=render_config_present",
        "posthog_desktop_direct=contract_tested",
        "posthog_autocapture=current_pages_enabled",
        "yandex_offline=dry_run_two_conversions",
        "yandex_render_config=present",
        "yandex_live_safe_upload=transport_verified",
        "dashboard_readiness=metadata_only_live_safe_verified",
        "dashboard_goal_visibility=metadata_only_contract_verified",
        "dashboard_owner=role_only",
        "dashboard_provider_gap_caveat=present",
        "provider_blockers=legal_privacy_security_qa_disclosure_campaign_product_rollout_separate",
        "product_rollout=blocked",
        "campaign_launch=blocked",
        "no_secret_scan=metadata_only_pass",
        "private_payload_status=none_committed",
        "rollback_status=metadata_only_not_executed",
        "rollback_execution=metadata_only_no_state_change",
    }
    for line in expected_lines:
        assert line in output

    forbidden_fragments = ("phc_", "oauth", "cookie=", "clientid", "yclid", "raw_payload", "properties")
    assert all(fragment not in output.lower() for fragment in forbidden_fragments)


def test_provider_smoke_python_checks_restore_gate_without_network() -> None:
    body = SMOKE_PATH.read_text().split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    prelude = """
import sys
def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("provider smoke attempted network access")
sys.addaudithook(deny_network)
"""
    result = subprocess.run(
        [sys.executable, "-c", prelude + body],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(REPO_ROOT / "apps/server"), str(REPO_ROOT / "apps/server/src"))),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "provider_smoke_result=pass" in result.stdout
    assert "provider_transport_evidence=synthetic_test_process_only" in result.stdout
    assert "restore_gate=blocked_before_and_after_transport_test" in result.stdout
