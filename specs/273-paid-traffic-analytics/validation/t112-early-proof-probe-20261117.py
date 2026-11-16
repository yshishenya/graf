"""Single synthetic GET with rare boundary metadata; never auto-loaded."""
import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from tests.contract.test_result_view_http_integration import (
    _headers, _postgres_response_gate, _real_app, _run,
)
from tests.contract.test_result_view_http_integration import (  # noqa: F401
    http_period, isolated_admission,
)

pytestmark = pytest.mark.usefixtures("isolated_admission", "http_period")
STAGES = {"optional", "eligible", "issue", "inspect", "account", "bindings", "operation"}
ACTIVE = ContextVar("early_proof_probe", default=None)
PINS = {
    "tests/contract/test_result_view_http_integration.py": "1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0",
    "tests/contract/test_result_view_http_budget.py": "f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7",
    "src/twobrain_rec_server/cabinet/web_routes/result_views.py": "232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e",
    "src/twobrain_rec_server/product_analytics/ingest.py": "69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795",
    "src/twobrain_rec_server/cabinet/result_visibility.py": "ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04",
    "src/twobrain_rec_server/api/product_analytics_guard.py": "7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6",
}


class Observation:
    def __init__(self):
        self.start = asyncio.get_running_loop().time()
        self.work = self.hard = None
        self.records, self.summary = [], {}
        self.dropped = 0
        self.incomplete = False

    def emit(self, stage, event, **facts):
        assert stage in STAGES
        now = asyncio.get_running_loop().time()
        row = dict(stage=stage, event=event, t=round(now-self.start, 6),
                   work_remaining=None if self.work is None else round(self.work-now, 6),
                   hard_remaining=None if self.hard is None else round(self.hard-now, 6), **facts)
        terminal = self.summary.setdefault(stage, {"count": 0, "first_t": row["t"]})
        terminal["count"] += 1
        terminal.update(row)
        if "exception_type" in facts and "first_exception_type" not in terminal:
            terminal.update(first_exception_type=facts["exception_type"],
                            first_exception_module=facts["exception_module"])
        if len(self.records) < 32:
            self.records.append(row)
        else:
            self.dropped += 1
            self.incomplete = True

    def deadlines(self, kwargs):
        if "work_deadline" in kwargs:
            self.work = kwargs["work_deadline"]
            self.hard = kwargs.get("cleanup_deadline")


def shape(value):
    return {"result_kind": "dict", "result_count": len(value)} if isinstance(value, dict) else {
        "result_kind": "none" if value is None else "unexpected", "result_count": None,
    }


def error_type(error):
    return dict(exception_type=type(error).__name__, exception_module=type(error).__module__)


def boundary(original, stage):
    async def observed(*args, **kwargs):
        obs = ACTIVE.get()
        if obs is None:
            return await original(*args, **kwargs)
        obs.deadlines(kwargs)
        facts = {}
        if stage == "optional":
            access = kwargs["review"].access
            facts = dict(access_present=access is not None,
                         access_owner=access is not None and access.state == "owner",
                         access_view=access is not None and bool(access.can_view),
                         access_full=access is not None and bool(access.can_view_full_meeting))
        if stage == "inspect":
            principal = kwargs.get("principal")
            facts = dict(principal_present=principal is not None,
                         session_present=principal is not None and principal.auth_via_session
                         and principal.session_id is not None,
                         membership_match=principal is not None and kwargs["workspace_id"] in principal.workspace_ids,
                         workspace_match=principal is not None and principal.session_workspace_id == kwargs["workspace_id"],
                         sessionmaker_present=kwargs.get("sessionmaker") is not None,
                         surface_allowed=kwargs.get("surface") in {"cabinet_web", "cabinet_desktop"})
        obs.emit(stage, "enter", **facts)
        try:
            result = await original(*args, **kwargs)
        except BaseException as error:
            obs.emit(stage, "raise", **error_type(error))
            raise
        obs.emit(stage, "leave", **shape(result))
        if shape(result)["result_kind"] == "unexpected":
            obs.incomplete = True
        return result
    return observed


