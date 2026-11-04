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
revalidation_scenarios = {"history-revalidation-terminal", "history-revalidation-preheaders", "history-revalidation-before-start"}
revalidation_negative_scenarios = {'history-revalidation-no-anchor', 'history-revalidation-workspace-boundary', 'history-revalidation-token-boundary', 'history-revalidation-epoch-boundary', 'history-revalidation-post', 'history-revalidation-timeout-unknown', 'history-revalidation-timeout-reconfirmed', 'history-revalidation-close'}
if scenario not in revalidation_scenarios | revalidation_negative_scenarios | {"shared-reader-session", "history-get-repeated-url", "history-host-ordinary-back", "initial200", "login400", "email503", "cabinet401", "cabinet503",
                    "login429", "email429", "email-json503", "reselect", "billing401",
                    "meeting401", "transport-reset", "tls-failure", "login-post400",
                    "history-get", "history-post", "history-entry", "history-entry-same-url", "cancel-before-start", "history-host-same-url",
                    "cancel-history-host", "cancel-history-script", "history-same-document",
                    "history-race-native-first", "history-race-script-first", "history-reset",
                    "history-host-get", "history-host-quarantine", "history-pending-read-fence", "history-terminal-held", "history-fresh-login-redirect", "history-reset-stale-readback", "history-reset-account-boundary", "history-account-boundary-redirect-held"}:
    raise SystemExit(2)
meeting_path = "/desktop/meetings/11111111-1111-4111-8111-111111111111"
cabinet_path = "/billing" if scenario == "billing401" else meeting_path if scenario == "meeting401" else "/desktop/meetings"
history_posts = {"history-post", "history-entry", "history-entry-same-url", "history-host-same-url",
                 "cancel-history-script", "history-same-document",
                 "history-race-native-first", "history-race-script-first", "history-reset", "history-host-quarantine", "history-reset-stale-readback", "history-reset-account-boundary", "history-account-boundary-redirect-held"}
history_paths = ("/desktop/meetings", "/desktop/meetings" if scenario in {"history-entry-same-url", "history-host-same-url", "history-race-native-first", "history-race-script-first"} else meeting_path,
                 "/desktop/meetings/33333333-3333-4333-8333-333333333333")
if scenario == "history-host-ordinary-back":
    history_paths = ("/desktop/meetings", "/desktop/settings", "/desktop/shared-with-me")
if scenario == "history-get-repeated-url":
    history_paths = (history_paths[0], history_paths[1], history_paths[0])
