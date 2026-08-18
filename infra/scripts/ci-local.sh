#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

mode="full"
if [[ "$#" -gt 1 ]]; then
  echo "usage: $0 [--fast|--full]" >&2
  exit 2
fi
if [[ "${1:-}" == "--fast" ]]; then
  mode="fast"
elif [[ "${1:-}" != "" && "${1:-}" != "--full" ]]; then
  echo "usage: $0 [--fast|--full]" >&2
  exit 2
fi

run_step() {
  local name="$1"
  shift
  printf '\n==> %s\n' "$name"
  "$@"
}

run_step "macOS legacy audio architecture guard" sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh

if [[ "$mode" == "full" && "$(uname -s)" == "Darwin" ]]; then
  run_step "macOS Swift build" swift build --package-path apps/macos
  run_step "macOS Swift tests" swift test --package-path apps/macos
  run_step "macOS contract validation" swift run --package-path apps/macos ContractValidation
elif [[ "$mode" == "fast" ]]; then
  printf '\n==> macOS Swift validation skipped in fast lane\n'
else
  printf '\n==> macOS Swift validation skipped (requires Darwin)\n'
fi

# The expanded 097 collection is stable on the current 8 GB Docker allocation
# with four isolated workers. Keep an explicit override for larger runners.
run_step "server tests" env GRAF_TEST_WORKERS="${GRAF_TEST_WORKERS:-4}" \
  bash apps/server/scripts/run_local_postgres_tests.sh "--${mode}" -q
run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ."
run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
if [[ "$mode" == "full" ]]; then
  run_step "rls hardening validation boundary" bash -c "cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py"
  run_step "production compose config" docker compose -f infra/docker-compose.yml config
  run_step "deployment evidence scan" infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec
fi

printf '\nci_local_result=pass mode=%s\n' "$mode"