def eligibility(original):
    def observed(*args, **kwargs):
        obs = ACTIVE.get()
        if obs is None:
            return original(*args, **kwargs)
        obs.emit("eligible", "enter")
        try:
            result = original(*args, **kwargs)
        except BaseException as error:
            obs.emit("eligible", "raise", **error_type(error))
            raise
        obs.emit("eligible", "leave", allowed=result if type(result) is bool else None)
        obs.incomplete |= type(result) is not bool
        return result
    return observed


def transaction(original, inspection_owner):
    @asynccontextmanager
    async def observed(*args, **kwargs):
        obs = ACTIVE.get()
        if obs is None:
            async with original(*args, **kwargs) as context:
                yield context
            return
        obs.deadlines(kwargs)
        obs.emit("account", "enter_begin")
        yielded = False
        try:
            async with original(*args, **kwargs) as context:
                yielded = True
                obs.emit("account", "yielded", is_none=context is None,
                         inspection_owner=context is not None and type(context.owner) is inspection_owner)
                try:
                    yield context
                except BaseException as error:
                    obs.emit("account", "body_exception", **error_type(error))
                    raise
                finally:
                    obs.emit("account", "exit_begin")
        except BaseException as error:
            obs.emit("account", "exit_exception" if yielded else "enter_exception", **error_type(error))
            raise
        else:
            obs.emit("account", "exit_finished")
    return observed


def install(monkeypatch):
    from twobrain_rec_server.cabinet import result_visibility
    from twobrain_rec_server.cabinet.result_projection_session import ResultInspectionSession
    from twobrain_rec_server.cabinet.web_routes import result_views
    from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService as Service
    for target, name, stage in (
        (result_views, "optional_result_view_proofs", "optional"),
        (result_views, "_run_result_view_operation", "operation"),
        (Service, "issue_result_view_proofs", "issue"),
        (Service, "_inspect_result_view", "inspect"),
        (result_visibility, "load_fresh_result_view_bindings", "bindings"),
    ):
        monkeypatch.setattr(target, name, boundary(getattr(target, name), stage))
    monkeypatch.setattr(result_views, "_eligible", eligibility(result_views._eligible))
    monkeypatch.setattr(Service, "_account_transaction", transaction(Service._account_transaction, ResultInspectionSession))


def test_early_proof_single_get(postgres_seeded_database_url, monkeypatch):
    root = Path(__file__).resolve().parent
    for path, expected in PINS.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected
    install(monkeypatch)
    observations = []

    async def scenario(engine):
        streams, warm = [], []
        async with _postgres_response_gate(postgres_seeded_database_url, streams=streams) as (url, _, relay_tasks):
            from sqlalchemy.ext.asyncio import create_async_engine
            request_engine = create_async_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True)
            try:
                for _ in range(2):
                    db = await request_engine.connect()
                    warm.append(db)
                    from sqlalchemy import text
                    await db.scalar(text("SELECT pg_backend_pid()"))
                    await db.commit()
                for db in warm:
                    await db.close()
                app, sessions, session_id, review, current, old = await _real_app(request_engine)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    obs = Observation()
                    observations.append(obs)
                    token = ACTIVE.set(obs)
                    try:
                        response = await client.get(f"/meetings/{review.meeting.meeting_id}", headers=_headers(session_id))
                        obs.http_status = response.status_code
                    finally:
                        obs.http_elapsed = round(asyncio.get_running_loop().time() - obs.start, 6)
                        ACTIVE.reset(token)
            finally:
                for db in warm:
                    if not db.closed:
                        await db.close()
                await request_engine.dispose()

    try:
        _run(postgres_seeded_database_url, scenario)
    finally:
        for obs in observations:
            print(json.dumps(dict(early_proof_records=obs.records, terminal=obs.summary, dropped=obs.dropped,
                                  incomplete=obs.incomplete, http_status=getattr(obs, "http_status", None),
                                  http_elapsed=getattr(obs, "http_elapsed", None)), sort_keys=True))
