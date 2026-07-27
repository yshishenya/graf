#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

lane="full"
for argument in "$@"; do
  case "$argument" in
    --fast|--full|--governance)
      lane="${argument#--}"
      ;;
    *)
      printf 'usage: %s [--fast|--full|--governance]\n' "$0" >&2
      exit 2
      ;;
  esac
done

run_step() {
  local name="$1"
  shift
  printf '\n==> %s\n' "$name"
  "$@"
}

printf 'ci_local_lane=%s\n' "$lane"
if [[ "$lane" == "fast" ]]; then
  run_step "server fast tests" bash -c \
    "cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q -m 'not requires_postgres and not governance and not strict_rls and not spike'"
elif [[ "$lane" == "governance" ]]; then
  run_step "server governance tests" bash apps/server/scripts/run_local_postgres_tests.sh --focused -m "governance and not spike"
else
  run_step "server full tests" bash apps/server/scripts/run_local_postgres_tests.sh --full
fi
run_step "server lint" bash -c "cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ."
run_step "python compile" python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
run_step "rls hardening validation boundary" python3 apps/server/scripts/verify_rls_hardening.py
run_step "production compose config" docker compose -f infra/docker-compose.yml config
run_step "deployment evidence scan" infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec

printf '\nci_local_result=pass\n'
