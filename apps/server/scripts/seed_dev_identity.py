#!/usr/bin/env python3
import argparse
import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

DEFAULT_ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = UUID("30000000-0000-0000-0000-000000000001")
DEFAULT_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000001")


async def seed_identity(settings: Settings) -> dict[str, str]:
    engine = create_async_engine(settings.database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as db:
        for model, key, values in [
            (Organization, DEFAULT_ORG_ID, {"slug": "local-org", "name": "Local Org"}),
            (Workspace, DEFAULT_WORKSPACE_ID, {"organization_id": DEFAULT_ORG_ID, "slug": "local-workspace", "name": "Local Workspace"}),
            (UserIdentity, DEFAULT_USER_ID, {"organization_id": DEFAULT_ORG_ID, "external_subject": str(DEFAULT_USER_ID), "display_name": "Local User"}),
            (RegisteredDevice, DEFAULT_DEVICE_ID, {"workspace_id": DEFAULT_WORKSPACE_ID, "user_id": DEFAULT_USER_ID, "device_public_id": "local-macos-device", "status": "active"}),
        ]:
            existing = await db.get(model, key)
            if existing is None:
                db.add(model(id=key, **values))
        membership = await db.get(
            WorkspaceMembership,
            {"workspace_id": DEFAULT_WORKSPACE_ID, "user_id": DEFAULT_USER_ID},
        )
        if membership is None:
            db.add(
                WorkspaceMembership(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    user_id=DEFAULT_USER_ID,
                    role="owner",
                    status="active",
                )
            )
        await db.commit()
    await engine.dispose()
    return {
        "organization_id": str(DEFAULT_ORG_ID),
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "user_id": str(DEFAULT_USER_ID),
        "device_id": str(DEFAULT_DEVICE_ID),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic local 2brain Rec identity/device records.")
    parser.add_argument("--print-headers", action="store_true")
    args = parser.parse_args()
    ids = asyncio.run(seed_identity(Settings()))
    if args.print_headers:
        print(f"X-Organization-Id: {ids['organization_id']}")
        print(f"X-Workspace-Id: {ids['workspace_id']}")
        print(f"X-User-Id: {ids['user_id']}")
        print(f"X-Device-Id: {ids['device_id']}")
    else:
        print(ids)


if __name__ == "__main__":
    main()
