"""Real cabinet aliases and auth; the real operating period stays closed."""

import asyncio
import base64
import hmac
import json
import re
from contextlib import asynccontextmanager, suppress
from contextvars import Context
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic

import httpx
import pytest
from sqlalchemy import event, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from tests.contract.test_activation_milestone_ingress import isolated_admission  # noqa: F401
from tests.contract.test_result_view_http_budget import (
    MEETING_ID,
    SECRET,
    _headers,
    _postgres_response_gate,
    _run,
    _setup,
)
from tests.contract.test_result_view_projection import _seed_projection
from tests.contract.test_result_visibility import NOW, START
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.api import product_analytics_guard as guard_module
from twobrain_rec_server.cabinet.result_projection_session import (
    result_admission_session,
    result_inspection_session,
)
from twobrain_rec_server.cabinet.web import router
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MeetingSummarySlot,
    ProcessingResult,
    ProductActivationMilestone,
    TranscriptSegment,
)
from twobrain_rec_server.product_analytics import ingest

pytestmark = pytest.mark.usefixtures("isolated_admission")


async def _real_app(engine, *, ordinary=False):
    app, sessions, session_id = await _setup(engine)
    app.router.routes[:] = [route for route in app.router.routes
                            if not route.path.endswith("/result-viewed")]
    app.include_router(router)
    app.state.settings = app.state.settings.model_copy(update={"product_analytics_enabled": True})
    app.state.storage = object()  # No external storage or provider is contacted.
    async with sessions() as db:
        if ordinary:
            from tests.contract.test_result_projection_session import _seed_ordinary_projection
            review, pinned, current, old, previous_id = await _seed_ordinary_projection(db)
        else:
            review, pinned, current, old = await _seed_projection(db)
            pinned.template_key, pinned.template_version, pinned.revision_state = "graf-auto-v1", 1, "accepted"
            db.add(MeetingSummarySlot(
                workspace_id=WORKSPACE_ID, meeting_id=review.meeting.meeting_id,
                template_key="graf-auto-v1", current_outcome_set_id=pinned.id,
                current_binding_class="verified_complete", is_meeting_default=True,
                default_resolution_source="explicit_meeting", default_resolution_version="synthetic",
                default_resolved_at=NOW,
            ))
            await db.commit()
    return app, sessions, session_id, review, current, old


@pytest.fixture
def http_period(monkeypatch):
    observations = []

    @asynccontextmanager
    async def period(self, sessions, *, work_deadline, cleanup_deadline, inspection=False):
        factory = result_inspection_session if inspection else result_admission_session
        async with factory(sessions, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline) as owner:
            facts = {"inspection": inspection, "writes": 0, "commits": 0, "owner": owner,
                     "work_deadline": work_deadline, "cleanup_deadline": cleanup_deadline}
            observations.append(facts)

            def sql(connection, cursor, statement, parameters, context, many):
                if statement.lstrip().lower().startswith(("insert ", "update ", "delete ")):
                    facts["writes"] += 1

            def commit(connection):
                facts["commits"] += 1

            event.listen(owner._connection, "before_cursor_execute", sql)
            event.listen(owner._connection, "commit", commit)
            try:
                yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=lambda: None, owner=owner)
            finally:
                event.remove(owner._connection, "before_cursor_execute", sql)
                event.remove(owner._connection, "commit", commit)

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
    return observations


def _proofs(html):
    return re.findall(r'data-result-view-proof="([^"]+)"', html)


def _age_proof(proof, seconds):
    encoded, _ = proof.split(".")
    value = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    value["issued_at"] = int(datetime.now(UTC).timestamp()) - seconds
    encoded = base64.urlsafe_b64encode(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET.encode(), f"f273-result-view-v1:{encoded}".encode(), sha256).hexdigest()
    return f"{encoded}.{signature}"


@pytest.mark.parametrize("embedded", [False, True])
def test_real_alias_rejects_invalid_proof_without_opening_measurement(
    postgres_seeded_database_url, embedded,
):
    async def scenario(engine):
        app, sessions, session_id = await _setup(engine)
        # Replace only the old budget suite's synthetic endpoint with real routes.
        app.router.routes[:] = [route for route in app.router.routes
                                if not route.path.endswith("/result-viewed")]
        app.include_router(router)
        path = ("/desktop" if embedded else "") + f"/meetings/{MEETING_ID}/result-viewed"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            response = await client.post(path, json={"proof": "synthetic"}, headers=_headers(session_id))
        assert response.status_code == 200, response.text
        assert response.json() == {"status": "unavailable"}
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("embedded,hx", [(False, False), (False, True), (True, False), (True, True)])
def test_get_renewal_and_real_post_keep_distinct_read_and_pair_authority(
    postgres_seeded_database_url, http_period, embedded, hx,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = ("/desktop" if embedded else "") + f"/meetings/{review.meeting.meeting_id}"
        headers = _headers(session_id) | ({"HX-Request": "true"} if hx else {})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=headers)
            assert page.status_code == 200, page.text
            proofs = _proofs(page.text)
            assert len(proofs) == 2
            assert http_period[-1]["inspection"]
            assert (http_period[-1]["writes"], http_period[-1]["commits"]) == (0, 0)
            async with sessions() as db:
                assert not list(await db.scalars(select(ProductActivationMilestone)))
            renewed = await client.post(path + "/result-viewed", json={"proof": _age_proof(proofs[0], 601)}, headers=headers)
            assert renewed.json()["status"] == "renewed", renewed.text
            assert http_period[-1]["inspection"]
            assert (http_period[-1]["writes"], http_period[-1]["commits"]) == (0, 0)
            async with sessions() as db:
                assert not list(await db.scalars(select(ProductActivationMilestone)))
            accepted = await client.post(path + "/result-viewed", json={"proof": renewed.json()["proof"]}, headers=headers)
            assert accepted.json() == {"status": "accepted"}, accepted.text
            assert not http_period[-1]["inspection"]
            assert (http_period[-1]["writes"], http_period[-1]["commits"]) == (2, 1)
            duplicate = await client.post(path + "/result-viewed", json={"proof": proofs[-1]}, headers=headers)
            assert duplicate.json() == {"status": "accepted"}
        async with sessions() as db:
            rows = list(await db.scalars(select(ProductActivationMilestone)))
            assert {row.event_name for row in rows} == {"first_result_viewed", "first_value_session_completed"}
            assert len(rows) == 2 and all(row.account_id == USER_ID for row in rows)
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("change", ["version", "text"])
def test_get_never_signs_a_fresh_version_for_the_previous_render(
    postgres_seeded_database_url, http_period, monkeypatch, change,
):
    from twobrain_rec_server.cabinet.web_routes import result_views

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        original = result_views.optional_result_view_proofs

        async def change_before_inspection(*args, **kwargs):
            async with sessions() as writer:
                if change == "version":
                    await writer.execute(update(ProcessingResult).where(ProcessingResult.id == current.id)
                                         .values(result_version=current.result_version + 1))
                else:
                    await writer.execute(update(TranscriptSegment).where(
                        TranscriptSegment.processing_result_id == current.id,
                    ).values(text="Другая синтетическая версия"))
                    await writer.execute(update(DiarizationSegment).where(
                        DiarizationSegment.processing_result_id == current.id,
                    ).values(text="Другая синтетическая версия"))
                await writer.commit()
            return await original(*args, **kwargs)

        monkeypatch.setattr(result_views, "optional_result_view_proofs", change_before_inspection)
        path = f"/meetings/{review.meeting.meeting_id}?summary_format=unknown-template"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id))
        assert page.status_code == 200
        assert "Тело расшифровки" in page.text
        proofs = _proofs(page.text)
        assert len(proofs) == 1  # The unchanged pinned outcome keeps its own old result.
        encoded = proofs[0].split(".")[0]
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        assert payload["binding"]["source"]["result_id"] == str(old.id)
        assert payload["binding"]["source"]["result_version"] == old.result_version
        assert all(item["inspection"] and not item["writes"] and not item["commits"] for item in http_period)
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


