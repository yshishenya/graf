import pytest

from tests.fixtures.deployment import smoke_evidence_record
from twobrain_rec_server.deployment import PlaybackNormalizationDeploymentEvidence

NORMALIZATION_GATE_FIELDS = (
    "migration_0022_result",
    "image_capability_result",
    "profile_contract_result",
    "media_worker_result",
    "automatic_retry_result",
    "backfill_inventory_result",
    "range_playback_result",
    "cleanup_result",
    "forbidden_metadata_result",
)


def _normalization_gate_payload(**overrides: str) -> dict[str, str]:
    payload = {field: "pass" for field in NORMALIZATION_GATE_FIELDS}
    payload.update(
        {
            "readiness_state": "ready",
            "runtime_sha": "candidate-sha",
            "profile_version": "review_m4a_aac_lc_48k_mono_64k_v1",
            "validation_version": "playback_validator_v1",
        }
    )
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "overrides",
    [
        {"restore_or_rollback_rehearsal_result": "blocked"},
        {"cleanup_result": "blocked"},
        {"log_redaction_result": "failed"},
        {"no_forbidden_side_effects_result": "failed"},
    ],
)
def test_blocked_deployment_gates_prevent_infra_smoke_ready(overrides: dict[str, str]) -> None:
    payload = {
        "readiness_verdict": "infra_smoke_ready",
        **overrides,
    }

    with pytest.raises(ValueError):
        smoke_evidence_record(**payload)


def test_normalization_deployment_ready_requires_every_feature_gate() -> None:
    evidence = PlaybackNormalizationDeploymentEvidence(**_normalization_gate_payload())

    assert evidence.readiness_state == "ready"
    assert evidence.scope == "playback_normalization_capability"


@pytest.mark.parametrize("gate", NORMALIZATION_GATE_FIELDS)
def test_normalization_deployment_ready_rejects_any_non_pass_gate(gate: str) -> None:
    with pytest.raises(ValueError, match=gate):
        PlaybackNormalizationDeploymentEvidence(
            **_normalization_gate_payload(**{gate: "blocked"})
        )


def test_remote_deploy_script_declares_and_executes_all_normalization_gates() -> None:
    from pathlib import Path

    repo_root = Path(__file__).parents[4]
    wrapper = (repo_root / "infra/scripts/cd-remote.sh").read_text()
    runtime = (repo_root / "infra/scripts/cd-remote-runtime.sh").read_text()

    for token in (
        "migration_head",
        "runtime_db_role_bootstrap",
        "runtime_database_identity",
        "image_capability",
        "profile_contract",
        "media_worker",
        "automatic_retry",
        "backfill_inventory",
        "range_playback",
        "normalization_cleanup",
    ):
        assert token in wrapper + runtime
    assert 'bash infra/scripts/cd-remote-runtime.sh "$branch" "$expected_sha" "$previous_sha"' in wrapper
    assert "rec-media-worker" in runtime
    assert "twobrain_rec_app" in runtime
    assert "for role_name in twobrain_rec_app twobrain_rec_media twobrain_rec_maintenance" in runtime
    assert "twobrain_rec_media" in runtime
    assert "scheduler_function_access=denied" in runtime
    assert "scheduler_function_access=allowed" in runtime
    assert "media_worker_network_boundary_failed" in runtime
    assert "no-new-privileges:true" in runtime


@pytest.mark.parametrize(
    ("compose_images", "inspect_result", "expected_code"),
    [
        (
            "twobrain-rec-rec-api\ntwobrain-rec-rec-media-worker\npostgres:17-alpine",
            "pass",
            0,
        ),
        ("twobrain-rec-rec-api\npostgres:17-alpine", "pass", 1),
        ("twobrain-rec-rec-media-worker", "fail", 1),
    ],
)
def test_remote_deploy_resolves_new_media_image_without_existing_container(
    compose_images: str,
    inspect_result: str,
    expected_code: int,
) -> None:
    import os
    import subprocess
    from pathlib import Path

    runtime = (
        Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh"
    ).read_text()
    gate_start = runtime.index('media_image_ref="$(')
    gate_end = runtime.index("expected_schema_head=", gate_start)
    image_gate = runtime[gate_start:gate_end]
    fixture_script = f"""
set -euo pipefail
docker() {{
  if [[ "$1" == "compose" && "$2" == "config" && "$3" == "--images" ]]; then
    printf '%s\\n' "$COMPOSE_IMAGES"
    return 0
  fi
  if [[ "$1" == "image" && "$2" == "inspect" ]]; then
    [[ "$3" == "twobrain-rec-rec-media-worker" ]] || return 8
    [[ "$INSPECT_RESULT" == "pass" ]] || return 1
    printf 'sha256:fixture\\n'
    return 0
  fi
  return 9
}}
compose=(docker compose)
{image_gate}
"""

    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "COMPOSE_IMAGES": compose_images,
            "INSPECT_RESULT": inspect_result,
        },
    )

    assert '"${compose[@]}" config --images' in runtime
    assert 'docker image inspect "$media_image_ref"' in runtime
    assert '"${compose[@]}" images -q rec-media-worker' not in runtime
    assert result.returncode == expected_code
    if expected_code == 1:
        assert "reason=media_worker_image_missing" in result.stdout


def test_remote_deploy_rollback_never_deletes_099_truth_to_reach_old_code() -> None:
    from pathlib import Path

    runtime = (
        Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh"
    ).read_text()

    assert "delete from playback_normalization" not in runtime.lower()
    assert "delete from track_artifacts" not in runtime.lower()
    assert "mc find" not in runtime
    assert '"$truth_count" == "0"' in runtime
    assert '"$dispatch_opened" == "0"' in runtime
    assert "rollback_target=compatibility_099" in runtime
    assert "legacy_playback_guard_retained=true" in runtime
    assert "verify_api_dispatch_gate false false" in runtime


def test_remote_deploy_turns_signals_into_nonzero_exit_for_rollback_trap() -> None:
    from pathlib import Path

    runtime = (
        Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh"
    ).read_text()

    assert "trap rollback_on_exit EXIT" in runtime
    assert "trap 'exit 130' INT" in runtime
    assert "trap 'exit 143' TERM" in runtime


def test_remote_deploy_marks_dispatch_open_before_enabling_worker_reconciliation() -> None:
    from pathlib import Path

    runtime = (
        Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh"
    ).read_text()
    marker_index = runtime.index("dispatch_opened=1")
    enabled_worker_index = runtime.index(
        "TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=true",
        marker_index,
    )

    assert marker_index < enabled_worker_index
