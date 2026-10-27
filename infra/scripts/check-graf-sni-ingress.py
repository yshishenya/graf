#!/usr/bin/env python3
"""Disposable nginx protocol check. Never reads installed nginx configuration."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time


def stop_process_group(process, grace_seconds=5):
    def alive():
        for proc in Path("/proc").iterdir():
            if not proc.name.isdecimal():
                continue
            try:
                fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            except FileNotFoundError:
                continue
            if int(fields[2]) == process.pid and fields[0] not in ("Z", "X"):
                return True
        return False

    # The new session is exclusively ours. Master exit alone is insufficient:
    # a worker ignoring TERM may retain its listeners after its parent exits.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace_seconds
        while alive() and time.monotonic() < deadline:
            time.sleep(.05)
        if not alive():
            break
    process.wait(timeout=5)
    if alive():
        raise ValueError("isolated_process_group_not_stopped")


def run(repo, nginx, module, protocol_only=False):
    checks = {}
    measurements = {}
    # Exercise the forced-cleanup branch with our own TERM-resistant child.
    child_code = ("import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                  "print('ready',flush=True);time.sleep(30)")
    parent_code = ("import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"
                   + repr(child_code) + "]);time.sleep(30)")
    cleanup_probe = subprocess.Popen([sys.executable, "-c", parent_code],
                                     start_new_session=True, stdout=subprocess.PIPE)
    try:
        if cleanup_probe.stdout.readline() != b"ready\n":
            raise ValueError("cleanup_probe_not_ready")
    finally:
        stop_process_group(cleanup_probe, grace_seconds=.2)
        cleanup_probe.stdout.close()
    checks["forced_process_group_cleanup"] = True
    # Reserve together so the kernel cannot assign the same ephemeral port twice.
    reservations = [socket.socket() for _ in range(7)]
    try:
        for sock in reservations:
            sock.bind(("127.0.0.1", 0))
        ports = [sock.getsockname()[1] for sock in reservations]
    finally:
        for sock in reservations:
            sock.close()
    ingress, graf, default_relay, special_relay, default, special, api = ports
    routing = (repo / "infra/nginx/graf-sni-routing.conf").read_text()
    blocks = (repo / "infra/nginx/rec.2brain.pro.conf").read_text().split("\nserver {")
    if len(blocks) != 3:
        raise ValueError("unexpected_rec_server_layout")
    rec = "server {" + blocks[1].split("# YooKassa", 1)[0]
    checks["dedicated_receivers"] = all(
        f"listen {host}:10445 ssl http2 proxy_protocol;" in rec
        for host in ("127.0.0.1", "[::1]")
    ) and "10444" not in rec
    if not checks["dedicated_receivers"]:
        raise ValueError("rec_receiver_contract")
    with tempfile.TemporaryDirectory(prefix="graf-sni-check-") as directory:
        root = Path(directory)
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(root / "key.pem"), "-out", str(root / "cert.pem"),
            "-days", "1", "-subj", "/CN=isolated.invalid",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        cert = f"ssl_certificate {root}/cert.pem; ssl_certificate_key {root}/key.pem;"
        rec = rec.replace("127.0.0.1:10445", f"127.0.0.1:{graf}")
        rec = rec.replace("[::1]:10445", f"[::1]:{graf}")
        rec = rec.replace("127.0.0.1:18081", f"127.0.0.1:{api}")
        # Only certificates/log destinations are substituted. Locations, guards
        # and forwarding directives come from the candidate rec file itself.
        rec = "\n".join(
            "" if line.strip().startswith(("ssl_certificate", "include ", "ssl_dhparam"))
            else "access_log off;" if line.strip().startswith("access_log ")
            else "error_log /dev/null crit;" if line.strip().startswith("error_log ")
            else line for line in rec.splitlines()
        ).replace("server_name rec.2brain.pro;", "server_name rec.2brain.pro; " + cert)
        for old, new in ((10445, graf), (10446, default_relay), (10447, special_relay)):
            routing = routing.replace(f":{old}", f":{new}")
        (root / "routing.conf").write_text(routing)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # Generated fixture certificate only.

        def connect(sni, port=ingress, prefix=b"", ipv6=False, raw=None):
            sock = raw or socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET)
            try:
                if raw is None:
                    sock.settimeout(4)
                    sock.bind(("::1" if ipv6 else "127.0.0.2", 0))
                    sock.connect(("::1" if ipv6 else "127.0.0.1", port))
                if prefix:
                    sock.sendall(prefix)
                return context.wrap_socket(sock, server_hostname=sni)
            except BaseException:
                sock.close()
                raise

        def request(sni, host="rec.2brain.pro", headers="", stage=None, **kwargs):
            with connect(sni, **kwargs) as tls:
                tls.sendall((f"GET / HTTP/1.1\r\nHost: {host}\r\n"
                             f"Connection: close\r\n{headers}\r\n").encode())
                response = http.client.HTTPResponse(tls)
                response.begin()
                status = response.status
                if stage is not None and response.getheader("X-Graf-Probe-Stage") != stage:
                    status = 0
                return status, response.read()

        def config(stage):
            switched = stage in ("switch", "final")
            old_receiver = stage != "final"
            stream_routing = ("include " + str(root / "routing.conf") + ";"
                              if stage != "baseline" else "")
            if not switched:
                stream_routing += "\nmap $ssl_preread_server_name $old_target { " \
                    "www.amazon.com kvn_xray_reality; default kvn_https_nginx; }"
            text = f"""
