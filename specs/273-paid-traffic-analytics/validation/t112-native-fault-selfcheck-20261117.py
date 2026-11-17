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
FOOTER = "\n# BEGIN FAULT DIAGNOSTIC HELPERS (inert until the selected True test runs)\n"
# Each replacement is unique inside this one test; reversal cannot discard arbitrary statements.
EDITS = [('    provider_calls = []\n', '    diag = _FaultObservation(fault)\n    provider_calls = []\n'),
 ('httpx.ASGITransport(app=app)', 'httpx.ASGITransport(app=diag.app(app))'),
 ('                    assert page.status_code == 200 and len(_proofs(page.text)) == 2\n',
  '                    diag.get_status(page.status_code)\n'
  '                    assert page.status_code == 200 and len(diag.proofs(_proofs, page.text)) == 2\n'),
 ('                    proof = _proofs(page.text)[0]\n',
  '                    proof = diag.proofs(_proofs, page.text)[0]\n'),
 ('post = asyncio.create_task(client.post(path + "/result-viewed",',
  'post = asyncio.create_task(diag.post(1, client.post, path + "/result-viewed",'),
 ('                        assert request_engine.pool.checkedout() == 1\n',
  '                        assert request_engine.pool.checkedout() == 1\n'
  '                        diag.step("early_cleanup")\n'),
 ('                        target["stream"]["response_gate"].set()\n',
  '                        diag.step("borrower_before_gate")\n'
  '                        target["stream"]["response_gate"].set()\n'
  '                        diag.step("gate_opened")\n'),
 ('                        assert not driver.is_closed() and not driver.is_in_transaction()\n',
  '                        assert not driver.is_closed() and not driver.is_in_transaction()\n'
  '                        diag.step("borrower_after_gate")\n'),
 ('repeated = await client.post(path + "/result-viewed",',
  'repeated = await diag.post(2, client.post, path + "/result-viewed",'),
 ('                    assert repeated.json() == {"status": "accepted"}\n',
  '                    assert repeated.json() == {"status": "accepted"}\n'
  '                    diag.step("post2_json")\n'),
 ('                        assert await pair_snapshot(db) == saved\n',
  '                        assert await pair_snapshot(db) == saved\n'
  '                    diag.step("post2_rows")\n'),
 ('                    assert request_engine.pool.checkedout() == 0\n            finally:\n',
  '                    assert request_engine.pool.checkedout() == 0\n'
  '                    diag.step("scenario_complete")\n'
  '            finally:\n'),
 ('            finally:\n                armed = False\n',
  '            finally:\n'
  '                diag.snapshot(target, entered, markers, returns, checkouts, post, observer,\n'
  '                              watchdog_fired, _fault_sys.exception())\n'
  '                armed = False\n'),
 ('    _run(postgres_seeded_database_url, scenario)\n',
  '    try:\n'
  '        _run(postgres_seeded_database_url, scenario)\n'
  '    finally:\n'
  '        diag.finish(_fault_sys.exception())\n'),
 ('                entered.set()\n',
  '                entered.set()\n'
  '                diag.phase("commit_enter", target, markers, post, watchdog_fired)\n'),
 ('                async with asyncio.timeout_at(min(target["facts"]["work_deadline"] - .1,\n'
  '                                                 asyncio.get_running_loop().time() + .9)):\n',
  '                async with diag.window(asyncio.timeout_at(min(target["facts"]["work_deadline"] - .1,\n'
  '                                                 asyncio.get_running_loop().time() + .9))):\n'),
 ('                    await stream["response_held"].wait()\n',
  '                    diag.phase("hold_wait_enter", target, markers, post, watchdog_fired)\n'
  '                    await stream["response_held"].wait()\n'
  '                    diag.phase("held_observed", target, markers, post, watchdog_fired)\n'),
 ('                        while True:\n                            rows = await pair_snapshot(db)\n',
  '                        while True:\n'
  '                            diag.iteration()\n'
  '                            rows = await pair_snapshot(db)\n'
  '                            diag.boundary("pair")\n'),
 ('                            ), {"pid": target["pid"]})).first()\n                            locks =',
  '                            ), {"pid": target["pid"]})).first()\n'
  '                            diag.boundary("activity")\n'
  '                            locks ='),
 ('                                                    {"pid": target["pid"]})\n'
  '                            if len(rows)',
  '                                                    {"pid": target["pid"]})\n'
  '                            diag.boundary("locks")\n'
  '                            if len(rows)'),
 ('                                    and activity.xact_start is None and locks == 0:\n'
  '                                break\n',
  '                                    and activity.xact_start is None and locks == 0:\n'
  '                                diag.durable(target, markers, post, watchdog_fired, len(rows),\n'
  '                                             activity is not None, activity.state == "idle",\n'
  '                                             activity.xact_start is None, locks)\n'
  '                                break\n'),
 ('                    await foreign_healthy()\n                    target["m1_pair"] = rows\n',
  '                    diag.phase("m1_foreign_enter", target, markers, post, watchdog_fired)\n'
  '                    await foreign_healthy()\n'
  '                    diag.phase("m1_foreign_returned", target, markers, post, watchdog_fired)\n'
  '                    target["m1_pair"] = rows\n'),
 ('                    target["m1_at"] = asyncio.get_running_loop().time()\n',
  '                    target["m1_at"] = asyncio.get_running_loop().time()\n'
  '                    diag.phase("m1_complete", target, markers, post, watchdog_fired)\n'),
 ('                            assert all(w.is_closing() for w in stream["writers"])\n',
  '                            assert all(w.is_closing() for w in stream["writers"])\n'
  '                            diag.cleanup(target, markers, returns, checkouts, post, watchdog_fired)\n'),
 ('                                                   {"pid": target["pid"]}) == 0\n'
  '                        await foreign_healthy()\n',
  '                                                   {"pid": target["pid"]}) == 0\n'
  '                        diag.phase("old_backend_checked", target, markers, post, watchdog_fired)\n'
  '                        await foreign_healthy()\n'),
 ('            async def observe_committed_pair():\n'
  '                await entered.wait()\n'
  '                assert "snapshot_error" not in target and all(target["checks"])\n'
  '                assert markers.count("commit") == 1\n'
  '                if not fault:\n'
  '                    return\n'
  '                stream = target["stream"]\n'
  '                async with diag.window(asyncio.timeout_at(min(target["facts"]["work_deadline"] - .1,\n'
  '                                                 asyncio.get_running_loop().time() + .9))):\n'
  '                    diag.phase("hold_wait_enter", target, markers, post, watchdog_fired)\n'
  '                    await stream["response_held"].wait()\n'
  '                    diag.phase("held_observed", target, markers, post, watchdog_fired)\n'
  '                    async with direct_sessions() as db:\n'
  '                        while True:\n'
  '                            diag.iteration()\n'
  '                            rows = await pair_snapshot(db)\n'
  '                            diag.boundary("pair")\n'
  '                            activity = (await db.execute(text(\n'
  '                                "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"\n'
  '                            ), {"pid": target["pid"]})).first()\n'
  '                            diag.boundary("activity")\n'
  '                            locks = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE '
  'pid=:pid"),\n'
  '                                                    {"pid": target["pid"]})\n'
  '                            diag.boundary("locks")\n'
  '                            if len(rows) == 2 and activity is not None and activity.state == "idle" \\\n'
  '                                    and activity.xact_start is None and locks == 0:\n'
  '                                diag.durable(target, markers, post, watchdog_fired, len(rows),\n'
  '                                             activity is not None, activity.state == "idle",\n'
  '                                             activity.xact_start is None, locks)\n'
  '                                break\n'
  '                            await db.rollback()\n'
  '                            await asyncio.sleep(.01)\n'
  '                    assert not post.done() and not target["task"].cancelling()\n'
  '                    assert "after_commit" not in markers and not stream["response_gate"].is_set()\n'
  '                    diag.phase("m1_foreign_enter", target, markers, post, watchdog_fired)\n'
  '                    await foreign_healthy()\n'
  '                    diag.phase("m1_foreign_returned", target, markers, post, watchdog_fired)\n'
  '                    target["m1_pair"] = rows\n'
  '                    target["m1_at"] = asyncio.get_running_loop().time()\n'
  '                    diag.phase("m1_complete", target, markers, post, watchdog_fired)\n'
  '\n'
  '            def release_for_failed_test():\n',
  '            async def observe_committed_pair():\n'
  '                try:\n'
  '                    await entered.wait()\n'
  '                    assert "snapshot_error" not in target and all(target["checks"])\n'
  '                    assert markers.count("commit") == 1\n'
  '                    if not fault:\n'
  '                        return\n'
  '                    stream = target["stream"]\n'
  '                    async with diag.window(asyncio.timeout_at(min(target["facts"]["work_deadline"] - '
  '.1,\n'
  '                                                     asyncio.get_running_loop().time() + .9))):\n'
  '                        diag.phase("hold_wait_enter", target, markers, post, watchdog_fired)\n'
  '                        await stream["response_held"].wait()\n'
  '                        diag.phase("held_observed", target, markers, post, watchdog_fired)\n'
  '                        async with direct_sessions() as db:\n'
  '                            while True:\n'
  '                                diag.iteration()\n'
  '                                rows = await pair_snapshot(db)\n'
  '                                diag.boundary("pair")\n'
  '                                activity = (await db.execute(text(\n'
  '                                    "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"\n'
  '                                ), {"pid": target["pid"]})).first()\n'
  '                                diag.boundary("activity")\n'
  '                                locks = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE '
  'pid=:pid"),\n'
  '                                                        {"pid": target["pid"]})\n'
  '                                diag.boundary("locks")\n'
  '                                if len(rows) == 2 and activity is not None and activity.state == "idle" '
  '\\\n'
  '                                        and activity.xact_start is None and locks == 0:\n'
  '                                    diag.durable(target, markers, post, watchdog_fired, len(rows),\n'
  '                                                 activity is not None, activity.state == "idle",\n'
  '                                                 activity.xact_start is None, locks)\n'
  '                                    break\n'
  '                                await db.rollback()\n'
  '                                await asyncio.sleep(.01)\n'
  '                        assert not post.done() and not target["task"].cancelling()\n'
  '                        assert "after_commit" not in markers and not stream["response_gate"].is_set()\n'
  '                        diag.phase("m1_foreign_enter", target, markers, post, watchdog_fired)\n'
  '                        await foreign_healthy()\n'
  '                        diag.phase("m1_foreign_returned", target, markers, post, watchdog_fired)\n'
  '                        target["m1_pair"] = rows\n'
  '                        target["m1_at"] = asyncio.get_running_loop().time()\n'
  '                        diag.phase("m1_complete", target, markers, post, watchdog_fired)\n'
  '                except BaseException as error:\n'
  '                    diag.observer_error(error)\n'
  '                    raise\n'
  '\n'
  '            def release_for_failed_test():\n')]


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
        ('ClassDef', '_FaultObservation'),
    ], "extra executable module statement"
    # All 45 original awaits remain in the same order before/after diagnostics.
    native_name = next(n for n in ast.parse(original).body if isinstance(n, ast.FunctionDef) and n.name == TEST)
    observed_name = next(n for n in ast.parse(body).body if isinstance(n, ast.FunctionDef) and n.name == TEST)
    assert sum(isinstance(n, ast.Await) for n in ast.walk(native_name)) == 45
    assert sum(isinstance(n, ast.Await) for n in ast.walk(observed_name)) == 45
    return restored


