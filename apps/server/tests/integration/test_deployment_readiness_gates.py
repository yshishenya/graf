import os
import subprocess
from pathlib import Path

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
        PlaybackNormalizationDeploymentEvidence(**_normalization_gate_payload(**{gate: "blocked"}))


def test_remote_deploy_script_declares_and_executes_all_normalization_gates() -> None:
    repo_root = Path(__file__).parents[4]
    wrapper = (repo_root / "infra/scripts/cd-remote.sh").read_text()
    runtime = (repo_root / "infra/scripts/cd-remote-runtime.sh").read_text()

    for token in (
        "migration_head",
        "runtime_db_role_bootstrap",
        "runtime_database_identity",
        "runtime_service_secret_permissions",
        "temporal_readiness",
        "processing_worker_readiness",
        "image_capability",
        "profile_contract",
        "media_worker",
        "automatic_retry",
        "backfill_inventory",
        "range_playback",
        "normalization_cleanup",
    ):
        assert token in wrapper + runtime
    assert (
        'bash infra/scripts/cd-remote-runtime.sh "$branch" "$expected_sha" "$previous_sha"'
        in wrapper
    )
    assert "rec-media-worker" in runtime
    assert "twobrain_rec_app" in runtime
    assert (
        "for role_name in twobrain_rec_app twobrain_rec_media twobrain_rec_maintenance" in runtime
    )
    assert "twobrain_rec_media" in runtime
    assert "scheduler_function_access=denied" in runtime
    assert "scheduler_function_access=allowed" in runtime
    assert "media_worker_network_boundary_failed" in runtime
    assert "no-new-privileges:true" in runtime
    assert "HostConfig.GroupAdd" in runtime
    dry_run_steps = next(line for line in wrapper.splitlines() if line.startswith("steps="))
    assert "runtime_secret_group" in dry_run_steps
    assert 'export TWOBRAIN_LANGFUSE_RELEASE="$expected_sha"' in runtime
    assert runtime.count('export TWOBRAIN_LANGFUSE_RELEASE="$previous_sha"') == 2


