#!/bin/sh
# Installation fixes the mode; SSH supplies neither arguments nor environment.
exec /usr/bin/env -i PATH=/usr/bin:/bin /usr/bin/python3 -I - "$@" <<'PY'
import concurrent.futures
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

DOCKER = "/usr/bin/docker"
CONFIG = Path("/etc/graf/billing-observation")
STATE = Path("/var/lib/graf-billing-observation")
BACKUP = Path("/var/lib/graf-billing-observation-backup")
RUNTIME = Path("/run/graf-billing-observation")
MODES = {"source", "status", "tick", "witness", "activate", "transfer", "recover", "backup", "restore"}
MAX_OUTPUT = 16384


class LauncherError(RuntimeError):
    def __init__(self):
        super().__init__("observation_unavailable")


def require(condition):
    if not condition:
        raise LauncherError()


def owned_file(path, mode):
    for parent in path.absolute().parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_nlink == 1
            and stat.S_IMODE(before.st_mode) == mode)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
                and after.st_uid == 0 and after.st_nlink == 1 and stat.S_IMODE(after.st_mode) == mode)
        return fd
    except BaseException:
        os.close(fd)
        raise


def object_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value)
            value[key] = item
        return value
    def invalid(_value):
        raise LauncherError()
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def profile():
    fd = owned_file(CONFIG / "launcher.json", 0o400)
    try:
        raw = os.read(fd, MAX_OUTPUT + 1)
        require(len(raw) <= MAX_OUTPUT)
        value = object_json(raw)
    finally:
        os.close(fd)
    require(type(value) is dict and set(value) == {"image_id", "source_sha", "platform", "run_uid", "network", "role"})
    require(type(value["image_id"]) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", value["image_id"]))
    require(type(value["source_sha"]) is str and re.fullmatch(r"[0-9a-f]{40}", value["source_sha"]))
    require(value["platform"] in {"linux/amd64", "linux/arm64"} and value["role"] in {"primary", "witness"})
    require(type(value["run_uid"]) is int and 1000 <= value["run_uid"] <= 60000)
    require(type(value["network"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value["network"]))
    return value


def state_directory(path, uid):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700)
    for parent in path.absolute().parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)


def call(args, deadline, maximum=MAX_OUTPUT):
    require(time.monotonic() < deadline)
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env={"PATH": "/usr/bin:/bin"}, start_new_session=True)
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                require(remaining > 0)
                for key, _events in selector.select(remaining):
                    raw = os.read(key.fileobj.fileno(), min(65536, maximum + 1 - len(output)))
                    if not raw:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(raw)
                        require(len(output) <= maximum)
        require(process.wait(timeout=max(.001, deadline - time.monotonic())) == 0)
        return bytes(output)
    finally:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        process.stdout.close()


def validate_image(cfg, raw):
    infos = object_json(raw)
    require(type(infos) is list and len(infos) == 1)
    info = infos[0]
    require(info.get("Id") == cfg["image_id"]
            and f"{info.get('Os')}/{info.get('Architecture')}" == cfg["platform"])
    settings = info.get("Config") or {}
    require((settings.get("Labels") or {}).get("org.2brain.graf.dev.source-sha") == cfg["source_sha"])
    source = [value for value in settings.get("Env", []) if value.startswith("GRAF_DEV_SOURCE_SHA=")]
    require(source == ["GRAF_DEV_SOURCE_SHA=" + cfg["source_sha"]])