def test_real_closed_period_keeps_the_page_and_refuses_both_post_branches(postgres_seeded_database_url):
    async def scenario(engine):
        from dataclasses import replace

        from tests.fakes.auth_contexts import DEVICE_ID, principal
        from twobrain_rec_server.cabinet.result_visibility import (
            issue_result_view_proof,
            load_fresh_result_view_bindings,
        )

        app, sessions, session_id, review, current, old = await _real_app(engine)
        identity = replace(principal(), session_id=session_id, auth_via_session=True,
                           session_workspace_id=WORKSPACE_ID, session_device_id=DEVICE_ID)
        async with sessions() as db:
            bindings = await load_fresh_result_view_bindings(
                db, principal=identity, workspace_id=WORKSPACE_ID,
                meeting_id=review.meeting.meeting_id, started_at=START,
            )
            proof = issue_result_view_proof(next(iter(bindings.values())), secret=SECRET, issued_at=datetime.now(UTC))
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id))
            assert page.status_code == 200 and not _proofs(page.text)
            for candidate in (proof, _age_proof(proof, 601)):
                response = await client.post(path + "/result-viewed", json={"proof": candidate}, headers=_headers(session_id))
                assert response.json() == {"status": "unavailable"}
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("excluded", ["internal", "automated", "smoke"])
def test_excluded_requests_keep_the_page_without_analytics_checkout(
    postgres_seeded_database_url, http_period, excluded,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        settings = {}
        headers = _headers(session_id)
        if excluded == "internal":
            settings["product_analytics_internal_hosts"] = ("127.0.0.1",)
        elif excluded == "automated":
            headers["User-Agent"] = "synthetic-crawler"
        else:
            settings.update(smoke_identity_class="internal_smoke", smoke_user_id=USER_ID)
        app.state.settings = app.state.settings.model_copy(update=settings)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=headers)
        assert page.status_code == 200 and "Тело расшифровки" in page.text
        assert not _proofs(page.text) and not http_period
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("transport,csrf,expected", [("native", True, 200), ("cookie", True, 200),
                                                   ("cookie", False, 403)])
def test_real_handler_keeps_cookie_csrf_and_native_auth(
    postgres_seeded_database_url, http_period, transport, csrf, expected,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id, transport))
            proof = _proofs(page.text)[0]
            before = len(http_period)
            response = await client.post(path + "/result-viewed", json={"proof": proof},
                                         headers=_headers(session_id, transport, csrf))
        assert response.status_code == expected
        if expected == 200:
            assert response.json() == {"status": "accepted"}
        else:
            assert len(http_period) == before
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


def test_complete_ordinary_hour_passes_get_renewal_and_admission_without_raising_caps(
    postgres_seeded_database_url, http_period,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine, ordinary=True)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id))
            assert page.status_code == 200
            proofs = _proofs(page.text)
            assert len(proofs) >= 601
            renewed = await client.post(path + "/result-viewed", json={"proof": _age_proof(proofs[0], 601)},
                                        headers=_headers(session_id))
            assert renewed.json()["status"] == "renewed"
            accepted = await client.post(path + "/result-viewed", json={"proof": renewed.json()["proof"]},
                                         headers=_headers(session_id))
            assert accepted.json() == {"status": "accepted"}
        assert len(http_period) == 3
        for observed in http_period:
            owner = observed["owner"]
            assert owner.sql_count <= 128
            print(f"ordinary_http_phase={'inspection' if observed['inspection'] else 'admission'} "
                  f"sql={owner.sql_count} rows={owner.budget.rows} "
                  f"bytes={owner.budget.raw_bytes} nodes={owner.budget.json_nodes}")
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("failure", ["second_insert", "after_commit"])
def test_real_http_does_not_acknowledge_partial_or_unknown_pair_outcomes(
    postgres_seeded_database_url, http_period, failure,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        writes = 0

        def before_sql(connection, cursor, statement, parameters, context, many):
            nonlocal writes
            if statement.lstrip().lower().startswith("insert into product_activation_milestones"):
                writes += 1
                if failure == "second_insert" and writes == 2:
                    raise OSError("synthetic second insert refusal")

        def after_commit(session):
            if failure == "after_commit" and hasattr(session, "_projection_owner"):
                raise OSError("synthetic unknown commit reply")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id))
            proof = _proofs(page.text)[0]
            event.listen(engine.sync_engine, "before_cursor_execute", before_sql)
            event.listen(Session, "after_commit", after_commit)
            try:
                response = await client.post(path + "/result-viewed", json={"proof": proof}, headers=_headers(session_id))
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", before_sql)
                event.remove(Session, "after_commit", after_commit)
            assert response.json() == {"status": "unavailable"}
            async with sessions() as db:
                saved = list(await db.scalars(select(ProductActivationMilestone)))
                assert len(saved) == (0 if failure == "second_insert" else 2)
            assert len(http_period) == 2  # No automatic replay by either layer.
            accepted = await client.post(path + "/result-viewed", json={"proof": proof}, headers=_headers(session_id))
            assert accepted.json() == {"status": "accepted"}
        async with sessions() as db:
            assert len(list(await db.scalars(select(ProductActivationMilestone)))) == 2
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


