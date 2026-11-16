"""The outer ASGI boundary, not proof of a rendered result or T113 readiness."""

import asyncio
import json
from contextlib import asynccontextmanager
from time import monotonic
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from twobrain_rec_server.api.product_analytics_guard import ProductAnalyticsIngressGuard
from twobrain_rec_server.auth import session_renewal

PATHS = [
    "/meetings/70000000-0000-0000-0000-000000000001/result-viewed",
    "/desktop/meetings/70000000-0000-0000-0000-000000000001/result-viewed",
]


async def _request(app, *, path=PATHS[0], chunks=None, headers=None, method="POST", delay=0):
    chunks = list(chunks if chunks is not None else [b'{"proof":"synthetic"}'])
    output = []
    consumed = 0
    ended = asyncio.Event()

    async def receive():
        nonlocal consumed
        if chunks:
            if delay:
                await asyncio.sleep(delay)
            value = chunks.pop(0)
            consumed += len(value)
            return {"type": "http.request", "body": value, "more_body": bool(chunks)}
        await ended.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        output.append(message.copy())
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            ended.set()

    scope = dict(type="http", asgi={"version": "3.0"}, http_version="1.1", method=method,
                 scheme="https", path=path, raw_path=path.encode(), query_string=b"",
                 headers=headers if headers is not None else [(b"content-type", b"application/json")],
                 client=("127.0.0.1", 1), server=("test", 443), state={})
    began = monotonic()
    await app(scope, receive, send)
    elapsed = monotonic() - began
    start = [m for m in output if m["type"] == "http.response.start"]
    assert len(start) == 1
    body = b"".join(m.get("body", b"") for m in output if m["type"] == "http.response.body")
    return start[0], body, elapsed, consumed


def _accepted(calls):
    async def app(scope, receive, send):
        calls.append(scope)
        body = bytearray()
        while True:
            message = await receive()
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        assert json.loads(body)["proof"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"status":"accepted"}'})
    return app


@pytest.mark.parametrize("path", PATHS)
def test_valid_json_replays_only_its_bounded_body_and_keeps_private_response(path):
    calls = []
    start, body, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), path=path,
        chunks=[b'{"proof":', b'"synthetic"}'],
    ))
    assert start["status"] == 200 and json.loads(body) == {"status": "accepted"}
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"
    assert len(calls) == 1


@pytest.mark.parametrize("body", [
    b"", b"null", b"[]", b"5", b'{"proof":5}', b'{"proof":null}',
    b'{"proof":""}', b'{"proof":"x","owner":"forged"}',
    b'{"proof":"x","proof":"y"}', b'{"proof":"\\u0410"}',
    b'{"proof":"x"} trailing', b'{"proof":NaN}',
    json.dumps({"proof": "x" * 1537}).encode(),
])
def test_ambiguous_or_non_ascii_json_is_rejected_before_downstream(body):
    calls = []
    start, raw, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[body]))
    assert start["status"] == 400
    assert json.loads(raw) == {"status": "unavailable"}
    assert not calls


@pytest.mark.parametrize("media", [b"application/x-www-form-urlencoded", b"multipart/form-data; boundary=x", b"text/plain"])
def test_non_json_never_enters_body_form_or_auth(media):
    calls = []
    start, body, _, consumed = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[b"proof=synthetic"],
        headers=[(b"content-type", media)],
    ))
    assert start["status"] == 415 and json.loads(body) == {"status": "unavailable"}
    assert not calls and consumed == 0


@pytest.mark.parametrize("declared", [None, b"1", b"2049"])
def test_actual_size_limit_cannot_be_bypassed_by_content_length(declared):
    calls = []
    headers = [(b"content-type", b"application/json")]
    if declared is not None:
        headers.append((b"content-length", declared))
    start, body, _, consumed = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), headers=headers,
        chunks=[b'{"proof":"x"}', b" " * 2048],
    ))
    assert start["status"] == 413 and json.loads(body) == {"status": "unavailable"}
    assert consumed == (0 if declared == b"2049" else 2061)
    assert not calls


def test_exact_body_and_proof_limits_are_accepted():
    calls = []
    value = json.dumps({"proof": "x" * 1536}).encode()
    start, _, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[value + b" " * (2048 - len(value))],
    ))
    assert start["status"] == 200 and len(calls) == 1


def test_slow_receive_uses_the_outer_deadline_without_a_live_request_tail():
    async def scenario():
        before = set(asyncio.all_tasks())
        calls = []
        start, body, elapsed, _ = await _request(
            ProductAnalyticsIngressGuard(_accepted(calls)), delay=3,
        )
        assert elapsed < 2 and start["status"] == 200
        assert json.loads(body) == {"status": "unavailable"} and not calls
        assert set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("path", PATHS)
