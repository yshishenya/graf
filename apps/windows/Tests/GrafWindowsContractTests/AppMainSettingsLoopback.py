"""Serve generated, synthetic cabinet resources over real loopback TLS only."""
import hashlib
import http.server
import json
from pathlib import Path
import ssl
import sys
import threading
import time
from urllib.parse import urlsplit

stage = Path(sys.argv[1]).resolve()
origin = (stage / "fixture-origin.txt").read_text().strip()
url = urlsplit(origin)
assert url.scheme == "https" and url.hostname == "localhost" and 1024 <= url.port <= 65535
resources = stage / "resources"
manifest = json.loads((stage / "resources.json").read_text(encoding="utf-8-sig"))
# Reject drift before exposing even synthetic content.
for name, expected in manifest.items():
    assert hashlib.sha256((resources / name).read_bytes()).hexdigest() == expected
counts = {"served": 0, "denied": 0}
lock = threading.Lock()


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)  # Bound TLS handshake, headers and body writes.
        super().setup()

    def log_message(self, *_):
        pass  # Never log cookies, headers, URLs or page contents.

    def do_GET(self):
        parsed = urlsplit(self.path)
        relative = parsed.path.removeprefix("/")
        allowed = self.headers.get("Host") == url.netloc and not parsed.scheme and not parsed.netloc
        settings_redirect = relative == "desktop/settings" and "desktop/settings/account" in manifest
        allowed = allowed and (relative in manifest or settings_redirect) and ".." not in Path(relative).parts
        with lock:
            counts["served" if allowed else "denied"] += 1
        if not allowed:
            self.send_error(403)
            return
        if settings_redirect:
            # Match the production embedded route, including its redirect status.
            self.send_response(303)
            self.send_header("Location", "/desktop/settings/account")
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        file = resources / relative
        body = file.read_bytes()
        mime = "text/html; charset=utf-8" if relative in ("desktop/settings/notifications", "desktop/settings/account", "desktop/meetings") else (
            "application/json" if not file.suffix else {".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8", ".png": "image/png", ".ico": "image/x-icon"}.get(file.suffix, "application/octet-stream"))
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


server = http.server.ThreadingHTTPServer(("127.0.0.1", url.port), Handler)
server.daemon_threads = False
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_cert_chain(stage / "cert.pem", stage / "key.pem")
server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)


def stop():
    deadline = time.monotonic() + 660
    while not (stage / "stop.request").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    server.shutdown()


threading.Thread(target=stop, daemon=True).start()
(stage / "ready").write_text("127.0.0.1", encoding="ascii")
try:
    server.serve_forever(poll_interval=0.05)
finally:
    server.server_close()
    (stage / "server-counts.json").write_text(json.dumps(counts), encoding="ascii")
