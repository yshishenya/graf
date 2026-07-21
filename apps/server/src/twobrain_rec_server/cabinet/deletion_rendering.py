from __future__ import annotations

from html import escape

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    DeletionVerificationReport,
    LocalPurgeTask,
)
from twobrain_rec_server.cabinet.rendering_shared import _base_path, _page_shell, _ui_text
from twobrain_rec_server.cabinet.templates import render_template, trusted_component_html


def render_deletion_report_page(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    content = _render_deletion_report_content(meeting_title, report, embedded=embedded)
    return _page_shell(
        "Отчет удаления",
        content,
        embedded=embedded,
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content_source="deletion_report.content",
    )


def render_deletion_report_fragment(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool = False,
) -> str:
    return render_template(
        "cabinet/fragments/deletion_report.html",
        content=trusted_component_html(
            _render_deletion_report_content(meeting_title, report, embedded=embedded),
            source="deletion_report.content",
        ),
    )


def render_deletion_feedback_fragment() -> str:
    return render_template("cabinet/fragments/deletion_feedback.html")


def _render_deletion_report_content(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool,
) -> str:
    return render_template(
        "cabinet/pages/deletion_report_content.html",
        base_path=_base_path(embedded),
        meeting_title=meeting_title,
        overall_state_label=_ui_text(report.overall_state.value),
        bounded_copy=report.bounded_copy,
        bounded_copy_text=_ui_text(report.bounded_copy),
        artifact_band=trusted_component_html(
            _render_report_band("Файлы под контролем GRAF", report.artifact_states),
            source="deletion_report.band",
        ),
        backup_band=trusted_component_html(
            _render_report_band("Резервные копии", [report.backup]),
            source="deletion_report.band",
        ),
        dependencies_band=trusted_component_html(
            _render_report_band("Внешние зависимости", report.dependencies),
            source="deletion_report.band",
        ),
        egress_limits_band=trusted_component_html(
            _render_report_band("Ограничения после выгрузки", report.post_egress_limits),
            source="deletion_report.band",
        ),
        local_purge=trusted_component_html(_render_local_purge_tasks(report.local_purge), source="deletion_report.local_purge"),
        activity=trusted_component_html(_render_lifecycle_activity(report.activity), source="deletion_report.activity"),
        analytics_limits=(
            "Product analytics uses pseudonymous metadata only. GRAF can remove GRAF-controlled bridge and gap records; "
            "provider-held aggregates, Yandex offline conversion reports, and exported dashboard snapshots may require "
            "separate provider/manual handling and must not be described as universal erasure."
        ),
    )


def _render_report_band(title: str, rows: list[ArtifactDeletionState]) -> str:
    rendered = "".join(_render_report_artifact_row(row) for row in rows)
    if not rendered:
        rendered = f'<div class="muted">{escape(_ui_text("No lifecycle rows yet."))}</div>'
    return f"""
      <div class="report-band">
        <h3>{escape(title)}</h3>
        <div class="state-list">{rendered}</div>
      </div>
    """


def _render_report_artifact_row(row: ArtifactDeletionState) -> str:
    reason = row.safe_reason or row.label
    return f"""
      <div class="state-row">
        <span><strong>{escape(_ui_text(row.label))}</strong><br><span class="muted">{escape(_ui_text(reason))}</span></span>
        <span class="chip {escape(row.state.value)}">{escape(_ui_text(row.state.value))}</span>
      </div>
    """


def _render_local_purge_tasks(tasks: list[LocalPurgeTask]) -> str:
    if not tasks:
        return f'<div class="muted">{escape(_ui_text("No local purge acknowledgement has been received yet."))}</div>'
    return '<div class="state-list">' + "".join(_render_local_purge_task(task) for task in tasks) + "</div>"


def _render_local_purge_task(task: LocalPurgeTask) -> str:
    return f"""
      <div class="state-row">
        <span><strong>{escape(_ui_text(task.task_type.value))}</strong><br><span class="muted">{escape(_ui_text(task.safe_reason or "metadata only"))}</span></span>
        <span class="chip {escape(task.state.value)}">{escape(_ui_text(task.state.value))}</span>
      </div>
    """


def _render_lifecycle_activity(activity: list) -> str:
    if not activity:
        return f'<div class="muted">{escape(_ui_text("No lifecycle activity yet."))}</div>'
    rows = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(_ui_text(item.event_type))}</strong><br><span class="muted">{escape(_ui_text(item.actor_label))} · {escape(_ui_text(item.safe_reason or "metadata only"))}</span></span>
          <span class="chip {escape(item.outcome)}">{escape(_ui_text(item.outcome))}</span>
        </div>
        """
        for item in activity
    )
    return f'<div class="state-list">{rows}</div>'
