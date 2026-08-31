#!/usr/bin/env python3
"""Ensure a feature declares a bounded legacy decision."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


CLASSIFICATION_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?classification(?:\*\*)?"
    r"[ \t]*:[ \t]*[`']?(remove|retain-with-exception|untouched)[`']?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
EXCEPTION_FIELDS = {
    "owner": re.compile(r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?owner(?:\*\*)?[ \t]*:", re.IGNORECASE | re.MULTILINE),
    "expiry": re.compile(r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?expiry(?:\*\*)?[ \t]*:", re.IGNORECASE | re.MULTILINE),
    "removal trigger": re.compile(r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?removal[ \t]+trigger(?:\*\*)?[ \t]*:", re.IGNORECASE | re.MULTILINE),
    "retirement task": re.compile(r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?retirement[ \t]+task(?:\*\*)?[ \t]*:", re.IGNORECASE | re.MULTILINE),
}


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []
    match = re.search(r"^## Legacy Impact\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match: return [f"{path}: missing ## Legacy Impact"]
    section = match.group(1)
    classifications = CLASSIFICATION_RE.findall(section)
    if len(classifications) != 1:
        errors.append(
            f"{path}: Legacy Impact needs exactly one Classification field with "
            "remove/retain-with-exception/untouched"
        )
    elif classifications[0].lower() == "retain-with-exception":
        for field, pattern in EXCEPTION_FIELDS.items():
            match = pattern.search(section)
            if not match:
                errors.append(f"{path}: compatibility exception needs {field}")
            else:
                value = section[match.end():].splitlines()
                if not value or not value[0].strip():
                    errors.append(f"{path}: compatibility exception {field} must not be empty")

        expiry_pattern = EXCEPTION_FIELDS["expiry"]
        expiry_match = expiry_pattern.search(section)
        if expiry_match:
            expiry_line = section[expiry_match.end():].splitlines()[0]
            date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", expiry_line)
            if not date_match:
                errors.append(f"{path}: compatibility exception needs an ISO expiry date")
            else:
                value = date_match.group(1)
                try:
                    expiry = date.fromisoformat(value)
                except ValueError:
                    errors.append(f"{path}: invalid ISO expiry date {value}")
                else:
                    if expiry < date.today():
                        errors.append(f"{path}: expired legacy exception {value}")
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
