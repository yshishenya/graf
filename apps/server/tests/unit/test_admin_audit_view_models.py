from __future__ import annotations

from twobrain_rec_server.admin.metrics import metric_families
from twobrain_rec_server.admin.view_models import build_audit_view, build_metrics_view


def test_metric_families_cover_required_admin_groups() -> None:
    families = metric_families()

    assert families == ["adoption", "usage", "funnel", "reliability", "governance"]


def test_metrics_and_audit_view_models_keep_admin_navigation() -> None:
    metrics = build_metrics_view(
        workspace_name="Workspace", actor_role="owner", metrics={"metrics": []}
    )
    audit = build_audit_view(workspace_name="Workspace", actor_role="owner", audit={"entries": []})

    assert metrics.navigation.active == "metrics"
    assert audit.navigation.active == "audit"
    assert metrics.page_title == "Метрики"
    assert audit.page_title == "Аудит"
