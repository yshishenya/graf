#!/usr/bin/env python3
"""Metadata-only Dev migration probe and isolated backup/restore rehearsal."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import unquote, urlsplit


SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
MIGRATION_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
FORBIDDEN = ("prod", "production", "staging")
SAFE_TARGET_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
TARGETS = {"isolated-dev", "isolated-restore", "dev-existing"}
DEV_POSTGRES_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEV_POSTGRES_PORTS = {54329, 54330}
DEV_POSTGRES_USER = "twobrain_rec"
DEV_POSTGRES_DATABASE = "twobrain_rec"
ALEMBIC_REVISION_QUERY = "SELECT version_num FROM alembic_version ORDER BY version_num;"


class RepairError(RuntimeError):
    """Expected fail-closed repair error."""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RepairError(f"cannot read metadata file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RepairError(f"metadata file must contain an object: {path}")
    return value


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_sha(root: Path) -> str:
    try:
        value = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RepairError(f"cannot resolve source SHA: {exc}") from exc
    if not SHA_RE.fullmatch(value):
        raise RepairError("source SHA is not a full 40-character git SHA")
    return value.lower()


def target_path(root: Path, target: str) -> Path:
    if not isinstance(target, str) or not SAFE_TARGET_RE.fullmatch(target) or target not in TARGETS:
        raise RepairError(f"unsupported or unsafe target: {target!r}")
    if any(token in target.lower() for token in FORBIDDEN):
        raise RepairError("production-looking migration target is rejected")
    return root / ".dev" / "migration-repair" / "targets" / target / "state.json"


def schema_fingerprint(path: Path) -> str:
    """Digest metadata descriptor bytes; never inspect database rows."""
    if not path.exists():
        return "sha256:" + hashlib.sha256(b"missing-state").hexdigest()
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def code_heads(root: Path) -> list[str]:
    versions = root / "apps" / "server" / "src" / "twobrain_rec_server" / "db" / "migrations" / "versions"
    if not versions.is_dir():
        raise RepairError(f"migration directory is missing: {versions}")
    revisions: set[str] = set()
    referenced: set[str] = set()
    for path in sorted(versions.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="strict")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            raise RepairError(f"cannot parse migration file {path}: {exc}") from exc
        for node in tree.body:
            names = []
            value_node = None
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
                value_node = node.value
            elif isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                value_node = node.value
            if not value_node or not names or not ({"revision", "down_revision"} & set(names)):
                continue
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError):
                continue
            if "revision" in names and isinstance(value, str):
                revisions.add(value)
            if "down_revision" in names:
                values = (value,) if isinstance(value, str) else value if isinstance(value, (tuple, list)) else ()
                referenced.update(item for item in values if isinstance(item, str))
    heads = sorted(revisions - referenced)
    if not heads:
        raise RepairError("migration graph has no resolvable head")
    return heads


def read_current(path: Path) -> str | None:
    if not path.exists():
        return None
    data = load_json(path)
    value = data.get("current_revision")
    return value if isinstance(value, str) and value.strip() else None


def _dev_database_connection(database_url: str) -> tuple[str, int, str, str, str | None]:
    """Validate and split the explicitly allowed local Dev database URL.

    The probe deliberately does not accept the application's generic database
    environment variable.  That variable is also used by deployment/runtime
    commands, so silently reusing it would make a read-only diagnostic capable
    of reaching a non-Dev database.  Only loopback, the two repository-owned
    local Dev ports, and the Dev database/user are accepted.
    """
    if not isinstance(database_url, str) or not database_url.strip():
        raise RepairError("local Dev database URL is not configured")
    try:
        parsed = urlsplit(database_url.strip())
        port = parsed.port
    except ValueError as exc:
        raise RepairError("local Dev database URL has an invalid port") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg"}:
        raise RepairError("local Dev migration probe requires a PostgreSQL URL")
    hostname = (parsed.hostname or "").lower()
    if hostname not in DEV_POSTGRES_HOSTS:
        raise RepairError("local Dev database host must be loopback")
    if any(token in hostname for token in FORBIDDEN):
        raise RepairError("production-looking database host is rejected")
    if port not in DEV_POSTGRES_PORTS:
        raise RepairError("local Dev database port is not allowlisted")
    if parsed.query or parsed.fragment:
        raise RepairError("database URL query and fragment are not allowed")
    if unquote(parsed.username or "") != DEV_POSTGRES_USER:
        raise RepairError("local Dev database user is not allowlisted")
    database = unquote(parsed.path.lstrip("/"))
    if database != DEV_POSTGRES_DATABASE:
        raise RepairError("local Dev database name is not allowlisted")
    password = unquote(parsed.password) if parsed.password is not None else None
    return hostname, port, DEV_POSTGRES_USER, database, password


def read_dev_postgres_revision(database_url: str) -> dict[str, object]:
    """Read only Alembic metadata from the explicitly allowed local Dev DB.

    The SQL intentionally selects only ``alembic_version``.  It never reads
    application tables, writes a migration pointer, runs Alembic, or changes a
    volume.  All operational failures are reduced to stable metadata-only
    reason codes so stderr from a client cannot leak credentials, rows, or
    private paths into evidence.
    """
    host, port, user, database, password = _dev_database_connection(database_url)
    child_env = os.environ.copy()
    # Do not let a caller's libpq service, host-address, options, or password
    # file silently replace the validated loopback connection parameters.
    for key in tuple(child_env):
        if key.startswith("PG"):
            child_env.pop(key, None)
    child_env.update(
        {
            "PGHOST": host,
            "PGPORT": str(port),
            "PGUSER": user,
            "PGDATABASE": database,
        }
    )
    if password is None:
        child_env.pop("PGPASSWORD", None)
    else:
        child_env["PGPASSWORD"] = password
    try:
        completed = subprocess.run(
            [
                "psql",
                "--no-psqlrc",
                "--no-password",
                "--tuples-only",
                "--no-align",
                "--quiet",
                "--command",
                ALEMBIC_REVISION_QUERY,
            ],
            env=child_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired, UnicodeError):
        return {
            "status": "blocked",
            "reason_code": "database_unavailable",
            "current_revision": None,
        }
    if completed.returncode != 0:
        return {
            "status": "blocked",
            "reason_code": "database_unavailable",
            "current_revision": None,
        }
    revisions = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not revisions:
        return {
            "status": "blocked",
            "reason_code": "alembic_version_metadata_missing",
            "current_revision": None,
        }
    if any(not MIGRATION_REVISION_RE.fullmatch(revision) for revision in revisions):
        return {
            "status": "blocked",
            "reason_code": "invalid_revision_metadata",
            "current_revision": None,
        }
    if len(revisions) != 1:
        return {
            "status": "blocked",
            "reason_code": "multiple_current_revisions",
            "current_revision": None,
            "revision_count": len(revisions),
        }
    return {
        "status": "pass",
        "reason_code": "current_revision_read",
        "current_revision": revisions[0],
    }


def _metadata_only_database_probe(reason_code: str) -> dict[str, object]:
    return {
        "status": "blocked",
        "reason_code": reason_code,
        "current_revision": None,
    }


def probe(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.target != "dev-existing" and args.database_url:
        raise RepairError("--database-url is only allowed for dev-existing")
    target = target_path(root, args.target)
    sha = source_sha(root)
    heads = code_heads(root)
    database_probe: dict[str, object] | None = None
    if args.target == "dev-existing":
        database_url = args.database_url or os.environ.get("GRAF_DEV_DATABASE_URL")
        if not database_url:
            database_probe = _metadata_only_database_probe("database_not_configured")
        else:
            database_probe = read_dev_postgres_revision(database_url)
        current = database_probe.get("current_revision")
        current = current if isinstance(current, str) else None
    else:
        current = read_current(target)
    boundary = "dev-existing" if args.target == "dev-existing" else "dev-isolated"
    database_probe_pass = database_probe is None or database_probe.get("status") == "pass"
    graph_mismatch = current not in heads or len(heads) != 1
    probe_pass = database_probe_pass and current in heads and len(heads) == 1
    if len(heads) != 1:
        reason = "migration graph has multiple heads; repair remains blocked"
    else:
        reason = "migration head matches code graph" if probe_pass else "target state is absent or outside the code graph"
    if database_probe is not None and database_probe.get("status") != "pass":
        reason = "local Dev Postgres metadata probe is blocked; no migration mutation performed"
    result = {
        "schema_version": 1,
        "operation_id": "probe-" + uuid.uuid4().hex,
        "source_sha": sha,
        "target": args.target,
        "current_revision": current,
        "code_heads": heads,
        "graph_mismatch": graph_mismatch,
        "boundary": boundary,
        "schema_fingerprint": schema_fingerprint(target),
        "created_at": now(),
        "status": "pass" if probe_pass else "blocked",
        "reason": reason,
    }
    if database_probe is not None:
        result["database_probe"] = database_probe
    atomic_write(Path(args.output).resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def backup_restore(args: argparse.Namespace) -> int:
    root = repo_root()
    source = target_path(root, args.source)
    target = target_path(root, args.target)
    sha = source_sha(root)
    source_digest = schema_fingerprint(source)
    result: dict[str, object] = {
        "schema_version": 1,
        "operation_id": "restore-" + uuid.uuid4().hex,
        "source_sha": sha,
        "source_target": args.source,
        "restore_target": args.target,
        "source_fingerprint": source_digest,
        "restored_fingerprint": None,
        "backup_digest": source_digest,
        "boundary": "dev-isolated",
        "created_at": now(),
        "status": "blocked",
        "reason": "isolated source metadata is missing; no database mutation performed",
    }
    if source.exists():
        data = load_json(source)
        if any(key in data for key in ("rows", "transcript", "raw_audio", "credentials")):
            raise RepairError("source metadata contains prohibited data fields")
        atomic_write(target, data)
        result["restored_fingerprint"] = schema_fingerprint(target)
        if result["restored_fingerprint"] == source_digest:
            result["status"] = "pass"
            result["reason"] = "isolated metadata backup and restore fingerprints match"
        else:
            result["reason"] = "restored metadata fingerprint differs from source"
    atomic_write(Path(args.output).resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def decision(args: argparse.Namespace) -> int:
    probe_record = load_json(Path(args.probe).resolve())
    restore_record = load_json(Path(args.restore).resolve())
    status = "ready" if probe_record.get("status") == "pass" and restore_record.get("status") == "pass" else "blocked"
    result = {
        "schema_version": 1,
        "decision_id": "decision-" + uuid.uuid4().hex,
        "owner": args.owner or "",
        "reason": args.reason or "",
        "affected_boundary": probe_record.get("boundary", "rejected"),
        "backup_evidence": str(Path(args.restore).resolve()),
        "rollback_target": "isolated-restore",
        "abort_conditions": ["source SHA changes", "backup fingerprint changes", "reviewer approval is absent"],
        "approved_by": None,
        "approved_at": None,
        "target_sha": probe_record.get("source_sha"),
        "status": status,
        "created_at": now(),
    }
    if status == "ready":
        result["status"] = "blocked"
        result["reason"] = "decision is prepared but reviewer approval is required before repair"
    else:
        result["reason"] = "probe or restore rehearsal is not passing"
    atomic_write(Path(args.output).resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def repair(args: argparse.Namespace) -> int:
    record = load_json(Path(args.decision).resolve())
    result = {
        "schema_version": 1,
        "operation_id": "repair-" + uuid.uuid4().hex,
        "decision_id": record.get("decision_id"),
        "source_sha": record.get("target_sha"),
        "boundary": record.get("affected_boundary", "rejected"),
        "status": "blocked",
        "reason": "reviewer approval is required; no migration command was executed",
        "created_at": now(),
        "upgrade_runs": [],
    }
    atomic_write(Path(args.output).resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--target", required=True)
    p_probe.add_argument(
        "--database-url",
        help="explicit loopback Dev PostgreSQL URL; otherwise GRAF_DEV_DATABASE_URL is used for dev-existing",
    )
    p_probe.add_argument("--output", type=Path, required=True)
    p_probe.set_defaults(handler=probe)
    p_restore = sub.add_parser("backup-restore")
    p_restore.add_argument("--source", required=True)
    p_restore.add_argument("--target", required=True)
    p_restore.add_argument("--output", type=Path, required=True)
    p_restore.set_defaults(handler=backup_restore)
    p_decision = sub.add_parser("decision")
    p_decision.add_argument("--probe", type=Path, required=True)
    p_decision.add_argument("--restore", type=Path, required=True)
    p_decision.add_argument("--output", type=Path, required=True)
    p_decision.add_argument("--owner")
    p_decision.add_argument("--reason")
    p_decision.set_defaults(handler=decision)
    p_repair = sub.add_parser("repair")
    p_repair.add_argument("--decision", type=Path, required=True)
    p_repair.add_argument("--output", type=Path, required=True)
    p_repair.set_defaults(handler=repair)
    args = parser.parse_args()
    try:
        return args.handler(args)
    except RepairError as exc:
        print(f"dev-migration-repair: blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
