"""Small fail-closed helpers for metadata-only production smoke scripts."""

from __future__ import annotations

import ipaddress
import os
import re
import stat
from argparse import ArgumentParser
from pathlib import Path
from urllib.parse import urlsplit

PRODUCTION_ORIGIN = "https://rec.2brain.pro"
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def validate_run_id(value: str) -> str:
    """Return a run id that is safe for paths, shell args, and smoke identity keys."""
    if not isinstance(value, str) or _RUN_ID_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "run_id must start with an ASCII letter or digit and contain only "
            "ASCII letters, digits, '.', '_' or '-' (maximum 128 characters)"
        )
    return value


def validate_origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("api must be an approved origin without credentials or a path")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("api must be an approved http(s) origin")
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin == PRODUCTION_ORIGIN:
        return origin
    host = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "localhost"
    if is_loopback:
        return origin
    raise ValueError("api origin is not approved; use production or loopback")


def read_private_auth_material(path: Path, *, expected_run_id: str | None = None) -> str:
    if expected_run_id is not None:
        validate_run_id(expected_run_id)
        if path.name != expected_run_id and not path.name.endswith(f"-{expected_run_id}"):
            raise ValueError("auth material is not bound to the exact run_id")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ValueError("auth material must be a regular mode-0600 file")
        if metadata.st_size <= 0 or metadata.st_size > 4096:
            raise ValueError("auth material has an invalid size")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            value = handle.read().strip()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not value:
        raise ValueError("auth material is empty")
    return value


def main() -> None:
    parser = ArgumentParser(description="Validate a production smoke run id.")
    parser.add_argument("--validate-run-id", required=True)
    args = parser.parse_args()
    try:
        validate_run_id(args.validate_run_id)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
