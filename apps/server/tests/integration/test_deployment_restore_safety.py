"""Execute rehearsal shells with synthetic Docker/MinIO; never contact a server."""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parents[4]
DOCKER = r"""#!/usr/bin/env python3
import os,pathlib,subprocess,sys
root=pathlib.Path(os.environ['RESTORE_TEST_ROOT']); a=sys.argv[1:]
failure=os.environ.get('RESTORE_TEST_FAILURE','')
for stage in root.glob('graf-rec-restore.*'):
 if stage.stat().st_mode & 0o777 != 0o700:sys.exit(9)
 log=stage/'commands.log'
 if log.exists() and log.stat().st_mode & 0o777 != 0o600:sys.exit(9)
with (root/'calls').open('a') as log:log.write(repr(a)+'\n')
if a[0]=='compose' and 'ps' in a:print('synthetic-postgres');sys.exit(0)
if a[0]=='compose' and 'exec' in a:
 cmd=a[a.index('rec-postgres')+1:]; tool=cmd[0]
 if tool=='createdb':
  if failure=='createdb':
   (root/'foreign-db').write_text(cmd[-1]);sys.exit(7)
  (root/'owned-db').write_text(cmd[-1]);sys.exit(0)
 if tool=='dropdb':
  if failure=='database-cleanup':sys.exit(7)
  target=root/('owned-db' if (root/'owned-db').exists() else 'foreign-db')
  target.unlink();sys.exit(0)
 if tool=='pg_restore':
  sys.stdin.buffer.read();sys.exit(7 if failure=='restore' else 0)
 if tool=='psql':
  print('1' if (root/'owned-db').exists() else '0');sys.exit(0)
 sys.exit(8)
if a[0]=='run':
 cmd=a[a.index('-c')+1]
 for flag_index,value in enumerate(a):
  if value=='-v':
   mount=a[flag_index+1]; source,dest,*_=mount.split(':')
   cmd=cmd.replace(dest,source)
 os.umask(0o022)
 sys.exit(subprocess.call(['sh','-c',cmd]))
sys.exit(8)
"""
MC = r"""#!/usr/bin/env python3
import json,os,pathlib,sys
root=pathlib.Path(os.environ['RESTORE_TEST_ROOT']);a=sys.argv[1:]
failure=os.environ.get('RESTORE_TEST_FAILURE','')
if a[0]=='alias':sys.exit(0)
if a[0]=='mb':
 if failure=='bucket-create':
  (root/'foreign-bucket').write_text(a[-1]);sys.exit(0 if '--ignore-existing' in a else 7)
 (root/'owned-bucket').write_text(a[-1]);sys.exit(0)
if a[0]=='mirror':
 if os.environ.get('RESTORE_TEST_WAIT'):
  import time
  (root/'mirror-started').touch()
  deadline=time.monotonic()+10
  while not (root/'mirror-release').exists():
   if time.monotonic()>deadline:sys.exit(7)
   time.sleep(0.01)
 sys.exit(7 if failure=='mirror' else 0)
if a[0]=='rb':
 if failure=='bucket-cleanup':sys.exit(7)
 target=root/('owned-bucket' if (root/'owned-bucket').exists() else 'foreign-bucket')
 target.unlink();sys.exit(0)
if a[0]=='ls':
 if failure=='bucket-readback':sys.exit(7)
 if (root/'owned-bucket').exists():print(json.dumps({'key':(root/'owned-bucket').read_text().split('/')[-1]+'/'}))
 sys.exit(0)
sys.exit(8)
"""


@pytest.fixture
def restore_env(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, text in [("docker", DOCKER), ("mc", MC)]:
        p = bindir / name
        p.write_text(text)
        p.chmod(0o700)
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "postgres.dump").write_bytes(b"synthetic database")
    (backup / "minio-objects").mkdir()
    for name in ["user", "password", "unrelated"]:
        (tmp_path / name).write_text("synthetic")
    return {
        **os.environ,
        "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
        "RESTORE_TEST_ROOT": str(tmp_path),
        "RESTORE_BACKUP_REFERENCE": str(backup),
        "GRAF_RELEASE_MC_IMAGE": "synthetic-mc",
        "TWOBRAIN_MINIO_ROOT_USER_FILE": str(tmp_path / "user"),
        "TWOBRAIN_MINIO_ROOT_PASSWORD_FILE": str(tmp_path / "password"),
        "TMPDIR": str(tmp_path),
    }


def rehearsal(env):
    return subprocess.run(
        [str(REPO / "infra/scripts/rehearse-rec-restore.sh"), "--execute"],
        cwd=env["RESTORE_TEST_ROOT"],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )


def test_restore_cleans_only_confirmed_own_targets_before_pass(restore_env):
    root = Path(restore_env["RESTORE_TEST_ROOT"])
    r = rehearsal(restore_env)
    assert r.returncode == 0, r.stderr
    assert "restore_rehearsal_result=pass" in r.stdout
    assert not (root / "owned-db").exists() and not (root / "owned-bucket").exists()
    assert not list(root.glob("graf-rec-restore.*"))
    assert (root / "unrelated").read_text() == "synthetic"
    assert "['cp'," not in (root / "calls").read_text()  # No shared container dump.


