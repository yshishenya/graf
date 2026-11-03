#!/usr/bin/env python3
"""Ensure a feature declares a bounded legacy decision."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path


CLASSIFICATION_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?classification(?:\*\*)?"
    r"[ \t]*:[ \t]*[`']?(remove|retain-with-exception|untouched)[`']?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
EXCEPTION_FIELDS = ("owner", "expiry", "reason", "compatibility boundary",
                    "removal trigger", "risk", "validation", "retirement task")


def validate_exception(section: str) -> list[str]:
    """Check the same finite text contract for a spec and a trusted PR policy."""
    errors: list[str] = []
    values: dict[str, str] = {}
    for field in EXCEPTION_FIELDS:
        label = re.escape(field).replace(r"\ ", r"[ \t]+")
        matches = re.findall(
            rf"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?{label}(?:\*\*)?[ \t]*:[ \t]*([^\n]*)$",
            section, re.IGNORECASE | re.MULTILINE,
        )
        if len(matches) != 1:
            errors.append(f"compatibility exception needs {field} exactly once")
            continue
        value = matches[0].strip().strip("`'\"").strip()
        if not value:
            errors.append(f"compatibility exception {field} must not be empty")
        elif (re.search(r"<[^>]*>|_{2,}|\.{3}|\b(?:TODO|TBD|FIXME|TKTK)\b", value, re.IGNORECASE)
              or value.casefold() in {"n/a", "none", "null", "указать", "заполнить", "не указано", "-", "?"}):
            errors.append(f"compatibility exception {field} must not be a placeholder")
        else:
            values[field] = value

    if "expiry" in values:
        value = values["expiry"]
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError()
            expiry = date.fromisoformat(value)
        except ValueError:
            errors.append("invalid ISO expiry date")
        else:
            if expiry <= datetime.now(timezone.utc).date():
                errors.append("compatibility exception expiry must be in the future (UTC)")
    if "retirement task" in values:
        value = values["retirement task"]
        if any(len(re.findall(pattern, value)) != 1 for pattern in
               (r"\bF[0-9]{3,}\b", r"\bT[0-9]{3,}\b", r"(?<![\w#])#[1-9][0-9]*\b")):
            errors.append("compatibility exception retirement task needs one F###, T### and #issue")
    return errors


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []
    sections = re.findall(r"^## Legacy Impact[ \t]*\n([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not sections:
        return [f"{path}: missing ## Legacy Impact"]
    if len(sections) != 1:
        return [f"{path}: duplicate ## Legacy Impact"]
    section = sections[0]
    classifications = CLASSIFICATION_RE.findall(section)
    labels = re.findall(r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?classification(?:\*\*)?[ \t]*:",
                        section, re.IGNORECASE | re.MULTILINE)
    if len(classifications) != 1 or len(labels) != 1:
        errors.append(
            f"{path}: Legacy Impact needs exactly one Classification field with "
            "remove/retain-with-exception/untouched"
        )
    elif classifications[0].lower() == "retain-with-exception":
        errors.extend(f"{path}: {error}" for error in validate_exception(section))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.feature.resolve())
    if errors:
        for error in errors:
            print(f"legacy-impact: ERROR: {error}", file=sys.stderr)
        return 1
    print("legacy-impact: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
