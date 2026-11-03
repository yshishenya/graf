"""Synthetic host commands: never contact SSH, Docker, a database or mail."""
import json
import sys
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def launcher():
    text = (ROOT / "infra/scripts/billing-observation-probe.sh").read_text()
    code = text.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    module = types.ModuleType("synthetic_billing_launcher")
    exec(compile(code, "synthetic_billing_launcher", "exec"), module.__dict__)
    return module


def profile():
    return {"image_id": "sha256:" + "1" * 64, "source_sha": "2" * 40,
            "platform": "linux/amd64", "run_uid": 1200, "network": "synthetic-network",
            "role": "primary"}


def test_fixed_services_timers_and_clean_shell_entrypoints():
    for name in ("graf-billing-observation", "graf-billing-observation-witness"):
        service = (ROOT / f"infra/systemd/{name}.service").read_text()
        timer = (ROOT / f"infra/systemd/{name}.timer").read_text()
        assert "TimeoutStartSec=60" in service and "KillMode=control-group" in service
        assert "NoNewPrivileges=true" in service and "ProtectSystem=strict" in service
        assert "OnUnitActiveSec=300s" in timer and "RandomizedDelaySec=0" in timer
        assert "AccuracySec=1s" in timer
    script = (ROOT / "infra/scripts/billing-observation-probe.sh").read_text()
    assert "/usr/bin/env -i" in script and "/usr/bin/python3 -I" in script
    assert "SSH_ORIGINAL_COMMAND" not in script
    wrapper = (ROOT / "infra/scripts/check-billing-observation.sh").read_text()
    assert "/usr/local/libexec/billing-observation-probe.sh" in wrapper


@pytest.mark.parametrize("mode", ["source", "status", "tick", "witness", "transfer", "recover", "backup", "restore", "activate"])
def test_container_has_only_scoped_mounts_and_a_second_deadline(launcher, mode):
    args = launcher.container_command(profile(), mode, "graf-observation-synthetic", "/run/graf-billing-observation/synthetic", 18)
    assert args[:2] == ["/usr/bin/docker", "run"]
    for flag in ("--rm", "--read-only", "--init"):
        assert flag in args
    for key, value in (("--pull", "never"), ("--user", "1200:1200"), ("--cap-drop", "ALL"),
                       ("--security-opt", "no-new-privileges:true"), ("--entrypoint", "/usr/bin/timeout"),
                       ("--pids-limit", "64"), ("--log-driver", "none")):
        assert args[args.index(key) + 1] == value
    assert "--signal=KILL" in args and "18s" in args and "/usr/local/bin/python" in args
    assert "-I" in args and "-m" in args
    assert profile()["image_id"] in args and "/var/run/docker.sock" not in " ".join(args)
    mounts = [args[i + 1] for i, value in enumerate(args) if value == "--mount"]
    if mode == "source":
        assert len(mounts) == 1 and "billing-observation-source.json" in mounts[0]
    else:
        assert all("billing-observation-source.json" not in m for m in mounts)
    if mode == "status":
        assert len(mounts) == 1 and mounts[0].endswith(",readonly")
    if mode not in {"source", "tick", "witness"}:
        assert args[args.index("--network") + 1] == "none"
    assert not any(value in args for value in ("--privileged", "--env-file", "--publish", "--volumes-from"))


def test_image_identity_platform_and_both_source_bindings_are_required(launcher):
    cfg = profile()
    good = [{"Id": cfg["image_id"], "Os": "linux", "Architecture": "amd64",
             "Config": {"Labels": {"org.2brain.graf.dev.source-sha": cfg["source_sha"]},
                        "Env": ["GRAF_DEV_SOURCE_SHA=" + cfg["source_sha"]]}}]
    launcher.validate_image(cfg, json.dumps(good).encode())
    for field in ("Id", "Architecture", "label", "environment"):
        bad = json.loads(json.dumps(good))
        if field == "label":
            bad[0]["Config"]["Labels"] = {}
        elif field == "environment":
            bad[0]["Config"]["Env"] = []
        else:
            bad[0][field] = "wrong"
        with pytest.raises(launcher.LauncherError):
            launcher.validate_image(cfg, json.dumps(bad).encode())


def test_ssh_uses_fixed_alias_and_no_remote_command_or_client_environment(launcher):
    for kind, alias in (("source", "graf-billing-source"), ("peer", "graf-billing-peer")):
        args = launcher.ssh_command(kind)
        assert args[0] == "/usr/bin/ssh" and args[-1] == alias
        for value in ("-T", "-n", "BatchMode=yes", "StrictHostKeyChecking=yes",
                      "ForwardAgent=no", "ClearAllForwardings=yes", "PermitLocalCommand=no"):
            assert value in args
    with pytest.raises(launcher.LauncherError):
        launcher.ssh_command("arbitrary-command")


