"""Real, disposable MinIO/SDK checks with synthetic bytes and read-only mounts."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).parents[4]
CHECKER = REPO / "infra/scripts/rec-object-verify.py"
CLIENT = """
import io, sys
from pathlib import Path
from minio import Minio
import urllib3
c = Minio('rec-minio:9000', region='us-east-1', access_key='synthetic-user',
          secret_key='synthetic-password', secure=False,
          http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=2), retries=False))
b = sys.argv[1]
"""


def docker(*args, check=True, timeout=40):
    return subprocess.run(["docker", *args], text=True, capture_output=True,
                          check=check, timeout=timeout)


@contextmanager
def native(minio_image, sdk_image):
    # Missing images/daemon fail explicitly; this profile never silently skips.
    for image in (minio_image, sdk_image):
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", image), "immutable local image ID required"
        docker("image", "inspect", image)
    root = Path(tempfile.mkdtemp(prefix="graf-object-native-")).resolve()
    root.chmod(0o700)
    source = root / "objects"
    source.mkdir(mode=0o700)
    for name in ("user", "password"):
        (root / name).write_text("synthetic-user" if name == "user" else "synthetic-password")
        (root / name).chmod(0o600)
    token = uuid.uuid4().hex
    network = container = None
    try:
        network = docker("network", "create", "--internal", "--subnet", "10.246.82.0/28",
                         "graf-object-test-" + token).stdout.strip()
        container = docker("create", "--pull", "never", "--network", network,
                           "--network-alias", "rec-minio", "--label", "graf.object-test=" + token,
                           "-e", "MINIO_ROOT_USER=synthetic-user", "-e", "MINIO_ROOT_PASSWORD=synthetic-password",
                           minio_image, "server", "/data").stdout.strip()
        docker("start", container)

        def sdk(code, bucket, check=True):
            return docker("run", "--rm", "--pull", "never", "--network", network,
                          "--user", f"{os.geteuid()}:{os.getegid()}", "--read-only",
                          "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                          "--label", "graf.object-test=" + token,
                          "-v", f"{source}:/source:ro", "--entrypoint", "python", sdk_image,
                          "-c", CLIENT + code, bucket, check=check)

        deadline = time.monotonic() + 30
        while sdk("c.list_buckets()", "unused", check=False).returncode:
            assert time.monotonic() < deadline, "synthetic MinIO startup failed"
            time.sleep(0.2)

        def verify(bucket, manifest):
            return docker("run", "--rm", "--pull", "never", "--network", network,
                          "--user", f"{os.geteuid()}:{os.getegid()}", "--read-only",
                          "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                          "--label", "graf.object-test=" + token,
                          "-v", f"{source}:/source:ro", "-v", f"{manifest}:/manifest:ro",
                          "-v", f"{CHECKER}:/checker.py:ro",
                          "-v", f"{root / 'user'}:/run/secrets/user:ro",
                          "-v", f"{root / 'password'}:/run/secrets/password:ro",
                          "--entrypoint", "python", sdk_image,
                          "/checker.py", "verify", "/source", "/manifest", bucket, check=False)

        yield root, source, sdk, verify, lambda: docker("stop", "--time", "5", container)
    finally:
        own = docker("ps", "-aq", "--filter", "label=graf.object-test=" + token).stdout.split()
        for owned_id in own:
            assert re.fullmatch(r"[0-9a-f]{12,64}", owned_id)
            docker("rm", "-fv", owned_id)
        assert not docker("ps", "-aq", "--filter", "label=graf.object-test=" + token).stdout.strip()
        if network:
            docker("network", "rm", network)
            assert docker("network", "inspect", network, check=False).returncode != 0
        shutil.rmtree(root)
        assert not root.exists()


def check_native_object_readback(native, change):
    root, source, sdk, verify, _ = native
    for item in source.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    if change in {"gzip", "gzip-exact"}:
        import gzip
        (source / "object").write_bytes(gzip.compress(b"A" * 23, mtime=0) if change == "gzip-exact" else b"A" * 23)
        (source / "object").chmod(0o600)
    elif change != "empty":
        (source / "папка с пробелами").mkdir(mode=0o700)
        for key, data in {"папка с пробелами/запись.bin": b"synthetic\x00bytes", "empty": b""}.items():
            (source / key).write_bytes(data)
            (source / key).chmod(0o600)
        if change == "exact":
            # More than one S3 list page; content still well below one megabyte.
            for index in range(1001):
                p = source / f"page-{index:04d}"
                p.write_bytes(b"page")
                p.chmod(0o600)
    manifest = root / (change + ".json")
    snapshot = subprocess.run([sys.executable, str(CHECKER), "snapshot", str(source), str(manifest)],
                              text=True, capture_output=True, timeout=20)
    assert snapshot.returncode == 0, snapshot.stdout + snapshot.stderr
    bucket = "twobrain-rec-restore-rehearsal-" + uuid.uuid4().hex
    sdk("""
