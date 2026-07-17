#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

run_step() {
  local name="$1"
  shift
  printf '\n==> %s\n' "$name"
  "$@"
}

run_step "macOS legacy audio architecture guard" sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh

if [[ "$(uname -s)" == "Darwin" ]]; then
  run_step "macOS Swift build" swift build --package-path apps/macos
  run_step "macOS Swift tests" swift test --package-path apps/macos
  run_step "macOS contract validation" swift run --package-path apps/macos ContractValidation
else
  printf '\n==> macOS Swift validation skipped (requires Darwin)\n'
fi

run_step "server tests" bash apps/server/scripts/run_local_postgres_tests.sh -q
run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ."
run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
run_step "rls hardening validation boundary" python3 apps/server/scripts/verify_rls_hardening.py
run_step "production compose config" docker compose -f infra/docker-compose.yml config
run_step "deployment evidence scan" infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec

printf '\nci_local_result=pass\n'
