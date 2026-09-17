"""Opt-in real restore rehearsal, isolated Docker resources, no installed app.

Run with GRAF_SCHEMA_PREVIOUS_MANIFEST and GRAF_SCHEMA_TARGET_MANIFEST pointing
at immutable Dev image manifests. Only their pinned images are read.
"""
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import pytest
from test_dev_schema_transition import h, ROOT


@pytest.mark.skipif(not os.environ.get("GRAF_SCHEMA_TARGET_MANIFEST"), reason="explicit immutable image manifests required for Docker restore rehearsal")
def test_real_postgres_temporal_minio_cold_pair(tmp_path, monkeypatch):
    previous = json.loads(Path(os.environ["GRAF_SCHEMA_PREVIOUS_MANIFEST"]).read_text())
    target = json.loads(Path(os.environ["GRAF_SCHEMA_TARGET_MANIFEST"]).read_text())
    for manifest in (previous, target):
        h._validate_manifest(manifest)
    name = "graf-schema-fixture-" + uuid.uuid4().hex[:12]
    label = "pro.2brain.graf.schema-fixture=" + name
    pg, storage, temporal = (name + suffix for suffix in ("-pg", "-minio", "-temporal"))
    volumes = {name + "-postgres-data": {}, name + "-minio-data": {}}
    created_containers = []
    created_volumes = []
    network_created = False
    def docker(*args):
        result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise AssertionError("isolated Docker operation failed: " + args[0])
        return result.stdout.strip()
    def image(manifest, key):
        digest = manifest["components"][key]["digest"]
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
        assert docker("image", "inspect", "--format", "{{.Id}}", digest) == digest
        return digest
    images = {k: image(target, k) for k in ("database", "storage", "temporal", "migration")}
    old_migration = image(previous, "migration")
    def run_container(container, key, *args):
        docker("run", "-d", "--name", container, "--label", label, "--network", name, *args, images[key], *({"storage": ["server", "/data"]}.get(key, [])))
        created_containers.append(container)
    def sql(statement, db="twobrain_rec"):
        return docker("exec", pg, "psql", "-U", "twobrain_rec", "-d", db, "-At", "-v", "ON_ERROR_STOP=1", "-c", statement)
    def ready_pg():
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                if sql("SELECT 1") == "1": return
            except AssertionError: pass
            time.sleep(1)
        pytest.fail("isolated PostgreSQL readiness failed")
    def python(code, migration=None):
        return docker("run", "--rm", "--label", label, "--network", name, "--entrypoint", "python", migration or images["migration"], "-c", code)
    def migrate(migration):
        docker("run", "--rm", "--label", label, "--network", name, "-e", f"TWOBRAIN_DATABASE_URL=postgresql+asyncpg://twobrain_rec:twobrain_rec@{pg}:5432/twobrain_rec", "--entrypoint", "alembic", migration, "upgrade", "head")
    def temporal_command(*args):
        return docker("exec", temporal, "tctl", "--address", "127.0.0.1:7233", *args)
    client = f"""from minio import Minio
from io import BytesIO
c=Minio('{storage}:9000',access_key='fixture-user',secret_key='fixture-password',secure=False)
"""
    def cold():
        docker("stop", "--time", "60", temporal, pg, storage)
        for container in created_containers:
            assert docker("inspect", "--format", "{{.State.Running}}", container) == "false"
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    journal = {"operation_id": "upgrade-1", "target": target, "volumes": volumes, "snapshots": {}}
    backup = tmp_path / "schema-transactions" / "upgrade-1"
    backup.mkdir(parents=True, mode=0o700)
    try:
        docker("network", "create", "--internal", "--label", label, name); network_created = True
        for volume in volumes:
            docker("volume", "create", "--label", label, volume); created_volumes.append(volume)
        run_container(pg, "database", "-e", "POSTGRES_USER=twobrain_rec", "-e", "POSTGRES_PASSWORD=twobrain_rec", "-e", "POSTGRES_DB=twobrain_rec", "--mount", f"type=volume,src={next(iter(volumes))},dst=/var/lib/postgresql/data")
        run_container(storage, "storage", "-e", "MINIO_ROOT_USER=fixture-user", "-e", "MINIO_ROOT_PASSWORD=fixture-password", "--mount", f"type=volume,src={list(volumes)[1]},dst=/data")
        ready_pg(); migrate(old_migration)
        assert sql("SELECT version_num FROM alembic_version") == previous["migration_head"]
        sql("CREATE TABLE schema_restore_probe (id int PRIMARY KEY, value text); INSERT INTO schema_restore_probe VALUES (1, 'before')")
        run_container(temporal, "temporal", "-e", "DB=postgres12", "-e", "DB_PORT=5432", "-e", "BIND_ON_IP=0.0.0.0", "-e", f"POSTGRES_SEEDS={pg}", "-e", "POSTGRES_USER=twobrain_rec", "-e", "POSTGRES_PWD=twobrain_rec", "-e", "DBNAME=temporal", "-e", "VISIBILITY_DBNAME=temporal_visibility")
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            try:
                temporal_command("--namespace", "fixture-before", "namespace", "register", "--retention", "1")
                break
            except AssertionError: time.sleep(2)
        else: pytest.fail("isolated Temporal namespace creation failed")
        python(client + "c.make_bucket('fixture'); c.put_object('fixture','control',BytesIO(b'before'),6,metadata={'probe':'before'})")
        cold()
        for volume in volumes:
            journal["snapshots"][volume] = adapter._schema_volume_tool(journal, volume, "snapshot")
        # A corrupted archive must fail before extraction.
        archive = backup / (list(volumes)[1] + ".tar")
        with archive.open("r+b") as f:
            first = f.read(1); f.seek(0); f.write(bytes([first[0] ^ 1]))
        with pytest.raises(h.HarnessError): adapter._schema_volume_tool(journal, list(volumes)[1], "verify")
        with archive.open("r+b") as f: f.write(first)
        docker("start", pg, storage); ready_pg(); migrate(images["migration"])
        assert sql("SELECT version_num FROM alembic_version") == target["migration_head"]
        sql("UPDATE schema_restore_probe SET value='after'; INSERT INTO schema_restore_probe VALUES (2,'new')")
        python(client + "c.put_object('fixture','control',BytesIO(b'after'),5,metadata={'probe':'after'}); c.put_object('fixture','new',BytesIO(b'new'),3)")
        cold()
        # Use the production pair helper; replace only identity policy with fixture ownership.
        def check(j):
            for volume in volumes:
                assert json.loads(docker('volume','inspect',volume))[0]['Labels'].get('pro.2brain.graf.schema-fixture') == name
                assert not docker('ps','-q','--filter','volume='+volume)
        monkeypatch.setattr(adapter, "_schema_check_volumes", check)
        monkeypatch.setattr(adapter, "_schema_phase", lambda j, phase: j.update(phase=phase))
        adapter._schema_restore_pair(journal)
        docker("start", pg, storage); ready_pg()
        assert sql("SELECT version_num FROM alembic_version") == previous["migration_head"]
        assert sql("SELECT id::text || ':' || value FROM schema_restore_probe ORDER BY id") == "1:before"
        python(client + "assert c.get_object('fixture','control').read()==b'before'; assert c.stat_object('fixture','control').metadata['x-amz-meta-probe']=='before'; assert [o.object_name for o in c.list_objects('fixture')]==['control']")
        docker("start", temporal)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                temporal_command("--namespace", "fixture-before", "namespace", "describe"); break
            except AssertionError: time.sleep(2)
        else: pytest.fail("restored Temporal namespace unavailable")
    finally:
        for container in reversed(created_containers):
            with contextlib.suppress(Exception):
                labels = json.loads(docker("inspect", container))[0]["Config"]["Labels"]
                if labels.get("pro.2brain.graf.schema-fixture") == name: docker("rm", "-f", container)
        for volume in created_volumes:
            labels = json.loads(docker("volume", "inspect", volume))[0]["Labels"]
            assert labels.get("pro.2brain.graf.schema-fixture") == name
            docker("volume", "rm", volume)
        if network_created:
            assert json.loads(docker("network", "inspect", name))[0]["Labels"].get("pro.2brain.graf.schema-fixture") == name
            docker("network", "rm", name)
