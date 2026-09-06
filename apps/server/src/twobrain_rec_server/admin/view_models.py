from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


@dataclass(frozen=True, slots=True)
class AdminNavigationItem:
    id: str
    label: str
    href: str


@dataclass(frozen=True, slots=True)
class AdminNavigationModel:
    active: str
    items: tuple[AdminNavigationItem, ...]


def admin_navigation(*, active: str) -> AdminNavigationModel:
    return AdminNavigationModel(
        active=active,
        items=(
            AdminNavigationItem("overview", "Обзор", "/admin"),
            AdminNavigationItem("users", "Пользователи", "/admin/users"),
            AdminNavigationItem("files", "Файлы", "/admin/files"),
            AdminNavigationItem("meeting-detection", "ВКС", "/admin/meeting-detection"),
            AdminNavigationItem("balance", "Использование и лимиты", "/admin/balance"),
            AdminNavigationItem("metrics", "Метрики", "/admin/metrics"),
            AdminNavigationItem("audit", "Аудит", "/admin/audit"),
        ),
    )


def _page_view(
    *,
    page_title: str,
    workspace_name: str,
    actor_role: str,
    active: str,
    **payload: Any,
) -> SimpleNamespace:
    return SimpleNamespace(
        page_title=page_title,
        workspace_name=workspace_name,
        actor_role=actor_role,
        navigation=admin_navigation(active=active),
        **payload,
    )


def build_overview_view(
    *,
    workspace_name: str,
    actor_role: str,
    overview: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="Администрирование",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="overview",
        overview=overview,
    )


def build_users_view(
    *,
    workspace_name: str,
    actor_role: str,
    users: dict[str, Any],
    filters: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return _page_view(
        page_title="Пользователи",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="users",
        users=users,
        filters=filters or users.get("filters", {}),
    )


def build_user_detail_view(
    *,
    workspace_name: str,
    actor_role: str,
    user: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="Пользователь",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="users",
        user=user,
    )


def build_files_view(
    *,
    workspace_name: str,
    actor_role: str,
    files: dict[str, Any],
    filters: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return _page_view(
        page_title="Файлы",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="files",
        files=files,
        filters=filters or files.get("filters", {}),
    )


def build_file_detail_view(
    *,
    workspace_name: str,
    actor_role: str,
    file: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="Файл встречи",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="files",
        file=file,
    )


def build_balance_view(
    *,
    workspace_name: str,
    actor_role: str,
    usage: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="Использование и лимиты",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="balance",
        usage=usage,
    )


def build_metrics_view(
    *,
    workspace_name: str,
    actor_role: str,
    metrics: dict[str, Any],
    filters: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return _page_view(
        page_title="Метрики",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="metrics",
        metrics=metrics,
        playback_normalization=metrics.get(
            "playback_normalization",
            {
                "run_states": {},
                "job_states": {},
                "reason_counts": {},
                "backlog_total": 0,
                "oldest_backlog_age_seconds": 0,
                "execution_duration_seconds": {"count": 0, "average": 0, "maximum": 0},
                "processing_gate_waiting_count": 0,
                "oldest_processing_gate_wait_seconds": 0,
            },
        ),
        filters=filters or {},
    )


def build_audit_view(
    *,
    workspace_name: str,
    actor_role: str,
    audit: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="Аудит",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="audit",
        audit=audit,
        filters=audit.get("filters", {}),
    )


def build_meeting_detection_view(
    *,
    workspace_name: str,
    actor_role: str,
    meeting_detection: dict[str, Any],
) -> SimpleNamespace:
    return _page_view(
        page_title="ВКС-детектор",
        workspace_name=workspace_name,
        actor_role=actor_role,
        active="meeting-detection",
        meeting_detection=meeting_detection,
    )
