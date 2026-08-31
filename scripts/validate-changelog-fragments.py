#!/usr/bin/env python3
"""Small dependency-free validator for owned changelog fragments."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED = ("schema_version", "feature_id", "category", "summary", "issue", "tasks", "compatibility", "release_notes")
CATEGORIES = {"Added", "Changed", "Fixed", "Security", "Docs", "Ops"}
FORBIDDEN = ("/Users/", "/home/", "BEGIN PRIVATE KEY", "sk-", "signed-url", "raw audio", "transcript text")


def _field(text: str, name: str) -> re.Match[str] | None:
    """Return only an unindented, top-level YAML field occurrence."""
    return re.search(rf"^{re.escape(name)}[ \t]*:[ \t]*(.*)$", text, re.MULTILINE)


def validate(root: Path) -> list[str]:
    directory = root / "changes" / "unreleased"
    if not directory.is_dir():
        return []
    errors: list[str] = []
    seen: set[int] = set()
    for path in sorted(directory.glob("F*.yaml")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing = [
            key
            for key in REQUIRED
            if (match := _field(text, key)) is None or not match.group(1).strip()
        ]
        if missing:
            errors.append(f"{path}: missing {', '.join(missing)}")
        match = re.search(r"^feature_id[ \t]*:[ \t]*(\d+)[ \t]*$", text, re.MULTILINE)
        if match:
            feature_id = int(match.group(1))
            if feature_id in seen:
                errors.append(f"{path}: duplicate feature_id {feature_id}")
            seen.add(feature_id)
            if path.name != f"F{feature_id}.yaml":
                errors.append(f"{path}: filename must be F{feature_id}.yaml")
        else:
            feature_id = None
            if _field(text, "feature_id") is not None:
                errors.append(f"{path}: feature_id must be numeric")
        category = re.search(r"^category[ \t]*:[ \t]*([^\s]+)[ \t]*$", text, re.MULTILINE)
        if category and category.group(1) not in CATEGORIES:
            errors.append(f"{path}: invalid category")
        schema = re.search(r"^schema_version[ \t]*:[ \t]*([^\s]+)[ \t]*$", text, re.MULTILINE)
        if schema and schema.group(1) != "1":
            errors.append(f"{path}: schema_version must be 1")
        summary = re.search(r"^summary[ \t]*:[ \t]*(.+)$", text, re.MULTILINE)
        if not summary or not summary.group(1).strip() or not re.search(r"[А-Яа-яЁё]", summary.group(1)):
            errors.append(f"{path}: summary must be a non-empty Russian entry")
        if not re.search(r"^issue[ \t]*:[ \t]*#?\d+[ \t]*$", text, re.MULTILINE):
            errors.append(f"{path}: issue must contain a GitHub number")
        if not re.search(r"^tasks[ \t]*:[ \t]*.+T\d{3,}", text, re.MULTILINE):
            errors.append(f"{path}: tasks must contain a Spec Kit task ID")
        if any(token.lower() in text.lower() for token in FORBIDDEN):
            errors.append(f"{path}: forbidden secret/private/path token")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"changelog-fragments: ERROR: {error}", file=sys.stderr)
        return 1
    print("changelog-fragments: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