def test_get_checkout_timeout_preserves_product_and_foreign_pool_leases(
    postgres_seeded_database_url, http_period, monkeypatch,
):
    from twobrain_rec_server.cabinet.web_routes import result_views

    original = result_views.optional_result_view_proofs

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        # Product GET can use the third connection, its extra phase cannot.
        async with engine.connect() as first, engine.connect() as second:
            from sqlalchemy import text

            async def timed_phase(*args, **kwargs):
                started = monotonic()
                result = await original(*args, **kwargs)
                assert monotonic() - started < 2.1
                assert await first.scalar(text("SELECT 17")) == 17
                assert await second.scalar(text("SELECT 19")) == 19
                # Existing GET renewal needs its own slot while WebDbDependency
                # still holds the product connection. Free only our test lease.
                await second.close()
                return result

            monkeypatch.setattr(result_views, "optional_result_view_proofs", timed_phase)
            started = monotonic()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                page = await client.get(f"/meetings/{review.meeting.meeting_id}", headers=_headers(session_id))
            assert page.status_code == 200 and "Тело расшифровки" in page.text
            assert not _proofs(page.text)
            assert monotonic() - started < 2.75
            assert not http_period  # Owner.start never got a connection.
            assert await first.scalar(text("SELECT 17")) == 17
        assert engine.pool.checkedout() == 0
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("operation", ["dml", "flush", "commit", "raw_connection", "caught_gate"])
def test_inspection_cannot_gain_pair_authority_after_a_caught_refusal(
    postgres_seeded_database_url, http_period, monkeypatch, operation,
):
    from dataclasses import replace

    from sqlalchemy import insert

    from tests.fakes.auth_contexts import DEVICE_ID, principal
    from twobrain_rec_server.cabinet.result_projection_budget import ProjectionBudgetExceeded
    from twobrain_rec_server.db.models import UserIdentity

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        service = ingest.ProductAnalyticsIngestService(app.state.settings)
        identity = replace(principal(), session_id=session_id, auth_via_session=True,
                           session_workspace_id=WORKSPACE_ID, session_device_id=DEVICE_ID)
        observations = []

        async def inspect(db, started_at, owner):
            assert not hasattr(owner, "admit_event") and not hasattr(owner, "commit_pair")
            before = owner.sql_count
            try:
                if operation == "dml":
                    await db.execute(insert(ProductActivationMilestone).values())
                elif operation == "flush":
                    db.add(ProductActivationMilestone(account_id=USER_ID))
                    await db.flush()
                elif operation == "commit":
                    await db.commit()
                elif operation == "raw_connection":
                    await (await db.connection()).execute(select(UserIdentity.id))
                else:
                    original = ingest.activation_milestone_write_blockers
                    with monkeypatch.context() as patch:
                        patch.setattr(ingest, "activation_milestone_write_blockers", lambda settings: ["synthetic_closed"])
                        with suppress(PermissionError):
                            service._check_admission(ingest._AccountAdmissionContext(db, owner=owner))
                    assert ingest.activation_milestone_write_blockers is original
            except ProjectionBudgetExceeded:
                pass
            observations.append((owner.failed, owner.budget.failed, owner.sql_count == before))
            with pytest.raises(ProjectionBudgetExceeded):
                await db.scalar(select(UserIdentity.id))
            assert owner.sql_count == before
            return "cannot_escape"

        end = asyncio.get_running_loop().time() + 2
        result = await service._inspect_result_view(
            principal=identity, workspace_id=WORKSPACE_ID, sessionmaker=sessions,
            inspect_view=inspect, surface="cabinet_web", work_deadline=end - .5, cleanup_deadline=end,
        )
        assert result is None
        assert observations == [(True, True, True)]
        assert http_period[-1]["writes"] == http_period[-1]["commits"] == 0
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("kind", ["plain", "foreign", "readonly", "admission", "unstarted", "begun"])
def test_both_inspection_entrypoints_refuse_unowned_context_before_fresh_projection(
    postgres_seeded_database_url, http_period, monkeypatch, kind,
):
    from twobrain_rec_server.cabinet import result_visibility
    from twobrain_rec_server.cabinet.result_projection_session import (
        ResultInspectionSession,
        result_projection_session,
    )

    @asynccontextmanager
    async def invalid_period(self, sessions, *, work_deadline, cleanup_deadline, inspection=False):
        assert inspection
        if kind in {"readonly", "admission", "foreign"}:
            factory = {"readonly": result_projection_session, "admission": result_admission_session,
                       "foreign": result_inspection_session}[kind]
            deadlines = ({"deadline": cleanup_deadline} if kind == "readonly" else
                         {"work_deadline": work_deadline, "cleanup_deadline": cleanup_deadline})
            async with factory(sessions, **deadlines) as owner:
                if kind == "foreign":
                    async with sessions() as foreign:
                        yield ingest._AccountAdmissionContext(foreign, started_at=START, recheck=lambda: None, owner=owner)
                else:
                    yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=lambda: None, owner=owner)
        else:
            async with sessions() as db:
                if kind == "begun":
                    await db.begin()
                owner = None if kind == "plain" else ResultInspectionSession(db, work_deadline)
                yield ingest._AccountAdmissionContext(db, started_at=START, recheck=lambda: None, owner=owner)

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        called = []
        original = result_visibility.load_fresh_result_view_bindings

        async def traced(*args, **kwargs):
            called.append(True)
            return await original(*args, **kwargs)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            proof = _proofs((await client.get(path, headers=_headers(session_id))).text)[0]
            monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", invalid_period)
            monkeypatch.setattr(result_visibility, "load_fresh_result_view_bindings", traced)
            page = await client.get(path, headers=_headers(session_id))
            assert page.status_code == 200 and "Тело расшифровки" in page.text and not _proofs(page.text)
            response = await client.post(path + "/result-viewed", json={"proof": _age_proof(proof, 601)},
                                         headers=_headers(session_id))
            assert response.json() == {"status": "unavailable"}
        assert not called
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