c.make_bucket(b)
for p in Path('/source').rglob('*'):
    if p.is_file():
        data = p.read_bytes()
        c.put_object(b, p.relative_to('/source').as_posix(), io.BytesIO(data), len(data))
""", bucket)
    if change in {"gzip", "gzip-exact"}:
        sdk("import gzip; data=gzip.compress(b'A' * 23, mtime=0); assert len(data)==23; c.put_object(b, 'object', io.BytesIO(data), len(data), metadata={'Content-Encoding':'gzip'})", bucket)
    elif change == "same-size":
        sdk("c.put_object(b, 'папка с пробелами/запись.bin', io.BytesIO(b'X' * 15), 15)", bucket)
    elif change == "missing":
        sdk("c.remove_object(b, 'empty')", bucket)
    elif change == "extra":
        sdk("c.put_object(b, 'extra', io.BytesIO(b''), 0)", bucket)
    result = verify(bucket, manifest)
    assert result.returncode == (0 if change in {"exact", "empty", "gzip-exact"} else 1), result.stdout + result.stderr
    assert result.stdout == ("object_restore_result=pass\n" if result.returncode == 0
                             else "object_restore_result=failed\nreason=object_restore_unverified\n")
    assert result.stderr == ""
    # Container bind identities need not equal the host's identities.
    host = subprocess.run([sys.executable, str(CHECKER), "source", str(source), str(manifest)],
                          text=True, capture_output=True, timeout=20)
    assert host.returncode == 0
    sdk("""
for obj in c.list_objects(b, recursive=True):
    c.remove_object(b, obj.object_name)
c.remove_bucket(b)
assert not c.bucket_exists(b)
""", bucket)


def check_sdk_no_retry(sdk):
    sdk("""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import minio, urllib3
assert (minio.__version__, urllib3.__version__) == ('7.2.20', '2.7.0')
class Handler(BaseHTTPRequestHandler):
    calls = 0
    def answer(self):
        type(self).calls += 1
        self.send_response(301 if self.command == 'HEAD' else 503)
        self.send_header('x-amz-bucket-region', 'synthetic-other-region')
        self.send_header('Content-Length', '0')
        self.end_headers()
    do_HEAD = do_GET = answer
    def log_message(self, *args):
        pass
server = HTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    pool = urllib3.PoolManager(timeout=urllib3.Timeout(connect=1, read=1), retries=False)
    c = Minio('127.0.0.1:' + str(server.server_port), secure=False, region='us-east-1',
              access_key='synthetic-user', secret_key='synthetic-password', http_client=pool)
    for action in (c.stat_object, c.get_object):
        Handler.calls = 0
        try:
            action('synthetic-bucket', 'synthetic-object')
        except Exception:
            pass
        else:
            raise AssertionError('failed HTTP request accepted')
        assert Handler.calls == 1, 'SDK silently retried HTTP request'
    pool.clear()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    assert not thread.is_alive()
""", "unused")


def check_network_failure(native):
    root, source, _, verify, stop = native
    manifest = root / "network.json"
    subprocess.run([sys.executable, str(CHECKER), "snapshot", str(source), str(manifest)],
                   check=True, capture_output=True, timeout=20)
    stop()
    result = verify("twobrain-rec-restore-rehearsal-" + uuid.uuid4().hex, manifest)
    assert result.returncode == 1
    assert result.stdout == "object_restore_result=failed\nreason=object_restore_unverified\n"
    assert result.stderr == ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minio-image", required=True)
    parser.add_argument("--sdk-image", required=True)
    args = parser.parse_args()
    with native(args.minio_image, args.sdk_image) as resources:
        for change in ("exact", "empty", "same-size", "missing", "extra", "gzip", "gzip-exact"):
            check_native_object_readback(resources, change)
            print(f"native_object_restore_{change}=pass", flush=True)
        check_sdk_no_retry(resources[2])
        print("native_object_restore_no_retry=pass", flush=True)
        check_network_failure(resources)
        print("native_object_restore_network_failure=pass", flush=True)
    print("native_object_restore_cleanup=pass")


if __name__ == "__main__":
    main()
