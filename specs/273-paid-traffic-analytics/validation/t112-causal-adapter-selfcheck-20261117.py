"""Exercise only adapter/delegation functions with synthetic callables; no I/O."""
import ast
import asyncio
from collections import Counter
from contextvars import ContextVar
from pathlib import Path
import sys
import time
from types import SimpleNamespace

source = Path(sys.argv[1])
tree = ast.parse(source.read_text())
fixture = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "causal_trace")
functions = [n for n in fixture.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name in {"append", "task_state", "snapshot", "transport_init", "post"}]
assert len(functions) == 5


def context(fault):
    records, counts = [], Counter()
    state = {"target": {}, "streams": [], "post_number": 0}
    active = ContextVar("synthetic_post", default=None)
    env = dict(records=records, counts=counts, state=state, active=active, fault=fault,
               case="fault" if fault else "normal", case_start=time.monotonic(), time=time)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), env)
    return env


async def adapter_case(*, fault=False, post=2, app_error=None, send_error=None):
    env = context(fault)
    calls = Counter()
    private = b"synthetic-private-proof-body-not-for-observer"
    response_start = {"type": "http.response.start", "status": 200, "headers": [(b"x-private", private)]}
    response_body = {"type": "http.response.body", "body": private}
    scope, receive = {}, object()

    async def app(got_scope, got_receive, send):
        calls["app"] += 1
        assert got_scope is scope and got_receive is receive
        await send(response_start)
        if app_error is not None:
            raise app_error
        await send(response_body)

    async def send(message):
        calls["send"] += 1
        assert message is (response_start if calls["send"] == 1 else response_body)
        if send_error is not None:
            raise send_error

    def init(transport, original_app, *args, **kwargs):
        calls["init"] += 1
        assert args == ("synthetic-arg",) and kwargs == {"sentinel": True}
        transport.app = original_app
        return None

    env["original_init"] = init
    transport = SimpleNamespace()
    assert env["transport_init"](transport, app, "synthetic-arg", sentinel=True) is None
    token = env["active"].set((post, time.monotonic()))
    wanted = send_error if send_error is not None else app_error
    try:
        await transport.app(scope, receive, send)
    except BaseException as error:
        assert error is wanted
    else:
        assert wanted is None
    finally:
        env["active"].reset(token)
    assert calls["init"] == calls["app"] == 1
    assert calls["send"] == (1 if wanted is not None else 2)
    events = [r["event"] for r in env["records"]]
    if not fault and post == 1:
        assert events == []
    elif send_error is not None:
        assert events == ["send_attempted", "app_raise"]
    elif app_error is not None:
        assert events == ["send_attempted", "send_completed", "app_raise"]
    else:
        assert events == ["send_attempted", "send_completed", "send_attempted", "send_completed", "app_return"]
    assert private.decode() not in repr(env["records"])


async def post_case(error=None):
    env = context(False)
    calls = []
    response = SimpleNamespace(status_code=200)
    client, arguments, options = object(), (object(),), {"synthetic": object()}

    async def original(got_client, *args, **kwargs):
        assert got_client is client and args == arguments and kwargs == options
        calls.append(env["active"].get()[0])
        if error is not None:
            raise error
        return response

    env["original_post"] = original
    try:
        result = await env["post"](client, *arguments, **options)
        assert result is response and error is None
    except BaseException as caught:
        assert caught is error
    assert calls == [1] and env["active"].get() is None
    assert [r["event"] for r in env["records"]] == (
        ["post_enter", "post_leave"] if error is None else ["post_enter", "post_raise", "post_leave"])


async def main():
    await adapter_case(post=1)
    await adapter_case()
    await adapter_case(fault=True, post=1)
    await adapter_case(app_error=RuntimeError("synthetic-app"))
    await adapter_case(send_error=OSError("synthetic-send"))
    await adapter_case(send_error=asyncio.CancelledError())
    await post_case()
    await post_case(RuntimeError("synthetic-original"))
    await post_case(asyncio.CancelledError())
    env = context(False)
    for _ in range(100):
        env["append"]("synthetic")
    assert len(env["records"]) == 96 and env["counts"] == {"synthetic": 100, "dropped": 4}
    print("causal_adapter_selfcheck=PASS cases=10 network_calls=0 database_calls=0")


asyncio.run(main())