def test_valid_to_expired_race_never_starts_a_renewal_session(
    postgres_seeded_database_url, http_period, monkeypatch,
):
    from datetime import timedelta

    from twobrain_rec_server.cabinet.web_routes import result_views

    class AfterReadClock:
        shifted = False
        issued_at = None
        observed_ages = []

        @classmethod
        def now(cls, timezone):
            age = 604 if cls.shifted else 599
            cls.observed_ages.append(age)
            return cls.issued_at.astimezone(timezone) + timedelta(seconds=age)

    original = result_views.load_fresh_result_view_bindings

    async def age_during_read(*args, **kwargs):
        result = await original(*args, **kwargs)
        AfterReadClock.shifted = True
        return result

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            proof = _proofs((await client.get(path, headers=_headers(session_id))).text)[0]
            aged = _age_proof(proof, 599)
            encoded = aged.split(".")[0]
            issued_at = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))["issued_at"]
            AfterReadClock.issued_at = datetime.fromtimestamp(issued_at, UTC)
            monkeypatch.setattr(result_views, "datetime", AfterReadClock)
            monkeypatch.setattr(result_views, "load_fresh_result_view_bindings", age_during_read)
            response = await client.post(path + "/result-viewed", json={"proof": aged},
                                         headers=_headers(session_id))
        assert response.json() == {"status": "unavailable"}
        assert AfterReadClock.observed_ages[0] == 599 and 604 in AfterReadClock.observed_ages
        print({"ttl_race_route_ages": AfterReadClock.observed_ages, "fresh_read_completed": AfterReadClock.shifted})
        assert len(http_period) == 2 and not http_period[-1]["inspection"]
        assert http_period[-1]["writes"] == http_period[-1]["commits"] == 0
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("embedded", [False, True])
def test_query_selection_matches_the_existing_detail_get_in_both_aliases(
    postgres_seeded_database_url, http_period, embedded,
):
    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = ("/desktop" if embedded else "") + f"/meetings/{review.meeting.meeting_id}"
        valid = str(current.id)
        queries = [
            (f"source_result_id=bad&source_result_id={valid}", 200),
            (f"source_result_id={valid}&source_result_id=bad", 200 if embedded else 422),
            ("source_result_id=", 200 if embedded else 422),
            ("source_result_id=bad", 200 if embedded else 422),
            ("summary_format=bad&summary_format=graf-auto-v1", 200),
            ("summary_format=graf-auto-v1&summary_format=", 200),
        ]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            for query, expected in queries:
                page = await client.get(path + "?" + query, headers=_headers(session_id))
                assert page.status_code == expected, (query, page.text)
                before = len(http_period)
                if expected == 200:
                    proofs = _proofs(page.text)
                    assert proofs
                    proof = _age_proof(proofs[0], 601)
                else:
                    proof = "synthetic-invalid"
                response = await client.post(path + "/result-viewed?" + query,
                                             json={"proof": proof}, headers=_headers(session_id))
                assert response.status_code == expected, (query, response.text)
                if expected == 200:
                    assert response.json()["status"] == "renewed"
                    assert len(http_period) == before + 1 and http_period[-1]["inspection"]
                else:
                    assert len(http_period) == before
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("change", ["delete", "source", "result", "revoked_session", "closed_account"])
def test_real_mutation_after_render_cannot_use_the_previous_proof(
    postgres_seeded_database_url, http_period, change,
):
    from twobrain_rec_server.db.models import AuthSession, MediaRevision, Meeting, UserIdentity

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            candidates = _proofs((await client.get(path, headers=_headers(session_id))).text)
            proof = next(value for value in candidates if json.loads(base64.urlsafe_b64decode(
                value.split(".")[0] + "===",
            ))["binding"]["source"]["result_id"] == str(current.id))
            async with sessions() as writer:
                if change == "delete":
                    await writer.execute(update(Meeting).where(Meeting.id == review.meeting.meeting_id)
                                         .values(deletion_state="deleting", deletion_requested_at=datetime.now(UTC)))
                elif change == "source":
                    await writer.execute(update(MediaRevision).where(MediaRevision.id == review.provenance.media_revision_id)
                                         .values(track_sha256_by_role={"media": "f" * 64}))
                elif change == "result":
                    await writer.execute(update(ProcessingResult).where(ProcessingResult.id == current.id)
                                         .values(result_version=4))
                elif change == "revoked_session":
                    await writer.execute(update(AuthSession).where(AuthSession.id == session_id).values(status="revoked"))
                else:
                    await writer.execute(update(UserIdentity).where(UserIdentity.id == USER_ID).values(status="closed"))
                await writer.commit()
            for candidate in (proof, _age_proof(proof, 601)):
                response = await client.post(path + "/result-viewed", json={"proof": candidate}, headers=_headers(session_id))
                if response.status_code == 200:
                    assert response.json() == {"status": "unavailable"}
                else:
                    assert change in {"revoked_session", "closed_account"} and response.status_code in {401, 403}
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("phase", ["first_insert", "second_insert", "commit"])
def test_real_handler_rechecks_current_gate_at_each_pair_write_and_commit(
    postgres_seeded_database_url, http_period, monkeypatch, phase,
):
    from twobrain_rec_server.cabinet.result_projection_session import ResultAdmissionSession
    from twobrain_rec_server.product_analytics import milestones

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        original = milestones.admit_account_milestone
        commit = ResultAdmissionSession.commit_pair
        closed = False
        attempts = []

        async def close_before_write(db, value, **kwargs):
            execute = kwargs["_execute_insert"]

            async def at_statement(statement):
                nonlocal closed
                attempts.append(value.event_name)
                if phase == "first_insert" or phase == "second_insert" and len(attempts) == 2:
                    closed = True
                return await execute(statement)

            kwargs["_execute_insert"] = at_statement
            return await original(db, value, **kwargs)

        async def close_before_commit(owner, recheck):
            nonlocal closed
            if phase == "commit":
                closed = True
            return await commit(owner, recheck)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            proof = _proofs((await client.get(path, headers=_headers(session_id))).text)[0]
            monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda settings: ("withdrawn",) if closed else ())
            monkeypatch.setattr(milestones, "admit_account_milestone", close_before_write)
            monkeypatch.setattr(ResultAdmissionSession, "commit_pair", close_before_commit)
            response = await client.post(path + "/result-viewed", json={"proof": proof}, headers=_headers(session_id))
        assert response.json() == {"status": "unavailable"}
        assert closed
        assert http_period[-1]["writes"] == {"first_insert": 0, "second_insert": 1, "commit": 2}[phase]
        assert http_period[-1]["commits"] == 0
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("failure", ["secret", "period", "database", "timeout"])
def test_optional_phase_failure_keeps_the_product_page_and_cleans_tasks(
    postgres_seeded_database_url, http_period, monkeypatch, failure,
):
    from twobrain_rec_server.cabinet import result_visibility

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        finished = []
        if failure == "secret":
            app.state.web_csrf_secret = None
        elif failure == "period":
            monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda settings: ("unreadable",))
        else:
            async def fail(*args, **kwargs):
                try:
                    if failure == "timeout":
                        await asyncio.sleep(10)
                    raise OSError("synthetic unavailable projection")
                finally:
                    finished.append(True)

            monkeypatch.setattr(result_visibility, "load_fresh_result_view_bindings", fail)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            started = monotonic()
            page = await client.get(f"/meetings/{review.meeting.meeting_id}", headers=_headers(session_id))
        if failure == "secret":
            # The unchanged product CSRF renderer also requires this same secret.
            assert page.status_code == 503 and page.json()["code"] == "csrf_secret_unavailable"
            app.state.settings = app.state.settings.model_copy(update={"product_analytics_enabled": False})
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                baseline = await client.get(f"/meetings/{review.meeting.meeting_id}", headers=_headers(session_id))
            assert baseline.status_code == page.status_code and baseline.json() == page.json()
        else:
            assert page.status_code == 200 and "Тело расшифровки" in page.text
        assert not _proofs(page.text) and monotonic() - started < 2.75
        if failure in {"database", "timeout"}:
            assert finished == [True]
        assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        assert engine.pool.checkedout() == 0
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("phase", ["fresh_digest", "rendered_digest", "valid_verifier"])
def test_sync_budget_exhaustion_stops_before_processing_the_next_http_candidate(
    postgres_seeded_database_url, http_period, monkeypatch, phase,
):
    import time

    from twobrain_rec_server.cabinet import result_visibility
    from twobrain_rec_server.cabinet.web_routes import result_views

    calls = []
    matching = False
    digest = result_visibility.result_view_block_digest
    comparator = result_visibility.matching_render_bindings
    verifier = result_views.verify_result_view_proof

    def slow_digest(*args, **kwargs):
        if phase == "fresh_digest" or phase == "rendered_digest" and matching:
            calls.append(True)
            if len(calls) == 1:
                time.sleep(max(0, http_period[-1]["owner"].deadline - monotonic()) + .03)
        return digest(*args, **kwargs)

    def matching_phase(*args, **kwargs):
        nonlocal matching
        matching = True
        try:
            return comparator(*args, **kwargs)
        finally:
            matching = False

    def slow_verify(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            time.sleep(max(0, http_period[-1]["owner"].deadline - monotonic()) + .03)
        return verifier(*args, **kwargs)

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            if phase == "valid_verifier":
                proof = _proofs((await client.get(path, headers=_headers(session_id))).text)[-1]
                monkeypatch.setattr(result_views, "verify_result_view_proof", slow_verify)
                response = await client.post(path + "/result-viewed", json={"proof": proof}, headers=_headers(session_id))
                assert response.json() == {"status": "unavailable"}
            else:
                monkeypatch.setattr(result_visibility, "result_view_block_digest", slow_digest)
                monkeypatch.setattr(result_visibility, "matching_render_bindings", matching_phase)
                page = await client.get(path, headers=_headers(session_id))
                assert page.status_code == 200 and "Тело расшифровки" in page.text and not _proofs(page.text)
        assert calls == [True]
        assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        assert engine.pool.checkedout() == 0
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]

    _run(postgres_seeded_database_url, scenario, pool_size=3)


