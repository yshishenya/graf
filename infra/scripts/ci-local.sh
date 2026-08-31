#!/usr/bin/env bash

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  echo "usage: $0 --fast|--full|--help" >&2
}

classify_path() {
  case "$1" in
    apps/server/*)
      echo server
      ;;
    apps/macos/*)
      echo macos
      ;;
    infra/docker-compose.yml|infra/server/*|infra/dev/*|infra/release/*|infra/scripts/*.sh|infra/scripts/*.py|\
    harness/*|tests/governance/*|changes/unreleased/*|\
    docs/deployments/*|\
    scripts/*|.specify/*|.github/workflows/*|.github/actions/*|\
    Dockerfile*|docker-compose*|Makefile|pyproject.toml)
      echo infra
      ;;
    AGENTS.md|.github/pull_request_template.md|docs/agent-guidance/*|\
    infra/scripts/README.md)
      echo governance
      ;;
    CHANGELOG.md|README.md|CONTRIBUTING.md|docs/*|specs/*)
      echo docs
      ;;
    *)
      echo unknown
      ;;
  esac
}

performance_path() {
  case "$1" in
    apps/server/src/twobrain_rec_server/calendar/*|\
    apps/server/src/twobrain_rec_server/api/calendar.py|\
    apps/server/src/twobrain_rec_server/db/models/calendar.py|\
    apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py|\
    apps/server/tests/integration/test_calendar_auto_context_match.py)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

calendar_performance_test_path() {
  printf '%s\n' 'tests/integration/test_calendar_auto_context_match.py'
}

bounded_server_path() {
  case "$1" in
    apps/server/src/twobrain_rec_server/calendar/*|\
    apps/server/src/twobrain_rec_server/domain/*|\
    apps/server/tests/unit/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

merge_base_commit() {
  local base_ref="${GRAF_CI_BASE_REF:-origin/master}"
  git -C "$repo_root" rev-parse --verify "$base_ref^{commit}" >/dev/null 2>&1 || return 1
  git -C "$repo_root" merge-base HEAD "$base_ref"
}

changed_files() {
  local merge_base
  local tracked_changes
  local untracked_changes
  merge_base="$(merge_base_commit)" || return 1
  tracked_changes="$(git -C "$repo_root" diff --no-renames --name-only "$merge_base" --)" || return 1
  untracked_changes="$(git -C "$repo_root" ls-files --others --exclude-standard)" || return 1
  printf '%s\n%s\n' "$tracked_changes" "$untracked_changes" | LC_ALL=C sort -u
}

run_step() {
  local name="$1"
  local started_at
  local completed_at
  local duration_seconds
  local status
  shift
  printf '\n==> %s\n' "$name"
  started_at="$(date +%s)"
  if "$@"; then
    status=0
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'ci_stage=%s status=pass duration_seconds=%s\n' "$name" "$duration_seconds"
  else
    status=$?
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'ci_stage=%s status=fail duration_seconds=%s\n' "$name" "$duration_seconds" >&2
  fi
  return "$status"
}

check_active_docs() {
  python3 - "$repo_root" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
active = [
    root / "AGENTS.md",
    root / ".github/pull_request_template.md",
    root / "docs/agent-guidance/release-and-validation.md",
    root / "docs/agent-guidance/spec-kit-flow.md",
    root / "infra/scripts/README.md",
]
active.extend(path for path in (root / "README.md", root / "CONTRIBUTING.md") if path.is_file())
active.extend(sorted((root / "docs/agent-guidance").rglob("*.md")))
ambiguous = []
for path in dict.fromkeys(active):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "infra/scripts/ci-local.sh" in line and "--fast" not in line and "--full" not in line:
            ambiguous.append(f"{path.relative_to(root)}:{number}")
if ambiguous:
    print("ambiguous_ci_commands=" + ",".join(ambiguous), file=sys.stderr)
    raise SystemExit(1)
print("ci_documentation_consistency=pass")
PY
}

run_server_tests() {
  local mode="$1"
  local performance_gate="$2"
  shift 2
  env GRAF_TEST_WORKERS="${GRAF_TEST_WORKERS:-4}" GRAF_PERFORMANCE_GATE="$performance_gate" \
    bash apps/server/scripts/run_local_postgres_tests.sh "--${mode}" -q "$@"
}

run_changed_server_tests() {
  local performance_gate="$1"
  local changed_test_list="$2"
  local test_files=()
  local path
  while IFS= read -r path; do
    [[ -n "$path" ]] && test_files+=("${path#apps/server/}")
  done <<<"$changed_test_list"
  run_server_tests focused "$performance_gate" "${test_files[@]}"
}

check_shell_syntax() {
  local changed_file_list="$1"
  local shell_files=()
  local path
  while IFS= read -r path; do
    [[ "$path" == *.sh && -f "$repo_root/$path" ]] && shell_files+=("$path")
  done < <(
    { git -C "$repo_root" ls-files '*.sh'; printf '%s\n' "$changed_file_list"; } \
      | LC_ALL=C sort -u
  )
  for path in "${shell_files[@]}"; do
    bash -n "$path" || return $?
  done
}

check_diff_whitespace() {
  local changed_file_list="${1:-}"
  local merge_base
  local path
  local status
  if merge_base="$(merge_base_commit)"; then
    git -C "$repo_root" diff --check "$merge_base" -- || return $?
  else
    git -C "$repo_root" diff --check || return $?
  fi
  while IFS= read -r path; do
    [[ -n "$path" && -f "$repo_root/$path" ]] || continue
    if git -C "$repo_root" ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
      continue
    fi
    git -C "$repo_root" diff --no-index --check -- /dev/null "$path"
    status=$?
    [[ "$status" -le 1 ]] || return "$status"
  done <<<"$changed_file_list"
}

main() (
  set -uo pipefail
  local requested_sha="${GRAF_CI_REQUESTED_SHA:-}"
  local observed_sha_start=""
  local observed_sha_end=""
  local requested_mode="unselected"
  local effective_mode="unselected"
  local components="none"
  local selection_reason="explicit_full"
  local pipeline_result="fail"
  local pipeline_started
  local pipeline_completed
  local pipeline_duration
  local changed_list=""
  local changed_server_tests=""
  local has_server=0
  local needs_server_unit=0
  local has_macos=0
  local has_infra=0
  local has_docs=0
  local has_unknown=0
  local has_governance_tests=0
  local coverage="complete"
  local next_gate="unselected"
  local performance_required=0
  local performance_covered_by_changed_tests=0
  local performance_gate="report"
  local run_id=""
  local candidate_id="${GRAF_CI_CANDIDATE_ID:-}"
  local started_at=""
  local skipped_gates=""
  local evidence_status_override=""
  local evidence_reason_override=""
  local path
  local classification
  local performance_proof
  pipeline_started="$(date +%s)"

  finish_ci() {
    local exit_status=$?
    observed_sha_end="$(git rev-parse HEAD 2>/dev/null || true)"
    local evidence_status="${evidence_status_override:-failed}"
    local evidence_reason="${evidence_reason_override:-}"
    if [[ -n "$observed_sha_start" && "$observed_sha_end" != "$observed_sha_start" ]]; then
      printf 'ci_evidence_status=stale requested_sha=%s observed_sha_start=%s observed_sha_end=%s reason=target_changed_during_run\n' "${requested_sha:-$observed_sha_start}" "$observed_sha_start" "$observed_sha_end" >&2
      exit_status=2
      pipeline_result="fail"
      evidence_status="stale"
      evidence_reason="target_changed_during_run"
    elif [[ "$evidence_status_override" == "stale" ]]; then
      exit_status=2
      pipeline_result="fail"
    elif [[ "$exit_status" -eq 130 || "$exit_status" -eq 143 ]]; then
      evidence_status="cancelled"
      evidence_reason="ci_runner_interrupted"
    elif [[ "$exit_status" -eq 0 && "$pipeline_result" == "pass" ]]; then
      evidence_status="passed"
    else
      evidence_reason="ci_stage_failed"
    fi
    trap - EXIT INT TERM
    pipeline_completed="$(date +%s)"
    pipeline_duration=$((pipeline_completed - pipeline_started))
    if [[ "$requested_mode" == "full" && -n "$candidate_id" && -n "$skipped_gates" \
      && "$pipeline_result" == "pass" ]]; then
      pipeline_result="fail"
      exit_status=1
      evidence_status="failed"
      evidence_reason="full_candidate_skipped_gates"
    fi
    if [[ -n "$observed_sha_start" && "$effective_mode" != "help" ]]; then
      local finished_at
      local evidence_path
      local evidence_args
      finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      evidence_path="${GRAF_CI_EVIDENCE_PATH:-.dev/ci-evidence/${run_id}.json}"
      evidence_args=(
        --output "$evidence_path" --run-id "$run_id" --lane "$effective_mode"
        --requested-sha "${requested_sha:-$observed_sha_start}"
        --observed-sha-start "$observed_sha_start" --observed-sha-end "$observed_sha_end"
        --status "$evidence_status" --started-at "$started_at" --finished-at "$finished_at"
        --command "infra/scripts/ci-local.sh --$requested_mode"
        --scope "components=$components;reason=$selection_reason;coverage=$coverage"
        --component-sha "repository=$observed_sha_start"
      )
      # Bind evidence to bytes produced by the run when available. The source
      # revision digest remains a lightweight identity anchor; build outputs
      # provide the artifact-level provenance required for release decisions.
      [[ -f "$repo_root/CHANGELOG.md" ]] && evidence_args+=(--artifact "changelog=$repo_root/CHANGELOG.md")
      [[ -d "$repo_root/apps/macos/.build" ]] && evidence_args+=(--artifact "macos-build=$repo_root/apps/macos/.build")
      [[ -n "$evidence_reason" ]] && evidence_args+=(--reason "$evidence_reason")
      [[ -n "$candidate_id" ]] && evidence_args+=(--candidate-id "$candidate_id")
      [[ "$requested_mode" == "full" && -n "$candidate_id" ]] && evidence_args+=(--authoritative-full)
      while IFS= read -r skipped; do
        [[ -n "$skipped" ]] && evidence_args+=(--skipped-gate "$skipped")
      done <<< "$skipped_gates"
      if python3 scripts/emit-ci-evidence.py "${evidence_args[@]}" >/dev/null; then
        printf 'ci_evidence_path=%s run_id=%s status=%s\n' "$evidence_path" "$run_id" "$evidence_status"
      else
        printf 'ci_evidence_status=failed reason=evidence_write_failed\n' >&2
        [[ "$exit_status" -eq 0 ]] && exit_status=1
      fi
    fi
    if [[ "$exit_status" -eq 0 && "$pipeline_result" == "pass" ]]; then
      [[ "$requested_mode" == "full" ]] && next_gate="release_ready"
      printf '\nci_local_result=pass mode=%s requested_mode=%s duration_seconds=%s next_gate=%s\n' \
        "$effective_mode" "$requested_mode" "$pipeline_duration" "$next_gate"
    else
      [[ "$requested_mode" == "full" ]] && next_gate="full_failed"
      printf '\nci_local_result=fail mode=%s requested_mode=%s duration_seconds=%s next_gate=%s\n' \
        "$effective_mode" "$requested_mode" "$pipeline_duration" "$next_gate" >&2
    fi
    exit "$exit_status"
  }
  trap finish_ci EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  if [[ "$#" -ne 1 ]]; then
    usage
    return 2
  fi
  case "$1" in
    --fast)
      requested_mode="fast"
      effective_mode="fast"
      ;;
    --full)
      requested_mode="full"
      effective_mode="full"
      ;;
    --help|-h)
      requested_mode="help"
      effective_mode="help"
      usage
      pipeline_result="pass"
      return 0
      ;;
    *)
      usage
      return 2
      ;;
  esac

  cd "$repo_root" || return 1
  observed_sha_start="$(git rev-parse HEAD)"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  run_id="ci-${requested_mode}-${observed_sha_start:0:12}-$$"
  if [[ -z "$candidate_id" && -n "${GRAF_CI_CANDIDATE_FILE:-}" && -f "$GRAF_CI_CANDIDATE_FILE" ]]; then
    candidate_id="$(python3 - "$GRAF_CI_CANDIDATE_FILE" <<'PY'
import json
import sys
try:
    value = json.loads(open(sys.argv[1], encoding="utf-8").read()).get("candidate_id", "")
except (OSError, UnicodeError, json.JSONDecodeError):
    value = ""
print(value if isinstance(value, str) else "")
PY
)"
  fi
  if [[ -n "$requested_sha" && "$requested_sha" != "$observed_sha_start" ]]; then
    printf 'ci_evidence_status=stale requested_sha=%s observed_sha_start=%s reason=target_changed\n' "$requested_sha" "$observed_sha_start" >&2
    pipeline_result="fail"
    evidence_status_override="stale"
    evidence_reason_override="target_changed"
    return 2
  fi
  performance_proof="$(calendar_performance_test_path)" || return 1

  if ! changed_list="$(changed_files)"; then
    if [[ "$requested_mode" == "full" ]]; then
      performance_required=1
    else
      has_unknown=1
      coverage="partial"
      selection_reason="diff_unavailable"
      printf 'ci_fast_coverage reason=%s\n' "$selection_reason"
    fi
  elif [[ -n "$changed_list" ]]; then
    while IFS= read -r path; do
      [[ -z "$path" ]] && continue
      [[ "$path" == tests/governance/* ]] && has_governance_tests=1
      if performance_path "$path"; then
        performance_required=1
        if [[ "$requested_mode" == "fast" ]]; then
          has_server=1
          selection_reason="performance_path_requires_focused_proof"
          printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
        fi
      fi
      if [[ "$requested_mode" == "full" ]]; then
        continue
      fi
      classification="$(classify_path "$path")"
      case "$classification" in
        server)
          has_server=1
          if ! bounded_server_path "$path"; then
            coverage="partial"
            selection_reason="high_risk_or_shared_path"
            printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
          fi
          case "$path" in
            apps/server/tests/contract/*.py|apps/server/tests/integration/*.py)
              if [[ -f "$repo_root/$path" ]]; then
                changed_server_tests="${changed_server_tests}${changed_server_tests:+$'\n'}${path}"
                [[ "$path" == "apps/server/tests/integration/test_calendar_auto_context_match.py" ]] \
                  && performance_covered_by_changed_tests=1
              else
                needs_server_unit=1
                selection_reason="removed_server_test_path"
                printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
              fi
              ;;
            *) needs_server_unit=1 ;;
          esac
          ;;
        macos)
          has_macos=1
          coverage="partial"
          selection_reason="high_risk_or_shared_path"
          printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
          ;;
        infra)
          has_infra=1
          coverage="partial"
          selection_reason="high_risk_or_shared_path"
          printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
          ;;
        governance)
          has_docs=1
          coverage="partial"
          selection_reason="high_risk_or_shared_path"
          printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
          ;;
        docs) has_docs=1 ;;
        unknown)
          has_unknown=1
          coverage="partial"
          selection_reason="unknown_path"
          printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$path"
          ;;
      esac
    done <<<"$changed_list"
  else
    if [[ "$requested_mode" == "fast" ]]; then
      has_docs=1
      selection_reason="no_changes"
    else
      performance_required=1
      selection_reason="synchronized_full_requires_performance"
    fi
  fi

  case "${GRAF_PERFORMANCE_GATE:-auto}" in
    auto) ;;
    required)
      performance_required=1
      if [[ "$requested_mode" == "fast" ]]; then
        has_server=1
        selection_reason="explicit_performance_requires_focused_proof"
        printf 'ci_fast_coverage reason=%s\n' "$selection_reason"
      fi
      ;;
    report) ;;
    *)
      echo "GRAF_PERFORMANCE_GATE must be auto, report or required." >&2
      return 2
      ;;
  esac

  if [[ "$requested_mode" == "fast" && "$performance_required" -eq 1 && \
        "$performance_covered_by_changed_tests" -eq 0 && \
        ! -f "$repo_root/apps/server/$performance_proof" ]]; then
    coverage="partial"
    selection_reason="performance_proof_unavailable"
    printf 'ci_fast_coverage reason=%s path=%s\n' "$selection_reason" "$performance_proof"
  fi

  if [[ "$requested_mode" == "full" ]]; then
    effective_mode="full"
    components="full"
    next_gate="full_in_progress"
  else
    effective_mode="fast"
    [[ "$coverage" == "complete" ]] && coverage="bounded"
    next_gate="full_before_release"
    if [[ -z "$changed_list" && "$selection_reason" != "diff_unavailable" ]]; then
      has_docs=1
    fi
    [[ "$selection_reason" == "explicit_full" ]] && selection_reason="component_diff"
    [[ "$has_server" -eq 1 ]] && components="server"
    if [[ "$has_macos" -eq 1 ]]; then
      [[ "$components" == "none" ]] && components="macos" || components="$components,macos"
    fi
    if [[ "$has_infra" -eq 1 ]]; then
      [[ "$components" == "none" ]] && components="infra" || components="$components,infra"
    fi
    if [[ "$has_docs" -eq 1 ]]; then
      [[ "$components" == "none" ]] && components="docs" || components="$components,docs"
    fi
    if [[ "$has_unknown" -eq 1 ]]; then
      [[ "$components" == "none" ]] && components="unknown" || components="$components,unknown"
    fi
  fi

  [[ "$performance_required" -eq 1 ]] && performance_gate="required"

  printf 'ci_lane requested=%s effective=%s components=%s reason=%s performance_gate=%s coverage=%s next_gate=%s\n' \
    "$requested_mode" "$effective_mode" "$components" "$selection_reason" "$performance_gate" \
    "$coverage" "$next_gate"

  process_preflight=(python3 scripts/check-development-process.py)
  if [[ -n "${GRAF_PR_BODY_FILE:-}" ]]; then
    process_preflight+=(--pr-body "$GRAF_PR_BODY_FILE")
  fi
  if [[ -f "$repo_root/.specify/feature.json" ]]; then
    run_step "Development process preflight" "${process_preflight[@]}" || return $?
  else
    # Feature context is per-worktree and intentionally absent from clean
    # merged/release checkouts. The repository-wide Spec Kit gate still runs;
    # do not invent an active feature just to execute a release lane.
    printf '\n==> Development process preflight skipped (release checkout without active feature pointer)\n'
  fi
  run_step "Spec Kit governance" python3 scripts/check_spec_kit_governance.py || return $?

  if [[ "$effective_mode" == "full" || "$has_governance_tests" -eq 1 ]]; then
    run_step "governance tests" python3 -m pytest -q tests/governance || return $?
  fi

  if [[ "$effective_mode" == "full" ]]; then
    run_step "macOS legacy audio architecture guard" sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh || return $?
    if [[ "$(uname -s)" == "Darwin" ]]; then
      run_step "macOS Swift build" swift build --package-path apps/macos || return $?
      run_step "macOS Swift tests" swift test --package-path apps/macos || return $?
      run_step "macOS contract validation" swift run --package-path apps/macos ContractValidation || return $?
    else
      printf '\n==> macOS Swift validation skipped (requires Darwin)\n'
      skipped_gates="${skipped_gates}${skipped_gates:+$'\n'}macOS Swift validation (requires Darwin)"
    fi
    run_step "server tests" run_server_tests full "$performance_gate" || return $?
    run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ." || return $?
    run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts || return $?
    run_step "rls hardening validation boundary" bash -c "cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py" || return $?
    run_step "production compose config" bash -c 'docker compose -f infra/docker-compose.yml config >/dev/null' || return $?
    run_step "deployment evidence scan" infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec || return $?
    run_step "active CI documentation consistency" check_active_docs || return $?
  else
    if [[ "$has_macos" -eq 1 ]]; then
      run_step "macOS legacy audio architecture guard" sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh || return $?
      if [[ "$(uname -s)" == "Darwin" ]]; then
        run_step "macOS Swift build" swift build --package-path apps/macos || return $?
        run_step "macOS Swift tests" swift test --package-path apps/macos || return $?
        run_step "macOS contract validation" swift run --package-path apps/macos ContractValidation || return $?
      else
        printf '\n==> macOS Swift validation skipped (requires Darwin)\n'
        skipped_gates="${skipped_gates}${skipped_gates:+$'\n'}macOS Swift validation (requires Darwin)"
      fi
    fi
    if [[ "$has_server" -eq 1 ]]; then
      if [[ "$needs_server_unit" -eq 1 ]]; then
        run_step "server tests" run_server_tests fast report || return $?
      fi
      if [[ -n "$changed_server_tests" ]]; then
        run_step "changed server tests" run_changed_server_tests "$performance_gate" \
          "$changed_server_tests" || return $?
      fi
      if [[ "$performance_required" -eq 1 && "$performance_covered_by_changed_tests" -eq 0 && \
            -f "$repo_root/apps/server/$performance_proof" ]]; then
        run_step "calendar performance proof" run_server_tests focused required \
          "$performance_proof" -m serial_performance || return $?
      fi
      run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ." || return $?
      run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts || return $?
    fi
    if [[ "$has_infra" -eq 1 ]]; then
      run_step "shell syntax" check_shell_syntax "$changed_list" || return $?
      run_step "CI contracts" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
        tests/contract/test_ci_cd_contract.py \
        tests/contract/test_local_postgres_test_runner.py" || return $?
      run_step "production compose config" bash -c \
        'docker compose -f infra/docker-compose.yml config >/dev/null' || return $?
      run_step "deployment evidence scan" \
        infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec || return $?
    fi
    run_step "diff whitespace check" check_diff_whitespace "$changed_list" || return $?
    run_step "active CI documentation consistency" check_active_docs || return $?
  fi

  pipeline_result="pass"
  return 0
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
