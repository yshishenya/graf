#!/usr/bin/env python3
"""Issue a temporary Rec AuthSession for a production smoke upload run.

The script deliberately never prints the raw bearer token. In execute mode it
writes the token to a caller-provided file with 0600 permissions and prints only
non-secret identifiers needed by the smoke runner and cleanup scripts.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from scripts.seed_smoke_identity import seed_identity  # noqa: E402
from twobrain_rec_server.config import Settings  # noqa: E402
from twobrain_rec_server.deployment import build_smoke_identity_seed  # noqa: E402


def _load_auth_session_primitives() -> tuple[Any, Any]:
    try:
        from twobrain_rec_server.auth.sessions import issue_auth_session
    except ImportError as exc:  # pragma: no cover - execute-only production guard
        raise RuntimeError(
            "AuthSession smoke requires deployed provider-auth session support "
            "(twobrain_rec_server.auth.sessions.issue_auth_session)."
        ) from exc

    try:
        from twobrain_rec_server.db.models import AuthSessionDeviceBinding
    except ImportError:
        try:
            from twobrain_rec_server.db.models.federated_auth import (
                AuthSessionDeviceBinding,
            )
        except ImportError as exc:  # pragma: no cover - execute-only production guard
            raise RuntimeError(
                "AuthSession smoke requires deployed AuthSessionDeviceBinding model."
            ) from exc

    return issue_auth_session, AuthSessionDeviceBinding


def _safe_uuid(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return value


async def _invoke_issue_auth_session(
    issue_auth_session: Any,
    db: Any,
    *,
    run_id: str,
    ttl_seconds: int,
) -> Any:
    seed = build_smoke_identity_seed(run_id)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    base_kwargs: dict[str, Any] = {
        "db": db,
        "session": db,
        "db_session": db,
        "async_session": db,
        "user_id": _safe_uuid(seed.user_id),
        "identity_id": _safe_uuid(seed.user_id),
        "workspace_id": _safe_uuid(seed.workspace_id),
        "organization_id": _safe_uuid(seed.organization_id),
        "device_id": _safe_uuid(seed.device_id),
        "registered_device_id": _safe_uuid(seed.device_id),
        "provider": "internal_smoke",
        "provider_subject": str(seed.user_id),
        "subject": str(seed.user_id),
        "claims": {
            "purpose": "production_smoke",
            "run_id": run_id,
            "device_id": str(seed.device_id),
        },
        "claims_fingerprint": run_id,
        "ttl_seconds": ttl_seconds,
        "ttl": ttl_seconds,
        "expires_at": expires_at,
        "auth_method": "internal_smoke",
        "scopes": ["upload:write"],
    }

    try:
        signature = inspect.signature(issue_auth_session)
    except (TypeError, ValueError):
        result = issue_auth_session(db)
    else:
        kwargs: dict[str, Any] = {}
        positional_args: list[Any] = []
        missing_required: list[str] = []
        for name, parameter in signature.parameters.items():
            if parameter.kind in {
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            }:
                continue
            if name in base_kwargs:
                kwargs[name] = base_kwargs[name]
                continue
            if (
                parameter.default is inspect.Parameter.empty
                and parameter.kind
                in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                }
            ):
                missing_required.append(name)

        if missing_required:
            first_missing = missing_required[0]
            first_parameter = signature.parameters[first_missing]
            if first_parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
                positional_args.append(db)
                missing_required = missing_required[1:]

        if missing_required:
            raise RuntimeError(
                "Cannot issue smoke AuthSession; unsupported required arguments: "
                + ", ".join(missing_required)
            )

        result = issue_auth_session(*positional_args, **kwargs)

    if inspect.isawaitable(result):
        result = await result
    return result


def _field(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, dict) and name in source:
            return source[name]
        if hasattr(source, name):
            return getattr(source, name)
    if isinstance(source, tuple):
        for item in source:
            value = _field(item, *names)
            if value is not None:
                return value
    return None


def _extract_issued_session(issued: Any) -> tuple[Any, str, Any]:
    token = _field(issued, "token", "raw_token", "session_token", "bearer_token")
    auth_session_id = _field(issued, "id", "auth_session_id", "session_id")
    expires_at = _field(issued, "expires_at", "expires")

    if token is None and isinstance(issued, tuple):
        for item in issued:
            if isinstance(item, str):
                token = item
                break

    if auth_session_id is None and isinstance(issued, tuple):
        for item in issued:
            if not isinstance(item, str):
                auth_session_id = _field(item, "id", "auth_session_id", "session_id")
                expires_at = expires_at or _field(item, "expires_at", "expires")
                break

    if not token:
        raise RuntimeError("AuthSession issuer did not return a raw token.")
    if not auth_session_id:
        raise RuntimeError("AuthSession issuer did not return a session id.")
    return auth_session_id, str(token), expires_at


def _binding_kwargs(binding_model: Any, *, auth_session_id: Any, run_id: str) -> dict[str, Any]:
    seed = build_smoke_identity_seed(run_id)
    now = datetime.now(UTC)
    columns = set(binding_model.__table__.columns.keys())
    values: dict[str, Any] = {}

    candidates: dict[str, Any] = {
        "id": uuid.uuid4(),
        "auth_session_id": _safe_uuid(auth_session_id),
        "session_id": _safe_uuid(auth_session_id),
        "registered_device_id": _safe_uuid(seed.device_id),
        "device_id": _safe_uuid(seed.device_id),
        "user_id": _safe_uuid(seed.user_id),
        "workspace_id": _safe_uuid(seed.workspace_id),
        "organization_id": _safe_uuid(seed.organization_id),
        "device_state": "trusted",
        "trust_state": "trusted",
        "binding_state": "trusted",
        "status": "trusted",
        "created_at": now,
        "updated_at": now,
    }

    for column, value in candidates.items():
        if column in columns:
            values[column] = value

    if not any(name in values for name in ("auth_session_id", "session_id")):
        raise RuntimeError("AuthSessionDeviceBinding model has no session id column.")
    if not any(name in values for name in ("registered_device_id", "device_id")):
        raise RuntimeError("AuthSessionDeviceBinding model has no device id column.")

    return values


async def issue_smoke_auth_session(
    settings: Settings,
    *,
    run_id: str,
    token_file: Path,
    ttl_seconds: int,
    execute: bool,
) -> dict[str, Any]:
    identity_result = await seed_identity(settings, run_id, execute=execute)
    if not execute:
        return {
            **identity_result,
            "auth_session_result": "dry_run",
            "auth_session_id": None,
            "token_file": str(token_file),
            "token_written": False,
        }

    issue_auth_session, binding_model = _load_auth_session_primitives()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        issued = await _invoke_issue_auth_session(
            issue_auth_session,
            db,
            run_id=run_id,
            ttl_seconds=ttl_seconds,
        )
        auth_session_id, raw_token, expires_at = _extract_issued_session(issued)
        db.add(
            binding_model(
                **_binding_kwargs(
                    binding_model,
                    auth_session_id=auth_session_id,
                    run_id=run_id,
                )
            )
        )
        await db.commit()

    await engine.dispose()

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(raw_token, encoding="utf-8")
    os.chmod(token_file, 0o600)

    return {
        **identity_result,
        "auth_session_result": "pass",
        "auth_session_id": str(auth_session_id),
        "token_file": str(token_file),
        "token_written": True,
        "expires_at": expires_at.isoformat() if hasattr(expires_at, "isoformat") else expires_at,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Issue a temporary Rec AuthSession for production smoke upload."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--token-file",
        type=Path,
        default=Path("/tmp/twobrain-rec-smoke-auth-token"),
    )
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(
        issue_smoke_auth_session(
            Settings(),
            run_id=args.run_id,
            token_file=args.token_file,
            ttl_seconds=args.ttl_seconds,
            execute=args.execute,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
