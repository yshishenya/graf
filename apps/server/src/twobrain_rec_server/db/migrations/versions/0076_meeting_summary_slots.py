"""Add one current summary pointer per meeting and stable summary type."""

from __future__ import annotations

import hashlib
import json
import logging
import struct
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "0076_meeting_summary_slots"
down_revision: str | None = "0075_calendar_sync_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_CONTEXT = "rec_context_kind() in ('request', 'worker')"
SLOT_TABLE = "meeting_summary_slots"
SLOT_POLICY = "meeting_summary_slots_tenant_isolation"
logger = logging.getLogger(__name__)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        constraint.get("name") == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _legacy_proof(
    *,
    workspace_id: object,
    meeting_id: object,
    template_key: str,
    outcome_set_id: object,
    source_basis_hash: str | None,
) -> str:
    payload = json.dumps(
        {
            "meeting_id": str(meeting_id),
            "outcome_set_id": str(outcome_set_id),
            "pre_migration_pointer_kind": "meeting.current_outcome_set_id",
            "source_basis_hash": source_basis_hash,
            "template_key": template_key,
            "workspace_id": str(workspace_id),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    framed = b"GRAF-LEGACY-SLOT-PROOF\x00v1" + struct.pack(">Q", len(payload)) + payload
    return hashlib.sha256(framed).hexdigest()


def _create_policy() -> None:
    if not _is_postgresql():
        return
    predicate = (
        f"(({CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()) "
        "or rec_maintenance_allowed())"
    )
    table = f'"{SLOT_TABLE}"'
    policy = f'"{SLOT_POLICY}"'
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} using ({predicate}) with check ({predicate})"
    )


def _drop_policy() -> None:
    if not _is_postgresql() or not _table_exists(SLOT_TABLE):
        return
    table = f'"{SLOT_TABLE}"'
    policy = f'"{SLOT_POLICY}"'
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _metadata_receipt(**counts: int) -> dict[str, int | str]:
    receipt: dict[str, int | str] = {
        "schema_version": "graf.summary_slot_migration_receipt.v1",
        "migration_revision": revision,
        "mode": "metadata_only",
        "status": "pass",
        **counts,
    }
    logger.info("summary_slot_migration_receipt=%s", json.dumps(receipt, sort_keys=True))
    return receipt


