#!/bin/sh
set -eu
exec sh "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/run-local-app.sh" "$@"
