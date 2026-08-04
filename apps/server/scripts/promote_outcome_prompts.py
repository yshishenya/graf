#!/usr/bin/env python3
"""Promote or rollback the exact Feature 139 outcome prompt set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from twobrain_rec_server.cli.langfuse_prompts import desired_prompts
from twobrain_rec_server.outcomes.prompt_optimization import move_production_label
from twobrain_rec_server.outcomes.prompts import validate_prompt_snapshot


def _client(*, base_url: str, public_key_file: Path, secret_key_file: Path):
    from langfuse import Langfuse

    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != "cloud.langfuse.com" or parsed.path not in ("", "/"):
        raise ValueError("base URL must be https://cloud.langfuse.com")
    return Langfuse(
        base_url=base_url.rstrip("/"),
        public_key=public_key_file.read_text(encoding="utf-8").strip(),
        secret_key=secret_key_file.read_text(encoding="utf-8").strip(),
        environment="production",
        tracing_enabled=False,
    )


def _transition(item: dict[str, object], mode: str) -> tuple[int, int, str]:
    production_version = int(item["production_version"])
    target_version = int(item["target_version"])
    rollback_version = int(item["rollback_version"])
    if mode == "promote":
        return production_version, target_version, str(item["target_hash"])
    if mode == "rollback":
        return target_version, rollback_version, str(item["rollback_hash"])
    return rollback_version, target_version, str(item["target_hash"])


def run(args: argparse.Namespace) -> list[dict[str, object]]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = manifest.get("prompts")
    allowed_names = {
        name for name in desired_prompts() if name.startswith("graf/meeting-outcome/")
    }
    if manifest.get("feature") != "139-meeting-outcome-value":
        raise ValueError("prompt manifest feature mismatch")
    if not isinstance(items, list) or len(items) != len(allowed_names):
        raise ValueError("prompt manifest must contain the complete outcome prompt set")
    names = [item.get("name") for item in items if isinstance(item, dict)]
    if (
        len(names) != len(items)
        or not all(isinstance(name, str) for name in names)
        or len(set(names)) != len(names)
        or set(names) != allowed_names
    ):
        raise ValueError("prompt manifest names must exactly match the outcome prompt set")
    client = _client(
        base_url=args.base_url,
        public_key_file=args.public_key_file,
        secret_key_file=args.secret_key_file,
    )
    prepared: list[tuple[dict[str, object], int, int, str]] = []
    try:
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("prompt manifest item must be an object")
            name = str(item["name"])
            if name not in allowed_names:
                raise ValueError(f"{name}: prompt is not an allowlisted outcome prompt")
            source_version, target_version, expected_hash = _transition(item, args.mode)
            target = client.get_prompt(
                name,
                version=target_version,
                type="chat",
                cache_ttl_seconds=0,
                max_retries=0,
                fetch_timeout_seconds=10,
            )
            target_snapshot = validate_prompt_snapshot(
                name=name,
                version=int(target.version),
                prompt_type="chat",
                prompt=target.prompt,
                config=target.config or {},
            )
            if target_snapshot.canonical_hash != expected_hash:
                raise ValueError(f"{name}: target hash mismatch")
            prepared.append((item, source_version, target_version, expected_hash))

        results: list[dict[str, object]] = []
        for item, source_version, target_version, expected_hash in prepared:
            name = str(item["name"])
            promoted = move_production_label(
                client,
                prompt_name=name,
                prompt_type="chat",
                expected_source_version=source_version,
                target_version=target_version,
                protected_label_capability_verified=args.protected_label_capability_verified,
            )
            if promoted.canonical_hash != expected_hash:
                raise ValueError(f"{name}: production readback hash mismatch")
            results.append(
                {
                    "name": name,
                    "from_version": source_version,
                    "to_version": promoted.version,
                    "canonical_hash": promoted.canonical_hash,
                }
            )
        return results
    finally:
        client.flush()
        client.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote or rollback exact outcome prompts")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("promote", "rollback", "restore"), required=True)
    parser.add_argument("--base-url", default="https://cloud.langfuse.com")
    parser.add_argument("--public-key-file", type=Path, required=True)
    parser.add_argument("--secret-key-file", type=Path, required=True)
    parser.add_argument("--protected-label-capability-verified", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"mode": args.mode, "promotions": run(args)}, sort_keys=True))


if __name__ == "__main__":
    main()