def _backfill_explicit_pointers() -> dict[str, int | str]:
    """Backfill only the locked, explicit meeting pointer; never choose newest."""

    bind = op.get_bind()
    pointed_keyless = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from meetings m
                  join meeting_outcome_sets o
                    on o.id = m.current_outcome_set_id
                   and o.workspace_id = m.workspace_id
                   and o.meeting_id = m.id
                 where m.current_outcome_set_id is not null
                   and m.deletion_state not in ('deleting', 'deleted')
                   and (o.template_key is null or o.template_key = '')
                """
            )
        ).scalar_one()
    )
    # Normalize only the type metadata of a uniquely pointed legacy row before
    # creating the composite slot FK. Content and revision identity are untouched.
    bind.execute(
        sa.text(
            """
            update meeting_outcome_sets o
               set template_key = 'legacy-default'
             from meetings m
            where m.current_outcome_set_id = o.id
              and m.workspace_id = o.workspace_id
              and m.id = o.meeting_id
              and (o.template_key is null or o.template_key = '')
              and m.deletion_state not in ('deleting', 'deleted')
            """
        )
    )
    rows = list(
        bind.execute(
            sa.text(
                """
                select
                    m.workspace_id,
                    m.id as meeting_id,
                    o.id as outcome_set_id,
                    coalesce(nullif(o.template_key, ''), 'legacy-default') as template_key,
                    coalesce(o.source_fingerprint, o.source_result_hash) as source_basis_hash
                from meetings m
                join meeting_outcome_sets o
                  on o.id = m.current_outcome_set_id
                 and o.workspace_id = m.workspace_id
                 and o.meeting_id = m.id
                where m.current_outcome_set_id is not null
                  and m.deletion_state not in ('deleting', 'deleted')
                for update of m, o
                """
            )
        ).mappings()
    )
    resolved_at = datetime(2026, 1, 1, tzinfo=UTC)
    for row in rows:
        template_key = str(row["template_key"])
        proof = _legacy_proof(
            workspace_id=row["workspace_id"],
            meeting_id=row["meeting_id"],
            template_key=template_key,
            outcome_set_id=row["outcome_set_id"],
            source_basis_hash=row["source_basis_hash"],
        )
        bind.execute(
            sa.text(
                """
                insert into meeting_summary_slots (
                    id, workspace_id, meeting_id, template_key,
                    current_outcome_set_id, current_binding_class,
                    legacy_migration_proof_hash, is_meeting_default,
                    default_resolution_source, default_resolution_version,
                    default_resolved_at, created_at, updated_at
                ) values (
                    :id, :workspace_id, :meeting_id, :template_key,
                    :outcome_set_id, 'migrated_legacy_read_only',
                    :proof, true, 'legacy_pointer', '0076-legacy-pointer-v1',
                    :resolved_at, :resolved_at, :resolved_at
                )
                on conflict (workspace_id, meeting_id, template_key) do nothing
                """
            ),
            {
                "id": _stable_slot_id(row["workspace_id"], row["meeting_id"], template_key),
                "workspace_id": row["workspace_id"],
                "meeting_id": row["meeting_id"],
                "template_key": template_key,
                "outcome_set_id": row["outcome_set_id"],
                "proof": proof,
                "resolved_at": resolved_at,
            },
        )
    active_pointer_count = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from meetings
                 where current_outcome_set_id is not null
                   and deletion_state not in ('deleting', 'deleted')
                """
            )
        ).scalar_one()
    )
    deleted_pointer_count = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from meetings
                 where current_outcome_set_id is not null
                   and deletion_state in ('deleting', 'deleted')
                """
            )
        ).scalar_one()
    )
    missing_target_count = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from meetings m
                  left join meeting_outcome_sets o on o.id = m.current_outcome_set_id
                 where m.current_outcome_set_id is not null
                   and m.deletion_state not in ('deleting', 'deleted')
                   and o.id is null
                """
            )
        ).scalar_one()
    )
    cross_scope_target_count = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from meetings m
                  join meeting_outcome_sets o on o.id = m.current_outcome_set_id
                 where m.current_outcome_set_id is not null
                   and m.deletion_state not in ('deleting', 'deleted')
                   and (o.workspace_id <> m.workspace_id or o.meeting_id <> m.id)
                """
            )
        ).scalar_one()
    )
    ambiguous_unpointed_count = int(
        bind.execute(
            sa.text(
                """
                select count(*)
                  from (
                    select m.id
                      from meetings m
                      join meeting_outcome_sets o
                        on o.workspace_id = m.workspace_id
                       and o.meeting_id = m.id
                     where m.current_outcome_set_id is null
                       and m.deletion_state not in ('deleting', 'deleted')
                     group by m.id
                    having count(o.id) > 1
                  ) ambiguous
                """
            )
        ).scalar_one()
    )
    return _metadata_receipt(
        active_pointer_count=active_pointer_count,
        ambiguous_unpointed_count=ambiguous_unpointed_count,
        cross_scope_target_count=cross_scope_target_count,
        deleted_pointer_count=deleted_pointer_count,
        materialized_count=len(rows),
        missing_target_count=missing_target_count,
        pointed_keyless_count=pointed_keyless,
    )


def _verify_post_backfill(receipt: dict[str, int | str] | None = None) -> None:
    """Fail closed if any materialized legacy slot is not exactly representable."""

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            select s.id,
                   s.workspace_id,
                   s.meeting_id,
                   s.template_key,
                   s.current_outcome_set_id,
                   s.legacy_migration_proof_hash,
                   o.source_fingerprint,
                   o.source_result_hash
              from meeting_summary_slots s
              join meetings m
                on m.id = s.meeting_id
               and m.workspace_id = s.workspace_id
             left join meeting_outcome_sets o
                on o.id = s.current_outcome_set_id
               and o.workspace_id = s.workspace_id
               and o.meeting_id = s.meeting_id
               and o.template_key = s.template_key
             where s.current_binding_class = 'migrated_legacy_read_only'
               and (
                    not s.is_meeting_default
                    or s.legacy_migration_proof_hash is null
                    or m.current_outcome_set_id is distinct from s.current_outcome_set_id
                    or o.id is null
               )
            """
        )
    ).mappings()
    invalid = next(iter(rows), None)
    if invalid is not None:
        raise RuntimeError("0076 post-backfill verifier failed: legacy slot is not representable")
    proof_rows = list(
        bind.execute(
            sa.text(
                """
                select s.workspace_id,
                       s.meeting_id,
                       s.template_key,
                       s.current_outcome_set_id,
                       s.legacy_migration_proof_hash,
                       o.source_fingerprint,
                       o.source_result_hash
                  from meeting_summary_slots s
                  join meeting_outcome_sets o
                    on o.id = s.current_outcome_set_id
                   and o.workspace_id = s.workspace_id
                   and o.meeting_id = s.meeting_id
                   and o.template_key = s.template_key
                 where s.current_binding_class = 'migrated_legacy_read_only'
                """
            )
        ).mappings()
    )
    for row in proof_rows:
        expected = _legacy_proof(
            workspace_id=row["workspace_id"],
            meeting_id=row["meeting_id"],
            template_key=row["template_key"],
            outcome_set_id=row["current_outcome_set_id"],
            source_basis_hash=row["source_fingerprint"] or row["source_result_hash"],
        )
        if row["legacy_migration_proof_hash"] != expected:
            raise RuntimeError("0076 post-backfill verifier failed: legacy proof mismatch")
    if receipt is not None and receipt.get("status") != "pass":
        raise RuntimeError("0076 post-backfill verifier failed: migration receipt is not passing")
    _metadata_receipt(
        **{
            key: int(value)
            for key, value in (receipt or {}).items()
            if key.endswith("_count") and isinstance(value, int)
        },
        verified_legacy_count=len(proof_rows),
    )


