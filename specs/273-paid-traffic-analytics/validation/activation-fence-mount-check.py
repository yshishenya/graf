"""Real Linux bind mounts; only a newly owned synthetic volume and containers."""

import hashlib
import json
import selectors
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

source = Path(sys.argv[1]).resolve(strict=True)
token = uuid4().hex
volume = "graf-fence-proof-" + token
label = "org.2brain.graf.test-owner=" + token
image = subprocess.run(["docker", "image", "inspect", "python:3.12-slim", "--format", "{{.Id}}"],
                       capture_output=True, text=True, check=True, timeout=30).stdout.strip()
owned = False
readers = []
facts = {}


def docker(*args, script=None):
    return subprocess.run(["docker", *args], input=script, capture_output=True, text=True,
                          check=True, timeout=30).stdout.strip()


def command(mount):
    return ["run", "--rm", "-i", "--pull=never", "--network=none", "--read-only",
            "--cap-drop=ALL", "--label", label, "--mount", mount,
            "--mount", f"type=bind,src={source},dst=/code/activation_fence.py,readonly",
            "--env", "PYTHONDONTWRITEBYTECODE=1", image, "python", "-u"]


prefix = """
import json,os,sys,hashlib,stat
from pathlib import Path
from datetime import UTC,datetime
sys.path.insert(0,'/code')
from activation_fence import activation_fence,ActivationHold,READY_FIELDS,DIGEST_FIELDS
expected=dict(source_sha='a'*40,image_id='sha256:'+'b'*64,cluster_id='123',
              db_name='synthetic',db_oid=123,schema_revision='0106_activation_milestones')
"""


def writer(script):
    return docker(*command(f"type=volume,src={volume},dst=/outer"), "-c", prefix + script)


def line(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        if not selector.select(timeout=15):
            raise RuntimeError("synthetic_reader_timeout")
    value = process.stdout.readline().strip()
    assert value, "synthetic_reader_failed"
    return value


def reader(mount, path, *, negative_control=False, reopen=False):
    name = "graf-fence-reader-" + uuid4().hex
    code = prefix + f"""
path=Path({path!r})
try:
 with activation_fence(path,owner_uid=0,readonly={not negative_control!r}) as fence:
  fence.read_ready(expected=expected)
  print('ready',flush=True)
  sys.stdin.readline()
  if not {reopen!r}:
   try:
    fence.read_ready(expected=expected)
    print('still_ready',flush=True)
   except ActivationHold as error: print(str(error),flush=True)
except ActivationHold as error: print(str(error),flush=True)
if {reopen!r}:
 print('released',flush=True)
 sys.stdin.readline()
 try:
  with activation_fence(path,owner_uid=0) as fence:
   fence.read_ready(expected=expected)
   print('unexpected_ready',flush=True)
 except ActivationHold as error: print(str(error),flush=True)
"""
    process = subprocess.Popen(["docker", *command(mount)[:1], "--name", name,
                                *command(mount)[1:], "-c", code],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    readers.append((name, process))
    return process


try:
    assert docker("volume", "create", "--label", label, volume) == volume
    owned = True
    root = docker("volume", "inspect", volume, "--format", "{{.Mountpoint}}")
    assert root.startswith("/"), "synthetic_mountpoint_invalid"
    writer("""
os.chmod('/outer',0o700)
for name in ('direct','supported','atomic'):
 d=Path('/outer')/name; d.mkdir(mode=0o700)
 def save(p,obj):
  p.write_bytes(obj if isinstance(obj,bytes) else json.dumps(obj).encode()); p.chmod(0o600)
 save(d/'activation.lock',b'permanent')
 info=(d/'activation.lock').stat(); now=datetime.now(UTC).isoformat()
 initial=dict(version=1,started_at=now,lock_dev=info.st_dev,lock_ino=info.st_ino,
              history_proof_sha256='c'*64)
 save(d/'initial.json',initial)
 save(d/'activation.lock',dict(version=1,state='attempted',initial_sha256=hashlib.sha256(
  (d/'initial.json').read_bytes()).hexdigest()))
 record=dict.fromkeys(READY_FIELDS); record.update({k:'c'*64 for k in DIGEST_FIELDS})
 record.update(expected); record.update(initial)
 record.update(status='ready',mode='local_only',reason='verified',verified_at=now,
  backup_finished_at=now,restore_verified_at=now,retention_verified_at=now,resource_verified_at=now,
  initial_receipt_sha256=hashlib.sha256((d/'initial.json').read_bytes()).hexdigest())
 save(d/'state.json',record)
""")
    direct = f"type=bind,src={root}/direct,dst=/state,readonly"
    refused = reader(direct, "/state/state.json")
    assert line(refused) == "activation_direct_mount"
    assert refused.wait(timeout=15) == 0
    facts["direct_bind_rejected"] = True
    for name, mount, path, negative, expected in (
        ("direct", direct, "/state/state.json", True, "still_ready"),
        ("supported", f"type=bind,src={root},dst=/outer,readonly",
         "/outer/supported/state.json", False, "activation_directory_changed"),
    ):
        process = reader(mount, path, negative_control=negative)
        assert line(process) == "ready"
        writer(f"""
d=Path('/outer/{name}'); d.rename('/outer/{name}-retired'); d.mkdir(mode=0o700)
(d/'activation.lock').write_bytes(b'replacement'); (d/'activation.lock').chmod(0o600)
with activation_fence(d/'state.json',owner_uid=0,exclusive=True) as fence: fence.revoke()
""")
        process.stdin.write("continue\n")
        process.stdin.flush()
        assert line(process) == expected
        assert process.wait(timeout=15) == 0
        facts[name + "_replacement"] = "negative_control_stale" if negative else "hold"
    process = reader(f"type=bind,src={root},dst=/outer,readonly", "/outer/atomic/state.json",
                     reopen=True)
    assert line(process) == "ready"
    process.stdin.write("release\n")
    process.stdin.flush()
    assert line(process) == "released"
    writer("""
p=Path('/outer/atomic/state.json'); inode=(p.parent/'activation.lock').stat().st_ino
with activation_fence(p,owner_uid=0,exclusive=True) as fence: fence.revoke()
assert (p.parent/'activation.lock').stat().st_ino == inode
""")
    process.stdin.write("reopen\n")
    process.stdin.flush()
    assert line(process) == "activation_not_ready"
    assert process.wait(timeout=15) == 0
    facts["atomic_revoke_visible_same_lock"] = True
finally:
    for name, process in readers:
        if process.poll() is None:
            info = json.loads(docker("inspect", name))[0]
            assert info["Config"]["Labels"].get("org.2brain.graf.test-owner") == token
            docker("rm", "--force", name)
            process.communicate(timeout=15)
        else:
            process.communicate(timeout=15)
    if owned:
        info = json.loads(docker("volume", "inspect", volume))[0]
        assert info["Labels"].get("org.2brain.graf.test-owner") == token
        assert docker("volume", "rm", volume) == volume
        facts["owned_volume_removed"] = True

print(json.dumps({"result":"pass", "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                  "image_id":image, "facts":facts},sort_keys=True))
