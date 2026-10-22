#!/usr/bin/env bash
set -euo pipefail
# T116: one metadata-only collector, reused by the existing guard.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/posthog-storage.py" "$@"