def test_rendered_large_text_is_refused_before_extra_digest_even_if_fresh_db_text_is_small(
    postgres_seeded_database_url, http_period, monkeypatch,
):
    from twobrain_rec_server.cabinet import result_visibility
    from twobrain_rec_server.cabinet.web_routes import result_views

    oversized_digests = []
    original = result_views.optional_result_view_proofs
    digest = result_visibility.result_view_block_digest

    def observed_digest(*args, **kwargs):
        if any(len(value) > 256 * 1024 for value in kwargs["texts"]):
            oversized_digests.append(True)
        return digest(*args, **kwargs)

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        value = "x" * (256 * 1024 + 1)
        async with sessions() as writer:
            for model in (TranscriptSegment, DiarizationSegment):
                await writer.execute(update(model).where(model.processing_result_id == current.id).values(text=value))
            await writer.commit()

        async def shorten_before_inspection(*args, **kwargs):
            async with sessions() as writer:
                for model in (TranscriptSegment, DiarizationSegment):
                    await writer.execute(update(model).where(model.processing_result_id == current.id).values(text="Short synthetic text"))
                await writer.commit()
            return await original(*args, **kwargs)

        monkeypatch.setattr(result_views, "optional_result_view_proofs", shorten_before_inspection)
        monkeypatch.setattr(result_visibility, "result_view_block_digest", observed_digest)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(f"/meetings/{review.meeting.meeting_id}", headers=_headers(session_id))
        assert page.status_code == 200 and value in page.text
        assert not oversized_digests
        assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("envelope", ["field_exact", "field_above", "hour_near_total", "hour_above_total"])
