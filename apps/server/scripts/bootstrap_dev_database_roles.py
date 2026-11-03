"""Use the canonical protected runtime roles in the disposable development stack."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from bootstrap_runtime_database_roles import _bootstrap

_PASSWORD_ROLES = ("OWNER", "APP", "MAINTENANCE", "MEDIA")


async def bootstrap_development_roles() -> None:
    if os.environ.get("TWOBRAIN_ENV") != "development":
        raise RuntimeError("development database bootstrap requires development environment")
    passwords = {}
    for role in _PASSWORD_ROLES:
        value = os.environ.get(f"TWOBRAIN_DB_{role}_PASSWORD", "")
        if not value:
            raise RuntimeError("development database password is missing")
        passwords[role] = value
    previous = {
        f"TWOBRAIN_DB_{role}_PASSWORD_FILE": os.environ.get(f"TWOBRAIN_DB_{role}_PASSWORD_FILE")
        for role in _PASSWORD_ROLES
    }
    try:
        with TemporaryDirectory(prefix="graf-dev-database-roles-") as directory:
            for role, value in passwords.items():
                path = Path(directory) / role.lower()
                path.touch(mode=0o600)
                path.write_text(value, encoding="utf-8")
                os.environ[f"TWOBRAIN_DB_{role}_PASSWORD_FILE"] = str(path)
            await _bootstrap()
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> None:
    try:
        asyncio.run(bootstrap_development_roles())
    except Exception:
        print("dev_runtime_database_roles_result=fail")
        raise SystemExit(1) from None
    print("dev_runtime_database_roles_result=pass")


if __name__ == "__main__":
    main()