@pytest.mark.parametrize(
    "failure",
    [
        "createdb",
        "restore",
        "bucket-create",
        "mirror",
        "database-cleanup",
        "bucket-cleanup",
        "bucket-readback",
    ],
)
def test_restore_failure_never_passes_and_never_deletes_unowned_target(restore_env, failure):
    root = Path(restore_env["RESTORE_TEST_ROOT"])
    r = rehearsal({**restore_env, "RESTORE_TEST_FAILURE": failure})
    assert r.returncode != 0
    assert "restore_rehearsal_result=pass" not in r.stdout
    calls = (root / "calls").read_text()
    if failure == "createdb":
        assert "'dropdb'" not in calls
        assert (root / "foreign-db").exists()
    if failure == "bucket-create":
        assert "mc rb " not in calls
        assert (root / "foreign-bucket").exists()
    if failure not in ["database-cleanup", "bucket-cleanup", "bucket-readback"]:
        assert not (root / "owned-db").exists() and not (root / "owned-bucket").exists()
    assert (root / "unrelated").read_text() == "synthetic"
    assert not list(root.glob("graf-rec-restore.*"))


@pytest.mark.parametrize(
    "kind", ["missing", "empty", "dump-link", "objects-link", "reference-link"]
)
def test_restore_rejects_incomplete_explicit_copy_before_docker(restore_env, kind):
    root = Path(restore_env["RESTORE_TEST_ROOT"])
    dump = root / "backup/postgres.dump"
    if kind in ["missing", "empty", "dump-link"]:
        dump.unlink()
        if kind == "empty":
            dump.touch()
        if kind == "dump-link":
            dump.symlink_to(root / "unrelated")
    elif kind == "objects-link":
        (root / "backup/minio-objects").rmdir()
        (root / "foreign-objects").mkdir()
        (root / "backup/minio-objects").symlink_to(
            root / "foreign-objects", target_is_directory=True
        )
    else:
        (root / "backup").rename(root / "foreign-backup")
        (root / "backup").symlink_to(root / "foreign-backup", target_is_directory=True)
    r = rehearsal(restore_env)
    assert r.returncode != 0 and "restore_rehearsal_result=pass" not in r.stdout
    assert not (root / "calls").exists()


def test_scheduled_restore_selects_only_complete_dated_graf_copies(restore_env):
    root = Path(restore_env["RESTORE_TEST_ROOT"])
    copies = root / "backups"
    copies.mkdir()
    for name in ["20261027T010101Z", "20261028T010101Z", "nginx-edge-20990101T010101Z"]:
        p = copies / name
        p.mkdir()
        (p / "postgres.dump").write_bytes(b"synthetic")
        (p / "minio-objects").mkdir()
    (copies / "20990101T010101Z").mkdir()  # Later incomplete directory.
    link = copies / "20990101T020202Z"
    link.symlink_to(copies / "20261028T010101Z", target_is_directory=True)
    ssh = root / "bin/ssh"
    ssh.write_text("""#!/usr/bin/env python3
import os,pathlib,subprocess,sys
command=sys.argv[-1]
if 'python3 -' in command:
 sys.exit(subprocess.call(['sh','-c',command]))
pathlib.Path(os.environ['RESTORE_TEST_ROOT'],'selected-command').write_text(command)
print('restore_rehearsal_result=pass')
""")
    ssh.chmod(0o700)
    env = {**restore_env, "TWOBRAIN_DEPLOY_HOST": "synthetic", "TWOBRAIN_DEPLOY_PATH": str(root)}
    env.pop("RESTORE_BACKUP_REFERENCE", None)
    r = subprocess.run(
        [str(REPO / "infra/scripts/rehearse-restore-scheduled.sh"), "--execute"],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr
    assert str(copies / "20261028T010101Z") in (root / "selected-command").read_text()
    assert "nginx-edge" not in (root / "selected-command").read_text()


def test_restore_rejects_parallel_attempt_under_existing_deploy_lock(restore_env):
    import time

    root = Path(restore_env["RESTORE_TEST_ROOT"])
    first = subprocess.Popen(
        [str(REPO / "infra/scripts/rehearse-rec-restore.sh"), "--execute"],
        cwd=root,
        env={**restore_env, "RESTORE_TEST_WAIT": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 5
        while (
            not (root / "mirror-started").exists()
            and first.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert (root / "mirror-started").exists()
        second = rehearsal(restore_env)
        assert second.returncode != 0
        assert "deployment_or_rehearsal_running" in second.stdout
    finally:
        (root / "mirror-release").touch()
        output, error = first.communicate(timeout=15)
    assert first.returncode == 0, error
    assert "restore_rehearsal_result=pass" in output
    assert not (root / "owned-db").exists() and not (root / "owned-bucket").exists()


@pytest.mark.parametrize("stop", ["terminate", "kill"])
def test_restore_wrapper_stop_keeps_lock_until_child_cleanup(restore_env, stop):
    import time

    root = Path(restore_env["RESTORE_TEST_ROOT"])
    first = subprocess.Popen(
        [str(REPO / "infra/scripts/rehearse-rec-restore.sh"), "--execute"],
        cwd=root,
        env={**restore_env, "RESTORE_TEST_WAIT": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 5
        while (
            not (root / "mirror-started").exists()
            and first.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert (root / "mirror-started").exists()
        getattr(first, stop)()
        if stop == "kill":
            first.wait(timeout=5)
        second = rehearsal(restore_env)
        assert second.returncode != 0
        assert "deployment_or_rehearsal_running" in second.stdout
        assert (root / "owned-db").exists() and (root / "owned-bucket").exists()
    finally:
        (root / "mirror-release").touch()
        output, error = first.communicate(timeout=15)
    assert not (root / "owned-db").exists() and not (root / "owned-bucket").exists()
    assert not list(root.glob("graf-rec-restore.*"))
    if stop == "terminate":
        assert first.returncode != 0
        assert "restore_rehearsal_result=pass" not in output
