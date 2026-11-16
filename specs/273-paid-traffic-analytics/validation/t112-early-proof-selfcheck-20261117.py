"""Execute only pure observer wrappers extracted by AST; no HTTP or database."""
import ast
import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
import sys
from types import SimpleNamespace

source = Path(sys.argv[1])
names = {"Observation", "shape", "error_type", "boundary", "eligibility", "transaction"}
nodes = [n for n in ast.parse(source.read_text()).body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
assert len(nodes) == len(names)
active = ContextVar("check", default=None)
env = dict(asyncio=asyncio, asynccontextmanager=asynccontextmanager, ACTIVE=active,
           STAGES={"optional", "eligible", "issue", "inspect", "account", "bindings", "operation"})
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), env)
Observation, boundary, eligibility, transaction = [env[n] for n in ("Observation", "boundary", "eligibility", "transaction")]


class NoValues(dict):
    def __iter__(self):
        raise AssertionError("private keys accessed")

    def values(self):
        raise AssertionError("private values accessed")


class Manager:
    def __init__(self, context, *, enter_error=None, exit_error=None, suppress=False):
        self.context, self.enter_error, self.exit_error, self.suppress = context, enter_error, exit_error, suppress
        self.enters = self.exits = 0
        self.exc = None

    async def __aenter__(self):
        self.enters += 1
        if self.enter_error:
            raise self.enter_error
        return self.context

    async def __aexit__(self, cls, error, traceback):
        self.exits += 1
        self.exc = error
        if self.exit_error:
            raise self.exit_error
        return self.suppress


async def main():
    checks = 0
    obs = Observation()
    token = active.set(obs)
    try:
        for result in (None, NoValues(), NoValues({"private": "never read"})):
            calls = []

            async def original(*args, **kwargs):
                calls.append((args, kwargs))
                return result

            marker = object()
            assert await boundary(original, "bindings")(marker, same=marker) is result
            assert calls == [((marker,), {"same": marker})]
            checks += 1
        for failure in (RuntimeError("private"), asyncio.CancelledError("private")):
            calls = []

            async def failing(*args, **kwargs):
                calls.append(True)
                raise failure

            try:
                await boundary(failing, "operation")()
            except BaseException as caught:
                assert caught is failure
            else:
                raise AssertionError("exception swallowed")
            assert calls == [True]
            checks += 1
        for result in (False, True):
            calls = []

            def eligible(*args, **kwargs):
                calls.append((args, kwargs))
                return result

            assert eligibility(eligible)(marker, same=marker) is result
            assert calls == [((marker,), {"same": marker})]
            checks += 1
        owner_class = type("SyntheticOwner", (), {})
        context = SimpleNamespace(owner=owner_class())
        for mode in ("normal", "entry", "body", "cancel", "suppress", "cleanup"):
            body_error = asyncio.CancelledError("private") if mode == "cancel" else RuntimeError("private")
            exit_error = ValueError("private") if mode == "cleanup" else None
            manager = Manager(context, enter_error=body_error if mode == "entry" else None,
                              exit_error=exit_error, suppress=mode == "suppress")
            calls = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return manager

            caught = None
            try:
                async with transaction(factory, owner_class)(marker, same=marker) as yielded:
                    assert yielded is context
                    if mode in {"body", "cancel", "suppress", "cleanup"}:
                        raise body_error
            except BaseException as error:
                caught = error
            expected = exit_error or (body_error if mode in {"entry", "body", "cancel"} else None)
            assert caught is expected
            assert calls == [((marker,), {"same": marker})] and manager.enters == 1
            assert manager.exits == (0 if mode == "entry" else 1)
            if mode in {"body", "cancel", "suppress", "cleanup"}:
                assert manager.exc is body_error
            checks += 1
        assert "private" not in repr(obs.records) + repr(obs.summary)
        assert obs.dropped > 0 and obs.incomplete and len(obs.records) == 32
        assert obs.summary["account"]["event"] == "exit_exception"
        checks += 1
    finally:
        active.reset(token)
    assert active.get() is None
    # Inactive wrappers preserve delegation without creating an observation.
    result = object()

    async def inactive():
        return result

    assert await boundary(inactive, "issue")() is result
    checks += 1
    print(f"early_proof_selfcheck=PASS cases={checks} network_calls=0 database_calls=0")


asyncio.run(main())