def test_outer_deadline_covers_real_post_response_renewal(monkeypatch, path):
    async def scenario():
        calls, exited = [], []

        async def commit():
            calls.append("commit")

        @asynccontextmanager
        async def sessions():
            try:
                yield SimpleNamespace(commit=commit)
            finally:
                await asyncio.sleep(0.05)
                exited.append(True)

        async def apply(*args):
            pass

        async def activity(*args, **kwargs):
            calls.append("renewal")
            await asyncio.sleep(3)

        monkeypatch.setattr(session_renewal, "apply_tenant_context", apply)
        monkeypatch.setattr(session_renewal, "record_session_activity", activity)
        app = FastAPI()
        app.state.db_sessionmaker = sessions
        app.state.settings = SimpleNamespace(auth_session_ttl_seconds=3600)
        app.middleware("http")(session_renewal.session_renewal_middleware)

        @app.post(path)
        async def endpoint(request: Request):
            request.state.auth_session_renewal = ("synthetic", object(), object(), object())
            return JSONResponse({"status": "accepted"})

        before = set(asyncio.all_tasks())
        start, body, elapsed, _ = await _request(ProductAnalyticsIngressGuard(app), path=path)
        assert elapsed < 2
        assert calls == ["renewal"] and exited == [True]
        assert start["status"] == 200 and json.loads(body) == {"status": "unavailable"}
        assert set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("status", [401, 403, 422])
def test_auth_and_csrf_failures_keep_their_status(status):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b'{"code":"synthetic_auth_refusal"}'})

    start, body, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(app)))
    assert start["status"] == status and json.loads(body)["code"] == "synthetic_auth_refusal"
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"


@pytest.mark.parametrize("failure", ["raise_after_start", "large_body", "many_parts", "incomplete", "two_starts"])
def test_partial_oversized_or_failed_internal_response_cannot_leak_accepted(failure):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        if failure == "raise_after_start":
            raise RuntimeError("synthetic private exception must not be echoed")
        if failure == "two_starts":
            await send({"type": "http.response.start", "status": 200, "headers": []})
        if failure == "many_parts":
            for _ in range(33):
                await send({"type": "http.response.body", "body": b"", "more_body": True})
        await send({"type": "http.response.body", "body": b"x" * 4097 if failure == "large_body" else b"",
                    "more_body": failure == "incomplete"})

    start, body, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(app)))
    assert start["status"] == 200 and json.loads(body) == {"status": "unavailable"}


def test_send_failure_never_starts_a_second_response():
    async def scenario():
        starts = 0

        async def send(message):
            nonlocal starts
            if message["type"] == "http.response.start":
                starts += 1
            raise OSError("synthetic disconnected transport")

        guard = ProductAnalyticsIngressGuard(_accepted([]))

        async def receive():
            return {"type": "http.request", "body": b'{"proof":"x"}', "more_body": False}

        await guard(dict(type="http", method="POST", path=PATHS[0],
                         headers=[(b"content-type", b"application/json")]), receive, send)
        assert starts == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("refusal", ["media", "length", "timeout"])
@pytest.mark.parametrize("blocked_message", ["http.response.start", "http.response.body"])
def test_own_refusal_send_keeps_the_original_hard_deadline(refusal, blocked_message):
    async def scenario():
        calls, messages, cancelled = [], [], []

        async def app(scope, receive, send):
            calls.append(True)
            await asyncio.sleep(10)

        async def receive():
            return {"type": "http.request", "body": b'{"proof":"x"}', "more_body": False}

        async def send(message):
            messages.append(message.copy())
            if message["type"] == blocked_message:
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(True)

        headers = [(b"content-type", b"text/plain" if refusal == "media" else b"application/json")]
        if refusal == "length":
            headers.append((b"content-length", b"2049"))
        scope = dict(type="http", method="POST", path=PATHS[0], headers=headers)
        before = set(asyncio.all_tasks())
        began = monotonic()
        completed = False
        try:
            # The test watchdog stops the old unbounded send; it is not a request budget.
            await asyncio.wait_for(ProductAnalyticsIngressGuard(app)(scope, receive, send), timeout=2.3)
            completed = True
        except TimeoutError:
            pass
        elapsed = monotonic() - began
        assert completed and elapsed < 2.15
        assert calls == ([True] if refusal == "timeout" else [])
        starts = [m for m in messages if m["type"] == "http.response.start"]
        assert len(starts) == 1 and starts[0]["status"] == {"media": 415, "length": 413, "timeout": 200}[refusal]
        assert cancelled == [True] and set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


def test_disconnect_during_body_returns_without_reply_or_downstream_work():
    async def scenario():
        calls, messages = [], []

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        await ProductAnalyticsIngressGuard(_accepted(calls))(
            dict(type="http", method="POST", path=PATHS[0],
                 headers=[(b"content-type", b"application/json")]), receive, send,
        )
        assert not calls and not messages
    asyncio.run(scenario())


@pytest.mark.parametrize("path,method", [("/unrelated", "POST"), (PATHS[0], "GET"),
                                        (PATHS[0] + "/", "POST")])
def test_other_routes_and_methods_are_passed_through(path, method):
    calls = []
    start, _, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(_accepted(calls)), path=path, method=method))
    assert start["status"] == 200 and len(calls) == 1
    assert b"cache-control" not in dict(start["headers"])


@pytest.mark.parametrize("component", ["70000000000000000000000000000001", "{70000000-0000-0000-0000-000000000001}", "not-uuid"])
def test_noncanonical_uuid_or_invalid_component_cannot_bypass_the_route_boundary(component):
    calls = []
    start, _, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), path=f"/meetings/{component}/result-viewed",
    ))
    assert start["status"] == 200 and len(calls) == 1
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"
