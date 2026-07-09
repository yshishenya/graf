"""publish meeting detection registry from migration data

Revision ID: 0019_publish_meeting_registry
Revises: 0018_mediascribe_result
Create Date: 2026-07-09
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0019_publish_meeting_registry"
down_revision: str | None = "0018_mediascribe_result"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REGISTRY_VERSION = "2026.07.09.4"
REGISTRY_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "0019_meeting_target_registry.json"


def _registry_versions_table() -> sa.TableClause:
    return sa.table(
        "meeting_target_registry_versions",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("registry_version", sa.String()),
        sa.column("schema_version", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("source", sa.String()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("published_by_user_id", sa.Uuid()),
        sa.column("document_json", sa.JSON()),
        sa.column("etag", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )


def _registry_entries_table() -> sa.TableClause:
    return sa.table(
        "meeting_target_registry_entries",
        sa.column("id", sa.Uuid()),
        sa.column("registry_version_id", sa.Uuid()),
        sa.column("target_id", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("market", sa.String()),
        sa.column("platform", sa.String()),
        sa.column("target_family", sa.String()),
        sa.column("mode", sa.String()),
        sa.column("evidence", sa.String()),
        sa.column("native_bundle_ids", sa.JSON()),
        sa.column("windows_process_names", sa.JSON()),
        sa.column("browser_service_patterns", sa.JSON()),
        sa.column("required_signals", sa.JSON()),
        sa.column("comments", sa.String()),
    )


def _load_document() -> dict:
    return json.loads(REGISTRY_DATA_PATH.read_text(encoding="utf-8"))


def _etag(document: dict) -> str:
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _entries(registry_version_id: UUID, document: dict) -> list[dict]:
    return [
        {
            "id": uuid4(),
            "registry_version_id": registry_version_id,
            "target_id": target["id"],
            "display_name": target["displayName"],
            "market": target["market"],
            "platform": target["platform"],
            "target_family": target["targetFamily"],
            "mode": target["mode"],
            "evidence": target["evidence"],
            "native_bundle_ids": target.get("nativeBundleIds", []),
            "windows_process_names": target.get("windowsProcessNames", []),
            "browser_service_patterns": target.get("browserServicePatterns", []),
            "required_signals": target["requiredSignals"],
            "comments": target.get("comments"),
        }
        for target in document["targets"]
    ]


def upgrade() -> None:
    versions = _registry_versions_table()
    entries = _registry_entries_table()
    connection = op.get_bind()
    document = _load_document()
    published_at = datetime.now(UTC)
    registry_id = uuid4()

    connection.execute(
        versions.update()
        .where(versions.c.workspace_id.is_(None))
        .where(versions.c.status == "published")
        .values(status="superseded", updated_at=published_at)
    )
    connection.execute(
        versions.insert().values(
            id=registry_id,
            workspace_id=None,
            registry_version=document["registryVersion"],
            schema_version=document["schemaVersion"],
            status="published",
            source="migration",
            published_at=published_at,
            published_by_user_id=None,
            document_json=document,
            etag=_etag(document),
            created_at=published_at,
            updated_at=published_at,
        )
    )
    op.bulk_insert(entries, _entries(registry_id, document))


def downgrade() -> None:
    versions = _registry_versions_table()
    entries = _registry_entries_table()
    connection = op.get_bind()
    row = connection.execute(
        sa.select(versions.c.id).where(
            versions.c.workspace_id.is_(None),
            versions.c.registry_version == REGISTRY_VERSION,
            versions.c.source == "migration",
        )
    ).first()
    if row is not None:
        connection.execute(entries.delete().where(entries.c.registry_version_id == row.id))
        connection.execute(versions.delete().where(versions.c.id == row.id))
    previous = connection.execute(
        sa.select(versions.c.id)
        .where(versions.c.workspace_id.is_(None))
        .where(versions.c.status == "superseded")
        .order_by(sa.desc(versions.c.published_at), sa.desc(versions.c.created_at))
        .limit(1)
    ).first()
    if previous is not None:
        connection.execute(
            versions.update()
            .where(versions.c.id == previous.id)
            .values(status="published", updated_at=datetime.now(UTC))
        )
