"""Isolated T113 rehearsal: quarantine and exact ledger erasure, never readiness.

Only owned synthetic sources are accepted until the product-wide drain is built.
The caller creates/compares/cleans the UUID target and holds the operator lock.
No provider configuration, router, worker or sender is loaded by this process.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.db.models import ProductActivationMilestone
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.product_analytics.acquisition import delete_account_acquisition_attribute
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    LEVEL_RETENTION_CATEGORIES,
    LOCAL_CATEGORY_TABLES,
    _version2_records,
    apply_basis_loss_disposition,
    parse_disposition_cases,
    plan_processing_stop,
)
from twobrain_rec_server.product_analytics.milestones import (
    delete_account_activation_decisions,
    quarantine_milestone_deliveries,
)

CONTEXT = MaintenanceTenantContext(
    operation_name="backup_restore_rehearsal", actor_id="restore_operator",
    reason_category="restore_replay", feature_area="product_analytics",
)
CLOSURE_POLICY = "((requested_by_user_id = rec_current_user_id()) OR rec_maintenance_allowed())"
CLOSURE_POLICY_QUERY = """
        SELECT polname, polpermissive, polcmd::text, polroles::text,
               pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid)
          FROM pg_policy WHERE polrelid='public.account_closure_requests'::regclass
    """
CLOSURE_ACCESS_QUERY = """SELECT relrowsecurity AND relforcerowsecurity
    AND has_table_privilege(session_user,oid,'SELECT') FROM pg_class
    WHERE oid='public.account_closure_requests'::regclass"""
UNRESTRICTED_TABLES = sorted(name for category, name in LOCAL_CATEGORY_TABLES.items()
                             if category != "activation_milestone_decisions")
LOCAL_ACCESS_QUERY = """
    SELECT c.relname::text,c.relrowsecurity,c.relforcerowsecurity,
        has_table_privilege(session_user,c.oid,'SELECT'),
        (SELECT count(*) FROM pg_policy p WHERE p.polrelid=c.oid)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relname IN
        ('anonymous_page_aggregate_buckets','client_acquisition_attributes','public_visit_attributions')
    ORDER BY c.relname