def test_http_inspection_renewal_and_pair_keep_original_size_limits(
    postgres_seeded_database_url, http_period, monkeypatch, envelope,
):
    import sys

    from twobrain_rec_server.cabinet.result_projection_session import ResultProjectionSession

    first_refusals = {}
    refuse = ResultProjectionSession._refuse

    def observed_refuse(owner):
        first_refusals.setdefault(id(owner), dict(
            origin=sys._getframe(1).f_code.co_name,
            expired=asyncio.get_running_loop().time() >= owner.deadline,
            failed=owner.failed, budget_failed=owner.budget.failed, numeric=owner._numeric,
            same_task=asyncio.current_task() is owner._task,
            pending=bool(owner.db.new or owner.db.dirty or owner.db.deleted),
        ))
        return refuse(owner)

    monkeypatch.setattr(ResultProjectionSession, "_refuse", observed_refuse)

    async def scenario(engine):
        ordinary = envelope.startswith("hour")
        allowed = envelope in {"field_exact", "hour_near_total"}
        app, sessions, session_id, review, current, old = await _real_app(engine, ordinary=ordinary)
        length = {"field_exact": 256 * 1024, "field_above": 256 * 1024 + 1,
                  "hour_near_total": 6700, "hour_above_total": 7000}[envelope]
        async with sessions() as writer:
            for model in (TranscriptSegment, DiarizationSegment):
                await writer.execute(update(model).where(model.processing_result_id == current.id)
                                     .values(text="x" * length))
            await writer.commit()
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            page = await client.get(path, headers=_headers(session_id))
            assert page.status_code == 200
            proofs = _proofs(page.text)
            for item in http_period:
                owner = item["owner"]
                print(f"envelope_diagnostic={envelope} sql={owner.sql_count} rows={owner.budget.rows} "
                      f"bytes={owner.budget.raw_bytes} nodes={owner.budget.json_nodes} "
                      f"over_work={asyncio.get_running_loop().time() >= owner.deadline}")
            if envelope == "hour_near_total" and not proofs:
                # Size fits; the unchanged time budget may still refuse this large input.
                owner = http_period[-1]["owner"]
                assert 7_900_000 < owner.budget.raw_bytes <= 8 * 1024 * 1024
                assert owner.budget.failed and owner.sql_count <= 128
                refusal = first_refusals[id(owner)]
                assert refusal["origin"] == "checkpoint" and refusal["expired"]
                assert not refusal["failed"] and (not refusal["budget_failed"] or refusal["numeric"])
                assert refusal["same_task"] and not refusal["pending"]
                allowed = False
            if allowed:
                assert len(proofs) >= (601 if ordinary else 2)
                renewed = await client.post(path + "/result-viewed", json={"proof": _age_proof(proofs[0], 601)},
                                            headers=_headers(session_id))
                assert renewed.json()["status"] == "renewed"
                accepted = await client.post(path + "/result-viewed", json={"proof": renewed.json()["proof"]},
                                             headers=_headers(session_id))
                assert accepted.json() == {"status": "accepted"}
                assert len(http_period) == 3
                assert all(item["owner"].sql_count <= 128 for item in http_period)
                if ordinary:
                    assert all(7_900_000 < item["owner"].budget.raw_bytes <= 8 * 1024 * 1024 for item in http_period)
            else:
                assert not proofs
                assert http_period[-1]["owner"].budget.failed
                assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        async with sessions() as db:
            assert len(list(await db.scalars(select(ProductActivationMilestone)))) == (2 if allowed else 0)
        assert engine.pool.checkedout() == 0
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
        print(f"http_envelope={envelope} phases={len(http_period)} "
              f"max_bytes={max(item['owner'].budget.raw_bytes for item in http_period)}")

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("role", ["admin", "member", "shared"])
def test_authorized_nonowner_read_never_issues_or_admits_an_owner_proof(
    postgres_seeded_database_url, http_period, role,
):
    from uuid import uuid4

    from tests.fakes.auth_contexts import ORG_ID
    from twobrain_rec_server.db.models import (
        Meeting,
        MeetingShareGrant,
        UserIdentity,
        WorkspaceMembership,
    )

    async def scenario(engine):
        app, sessions, session_id, review, current, old = await _real_app(engine)
        path = f"/meetings/{review.meeting.meeting_id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            proof = _proofs((await client.get(path, headers=_headers(session_id))).text)[0]
            other = uuid4()
            async with sessions() as writer:
                writer.add(UserIdentity(id=other, organization_id=ORG_ID, external_subject="synthetic-other-result-owner"))
                await writer.flush()
                await writer.execute(update(Meeting).where(Meeting.id == review.meeting.meeting_id)
                                     .values(created_by_user_id=other, visibility="owner_only" if role == "shared" else "team"))
                await writer.execute(update(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID, WorkspaceMembership.user_id == USER_ID,
                ).values(role="member" if role == "shared" else role))
                if role == "shared":
                    writer.add(MeetingShareGrant(
                        workspace_id=WORKSPACE_ID, meeting_id=review.meeting.meeting_id,
                        grant_type="user", grantee_user_id=USER_ID, audience_type="user", audience_id=USER_ID,
                        content_scope="full_meeting", created_by_user_id=other, status="active",
                    ))
                await writer.commit()
            before = len(http_period)
            page = await client.get(path, headers=_headers(session_id))
            assert page.status_code == 200 and "Тело расшифровки" in page.text
            assert not _proofs(page.text) and len(http_period) == before
            for candidate in (proof, _age_proof(proof, 601)):
                response = await client.post(path + "/result-viewed", json={"proof": candidate}, headers=_headers(session_id))
                assert response.json() == {"status": "unavailable"}
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert all(item["writes"] == item["commits"] == 0 for item in http_period)
        assert engine.pool.checkedout() == 0

    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("fault", [False, True])