def _stable_slot_id(workspace_id: object, meeting_id: object, template_key: str) -> str:
    digest = hashlib.sha256(
        f"GRAF-SUMMARY-SLOT\x00v1:{workspace_id}:{meeting_id}:{template_key}".encode()
    ).hexdigest()[:32]
    return str(UUID(hex=digest))


def upgrade() -> None:
    if not _constraint_exists("meetings", "uq_meetings_id_workspace_id"):
        op.create_unique_constraint(
            "uq_meetings_id_workspace_id", "meetings", ["id", "workspace_id"]
        )
    if not _constraint_exists("meeting_outcome_sets", "uq_meeting_outcome_sets_target"):
        op.create_unique_constraint(
            "uq_meeting_outcome_sets_target",
            "meeting_outcome_sets",
            ["id", "workspace_id", "meeting_id", "template_key"],
        )

    if not _table_exists(SLOT_TABLE):
        op.create_table(
            SLOT_TABLE,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("workspace_id", sa.Uuid(), nullable=False),
            sa.Column("meeting_id", sa.Uuid(), nullable=False),
            sa.Column("template_key", sa.String(length=120), nullable=False),
            sa.Column("current_outcome_set_id", sa.Uuid()),
            sa.Column("current_binding_class", sa.String(length=40)),
            sa.Column("legacy_migration_proof_hash", sa.String(length=64)),
            sa.Column("is_meeting_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("default_resolution_source", sa.String(length=32)),
            sa.Column("default_resolution_version", sa.String(length=128)),
            sa.Column("default_resolved_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["meeting_id", "workspace_id"],
                ["meetings.id", "meetings.workspace_id"],
                name="fk_meeting_summary_slots_meeting_workspace",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["current_outcome_set_id", "workspace_id", "meeting_id", "template_key"],
                [
                    "meeting_outcome_sets.id",
                    "meeting_outcome_sets.workspace_id",
                    "meeting_outcome_sets.meeting_id",
                    "meeting_outcome_sets.template_key",
                ],
                name="fk_meeting_summary_slots_current_outcome_target",
            ),
            sa.UniqueConstraint(
                "workspace_id",
                "meeting_id",
                "template_key",
                name="uq_meeting_summary_slots_workspace_meeting_type",
            ),
            sa.CheckConstraint(
                "current_binding_class is null or current_binding_class in "
                "('verified_complete', 'migrated_legacy_read_only')",
                name="ck_meeting_summary_slots_binding_class",
            ),
            sa.CheckConstraint(
                "(current_outcome_set_id is null and current_binding_class is null "
                "and legacy_migration_proof_hash is null) or "
                "(current_outcome_set_id is not null and current_binding_class = 'verified_complete' "
                "and legacy_migration_proof_hash is null) or "
                "(current_outcome_set_id is not null and current_binding_class = 'migrated_legacy_read_only' "
                "and legacy_migration_proof_hash is not null)",
                name="ck_meeting_summary_slots_current_binding",
            ),
            sa.CheckConstraint(
                "(is_meeting_default is false and default_resolution_source is null "
                "and default_resolution_version is null and default_resolved_at is null) or "
                "(is_meeting_default is true and default_resolution_source in "
                "('explicit_meeting', 'owner_personal', 'workspace', 'legacy_pointer') "
                "and default_resolution_version is not null and default_resolved_at is not null)",
                name="ck_meeting_summary_slots_default_metadata",
            ),
        )
    if not any(
        index.get("name") == "uq_meeting_summary_slots_meeting_default"
        for index in sa.inspect(op.get_bind()).get_indexes(SLOT_TABLE)
    ):
        op.create_index(
            "uq_meeting_summary_slots_meeting_default",
            SLOT_TABLE,
            ["workspace_id", "meeting_id"],
            unique=True,
            postgresql_where=sa.text("is_meeting_default is true"),
        )
    _create_policy()
    receipt = _backfill_explicit_pointers()
    _verify_post_backfill(receipt)


def downgrade() -> None:
    if _table_exists(SLOT_TABLE):
        bind = op.get_bind()
        nonrepresentable = bind.execute(
            sa.text(
                """
                select 1
                from meeting_summary_slots
                group by workspace_id, meeting_id
                having count(*) > 1
                   or count(*) filter (where is_meeting_default) <> 1
                limit 1
                """
            )
        ).first()
        if nonrepresentable is not None:
            raise RuntimeError(
                "0076 downgrade blocked: multiple summary slots cannot be represented by the legacy pointer"
            )
        mismatch = bind.execute(
            sa.text(
                """
                select 1
                from meeting_summary_slots s
                join meetings m on m.id = s.meeting_id and m.workspace_id = s.workspace_id
                where s.current_outcome_set_id is distinct from m.current_outcome_set_id
                limit 1
                """
            )
        ).first()
        if mismatch is not None:
            raise RuntimeError("0076 downgrade blocked: slot current differs from legacy pointer")
        _drop_policy()
        op.drop_index("uq_meeting_summary_slots_meeting_default", table_name=SLOT_TABLE)
        op.drop_table(SLOT_TABLE)
    if _constraint_exists("meeting_outcome_sets", "uq_meeting_outcome_sets_target"):
        op.drop_constraint("uq_meeting_outcome_sets_target", "meeting_outcome_sets", type_="unique")
    if _constraint_exists("meetings", "uq_meetings_id_workspace_id"):
        op.drop_constraint("uq_meetings_id_workspace_id", "meetings", type_="unique")