def test_remote_deploy_secures_runtime_secrets_for_private_runtime_group(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("validate_runtime_secret_group()")
    helper_end = runtime.index("cleanup_runtime_files()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    secret_path = tmp_path / "generated-secret"
    secret_path.write_text("non-sensitive-fixture\n", encoding="utf-8")
    secret_path.chmod(0o600)

    fixture_script = f"""
set -euo pipefail
runtime_secret_gid=1001
{helper_source}
id() {{
  case "$1" in
    -g) printf '1001\\n' ;;
    -u) printf '1001\\n' ;;
    -un) printf 'yan\\n' ;;
    *) return 2 ;;
  esac
}}
getent() {{
  case "$1" in
    group) printf 'yan:x:1001:\\n' ;;
    passwd) printf 'yan:x:1001:1001::/home/yan:/bin/bash\\n' ;;
    *) return 2 ;;
  esac
}}
chgrp() {{ [[ "$1" == "1001" && "$2" == "--" && "$3" == {str(secret_path)!r} ]]; }}
chmod() {{ [[ "$1" == "640" && "$2" == "--" && "$3" == {str(secret_path)!r} ]]; }}
ls() {{ printf '%s\n' '-rw-r----- 1 1001 1001 22 Jul 16 00:00 fixture'; }}
stat() {{
  if [[ "$2" == "%u:%h" ]]; then
    printf '1001:1\\n'
  else
    printf '1001:1001:640:1\\n'
  fi
}}
validate_runtime_secret_group
secure_runtime_secret_file {str(secret_path)!r}
printf 'runtime_secret_private_group_result=pass\\n'
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ},
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "runtime_secret_private_group_result=pass\n"
    validate_call = runtime.index("if ! validate_runtime_secret_group; then")
    ensure_call = runtime.index("ensure_generated_secret \\")
    assert validate_call < ensure_call < runtime.index("backup_output=")
    assert 'export TWOBRAIN_RUNTIME_SECRET_GID="$runtime_secret_gid"' in runtime
    service_secret_call = runtime.index("for runtime_service_secret in \\")
    assert validate_call < service_secret_call < ensure_call
    for secret_variable in (
        "GRAF_CREDENTIAL_ENCRYPTION_KEY_SECRET_FILE",
        "TWOBRAIN_WEB_CSRF_SECRET_FILE",
        "TWOBRAIN_POSTAL_API_SECRET_FILE",
        "TWOBRAIN_YANDEX_CLIENT_SECRET_FILE",
        "TWOBRAIN_VK_CLIENT_SECRET_FILE",
        "TWOBRAIN_SUPPORT_INCIDENT_GITHUB_TOKEN_FILE",
        "TWOBRAIN_LANGFUSE_PUBLIC_KEY_SECRET_FILE",
        "TWOBRAIN_LANGFUSE_SECRET_KEY_SECRET_FILE",
        "TWOBRAIN_MEDIASCRIBE_API_KEY_FILE",
        "TWOBRAIN_MINIO_API_ACCESS_KEY_FILE",
        "TWOBRAIN_MINIO_API_SECRET_KEY_FILE",
        "TWOBRAIN_SMOKE_CREDENTIAL_FILE",
        "TWOBRAIN_POSTGRES_PASSWORD_FILE",
        "TWOBRAIN_MINIO_ROOT_USER_FILE",
        "TWOBRAIN_MINIO_ROOT_PASSWORD_FILE",
    ):
        assert secret_variable in runtime[service_secret_call:ensure_call]
    assert "runtime_service_secret_permissions_result=pass" in runtime
    litellm_gate = runtime.index('litellm_secret_file="${TWOBRAIN_LITELLM_API_KEY_SECRET_FILE:-}"')
    assert service_secret_call < litellm_gate < ensure_call
    assert '"${TWOBRAIN_OUTCOME_GENERATION_ENABLED:-false}" == "true"' in runtime
    assert '"${TWOBRAIN_PROMPT_OPTIMIZATION_ENABLED:-false}" == "true"' in runtime
    assert "reason=litellm_secret_permissions_invalid" in runtime[litellm_gate:ensure_call]
    assert "litellm_secret_permissions_result=pass" in runtime[litellm_gate:ensure_call]


@pytest.mark.parametrize(
    ("runtime_gid", "current_gid", "group_record", "passwd_records"),
    [
        ("999", "999", "fixture:x:999:", "fixture:x:999:999::/:/bin/false\n"),
        ("1001", "2000", "yan:x:1001:", "yan:x:1001:1001::/:/bin/false\n"),
        ("1001", "1001", "yan:x:1001:other", "yan:x:1001:1001::/:/bin/false\n"),
        (
            "1001",
            "1001",
            "yan:x:1001:",
            "yan:x:1001:1001::/:/bin/false\nother:x:1002:1001::/:/bin/false\n",
        ),
        ("not-a-gid", "1001", "yan:x:1001:", "yan:x:1001:1001::/:/bin/false\n"),
    ],
)
def test_remote_deploy_rejects_non_private_runtime_secret_group(
    runtime_gid: str,
    current_gid: str,
    group_record: str,
    passwd_records: str,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("validate_runtime_secret_group()")
    helper_end = runtime.index("secure_runtime_secret_file()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    fixture_script = f"""
set -euo pipefail
runtime_secret_gid="$FIXTURE_RUNTIME_GID"
{helper_source}
id() {{
  case "$1" in
    -g) printf '%s\\n' "$FIXTURE_CURRENT_GID" ;;
    -un) printf 'yan\\n' ;;
    *) return 2 ;;
  esac
}}
getent() {{
  case "$1" in
    group) printf '%s\\n' "$FIXTURE_GROUP_RECORD" ;;
    passwd) printf '%s' "$FIXTURE_PASSWD_RECORDS" ;;
    *) return 2 ;;
  esac
}}
if validate_runtime_secret_group; then
  printf 'runtime_secret_group_result=unsafe_accept\\n'
  exit 1
fi
printf 'runtime_secret_group_result=blocked\\n'
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "FIXTURE_RUNTIME_GID": runtime_gid,
            "FIXTURE_CURRENT_GID": current_gid,
            "FIXTURE_GROUP_RECORD": group_record,
            "FIXTURE_PASSWD_RECORDS": passwd_records,
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "runtime_secret_group_result=blocked\n"


