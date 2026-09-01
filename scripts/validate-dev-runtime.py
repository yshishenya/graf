#!/usr/bin/env python3
"""Validate repository-local safety invariants for the GRAF Dev runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


SHA = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_EVIDENCE = re.compile(r"(?i)(password|api[_-]?key|secret|signed[_ -]?url|raw[_ -]?audio|transcript)")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    pointer = root / ".specify" / "feature.json"
    try:
        feature = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["active Feature pointer is unreadable"]
    if str(feature.get("feature_id")) != "229":
        errors.append("active feature is not Feature 229")
    owned = feature.get("owned_paths")
    if not isinstance(owned, list) or not all(isinstance(path, str) for path in owned):
        errors.append("active Feature owned_paths must be a list of strings")
    else:
        for required in ("infra/docker-compose.dev.yml", "scripts/dev-harness.py", "infra/scripts/start-dev-runtime.sh"):
            if required not in owned:
                errors.append(f"Feature 229 ownership misses {required}")
    compose = root / "infra" / "docker-compose.dev.yml"
    text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    if "name: graf-dev" not in text:
        errors.append("Dev Compose project is not explicitly graf-dev")
    if "TWOBRAIN_PROCESSING_ENABLED: \"true\"" not in text:
        errors.append("Dev processing is not explicitly enabled")
    if "env_file:" in text:
        errors.append("Dev Compose must not inherit env_file")
    for evidence_root in (root / ".dev" / "ci-evidence", root / "tests" / "governance" / "fixtures" / "feature_229"):
        if evidence_root.exists():
            for path in evidence_root.rglob("*"):
                if path.is_file() and FORBIDDEN_EVIDENCE.search(path.read_text(encoding="utf-8", errors="replace")):
                    # Fixture names may explain the forbidden class, but their
                    # contents must remain metadata-only and credential-free.
                    errors.append(f"forbidden evidence content in {path.relative_to(root)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: GRAF Dev runtime governance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