def safe_output(mode, value):
    require(type(value) is dict and type(value.get("schema_version")) is int
            and value["schema_version"] in ((1, 2) if mode == "source" else (1,)))
    if mode == "source":
        keys = {"schema_version", "source_profile", "source_generation", "as_of", "coverage",
                "event_count", "failed_event_count", "conflicting_attempt_count", "last_event_at"}
        counters = {"event_count", "failed_event_count", "conflicting_attempt_count"}
        if value["schema_version"] == 2:
            receipt = {"receipt_canceled_count", "receipt_overdue_confirmed_count", "receipt_overdue_unknown_count"}
            keys |= receipt
            counters |= receipt
        require(set(value) == keys and value["coverage"] == "partial")
        for field in ("source_profile", "source_generation"):
            require(type(value[field]) is str and str(UUID(value[field])) == value[field])
        for field in counters:
            require(type(value[field]) is int and 0 <= value[field] <= 9223372036854775807)
        times = [value["as_of"]] + ([] if value["last_event_at"] is None else [value["last_event_at"]])
    elif mode in {"status", "tick", "witness"}:
        require(set(value) == {"schema_version", "role", "completed_at", "source_check", "peer_tick_at", "sequence", "head"}
                and value["role"] in {"primary", "witness"}
                and value["source_check"] in {"available", "unavailable", "discontinuity"})
        times = [value[field] for field in ("completed_at", "peer_tick_at") if value[field] is not None]
    elif mode == "backup":
        require(set(value) == {"schema_version", "sequence", "head"})
        times = []
    else:
        codes = {"activate": "activated", "transfer": "reaction_recorded", "recover": "lineage_recovered",
                 "restore": "recovery_hold"}
        require(set(value) == {"schema_version", "result_code"} and value["result_code"] == codes[mode])
        times = []
    if "sequence" in value:
        require(type(value["sequence"]) is int and 0 <= value["sequence"] <= 262144
                and type(value["head"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["head"]))
    for text in times:
        require(type(text) is str and 0 < len(text) <= 40)
        instant = datetime.fromisoformat(text)
        require(instant.tzinfo is not None and instant.utcoffset() == timedelta(0))
    return value


def ssh_command(kind):
    require(kind in {"source", "peer"})
    return ["/usr/bin/ssh", "-F", str(CONFIG / "ssh.conf"), "-T", "-n",
            "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UserKnownHostsFile=" + str(CONFIG / "known_hosts"), "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no", "-o", "PermitLocalCommand=no",
            "-o", "ConnectTimeout=5", "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=2",
            "-o", "ControlMaster=no", "-o", "ControlPath=none", "graf-billing-" + kind]


def container_command(cfg, mode, name, inputs, seconds):
    require(mode in MODES and type(seconds) is int and 1 <= seconds <= 50)
    args = [DOCKER, "run", "--rm", "--pull", "never", "--name", name,
            "--label", "org.2brain.graf.observation.run=" + name,
            "--platform", cfg["platform"], "--user", f"{cfg['run_uid']}:{cfg['run_uid']}",
            "--read-only", "--init", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--pids-limit", "64", "--memory", "512m", "--memory-swap", "512m", "--cpus", "1",
            "--ulimit", "nofile=128:128", "--log-driver", "none",
            "--network", cfg["network"] if mode in {"source", "tick", "witness"} else "none"]
    def mount(path, target, readonly=True):
        args.extend(["--mount", f"type=bind,src={path},dst={target}" + (",readonly" if readonly else "")])
    if mode == "source":
        mount(CONFIG / "source.json", "/run/secrets/billing-observation-source.json")
        module = "twobrain_rec_server.cli.billing_observation_probe"
        module_args = []
    else:
        mount(STATE, "/state", mode == "status")
        if mode != "status":
            mount(CONFIG / "mail.json", "/run/secrets/billing-observation-mail.json")
        if mode in {"tick", "witness"}:
            mount(inputs, "/input")
        if mode in {"transfer", "recover"}:
            mount(CONFIG / "relay", "/relay")
        if mode in {"backup", "restore"}:
            mount(BACKUP, "/backup", mode == "restore")
        module = "twobrain_rec_server.cli.billing_observation_alerts"
        module_args = [mode]
    return args + ["--entrypoint", "/usr/bin/timeout", cfg["image_id"], "--signal=KILL", f"{seconds}s",
                   "/usr/local/bin/python", "-I", "-m", module, *module_args]


def cleanup(name, deadline):
    try:
        with suppress(LauncherError, OSError, subprocess.TimeoutExpired):
            call([DOCKER, "rm", "--force", name], min(deadline, time.monotonic() + 2))
        remaining = call([DOCKER, "ps", "--all", "--quiet", "--filter", "name=^/" + name + "$"], deadline)
        return not remaining.strip()
    except (LauncherError, OSError, subprocess.TimeoutExpired):
        return False


def remote(kind, deadline):
    try:
        raw = call(ssh_command(kind), deadline)
        value = object_json(raw)
        require(type(value) is dict)
        return raw if "result_code" not in value else None
    except (LauncherError, OSError, ValueError, subprocess.TimeoutExpired):
        return None


def interrupt(_signal, _frame):
    raise InterruptedError()


def execute(mode):
    require(mode in MODES and os.geteuid() == 0)
    os.umask(0o077)
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, interrupt)
    # Four seconds are reserved for cleanup, including when SSH disconnects.
    deadline = time.monotonic() + (25 if mode in {"source", "status"} else 60)
    work_deadline = deadline - 4
    cfg = profile()
    require(mode not in {"tick", "witness"} or (mode == "tick") == (cfg["role"] == "primary"))
    require(mode != "source" or cfg["role"] == "witness")
    validate_image(cfg, call([DOCKER, "image", "inspect", cfg["image_id"]],
                             min(work_deadline, time.monotonic() + 3), 65536))
    if mode != "source":
        state_directory(STATE, cfg["run_uid"])
    if mode in {"backup", "restore"}:
        state_directory(BACKUP, cfg["run_uid"])
    secret = "source.json" if mode == "source" else "mail.json"
    if mode != "status":
        os.close(owned_file(CONFIG / secret, 0o440))
    inputs = None
    name = "graf-observation-" + uuid4().hex
    clean = True
    try:
        if mode in {"tick", "witness"}:
            os.close(owned_file(CONFIG / "ssh.conf", 0o400))
            os.close(owned_file(CONFIG / "known_hosts", 0o400))
            state_directory(RUNTIME, 0)
            inputs = Path(tempfile.mkdtemp(prefix="input-", dir=RUNTIME))
            os.chown(inputs, cfg["run_uid"], cfg["run_uid"])
            kinds = ["source", "peer"] if mode == "tick" else ["peer"]
            remote_deadline = min(work_deadline, time.monotonic() + 25)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = {kind: pool.submit(remote, kind, remote_deadline) for kind in kinds}
                for kind, future in futures.items():
                    raw = future.result(timeout=max(.001, remote_deadline - time.monotonic()) + 1)
                    if raw is not None:
                        target = inputs / ("source.json" if kind == "source" else "peer.json")
                        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o440)
                        try:
                            os.fchown(fd, 0, cfg["run_uid"])
                            os.fchmod(fd, 0o440)
                            require(os.write(fd, raw) == len(raw))
                        finally:
                            os.close(fd)
        seconds = min(18 if mode in {"source", "status"} else 50, int(work_deadline - time.monotonic()))
        args = container_command(cfg, mode, name, inputs, seconds)
        clean = False
        try:
            raw = call(args, work_deadline)
            value = safe_output(mode, object_json(raw))
        finally:
            clean = cleanup(name, deadline)
        require(clean)
        return value
    finally:
        if clean and inputs is not None:
            shutil.rmtree(inputs)


def main():
    try:
        require(len(sys.argv) == 2 and sys.argv[1].startswith("--"))
        result = execute(sys.argv[1][2:])
        code = 0
    except (Exception, KeyboardInterrupt):
        result, code = {"schema_version": 1, "result_code": "observation_unavailable"}, 1
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
PY