def test_remote_deploy_rejects_unsafe_secret_inode_before_permission_change(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("secure_runtime_secret_file()")
    helper_end = runtime.index("ensure_generated_secret()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    secret_path = tmp_path / "linked-secret"
    secret_path.write_text("non-sensitive-fixture\n", encoding="utf-8")
    fixture_script = f"""
set -euo pipefail
runtime_secret_gid=1001
{helper_source}
id() {{ printf '1001\\n'; }}
stat() {{ printf '1001:2\\n'; }}
chgrp() {{ printf 'unsafe_mutation=chgrp\\n'; }}
chmod() {{ printf 'unsafe_mutation=chmod\\n'; }}
if secure_runtime_secret_file {str(secret_path)!r}; then
  printf 'unsafe_inode_result=accepted\\n'
  exit 1
fi
printf 'unsafe_inode_result=blocked\\n'
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ},
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "unsafe_inode_result=blocked\n"


def test_remote_deploy_rejects_secret_with_extended_acl_before_permission_change(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("secure_runtime_secret_file()")
    helper_end = runtime.index("ensure_generated_secret()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    secret_path = tmp_path / "acl-secret"
    secret_path.write_text("non-sensitive-fixture\n", encoding="utf-8")
    fixture_script = f"""
set -euo pipefail
runtime_secret_gid=1001
{helper_source}
id() {{ printf '1001\n'; }}
stat() {{ printf '1001:1\n'; }}
ls() {{ printf '%s\n' '-rw-r-----+ 1 1001 1001 22 Jul 16 00:00 fixture'; }}
chgrp() {{ printf 'unsafe_mutation=chgrp\n'; }}
chmod() {{ printf 'unsafe_mutation=chmod\n'; }}
if secure_runtime_secret_file {str(secret_path)!r}; then
  printf 'extended_acl_result=accepted\n'
  exit 1
fi
printf 'extended_acl_result=blocked\n'
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ},
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "extended_acl_result=blocked\n"


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

    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
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

    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert "delete from playback_normalization" not in runtime.lower()
    assert "delete from track_artifacts" not in runtime.lower()
    assert "mc find" not in runtime
    assert '"$truth_count" == "0"' in runtime
    assert '"$dispatch_opened" == "0"' in runtime
    assert "rollback_target=compatibility_099" in runtime
    assert "legacy_playback_guard_retained=true" in runtime
    assert "verify_api_dispatch_gate false false" in runtime
    compatibility_start = runtime.index("restore_compatibility_runtime()")
    compatibility_end = runtime.index("restore_previous_runtime()", compatibility_start)
    compatibility_block = runtime[compatibility_start:compatibility_end]
    assert "rec-temporal rec-processing-worker rec-api" in compatibility_block
    assert "verify_processing_runtime_health" in compatibility_block
    assert compatibility_block.index(
        "verify_processing_runtime_health"
    ) < compatibility_block.index('echo "rollback_result=pass"')
    fallback_start = runtime.index("restore_previous_safe_processing_runtime()")
    fallback_end = runtime.index("restore_previous_runtime()", fallback_start)
    fallback_block = runtime[fallback_start:fallback_end]
    assert 'git reset --hard "$previous_sha"' in fallback_block
    assert (
        'docker network disconnect twobrain-rec-media-private "$temporal_container"'
        in fallback_block
    )
    assert "--task-queue-type-legacy workflow" in runtime
    assert "--task-queue-type-legacy activity" in runtime
    assert "wait_for_previous_processing_pollers" in fallback_block
    assert "verify_api_dispatch_gate false false" in fallback_block
    assert "media_worker_present=false" in fallback_block
    restore_start = runtime.index("restore_previous_runtime()")
    restore_end = runtime.index("rollback_on_exit()", restore_start)
    restore_block = runtime[restore_start:restore_end]
    assert restore_block.index("restore_compatibility_runtime") < restore_block.index(
        "restore_previous_safe_processing_runtime"
    )


def test_remote_rollback_uses_compatibility_runtime_when_legacy_lineage_blocks_downgrade(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    restore_start = runtime.index("restore_previous_runtime()")
    restore_end = runtime.index("rollback_on_exit()", restore_start)
    restore_block = runtime[restore_start:restore_end]
    trace_path = tmp_path / "rollback-trace"
    fixture_script = f"""
set -euo pipefail
compose=(compose_stub)
dispatch_opened=0
previous_schema_head=0037_auth_rate_limit_buckets
expected_schema_head=0041_share_account_created_email
backup_reference=fixture-backup
legacy_lineage_rows=1
{restore_block}
feature_truth_count() {{ printf '0\\n'; }}
rollback_feature_database() {{
  printf 'legacy_lineage_rows=%s\\n' "$legacy_lineage_rows" >>"$TRACE_PATH"
  return 1
}}
rollback_feature_storage() {{ printf 'unsafe_storage_rollback\\n' >>"$TRACE_PATH"; return 0; }}
restore_previous_services() {{ printf 'unsafe_previous_checkout\\n' >>"$TRACE_PATH"; return 0; }}
restore_compatibility_runtime() {{
  printf 'compatibility_runtime_started\\n' >>"$TRACE_PATH"
  return 0
}}
compose_stub() {{
  case "$1:${{2:-}}:${{3:-}}" in
    ps:-q:rec-media-worker) return 0 ;;
    stop:*) return 0 ;;
    exec:-T:rec-postgres) printf '%s\\n' "$expected_schema_head" ;;
    *) return 2 ;;
  esac
}}
restore_previous_runtime
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "TRACE_PATH": str(trace_path)},
    )

    assert result.returncode == 0, result.stderr
    trace = trace_path.read_text()
    assert "legacy_lineage_rows=1" in trace
    assert "rollback_database_downgrade=blocked" in result.stdout
    assert "compatibility_runtime_started" in trace
    assert "unsafe_storage_rollback" not in trace
    assert "unsafe_previous_checkout" not in trace


def test_remote_rollback_discovers_operations_profile_services() -> None:
    from pathlib import Path

    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert "compose=(docker compose --profile operations -f infra/docker-compose.yml)" in runtime
    assert '"${compose[@]}" config --services' in runtime
    assert "rec-maintenance" in runtime
    assert "rec-reprocess-maintenance" in runtime
    assert "maintenance_container" in runtime
    assert "maintenance_restart_count" in runtime
    assert "{{.State.Status}}" in runtime


def test_previous_safe_processing_fallback_executes_verified_single_network_restore(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("wait_for_previous_temporal_health()")
    helper_end = runtime.index("restore_previous_runtime()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    trace_path = tmp_path / "rollback-trace"
    fixture_script = f"""
set -euo pipefail
compose=(compose_stub)
previous_sha=previous-safe-sha
backup_reference=fixture-backup
previous_schema_head=0023_production_smoke_setup
expected_schema_head=0023_production_smoke_setup
{helper_source}
git() {{
  printf 'git_%s_%s\n' "$1" "$2" >>"$TRACE_PATH"
  [[ "$1" == "reset" && "$2" == "--hard" && "$3" == "$previous_sha" ]]
}}
compose_stub() {{
  case "$1:$2:${{3:-}}" in
    build:rec-api:rec-processing-worker)
      printf 'compose_build_previous\n' >>"$TRACE_PATH"
      ;;
    ps:-aq:rec-media-worker)
      printf 'media-container\n'
      ;;
    ps:-q:rec-temporal)
      printf 'temporal-container\n'
      ;;
    ps:-q:rec-processing-worker)
      printf 'processing-container\n'
      ;;
    stop:*)
      printf 'compose_stop_runtime\n' >>"$TRACE_PATH"
      ;;
    up:*)
      if [[ "$*" == *"rec-temporal"* ]]; then
        printf 'compose_up_previous_temporal\n' >>"$TRACE_PATH"
      elif [[ "$*" == *"rec-processing-worker"* ]]; then
        printf 'compose_up_previous_processing\n' >>"$TRACE_PATH"
      elif [[ "$*" == *"rec-api"* ]]; then
        printf 'compose_up_previous_api\n' >>"$TRACE_PATH"
      fi
      ;;
    *) return 2 ;;
  esac
}}
docker() {{
  case "$1:$2" in
    rm:-f)
      printf 'docker_remove_media\n' >>"$TRACE_PATH"
      ;;
    network:disconnect)
      [[ "$3" == "twobrain-rec-media-private" && "$4" == "temporal-container" ]]
      printf 'docker_disconnect_media_network\n' >>"$TRACE_PATH"
      ;;
    restart:temporal-container)
      printf 'docker_restart_temporal\n' >>"$TRACE_PATH"
      ;;
    inspect:processing-container)
      printf 'previous-worker\n'
      ;;
    exec:temporal-container)
      if [[ "$*" == *"operator cluster health"* ]]; then
        printf 'temporal_cluster_health\n' >>"$TRACE_PATH"
      elif [[ "$*" == *"task-queue-type-legacy workflow"* ]]; then
        printf 'workflow_poller_receipt\n' >>"$TRACE_PATH"
        printf '1@previous-worker\n'
      elif [[ "$*" == *"task-queue-type-legacy activity"* ]]; then
        printf 'activity_poller_receipt\n' >>"$TRACE_PATH"
        printf '1@previous-worker\n'
      else
        return 2
      fi
      ;;
    *) return 2 ;;
  esac
}}
verify_api_dispatch_gate() {{
  [[ "$1" == "false" && "$2" == "false" ]]
  printf 'api_dispatch_closed\n' >>"$TRACE_PATH"
}}
curl() {{ printf 'public_health\n' >>"$TRACE_PATH"; }}
restore_previous_safe_processing_runtime 0023_production_smoke_setup
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "TRACE_PATH": str(trace_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "rollback_result=pass" in result.stdout
    assert "rollback_target=previous_safe_processing_runtime" in result.stdout
    trace = trace_path.read_text()
    for receipt in (
        "git_reset_--hard",
        "compose_build_previous",
        "docker_disconnect_media_network",
        "docker_restart_temporal",
        "temporal_cluster_health",
        "compose_up_previous_processing",
        "workflow_poller_receipt",
        "activity_poller_receipt",
        "compose_up_previous_api",
        "api_dispatch_closed",
    ):
        assert receipt in trace
    assert trace.index("git_reset_--hard") < trace.index("compose_build_previous")
    assert trace.index("docker_disconnect_media_network") < trace.index("temporal_cluster_health")
    assert trace.index("activity_poller_receipt") < trace.index("api_dispatch_closed")


def test_previous_sha_fallback_is_forbidden_for_incompatible_schema(
    tmp_path: Path,
) -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    helper_start = runtime.index("restore_previous_runtime()")
    helper_end = runtime.index("rollback_on_exit()", helper_start)
    helper_source = runtime[helper_start:helper_end]
    trace_path = tmp_path / "incompatible-schema-trace"
    fixture_script = f"""
set -euo pipefail
compose=(compose_stub)
dispatch_opened=1
previous_schema_head=0022_previous
expected_schema_head=0023_expected
previous_sha=previous-incompatible-sha
backup_reference=fixture-backup
{helper_source}
compose_stub() {{
  case "$1" in
    ps) return 0 ;;
    stop) return 0 ;;
    exec) printf '0023_expected\n' ;;
    *) return 2 ;;
  esac
}}
feature_truth_count() {{ printf '1\n'; }}
restore_compatibility_runtime() {{
  printf 'rollback_attempt=compatibility_runtime_failed\n'
  return 1
}}
restore_previous_safe_processing_runtime() {{
  printf 'unsafe_previous_fallback_called\n' >>"$TRACE_PATH"
  return 0
}}
restore_previous_runtime
"""
    result = subprocess.run(
        ["bash", "-c", fixture_script],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "TRACE_PATH": str(trace_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "rollback_result=blocked" in result.stdout
    assert "rollback_target=forward_fix_required" in result.stdout
    assert not trace_path.exists()


def test_remote_deploy_rechecks_temporal_and_processing_worker_before_success() -> None:
    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()

    final_check = runtime.rindex("if ! verify_processing_runtime_health; then")
    completion = runtime.index("deployment_complete=1", final_check)
    assert final_check < runtime.index("final_temporal_readiness_result=pass", final_check)
    assert final_check < runtime.index("final_processing_worker_readiness_result=pass", final_check)
    assert final_check < completion
    health_helper = runtime[
        runtime.index("verify_processing_runtime_health()") : runtime.index(
            "rollback_feature_storage()"
        )
    ]
    assert "{{.RestartCount}}" in health_helper
    assert "restart_baseline" in health_helper
    assert "twobrain-rec-private" in health_helper
    assert "twobrain-rec-media-private" in health_helper


def test_remote_deploy_turns_signals_into_nonzero_exit_for_rollback_trap() -> None:
    from pathlib import Path

    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert "trap rollback_on_exit EXIT" in runtime
    assert "trap 'exit 130' INT" in runtime
    assert "trap 'exit 143' TERM" in runtime


def test_remote_deploy_marks_dispatch_open_before_enabling_worker_reconciliation() -> None:
    from pathlib import Path

    runtime = (Path(__file__).parents[4] / "infra/scripts/cd-remote-runtime.sh").read_text()
    marker_index = runtime.index("dispatch_opened=1")
    enabled_worker_index = runtime.index(
        "TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=true",
        marker_index,
    )

    assert marker_index < enabled_worker_index
