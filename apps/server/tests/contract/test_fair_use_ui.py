from pathlib import Path

from twobrain_rec_server.cabinet.templates import render_template

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
    assert "incident" not in template
    assert "evidence" not in template.lower()
