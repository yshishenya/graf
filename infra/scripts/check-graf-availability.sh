#!/usr/bin/env bash
set -euo pipefail
# Independent public probe; no SSH, Docker or database access to the target.
exec python3 - "$@" <<'PY'
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

def safe_error(kind, value, trace):
    # Operational exceptions must not print private host paths or payloads.
    print("availability_result=unknown reason=observer_error", file=sys.stderr)

sys.excepthook = safe_error
os.umask(0o077)
mode = sys.argv[1:] or ["--dry-run"]
if mode not in (["--execute"], ["--dry-run"], ["--status"]):
    raise SystemExit("usage: check-graf-availability.sh [--execute|--dry-run|--status]")
root = Path(os.environ.get("GRAF_AVAILABILITY_STATE_DIR", "/var/lib/graf-external-availability"))
state_file = root / "state.json"
url = os.environ.get("GRAF_AVAILABILITY_URL", "https://rec.2brain.pro/api/v1/health/live")
sender = os.environ.get("GRAF_AVAILABILITY_ALERT_SCRIPT", "/usr/local/libexec/graf-analytics-degradation-alert.sh")
parsed = urlsplit(url)
if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
    raise SystemExit("availability_result=failed reason=invalid_target")
target_id = hashlib.sha256(json.dumps(
    [parsed.hostname.lower(), parsed.port or 443, parsed.path or "/"],
    separators=(",", ":"),
).encode()).hexdigest()
if mode == ["--dry-run"]:
    print("availability_result=dry_run interval_seconds=60 timeout_seconds=10 failure_threshold=2")
    raise SystemExit(0)

root.mkdir(mode=0o700, parents=True, exist_ok=True)
with (root / "lock").open("a") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("availability_result=unknown reason=probe_already_running")
    now = int(time.time())
    initial_state = dict(target_id=target_id, recorded_epoch=0, failures=0, first_failure_epoch=0,
                 last_delivery_epoch=0, notified_outage=False)
    state = initial_state.copy()
    if state_file.exists():
        try:
            loaded = json.loads(state_file.read_text())
            for key in ("recorded_epoch", "failures", "first_failure_epoch", "last_delivery_epoch"):
                if type(loaded[key]) is not int or not 0 <= loaded[key] <= now:
                    raise ValueError("invalid state number")
            if type(loaded["notified_outage"]) is not bool:
                raise ValueError("invalid state flag")
            if (loaded["failures"] > 2
                    or set(loaded) != set(state) | {"target_status", "channel_status", "delivery", "result"}
                    or loaded["target_status"] not in {"up", "unreachable", "degraded"}
                    or loaded["channel_status"] not in {"available", "channel_unavailable"}
                    or loaded["delivery"] not in {"not_required", "delivered", "failed"}
                    or loaded["result"] not in {"ready", "degraded"}
                    or not isinstance(loaded["target_id"], str)
                    or len(loaded["target_id"]) != 64
                    or any(c not in "0123456789abcdef" for c in loaded["target_id"])):
                raise ValueError("invalid state schema")
            failures = loaded["failures"]
            notified = loaded["notified_outage"]
            delivery = loaded["delivery"]
            if (loaded["recorded_epoch"] == 0
                    or loaded["last_delivery_epoch"] > loaded["recorded_epoch"]
                    or loaded["target_status"] != ("up" if failures == 0 else "degraded" if failures == 1 else "unreachable")
                    or (failures == 0 and loaded["first_failure_epoch"] != 0)
                    or (failures > 0 and not 0 < loaded["first_failure_epoch"] <= loaded["recorded_epoch"])
                    or (notified and loaded["last_delivery_epoch"] == 0)
                    or (delivery == "delivered" and loaded["last_delivery_epoch"] == 0)
                    or (failures == 0 and notified != (delivery == "failed"))
                    or (failures == 1 and delivery != "not_required")
                    or (failures == 2 and delivery != "failed" and not notified)
                    or loaded["result"] != ("ready" if failures == 0 and loaded["channel_status"] == "available" and delivery != "failed" else "degraded")):
                raise ValueError("inconsistent state")
            state.update(loaded)
        except (OSError, ValueError, KeyError, TypeError):
            raise SystemExit("availability_result=unknown reason=state_invalid")
    if state["target_id"] != target_id:
        if mode == ["--status"]:
            raise SystemExit("availability_result=unknown reason=target_changed")
        state = initial_state.copy()
    if mode == ["--status"]:
        if not state_file.exists() or now - state["recorded_epoch"] >= 180:
            raise SystemExit("availability_result=unknown reason=state_missing_or_stale")
        print(json.dumps(state, sort_keys=True))
        raise SystemExit(0 if state.get("result") == "ready" else 1)

    # The shared EnvironmentFile may name another sender state directory.
    os.environ["GRAF_ANALYTICS_ALERT_STATE_DIR"] = str(root / "alert")

    def run(argv, timeout):
        try:
            return subprocess.run(argv, capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            return None

    response = run(["curl", "--disable", "--silent", "--show-error", "--max-time", "10",
                    "--proto", "=https", "--max-filesize", "65536", "--write-out", "\n%{http_code}", url], 12)
    healthy = False
    if response is not None and response.returncode == 0:
        try:
            body, code = response.stdout.rsplit(b"\n", 1)
            payload = json.loads(body)
            healthy = code == b"200" and isinstance(payload, dict) and payload.get("status") == "ok"
        except (ValueError, TypeError):
            pass
    channel = run([sender, "--external-channel"], 25)
    channel_ok = channel is not None and channel.returncode == 0
    notification = None
    if healthy:
        state["failures"] = state["first_failure_epoch"] = 0
        if state["notified_outage"]:
            notification = "target-recovered"
        state["target_status"] = "up"
    else:
        if state["failures"] == 0:
            state["first_failure_epoch"] = now
        state["failures"] = min(2, state["failures"] + 1)
        state["target_status"] = "unreachable" if state["failures"] >= 2 else "degraded"
        if state["failures"] >= 2 and (not state["notified_outage"] or now - state["last_delivery_epoch"] >= 3600):
            notification = "target-unreachable"
    delivery = "not_required"
    if notification:
        sent = run([sender, "--" + notification], 25)
        delivered = sent is not None and sent.returncode == 0
        delivery = "delivered" if delivered else "failed"
        if delivered:
            state["last_delivery_epoch"] = int(time.time())
            state["notified_outage"] = notification == "target-unreachable"
    state.update(recorded_epoch=int(time.time()), channel_status="available" if channel_ok else "channel_unavailable",
                 delivery=delivery, result="ready" if healthy and channel_ok and delivery != "failed" else "degraded")
    fd, name = tempfile.mkstemp(dir=root, prefix=".state-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, state_file)
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(name).unlink(missing_ok=True)
    print(json.dumps(state, sort_keys=True))
    raise SystemExit(0 if state["result"] == "ready" else 1)
PY
