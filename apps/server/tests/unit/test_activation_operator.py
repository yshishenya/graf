"""Concrete Docker inventory and owned subprocess lifetime, without product writes."""

import asyncio
import copy
import json
import os
import sys
import time

import pytest

from twobrain_rec_server.product_analytics import activation_operator as operator
from twobrain_rec_server.product_analytics.activation_fence import ActivationHold, activation_fence


@pytest.fixture
def fence(tmp_path):
    directory = tmp_path / "operator"
    directory.mkdir(mode=0o700)
    (directory / "activation.lock").write_bytes(b"lock")
    (directory / "activation.lock").chmod(0o600)
    with activation_fence(
        directory / "state.json", owner_uid=os.geteuid(), exclusive=True, readonly=False
    ) as value:
        value.revoke()
        yield value


def inventory():
    rows = []
    for index, (service, names) in enumerate(operator.SERVICE_NETWORKS.items()):
        running = service in operator.REQUIRED_WRITERS | operator.INFRASTRUCTURE
        rows.append(
            dict(
                id=f"{index + 1:064x}",
                service=service,
                project="synthetic",
                oneoff="False",
                state=dict(
                    status="running" if running else "exited",
                    running=running,
                    restarting=False,
                    paused=False,
                    pid=123 if running else 0,
                    exit=0,
                ),
                networks={
                    n: {"NetworkID": f"{9 if n.endswith('media-private') else 8:064x}"}
                    for n in names
                },
            )
        )
    networks = [
        dict(
            id=f"{i:064x}",
            name=name,
            internal=internal,
            project="synthetic",
            containers={
                r["id"]: {} for r in rows if r["state"]["running"] and name in r["networks"]
            },
        )
        for i, name, internal in [
            (8, "twobrain-rec-private", False),
            (9, "twobrain-rec-media-private", True),
        ]
    ]
    return rows, networks


@pytest.mark.parametrize(
    "change",
    [
        "good",
        "optional_absent",
        "bootstrap_absent",
        "optional_created",
        "required_absent",
        "required_created",
        "dead",
        "removing",
        "initializer_failed",
        "duplicate",
        "foreign_network",
        "wrong_network",
        "oneoff",
    ],
)
def test_concrete_inventory_matrix(change):
    rows, networks = inventory()
    optional = next(r for r in rows if r["service"] == "rec-maintenance")
    required = next(r for r in rows if r["service"] == "rec-api")
    if change == "optional_absent":
        rows.remove(optional)
    if change == "bootstrap_absent":
        rows.remove(next(r for r in rows if r["service"] == "rec-db-runtime-bootstrap"))
    if change == "optional_created":
        optional["state"]["status"] = "created"
        optional["networks"] = {}
    if change == "required_absent":
        rows.remove(required)
    if change == "required_created":
        required["state"].update(status="created", running=False, pid=0)
    if change in {"dead", "removing"}:
        optional["state"]["status"] = change
    if change == "initializer_failed":
        next(r for r in rows if r["service"] == "rec-migrate")["state"]["exit"] = 1
    if change == "duplicate":
        rows.append(copy.deepcopy(optional))
    if change == "foreign_network":
        networks[0]["containers"]["f" * 64] = {}
    if change == "wrong_network":
        optional["networks"] = {"unexpected": {}}
    if change == "oneoff":
        optional["oneoff"] = "True"
    if change in {"good", "optional_absent", "bootstrap_absent", "optional_created"}:
        operator._validate_inventory(
            rows, networks, project="synthetic", postal_network="postal-network", stopped=False
        )
    else:
        with pytest.raises(ActivationHold):
            operator._validate_inventory(
                rows, networks, project="synthetic", postal_network="postal-network", stopped=False
            )


