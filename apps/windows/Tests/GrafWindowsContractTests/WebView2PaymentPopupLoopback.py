import http.server
import http.cookies
import pathlib
import ssl
import sys
import threading
import time
import urllib.parse

root = pathlib.Path(sys.argv[1])
scenario = sys.argv[2]
port = int(sys.argv[3])
counts = [0] * 14  # POST, return POST, body, opener, bank POST/body/opener, return body, bank GET, return/provider cookies, all payment requests, live/ended frame requests
body = b'fixture=synthetic-payment-body-36byte'
lock = threading.Lock()

def receipt():
    temp = root / 'receipt.tmp'
    try:
        for attempt in range(50):
            try:
                temp.write_text(' '.join(map(str, counts)), encoding='ascii')
                temp.replace(root / 'receipt.txt')
                return
            except PermissionError:
                # Windows can briefly hold a snapshot during inspection or
                # scanning. Retry the same counters, never accept a lost write.
                if attempt == 49:
                    raise
                time.sleep(0.01)
    except OSError:
        print('T102_RECEIPT_FAILURE', file=sys.stderr, flush=True)
        raise

class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_):
        pass

    def parse_request(self):
        if not super().parse_request():
            return False
        # Count before method dispatch: denied scenarios must send no payment
        # request at all, including GET fallback and unsupported HTTP methods.
        path = urllib.parse.urlsplit(self.path).path
        if path in ('/pay', '/bank', '/billing/checkout', '/frame-live', '/frame-after'):
            with lock:
                counts[11] += 1
                if path in ('/frame-live', '/frame-after'):
                    counts[12 if path == '/frame-live' else 13] += 1
                receipt()
        return True

    def page(self, content, *, seed_session=False):
        data = ('<!doctype html><meta charset=utf-8>' + content).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        if seed_session:
            self.send_header('Set-Cookie', 'graf-fixture=synthetic-profile; Path=/; Secure; HttpOnly; SameSite=None')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ('/frame-live', '/frame-after'):
            self.page('<body>synthetic bank frame')
            return
        if path in ('/proof-provider', '/proof-bank'):
            with lock:
                counts[6 if path == '/proof-bank' else 3] = 1
                receipt()
            self.page('ok')
            return
        provider = f'https://api.yookassa.test:{port}/pay'
        form = f"function submit(target,url='{provider}'){{let f=document.createElement('form');f.method='POST';f.action=url;f.target=target;let i=document.createElement('input');i.name='fixture';i.value='synthetic-payment-body-36byte';f.append(i);document.body.append(f);f.submit();}}"
        if path == '/iframe-source':
            self.page(f"<body><script>{form}submit('_blank');</script>")
            return
        if path == '/billing':
            if scenario in ('iframe', 'same-url-iframe'):
                # Exercise distinct URLs as well as a frame indistinguishable by URL.
                frame_url = 'location.href' if scenario == 'same-url-iframe' else "'/iframe-source'"
                self.page(f"<body><script>{form} function runFixture(){{let f=document.createElement('iframe'); f.src={frame_url}; document.body.append(f);}} if(window!==top)submit('_blank');</script>", seed_session=True)
                return
            script = "submit('_blank');"
            if scenario in ('immediate', 'later', 'nested'):
                script = f"window.open('{provider}?holding=1','payment');" + ("setTimeout(()=>submit('payment'),500);" if scenario == 'later' else "submit('payment');")
            if scenario == 'abort-only':
                script = f"const popup=window.open('{provider}?holding=1','payment');popup.stop();"
            self.page(f'<body><script>{form}function runFixture(){{{script}}}</script>', seed_session=True)
            return
        if path == '/bank':
            with lock:
                counts[8] += 1
                receipt()
            if scenario == 'redirect-303':
                self.continue_payment(path)
                return
        if path == '/pay' or path == '/bank':
            self.page('<body>synthetic holding page')
            return
        self.page('<body>synthetic completed')

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        if n > 4096:
            self.send_error(413)
            return
        data = self.rfile.read(n)
        path = urllib.parse.urlsplit(self.path).path
        cookies = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
        def cookie_matches(name):
            return name in cookies and cookies[name].value == 'synthetic-profile'
        with lock:
            if path == '/pay':
                counts[0] += 1
                counts[2] = int(data == body)
                counts[10] = int(cookie_matches('graf-native-fixture'))
            elif path == '/bank':
                counts[4] += 1
                counts[5] = int(data == (body if scenario == 'redirect-307' else b'fixture=synthetic-return'))
            elif path == '/billing/checkout':
                counts[1] += 1
                counts[7] = int(data == b'fixture=synthetic-return')
                counts[9] = int(cookie_matches('graf-fixture'))
            receipt()
        if path == '/pay' and scenario in ('redirect-307', 'redirect-303'):
            self.send_response(307 if scenario == 'redirect-307' else 303)
            self.send_header('Location', f'https://bank.test:{port}/bank')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.continue_payment(path)

    def continue_payment(self, path):
        if path == '/billing/checkout':
            frame = f"<iframe src='https://bank.test:{port}/frame-after'></iframe>" if scenario == 'frame-chain' else ''
            self.page('<body>original return POST completed' + frame)
            return
        expected = '!!window.opener' if scenario in ('immediate', 'later', 'nested') else '!window.opener'
        proof_path = '/proof-bank' if path == '/bank' else '/proof-provider'
        proof = f"if({expected})fetch('{proof_path}');"
        target = f'https://graf.test:{port}/billing/checkout'
        action = f"setTimeout(()=>{{document.forms[0].submit();}},400);"
        extra = ''
        if scenario == 'nested' and path == '/pay':
            target = f'https://bank.test:{port}/bank'
            extra = "target='bank'"
            action = f"window.open('{target}','bank');document.forms[0].submit();"
        if scenario == 'frame-chain' and path == '/pay':
            action = f"let frame=document.createElement('iframe');frame.src='https://bank.test:{port}/frame-live';frame.onload=()=>document.forms[0].submit();document.body.append(frame);"
        self.page(f"<body><form method=POST action='{target}' {extra}><input name=fixture value=synthetic-return></form><script>{proof}{action}</script>")

receipt()
server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
server.daemon_threads = False  # server_close joins pending receipt publications.
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(root / 'cert.pem', root / 'key.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
def stop_when_requested():
    while not (root / 'stop.request').exists():
        time.sleep(0.01)
    server.shutdown()

threading.Thread(target=stop_when_requested, daemon=True).start()
try:
    server.serve_forever(poll_interval=0.05)
finally:
    server.server_close()
with lock:
    receipt()  # Final authoritative snapshot, after every request has finished.
