"""Temporary synthetic T103 server: no auth, cookies, payment or external calls."""
import http.server
import pathlib
import socket
import ssl
import sys
import threading
import time
import urllib.parse

root = pathlib.Path(sys.argv[1])
scenario = sys.argv[2]
port = int(sys.argv[3])
if scenario not in {"initial200", "login400", "email503", "cabinet401", "cabinet503",
                    "login429", "email429", "email-json503", "reselect", "billing401",
                    "meeting401", "transport-reset", "tls-failure", "login-post400"}:
    raise SystemExit(2)
meeting_path = "/desktop/meetings/11111111-1111-4111-8111-111111111111"
cabinet_path = "/billing" if scenario == "billing401" else meeting_path if scenario == "meeting401" else "/desktop/meetings"
# cabinet GET, login GET, email GET, safe login next, unexpected path, non-GET.
counts = [0] * 6
lock = threading.Lock()


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(1)

    def log_message(self, *_):
        pass

    def parse_request(self):
        if not super().parse_request():
            return False
        if self.command != "GET":
            with lock:
                counts[5] += 1
        return True

    def page(self, status, kind, post_accepted=False):
        form = ""
        if kind == "form":
            method = " method='POST' action='/login'" if scenario == "login-post400" else ""
            button_type = "submit" if scenario == "login-post400" else "button"
            input_value = " value='synthetic-value'" if post_accepted else ""
            form = (f"<form id='synthetic-form'{method} style='width:320px;height:100px'>"
                    f"<label>Synthetic<input id='synthetic-input' name='probe' autocomplete='off'{input_value}></label>"
                    f"<button type='{button_type}'>Synthetic</button></form>")
        # The real product bootstrap emits native_ready. Only a boolean is retained.
        listener = "window.chrome?.webview?.addEventListener('message',e=>{if(e.data?.command==='native_ready'&&typeof e.data.nonce==='string')document.documentElement.dataset.syntheticNativeReady='1';});"
        accepted = " data-post-accepted='1'" if post_accepted else ""
        data = ("<!doctype html><html><head><meta charset='utf-8'><title>Synthetic T103</title>"
                "<link rel='icon' href='data:,'></head><body>"
                f"<div id='synthetic-marker' data-kind='{kind}'{accepted}>Synthetic</div>{form}"
                f"<script>{listener}</script></body></html>").encode()
        if kind == "json":
            data = b'{"error":"synthetic-delivery-error"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json" if kind == "json" else "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if scenario == "reselect" and status == 503 and kind == "form":
            self.send_header("X-GRAF-Cabinet-Recovery", "reselect-space")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        with lock:
            if path == cabinet_path:
                counts[0] += 1
                status = 401 if scenario in {"cabinet401", "billing401", "meeting401"} else 503 if scenario == "cabinet503" else 200
                kind = "cabinet" if status == 200 else "error"
            elif path == "/login":
                counts[1] += 1
                if urllib.parse.parse_qs(parsed.query, keep_blank_values=True) == {"next": [cabinet_path]}:
                    counts[3] += 1
                status, kind = (400 if scenario == "login400" else 429 if scenario == "login429" else 200), "form"
            elif path == "/desktop/settings/account/email-link/start" and scenario in {"email503", "email429", "email-json503", "reselect"}:
                counts[2] += 1
                status = 429 if scenario == "email429" else 503
                kind = "json" if scenario == "email-json503" else "form"
            else:
                counts[4] += 1
                status, kind = 404, "error"
        if scenario == "transport-reset" and path == "/login":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        self.page(status, kind)

    def do_POST(self):
        valid = False
        lengths = self.headers.get_all("Content-Length", [])
        if (scenario == "login-post400" and self.path == "/login"
                and not self.headers.get("Transfer-Encoding") and len(lengths) == 1
                and lengths[0].isascii() and lengths[0].isdecimal()
                and len(lengths[0]) <= 3 and 0 < int(lengths[0]) <= 256):
            length = int(lengths[0])
            try:
                body = self.rfile.read(length)
                valid = len(body) == length and urllib.parse.parse_qs(
                    body.decode("ascii"), keep_blank_values=True,
                    strict_parsing=True, max_num_fields=2) == {"probe": ["synthetic-value"]}
            except (OSError, UnicodeError, ValueError):
                pass
        if not valid:
            with lock:
                counts[4] += 1
        self.close_connection = True
        self.page(400, "form" if valid else "error", post_accepted=valid)


server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
server.daemon_threads = False
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(root / "cert.pem", root / "key.pem")
server.socket = context.wrap_socket(server.socket, server_side=True)


def stop_requested():
    while not (root / "stop.request").exists():
        time.sleep(0.01)
    server.shutdown()


threading.Thread(target=stop_requested, daemon=True).start()
(root / "ready").write_text("ready", encoding="ascii")
try:
    server.serve_forever(poll_interval=0.05)
finally:
    server.server_close()  # joins request writers; no live receipt reader exists
with lock:
    (root / "final-counts.txt").write_text(" ".join(map(str, counts)), encoding="ascii")