def test_stop_uses_one_fixed_command_and_rechecks_ids_and_revocation(fence, tmp_path, monkeypatch):
    async def run(replace=False):
        rows, networks = inventory()
        before = copy.deepcopy(rows)
        calls = []

        async def command(argv, *, deadline):
            calls.append(argv)
            assert deadline - time.monotonic() <= 120
            if "stop" in argv:
                assert set(argv[argv.index("stop") + 1 :]) == operator.WRITERS
                for row in rows:
                    if row["service"] in operator.WRITERS:
                        row["state"].update(status="exited", running=False, pid=0, exit=137)
                for net in networks:
                    net["containers"] = {
                        r["id"]: {}
                        for r in rows
                        if r["state"]["running"] and net["name"] in r["networks"]
                    }
                if replace:
                    rows[0]["id"] = "e" * 64
                return b""
            if argv[1:3] == ["container", "ls"]:
                return ("\n".join(r["id"] for r in rows)).encode()
            if argv[1:3] == ["network", "inspect"]:
                return ("\n".join(json.dumps(n) for n in networks)).encode()
            assert argv[1] == "inspect"
            return ("\n".join(json.dumps(r) for r in rows)).encode()

        monkeypatch.setattr(operator, "_command", command)
        if replace:
            with pytest.raises(ActivationHold):
                await operator.stop_product_writers(
                    fence, root=tmp_path, project="synthetic", postal_network="postal-network"
                )
        else:
            result = await operator.stop_product_writers(
                fence, root=tmp_path, project="synthetic", postal_network="postal-network"
            )
            assert result == {r["service"]: r["id"] for r in before}
        assert len([c for c in calls if "stop" in c]) == 1
        assert not any(set(c) & {"start", "restart", "kill", "up"} for c in calls)
        fence.exclusive = False
        count = len(calls)
        with pytest.raises(ActivationHold):
            await operator.stop_product_writers(
                fence, root=tmp_path, project="synthetic", postal_network="postal-network"
            )
        assert count == len(calls)
        fence.exclusive = True

    asyncio.run(run())
    asyncio.run(run(True))


@pytest.mark.parametrize("mode", ["timeout", "cancel_twice", "spawn_timeout", "spawn_cancel"])
def test_real_cli_child_is_reaped_before_cancel_or_timeout_returns(tmp_path, mode, monkeypatch):
    async def run():
        if mode.startswith("spawn_"):
            original = asyncio.create_subprocess_exec

            async def delayed(*args, **kwargs):
                child = await original(*args, **kwargs)
                await asyncio.sleep(0.2)
                return child

            monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
        pidfile = tmp_path / "pid"
        # Delayed TERM proves repeated cancellation cannot interrupt the reap owner.
        script = (
            "import os,signal,time,pathlib; "
            "signal.signal(signal.SIGTERM,lambda *_: (time.sleep(.15),exit(0))); "
            f"pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"
        )
        task = asyncio.create_task(
            operator._command(
                [sys.executable, "-c", script],
                deadline=time.monotonic()
                + (0.1 if mode == "spawn_timeout" else 0.3 if mode == "timeout" else 5),
            )
        )
        async with asyncio.timeout(3):
            while not pidfile.exists():
                await asyncio.sleep(0.005)
        pid = int(pidfile.read_text())
        if mode in {"cancel_twice", "spawn_cancel"}:
            task.cancel()
            await asyncio.sleep(0.03)
            task.cancel()
        with pytest.raises(
            ActivationHold if mode in {"timeout", "spawn_timeout"} else asyncio.CancelledError
        ):
            await task
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

    asyncio.run(run())


@pytest.mark.parametrize("postal", ["postal_postal-network", "custom_postal-net"])
def test_actual_postal_name_is_resolved_separately_from_compose_key(postal):
    rows, networks = inventory()
    for row in rows:
        if "postal-network" in row["networks"]:
            row["networks"][postal] = row["networks"].pop("postal-network")
    operator._validate_inventory(
        rows, networks, project="synthetic", postal_network=postal, stopped=False
    )
    with pytest.raises(ActivationHold):
        operator._validate_inventory(
            rows, networks, project="synthetic", postal_network="postal-network", stopped=False
        )


def test_one_database_deadline_starts_before_identity_sql(fence, monkeypatch):
    from types import SimpleNamespace

    async def run():
        calls = []

        class Connection:
            def is_in_transaction(self):
                return False

            async def fetchrow(self, sql):
                calls.append(sql)
                await asyncio.sleep(1)

            async def execute(self, sql):
                pytest.fail("ALTER cannot follow expired identity check")

        # Leave 150ms of the same original budget; do not change asyncio's clock.
        monkeypatch.setattr(
            operator, "time", SimpleNamespace(monotonic=lambda: time.monotonic() - 29.85)
        )
        start = time.monotonic()
        with pytest.raises(ActivationHold):
            await operator.drain_product_database(
                fence,
                source=Connection(),
                owner=Connection(),
                name="synthetic",
                oid=1,
                cluster_id="123",
            )
        assert time.monotonic() - start < 0.5 and len(calls) == 1

    asyncio.run(run())
