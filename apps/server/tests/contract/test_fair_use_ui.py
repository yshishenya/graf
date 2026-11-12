import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from starlette.requests import Request

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.web_routes.fair_use import _review_view, fair_use_appeal

ROOT = Path(__file__).parents[2] / "src/twobrain_rec_server"


def test_fair_use_routes_and_template_keep_user_safe_boundaries() -> None:
    route_source = (ROOT / "cabinet/web_routes/fair_use.py").read_text()
    template = render_template(
        "cabinet/pages/fair_use_content.html",
        embedded=False,
        settings_navigation=(),
        settings_active="account",
        back_href="/meetings",
        csrf_token="synthetic-csrf",
        reviews=[
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "capability": "обработка встреч",
                "reason_label": "автоматизированная массовая обработка",
                "state_label": "Ограничение на проверке",
                "review_by_label": "07.08.2026, 12:00",
                "review_overdue": False,
                "review_completed": False,
                "support_reference": "FU-000000000001",
                "can_appeal": True,
                "appealed": False,
            }
        ],
        unavailable=False,
        fair_use_result=None,
        appeal_base_path="/account/fair-use",
        support_email=None,
    )
    assert '@router.get("/account/fair-use"' in route_source
    assert '@router.post(' in route_source
    assert '"/account/fair-use/{review_id}/appeal"' in route_source
    assert 'name="csrf_token" value="synthetic-csrf"' in template
    assert "Обжаловать проверку" in template
    assert "обработка встреч" in template
    assert "Локальная запись и остановка" in template
    assert "Скопировать номер для поддержки" in template
    assert "incident" not in template
    assert "evidence" not in template.lower()


def test_fair_use_first_appeal_is_reported_before_repeat() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    review_id = uuid4()
    row = SimpleNamespace(
        id=review_id,
        workspace_id=workspace_id,
        subject_user_id=user_id,
        state="notice",
        appealed_at=None,
        appeal_ref=None,
    )

    class FakeDB:
        async def commit(self) -> None:
            return None

    def request(path: str) -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "https",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "server": ("test", 443),
                "client": ("test", 1),
            }
        )

    principal = AuthenticatedPrincipal(
        user_id=user_id,
        organization_id=uuid4(),
        workspace_ids=frozenset({workspace_id}),
        subject="test-user",
    )
    scope = TenantScope(
        organization_id=principal.organization_id,
        workspace_id=workspace_id,
        user_id=user_id,
        device_id=uuid4(),
    )
    db = FakeDB()
    helper = AsyncMock(side_effect=[(row, True), (row, False)])
    with patch("twobrain_rec_server.cabinet.web_routes.fair_use.appeal_persisted_review", helper):
        first = asyncio.run(
            fair_use_appeal(
                str(review_id), request("/account/fair-use/" + str(review_id) + "/appeal"), scope, principal, db
            )
        )
        second = asyncio.run(
            fair_use_appeal(
                str(review_id), request("/account/fair-use/" + str(review_id) + "/appeal"), scope, principal, db
            )
        )
    assert first.headers["location"].endswith("?result=appealed")
    assert second.headers["location"].endswith("?result=already_appealed")


def test_fair_use_route_uses_lineage_helper_for_source_subject_once() -> None:
    survivor_id = uuid4()
    source_id = uuid4()
    workspace_id = uuid4()
    review_id = uuid4()
    row = SimpleNamespace(
        id=review_id,
        workspace_id=workspace_id,
        subject_user_id=source_id,
        state="restricted",
        appealed_at=None,
        appeal_ref=None,
    )

    class FakeDB:
        async def scalar(self, _statement):
            return None

        async def commit(self) -> None:
            return None

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": f"/account/fair-use/{review_id}/appeal",
            "raw_path": f"/account/fair-use/{review_id}/appeal".encode(),
            "query_string": b"",
            "headers": [],
            "server": ("test", 443),
            "client": ("test", 1),
        }
    )
    principal = AuthenticatedPrincipal(
        user_id=survivor_id,
        organization_id=uuid4(),
        workspace_ids=frozenset({workspace_id}),
        subject="merged-survivor",
    )
    scope = TenantScope(
        organization_id=principal.organization_id,
        workspace_id=workspace_id,
        user_id=survivor_id,
        device_id=uuid4(),
    )

    async def appeal(*_args, subject_user_id, **_kwargs):
        assert subject_user_id == survivor_id
        changed = row.appealed_at is None
        if changed:
            row.appealed_at = datetime(2000, 1, 1, tzinfo=UTC)
        return row, changed

    helper = AsyncMock(side_effect=appeal)
    with patch(
        "twobrain_rec_server.cabinet.web_routes.fair_use.appeal_persisted_review",
        helper,
    ):
        first = asyncio.run(
            fair_use_appeal(str(review_id), request, scope, principal, FakeDB())
        )
        second = asyncio.run(
            fair_use_appeal(str(review_id), request, scope, principal, FakeDB())
        )

    assert first.headers["location"].endswith("?result=appealed")
    assert second.headers["location"].endswith("?result=already_appealed")
    assert helper.await_count == 2


@pytest.mark.parametrize("state,label", [
    ("notice", "Проверка принята"),
    ("restricted", "Ограничение на проверке"),
    ("appealed", "Апелляция принята"),
    ("cleared", "Проверка завершена"),
    ("confirmed", "Основание подтверждено"),
])
def test_fair_use_result_preserves_historical_deadline_without_promising_enforcement(state, label):
    now = datetime(2026, 11, 11, tzinfo=UTC)
    row = SimpleNamespace(id=uuid4(), capability="server_processing", reason_code="resale",
                          state=state, review_by=now - timedelta(days=3))
    view = _review_view(row, now=now, can_appeal=True)
    completed = state in {"cleared", "confirmed"}
    assert view["state_label"] == label
    assert view["review_completed"] is completed
    assert view["review_overdue"] is not completed
    html = render_template(
        "cabinet/pages/fair_use_content.html", reviews=[view], unavailable=False,
        fair_use_result=None, csrf_token="synthetic-csrf", appeal_base_path="/account/fair-use",
        support_mailto=None,
    )
    assert label in html and str(view["review_by_label"]) in html
    assert "не подтверждает применение или снятие ограничения" in html
    assert "Ограничение снято" not in html and "Ограничение подтверждено" not in html
    assert ("Первоначальный срок проверки" in html) is completed
    assert ("срок уже прошел, обращение требует внимания поддержки" in html) is not completed
    assert ("Обжаловать проверку" in html) is (state in {"notice", "restricted"})
    if state == "appealed":
        assert 'role="status"' in html