"""


def check_local_access(rows):
    if [tuple(row) for row in rows] != [(name, False, False, True, 0) for name in UNRESTRICTED_TABLES]:
        raise ReplayHold("replay_local_access_invalid")


def withdrawn_local_categories(value):
    return {category for kind, row in _version2_records(value)
            if kind == "basis_withdrawal" and row["level"] != "provider_analytics"
            for category in LEVEL_RETENTION_CATEGORIES[row["level"]]}

CLOSURE_ROWS_QUERY = """
        SELECT id, requested_by_user_id AS account_id, state, requested_at, finalize_at,
               finalized_at, canceled_at,
               metadata_json->>'activation_decisions_purged_at' AS purged_at,
               metadata_json->>'activation_decisions_purged_count' AS purged_count,
               json_typeof(metadata_json->'activation_decisions_purged_count') AS purged_type,
               metadata_json->>'acquisition_attributes_purged_at' AS acquisition_purged_at,
               metadata_json->>'acquisition_attributes_purged_count' AS acquisition_purged_count,
               json_typeof(metadata_json->'acquisition_attributes_purged_count') AS acquisition_purged_type,
               metadata_json::jsonb ?| ARRAY['acquisition_attributes_purged_at',
                   'acquisition_attributes_purged_count'] AS acquisition_present
          FROM public.account_closure_requests ORDER BY id
    """
UNCONFIRMED = {"pending", "pre_send_retry", "dispatching", "submitted"}


class ReplayHold(ValueError):
    """Safe finite code only; never attach a row, selector or DB exception."""


def private_bytes(path: Path, *, limit: int = 10 * 1024 * 1024) -> bytes:
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid()
            or stat.S_IMODE(parent.st_mode) != 0o700):
        raise ReplayHold("replay_private_directory_invalid")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or not 0 < info.st_size <= limit):
            raise ReplayHold("replay_private_file_invalid")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            value = stream.read(limit + 1)
        if len(value) != info.st_size:
            raise ReplayHold("replay_private_file_changed")
        return value
    finally:
        os.close(fd)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def ownership_record(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReplayHold("replay_ownership_duplicate")
            result[key] = value
        return result

    record = json.loads(raw, object_pairs_hook=unique)
    fields = {"version", "token", "source_database", "source_oid", "target_database",
              "target_oid", "backup_sha256"}
    if (not isinstance(record, dict) or set(record) != fields or type(record["version"]) is not int
            or record["version"] != 1 or not isinstance(record["token"], str)
            or re.fullmatch(r"[0-9a-f]{32}", record["token"]) is None
            or not isinstance(record["source_database"], str)
            or re.fullmatch(r"twobrain_rec_test_[0-9a-f]{32}", record["source_database"]) is None
            or record["target_database"] != "rec_restore_rehearsal_" + record["token"]
            or any(type(record[key]) is not int or record[key] <= 0
                   for key in ("source_oid", "target_oid"))
            or record["source_oid"] == record["target_oid"]
            or not isinstance(record["backup_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", record["backup_sha256"]) is None):
        raise ReplayHold("replay_ownership_invalid")
    return record


async def database_context(db, *, name: str, oid: int):
    await apply_tenant_context(db, CONTEXT)
    identity = (await db.execute(text("""
        SELECT current_database(), d.oid::bigint, session_user, current_user,
               current_setting('row_security'), rec_maintenance_allowed(),
               r.rolsuper, r.rolbypassrls, r.rolcreatedb, r.rolcreaterole, r.rolinherit
          FROM pg_database d CROSS JOIN pg_roles r
         WHERE d.datname=current_database() AND r.rolname=session_user
    """))).one()
    if tuple(identity) != (name, oid, "twobrain_rec_maintenance", "twobrain_rec_maintenance",
                           "on", True, False, False, False, False, False):
        raise ReplayHold("replay_database_identity_invalid")


async def closure_snapshot(db) -> list[dict]:
    policy = (await db.execute(text(CLOSURE_POLICY_QUERY))).all()
    expected = ("account_closure_requests_owner", True, "*", "{0}",
                CLOSURE_POLICY, CLOSURE_POLICY)
    if [tuple(row) for row in policy] != [expected] or not await db.scalar(text(CLOSURE_ACCESS_QUERY)):
        raise ReplayHold("replay_source_policy_invalid")
    # No due filter/limit, and no request key or arbitrary metadata in the snapshot.
    rows = (await db.execute(text(CLOSURE_ROWS_QUERY))).mappings().all()
    return [dict(row) for row in rows]


def replay_accounts(rows, cases, *, required_categories: set[str], now: datetime):
    requests = {str(row["id"]): row for row in rows}
    if len(requests) != len(rows) or any(case.stage == "failed" for case in cases):
        raise ReplayHold("replay_history_invalid")
    account_cases = {case.selector_ref: case for case in cases if case.scope == "account_closure"}
    categories = [case for case in cases if case.scope in LOCAL_CATEGORY_TABLES]
    if not required_categories <= {case.scope for case in categories}:
        raise ReplayHold("replay_category_case_missing")
    completed = set()
    for reference, row in requests.items():
        if row["state"] in {"scheduled", "canceled"}:
            continue
        if row["state"] != "completed":
            raise ReplayHold("replay_history_unresolved")
        completed.add(reference)
        try:
            purged = datetime.fromisoformat(row["purged_at"])
            count = row["purged_count"]
            valid = (row["finalized_at"] is not None and purged.tzinfo is not None
                     and row["requested_at"] <= purged <= row["finalized_at"] <= now
                     and row["purged_type"] == "number" and count.isascii()
                     and count.isdecimal() and len(count) <= 19 and int(count) <= 2**63 - 1)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise ReplayHold("replay_purge_result_missing")
    if completed != set(account_cases):
        raise ReplayHold("replay_case_coverage_incomplete")
    return {requests[key]["account_id"] for key in completed}, categories


def source_replay_accounts(rows, cases, *, required_categories: set[str], now: datetime):
    """Current source postconditions; a replay intent is not historical deadline proof."""
    accounts, categories = replay_accounts(rows, cases, required_categories=required_categories, now=now)
    for row in rows:
        times = [row[key] for key in ("requested_at", "finalize_at", "finalized_at", "canceled_at")]
        if any(not isinstance(value, datetime) or value.utcoffset() is None
               for value in times if value is not None):
            raise ReplayHold("replay_source_timeline_invalid")
        requested, due, finalized, canceled = times
        if requested is None or due is None or not requested <= now or due < requested:
            raise ReplayHold("replay_source_timeline_invalid")
        if row["state"] == "completed":
            valid = canceled is None and due <= datetime.fromisoformat(row["purged_at"]) <= finalized
        else:
            valid = finalized is None and all(row[key] is None for key in
                ("purged_at", "purged_count", "purged_type"))
            if row["state"] == "scheduled":
                valid = valid and canceled is None and now < due
            else:  # replay_accounts already rejected unresolved/unknown states.
                valid = valid and canceled is not None and requested <= canceled <= now and canceled < due
        if row.get("acquisition_present", False):
            try:
                purged = datetime.fromisoformat(row["acquisition_purged_at"])
                count = row["acquisition_purged_count"]
                valid = (valid and row["state"] == "completed" and purged.utcoffset() is not None
                         and due <= purged <= finalized
                         and row["acquisition_purged_type"] == "number" and count.isascii()
                         and count.isdecimal() and len(count) <= 19 and int(count) <= 2**63 - 1)
            except (ValueError, TypeError, AttributeError):
                valid = False
        if not valid:
            raise ReplayHold("replay_source_timeline_invalid")
    if any(case.stage != "applied" for case in categories):
        raise ReplayHold("replay_source_category_result_missing")
    # A later idempotent replay can legitimately have different count/time from the first purge.
    late = sum(case.applied_at > case.due_at for case in cases if case.applied_at is not None)
    return accounts, categories, late


async def ledger(db):
    return {row["id"]: dict(row) for row in
            (await db.execute(select(ProductActivationMilestone.__table__))).mappings()}


def expected_ledger(before, accounts, *, category: bool):
    expected = {}
    for key, original in before.items():
        if category or original["account_id"] in accounts:
            continue
        row = dict(original)
        changed = False
        for provider in ("posthog", "yandex"):
            if row[f"{provider}_state"] in UNCONFIRMED:
                row[f"{provider}_state"] = "ambiguous"
                row[f"{provider}_reason"] = "restore_quarantine"
                changed = True
        if changed:
            row.pop("updated_at")
        expected[key] = row
    return expected


async def verify_ledger(db, expected):
    actual = await ledger(db)
    if set(actual) != set(expected):
        raise ReplayHold("replay_ledger_mismatch")
    for key, row in expected.items():
        if any(actual[key][field] != value for field, value in row.items()):
            raise ReplayHold("replay_ledger_mismatch")


async def local_rows(db):
    check_local_access((await db.execute(text(LOCAL_ACCESS_QUERY))).all())
    return {category: {row["id"]: dict(row) for row in
            (await db.execute(text(f'SELECT * FROM public."{table}"'))).mappings()}
            for category, table in LOCAL_CATEGORY_TABLES.items()
            if category != "activation_milestone_decisions"}


def expected_local_rows(before, accounts, categories):
    return {category: {key: row for key, row in rows.items()
            if category not in categories and not (
                category == "client_acquisition_attribute" and row["account_id"] in accounts)}
            for category, rows in before.items()}


async def verify_local_rows(db, expected):
    if await local_rows(db) != expected:
        raise ReplayHold("replay_local_rows_mismatch")


async def reconcile(*, host: str, port: int, password_file: Path, operator_file: Path,
                    ownership_file: Path, staging: Path) -> dict:
    """One stopped synthetic source and one previously compared owned UUID target."""

    staging_info = staging.lstat()
    if (not stat.S_ISDIR(staging_info.st_mode) or staging_info.st_uid != os.geteuid()
            or stat.S_IMODE(staging_info.st_mode) != 0o700):
        raise ReplayHold("replay_private_directory_invalid")
    operator = private_bytes(operator_file)
    ownership = private_bytes(ownership_file)
    binding = ownership_record(ownership)
    now = datetime.now(UTC)
    cases = parse_disposition_cases(operator.decode("utf-8"), now=now)
    required_categories = withdrawn_local_categories(operator.decode("utf-8"))
    password = private_bytes(password_file, limit=16384).decode("utf-8").strip()
    if not password or "\x00" in password:
        raise ReplayHold("replay_password_invalid")
    engines = []
    commit_attempted = False
    try:
        for name in (binding["source_database"], binding["target_database"]):
            engines.append(create_async_engine(
                URL.create("postgresql+asyncpg", username="twobrain_rec_maintenance",
                           password=password, host=host, port=port, database=name),
                poolclass=NullPool, hide_parameters=True,
                connect_args={"timeout": 5, "command_timeout": 30,
                              "server_settings": {"statement_timeout": "25000", "lock_timeout": "5000",
                                                  "idle_in_transaction_session_timeout": "30000"}},
            ))
        source_sessions, target_sessions = (async_sessionmaker(engine) for engine in engines)
        async with source_sessions() as source:
            await source.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await database_context(source, name=binding["source_database"], oid=binding["source_oid"])
            rows = await closure_snapshot(source)
            accounts, categories = replay_accounts(rows, cases, required_categories=required_categories, now=now)
            snapshot = json.dumps({"binding": binding, "register_sha256": digest(operator),
                                   "captured_at": now.isoformat(), "requests": rows},
                                  default=str, sort_keys=True).encode()
            # Created here from the authoritative read; no input accepts a supplied pass snapshot.
            with tempfile.TemporaryDirectory(prefix="replay-", dir=staging) as directory:
                path = Path(directory) / "closure-snapshot.json"
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(snapshot)
                    stream.flush()
                    os.fsync(stream.fileno())
                if private_bytes(path) != snapshot:
                    raise ReplayHold("replay_snapshot_changed")

                def unchanged():
                    if (private_bytes(operator_file) != operator
                            or private_bytes(ownership_file) != ownership
                            or private_bytes(path) != snapshot):
                        raise ReplayHold("replay_inputs_changed")

                async with target_sessions() as target:
                    await database_context(target, name=binding["target_database"], oid=binding["target_oid"])
                    before = await ledger(target)
                    scopes = {case.scope for case in categories}
                    expected = expected_ledger(before, accounts, category="activation_milestone_decisions" in scopes)
                    expected_local = expected_local_rows(await local_rows(target), accounts, scopes)
                    unchanged()
                    intents = await quarantine_milestone_deliveries(target, after_restore=True)
                    removed = 0
                    for account in sorted(accounts, key=str):
                        removed += await delete_account_activation_decisions(target, account_id=account)
                        removed += await delete_account_acquisition_attribute(target, account_id=account)
                    for case in categories:
                        plan = plan_processing_stop(
                            level_key=next(level for level, group in LEVEL_RETENTION_CATEGORIES.items()
                                           if case.scope in group), basis_lost_at=case.decided_at,
                            reason=case.reason, affected_categories=(case.scope,),
                            deletion_deadlines={case.scope: case.due_at},
                        )
                        outcomes = await apply_basis_loss_disposition(target, plan, commit=False)
                        removed += sum(result.rows_affected for result in outcomes)
                    await verify_ledger(target, expected)
                    await verify_local_rows(target, expected_local)
                    unchanged()
                    commit_attempted = True
                    await target.commit()
                # A fresh connection observes committed state. Failure here is unknown, not rollback.
                async with target_sessions() as readback:
                    await database_context(readback, name=binding["target_database"], oid=binding["target_oid"])
                    await verify_ledger(readback, expected)
                    await verify_local_rows(readback, expected_local)
                    unchanged()
            if Path(directory).exists():
                raise ReplayHold("replay_cleanup_failed")
        verified_at = datetime.now(UTC)
        return {"replay_result": "verified", "readiness": "hold", "cases": len(cases),
                "quarantined_intents": intents, "deleted_rows": removed,
                "overdue_cases": sum(verified_at > case.due_at for case in cases),
                "verified_at": verified_at.isoformat(),
                "operator_sha256": digest(operator), "snapshot_sha256": digest(snapshot),
                "backup_sha256": binding["backup_sha256"]}
    except Exception as exc:
        code = exc.args[0] if isinstance(exc, ReplayHold) else "replay_refused"
        raise ReplayHold("replay_result_unknown" if commit_attempted else code) from None
    finally:
        for engine in engines:
            await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    for name in ("password-file", "operator-file", "ownership-file", "staging"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(reconcile(host=args.host, port=args.port,
                                      password_file=args.password_file, operator_file=args.operator_file,
                                      ownership_file=args.ownership_file, staging=args.staging))
    except Exception as exc:
        unknown = isinstance(exc, ReplayHold) and exc.args == ("replay_result_unknown",)
        print(json.dumps({"replay_result": "unknown" if unknown else "hold", "readiness": "hold",
                          "reason": exc.args[0] if isinstance(exc, ReplayHold) else "replay_refused"}))
        raise SystemExit(1) from None
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