def test_command_output_limit_and_stderr_are_bounded_and_private(launcher):
    with pytest.raises(launcher.LauncherError) as error:
        launcher.call([sys.executable, "-c", "import sys;sys.stderr.write('private-secret');print('x'*17000)"],
                      time.monotonic() + 3)
    assert str(error.value) == "observation_unavailable"
    started = time.monotonic()
    with pytest.raises(launcher.LauncherError):
        launcher.call([sys.executable, "-c", "import time;time.sleep(30)"], time.monotonic() + .2)
    assert time.monotonic() - started < 2


def test_cleanup_requires_a_successful_empty_container_listing(launcher, monkeypatch):
    calls = []

    def command(args, deadline, maximum=16384):
        calls.append(args)
        if args[1] == "rm":
            raise launcher.LauncherError()
        return b""

    monkeypatch.setattr(launcher, "call", command)
    assert launcher.cleanup("graf-observation-synthetic", time.monotonic() + 5)
    assert calls[-1][1:3] == ["ps", "--all"]
    monkeypatch.setattr(launcher, "call", lambda *_args, **_kwargs: b"still-running")
    assert not launcher.cleanup("graf-observation-synthetic", time.monotonic() + 5)
    def unavailable(*_args, **_kwargs):
        raise launcher.LauncherError()
    monkeypatch.setattr(launcher, "call", unavailable)
    assert not launcher.cleanup("graf-observation-synthetic", time.monotonic() + 5)


def test_tick_launcher_prepares_readable_inputs_and_cleans_its_temporary_directory(launcher, monkeypatch, tmp_path):
    import os
    import stat

    cfg = profile()
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    monkeypatch.setattr(launcher, "RUNTIME", runtime)
    monkeypatch.setattr(launcher, "profile", lambda: cfg)
    monkeypatch.setattr(launcher, "state_directory", lambda *_args: None)
    monkeypatch.setattr(launcher, "owned_file", lambda *_args: os.open(os.devnull, os.O_RDONLY))
    monkeypatch.setattr(launcher.os, "geteuid", lambda: 0)
    monkeypatch.setattr(launcher.os, "chown", lambda *_args: None)
    monkeypatch.setattr(launcher.os, "fchown", lambda *_args: None)
    monkeypatch.setattr(launcher.signal, "signal", lambda *_args: None)
    image = [{"Id": cfg["image_id"], "Os": "linux", "Architecture": "amd64",
              "Config": {"Labels": {"org.2brain.graf.dev.source-sha": cfg["source_sha"]},
                         "Env": ["GRAF_DEV_SOURCE_SHA=" + cfg["source_sha"]]}}]
    calls = []
    status = {"schema_version": 1, "role": "primary", "completed_at": "2026-11-03T12:00:00+00:00",
              "source_check": "available", "peer_tick_at": None, "sequence": 2, "head": "3" * 64}

    def command(args, deadline, maximum=16384):
        calls.append(args)
        assert deadline > time.monotonic()
        if args[1:3] == ["image", "inspect"]:
            return json.dumps(image).encode()
        if args[0] == "/usr/bin/ssh":
            return json.dumps(status).encode()
        if args[1] == "run":
            inputs = next(runtime.iterdir())
            assert sorted(p.name for p in inputs.iterdir()) == ["peer.json", "source.json"]
            for path in inputs.iterdir():
                assert stat.S_IMODE(path.stat().st_mode) == 0o440
            return json.dumps(status).encode()
        return b""

    monkeypatch.setattr(launcher, "call", command)
    previous = os.umask(0o022)
    try:
        assert launcher.execute("tick") == status
    finally:
        os.umask(previous)
    assert list(runtime.iterdir()) == []
    assert sum(args[0] == "/usr/bin/ssh" for args in calls) == 2
    assert sum(args[1] == "run" for args in calls) == 1


def test_failed_child_command_kills_its_descendants(launcher, tmp_path):
    target = tmp_path / "heartbeat"
    script = """
import subprocess,sys,time
subprocess.Popen([sys.executable,'-c',"import pathlib,sys,time;p=pathlib.Path(sys.argv[1]);\\nwhile True:\\n p.write_text(str(time.time_ns()));time.sleep(.01)",sys.argv[1]])
time.sleep(30)
"""
    with pytest.raises(launcher.LauncherError):
        launcher.call([sys.executable, "-c", script, str(target)], time.monotonic() + .5)
    assert target.exists()
    completed = target.read_bytes()
    time.sleep(.1)
    assert target.read_bytes() == completed


@pytest.mark.parametrize("value", [
    {"schema_version": True}, {"schema_version": 1, "private": "synthetic@example.invalid"},
    {"schema_version": 1, "role": "primary", "completed_at": "not-a-time", "source_check": "available",
     "peer_tick_at": None, "sequence": 1, "head": "0" * 64},
])
def test_unexpected_container_output_is_never_forwarded(launcher, value):
    with pytest.raises((launcher.LauncherError, ValueError)):
        launcher.safe_output("status", value)