def test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation(
    postgres_seeded_database_url, http_period, monkeypatch, fault,
):
    provider_calls = []

    def forbidden(*args, **kwargs):
        provider_calls.append(True)
        raise AssertionError("commit acknowledgement test must never enter provider transport")

    monkeypatch.setattr(
        "twobrain_rec_server.product_analytics.posthog_client.PostHogClientWrapper.capture_event", forbidden,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.product_analytics.router.ParallelMeasurementRouter.dispatch", forbidden,
    )

    async def scenario(engine):
        streams, generations, checkouts, markers = [], [], [], []
        target, entered = {}, asyncio.Event()
        foreign = borrower = second = post = observer = watchdog = None
        warm = []
        armed, watchdog_fired = True, False
        keys = (guard_module._RESULT_VIEW_CONNECTION_OWNER, guard_module._RESULT_VIEW_TRANSACTION_OWNER,
                guard_module._RESULT_VIEW_INITIALIZATION_OWNER)
        async with _postgres_response_gate(postgres_seeded_database_url, streams=streams) as (url, _, relay_tasks):
            request_engine = create_async_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True)
            direct_sessions = async_sessionmaker(engine, expire_on_commit=False)

            def connected(dbapi, entry):
                generations.append({"dbapi": dbapi, "entry": entry, "driver": entry.driver_connection})

            def checkout(dbapi, entry, proxy):
                checkouts.append((entry, dbapi, entry.driver_connection,
                                  guard_module._RESULT_VIEW_TASK_OWNER.get(), tuple(k for k in keys if k in entry.info)))

            def commit(connection):
                if not armed:
                    return
                facts = next((item for item in reversed(http_period)
                              if not item["inspection"] and item["owner"]._connection is connection), None)
                if facts is None:
                    return
                owner = facts["owner"]
                try:
                    session = owner.db.sync_session
                    root = session.get_transaction()
                    proxy = connection.connection
                    lease = connection.info[guard_module._RESULT_VIEW_CONNECTION_OWNER]
                    guard = guard_module._RESULT_VIEW_TASK_OWNER.get()
                    association = connection.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER]
                    task = asyncio.current_task()
                    target.update(facts=facts, owner=owner, guard=guard, task=task, session=session,
                                  root=root, lease=lease, connection=connection,
                                  commit_at=asyncio.get_running_loop().time(),
                                  checks=(proxy.dbapi_connection is target["dbapi"],
                                          proxy.driver_connection is target["driver"],
                                          lease[0] is guard, lease[1] is target["dbapi"],
                                          lease[2] is target["driver"], lease[3] is task,
                                          lease[4] is target["entry"], guard.get(target["entry"]) is lease,
                                          association[0] is guard.transactions[root], association[1] is lease,
                                          association[0][2] is task, root.session is session,
                                          session.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] is association[0],
                                          target["entry"].in_use, not target["driver"].is_closed(),
                                          task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is guard,
                                          facts["writes"] == 2, not owner.failed))
                    if fault:
                        target["stream"]["response_gate"].clear()
                except Exception as error:
                    target["snapshot_error"] = type(error).__name__
                markers.append("commit")
                entered.set()

            def after_commit(session):
                if session is target.get("session"):
                    markers.append("after_commit")

            def reset(dbapi, entry, state):
                if entered.is_set() and entry is target.get("entry") and "checkin" not in markers:
                    markers.append(("reset", state.asyncio_safe, state.terminate_only, state.transaction_was_reset))

            def checkin(dbapi, entry):
                if entered.is_set() and entry is target.get("entry") and "checkin" not in markers:
                    markers.append("checkin")
                    target["returned_dbapi"] = dbapi

            def invalidate(dbapi, entry, error):
                if entered.is_set() and entry is target.get("entry"):
                    markers.append("invalidate")

            listeners = [("connect", connected), ("checkout", checkout), ("commit", commit),
                         ("reset", reset), ("checkin", checkin), ("invalidate", invalidate)]
            for name, callback in listeners:
                event.listen(request_engine.sync_engine, name, callback)
            event.listen(Session, "after_commit", after_commit)

            async def pair_snapshot(db):
                return [dict(row) for row in (await db.execute(
                    select(ProductActivationMilestone.__table__).where(
                        ProductActivationMilestone.account_id == USER_ID,
                    ).order_by(ProductActivationMilestone.event_name)
                )).mappings()]

            async def foreign_healthy():
                proxy = foreign.sync_connection.connection
                assert proxy.driver_connection is foreign_generation["driver"]
                assert proxy.dbapi_connection is foreign_generation["dbapi"]
                assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_generation["pid"]
                assert await foreign.scalar(text("SELECT 1")) == 1
                await foreign.commit()

            async def observe_committed_pair():
                await entered.wait()
                assert "snapshot_error" not in target and all(target["checks"])
                assert markers.count("commit") == 1
                if not fault:
                    return
                stream = target["stream"]
                async with asyncio.timeout_at(min(target["facts"]["work_deadline"] - .1,
                                                 asyncio.get_running_loop().time() + .9)):
                    await stream["response_held"].wait()
                    async with direct_sessions() as db:
                        while True:
                            rows = await pair_snapshot(db)
                            activity = (await db.execute(text(
                                "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                            ), {"pid": target["pid"]})).first()
                            locks = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                    {"pid": target["pid"]})
                            if len(rows) == 2 and activity is not None and activity.state == "idle" \
                                    and activity.xact_start is None and locks == 0:
                                break
                            await db.rollback()
                            await asyncio.sleep(.01)
                    assert not post.done() and not target["task"].cancelling()
                    assert "after_commit" not in markers and not stream["response_gate"].is_set()
                    await foreign_healthy()
                    target["m1_pair"] = rows
                    target["m1_at"] = asyncio.get_running_loop().time()

            def release_for_failed_test():
                nonlocal watchdog_fired
                watchdog_fired = True
                target["stream"]["response_gate"].set()

            try:
                # Two sequential native connects make stream/generation pairing unambiguous.
                for _ in range(2):
                    count = len(streams)
                    db = await request_engine.connect()
                    warm.append(db)
                    assert len(streams) == count + 1 and len(generations) == count + 1
                    generation = generations[-1]
                    assert db.sync_connection.connection.driver_connection is generation["driver"]
                    generation.update(stream=streams[count], pid=await db.scalar(text("SELECT pg_backend_pid()")))
                    await db.commit()
                for db in warm:
                    await db.close()
                app, sessions, session_id, review, current, old = await _real_app(request_engine)
                path = f"/meetings/{review.meeting.meeting_id}"
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    page = await client.get(path, headers=_headers(session_id))
                    assert page.status_code == 200 and len(_proofs(page.text)) == 2
                    proof = _proofs(page.text)[0]
                    assert request_engine.pool.checkedout() == 0
                    async with direct_sessions() as db:
                        assert await pair_snapshot(db) == []
                    foreign = await request_engine.connect()
                    foreign_driver = foreign.sync_connection.connection.driver_connection
                    foreign_generation = next(item for item in generations if item["driver"] is foreign_driver)
                    await foreign_healthy()
                    second = await request_engine.connect()
                    second_driver = second.sync_connection.connection.driver_connection
                    target.update(next(item for item in generations if item["driver"] is second_driver))
                    assert target["entry"] is not foreign_generation["entry"]
                    assert await second.scalar(text("SELECT pg_backend_pid()")) == target["pid"]
                    await second.commit()
                    await second.close()
                    assert not any(k in foreign_generation["entry"].info for k in keys)
                    before_operations = len(http_period)
                    began = asyncio.get_running_loop().time()
                    watchdog = asyncio.get_running_loop().call_later(3, release_for_failed_test)
                    observer = asyncio.create_task(observe_committed_pair(), context=Context())
                    post = asyncio.create_task(client.post(path + "/result-viewed", json={"proof": proof},
                                                          headers=_headers(session_id)))
                    response, _ = await asyncio.gather(post, observer)
                    armed = False
                    hard = target["facts"]["cleanup_deadline"]
                    async with asyncio.timeout_at(hard):
                        assert response.status_code == 200
                        assert response.json() == {"status": "unavailable" if fault else "accepted"}
                        assert response.headers["cache-control"] == "private, no-store"
                        assert len(http_period) == before_operations + 1
                        assert target["facts"]["writes"] == 2 and target["facts"]["commits"] == 1
                        assert markers.count("commit") == 1 and not watchdog_fired
                        assert provider_calls == []
                        owner, guard = target["owner"], target["guard"]
                        assert not owner.db.in_transaction() and owner._listeners == []
                        assert not guard and not guard.transactions and not guard.unbound_roots
                        assert not any(task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is guard
                                       for task in asyncio.all_tasks())
                        assert not any(k in target["entry"].info for k in keys)
                        assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in target["session"].info
                        assert request_engine.pool.checkedout() == 1
                        if fault:
                            assert markers.count("invalidate") == markers.count("checkin") == 1
                            assert markers.index("invalidate") < markers.index("checkin")
                            assert target["returned_dbapi"] is None
                            assert target["m1_at"] < target["facts"]["work_deadline"]
                            assert not target["stream"]["response_gate"].is_set()
                            assert target["driver"].is_closed()
                            await target["stream"]["done"].wait()
                            stream = target["stream"]
                            assert stream["root"].done()
                            assert all(t.done() for t in stream["pumps"] + stream["wait_closed"])
                            assert all(w.is_closing() for w in stream["writers"])
                        else:
                            assert not target["driver"].is_closed() and not target["driver"].is_in_transaction()
                            assert markers[:4] == ["commit", "after_commit", ("reset", True, False, False), "checkin"]
                            assert target["returned_dbapi"] is target["dbapi"]
                        async with direct_sessions() as db:
                            saved = await pair_snapshot(db)
                            assert len(saved) == 2
                            if fault:
                                assert saved == target["m1_pair"]
                            activity = (await db.execute(text(
                                "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                            ), {"pid": target["pid"]})).first()
                            assert (activity is None if fault else
                                    activity.state == "idle" and activity.xact_start is None)
                            assert await db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                   {"pid": target["pid"]}) == 0
                        await foreign_healthy()
                        prior_checkouts = len(checkouts)
                        borrower = await request_engine.connect()
                        entry, dbapi, driver, context_owner, leftover = checkouts[prior_checkouts]
                        assert len(checkouts) == prior_checkouts + 1
                        assert entry is target["entry"] and context_owner is None and leftover == ()
                        assert (dbapi is not target["dbapi"]) if fault else (dbapi is target["dbapi"])
                        assert (driver is not target["driver"]) if fault else (driver is target["driver"])
                        borrower_pid = await borrower.scalar(text("SELECT pg_backend_pid()"))
                        assert (borrower_pid != target["pid"]) if fault else (borrower_pid == target["pid"])
                        assert await borrower.scalar(text("SELECT 1")) == 1
                        assert not guard and not guard.transactions and not guard.unbound_roots
                        assert not any(task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is guard
                                       for task in asyncio.all_tasks())
                        target["stream"]["response_gate"].set()
                        await foreign_healthy()
                        assert borrower.sync_connection.connection.driver_connection is driver
                        assert await borrower.scalar(text("SELECT pg_backend_pid()")) == borrower_pid
                        assert await borrower.scalar(text("SELECT 1")) == 1
                        await borrower.commit()
                        assert not driver.is_closed() and not driver.is_in_transaction()
                        print({"native_commit_ack_fault": fault, "m1": "m1_pair" in target,
                               "elapsed": round(asyncio.get_running_loop().time() - began, 3),
                               "old_generation_closed": target["driver"].is_closed(),
                               "same_pool_foreign": True, "safe_reuse": True, "watchdog": watchdog_fired})
                    watchdog.cancel()
                    watchdog = None
                    await borrower.close()
                    borrower = None
                    await foreign.close()
                    foreign = None
                    repeated = await client.post(path + "/result-viewed", json={"proof": proof},
                                                 headers=_headers(session_id))
                    assert repeated.json() == {"status": "accepted"}
                    async with direct_sessions() as db:
                        assert await pair_snapshot(db) == saved
                    assert len(http_period) == before_operations + 2
                    assert provider_calls == []
                    assert request_engine.pool.checkedout() == 0
            finally:
                armed = False
                if watchdog is not None:
                    watchdog.cancel()
                for stream in streams:
                    stream["response_gate"].set()
                for task in (post, observer):
                    if task is not None and not task.done():
                        task.cancel()
                await asyncio.gather(*(t for t in (post, observer) if t is not None), return_exceptions=True)
                event.remove(Session, "after_commit", after_commit)
                for name, callback in listeners:
                    event.remove(request_engine.sync_engine, name, callback)
                for db in (borrower, foreign, second, *warm):
                    if db is not None and not db.closed:
                        await db.close()
                await request_engine.dispose()

    _run(postgres_seeded_database_url, scenario)
