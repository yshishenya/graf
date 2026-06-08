#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-docs/deployments/2brain-rec}"
TARGET_ABS="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"

(
  cd apps/server
  PYTHONPATH=src uv run python - "$TARGET_ABS" <<'PY'
from pathlib import Path
import sys

from twobrain_rec_server.deployment import scan_deployment_evidence_text

target = Path(sys.argv[1])
paths = [target] if target.is_file() else sorted(target.rglob("*.md"))
for path in paths:
    scan_deployment_evidence_text(path.read_text(encoding="utf-8"))
print(f"deployment_evidence_scan=pass files={len(paths)} target={target}")
PY
)
