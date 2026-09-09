#!/usr/bin/env python3
"""Build a byte-reproducible Spec Kit extension release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "github-issue-canon"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
DIST_PATHS = (
    Path("LICENSE"),
    Path("README.md"),
    Path("extension.yml"),
    Path("commands"),
    Path("scripts/ensure_issue_canon.py"),
    Path("scripts/issue_canon_common.py"),
    Path("scripts/normalize_issue_canon.py"),
    Path("scripts/validate_issue_canon.py"),
    Path("templates"),
)


def extension_version() -> str:
    manifest = (ROOT / "extension.yml").read_text(encoding="utf-8")
    match = re.search(r'^  version: "(?P<version>\d+\.\d+\.\d+)"$', manifest, re.MULTILINE)
    if not match:
        raise SystemExit("build_release: could not read extension.version")
    return match.group("version")


def distribution_files() -> list[Path]:
    files: list[Path] = []
    for relative in DIST_PATHS:
        path = ROOT / relative
        if not path.exists():
            raise SystemExit(f"build_release: missing distribution path: {relative}")
        if path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and "__pycache__" not in candidate.parts
            )
        else:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def zip_info(relative: Path, executable: bool) -> ZipInfo:
    info = ZipInfo(f"{ARCHIVE_ROOT}/{relative.as_posix()}", date_time=FIXED_TIMESTAMP)
    info.create_system = 3
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = ZIP_STORED
    return info


def build(output_dir: Path) -> dict[str, str]:
    version = extension_version()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"github-issue-canon-{version}.zip"
    checksum = archive.with_suffix(".zip.sha256")

    with ZipFile(archive, "w") as target:
        for source in distribution_files():
            relative = source.relative_to(ROOT)
            executable = bool(source.stat().st_mode & 0o111)
            target.writestr(
                zip_info(relative, executable),
                source.read_bytes(),
                compress_type=ZIP_STORED,
            )

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {
        "version": version,
        "archive": str(archive),
        "checksum": str(checksum),
        "sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(args.output.resolve())
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"build_release: {result['archive']}")
        print(f"build_release: sha256 {result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
