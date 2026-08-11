import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from starlette.requests import Request

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.web_routes.fair_use import fair_use_appeal

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
                "capability": "server_processing",
                "reason_label": "автоматизированная массовая обработка",
                "state_label": "Ограничение на проверке",
                "review_by_label": "07.08.2026, 12:00",
                "review_overdue": False,
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
    assert "Обжаловать ограничение" in template
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
        async def scalar(self, _statement):
            return row

        async def flush(self) -> None:
            return None

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