async def check_wrappers(module):
    Observation, active = module._FaultObservation, module._FAULT_POST
    try:
        Observation(False)
    except ValueError:
        pass
    else:
        raise AssertionError("normal execution allowed")
    for forbidden in (None, 0, 1, 'True'):
        try:
            Observation(forbidden)
        except ValueError:
            pass
        else:
            raise AssertionError('non-exact True allowed')
    obs = Observation(True)
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
    cancelled = Observation(True)
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
    fresh = Observation(True)
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
            failed = Observation(True)
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
        failed = Observation(True)
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

    fresh = Observation(True)
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
    report = json.loads(output.getvalue())['t112_fault_observation']
    assert len(report['records']) == 48 and report['stages']['early_cleanup'] == 55
    assert 'PRIVATE' not in output.getvalue()
    # A sentinel payload never enters any observer data structure.
    assert 'PRIVATE' not in repr(obs.__dict__)



async def check_m1(module):
    Observation = module._FaultObservation
    now = asyncio.get_running_loop().time()
    calls = []
    obs = Observation(True)
    def original_expression():
        calls.append(True)
        return asyncio.timeout_at(min(now + 1.4, now + .9))
    timeout = original_expression()
    deadline = timeout.when()
    assert obs.window(timeout) is timeout
    assert calls == [True] and timeout.when() == deadline == obs.m1['deadline']
    assert timeout.expired() is False

    class Task:
        finished = False
        cancelling_count = 0
        def done(self):
            return self.finished
        def cancelling(self):
            return self.cancelling_count

    def fixture():
        diag = Observation(True)
        gate, held, done = asyncio.Event(), asyncio.Event(), asyncio.Event()
        task, post = Task(), Task()
        target = {'stream': {'response_gate': gate, 'response_held': held, 'done': done},
                  'task': task, 'checks': (True,) * 18,
                  'facts': {'work_deadline': now + 1.5, 'cleanup_deadline': now + 2.}}
        return diag, target, post

    def sequence(diag, target, post, *, omitted=None, complete=True):
        markers = ['commit']
        diag.phase('commit_enter', target, markers, post, False)
        diag.window(asyncio.timeout_at(now + .9))
        diag.phase('hold_wait_enter', target, markers, post, False)
        target['stream']['response_held'].set()
        for phase in ('held_observed', 'durable_idle_observed', 'm1_foreign_enter', 'm1_foreign_returned'):
            if phase == omitted:
                continue
            if phase == 'durable_idle_observed':
                diag.iteration()
                for name in ('pair', 'activity', 'locks'):
                    diag.boundary(name)
                diag.durable(target, markers, post, False, 2, True, True, True, 0)
            else:
                diag.phase(phase, target, markers, post, False)
        if complete:
            target['m1_at'] = asyncio.get_running_loop().time()
            diag.phase('m1_complete', target, markers, post, False)
        return markers

    diag, target, post = fixture()
    for _ in range(55):
        diag.step('early_cleanup')
    sequence(diag, target, post)
    assert diag.m1['valid'] is True and diag.m1['iterations'] == 1
    assert diag.m1['boundary'] == 'locks' and len(diag.records) == 48 and diag.dropped > 7
    diag.snapshot(target, asyncio.Event(), ['commit'], [], [], post, None, False, None)
    assert diag.final_snapshot['m1']['valid'] is True
    assert diag.final_snapshot['observer_done'] is None
    assert diag.final_snapshot['m1_remaining'] > 0
    for omitted in ('held_observed', 'durable_idle_observed', 'm1_foreign_enter', 'm1_foreign_returned'):
        diag, target, post = fixture()
        sequence(diag, target, post, omitted=omitted)
        assert diag.m1['valid'] is False, omitted
    # A fresh complete mark cannot use a late or incomplete earlier phase.
    for mutation in ('late_window', 'late_work', 'missing_target', 'cancelled', 'done',
                     'post_returned', 'gate_open', 'no_held', 'after_commit',
                     'two_commits', 'bad_checks', 'target_error', 'watchdog',
                     'one_row', 'backend_missing', 'transaction', 'locks', 'late_m1_at',
                     'observer_error', 'timeout_error', 'duplicate_foreign'):
        diag, target, post = fixture()
        markers = sequence(diag, target, post, complete=False)
        target['m1_at'] = asyncio.get_running_loop().time()
        watchdog = False
        if mutation == 'late_window':
            diag.m1['deadline'] = now - 1.
        elif mutation == 'late_work':
            target['facts']['work_deadline'] = now - 1.
        elif mutation == 'missing_target':
            target = {}
        elif mutation == 'cancelled':
            target['task'].cancelling_count = 1
        elif mutation == 'done':
            target['task'].finished = True
        elif mutation == 'post_returned':
            post.finished = True
        elif mutation == 'gate_open':
            target['stream']['response_gate'].set()
        elif mutation == 'no_held':
            target['stream']['response_held'].clear()
        elif mutation == 'after_commit':
            markers.append('after_commit')
        elif mutation == 'two_commits':
            markers.append('commit')
        elif mutation == 'bad_checks':
            target['checks'] = (False,)
        elif mutation == 'target_error':
            target['snapshot_error'] = 'ValueError'
        elif mutation == 'watchdog':
            watchdog = True
        elif mutation == 'one_row':
            diag.m1['durable']['rows_count'] = 1
        elif mutation == 'backend_missing':
            diag.m1['durable']['activity_present'] = False
        elif mutation == 'transaction':
            diag.m1['durable']['xact_start_none'] = False
        elif mutation == 'locks':
            diag.m1['durable']['locks'] = 1
        elif mutation == 'late_m1_at':
            target['m1_at'] = now + 4.
        elif mutation == 'observer_error':
            diag.observer_error(ValueError('PRIVATE'))
        elif mutation == 'timeout_error':
            diag.observer_error(TimeoutError('PRIVATE'))
        elif mutation == 'duplicate_foreign':
            diag.phase('m1_foreign_returned', target, markers, post, False)
        diag.phase('m1_complete', target, markers, post, watchdog)
        assert diag.m1['valid'] is False, mutation
        assert 'PRIVATE' not in repr(diag.__dict__)
    # Snapshot is frozen before rescue changes the observer summary.
    diag, target, post = fixture()
    sequence(diag, target, post)
    diag.snapshot(target, asyncio.Event(), ['commit'], [], [], post, None, False, None)
    diag.observer_error(TimeoutError('PRIVATE'))
    diag.m1['phases']['m1_complete']['gate_closed'] = False
    diag.m1['durable']['rows_count'] = 1
    assert diag.final_snapshot['m1']['valid'] is True
    assert diag.final_snapshot['m1']['phases']['m1_complete']['gate_closed'] is True
    assert diag.final_snapshot['m1']['durable']['rows_count'] == 2
    # Missing target and observer failure still preserve bounded partial evidence.
    diag, target, post = fixture()
    diag.observer_error(asyncio.CancelledError('PRIVATE'))
    diag.snapshot({}, asyncio.Event(), [], [], [], None, None, False, TimeoutError('PRIVATE'))
    assert diag.m1['valid'] is False
    assert diag.final_snapshot['snapshot_error'] is None
    assert diag.final_snapshot['m1_remaining'] is None
    assert diag.final_snapshot['test_error_type'] == 'TimeoutError'
    assert diag.m1['observer_error_type'] == 'CancelledError'
    assert 'PRIVATE' not in repr(diag.__dict__)


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
    spec = importlib.util.spec_from_file_location('t112_native_fault_probe', probe_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    asyncio.run(check_wrappers(module))
    asyncio.run(check_m1(module))
    print('PASS exact source/AST restoration, 3 rejected mutations, wrapper identity/error/cancel, '
          'ContextVar reset, ASGI send/app, proof count, cap/partial snapshot, identical Timeout, '
          'complete/partial/late M1 summaries; no HTTP/DB')


if __name__ == '__main__':
    main()
