#!/usr/bin/env python3
import argparse
import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.deployment import build_smoke_identity_seed


async def seed_identity(settings: Settings, run_id: str, *, execute: bool) -> dict[str, str]:
    seed = build_smoke_identity_seed(run_id)
    if not execute:
        return seed.headers() | {
            "identity_class": seed.identity_class,
            "device_class": seed.device_class,
            "seed_result": "dry_run",
        }

    engine = create_async_engine(settings.database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    slug_suffix = run_id.lower().replace("_", "-")[:80]
    async with sessionmaker() as db:
        for model, key, values in [
            (Organization, seed.organization_id, {"slug": f"internal-smoke-org-{slug_suffix}", "name": "Internal Smoke Org"}),
            (
                Workspace,
                seed.workspace_id,
                {"organization_id": seed.organization_id, "slug": f"internal-smoke-workspace-{slug_suffix}", "name": "Internal Smoke Workspace"},
            ),
            (
                UserIdentity,
                seed.user_id,
                {"organization_id": seed.organization_id, "external_subject": str(seed.user_id), "display_name": "Internal Smoke User"},
            ),
            (
                RegisteredDevice,
                seed.device_id,
                {"workspace_id": seed.workspace_id, "user_id": seed.user_id, "device_public_id": f"internal-smoke-{run_id}", "status": "active"},
            ),
        ]:
            if await db.get(model, key) is None:
                db.add(model(id=key, **values))
        membership = await db.get(WorkspaceMembership, {"workspace_id": seed.workspace_id, "user_id": seed.user_id})
        if membership is None:
            db.add(WorkspaceMembership(workspace_id=seed.workspace_id, user_id=seed.user_id, role="owner", status="active"))
        await db.commit()
    await engine.dispose()
    return seed.headers() | {
        "identity_class": seed.identity_class,
        "device_class": seed.device_class,
        "seed_result": "pass",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dedicated production smoke identity/device records.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(seed_identity(Settings(), args.run_id, execute=args.execute))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
