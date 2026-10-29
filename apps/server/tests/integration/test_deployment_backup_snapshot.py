"""Native PostgreSQL snapshot proof on synthetic data; no production access."""

import asyncio
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

REPO = Path(__file__).parents[4]
SQL = REPO / "infra/scripts/rec-db-backup-inventory.sql"


@pytest.fixture
def snapshot_postgres(request):
    owner = getattr(request, "param", "postgres")
    name = "graf-snapshot-" + uuid.uuid4().hex
    subprocess.run(
        ["docker", "run", "--pull=never", "--rm", "-d", "--network=none", "--name", name,
         "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", "POSTGRES_USER=" + owner,
         "-e", "POSTGRES_DB=postgres", "postgres:17-alpine"],
        check=True, capture_output=True,
    )
    try:
        for _ in range(100):
            if subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", owner],
                              capture_output=True).returncode == 0:
                break
            time.sleep(0.1)
        else:
            pytest.fail("synthetic PostgreSQL not ready")
        subprocess.run(["docker", "exec", name, "createdb", "-U", owner, "twobrain_rec"],
                       check=True, capture_output=True)
        yield name
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", name], check=True, capture_output=True)


def psql(name, sql, database="twobrain_rec", role="postgres"):
    return subprocess.run(
        ["docker", "exec", "-i", name, "psql", "-XqAt", "-v", "ON_ERROR_STOP=1",
         "-U", role, "-d", database], input=sql, text=True, capture_output=True, check=True,
    ).stdout


@pytest.mark.parametrize("bind_snapshot", [True, False])
def test_backup_inventory_and_dump_share_native_snapshot(snapshot_postgres, bind_snapshot):
    name = snapshot_postgres
    psql(name, """
        CREATE ROLE twobrain_rec_app LOGIN;
        CREATE TABLE user_identities(id uuid PRIMARY KEY);
        CREATE TABLE product_activation_milestones(
            id uuid PRIMARY KEY, account_id uuid NOT NULL REFERENCES user_identities(id),
            event_name text NOT NULL, posthog_state text NOT NULL, yandex_state text NOT NULL,
            UNIQUE(account_id,event_name));
        INSERT INTO user_identities VALUES('00000000-0000-0000-0000-000000000001');
        INSERT INTO product_activation_milestones VALUES(
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000001','first_recording_completed',
            'pending','not_requested');
        ALTER TABLE product_activation_milestones ENABLE ROW LEVEL SECURITY;
        ALTER TABLE product_activation_milestones FORCE ROW LEVEL SECURITY;
        CREATE POLICY hide_all ON product_activation_milestones USING(false);
        GRANT SELECT ON product_activation_milestones TO twobrain_rec_app;
    """)
    # Delay the real pg_dump AFTER snapshot export while another connection writes.
    subprocess.run(["docker", "exec", "-i", name, "sh", "-s"], input="""
set -eu
mkdir -m 700 /tmp/twobrain-rec-backup.TEST123 /tmp/snapshot-bin
cat > /tmp/snapshot-bin/pg_dump <<'SH'
#!/bin/sh
touch /tmp/snapshot-exported
while [ ! -e /tmp/snapshot-release ]; do sleep 0.05; done
exec /usr/local/bin/pg_dump "$@"
SH
chmod 700 /tmp/snapshot-bin/pg_dump
""", text=True, check=True, capture_output=True)
    script = SQL.read_text()
    if not bind_snapshot:
        # Negative control: the same interleaving exposes an independent pg_dump snapshot.
        script = script.replace(' --snapshot="$GRAF_DB_SNAPSHOT"', "")
    command = ["docker", "exec", "-i", "-e", "PATH=/tmp/snapshot-bin:/usr/local/bin:/usr/bin:/bin",
               name, "sh", "-c", 'umask 077; exec psql "$@"', "sh", "-XqAt", "-v", "ON_ERROR_STOP=1", "-U", "postgres",
               "-d", "twobrain_rec", "-v", "expected_db=twobrain_rec",
               "-v", "staging=/tmp/twobrain-rec-backup.TEST123", "-v", "capture_dump=true"]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        process.stdin.write(script)
        process.stdin.close()
        process.stdin = None
        for _ in range(100):
            if subprocess.run(["docker", "exec", name, "test", "-e", "/tmp/snapshot-exported"],
                              capture_output=True).returncode == 0:
                break
            time.sleep(0.05)
        else:
            pytest.fail("native dump did not reach the snapshot barrier")
        psql(name, "INSERT INTO user_identities VALUES('00000000-0000-0000-0000-000000000003')")
    finally:
        subprocess.run(["docker", "exec", name, "touch", "/tmp/snapshot-release"], check=True)
        output, error = process.communicate(timeout=30)
    assert process.returncode == 0, error
    assert output == ""
    base = "/tmp/twobrain-rec-backup.TEST123"
    rows = [json.loads(line) for line in subprocess.check_output(
        ["docker", "exec", name, "cat", base + "/inventory.jsonl"], text=True).splitlines()]
    counts = {r["relation"]: r["rows"] for r in rows if r["kind"] == "count"}
    assert counts["public.user_identities"] == 1  # the current DB already has two
    assert int(psql(name, "SELECT count(*) FROM user_identities")) == 2
    assert int(psql(name, "SELECT count(*) FROM product_activation_milestones",
                    role="twobrain_rec_app")) == 0
    assert counts["public.product_activation_milestones"] == 1  # no hidden RLS rows
    assert any(r["kind"] == "activation_states" and r["rows"] == 1
               and r["posthog_state"] == "pending" for r in rows)
    subprocess.run(["docker", "exec", name, "createdb", "-U", "postgres", "restored"],
                   check=True, capture_output=True)
    subprocess.run(["docker", "exec", name, "pg_restore", "--exit-on-error", "-U", "postgres",
                    "-d", "restored", base + "/postgres.dump"], check=True, capture_output=True)
    restored_count = int(psql(name, "SELECT count(*) FROM user_identities", database="restored"))
    assert (restored_count == counts["public.user_identities"]) is bind_snapshot
    subprocess.run(["docker", "exec", "-w", base, name, "sha256sum", "-c", "checksums.sha256"],
                   check=True, capture_output=True)
    modes = subprocess.check_output(
        ["docker", "exec", name, "sh", "-c", 'stat -c "%a" "$1"/*', "sh", base], text=True)
    assert modes.splitlines() == ["600"] * 4


