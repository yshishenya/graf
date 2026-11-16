"""Pure wrapper checks and exact reversal of the enumerated native-test edits; no HTTP/DB."""
import ast
import asyncio
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path

SOURCE_HASH = "1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0"
TEST = "test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation"
FOOTER = "\n# BEGIN NORMAL DIAGNOSTIC HELPERS (inert until the selected False test runs)\n"
# Each replacement is unique inside this one test; reversal cannot discard arbitrary statements.
EDITS = [
    ('    provider_calls = []\n', '    diag = _NormalObservation(fault)\n    provider_calls = []\n'),
    ('httpx.ASGITransport(app=app)', 'httpx.ASGITransport(app=diag.app(app))'),
    ('                    assert page.status_code == 200 and len(_proofs(page.text)) == 2\n',
     '                    diag.get_status(page.status_code)\n                    assert page.status_code == 200 and len(diag.proofs(_proofs, page.text)) == 2\n'),
    ('                    proof = _proofs(page.text)[0]\n',
     '                    proof = diag.proofs(_proofs, page.text)[0]\n'),
    ('post = asyncio.create_task(client.post(path + "/result-viewed",',
     'post = asyncio.create_task(diag.post(1, client.post, path + "/result-viewed",'),
    ('                        assert request_engine.pool.checkedout() == 1\n',
     '                        assert request_engine.pool.checkedout() == 1\n                        diag.step("early_cleanup")\n'),
    ('                        target["stream"]["response_gate"].set()\n',
     '                        diag.step("borrower_before_gate")\n                        target["stream"]["response_gate"].set()\n                        diag.step("gate_opened")\n'),
    ('                        assert not driver.is_closed() and not driver.is_in_transaction()\n',
     '                        assert not driver.is_closed() and not driver.is_in_transaction()\n                        diag.step("borrower_after_gate")\n'),
    ('repeated = await client.post(path + "/result-viewed",',
     'repeated = await diag.post(2, client.post, path + "/result-viewed",'),
    ('                    assert repeated.json() == {"status": "accepted"}\n',
     '                    assert repeated.json() == {"status": "accepted"}\n                    diag.step("post2_json")\n'),
    ('                        assert await pair_snapshot(db) == saved\n',
     '                        assert await pair_snapshot(db) == saved\n                    diag.step("post2_rows")\n'),
    ('                    assert request_engine.pool.checkedout() == 0\n            finally:\n',
     '                    assert request_engine.pool.checkedout() == 0\n                    diag.step("scenario_complete")\n            finally:\n'),
    ('            finally:\n                armed = False\n',
     '            finally:\n                diag.snapshot(target, entered, markers, returns, checkouts, post, observer,\n                              watchdog_fired, _normal_sys.exception())\n                armed = False\n'),
    ('    _run(postgres_seeded_database_url, scenario)\n',
     '    try:\n        _run(postgres_seeded_database_url, scenario)\n    finally:\n        diag.finish(_normal_sys.exception())\n'),
]


def native_parts(source):
    tree = ast.parse(source)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == TEST)
    start = min([node.lineno] + [item.lineno for item in node.decorator_list]) - 1
    lines = source.splitlines(keepends=True)
    assert node.end_lineno == len(lines), "native test must remain the final original definition"
    return ''.join(lines[:start]), ''.join(lines[start:])


def restore(original, probe):
    prefix, native = native_parts(original)
    assert probe.count(FOOTER) == 1
    body, helpers = probe.split(FOOTER)
    assert body.startswith(prefix) and body.endswith('\n')
    modified = body[len(prefix):]
    for before, after in reversed(EDITS):
        assert modified.count(after) == 1, "missing/duplicate exact diagnostic insertion"
        modified = modified.replace(after, before, 1)
    restored = prefix + modified
    assert restored == original, "an original statement/assertion/await/order was changed"
    assert ast.dump(ast.parse(restored)) == ast.dump(ast.parse(original))
    helper_tree = ast.parse(helpers)
    assert [(type(n).__name__, getattr(n, 'name', None)) for n in helper_tree.body] == [
        ('Import', None), ('ImportFrom', None), ('Assign', None), ('Assign', None),
        ('ClassDef', '_NormalObservation'),
    ], "extra executable module statement"
    return restored


