"""Native PostgreSQL snapshot proof on synthetic data; no production access."""

import json
import subprocess
import time
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).parents[4]
SQL = REPO / "infra/scripts/rec-db-backup-inventory.sql"


@pytest.fixture
def snapshot_postgres():
    name = "graf-snapshot-" + uuid.uuid4().hex
    subprocess.run(
        ["docker", "run", "--pull=never", "--rm", "-d", "--network=none", "--name", name,
         "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "postgres:17-alpine"],
        check=True, capture_output=True,
    )
    try:
        for _ in range(100):
            if subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
                              capture_output=True).returncode == 0:
                break
            time.sleep(0.1)
        else:
            pytest.fail("synthetic PostgreSQL not ready")
        subprocess.run(["docker", "exec", name, "createdb", "-U", "postgres", "twobrain_rec"],
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
