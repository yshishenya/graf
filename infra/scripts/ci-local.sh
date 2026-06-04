#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

run_step() {
  local name="$1"
  shift
  printf '\n==> %s\n' "$name"
  "$@"
}

run_step "server tests" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q"
run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ."
run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
run_step "production compose config" docker compose -f infra/docker-compose.yml config
run_step "deployment evidence scan" infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec

printf '\nci_local_result=pass\n'
