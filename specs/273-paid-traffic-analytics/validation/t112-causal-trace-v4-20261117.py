"""Temporary native-test observer; no response bodies, SQL payload or extra I/O."""

import asyncio
from collections import Counter
from contextvars import ContextVar
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time
import types

import httpx
import pytest


TEST = "test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation"
PINS = {
    "test_result_view_http_integration.py": "1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0",
    "test_result_view_http_budget.py": "f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7",
    "product_analytics_guard.py": "7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6",
}


def nested(code):
    yield code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            yield from nested(value)


@pytest.fixture(autouse=True)
def causal_trace(request, monkeypatch):
    if request.node.originalname != TEST:
        yield
        return
    from twobrain_rec_server.api import product_analytics_guard as guard

    native = {code.co_name: code for code in nested(request.node.function.__code__)}
    relay = {code.co_name: code for code in nested(inspect.unwrap(request.module._postgres_response_gate).__code__)}
    for path in (Path(request.module.__file__), Path(relay["copy"].co_filename), Path(guard.__file__)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == PINS[path.name], "observer source pin changed"
    fault = request.node.callspec.params["fault"]
    active = ContextVar("t112_causal_post", default=None)
    records, counts = [], Counter()
    case_start = time.monotonic()
    case = "fault" if fault else "normal"
    state = {"target": {}, "streams": [], "post_number": 0, "relay_counts": Counter()}
    previous = sys.gettrace()
    if previous is not None:
        raise RuntimeError("diagnostic refuses to replace an active tracer")
    original_post = httpx.AsyncClient.post
    original_init = httpx.ASGITransport.__init__
    guard_lines = {
        guard._guard_result_view.__code__: {521, 538, 590, 598, 600, 603, 604},
        guard._run_result_view_operation.__code__: {488, 489, 490, 492, 496, 499, 502, 504, 505, 507, 509},
        guard._result_view_unavailable.__code__: {458, 459, 463, 467, 470},
    }
    join = next(code for code in nested(guard._run_result_view_operation.__code__) if code.co_name == "join")
    guard_lines[join] = {483, 484}
    observer = native["observe_committed_pair"]
    scenario = native["scenario"]
    commit = native["commit"]
    watchdog = native["release_for_failed_test"]
    copy = relay["copy"]
    relay_root = relay["relay"]
    timeout_at = asyncio.timeout_at.__code__
    test_lines = {
        scenario: {1015, 1182, 1271},
        commit: {1065, 1066},
        observer: {1109, 1110, 1115, 1117, 1118, 1131, 1134, 1135},
        watchdog: {1139, 1140},
        copy: {138, 141, 142, 143, 144, 145, 146, 147, 149, 150, 153},
        relay_root: {158, 160, 172},
    }

    def append(event, **values):
        counts[event] += 1
        if len(records) < 96:
            records.append({"event": event, "case": case,
                            "t": round(time.monotonic() - case_start, 6), **values})
        else:
            counts["dropped"] += 1

    def task_state(task):
        return None if task is None else {"done": task.done(), "cancelling": task.cancelling()}

    def snapshot():
        target = state["target"]
        stream = target.get("stream", {})
        facts = target.get("facts", {})
        now = time.monotonic()
        return {
            "entered": state.get("entered") is not None and state["entered"].is_set(),
            "response_held": stream.get("response_held") is not None and stream["response_held"].is_set(),
            "response_gate": stream.get("response_gate") is not None and stream["response_gate"].is_set(),
            "eof_seen": stream.get("eof_seen") is not None and stream["eof_seen"].is_set(),
            "client_eof_seen": stream.get("client_eof_seen") is not None and stream["client_eof_seen"].is_set(),
            "relay_done": stream.get("done") is not None and stream["done"].is_set(),
            "commit_elapsed": round(now - target["commit_at"], 6) if "commit_at" in target else None,
            "work_remaining": round(facts["work_deadline"] - now, 6) if "work_deadline" in facts else None,
            "hard_remaining": round(facts["cleanup_deadline"] - now, 6) if "cleanup_deadline" in facts else None,
            "post_task": task_state(state.get("post")), "db_task": task_state(target.get("task")),
            "relay_root": task_state(stream.get("root")),
            "pumps": [task_state(t) for t in stream.get("pumps", ())],
            "watchdog_fired": state.get("watchdog_fired", False),
        }

    def trace(frame, event, arg):
        code, line, local = frame.f_code, frame.f_lineno, frame.f_locals
        if code is timeout_at:
            frame.f_trace_lines = False
            if event == "call" and frame.f_back is not None and frame.f_back.f_code is observer:
                append("m1_selected_deadline", remaining=round(local["when"] - time.monotonic(), 6), **snapshot())
            return trace
        if code in test_lines:
            frame.f_trace_lines = True
            frame.f_trace_opcodes = False
            if code is scenario and event == "line":
                for key in ("target", "streams", "entered", "post", "observer", "watchdog_fired"):
                    if key in local:
                        state[key] = local[key]
                if line == 1271:
                    append("scenario_before_finally", **snapshot())
                return trace
            if code in (copy, relay_root):
                stream = local.get("stream")
                ordinal = next((i + 1 for i, s in enumerate(state["streams"]) if s is stream), None)
                if ordinal is not None and event == "line" and line in test_lines[code]:
                    state["relay_counts"][(min(ordinal, 5), code.co_name, line)] += 1
                if stream is not state["target"].get("stream") or stream is None or not state["target"].get("facts"):
                    return trace
                extra = {"stream_ordinal": ordinal, "held_direction": local.get("held")}
            else:
                extra = {}
            if code is watchdog and event == "line" and line == 1140:
                state["watchdog_fired"] = True
            if event == "line" and line in test_lines[code]:
                append("native_line", function=code.co_name, line=line, **extra, **snapshot())
            elif event == "exception" and arg[0] not in (StopIteration, StopAsyncIteration):
                append("native_exception", function=code.co_name, line=line,
                       exception_type=arg[0].__name__, **extra, **snapshot())
            return trace
        marker = active.get()
        if code not in guard_lines or marker is None or not (fault or marker[0] == 2):
            return None
        frame.f_trace_lines = True
        frame.f_trace_opcodes = False
        data = {"post": marker[0], "function": code.co_name, "line": line,
                "post_elapsed": round(time.monotonic() - marker[1], 6)}
        now = time.monotonic()
        for name in ("deadline", "work_deadline"):
            if name in local:
                data[name + "_remaining"] = round(local[name] - now, 6)
        owner = local.get("owner")
        if owner is not None:
            data.update(failed=owner.failed, leases=len(owner), transactions=len(owner.transactions),
                        unbound_roots=len(owner.unbound_roots))
        for name in ("pending", "db_tasks"):
            if name in local:
                data[name] = [task_state(t) for t in local[name]]
        if "task" in local:
            data["operation_task"] = task_state(local["task"])
        if "messages" in local:
            messages = local["messages"]
            data.update(buffer_count=len(messages), response_bytes=local["response_bytes"],
                        starts=sum(m["type"] == "http.response.start" for m in messages),
                        terminal_body=bool(messages and messages[-1]["type"] == "http.response.body"
                                           and not messages[-1].get("more_body", False)))
        if "response_started" in local:
            data["response_started"] = local["response_started"]
        if event == "line" and line in guard_lines[code]:
            append("guard_line", **data)
        elif event == "exception" and arg[0] not in (StopIteration, StopAsyncIteration):
            append("guard_exception", exception_type=arg[0].__name__, **data)
        return trace

    def transport_init(transport, app, *args, **kwargs):
        async def observed_app(scope, receive, send):
            marker = active.get()
            selected = marker is not None and (fault or marker[0] == 2)

            async def observed_send(message):
                if selected:
                    append("send_attempted", post=marker[0], type=message["type"],
                           status=message.get("status"), more_body=message.get("more_body", False))
                await send(message)
                if selected:
                    append("send_completed", post=marker[0], type=message["type"],
                           status=message.get("status"), more_body=message.get("more_body", False))

            try:
                await app(scope, receive, observed_send)
            except BaseException as error:
                if selected:
                    append("app_raise", post=marker[0], exception_type=type(error).__name__)
                raise
            else:
                if selected:
                    append("app_return", post=marker[0])
        return original_init(transport, observed_app, *args, **kwargs)

    async def post(client, *args, **kwargs):
        state["post_number"] += 1
        number = state["post_number"]
        token = active.set((number, time.monotonic()))
        append("post_enter", post=number)
        response = None
        try:
            response = await original_post(client, *args, **kwargs)
            return response
        except BaseException as error:
            append("post_raise", post=number, exception_type=type(error).__name__, **snapshot())
            raise
        finally:
            active.reset(token)
            append("post_leave", post=number, http_status=response.status_code if response is not None else None)

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    monkeypatch.setattr(httpx.ASGITransport, "__init__", transport_init)
    sys.settrace(trace)
    try:
        yield
    finally:
        sys.settrace(previous)
        relay_counts = [{"stream_ordinal": k[0], "function": k[1], "line": k[2], "count": v}
                        for k, v in sorted(state["relay_counts"].items())]
        print(json.dumps({"t112_causal_trace": records, "counts": dict(counts), "relay_counts": relay_counts,
                          "tracer_restored": sys.gettrace() is previous}, sort_keys=True))
        state.clear()
