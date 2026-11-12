"""The operator input is closed and never echoed on a parsing failure."""
import asyncio
from contextlib import asynccontextmanager
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError


def arguments(command="create"):
    common = [command, "--workspace", str(uuid4()), "--evidence-ref", "incident:synthetic",
              "--operator-ref", "op-" + "a" * 32, "--evidence-reviewed"]
    if command == "create":
        return common + ["--subject", str(uuid4()), "--capability", "server_processing",
                         "--reason", "resale"]
    return common + ["--decision", "cleared", "--resolution-code", "not_substantiated"]


def test_operator_cli_is_read_only_by_default_and_execute_is_explicit():
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    for command in ("create", "resolve"):
        argv = arguments(command)
        assert cli.parse_args(argv).execute is False
        assert cli.parse_args(argv + ["--execute"]).execute is True


@pytest.mark.parametrize("value", [
    "", "op-" + "a" * 31, "op-" + "a" * 33, "op-" + "A" * 32,
    "op-" + "а" * 32, " op-" + "a" * 32, "op-" + "a" * 32 + "\n",
    "op-" + "a" * 31 + "\t", "private@example.test", "op-" + "０" * 32,
])
@pytest.mark.parametrize("command", ["create", "resolve"])
def test_operator_cli_rejects_noncanonical_operator_without_echo(value, command, capsys):
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    argv = arguments(command)
    argv[argv.index("--operator-ref") + 1] = value
    with pytest.raises(SystemExit) as error:
        cli.parse_args(argv)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == '{"result_code": "invalid_arguments"}\n'


@pytest.mark.parametrize("change", [
    ["--urgent"], ["--starts-at", "2020-01-01"], ["--execute=true"],
    ["--capability", "exports"], ["--reason", "volume_only"],
    ["--evidence-ref", "meeting-private"], ["--evidence-ref", "incident/unsafe"],
    ["--subject", "private@example.test"], ["--operator", "op-" + "b" * 32],
])
def test_operator_cli_rejects_unapproved_input_without_echo(change, capsys):
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    with pytest.raises(SystemExit) as error:
        cli.parse_args(arguments() + change)
    assert error.value.code == 2
    assert capsys.readouterr().err == '{"result_code": "invalid_arguments"}\n'


def test_operator_cli_requires_review_attestation(capsys):
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    for command in ("create", "resolve"):
        argv = arguments(command)
        argv.remove("--evidence-reviewed")
        with pytest.raises(SystemExit) as error:
            cli.parse_args(argv)
        assert error.value.code == 2
        assert capsys.readouterr().err == '{"result_code": "invalid_arguments"}\n'


@pytest.mark.parametrize("decision,code,accepted", [
    ("cleared", "not_substantiated", True), ("cleared", "no_longer_applicable", True),
    ("confirmed", "basis_confirmed", True), ("cleared", "basis_confirmed", False),
    ("confirmed", "not_substantiated", False), ("confirmed", "no_longer_applicable", False),
])
def test_operator_cli_checks_the_decision_and_code_together(decision, code, accepted, capsys):
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    argv = arguments("resolve")
    argv[argv.index("--decision") + 1] = decision
    argv[argv.index("--resolution-code") + 1] = code
    if accepted:
        result = cli.parse_args(argv)
        assert (result.decision, result.resolution_code) == (decision, code)
    else:
        with pytest.raises(SystemExit) as error:
            cli.parse_args(argv)
        assert error.value.code == 2
        assert capsys.readouterr().err == '{"result_code": "invalid_arguments"}\n'


@pytest.mark.parametrize("failure", ["commit", "dispose"])
def test_operator_cli_database_failure_never_returns_success_or_private_values(failure, monkeypatch, capsys):
    cli = import_module("twobrain_rec_server.cli.billing_fair_use")
    private = "postgresql://private:secret@invalid/private incident:private"

    @asynccontextmanager
    async def begin():
        yield
        if failure == "commit":
            raise SQLAlchemyError(private)

    session = SimpleNamespace(sync_session=SimpleNamespace(info={}), begin=begin, execute=AsyncMock())

    @asynccontextmanager
    async def sessions():
        yield session

    engine = SimpleNamespace(dispose=AsyncMock(side_effect=SQLAlchemyError(private) if failure == "dispose" else None))
    monkeypatch.setattr(cli, "create_engine", lambda settings: engine)
    monkeypatch.setattr(cli, "create_sessionmaker", lambda engine: sessions)
    monkeypatch.setattr(cli, "create_operator_review", AsyncMock(return_value=("notice", True)))
    result, code = asyncio.run(cli.run(cli.parse_args(arguments() + ["--execute"]), settings=object()))
    assert (result, code) == ({"result_code": "database_unavailable"}, 1)
    engine.dispose.assert_awaited_once()
    assert capsys.readouterr() == ("", "")
