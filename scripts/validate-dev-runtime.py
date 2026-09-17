#!/usr/bin/env python3
"""Validate repository-local safety invariants for the GRAF Dev runtime."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


FORBIDDEN_EVIDENCE = re.compile(r"(?i)(password|api[_-]?key|secret|signed[_ -]?url|raw[_ -]?audio|transcript)")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
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
