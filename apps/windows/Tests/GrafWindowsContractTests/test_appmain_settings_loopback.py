"""Run directly with Python; real TLS, synthetic resources, no trust-store changes."""
from contextlib import closing
import hashlib
import http.client
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time


with tempfile.TemporaryDirectory(prefix="graf-settings-loopback-") as directory:
    stage = Path(directory)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    (stage / "fixture-origin.txt").write_text(f"https://localhost:{port}")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
                    "-keyout", str(stage / "key.pem"), "-out", str(stage / "cert.pem")],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    resources = stage / "resources"
    manifest = {}
    for name in ("desktop/settings/account", "desktop/settings/notifications", "desktop/meetings", "api/v1/notifications"):
        file = resources / name
        file.parent.mkdir(parents=True, exist_ok=True)
        body = b"{}" if name.startswith("api/") else b"<!doctype html><title>Synthetic</title>"
        file.write_bytes(body)
        manifest[name] = hashlib.sha256(body).hexdigest()
    (stage / "resources.json").write_text(json.dumps(manifest))
    command = [sys.executable, str(Path(__file__).with_name("AppMainSettingsLoopback.py")), str(stage)]
    server = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 5
        while not (stage / "ready").exists() and server.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (stage / "ready").exists(), "server failed to start"
        context = ssl.create_default_context(cafile=str(stage / "cert.pem"))
        for path, status, mime in (
            ("/desktop/settings", 303, None),
            ("/desktop/settings/account", 200, "text/html; charset=utf-8"),
            ("/desktop/settings/notifications?theme=light", 200, "text/html; charset=utf-8"),
            ("/desktop/meetings", 200, "text/html; charset=utf-8"),
            ("/api/v1/notifications", 200, "application/json"),
            ("/desktop/settings/unknown", 403, None),
            ("/desktop/settings/../settings/account", 403, None),
        ):
            with closing(http.client.HTTPSConnection("localhost", port, context=context, timeout=3)) as client:
                client.request("GET", path)
                response = client.getresponse()
                assert response.status == status, (path, response.status)
                if mime:
                    assert response.getheader("Content-Type") == mime
                if status == 303:
                    assert response.getheader("Location") == "/desktop/settings/account"
                    assert response.read() == b""
                else:
                    response.read()
        with closing(http.client.HTTPSConnection("localhost", port, context=context, timeout=3)) as client:
            client.request("GET", "/desktop/settings/account", headers={"Host": "other.example"})
            assert client.getresponse().status == 403
        with closing(http.client.HTTPSConnection("localhost", port, context=context, timeout=3)) as client:
            client.request("POST", "/desktop/settings/account", body=b"")
            assert client.getresponse().status == 501
        with closing(http.client.HTTPConnection("localhost", port, timeout=3)) as client:
            try:
                client.request("GET", "/desktop/settings/account")
                client.getresponse()
            except (ConnectionError, http.client.HTTPException):
                pass
            else:
                raise AssertionError("plaintext HTTP accepted")
    finally:
        (stage / "stop.request").touch()
        try:
            _, errors = server.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
            server.communicate(timeout=3)
            raise
    assert server.returncode == 0, errors.decode()
    # The generated account page must still be bound to its original content.
    (resources / "desktop/settings/account").write_bytes(b"changed")
    (stage / "ready").unlink()
    drift = subprocess.run(command, capture_output=True, timeout=5)
    assert drift.returncode != 0 and not (stage / "ready").exists(), "resource drift accepted"
    print("PASS: settings redirect, document MIME, allowlist, host binding, TLS and content drift")
