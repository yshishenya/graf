#!/usr/bin/env sh
set -eu

if [ "${TWOBRAIN_ENV:-}" = "production" ] \
  && [ "${TWOBRAIN_PRODUCTION_RELEASE_GATE:-}" != "1" ]; then
  echo "migration_result=blocked"
  echo "reason=production_migration_requires_release_gate"
  exit 1
fi

exec "$@"
