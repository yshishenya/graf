#!/usr/bin/env python3
"""Ensure a feature declares a bounded legacy decision."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []
    match = re.search(r"^## Legacy Impact\s*$([\s\S]*)", text, re.MULTILINE)
    if not match: return [f"{path}: missing ## Legacy Impact"]
    section = match.group(1)
    classifications = [word for word in ("remove", "retain-with-exception", "untouched") if word in section]
    if not classifications:
        errors.append(f"{path}: Legacy Impact needs remove/retain-with-exception/untouched classification")
    elif "retain-with-exception" in classifications:
        lowered = section.lower()
        for field in ("owner", "expiry", "trigger", "retirement task"):
            if field not in lowered:
                errors.append(f"{path}: compatibility exception needs {field}")
        if not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", section):
            errors.append(f"{path}: compatibility exception needs an ISO expiry date")
    for line in section.splitlines():
        if "expiry" in line.lower() and re.search(r"\b20\d{2}-\d{2}-\d{2}\b", line):
            value = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", line).group(1)
            if date.fromisoformat(value) < date.today(): errors.append(f"{path}: expired legacy exception {value}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--feature", type=Path, required=True); args = parser.parse_args()
    errors = validate(args.feature.resolve())
    if errors:
        for error in errors: print(f"legacy-impact: ERROR: {error}", file=sys.stderr)
        return 1
    print("legacy-impact: OK")
    return 0


if __name__ == "__main__": raise SystemExit(main())