load_module {module};
daemon off;
pid {root}/nginx.pid;
error_log /dev/null crit;
worker_processes 2;
events {{ worker_connections 768; }}
stream {{
    upstream kvn_https_nginx {{ server 127.0.0.1:{default}; }}
    upstream kvn_xray_reality {{ server 127.0.0.1:{special}; }}
    {stream_routing}
    server {{ listen 127.0.0.1:{ingress}; listen [::1]:{ingress};
        ssl_preread on; proxy_protocol {'on' if switched else 'off'};
        proxy_pass {'$graf_sni_target' if switched else '$old_target'}; }}
}}
http {{
    access_log off;
    error_log /dev/null crit;
    limit_req_zone $binary_remote_addr zone=graf_summary_share:1m rate=100r/s;
    {rec.replace('server_name rec.2brain.pro;', f'server_name rec.2brain.pro; add_header X-Graf-Probe-Stage {stage} always;') if stage != 'baseline' else ''}
    server {{ listen 127.0.0.1:{default} ssl; {cert}
        server_name default.invalid; add_header X-Graf-Probe-Stage {stage} always; return 200 'default'; }}
    {f"server {{ listen 127.0.0.1:{default} ssl; {cert} server_name rec.2brain.pro; add_header X-Graf-Probe-Stage {stage} always; return 200 'legacy'; }}" if old_receiver else ''}
    server {{ listen 127.0.0.1:{special} ssl; {cert} add_header X-Graf-Probe-Stage {stage} always; return 200 'special'; }}
    server {{ listen 127.0.0.1:{api};
        return 200 '$http_x_forwarded_for|$http_x_real_ip|$http_x_forwarded_proto'; }}
}}
"""
            path = root / "nginx.conf"
            path.write_text(text)
            result = subprocess.run([nginx, "-t", "-p", directory, "-c", str(path)],
                                    capture_output=True, timeout=10)
            if result.returncode:
                raise ValueError("isolated_nginx_syntax_" + stage)
            return path

        path = config("baseline")
        process = subprocess.Popen([nginx, "-p", directory, "-c", str(path)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        try:
            def resources(label):
                routes = (("default.invalid", b"default"), ("www.amazon.com", b"special"))
                for sni, body in routes:
                    for _ in range(10):
                        if request(sni, host=sni) != (200, body):
                            raise ValueError("resource_warmup_failed")
                held = []
                maxima = {}
                try:
                    for index in range(100):
                        sni, body = routes[index % 2]
                        tls = connect(sni)
                        held.append(tls)
                        tls.sendall((f"GET / HTTP/1.1\r\nHost: {sni}\r\n"
                                     "Connection: keep-alive\r\n\r\n").encode())
                        response = http.client.HTTPResponse(tls)
                        response.begin()
                        if response.status != 200 or response.read() != body:
                            raise ValueError("resource_keepalive_failed")
                        response.close()
                    for _ in range(31):
                        workers = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
                        if not workers:
                            raise ValueError("resource_workers_missing")
                        for pid in workers:
                            proc = Path("/proc") / pid
                            limits = (proc / "limits").read_text().splitlines()
                            soft_fd = int(next(line for line in limits
                                               if line.startswith("Max open files")).split()[3])
                            fds = list((proc / "fd").iterdir())
                            sockets = sum(os.readlink(fd).startswith("socket:") for fd in fds)
                            values = maxima.setdefault(pid, [0, 0, soft_fd])
                            if values[2] != soft_fd:
                                raise ValueError("resource_fd_limit_changed")
                            values[0] = max(values[0], len(fds))
                            values[1] = max(values[1], sockets)
                        time.sleep(1)
                finally:
                    for tls in held:
                        tls.close()

                def timed(index):
                    sni, body = routes[index % 2]
                    start = time.monotonic()
                    with connect(sni) as tls:
                        tls.sendall((f"GET / HTTP/1.1\r\nHost: {sni}\r\n"
                                     "Connection: close\r\n\r\n").encode())
                        first = tls.recv(1)
                        elapsed = time.monotonic() - start
                        chunks = [first]
                        while chunk := tls.recv(4096):
                            chunks.append(chunk)
                    head, _, actual = b"".join(chunks).partition(b"\r\n\r\n")
                    if head.split(b" ", 2)[1] != b"200" or actual != body:
                        raise ValueError("resource_latency_response_failed")
                    return index % 2, elapsed * 1000

                start = time.monotonic()
                with ThreadPoolExecutor(max_workers=16) as pool:
                    futures = []
                    for index in range(500):
                        time.sleep(max(0, start + index / 8 - time.monotonic()))
                        futures.append(pool.submit(timed, index))
                    results = [future.result() for future in futures]
                p95 = []
                for route in range(2):
                    values = sorted(ms for kind, ms in results if kind == route)
                    if len(values) != 250:
                        raise ValueError("resource_latency_sample_incomplete")
                    p95.append(values[math.ceil(.95 * len(values)) - 1])
                measurements[label] = {
                    "worker_maxima": [{"fd": fd, "socket_fd": sockets, "soft_fd": limit,
                                       "worker_connections": 768} for fd, sockets, limit in maxima.values()],
                    "keepalive_connections": 100, "samples_per_worker": 31,
                    "latency_count": len(results), "latency_window_seconds": time.monotonic() - start,
                    "ttfb_p95_ms_default_special": p95,
                }
                checks[label + "_resource_limits"] = all(
                    fd / limit < .70 and sockets / 768 < .70 for fd, sockets, limit in maxima.values())

            for _ in range(60):
                if process.poll() is not None:
                    raise ValueError("isolated_nginx_exited")
                try:
                    if request("rec.2brain.pro") == (200, b"legacy"):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise ValueError("isolated_nginx_not_ready")
            if not protocol_only:
                resources("baseline")

            current_stage = "baseline"

            def reload(stage, expected):
                nonlocal current_stage
                # A pre-reload connection has no ClientHello yet. Its old worker
                # must still be able to open its previous upstream after reload.
                with socket.create_connection(("127.0.0.1", ingress), timeout=4) as late:
                    time.sleep(.1)
                    old_workers = Path(
                        f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
                    config(stage)
                    os.kill(process.pid, signal.SIGHUP)
                    for _ in range(80):
                        if request("rec.2brain.pro", stage=stage) == expected:
                            break
                        time.sleep(.05)
                    else:
                        raise ValueError("isolated_reload_" + stage)
                    old_expected = ((200, b"127.0.0.1|127.0.0.1|https")
                                    if current_stage in ("switch", "final")
                                    else (200, b"legacy"))
                    checks[f"late_hello_{current_stage}_to_{stage}"] = (
                        request("rec.2brain.pro", raw=late) == old_expected)
                    current_stage = stage
                # Readiness is not just reload exit0 or an unchanged response.
                for _ in range(100):
                    if not any(Path(f"/proc/{pid}").exists() for pid in old_workers):
                        checks["drained_" + stage] = True
                        break
                    time.sleep(.05)
                else:
                    raise ValueError("isolated_workers_not_drained_" + stage)

            expected = (200, b"127.0.0.2|127.0.0.2|https")
            reload("prepare", (200, b"legacy"))
            reload("switch", expected)
            reload("final", expected)
            checks["graf_source_https"] = request("rec.2brain.pro") == expected
            checks["ipv6_public_source"] = request("rec.2brain.pro", ipv6=True) == (
                200, b"::1|::1|https")
            checks["ipv6_receiver"] = request("rec.2brain.pro", port=graf, ipv6=True,
                prefix=b"PROXY TCP6 2001:db8::1 2001:db8::2 1234 443\r\n") == (
                    200, b"2001:db8::1|2001:db8::1|https")
            checks["headers_overwritten"] = request("rec.2brain.pro", headers=(
                "X-Forwarded-For: 192.0.2.1\r\nX-Real-IP: 192.0.2.2\r\n"
                "X-Forwarded-Proto: http\r\n")) == expected
            for label, sni, body in (("unknown_sni", "other.invalid", b"default"),
                                     ("no_sni", None, b"default"),
                                     ("special_fixture", "www.amazon.com", b"special")):
                checks[label] = request(sni) == (200, body)
            checks["mismatched_host"] = request("rec.2brain.pro", host="other.invalid")[0] == 421
            checks["unknown_source"] = request("rec.2brain.pro", port=graf,
                                                prefix=b"PROXY UNKNOWN\r\n")[0] == 400
            for label, kwargs in (("missing_envelope", {"port": graf}),
                                  ("public_proxy_prefix", {"prefix":
                                   b"PROXY TCP4 192.0.2.1 192.0.2.2 1234 443\r\n"})):
                try:
                    request("rec.2brain.pro", **kwargs)
                    checks[label] = False
                except (OSError, http.client.HTTPException):
                    checks[label] = True
            if not protocol_only:
                resources("candidate")
                checks["latency_delta_below_10ms_each_route"] = all(
                    candidate - baseline < 10 for baseline, candidate in zip(
                        measurements["baseline"]["ttfb_p95_ms_default_special"],
                        measurements["candidate"]["ttfb_p95_ms_default_special"], strict=True))
            # Roll back with receivers retained until the old PP worker drains.
            reload("switch", expected)
            reload("prepare", (200, b"legacy"))
            reload("baseline", (200, b"legacy"))
            checks["rollback_route"] = True
            if not all(checks.values()):
                raise ValueError("isolated_protocol_matrix:" + ",".join(
                    key for key, passed in checks.items() if not passed))
        finally:
            stop_process_group(process)
        checks["isolated_process_group_stopped"] = process.poll() is not None
    checks["temporary_directory_removed"] = not root.exists()
    return {"checks": checks, "all_pass": all(checks.values()), "measurements": measurements,
            "input_sha256": {name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
                             for name in ("infra/scripts/check-graf-sni-ingress.py",
                                          "infra/nginx/graf-sni-routing.conf",
                                          "infra/nginx/rec.2brain.pro.conf")},
            "resource_probe": "skipped" if protocol_only else "isolated_only",
            "production_config_read": False, "production_mutation": False,
            "raw_addresses_exported": False,
            "scope": "isolated nginx protocol only; special is HTTPS fixture; not T098 acceptance"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--nginx", default="nginx")
    parser.add_argument("--stream-module", default="/usr/lib/nginx/modules/ngx_stream_module.so")
    parser.add_argument("--protocol-only", action="store_true", help="Skip the separate resource probe")
    args = parser.parse_args()
    try:
        result = run(args.repo, args.nginx, args.stream_module, args.protocol_only)
    except Exception as error:
        print(json.dumps({"all_pass": False, "failure_type": type(error).__name__,
                          "failure_code": (str(error) if isinstance(error, ValueError)
                                           and re.fullmatch(r"[a-z0-9_:,]+", str(error))
                                           else "probe_failed"),
                          "production_mutation": False}))
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))
