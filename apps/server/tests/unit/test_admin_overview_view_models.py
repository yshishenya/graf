from __future__ import annotations

from twobrain_rec_server.admin.view_models import admin_navigation, build_overview_view


def test_admin_navigation_is_russian_first_and_excludes_support_analyst_billing() -> None:
    nav = admin_navigation(active="overview")
    labels = [item.label for item in nav.items]

    assert labels == ["Обзор", "Пользователи", "Файлы", "ВКС", "Баланс", "Метрики", "Аудит"]
    assert "Поддержка" not in labels
    assert "Analyst" not in labels
    assert "Биллинг" not in labels


def test_overview_view_model_keeps_workspace_and_actor_scope_visible() -> None:
    view = build_overview_view(
        workspace_name="Test Workspace",
        actor_role="owner",
        overview={
            "user_counts": {"active": 1, "pending": 0, "inactive": 0, "blocked": 0, "revoked": 0},
            "usage_summary": {
                "recording_minutes": 0,
                "storage_bytes": 0,
                "processing_jobs": 0,
                "quota_risk": "not_configured",
                "freshness": "unknown",
            },
            "file_summary": {"server_known_meetings": 0, "deleting": 0, "problem": 0},
            "metrics_summary": {"families": [], "freshness": "unavailable"},
            "recent_audit": [],
        },
    )

    assert view.page_title == "Администрирование"
    assert view.workspace_name == "Test Workspace"
    assert view.actor_role == "owner"
    assert view.navigation.active == "overview"