@pytest.mark.parametrize("failure", ["wrong-database", "rls-role", "dump", "schema"])
def test_native_snapshot_refuses_incomplete_or_untrusted_capture(snapshot_postgres, failure):
    name = snapshot_postgres
    psql(name, """
        CREATE ROLE limited LOGIN;
        CREATE TABLE product_activation_milestones(posthog_state text, yandex_state text);
        ALTER TABLE product_activation_milestones ENABLE ROW LEVEL SECURITY;
        ALTER TABLE product_activation_milestones FORCE ROW LEVEL SECURITY;
        GRANT SELECT ON product_activation_milestones TO limited;
    """)
    subprocess.run(["docker", "exec", name, "mkdir", "-m", "700",
                    "/tmp/twobrain-rec-backup.TEST123"], check=True)
    if failure in {"dump", "schema"}:
        subprocess.run(["docker", "exec", "-i", name, "sh", "-s"], input=f"""
mkdir /tmp/snapshot-bin
cat > /tmp/snapshot-bin/pg_dump <<'SH'
#!/bin/sh
case " $* " in *--schema-only*) phase=schema ;; *) phase=dump ;; esac
[ "$phase" != "{failure}" ] || exit 7
exec /usr/local/bin/pg_dump "$@"
SH
chmod 700 /tmp/snapshot-bin/pg_dump
""", text=True, check=True)
    result = subprocess.run(
        ["docker", "exec", "-i", "-e", "PATH=/tmp/snapshot-bin:/usr/local/bin:/usr/bin:/bin",
         name, "sh", "-c", 'umask 077; exec psql "$@"', "sh", "-XqAt", "-v", "ON_ERROR_STOP=1",
         "-U", "limited" if failure == "rls-role" else "postgres", "-d", "twobrain_rec",
         "-v", "expected_db=" + ("other" if failure == "wrong-database" else "twobrain_rec"),
         "-v", "staging=/tmp/twobrain-rec-backup.TEST123", "-v", "capture_dump=true"],
        input=SQL.read_text(), text=True, capture_output=True, timeout=30,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert subprocess.run(["docker", "exec", name, "test", "-e",
                           "/tmp/twobrain-rec-backup.TEST123/checksums.sha256"]).returncode != 0


def capture(name, database, destination, *, dump):
    staging = "/tmp/twobrain-rec-backup." + uuid.uuid4().hex
    subprocess.run(["docker", "exec", name, "mkdir", "-m", "700", staging],
                   check=True, capture_output=True)
    try:
        subprocess.run(
            ["docker", "exec", "-i", name, "sh", "-c", 'umask 077; exec psql "$@"', "sh",
             "-XqAt", "-v", "ON_ERROR_STOP=1", "-U", "twobrain_rec", "-d", database,
             "-v", "expected_db=" + database, "-v", "staging=" + staging,
             "-v", "capture_dump=" + str(dump).lower()],
            input=SQL.read_text(), text=True, capture_output=True, check=True, timeout=30,
        )
        destination.mkdir(mode=0o700, exist_ok=True)
        for artifact in (("postgres.dump", "checksums.sha256") if dump else ()) + (
                "schema.sql", "inventory.jsonl"):
            subprocess.run(["docker", "cp", f"{name}:{staging}/{artifact}", str(destination / artifact)],
                           check=True, capture_output=True)
            (destination / artifact).chmod(0o600)
    finally:
        subprocess.run(["docker", "exec", name, "rm", "-rf", staging], check=True, capture_output=True)


@pytest.mark.parametrize("snapshot_postgres", ["twobrain_rec"], indirect=True)
def test_full_migrated_database_restore_comparison(
    snapshot_postgres, postgres_isolated_cluster_database_url, tmp_path, monkeypatch,
):
    from sqlalchemy.engine import make_url

    url = make_url(postgres_isolated_cluster_database_url)
    assert url.database.startswith("twobrain_rec_test_")
    suffix = url.database.removeprefix("twobrain_rec_test_")
    assert len(suffix) == 32 and all(c in "0123456789abcdef" for c in suffix)
    source = "graf-postgres-test-bootstrap-" + suffix
    bootstrap_path = REPO / "apps/server/scripts/bootstrap_runtime_database_roles.py"
    spec = importlib.util.spec_from_file_location("restore_runtime_bootstrap", bootstrap_path)
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    monkeypatch.setenv("TWOBRAIN_DB_HOST", url.host)
    monkeypatch.setenv("TWOBRAIN_DB_PORT", str(url.port))
    monkeypatch.setenv("TWOBRAIN_DB_NAME", url.database)
    for role in ("OWNER", "APP", "MAINTENANCE", "MEDIA"):
        secret = tmp_path / role
        secret.write_text(url.password if role == "OWNER" else uuid.uuid4().hex)
        secret.chmod(0o600)
        monkeypatch.setenv("TWOBRAIN_DB_" + role + "_PASSWORD_FILE", str(secret))
    asyncio.run(bootstrap._bootstrap())  # SOURCE only: never repair the restore before comparing.
    psql(source, f'ALTER DATABASE "{url.database}" RENAME TO twobrain_rec',
         database="postgres", role="twobrain_rec")
    psql(source, """
        INSERT INTO organizations(id,slug,name) VALUES
          ('00000000-0000-0000-0000-000000000001','synthetic','Synthetic');
        INSERT INTO user_identities(id,organization_id,external_subject,locale,theme,status) VALUES
          ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','synthetic','ru-RU','system','active'),
          ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','other','ru-RU','system','active');
        INSERT INTO product_activation_milestones
          (id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind,posthog_state,yandex_state)
        VALUES ('00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002',
          'first_recording_completed','00000000-0000-0000-0000-000000000005',now(),now(),'{}','server','pending','submitted');
    """, role="twobrain_rec")
    reference = tmp_path / "reference"
    capture(source, "twobrain_rec", reference, dump=True)
    target = snapshot_postgres
    for role in ("app", "maintenance", "media"):
        # Only role attributes: schema/ACL must come from the real dump.
        psql(target, f"CREATE ROLE twobrain_rec_{role} LOGIN NOINHERIT; "
             f"ALTER ROLE twobrain_rec_{role} SET row_security=on", role="twobrain_rec")
    database = "rec_restore_rehearsal_" + uuid.uuid4().hex
    psql(target, f'CREATE DATABASE "{database}"', database="postgres", role="twobrain_rec")
    with (reference / "postgres.dump").open("rb") as stream:
        subprocess.run(["docker", "exec", "-i", target, "pg_restore", "--exit-on-error",
                        "-U", "twobrain_rec", "-d", database], stdin=stream,
                       check=True, capture_output=True, timeout=30)
    restored = tmp_path / "restored"
    capture(target, database, restored, dump=False)
    schema_database = "rec_restore_schema_" + uuid.uuid4().hex
    psql(target, f'CREATE DATABASE "{schema_database}"', database="postgres", role="twobrain_rec")
    psql(target, (reference / "schema.sql").read_text(), database=schema_database, role="twobrain_rec")
    canonical = tmp_path / "canonical"
    capture(target, schema_database, canonical, dump=False)
    result = subprocess.run([sys.executable, str(REPO / "infra/scripts/rec-db-verify.py"),
                             str(reference), str(restored), database, str(canonical), schema_database],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    command = result.args
    # A release backs up BEFORE migrating: its next checkout must accept that point.
    checkout = tmp_path / "next-checkout"
    verifier_path = checkout / "infra/scripts/rec-db-verify.py"
    verifier_path.parent.mkdir(parents=True)
    shutil.copyfile(command[1], verifier_path)
    migrations_relative = Path("apps/server/src/twobrain_rec_server/db/migrations/versions")
    shutil.copytree(REPO / migrations_relative, checkout / migrations_relative)
    next_migration = checkout / migrations_relative / "t113_next.py"
    next_migration.write_text("revision = 't113_next'\ndown_revision = '0106_activation_milestones'\n")
    next_command = [command[0], str(verifier_path), *command[2:]]
    preflight = next_command[:3] + ["--inventory"]
    assert subprocess.run(preflight, capture_output=True).returncode == 0
    assert subprocess.run(next_command, capture_output=True).returncode == 0
    # Different supported markers must not pass source/restore comparison.
    psql(target, "UPDATE alembic_version SET version_num='t113_next'", database=database, role="twobrain_rec")
    capture(target, database, restored, dump=False)
    next_spec = importlib.util.spec_from_file_location("next_restore_verifier", verifier_path)
    next_verifier = importlib.util.module_from_spec(next_spec)
    next_spec.loader.exec_module(next_verifier)
    next_verifier.inventory(restored, database)  # Valid alone; only the source/restore mismatch fails.
    assert subprocess.run(next_command, capture_output=True).returncode != 0
    psql(target, "UPDATE alembic_version SET version_num='0106_activation_milestones'", database=database, role="twobrain_rec")
    capture(target, database, restored, dump=False)
    assert subprocess.run(next_command, capture_output=True).returncode == 0
    # Broken checkout histories fail closed, without executing migration code.
    valid_migration = next_migration.read_text()
    for history in (
        "revision='t113_next'\ndown_revision='missing'\n",
        "revision='t113_next'\ndown_revision='t113_next'\n",
        "revision='0106_activation_milestones'\ndown_revision='0105_anonymous_aggregate_region'\n",
        "revision='t113_next'\ndown_revision=('0106_activation_milestones','0105_anonymous_aggregate_region')\n",
    ):
        next_migration.write_text(history)
        assert subprocess.run(preflight, capture_output=True, timeout=5).returncode != 0, history
    next_migration.write_text(valid_migration)
    other_migration = next_migration.with_name("t113_other.py")
    other_migration.write_text("revision='t113_other'\ndown_revision='0106_activation_milestones'\n")
    assert subprocess.run(preflight, capture_output=True, timeout=5).returncode != 0
    other_migration.unlink()
    assert subprocess.run(preflight, capture_output=True).returncode == 0
    # Causal preflight cases: bad metadata must fail before any Docker/resource call.
    invalid = tmp_path / "invalid"
    sentinel_bin = tmp_path / "sentinel-bin"
    sentinel_bin.mkdir()
    sentinel = sentinel_bin / "docker"
    sentinel.write_text('#!/bin/sh\ntouch "$RESTORE_TEST_DOCKER_SENTINEL"\nexit 99\n')
    sentinel.chmod(0o700)
    (invalid.parent / "called-docker").unlink(missing_ok=True)
    for defect in ("missing", "empty", "symlink", "hardlink", "checksum", "extra-manifest", "duplicate-manifest",
                   "malformed-json", "duplicate-json-key", "duplicate-row", "unknown-kind", "unknown-field",
                   "missing-field", "missing-count", "old-version", "wrong-db", "wrong-role", "wrong-head",
                   "missing-revision", "multiple-revisions", "pre-ledger-revision",
                   "state-count", "open-role", "missing-setting", "bad-policy", "bad-check"):
        if invalid.exists():
            shutil.rmtree(invalid)
        shutil.copytree(reference, invalid)
        (invalid / "minio-objects").mkdir()
        inventory_file = invalid / "inventory.jsonl"
        rows = [json.loads(line) for line in inventory_file.read_text().splitlines()]
        if defect in {"missing", "empty", "symlink", "hardlink", "checksum"}:
            artifact = invalid / "postgres.dump"
            if defect == "missing":
                artifact.unlink()
            elif defect == "empty":
                artifact.write_bytes(b"")
            elif defect == "checksum":
                artifact.write_bytes(b"corrupt")
            else:
                artifact.unlink()
                if defect == "symlink":
                    artifact.symlink_to(reference / "postgres.dump")
                else:
                    os.link(reference / "postgres.dump", artifact)
        elif defect in {"extra-manifest", "duplicate-manifest"}:
            manifest = invalid / "checksums.sha256"
            manifest.write_text(manifest.read_text() + manifest.read_text().splitlines()[0] + "\n")
        else:
            if defect == "duplicate-row":
                rows.append(rows[-1])
            elif defect == "unknown-kind":
                rows[-1]["kind"] = "unknown"
            elif defect == "unknown-field":
                rows[-1]["unexpected"] = True
            elif defect == "missing-field":
                rows[-1].pop("rows")
            elif defect == "missing-count":
                rows = [r for r in rows if r.get("relation") != "public.organizations"]
            elif defect == "old-version":
                rows[0]["format_version"] = 1
            elif defect == "wrong-db":
                rows[0]["database"] = "other"
            elif defect == "wrong-role":
                rows[0]["role"] = "twobrain_rec_app"
            elif defect == "wrong-head":
                next(r for r in rows if r["kind"] == "revision")["name"] = "unknown"
            elif defect == "missing-revision":
                rows = [r for r in rows if r["kind"] != "revision"]
            elif defect == "multiple-revisions":
                rows.append({"kind": "revision", "name": "t113_next"})
            elif defect == "pre-ledger-revision":
                next(r for r in rows if r["kind"] == "revision")["name"] = "0105_anonymous_aggregate_region"
            elif defect == "state-count":
                rows[-1]["rows"] += 1
            elif defect == "open-role":
                next(r for r in rows if r.get("name") == "twobrain_rec_app")["bypass_rls"] = True
            elif defect == "missing-setting":
                rows = [r for r in rows if r["kind"] != "role_setting"]
            elif defect == "bad-policy":
                next(r for r in rows if r.get("name") == "activation_account_isolation")["using"] = "true"
            elif defect == "bad-check":
                next(r for r in rows if r.get("name") == "ck_product_activation_milestones_activation_event")["definition"] = "CHECK (true)"
            content = "\n".join(json.dumps(r) for r in rows) + "\n"
            if defect == "malformed-json":
                content = "{invalid\n"
            elif defect == "duplicate-json-key":
                content = content.replace('"kind": "snapshot"', '"kind": "snapshot", "kind": "snapshot"', 1)
            inventory_file.write_text(content)
            (invalid / "checksums.sha256").write_text("".join(
                hashlib.sha256((invalid / name).read_bytes()).hexdigest() + "  " + name + "\n"
                for name in ("postgres.dump", "schema.sql", "inventory.jsonl")))
        blocked = subprocess.run([str(REPO / "infra/scripts/rehearse-rec-restore.sh"), "--execute"],
                                 env={"PATH": str(sentinel_bin) + os.pathsep + os.environ["PATH"],
                                      "RESTORE_BACKUP_REFERENCE": str(invalid),
                                      "RESTORE_TEST_DOCKER_SENTINEL": str(tmp_path / "called-docker")},
                                 capture_output=True, text=True)
        assert blocked.returncode != 0 and "restore_rehearsal_result=pass" not in blocked.stdout, defect
        assert not (tmp_path / "called-docker").exists(), defect
        if defect == "hardlink":
            (invalid / "postgres.dump").unlink()
    table = "product_activation_milestones"
    # Each mutation starts from the same real backup. No bootstrap/repair grants.
    mutations = [
        "DELETE FROM product_activation_milestones",
        "INSERT INTO organizations(id,slug,name) VALUES(gen_random_uuid(),'extra','Extra')",
        "UPDATE product_activation_milestones SET posthog_state='ambiguous'",
        "UPDATE product_activation_milestones SET yandex_state='confirmed'",
        "ALTER TABLE organizations ADD COLUMN unexpected text",
        "ALTER TABLE product_activation_milestones NO FORCE ROW LEVEL SECURITY",
        "DROP POLICY activation_account_isolation ON product_activation_milestones",
        "ALTER POLICY activation_account_isolation ON product_activation_milestones USING(true) WITH CHECK(true)",
        "CREATE POLICY extra_open ON product_activation_milestones USING(true)",
        "ALTER TABLE product_activation_milestones DISABLE TRIGGER activation_decision_immutable",
        "DROP TRIGGER activation_decision_immutable ON product_activation_milestones",
        "ALTER TABLE product_activation_milestones DROP CONSTRAINT uq_activation_account_event",
        "UPDATE pg_index SET indisvalid=false WHERE indexrelid='uq_activation_account_event'::regclass",
        "ALTER TABLE product_activation_milestones DROP CONSTRAINT fk_product_activation_milestones_account_id_user_identities",
        "ALTER TABLE product_activation_milestones DROP CONSTRAINT ck_product_activation_milestones_activation_source; "
        "ALTER TABLE product_activation_milestones ADD CONSTRAINT ck_product_activation_milestones_activation_source "
        "CHECK(source_kind IN ('browser','desktop','server')) NOT VALID",
        "ALTER TABLE product_activation_milestones DROP CONSTRAINT ck_product_activation_milestones_activation_event; "
        "ALTER TABLE product_activation_milestones ADD CONSTRAINT ck_product_activation_milestones_activation_event CHECK(true)",
        "ALTER TABLE product_activation_milestones DROP CONSTRAINT ck_product_activation_milestones_activation_event; "
        "ALTER TABLE product_activation_milestones ADD CONSTRAINT ck_product_activation_milestones_activation_event "
        "CHECK(event_name IN ('desktop_account_connected','desktop_autorecord_enabled','first_recording_completed','first_result_viewed','first_value_session_completed','extra'))",
        "CREATE OR REPLACE FUNCTION rec_activation_decision_immutable() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END$$",
        "GRANT SELECT ON product_activation_milestones TO PUBLIC",
        "REVOKE UPDATE ON product_activation_milestones FROM twobrain_rec_app",
        "GRANT UPDATE ON product_activation_milestones TO twobrain_rec_media",
        "REVOKE SELECT(plan_snapshot) ON billing_invoices FROM twobrain_rec_media",
        "GRANT SELECT ON organizations TO twobrain_rec_app WITH GRANT OPTION",
        "ALTER TABLE product_activation_milestones ALTER COLUMN account_id DROP NOT NULL",
        "ALTER TABLE product_activation_milestones SET UNLOGGED",
        "ALTER TABLE product_activation_milestones ALTER COLUMN source_kind TYPE text",
        "ALTER TABLE product_activation_milestones ALTER COLUMN posthog_state SET DEFAULT 'pending'",
        "GRANT SELECT(account_id) ON product_activation_milestones TO PUBLIC",
        "GRANT TRUNCATE ON product_activation_milestones TO twobrain_rec_media",
        "GRANT MAINTAIN ON product_activation_milestones TO twobrain_rec_app WITH GRANT OPTION",
        "GRANT SELECT ON product_activation_milestones TO twobrain_rec_app WITH GRANT OPTION",
    ]
    def reset_target():
        psql(target, f'DROP DATABASE "{database}"; CREATE DATABASE "{database}"',
             database="postgres", role="twobrain_rec")
        with (reference / "postgres.dump").open("rb") as stream:
            subprocess.run(["docker", "exec", "-i", target, "pg_restore", "--exit-on-error",
                            "-U", "twobrain_rec", "-d", database], stdin=stream,
                           check=True, capture_output=True, timeout=30)

    for mutation in mutations:
        reset_target()
        psql(target, mutation, database=database, role="twobrain_rec")
        capture(target, database, restored, dump=False)
        failed = subprocess.run(command, capture_output=True, text=True)
        assert failed.returncode != 0 and failed.stderr == "postgres_verification=failed\n", mutation
        # Positive source invariants must also reject an identically broken pair.
        if any(word in mutation for word in ("POLICY", "CHECK(true)", "DISABLE TRIGGER", "CHECK(event_name", "NOT VALID", "REPLACE FUNCTION", "indisvalid", "DROP NOT NULL", "UNLOGGED", "TYPE text", "SET DEFAULT", "SELECT(account_id)", "TRUNCATE", "MAINTAIN", "milestones TO twobrain_rec_app WITH GRANT")):
            verifier_spec = importlib.util.spec_from_file_location("restore_verifier", command[1])
            verifier = importlib.util.module_from_spec(verifier_spec)
            verifier_spec.loader.exec_module(verifier)
            with pytest.raises((ValueError, KeyError)):
                verifier.inventory(restored, database)

    reset_target()
    for change, undo in (
        ("ALTER ROLE twobrain_rec_app SUPERUSER", "ALTER ROLE twobrain_rec_app NOSUPERUSER"),
        ("ALTER ROLE twobrain_rec_app BYPASSRLS", "ALTER ROLE twobrain_rec_app NOBYPASSRLS"),
        ("ALTER ROLE twobrain_rec_app INHERIT", "ALTER ROLE twobrain_rec_app NOINHERIT"),
        ("ALTER ROLE twobrain_rec_app SET row_security=off", "ALTER ROLE twobrain_rec_app SET row_security=on"),
        ("GRANT twobrain_rec_media TO twobrain_rec_app", "REVOKE twobrain_rec_media FROM twobrain_rec_app"),
    ):
        psql(target, change, database=database, role="twobrain_rec")
        try:
            capture(target, database, restored, dump=False)
            assert subprocess.run(command, capture_output=True).returncode != 0, change
            with pytest.raises(ValueError):
                verifier.inventory(restored, database)
        finally:
            psql(target, undo, database=database, role="twobrain_rec")

    # Restore a valid target for actual constraint errors and real LOGIN RLS proof.
    reset_target()
    insert = f"INSERT INTO {table}(id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind) "
    values = "SELECT gen_random_uuid(),account_id,event_name,gen_random_uuid(),occurred_at,accepted_at,safe_payload,source_kind FROM " + table
    probes = [
        (insert + values, "23505"),
        (insert + values.replace("account_id,event_name,gen_random_uuid()", "account_id,'first_result_viewed',event_id"), "23505"),
        (insert + values.replace("account_id,event_name,gen_random_uuid()", "gen_random_uuid(),'first_result_viewed',gen_random_uuid()"), "23503"),
        (f"UPDATE {table} SET safe_payload='{{\"changed\":true}}'", "P0001"),
    ]
    for statement, code in probes:
        error = subprocess.run(["docker", "exec", "-i", target, "psql", "-XqAt", "-U", "twobrain_rec",
                                "-d", database, "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose"],
                               input=statement, text=True, capture_output=True)
        assert error.returncode != 0 and f"ERROR:  {code}:" in error.stderr
    for user, expected in (("00000000-0000-0000-0000-000000000002", "1"),
                           ("00000000-0000-0000-0000-000000000003", "0")):
        assert psql(target, "SET app.context_kind='request'; SET app.user_id='" + user + "'; "
                    f"SELECT count(*) FROM {table}", database=database, role="twobrain_rec_app").strip() == expected
    assert psql(target, "SET app.context_kind='maintenance'; SET app.maintenance_actor='synthetic'; "
                "SET app.maintenance_reason='synthetic'; SET app.maintenance_feature_area='product_analytics'; "
                "SET app.maintenance_operation='activation_milestone_delivery'; "
                f"SELECT count(*) FROM {table}", database=database, role="twobrain_rec_maintenance").strip() == "1"
    psql(target, "CREATE ROLE unrelated_public LOGIN", database=database, role="twobrain_rec")
    with pytest.raises(subprocess.CalledProcessError) as denied:
        psql(target, f"SELECT count(*) FROM {table}", database=database, role="unrelated_public")
    assert "permission denied" in denied.value.stderr
