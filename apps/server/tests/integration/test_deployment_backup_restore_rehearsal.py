import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[4]


def _run_script(path: str, *args: str) -> str:
    result = subprocess.run(
        [str(REPO_ROOT / path), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_backup_helper_dry_run_records_remote_target_without_secret_values() -> None:
    output = _run_script("infra/scripts/backup-rec-stack.sh", "--dry-run")

    assert "2brain.dev" in output
    assert "/opt/projects/2brain-rec" in output
    assert "postgres_artifact=postgres.dump" in output
    assert "minio_artifact=minio-objects/" in output
    assert "secret" not in output.lower()


def test_restore_rehearsal_dry_run_blocks_without_backup_reference() -> None:
    output = _run_script("infra/scripts/rehearse-rec-restore.sh", "--dry-run")

    assert "restore_rehearsal_result=blocked" in output
    assert "backup_reference_missing" in output


def test_forward_rehearsal_never_falls_back_when_its_manifest_is_missing(tmp_path):
    (tmp_path / "postgres.dump").write_bytes(b"synthetic")
    (tmp_path / "minio-objects").mkdir()
    script = str(REPO_ROOT / "infra/scripts/rehearse-rec-restore.sh")
    env = {**os.environ, "RESTORE_BACKUP_REFERENCE": str(tmp_path)}
    missing = subprocess.run(
        [script, "--execute", "--forward-attempt", "a" * 32], env=env, text=True, capture_output=True,
    )
    assert missing.returncode == 1
    assert "reason=protected_object_manifest_missing_or_invalid" in missing.stdout
    (tmp_path / "minio-inventory.jsonl").touch()
    ambiguous = subprocess.run([script, "--execute"], env=env, text=True, capture_output=True)
    assert ambiguous.returncode == 1
    assert "reason=forward_attempt_required" in ambiguous.stdout


@pytest.mark.parametrize("failure", [None, "extra-archive", "wrong-marker", "wrong-type", "extra-target"])
def test_protected_restore_rehearsal_matches_exact_object_inventory(tmp_path, failure):
    archive = tmp_path / "minio-objects"
    archive.mkdir()
    key = "with ' space"
    content = b"fixture"
    (archive / key).write_bytes(content)
    attempt = "00000000-0000-0000-0000-000000000001"
    content_type = "text/plain; charset=utf-8"
    manifest = tmp_path / "minio-inventory.jsonl"
    manifest.write_text(
        json.dumps(dict(schema=1, bucket="graf-source", versioning="disabled", incomplete=0))
        + "\n"
        + json.dumps(dict(key=key, size=len(content), sha256=hashlib.sha256(content).hexdigest(),
                          attempt=attempt, content_type=content_type))
        + "\n"
    )
    bucket = "twobrain-rec-restore-rehearsal-" + "a" * 32
    helper = [sys.executable, str(REPO_ROOT / "infra/scripts/verify-rec-object-backup.py")]
    if failure == "extra-archive":
        (archive / "unexpected").touch()
    prepared = subprocess.run(
        [*helper, "--prepare-rehearsal", str(tmp_path.resolve()), str(manifest), bucket],
        text=True, capture_output=True,
    )
    if failure == "extra-archive":
        assert prepared.returncode == 1 and not prepared.stdout
        return
    assert prepared.returncode == 0
    row = dict(
        status="success", type="file", name=f"{bucket}/{key}", size=len(content), etag="fixture",
        metadata={
            "X-Amz-Meta-Graf-Upload-Attempt": attempt if failure != "wrong-marker" else (
                "00000000-0000-0000-0000-000000000002"
            ),
            "Content-Type": content_type if failure != "wrong-type" else "application/octet-stream",
        },
    )
    listing = tmp_path / "restored.jsonl"
    lines = [json.dumps(row)]
    if failure == "extra-target":
        lines.append(json.dumps({**row, "name": f"{bucket}/extra"}))
    listing.write_text("\n".join(lines) + "\n")
    verified = subprocess.run(
        [*helper, "--verify-rehearsal", str(manifest), str(listing), bucket],
        capture_output=True,
    )
    assert verified.returncode == int(failure is not None)


# Execute the real container shell commands on synthetic files, without Docker.
FAKE_DOCKER = r"""#!/usr/bin/env python3
import os, pathlib, shutil, subprocess, sys
a = sys.argv[1:]
root = pathlib.Path(os.environ["BACKUP_TEST_ROOT"])
failure = os.environ.get("BACKUP_TEST_FAILURE", "")
with (root / "docker-calls").open("a") as log:
    log.write(repr(a) + "\n")
if a[0] == "compose" and "ps" in a:
    if failure == "ps": sys.exit(7)
    if failure != "empty-ps": print("synthetic-postgres")
elif a[0] == "exec" or (a[0] == "compose" and "exec" in a):
    command = a[3:] if a[0] == "exec" else a[a.index("rec-postgres") + 1:]
    if failure == "mktemp" and any("mktemp " in x for x in command): sys.exit(7)
    if failure == "staging-invalid" and any("mktemp " in x for x in command):
        print("/tmp/unrelated")
        sys.exit(0)
    if failure == "cleanup" and ("rm" in command or any("rm " in x for x in command)):
        sys.exit(7)
    command = [x.replace("/tmp/", str(root / "tmp") + "/") for x in command]
    os.umask(0o022)  # A container does not inherit the caller's umask.
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE)
    sys.stdout.write(result.stdout.replace(str(root / "tmp") + "/", "/tmp/"))
    sys.exit(result.returncode)
elif a[0] == "cp":
    if failure == "copy": sys.exit(7)
    source = a[1].split(":", 1)[1].replace("/tmp/", str(root / "tmp") + "/")
    shutil.copyfile(source, a[2])
    if failure == "corrupt-copy" and a[2].endswith("/inventory.jsonl"):
        pathlib.Path(a[2]).write_text("corrupt")
    os.chmod(a[2], 0o644)  # Docker may preserve source/tool modes.
elif a[0] == "run":
    if a[a.index("--user") + 1] != f"{os.getuid()}:{os.getgid()}": sys.exit(7)
    if "MC_CONFIG_DIR=/tmp/graf-backup-mc" not in a: sys.exit(7)
    mount, target = next(x.rsplit(":", 1) for x in a if x.endswith((":/backup", ":/backup/minio-objects")))
    command = a[a.index("-c") + 1].replace(target, mount)
    command = command.replace("/run/secrets/twobrain_minio_root_user", str(root / "user"))
    command = command.replace("/run/secrets/twobrain_minio_root_password", str(root / "password"))
    os.umask(0o022)
    env = {**os.environ}
    for index, flag in enumerate(a):
        if flag == "-e":
            key, value = a[index + 1].split("=", 1)
            env[key] = value
    sys.exit(subprocess.call(["bash", "-c", command], env=env))
else:
    sys.exit("unexpected synthetic Docker call")
"""

FAKE_TOOLS = r"""#!/usr/bin/env python3
import hashlib, os, pathlib, subprocess, sys, time
root = pathlib.Path(os.environ["BACKUP_TEST_ROOT"])
failure = os.environ.get("BACKUP_TEST_FAILURE", "")
tool = pathlib.Path(sys.argv[0]).name
a = sys.argv[1:]
if tool in {"find", "chmod"}:
    if tool == "find" and failure == "find": sys.exit(7)
    if tool == "chmod":
        if failure == "chmod-initial": sys.exit(7)
        if failure == "chmod":
            count = root / "chmod-count"
            calls = int(count.read_text()) + 1 if count.exists() else 1
            count.write_text(str(calls))
            if calls > 1: sys.exit(7)
    os.execv(os.environ["BACKUP_REAL_" + tool.upper()], [tool, *a])
mask = os.umask(0)
os.umask(mask)
if tool == "psql":
    script = sys.stdin.read()
    if "pg_export_snapshot()" not in script: sys.exit(7)
    if failure == "snapshot": sys.exit(7)
    target = pathlib.Path(next(x.split("=", 1)[1] for x in a if x.startswith("staging=")))
    subprocess.run(["pg_dump", "--file=" + str(target / "postgres.dump")], check=True)
    (target / "schema.sql").write_text("synthetic schema")
    (target / "inventory.jsonl").write_text('{"kind":"snapshot","format_version":1}\n')
    artifacts = ["postgres.dump", "schema.sql", "inventory.jsonl"]
    (target / "checksums.sha256").write_text("".join(
        hashlib.sha256((target / name).read_bytes()).hexdigest() + "  " + name + "\n"
        for name in artifacts))
    if failure == "empty-inventory": (target / "inventory.jsonl").write_text("")
    sys.exit(0)
if tool == "pg_dump":
    (root / ("pg-mask-" + str(os.getpid()))).write_text(oct(mask))
    target = pathlib.Path(next(x.split("=", 1)[1] for x in a if x.startswith("--file=")))
    target.write_bytes(b"synthetic database")
    (root / ("pg-permissions-" + str(os.getpid()))).write_text(
        oct(target.parent.stat().st_mode & 0o777) + "/" + oct(target.stat().st_mode & 0o777))
    time.sleep(0.1)  # Overlap two real helper executions.
    sys.exit(7 if failure == "dump" else 0)
if tool == "mc" and a[0] == "mirror":
    if failure == "empty-bucket": sys.exit(0)
    (root / ("mc-mask-" + str(os.getpid()))).write_text(oct(mask))
    target = pathlib.Path(a[-1])
    folder = target / "nested"
    folder.mkdir()
    os.chmod(folder, 0o777)
    (folder / "object").write_bytes(b"synthetic xbject" if failure == "same-size" else b"synthetic object")
    os.chmod(folder / "object", 0o666)
    if failure == "symlink": (folder / "link").symlink_to(root / "unrelated")
    if failure == "fifo": os.mkfifo(folder / "fifo")
    if failure == "hardlink": os.link(root / "unrelated", folder / "link")
    sys.exit(7 if failure == "mirror" else 0)
if tool == "mc" and a[:3] == ["--json", "version", "info"]:
    assert a[-1] == "rec/test-ingest"
    print('{"status":"success","versioning":{"status":"Enabled"}}' if failure == "versioned" else
          '{"status":"success","versioning":{"status":""}}')
if tool == "mc" and a[:2] == ["--json", "ls"] and failure == "multipart":
    print('{"status":"success","key":"synthetic-multipart"}')
if tool == "mc" and a[:2] == ["--json", "ls"] and "--incomplete" not in a and failure == "stat-failed":
    print('{"status":"success","key":"existing-object"}')
if tool == "mc" and a[:2] == ["--json", "stat"]:
    if failure in {"empty-bucket", "stat-failed"}: sys.exit(7)
    assert a[-1] == "rec/test-ingest"
    print('{"status":"success","type":"file","name":"test-ingest/nested/object","etag":"test","size":' +
          ('17' if failure == "mismatch" else '16') + ','
          '"metadata":{"X-Amz-Meta-Graf-Upload-Attempt":"41c77879-1c96-45aa-9842-b6d97a88d996"}}')
if tool == "mc" and a[0] == "cat":
    assert a[1] == "rec/test-ingest/nested/object"
    sys.stdout.buffer.write(b"synthetic object")
if tool == "sha256sum":
    print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest() + "  -")
"""


@pytest.fixture
def backup_env(tmp_path: Path) -> dict[str, str]:
    import shutil

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, source in {
        "docker": FAKE_DOCKER,
        **dict.fromkeys(["psql", "pg_dump", "mc", "find", "chmod", "sha256sum"], FAKE_TOOLS),
    }.items():
        executable = bin_dir / name
        executable.write_text(source)
        executable.chmod(0o700)
    (tmp_path / "tmp").mkdir()
    for name in ("user", "password", "unrelated"):
        (tmp_path / name).write_text("synthetic")
    (tmp_path / "tmp" / "unrelated").mkdir()
    return {
        "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
        "BACKUP_TEST_ROOT": str(tmp_path),
        "BACKUP_REAL_FIND": str(shutil.which("find")),
        "BACKUP_REAL_CHMOD": str(shutil.which("chmod")),
        "GRAF_RELEASE_MC_IMAGE": "synthetic-mc",
        "TWOBRAIN_BACKUP_DIR": str(tmp_path / "backups" / "new"),
    }


def _backup(env: dict[str, str], mode: str = "--execute", *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(REPO_ROOT / "infra/scripts/backup-rec-stack.sh"), mode, *extra],
        cwd=env["BACKUP_TEST_ROOT"],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )


def _assert_private(tree: Path) -> None:
    for item in [tree, *tree.rglob("*")]:
        assert stat.S_IMODE(item.lstat().st_mode) == (0o700 if item.is_dir() else 0o600)


def test_backup_executes_private_container_shells_and_cleans_own_staging(backup_env) -> None:
    root = Path(backup_env["BACKUP_TEST_ROOT"])
    result = _backup(backup_env)
    assert result.returncode == 0, result.stderr
    assert "backup_result=pass" in result.stdout
    _assert_private(Path(backup_env["TWOBRAIN_BACKUP_DIR"]))
    for artifact in ("inventory.jsonl", "schema.sql", "checksums.sha256"):
        assert (Path(backup_env["TWOBRAIN_BACKUP_DIR"]) / artifact).is_file()
    for pattern in ("pg-mask-*", "mc-mask-*"):
        masks = list(root.glob(pattern))
        assert len(masks) == 1
        assert masks[0].read_text() == "0o77"
    assert [x.read_text() for x in root.glob("pg-permissions-*")] == ["0o700/0o600"]
    assert list((root / "tmp").iterdir()) == [root / "tmp" / "unrelated"]


def test_forward_backup_reads_the_exact_stores_without_compose_lookup(backup_env) -> None:
    import ast

    root = Path(backup_env["BACKUP_TEST_ROOT"])
    postgres, minio = "1" * 64, "2" * 64
    mc_image = "sha256:" + "3" * 64
    (root / ".env").write_text("GRAF_RELEASE_MC_IMAGE=must-not-replace-the-pin\nTWOBRAIN_MINIO_BUCKET=wrong-bucket\n")
    result = _backup({**backup_env, "GRAF_RELEASE_MC_IMAGE": mc_image}, "--execute",
                     "--pinned-stores", postgres, minio, "test-ingest")
    assert result.returncode == 0, result.stderr
    calls = [ast.literal_eval(line) for line in (root / "docker-calls").read_text().splitlines()]
    assert all(call[0] != "compose" for call in calls)
    assert all(call[2] == postgres for call in calls if call[0] == "exec")
    assert all(call[1].startswith(postgres + ":") for call in calls if call[0] == "cp")
    minio_call = next(call for call in calls if call[0] == "run")
    assert minio_call[minio_call.index("--network") + 1] == "container:" + minio
    assert "GRAF_BACKUP_MINIO_ENDPOINT=http://127.0.0.1:9000" in minio_call
    assert "GRAF_BACKUP_PINNED_BUCKET=test-ingest" in minio_call
    assert mc_image in minio_call and "must-not-replace-the-pin" not in minio_call
    manifest = (Path(backup_env["TWOBRAIN_BACKUP_DIR"]) / "minio-inventory.jsonl").read_text()
    assert "41c77879-1c96-45aa-9842-b6d97a88d996" in manifest


def test_forward_backup_can_attest_a_proven_empty_bucket(backup_env) -> None:
    result = _backup({**backup_env, "GRAF_RELEASE_MC_IMAGE": "sha256:" + "3" * 64,
                      "BACKUP_TEST_FAILURE": "empty-bucket"}, "--execute",
                     "--pinned-stores", "1" * 64, "2" * 64, "test-ingest")
    assert result.returncode == 0, result.stderr
    manifest = Path(backup_env["TWOBRAIN_BACKUP_DIR"]) / "minio-inventory.jsonl"
    assert [json.loads(line) for line in manifest.read_text().splitlines()] == [
        dict(schema=1, bucket="test-ingest", versioning="disabled", incomplete=0),
    ]


@pytest.mark.parametrize("failure", ["versioned", "multipart", "mismatch", "same-size", "stat-failed"])
def test_forward_backup_cannot_attest_an_unsafe_object_copy(backup_env, failure) -> None:
    result = _backup({**backup_env, "GRAF_RELEASE_MC_IMAGE": "sha256:" + "3" * 64,
                      "BACKUP_TEST_FAILURE": failure}, "--execute",
                     "--pinned-stores", "1" * 64, "2" * 64, "test-ingest")
    assert result.returncode != 0
    assert "backup_result=pass" not in result.stdout
    target = Path(backup_env["TWOBRAIN_BACKUP_DIR"])
    assert not (target / "minio-inventory.jsonl").exists()
    assert not list(target.glob(".minio-*"))


def test_backup_clears_inherited_setgid_without_changing_parent(backup_env) -> None:
    target = Path(backup_env["TWOBRAIN_BACKUP_DIR"])
    target.parent.mkdir()
    target.parent.chmod(0o2770)
    before = stat.S_IMODE(target.parent.stat().st_mode)
    result = _backup(backup_env)
    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(target.parent.stat().st_mode) == before
    _assert_private(target)


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling"])
def test_backup_rejects_existing_target_without_changes(backup_env, kind) -> None:
    target = Path(backup_env["TWOBRAIN_BACKUP_DIR"])
    target.parent.mkdir()
    if kind == "directory":
        target.mkdir(mode=0o755)
        (target / "keep").write_bytes(b"keep")
    elif kind == "file":
        target.write_bytes(b"keep")
    else:
        target.symlink_to(target.parent / ("missing" if kind == "dangling" else "keep"))
        if kind == "symlink":
            (target.parent / "keep").mkdir()
    before = target.lstat()
    result = _backup(backup_env)
    assert result.returncode != 0
    assert "backup_result=pass" not in result.stdout
    assert target.lstat() == before
    assert not (Path(backup_env["BACKUP_TEST_ROOT"]) / "docker-calls").exists()
    if kind == "directory":
        assert (target / "keep").read_bytes() == b"keep"
    if kind == "file":
        assert target.read_bytes() == b"keep"


@pytest.mark.parametrize(
    "failure",
    [
        "mktemp",
        "staging-invalid",
        "dump",
        "snapshot",
        "empty-inventory",
        "corrupt-copy",
        "copy",
        "ps",
        "empty-ps",
        "mirror",
        "cleanup",
        "find",
        "chmod",
        "chmod-initial",
        "symlink",
        "fifo",
        "hardlink",
    ],
)
def test_backup_failures_never_pass_or_remove_other_staging(backup_env, failure) -> None:
    root = Path(backup_env["BACKUP_TEST_ROOT"])
    original = (root / "unrelated").stat()
    result = _backup({**backup_env, "BACKUP_TEST_FAILURE": failure})
    assert result.returncode != 0
    assert "backup_result=pass" not in result.stdout
    after = (root / "unrelated").stat()
    assert (after.st_mode, after.st_uid, after.st_gid) == (
        original.st_mode,
        original.st_uid,
        original.st_gid,
    )
    assert (root / "unrelated").read_text() == "synthetic"
    assert (root / "tmp" / "unrelated").is_dir()
    assert stat.S_IMODE(Path(backup_env["TWOBRAIN_BACKUP_DIR"]).stat().st_mode) == 0o700
    if failure != "cleanup":
        assert list((root / "tmp").iterdir()) == [root / "tmp" / "unrelated"]


def test_backup_parallel_runs_use_separate_staging(backup_env) -> None:
    root = Path(backup_env["BACKUP_TEST_ROOT"])
    command = [str(REPO_ROOT / "infra/scripts/backup-rec-stack.sh"), "--execute"]
    processes = [
        subprocess.Popen(
            command,
            cwd=root,
            env={**backup_env, "TWOBRAIN_BACKUP_DIR": str(root / f"copy-{i}")},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for i in range(2)
    ]
    for process in processes:
        output, error = process.communicate(timeout=15)
        assert process.returncode == 0, error
        assert "backup_result=pass" in output
    calls = (root / "docker-calls").read_text().splitlines()
    copies = [line for line in calls if line.startswith("['cp'") and "/postgres.dump'" in line]
    assert len(copies) == 2 and copies[0].split(",")[1] != copies[1].split(",")[1]
    assert list((root / "tmp").iterdir()) == [root / "tmp" / "unrelated"]
    for i in range(2):
        _assert_private(root / f"copy-{i}")


def test_backup_dry_run_has_no_files_or_docker_calls(backup_env) -> None:
    root = Path(backup_env["BACKUP_TEST_ROOT"])
    before = sorted(str(x) for x in root.rglob("*"))
    result = _backup(backup_env, "--dry-run")
    assert result.returncode == 0
    assert "backup_result=dry_run" in result.stdout
    assert sorted(str(x) for x in root.rglob("*")) == before
