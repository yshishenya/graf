#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
LOCAL_COMPOSE="$ROOT_DIR/infra/docker-compose.local.yml"
LOCAL_API="${GRAF_LOCAL_ORIGIN:-http://127.0.0.1:8081}"

case "$LOCAL_API" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) printf 'ERROR: GRAF_LOCAL_ORIGIN must be loopback HTTP\n' >&2; exit 1 ;;
esac

usage() {
  cat <<'EOF'
Usage: ./scripts/graf-mac.sh <command>

Commands:
  status     Show branch, local API, Docker and macOS tool status.
  health     Require the local API and MinIO health endpoints to be ready.
  preflight  Check tools, Compose configuration, diff whitespace and health.
  start      Start the existing local API in the current terminal.
  app        Build and open the local macOS app after the API is ready.
  ci         Run the repository fast CI lane.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

http_code() {
  code=$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 1 --max-time 3 "$1" 2>/dev/null || true)
  printf '%s\n' "${code:-000}"
}

endpoint_status() {
  label=$1
  url=$2
  code=$(http_code "$url")
  case "$code" in
    200) printf '  %-18s PASS (%s)\n' "$label" "$code"; return 0 ;;
    *)   printf '  %-18s DOWN (%s)\n' "$label" "$code"; return 1 ;;
  esac
}

health() {
  require_command curl
  printf 'GRAF local health (%s)\n' "$LOCAL_API"
  live_ok=0
  ready_ok=0
  minio_ok=0
  endpoint_status 'API live' "$LOCAL_API/api/v1/health/live" || live_ok=1
  endpoint_status 'API ready' "$LOCAL_API/api/v1/health/ready" || ready_ok=1
  endpoint_status 'MinIO live' 'http://127.0.0.1:9010/minio/health/live' || minio_ok=1
  [ "$live_ok" -eq 0 ] && [ "$ready_ok" -eq 0 ] && [ "$minio_ok" -eq 0 ] ||
    fail 'local services are not ready; run ./scripts/graf-mac.sh start'
}

git_status() {
  branch=$(git -C "$ROOT_DIR" branch --show-current)
  sha=$(git -C "$ROOT_DIR" rev-parse --short HEAD)
  changes=$(git -C "$ROOT_DIR" status --short)
  printf '  branch             %s\n' "${branch:-detached}"
  printf '  commit             %s\n' "$sha"
  if [ -n "$changes" ]; then
    printf '  worktree           DIRTY\n'
  else
    printf '  worktree           clean\n'
  fi
}

status() {
  printf 'GRAF Mac Command Center\n'
  printf 'Repository           %s\n' "$ROOT_DIR"
  printf 'Git\n'
  git_status
  printf 'Local services\n'
  endpoint_status 'API live' "$LOCAL_API/api/v1/health/live" || true
  endpoint_status 'API ready' "$LOCAL_API/api/v1/health/ready" || true
  endpoint_status 'MinIO live' 'http://127.0.0.1:9010/minio/health/live' || true
  printf 'Docker\n'
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker compose -f "$LOCAL_COMPOSE" ps --format '  {{.Service}}  {{.Status}}' 2>/dev/null ||
      printf '  compose           unavailable\n'
  else
    printf '  daemon            unavailable\n'
  fi
  printf 'macOS\n'
  printf '  system             %s %s\n' "$(sw_vers -productVersion 2>/dev/null || printf unknown)" "$(uname -m)"
  for command in git curl docker swift uv; do
    if command -v "$command" >/dev/null 2>&1; then
      printf '  %-18s available\n' "$command"
    else
      printf '  %-18s missing\n' "$command"
    fi
  done
}

preflight() {
  [ "$(uname -s)" = 'Darwin' ] || fail 'this command center is for macOS'
  for command in git curl docker swift uv xcode-select; do
    require_command "$command"
  done
  docker info >/dev/null 2>&1 || fail 'Docker daemon is not available'
  docker compose -f "$LOCAL_COMPOSE" config --quiet
  git -C "$ROOT_DIR" diff --check
  health
  printf 'Preflight: PASS\n'
}

start() {
  require_command docker
  require_command uv
  if endpoint_status 'API ready' "$LOCAL_API/api/v1/health/ready" >/dev/null 2>&1; then
    printf 'Local API is already ready at %s\n' "$LOCAL_API"
    exit 0
  fi
  exec "$ROOT_DIR/infra/scripts/start-local.sh"
}

app() {
  health
  require_command swift
  exec "$ROOT_DIR/apps/macos/Scripts/build-local-app.sh" --open
}

ci() {
  exec "$ROOT_DIR/infra/scripts/ci-local.sh" --fast
}

command_name=${1:-status}
case "$command_name" in
  help|-h|--help) usage ;;
  status) status ;;
  health) health ;;
  preflight) preflight ;;
  start) start ;;
  app) app ;;
  ci) ci ;;
  *) usage >&2; fail "unknown command: $command_name" ;;
esac
