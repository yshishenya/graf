"""Transaction-scoped registry receipts; no provider objects or money are stored."""
from datetime import date, timedelta

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.registry import (
    CONFIG_FINGERPRINT,
    PROFILE,
    RegistryBundle,
    canonical_hash,
)
from twobrain_rec_server.db.models.billing_registry import BillingRegistryGap, BillingRegistryImport

IMPORTS = BillingRegistryImport.__table__
GAPS = BillingRegistryGap.__table__


def _scope(table, environment, shop_id, report_date):
    return (table.c.environment == environment, table.c.shop_id == shop_id,
            table.c.report_date == report_date)


async def _access(db, statement):
    # The real login/context is checked before EVERY protected store statement.
    await require_billing_maintenance_database(db)
    return await db.execute(statement)


async def _scope_lock(db, environment, shop_id, report_date, *, shared=False):
    await require_billing_maintenance_database(db)
    scope_key = canonical_hash([environment, shop_id, report_date.isoformat()])
    function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    await db.execute(text(f"SELECT {function}(hashtextextended(:scope, 0))"), {"scope": scope_key})


def receipt_metadata(row):
    if row is None:
        return None
    return {"receipt_id": row["id"], "input_digest": row["input_digest"],
            "profile": row["profile"], "config_fingerprint": row["config_fingerprint"],
            "parts": row["parts"], "expected_empty": row["expected_empty"],
            "accepted": row["accepted"], "files_complete": row["files_complete"],
            "result_code": row["result_code"], "previous_accepted_id": row["previous_accepted_id"],
            "operator": row["operator"], "reason_code": row["reason_code"],
            "created_at": row["created_at"].isoformat(),
            "session_identity": row["session_identity"], "current_identity": row["current_identity"],
            "financial_status": "not_checked"}


async def registry_status(db: AsyncSession, *, environment: str, shop_id: str, report_date: date):
    # Hold a shared scope lock through all reads; imports hold its exclusive peer.
    await _scope_lock(db, environment, shop_id, report_date, shared=True)
    query = select(IMPORTS).where(*_scope(IMPORTS, environment, shop_id, report_date)).order_by(IMPORTS.c.id.desc())
    attempt = (await _access(db, query.limit(1))).mappings().first()
    accepted = (await _access(db, query.where(IMPORTS.c.accepted).limit(1))).mappings().first()
    gaps = (await _access(db, select(GAPS).where(*_scope(GAPS, environment, shop_id, report_date),
                                               GAPS.c.state == "detected").order_by(GAPS.c.id))).mappings().all()
    return {"last_attempt": receipt_metadata(attempt), "latest_accepted": receipt_metadata(accepted),
            "financial_status": "not_checked", "open_gaps": [
                {"gap_id": g["id"], "kind": g["kind"], "part_index": g["part_index"],
                 "reason": g["reason"], "generation": g["generation"], "owner": g["owner"],
                 "severity": g["severity"], "containment": g["containment"],
                 "detected_receipt_id": g["detected_receipt_id"], "state": g["state"],
                 **{key: g[key].isoformat() for key in ("detected_at", "checked_at", "deadline_at")}}
                for g in gaps]}


async def persist_registry(db: AsyncSession, *, environment: str, shop_id: str, report_date: date,
                           bundle: RegistryBundle | None, expected_empty: frozenset[str],
                           error_code: str | None, owner: str, operator: str,
                           replace_digest: str | None, reason: str):
    """Caller owns one transaction: scope lock, receipt and all gap transitions."""
    await _scope_lock(db, environment, shop_id, report_date)
    scope = _scope(IMPORTS, environment, shop_id, report_date)
    current = (await _access(db, select(IMPORTS).where(*scope, IMPORTS.c.accepted)
                             .order_by(IMPORTS.c.id.desc()).limit(1))).mappings().first()
    if bundle is not None and error_code is None:
        replay = (await _access(db, select(IMPORTS).where(*scope, IMPORTS.c.accepted,
                             IMPORTS.c.profile == PROFILE, IMPORTS.c.config_fingerprint == CONFIG_FINGERPRINT,
                             IMPORTS.c.input_digest == bundle.input_digest).limit(1))).mappings().first()
        if replay:
            return {**receipt_metadata(replay), "replay": True}, 0
        if (current is not None and replace_digest != current["input_digest"]) or (current is None and replace_digest is not None):
            error_code = "replace_conflict"
    accepted = error_code is None and bundle is not None
    complete = accepted and bundle.files_complete
    receipt = (await _access(db, insert(IMPORTS).values(
        environment=environment, shop_id=shop_id, report_date=report_date, profile=PROFILE,
        config_fingerprint=CONFIG_FINGERPRINT, input_digest=bundle.input_digest if bundle else None,
        parts=list(bundle.parts) if bundle else [], expected_empty=sorted(expected_empty),
        accepted=accepted, files_complete=complete,
        result_code=error_code or ("accepted_complete" if complete else "accepted_incomplete"),
        previous_accepted_id=current["id"] if current else None, operator=operator, reason_code=reason,
    ).returning(IMPORTS))).mappings().one()
    now = (await db.execute(select(func.clock_timestamp()))).scalar_one()
    pending = set(bundle.gaps if accepted else [("input", 0, error_code)])
    scope_gaps = _scope(GAPS, environment, shop_id, report_date)
    existing = (await _access(db, select(GAPS).where(*scope_gaps, GAPS.c.state == "detected"))).mappings().all()
    for gap in existing:
        key = (gap["kind"], gap["part_index"], gap["reason"])
        if key in pending:
            # A rejected attempt must not touch gaps belonging to the accepted set.
            if accepted or gap["kind"] == "input":
                await _access(db, update(GAPS).where(GAPS.c.id == gap["id"]).values(checked_at=now))
            pending.discard(key)
        elif accepted:
            await _access(db, update(GAPS).where(GAPS.c.id == gap["id"]).values(
                state="resolved", checked_at=now, closing_receipt_id=receipt["id"], resolved_at=now,
                resolution_code="verified_replacement", resolved_by=operator))
    for kind, index, code in sorted(pending):
        last_generation = (await _access(db, select(func.max(GAPS.c.generation)).where(
            *scope_gaps, GAPS.c.kind == kind, GAPS.c.part_index == index, GAPS.c.reason == code))).scalar_one()
        await _access(db, insert(GAPS).values(
            environment=environment, shop_id=shop_id, report_date=report_date,
            kind=kind, part_index=index, reason=code, generation=(last_generation or 0) + 1,
            owner=owner, detected_receipt_id=receipt["id"], detected_at=now, checked_at=now,
            deadline_at=now + timedelta(hours=24)))
    return {**receipt_metadata(receipt), "replay": False}, 0 if accepted else 1
