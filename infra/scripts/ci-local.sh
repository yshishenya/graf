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
    infra/docker-compose.yml|infra/server/*|infra/scripts/*.sh|infra/scripts/*.py|\
    scripts/*|.specify/*|.github/workflows/*|.github/actions/*|\
    Dockerfile*|docker-compose*|Makefile|pyproject.toml)
      echo infra
      ;;
    AGENTS.md|.github/pull_request_template.md|CHANGELOG.md|README.md|\
    CONTRIBUTING.md|infra/scripts/README.md|docs/*|specs/*)
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
  [[ "${#shell_files[@]}" -eq 0 ]] || bash -n "${shell_files[@]}"
}

check_diff_whitespace() {
  local merge_base
  if merge_base="$(merge_base_commit)"; then
    git -C "$repo_root" diff --check "$merge_base" --
  else
    git -C "$repo_root" diff --check
  fi
}

main() (
  set -uo pipefail
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
  local coverage="complete"
  local next_gate="release_ready"
  local performance_required=0
  local performance_covered_by_changed_tests=0
  local performance_gate="report"
  local path
  local classification
  pipeline_started="$(date +%s)"

  finish_ci() {
    local exit_status=$?
    trap - EXIT INT TERM
    pipeline_completed="$(date +%s)"
    pipeline_duration=$((pipeline_completed - pipeline_started))
    if [[ "$exit_status" -eq 0 && "$pipeline_result" == "pass" ]]; then
      printf '\nci_local_result=pass mode=%s requested_mode=%s duration_seconds=%s\n' \
        "$effective_mode" "$requested_mode" "$pipeline_duration"
    else
      printf '\nci_local_result=fail mode=%s requested_mode=%s duration_seconds=%s\n' \
        "$effective_mode" "$requested_mode" "$pipeline_duration" >&2
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
      ;;
    --full)
      requested_mode="full"
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

  if [[ "$requested_mode" == "full" ]]; then
    effective_mode="full"
    components="full"
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

  run_step "Spec Kit governance" python3 scripts/check_spec_kit_governance.py || return $?

  if [[ "$effective_mode" == "full" ]]; then
    run_step "macOS legacy audio architecture guard" sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh || return $?
    if [[ "$(uname -s)" == "Darwin" ]]; then
      run_step "macOS Swift build" swift build --package-path apps/macos || return $?
      run_step "macOS Swift tests" swift test --package-path apps/macos || return $?
      run_step "macOS contract validation" swift run --package-path apps/macos ContractValidation || return $?
    else
      printf '\n==> macOS Swift validation skipped (requires Darwin)\n'
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
      if [[ "$performance_required" -eq 1 && "$performance_covered_by_changed_tests" -eq 0 ]]; then
        run_step "calendar performance proof" run_server_tests focused required \
          tests/integration/test_calendar_auto_context_match.py -m serial_performance || return $?
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
    fi
    run_step "diff whitespace check" check_diff_whitespace || return $?
    run_step "active CI documentation consistency" check_active_docs || return $?
  fi

  pipeline_result="pass"
  return 0
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