async def check_wrappers(module):
    Observation, active = module._NormalObservation, module._NORMAL_POST
    try:
        Observation(True)
    except ValueError:
        pass
    else:
        raise AssertionError("fault execution allowed")
    obs = Observation(False)
    marker = object()
    calls = []

    class NoPayload:
        def __getattribute__(self, name):
            raise AssertionError("response payload/attribute was read")

    response = NoPayload()

    async def original(*args, **kwargs):
        assert active.get() == 1
        calls.append((args, kwargs))
        return response

    outer = active.set(2)
    try:
        assert await obs.post(1, original, marker, same=marker) is response
        assert active.get() == 2
        assert calls == [((marker,), {'same': marker})]
        for error in (RuntimeError('PRIVATE'), asyncio.CancelledError('PRIVATE')):
            calls.clear()

            async def failing(*args, failure=error, **kwargs):
                calls.append((args, kwargs))
                assert active.get() == 1
                raise failure

            try:
                await obs.post(1, failing, marker, same=marker)
            except BaseException as caught:
                assert caught is error
            else:
                raise AssertionError('exception swallowed')
            assert active.get() == 2
            assert calls == [((marker,), {'same': marker})]
    finally:
        active.reset(outer)
    assert active.get() is None

    waiting = asyncio.Event()
    cancelled = Observation(False)
    caught_cancel = []

    async def blocked():
        waiting.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError as error:
            caught_cancel.append(error)
            raise

    task = asyncio.create_task(cancelled.post(1, blocked))
    await waiting.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError as error:
        assert caught_cancel == [error]
    else:
        raise AssertionError('task cancellation swallowed')
    assert task.cancelled() and active.get() is None
    assert cancelled.requests[1]['post_raise'] == 1

    # Counting uses only the existing parse result and returns its exact identity.
    class Proofs:
        def __len__(self):
            return 2

        def __iter__(self):
            raise AssertionError('proof values read')

        def __getitem__(self, key):
            raise AssertionError('proof values read')

    result = Proofs()
    proof_calls = []

    def parse(html):
        proof_calls.append(html is marker)
        return result

    assert obs.proofs(parse, marker) is result and proof_calls == [True]
    assert obs.get == {'status': None, 'proof_count': 2, 'proof_calls': 1}
    fresh = Observation(False)
    assert fresh.get['proof_count'] is None
    status = 403
    assert not (status == 200 and len(fresh.proofs(parse, marker)) == 2)
    assert fresh.get['proof_count'] is None and proof_calls == [True]

    # ASGI double accepts only type/status/more_body; body/headers/path/query cannot be read.
    class Message(dict):
        def get(self, key, default=None):
            assert key in {'type', 'status', 'more_body'}
            return super().get(key, default)

    class Scope(dict):
        def get(self, key, default=None):
            assert key == 'state'
            return super().get(key, default)

    async def receive():
        raise AssertionError('extra receive')

    messages = [Message(type='http.response.start', status=200),
                Message(type='http.response.body', more_body=True),
                Message(type='http.response.body', more_body=False)]
    scope = Scope(state={'result_view_deadline': 10., 'result_view_cleanup_deadline': 10.5})
    received = []

    async def send(message):
        received.append(message)
        return marker

    async def app(actual_scope, actual_receive, actual_send):
        assert actual_scope is scope and actual_receive is receive
        for message in messages:
            assert await actual_send(message) is marker
        return response

    token = active.set(1)
    try:
        assert await fresh.app(app)(scope, receive, send) is response
    finally:
        active.reset(token)
    assert len(received) == 3 and all(a is b for a, b in zip(received, messages, strict=True))
    facts = fresh.requests[1]
    assert (facts['start_attempted'], facts['start_completed'], facts['body_attempted'],
            facts['body_completed'], facts['terminal_attempted'], facts['terminal_completed']) == (1, 1, 2, 2, 1, 1)
    assert facts['app_return'] == 1 and facts['app_raise'] == 0
    assert facts['work_deadline'] == 10. and facts['hard_deadline'] == 10.5
    assert fresh.requests[2]['work_deadline'] is None

    second_scope = Scope(state={'result_view_deadline': 20., 'result_view_cleanup_deadline': 20.5})

    async def second_app(actual_scope, actual_receive, actual_send):
        assert actual_scope is second_scope and actual_receive is receive
        for message in messages:
            await actual_send(message)
        return response

    token = active.set(2)
    try:
        assert await fresh.app(second_app)(second_scope, receive, send) is response
    finally:
        active.reset(token)
    assert fresh.requests[1]['work_deadline'] == 10. and fresh.requests[2]['work_deadline'] == 20.

    # Send failure and cancellation retain attempted/completed distinction and exception identity.
    for error in (ValueError('PRIVATE'), asyncio.CancelledError('PRIVATE')):
        for failed_index in (0, 2):
            failed = Observation(False)
            received.clear()

            async def failing_send(message, index=failed_index, failure=error):
                received.append(message)
                if len(received) == index + 1:
                    raise failure
                return marker

            token = active.set(2)
            try:
                try:
                    await failed.app(app)(scope, receive, failing_send)
                except BaseException as caught:
                    assert caught is error
                else:
                    raise AssertionError('ASGI error swallowed')
            finally:
                active.reset(token)
            facts = failed.requests[2]
            assert facts['app_return'] == 0 and facts['app_raise'] == 1
            assert facts['start_attempted'] == 1
            assert facts['start_completed'] == (failed_index != 0)
            assert facts['terminal_attempted'] == (failed_index == 2) and facts['terminal_completed'] == 0
            assert len(received) == failed_index + 1
            assert all(a is b for a, b in zip(received, messages, strict=False))

        async def raising_app(actual_scope, actual_receive, actual_send, failure=error):
            assert actual_scope is scope and actual_receive is receive
            raise failure

        token = active.set(1)
        failed = Observation(False)
        try:
            try:
                await failed.app(raising_app)(scope, receive, send)
            except BaseException as caught:
                assert caught is error
            else:
                raise AssertionError('app error swallowed')
        finally:
            active.reset(token)
        assert failed.requests[1]['app_raise'] == 1 and failed.requests[1]['body_attempted'] == 0

    # GET passes the original send unchanged and does not acquire POST1/POST2 deadlines.
    async def direct(actual_scope, actual_receive, actual_send):
        assert actual_scope is scope and actual_receive is receive and actual_send is send
        return response

    fresh = Observation(False)
    assert await fresh.app(direct)(scope, receive, send) is response
    assert fresh.requests[1]['work_deadline'] is fresh.requests[2]['work_deadline'] is None

    # Fixed summaries and final snapshot survive a full detail buffer.
    for _ in range(55):
        fresh.step('early_cleanup')
    assert len(fresh.records) == 48 and fresh.dropped == 7
    assert fresh.stages['early_cleanup'] == 55

    async def capped_post():
        return await fresh.app(app)(scope, receive, send)

    assert await fresh.post(2, capped_post) is response
    assert len(fresh.records) == 48 and fresh.dropped > 7
    assert fresh.requests[2]['post_return'] == fresh.requests[2]['terminal_completed'] == 1
    assert fresh.requests[2]['app_return'] == 1 and fresh.requests[1]['post_return'] == 0
    # Clear only the synthetic test scope's deadlines through an actual empty state.
    empty_scope = Scope()

    async def empty_app(actual_scope, actual_receive, actual_send):
        assert actual_scope is empty_scope
        return response

    token = active.set(2)
    try:
        assert await fresh.app(empty_app)(empty_scope, receive, send) is response
    finally:
        active.reset(token)
    entered = asyncio.Event()
    current = asyncio.current_task()
    fresh.snapshot({}, entered, [], [], [], current, None, False, None)
    snap = fresh.final_snapshot
    assert snap['snapshot_error'] is None and snap['db_task_done'] is None
    assert snap['post1_work_deadline_remaining'] is snap['post2_work_deadline_remaining'] is None
    assert snap['post_done'] is False and snap['post_cancelling'] == 0
    gate = asyncio.Event()
    gate.set()
    now = asyncio.get_running_loop().time()
    fresh.snapshot({'stream': {'response_gate': gate}, 'checkout_index': 2,
                    'facts': {'work_deadline': now + 1., 'cleanup_deadline': now + 1.5}},
                   entered, ['commit', 'after_commit', ('reset', True, False, False), 'checkin'],
                   [2, 4], [marker] * 4, current, None, False, RuntimeError('PRIVATE'))
    snap = fresh.final_snapshot
    assert 0 < snap['post1_work_deadline_remaining'] <= 1.
    assert snap['post2_work_deadline_remaining'] is None
    assert snap['return_checkout_offsets'] == [0, 2]
    assert snap['commit_count'] == snap['reset_count'] == snap['checkin_count'] == 1
    assert snap['response_gate'] is True and snap['done'] is None
    assert snap['test_error_type'] == 'RuntimeError' and snap['snapshot_error'] is None
    fresh.snapshot({'stream': {'response_gate': marker}}, entered, [], [], [], None, None, False, None)
    assert fresh.final_snapshot['snapshot_error'] == 'AttributeError'
    output = io.StringIO()
    with redirect_stdout(output):
        fresh.finish(None)
    report = json.loads(output.getvalue())['t112_normal_observation']
    assert len(report['records']) == 48 and report['stages']['early_cleanup'] == 55
    assert 'PRIVATE' not in output.getvalue()
    # A sentinel payload never enters any observer data structure.
    assert 'PRIVATE' not in repr(obs.__dict__)


def main():
    original_path, probe_path = map(Path, sys.argv[1:])
    original = original_path.read_text()
    probe = probe_path.read_text()
    assert sha256(original_path.read_bytes()).hexdigest() == SOURCE_HASH
    restore(original, probe)
    for before, after in [
        ('assert response.status_code == 200', 'assert response.status_code == 201'),
        ('await foreign_healthy()\n                        assert markers.count',
         'await asyncio.sleep(0)\n                        assert markers.count'),
        ('                        diag.step("early_cleanup")\n', ''),
    ]:
        prefix, _ = native_parts(original)
        modified = probe[:len(prefix)] + probe[len(prefix):].replace(before, after, 1)
        assert modified != probe
        try:
            restore(original, modified)
        except AssertionError:
            pass
        else:
            raise AssertionError('normalizer accepted a native mutation')
    spec = importlib.util.spec_from_file_location('t112_native_normal_probe', probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    asyncio.run(check_wrappers(module))
    print('PASS exact source/AST restoration, 3 rejected mutations, wrapper identity/error/cancel, '
          'ContextVar reset, ASGI send/app, proof count, cap and partial snapshot; no HTTP/DB')


if __name__ == '__main__':
    main()
