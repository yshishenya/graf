from __future__ import annotations

from html import escape

from twobrain_rec_server.api.schemas import ArtifactEgressState, MeetingReviewResponse
from twobrain_rec_server.cabinet.rendering_shared import _base_path, _ui_text
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def _render_access_chip(access) -> str:
    if access is None:
        return ""
    return f'<span class="chip {escape(access.state)}">{escape(_ui_text(access.label))}</span>'


def _render_access_summary(review: MeetingReviewResponse) -> str:
    access = review.access
    if access is None:
        return f'<div class="muted">{escape(_ui_text("Access state is unavailable."))}</div>'
    reason = f'<div class="muted">{escape(_ui_text(access.reason))}</div>' if access.reason else ""
    capabilities = [
        ("Поделиться", access.can_share),
        ("Скачать", access.can_download),
        ("Экспорт", access.can_export),
    ]
    capability_rows = "".join(
        f'<div class="state-row"><span>{escape(label)}</span><span class="chip {"available" if enabled else "disabled"}">{escape(_ui_text("On" if enabled else "Off"))}</span></div>'
        for label, enabled in capabilities
    )
    return f"""
      <div class="state-list">
        <div class="state-row"><strong>{escape(_ui_text(access.label))}</strong><span class="chip {escape(access.state)}">{escape(_ui_text(access.state))}</span></div>
        {reason}
        {capability_rows}
      </div>
    """


def _render_share_panel(review: MeetingReviewResponse) -> str:
    share = review.share
    if share is None:
        return f'<div class="muted">{escape(_ui_text("Sharing is unavailable for this meeting."))}</div>'
    grants = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(grant.display_name)}</strong><br><span class="muted">{escape(_ui_text(grant.role_label))}</span></span>
          <span class="chip {escape(grant.status)}">{escape(_ui_text(grant.status))}</span>
        </div>
        """
        for grant in share.active_grants
    )
    if not grants:
        grants = f'<div class="muted">{escape(_ui_text("No active user grants."))}</div>'
    return f"""
      <div class="state-list">
        <div class="state-row"><span>{escape(_ui_text("Team visibility"))}</span><span class="chip {escape(share.team_visibility)}">{escape(_ui_text(share.team_visibility))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Copy link"))}</span><span class="chip {escape(share.copy_link_state)}">{escape(_ui_text(share.copy_link_state))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Public links"))}</span><span class="chip {escape(share.public_link_state)}">{escape(_ui_text(share.public_link_state))}</span></div>
        {grants}
      </div>
    """


def _render_artifacts(review: MeetingReviewResponse) -> str:
    if not review.artifacts:
        return f'<div class="muted">{escape(_ui_text("No exportable artifacts yet."))}</div>'
    rows = "".join(_render_artifact_state(review, artifact) for artifact in review.artifacts)
    return f'<div class="state-list">{rows}</div>'


def _render_artifact_state(review: MeetingReviewResponse, artifact: ArtifactEgressState) -> str:
    label = escape(_ui_text(artifact.label))
    reason = f'<span class="muted">{escape(_ui_text(artifact.reason))}</span>' if artifact.reason else ""
    if artifact.state == "available" and artifact.artifact_class != "package":
        action = (
            f'<a class="mini-link" href="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/downloads/'
            f'{escape(artifact.artifact_class)}">{escape(_ui_text("Download"))}</a>'
        )
    elif artifact.state == "available":
        action = f'<span class="chip available">{escape(_ui_text("Export ready"))}</span>'
    else:
        action = f'<span class="chip {escape(artifact.state)}">{escape(_ui_text(artifact.state))}</span>'
    return f"""
      <div class="state-row">
        <span><strong>{label}</strong><br>{reason}</span>
        {action}
      </div>
    """


def _render_delete_confirmation(review: MeetingReviewResponse, *, embedded: bool) -> str:
    report_href = f"{_base_path(embedded)}/{review.meeting.meeting_id}/deletion-report"
    return f"""
      <div class="delete-confirmation">
        <strong>{escape(_ui_text("Delete this meeting everywhere GRAF controls"))}</strong>
        <div class="truth-copy" data-boundary-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(_ui_text(BOUNDED_DELETE_COPY))}</div>
        <div class="state-row">
          <span class="muted">Резервные копии, локальные буферы, метаданные провайдера и уже переданные копии показываются отдельно.</span>
          <a class="mini-link" href="{report_href}">{escape(_ui_text("Report"))}</a>
        </div>
        <button type="button" disabled>{escape(_ui_text("Request deletion"))}</button>
      </div>
    """


def _render_activity(review: MeetingReviewResponse) -> str:
    activity = review.activity
    if activity is None or not activity.items:
        return f'<div class="muted">{escape(_ui_text("No access activity yet."))}</div>'
    rows = "".join(
        f"""
        <div class="activity-item">
          <div class="state-row"><strong>{escape(_ui_text(item.event_type))}</strong><span class="chip {escape(item.outcome)}">{escape(_ui_text(item.outcome))}</span></div>
          <div class="muted">{escape(_ui_text(item.actor_label))} · {escape(item.created_at.strftime("%Y-%m-%d %H:%M"))}</div>
        </div>
        """
        for item in activity.items[:6]
    )
    return f'<div class="activity-list">{rows}</div>'


def _render_governance(review: MeetingReviewResponse) -> str:
    actions = [
        review.governance.share,
        review.governance.export,
        review.governance.download,
        review.governance.retention,
        review.governance.delete,
    ]
    return "\n".join(
        f'<button type="button" title="{escape(_ui_text(action.reason or action.label))}" {"disabled" if action.state != "available" else ""}>{escape(_ui_text(action.label))}</button>'
        for action in actions
    )


def _render_top_actions(review: MeetingReviewResponse, *, embedded: bool) -> str:
    content_export_available = review.content_exports is not None and (
        review.content_exports.transcript.state == "available"
        or review.content_exports.summary.state in {"available", "partial"}
        or review.content_exports.combined.state == "available"
    )
    export_disabled = "" if content_export_available else "disabled"
    export_button = (
        f'<button type="button" {export_disabled} data-export-dialog-open '
        f'aria-haspopup="dialog" aria-controls="content-export-dialog">'
        f'{escape(_ui_text("Export"))}</button>'
    )
    if embedded:
        return (
            f'<button type="button" disabled>{escape(_ui_text("Open in browser"))}</button>'
            + export_button
        )
    share_disabled = "disabled" if review.governance.share.state != "available" else ""
    return f"""
      <button type="button" disabled>{escape(_ui_text(review.template.label))}</button>
      {export_button}
      <button type="button" {share_disabled}>{escape(_ui_text(review.governance.share.label))}</button>
      <button type="button" disabled>{escape(_ui_text("More"))}</button>
    """