# cabinet GET, login GET, email GET, safe login next, unexpected path, non-GET.
shared_path = "/api/v1/cabinet/public-shares/" + "a" * 43
shared_query = "workspace_id=22222222-2222-4222-8222-222222222222"
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

    def hold_negative_response(self):
        (root / "response-held").write_text("NEGATIVE_SETTINGS_BEFORE_HEADERS", encoding="ascii")
        deadline = time.monotonic() + 8  # Existing held-response budget, never a product deadline.
        while not (root / "response-release").exists():
            if (root / "stop.request").exists():
                self.close_connection = True
                return False
            if time.monotonic() >= deadline:
                (root / "response-timeout").write_text("HOLD_TIMEOUT", encoding="ascii")
                self.close_connection = True
                return False
            time.sleep(0.01)
        return True

    def page(self, status, kind, post_accepted=False):
        form = ""
        if kind == "form" or kind == "history-a" or post_accepted or (scenario == "history-revalidation-post" and kind == "revalidation-meetings"):
            post_target = "/desktop/settings/account" if scenario == "history-revalidation-post" else history_paths[1] if scenario in history_posts else "/login"
            submits = scenario == "login-post400" or scenario in history_posts or scenario == "history-revalidation-post"
            method = f" method='POST' action='{post_target}'" if submits else ""
            button_type = "submit" if submits else "button"
            input_value = " value='synthetic-value'" if post_accepted else ""
            form = (f"<form id='synthetic-form'{method} style='width:320px;height:100px'>"
                    f"<label>Synthetic<input id='synthetic-input' name='probe' autocomplete='off'{input_value}></label>"
                    f"<button type='{button_type}'>Synthetic</button></form>")
        # The real product bootstrap emits native_ready. Only a boolean is retained.
        listener = "window.chrome?.webview?.addEventListener('message',e=>{if(e.data?.command==='native_ready'&&typeof e.data.nonce==='string')document.documentElement.dataset.syntheticNativeReady='1';});"
        if scenario == "shared-reader-session":
            listener += "window.chrome.webview.addEventListener('message',e=>{if(e.data?.command==='local_recordings')document.documentElement.dataset.syntheticLocalSeen='1';});"
        accepted = " data-post-accepted='1'" if post_accepted else ""
        identity = ("<meta name='graf-time-user' content='11111111-1111-4111-8111-111111111111'>"
                    "<meta name='graf-workspace' content='22222222-2222-4222-8222-222222222222'>"
                    "<meta name='graf-time-session' content='33333333-3333-4333-8333-333333333333'>"
                    "<meta name='graf-time-preferred' content='UTC'>") if scenario == "initial200" or scenario in revalidation_scenarios or scenario in revalidation_negative_scenarios else ""
        data = ("<!doctype html><html><head><meta charset='utf-8'><title>Synthetic T103</title>"
                f"{identity}"
                "<link rel='icon' href='data:,'></head><body>"
                f"<div id='synthetic-marker' data-kind='{kind}'{accepted}>Synthetic</div>{form}"
                f"<script>{listener}</script></body></html>").encode()
        if kind == "json":
            data = b'{"error":"synthetic-delivery-error"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json" if kind == "json" else "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if scenario == "shared-reader-session":
            token = "synthetic-shared-public-session" if kind == "shared-public" else "synthetic-shared-cabinet-session"
            self.send_header("Set-Cookie", f"__Host-twobrain_rec_owner_session={token}; Path=/; Secure; HttpOnly; SameSite=Lax")
        if scenario in revalidation_scenarios:
            self.send_header("Set-Cookie", "__Host-twobrain_rec_owner_session=synthetic-revalidation-session; Path=/; Secure; HttpOnly; SameSite=Lax")
        if scenario in revalidation_negative_scenarios:
            token = "synthetic-revalidation-session-b" if scenario == "history-revalidation-token-boundary" and kind == "revalidation-settings" else "synthetic-revalidation-session"
            self.send_header("Set-Cookie", f"__Host-twobrain_rec_owner_session={token}; Path=/; Secure; HttpOnly; SameSite=Lax")
        if scenario == "initial200":
            self.send_header("Set-Cookie", "__Host-twobrain_rec_owner_session=synthetic-inventory-session; Path=/; Secure; HttpOnly; SameSite=Lax")
        if scenario in {"history-reset-account-boundary", "history-account-boundary-redirect-held"}:
            self.send_header("Set-Cookie", "__Host-twobrain_rec_owner_session=synthetic-history-session; Path=/; Secure; HttpOnly; SameSite=Lax")
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
        if scenario in revalidation_negative_scenarios:
            valid = path in {cabinet_path, "/desktop/settings/account"} and not parsed.query and not (
                scenario == "history-revalidation-post" and path == "/desktop/settings/account")
            with lock:
                counts[0 if valid else 4] += 1
            if not valid:
                self.page(404, "error")
                return
            if path == "/desktop/settings/account" and scenario == "history-revalidation-timeout-unknown" and not self.hold_negative_response():
                return
            try:
                self.page(200, "revalidation-meetings" if path == cabinet_path else "revalidation-settings")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ssl.SSLEOFError, ssl.SSLZeroReturnError):
                (root / "response-disconnected").write_text("CLIENT_DISCONNECTED", encoding="ascii")
            return
        if scenario in revalidation_scenarios:
            valid = path in {cabinet_path, "/desktop/settings/account"} and not parsed.query
            with lock:
                counts[0 if valid else 4] += 1
            if not valid:
                self.page(404, "error")
                return
            if path == "/desktop/settings/account" and scenario != "history-revalidation-terminal":
                # Existing held-response protocol; no headers until the native witness releases it.
                (root / "response-held").write_text("GET_SETTINGS_BEFORE_HEADERS", encoding="ascii")
                deadline = time.monotonic() + 8
                while not (root / "response-release").exists():
                    if (root / "stop.request").exists():
                        self.close_connection = True
                        return
                    if time.monotonic() >= deadline:
                        (root / "response-timeout").write_text("HOLD_TIMEOUT", encoding="ascii")
                        self.close_connection = True
                        return
                    time.sleep(0.01)
            try:
                self.page(200, "revalidation-meetings" if path == cabinet_path else "revalidation-settings")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ssl.SSLEOFError, ssl.SSLZeroReturnError):
                (root / "response-disconnected").write_text("CLIENT_DISCONNECTED", encoding="ascii")
            return
        if scenario == "shared-reader-session":
            valid = (path == cabinet_path and not parsed.query) or (path == shared_path and parsed.query == shared_query)
            with lock:
                counts[0 if valid else 4] += 1
            self.page(200 if valid else 404, "shared-public" if valid and path == shared_path else "shared-cabinet" if valid else "error")
            return
        if scenario == "history-account-boundary-redirect-held" and path == cabinet_path:
            with lock:
                counts[0] += 1
                hold = counts[0] == 3  # A GET, C GET, then the single public navigate(list).
            if not hold:
                self.page(200, "history-a")  # Initial A or the later ordinary Reload GET.
                return
            if self.headers.get_all("X-GRAF-History-Intent"):
                with lock:
                    counts[4] += 1
                (root / "unexpected-http").write_text("GET list", encoding="ascii")
                self.page(400, "error")
                return
            (root / "response-held").write_text("GET_UNMARKED_BEFORE_HEADERS", encoding="ascii")
            deadline = time.monotonic() + 8
            while True:
                if (root / "stop.request").exists():
                    self.close_connection = True
                    return
                if time.monotonic() >= deadline:
                    (root / "response-timeout").write_text("HOLD_TIMEOUT", encoding="ascii")
                    self.close_connection = True
                    return
                if (root / "response-release").exists():
                    break
                time.sleep(0.01)  # Never hold counts lock or the server shutdown thread.
            if (root / "stop.request").exists():
                self.close_connection = True
                return
            self.close_connection = True
            try:
                self.send_response(302)
                self.send_header("Location", "/login?next=%2Fdesktop%2Fmeetings")
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.flush()
                (root / "response-sent").write_text("302", encoding="ascii")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ssl.SSLEOFError, ssl.SSLZeroReturnError):
                (root / "response-disconnected").write_text("CLIENT_DISCONNECTED", encoding="ascii")
            return
        if scenario == "history-fresh-login-redirect" and path in {history_paths[2], cabinet_path}:
            with lock:
                counts[0] += 1
            if path == history_paths[2]:
                self.page(200, "history-c")
            else:
                self.send_response(302)
                self.send_header("Location", "/login?next=%2Fdesktop%2Fmeetings")
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            return  # /login still uses the ordinary query validation and safe-next counter below.
        if scenario in {"history-get-repeated-url", "history-host-ordinary-back", "history-get", "cancel-before-start", "cancel-history-host", "history-host-get",
                        "history-pending-read-fence", "history-terminal-held"} or scenario in history_posts:
            with lock:
                allowed = path in history_paths and not (scenario in {"history-post", "history-entry",
                                                                   "cancel-history-script", "history-same-document", "history-reset", "history-host-quarantine", "history-reset-stale-readback", "history-reset-account-boundary", "history-account-boundary-redirect-held"} and path == history_paths[1])
                counts[0 if allowed else 4] += 1
            if scenario == "history-account-boundary-redirect-held" and not allowed:
                category = "login" if path == "/login" else "list" if path == cabinet_path else "detail" if path in history_paths else "other"
                (root / "unexpected-http").write_text("GET " + category, encoding="ascii")
            self.page(200 if allowed else 404,
                      "history-" + "abc"[history_paths.index(path)] if allowed else "error")
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
        target = "/desktop/settings/account" if scenario == "history-revalidation-post" else history_paths[1] if scenario in history_posts else "/login"
        if ((scenario == "login-post400" or scenario in history_posts or scenario == "history-revalidation-post") and self.path == target
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
        if scenario == "history-revalidation-post":
            if not valid or not self.hold_negative_response():
                return
            try:
                self.page(200, "revalidation-settings")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ssl.SSLEOFError, ssl.SSLZeroReturnError):
                (root / "response-disconnected").write_text("CLIENT_DISCONNECTED", encoding="ascii")
            return
        self.close_connection = True
        self.page(200 if valid and scenario in history_posts else 400,
                  ("history-b" if scenario in history_posts else "form") if valid else "error",
                  post_accepted=valid)


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
