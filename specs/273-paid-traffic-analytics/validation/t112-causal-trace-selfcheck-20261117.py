"""Exercise trace with partially initialized synthetic frames; no HTTP or DB."""
import ast
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
             and n.name in {"append", "task_state", "snapshot", "trace"}]
assert len(functions) == 4
code = compile("pass", "synthetic-guard", "exec")
private = b"synthetic-private-body-never-in-records"


def check(event, line, local, *, error=RuntimeError, expected=None, inactive=False):
    records, counts = [], Counter()
    active = ContextVar("synthetic_trace", default=None if inactive else (2, time.monotonic()))
    env = dict(records=records, counts=counts, state={"target": {}}, active=active,
               fault=False, case="normal", case_start=time.monotonic(), time=time,
               timeout_at=object(), observer=object(), test_lines={}, guard_lines={code: {590}})
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), env)
    frame = SimpleNamespace(f_code=code, f_lineno=line, f_locals=local)
    result = env["trace"](frame, event, (error, error("synthetic"), None) if event == "exception" else None)
    assert result is (None if inactive else env["trace"])
    assert private.decode() not in repr(records)
    if expected is None:
        assert records == [] and counts == {}
    else:
        assert len(records) == 1 and records[0]["event"] == expected
        assert records[0].get("response_bytes") == local.get("response_bytes")
        assert counts == {expected: 1}


# Guard line569 runs before response_bytes=0, immediately after messages=[].
check("line", 569, {"messages": []})
check("exception", 569, {"messages": []}, expected="guard_exception")
check("line", 590, {"messages": []}, expected="guard_line")
check("line", 590, {"messages": [{"type": "http.response.body", "body": private}],
                    "response_bytes": 31}, expected="guard_line")
check("call", 590, {"messages": []})
check("return", 590, {"messages": []})
check("exception", 569, {"messages": []}, error=StopIteration)
check("line", 590, {"messages": []}, inactive=True)
print("causal_trace_selfcheck=PASS cases=8 network_calls=0 database_calls=0")
