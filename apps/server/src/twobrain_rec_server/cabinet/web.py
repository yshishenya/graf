from __future__ import annotations

from html import escape
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    ArtifactEgressState,
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    TranscriptSegmentView,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review, list_cabinet_meetings

router = APIRouter(tags=["cabinet-web"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
DbDependency = Depends(get_request_db_session)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)

CSS = """
:root {
  color-scheme: dark;
  --bg: #17191b;
  --panel: #202326;
  --panel-strong: #25282c;
  --border: #34383d;
  --text: #f4f5f7;
  --muted: #a9adb4;
  --soft: #777d87;
  --accent: #8b73ff;
  --accent-strong: #7258f6;
  --green: #2ec6a3;
  --yellow: #f2c85b;
  --red: #fb6b6b;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html, body { min-height: 100%; margin: 0; background: var(--bg); color: var(--text); overflow-x: hidden; }
body { font-size: 14px; line-height: 1.45; letter-spacing: 0; }
a { color: inherit; text-decoration: none; }
a:focus-visible, button:focus-visible, .button:focus-visible, .chip:focus-visible {
  outline: 2px solid #b7a8ff;
  outline-offset: 2px;
}
button, .button {
  border: 1px solid var(--border);
  background: #262a2e;
  color: var(--text);
  border-radius: 7px;
  min-width: 0;
  min-height: 34px;
  max-width: 100%;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font: inherit;
  text-align: center;
  white-space: normal;
  overflow-wrap: anywhere;
}
button[disabled], .is-disabled { cursor: not-allowed; }
button[disabled]:not(.primary), .is-disabled { color: var(--muted); opacity: .72; }
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 184px minmax(0, 1fr); }
.app-shell.desktop-embedded { grid-template-columns: minmax(0, 1fr); }
.sidebar { background: #202326; border-right: 1px solid var(--border); padding: 14px 10px; display: flex; flex-direction: column; gap: 14px; }
.workspace { display: grid; grid-template-columns: 28px 1fr; gap: 9px; align-items: center; }
.avatar { width: 28px; height: 28px; border-radius: 7px; background: #f1f3f5; color: #24262a; display: grid; place-items: center; font-weight: 700; }
.workspace-title { font-weight: 700; }
.workspace-subtitle, .muted { color: var(--muted); font-size: 12px; }
.nav { display: grid; gap: 3px; }
.nav a { min-height: 30px; display: flex; align-items: center; gap: 8px; border-radius: 7px; padding: 0 9px; color: #d6d9df; }
.nav a.active, .nav a:hover { background: #30343a; }
.sidebar-foot { margin-top: auto; display: grid; gap: 8px; }
.trial { background: #4b37a7; border-radius: 7px; padding: 9px 10px; font-weight: 700; }
.main { min-width: 0; padding: 28px clamp(24px, 7vw, 132px); }
.topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.crumbs { display: flex; gap: 10px; align-items: center; min-width: 0; color: var(--muted); }
.crumbs strong { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.action-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.primary { background: var(--accent-strong); border-color: var(--accent-strong); color: white; font-weight: 700; }
.section-title { margin: 22px 0 10px; color: #c7cbd2; font-size: 13px; font-weight: 700; }
.upcoming { background: var(--panel); border-radius: 8px; padding: 14px 16px; display: grid; gap: 10px; border: 1px solid transparent; max-width: 900px; }
.calendar-row { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 12px; align-items: center; }
.date-badge { width: 36px; min-height: 38px; border: 1px solid var(--border); border-radius: 7px; display: grid; place-items: center; font-size: 11px; color: #dfe3ea; }
.list-card { max-width: 900px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #1d2023; }
.list-toolbar { max-width: 900px; display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; }
.filterbar { display: flex; gap: 8px; flex-wrap: wrap; color: var(--muted); }
.meeting-row { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto auto; gap: 10px; align-items: center; min-height: 48px; padding: 0 14px; border-bottom: 1px solid var(--border); }
.meeting-row:last-child { border-bottom: 0; }
.meeting-row:hover { background: #2b2f33; }
.row-icon { color: var(--muted); }
.row-title { font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-meta { color: var(--muted); font-size: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.chip { border: 1px solid var(--border); border-radius: 999px; min-height: 24px; min-width: 0; max-width: 100%; padding: 0 9px; display: inline-flex; align-items: center; color: #d9dde4; font-size: 12px; overflow-wrap: anywhere; }
.chip.ready { color: var(--green); border-color: rgba(46, 198, 163, .45); }
.chip.processing, .chip.submitted { color: var(--accent); border-color: rgba(139, 115, 255, .5); }
.chip.partial { color: var(--yellow); border-color: rgba(242, 200, 91, .45); }
.chip.failed, .chip.blocked { color: var(--red); border-color: rgba(251, 107, 107, .45); }
.chip.owner, .chip.team, .chip.shared, .chip.available { color: var(--green); border-color: rgba(46, 198, 163, .45); }
.chip.denied, .chip.policy_blocked, .chip.owner_only, .chip.audit_unavailable { color: var(--red); border-color: rgba(251, 107, 107, .45); }
.chip.disabled, .chip.missing, .chip.deleted, .chip.deleted_future { color: var(--soft); }
.future-actions { display: flex; gap: 5px; }
.icon-button { width: 30px; height: 30px; border-radius: 7px; padding: 0; color: var(--muted); }
.floating-search { position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); width: min(520px, calc(100vw - 48px)); min-height: 44px; border-radius: 999px; border: 1px solid #454a51; background: #24272b; color: var(--muted); display: flex; align-items: center; padding: 0 18px; }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 22px; align-items: start; }
.detail-main { min-width: 0; }
.tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--border); margin-bottom: 18px; }
.tab { min-height: 38px; display: inline-flex; align-items: center; border-bottom: 2px solid transparent; color: var(--muted); font-weight: 700; }
.tab.active { color: #dcd7ff; border-color: var(--accent); }
.transcript { display: grid; gap: 16px; padding-bottom: 112px; }
.segment { display: grid; grid-template-columns: 84px 112px minmax(0, 1fr); gap: 12px; }
.timestamp { color: var(--accent); font-size: 12px; font-weight: 700; }
.speaker { display: flex; align-items: center; gap: 7px; font-weight: 700; font-size: 12px; color: #d5d8de; }
.dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); }
.notes, .segment, .speaker, .text, .right-panel { min-width: 0; max-width: 100%; }
.text { color: #e6e8ec; overflow-wrap: anywhere; word-break: break-word; }
.notes .muted { overflow-wrap: anywhere; word-break: break-word; }
.empty-state { min-height: 260px; display: grid; place-items: center; text-align: center; color: var(--muted); }
.right-panel { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 14px; display: grid; gap: 14px; position: sticky; top: 24px; }
.right-panel h3, .notes h3 { margin: 0; font-size: 14px; }
.speaker-lane { display: grid; gap: 7px; }
.lane-track { height: 8px; background: #33383e; border-radius: 999px; overflow: hidden; }
.lane-fill { height: 100%; background: var(--accent); border-radius: inherit; }
.governance { display: grid; gap: 8px; }
.governance button { justify-content: flex-start; width: 100%; }
.state-list { display: grid; gap: 7px; }
.state-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: center; min-width: 0; }
.state-row strong, .state-row span { min-width: 0; overflow-wrap: anywhere; }
.state-row .muted { font-size: 11px; }
.mini-link { color: #dcd7ff; font-weight: 700; font-size: 12px; }
.activity-list { display: grid; gap: 8px; }
.activity-item { border-top: 1px solid var(--border); padding-top: 8px; display: grid; gap: 2px; }
.truth-copy { color: var(--muted); font-size: 12px; line-height: 1.35; }
.playback { position: fixed; left: 184px; right: 0; bottom: 0; min-height: 64px; border-top: 1px solid var(--border); background: #222529; display: flex; align-items: center; justify-content: center; gap: 16px; color: var(--muted); }
.detail-playback { right: calc(302px + clamp(24px, 7vw, 132px)); }
.desktop-embedded .playback { position: static; left: 0; right: 0; margin-top: 16px; }
.desktop-embedded .main { padding-right: clamp(20px, 5vw, 88px); }
@media (max-width: 900px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .main { width: 100%; max-width: 100vw; overflow-x: hidden; padding: 18px; }
  .topline { flex-direction: column; align-items: stretch; }
  .crumbs { flex-wrap: wrap; }
  .action-row { justify-content: flex-start; }
  .detail-main, .detail-layout, .transcript, .notes, .segment { width: 100%; max-width: 100%; }
  .detail-layout { grid-template-columns: 1fr; }
  .right-panel { position: static; }
  .meeting-row { grid-template-columns: 24px minmax(0, 1fr); padding: 10px 12px; }
  .meeting-row .chip, .meeting-row .future-actions { grid-column: 2; justify-self: start; }
  .segment { display: block; }
  .segment .speaker { margin-top: 3px; }
  .segment .text, .notes .muted { display: block; max-width: calc(100vw - 36px); margin-top: 7px; }
  .floating-search { position: static; transform: none; width: 100%; margin-top: 16px; }
  .playback { position: static; left: 0; right: 0; margin-top: 16px; }
  .detail-playback { right: 0; }
}
"""


@router.get("/meetings", response_class=HTMLResponse, include_in_schema=False, dependencies=[PrincipalDependency, DeviceDependency])
async def meeting_list_page(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )
    return HTMLResponse(render_meeting_list_page(response))


@router.get("/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False, dependencies=[PrincipalDependency, DeviceDependency])
async def meeting_detail_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return HTMLResponse(render_meeting_detail_page(response))


@router.get("/desktop/meetings", response_class=HTMLResponse, include_in_schema=False, dependencies=[PrincipalDependency, DeviceDependency])
async def embedded_meeting_list_page(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )
    return HTMLResponse(render_meeting_list_page(response, embedded=True))


@router.get("/desktop/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False, dependencies=[PrincipalDependency, DeviceDependency])
async def embedded_meeting_detail_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return HTMLResponse(render_meeting_detail_page(response, embedded=True))


def render_meeting_list_page(response: MeetingListResponse, *, embedded: bool = False) -> str:
    rows = "\n".join(_render_meeting_row(item, embedded=embedded) for item in response.items)
    if not rows:
        rows = '<div class="empty-state">Нет встреч для выбранного фильтра.</div>'
    new_control = "" if embedded else """
        <div class="action-row">
          <button class="button" type="button" aria-disabled="true">Filters</button>
          <button class="button" type="button" aria-disabled="true">Sort</button>
          <button class="button primary" type="button" aria-disabled="true">New</button>
          <span class="chip">Upload file</span>
        </div>
    """
    content = f"""
      <main class="main">
        <div class="topline">
          <div class="crumbs"><strong>My Meetings</strong><span>{escape(_sort_label(response.filters.sort))}</span></div>
          {new_control}
        </div>
        <section class="upcoming" aria-label="Upcoming">
          <div class="section-title">Upcoming</div>
          <div class="calendar-row"><div class="date-badge">Today<br>16</div><div><strong>Командный синк</strong><div class="muted">11:30 - 1:00PM</div></div></div>
          <div class="calendar-row"><div class="date-badge">Jun<br>19</div><div><strong>Ревью релиза</strong><div class="muted">12:00 - 1:00PM</div></div></div>
        </section>
        <div class="section-title">Meeting notes</div>
        <div class="list-toolbar">
          <div class="filterbar"><span class="chip">Search</span><span class="chip">Filters</span><span class="chip">Sort</span></div>
          {'' if embedded else '<span class="chip">New</span>'}
        </div>
        <section class="list-card" aria-label="Meeting notes">
          {rows}
        </section>
        <div class="floating-search">Ask anything...</div>
      </main>
    """
    return _page_shell("My Meetings", content, embedded=embedded)


def render_meeting_detail_page(review: MeetingReviewResponse, *, embedded: bool = False) -> str:
    transcript = _render_transcript(review.transcript.segments)
    if not review.transcript.available:
        transcript = f"""
          <div class="empty-state">
            <div>
              <strong>{_empty_title(review)}</strong>
              <div class="muted">{_empty_body(review)}</div>
            </div>
          </div>
        """
    recording_tab = "Transcript" if embedded else "Recording &amp; Transcript"
    speaker_lanes = _render_speaker_lanes(review)
    content = f"""
      <main class="main">
        <div class="topline">
          <div class="crumbs"><a href="{_base_path(embedded)}">My Meetings</a><span>/</span><strong>{escape(review.meeting.title)}</strong><span>{escape(review.meeting.status_label)}</span>{_render_access_chip(review.meeting.access)}</div>
          <div class="action-row">{_render_top_actions(review, embedded=embedded)}</div>
        </div>
        <div class="tabs">
          <span class="tab">Notes</span>
          <span class="tab active">{recording_tab}</span>
        </div>
        <div class="detail-layout">
          <section class="detail-main">
            <div class="notes">
              <h3>Notes</h3>
              <div class="muted">{_notes_copy(review)}</div>
            </div>
            <div class="transcript">{transcript}</div>
          </section>
          <aside class="right-panel">
            <h3>Access</h3>
            {_render_access_summary(review)}
            <h3>Share</h3>
            {_render_share_panel(review)}
            <h3>Artifacts</h3>
            {_render_artifacts(review)}
            <div class="truth-copy">{escape(review.deletion_truth_copy or "")}</div>
            <h3>Assign speakers</h3>
            {speaker_lanes}
            <h3>Governance</h3>
            <div class="governance">{_render_governance(review)}</div>
            <h3>Activity</h3>
            {_render_activity(review)}
            <h3>Assistant</h3>
            <button type="button" disabled>{escape(review.assistant.label)}</button>
            <h3>Template</h3>
            <button type="button" disabled>{escape(review.template.label)}</button>
          </aside>
        </div>
        <div class="playback detail-playback"><span>{escape(review.meeting.status_label)}</span><span>1x</span><span>{_duration(review.playback.duration_seconds)}</span></div>
      </main>
    """
    return _page_shell(review.meeting.title, content, embedded=embedded)


def _page_shell(title: str, content: str, *, embedded: bool) -> str:
    class_name = "app-shell desktop-embedded" if embedded else "app-shell"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - 2brain Rec</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="{class_name}">
    {'' if embedded else _sidebar()}
    {content}
  </div>
</body>
</html>"""


def _sidebar() -> str:
    return """
    <aside class="sidebar">
      <div class="workspace"><div class="avatar">2</div><div><div class="workspace-title">Personal</div><div class="workspace-subtitle">Free plan</div></div></div>
      <button class="primary" type="button" disabled>Invite teammates</button>
      <nav class="nav" aria-label="Cabinet">
        <a href="/meetings" class="active">My Meetings</a>
        <a href="#" aria-disabled="true">Shared with me</a>
        <a href="#" aria-disabled="true">Action Items</a>
        <a href="#" aria-disabled="true">Activity</a>
        <a href="#" aria-disabled="true">Contacts</a>
        <a href="#" aria-disabled="true">Settings</a>
      </nav>
      <div class="sidebar-foot"><div class="trial">TRIAL 7 days left</div><div class="muted">2brain Rec</div></div>
    </aside>
    """


def _render_meeting_row(item: MeetingListItem, *, embedded: bool) -> str:
    href = f"{_base_path(embedded)}/{item.meeting_id}"
    future = "".join(f'<button class="icon-button" type="button" disabled>{escape(slot.label[:1])}</button>' for slot in item.future_slots)
    access_chip = _render_access_chip(item.access)
    return f"""
      <a class="meeting-row" href="{href}">
        <span class="row-icon">◌</span>
        <span>
          <span class="row-title">{escape(item.title)}</span>
          <span class="row-meta"><span>{_duration(item.duration_seconds)}</span><span>{_date_label(item)}</span></span>
        </span>
        <span class="state-list"><span class="chip {escape(item.status)}">{escape(item.status_label)}</span>{access_chip}</span>
        <span class="future-actions">{future}</span>
      </a>
    """


def _render_transcript(segments: list[TranscriptSegmentView]) -> str:
    return "\n".join(
        f"""
          <article class="segment">
            <div class="timestamp">{escape(segment.timestamp_label)}</div>
            <div class="speaker"><span class="dot"></span>{escape(segment.speaker_label)}</div>
            <div class="text">{escape(segment.text)}</div>
          </article>
        """
        for segment in segments
    )


def _render_speaker_lanes(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return '<div class="muted">Speaker lanes are reserved until diarization is available.</div>'
    return "\n".join(
        f"""
        <div class="speaker-lane">
          <div class="row-meta"><strong>{escape(speaker.label)}</strong><span>{speaker.talk_time_percent}%</span></div>
          <div class="lane-track"><div class="lane-fill" style="width:{speaker.talk_time_percent}%"></div></div>
        </div>
        """
        for speaker in review.speakers.speakers
    )


def _render_access_chip(access) -> str:
    if access is None:
        return ""
    return f'<span class="chip {escape(access.state)}">{escape(access.label)}</span>'


def _render_access_summary(review: MeetingReviewResponse) -> str:
    access = review.access
    if access is None:
        return '<div class="muted">Access state is unavailable.</div>'
    reason = f'<div class="muted">{escape(access.reason)}</div>' if access.reason else ""
    capabilities = [
        ("Share", access.can_share),
        ("Download", access.can_download),
        ("Export", access.can_export),
    ]
    capability_rows = "".join(
        f'<div class="state-row"><span>{escape(label)}</span><span class="chip {"available" if enabled else "disabled"}">{ "On" if enabled else "Off" }</span></div>'
        for label, enabled in capabilities
    )
    return f"""
      <div class="state-list">
        <div class="state-row"><strong>{escape(access.label)}</strong><span class="chip {escape(access.state)}">{escape(access.state)}</span></div>
        {reason}
        {capability_rows}
      </div>
    """


def _render_share_panel(review: MeetingReviewResponse) -> str:
    share = review.share
    if share is None:
        return '<div class="muted">Sharing is unavailable for this meeting.</div>'
    grants = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(grant.display_name)}</strong><br><span class="muted">{escape(grant.role_label)}</span></span>
          <span class="chip {escape(grant.status)}">{escape(grant.status)}</span>
        </div>
        """
        for grant in share.active_grants
    )
    if not grants:
        grants = '<div class="muted">No active user grants.</div>'
    return f"""
      <div class="state-list">
        <div class="state-row"><span>Team visibility</span><span class="chip {escape(share.team_visibility)}">{escape(share.team_visibility.replace("_", " "))}</span></div>
        <div class="state-row"><span>Copy link</span><span class="chip {escape(share.copy_link_state)}">{escape(share.copy_link_state.replace("_", " "))}</span></div>
        <div class="state-row"><span>Public links</span><span class="chip {escape(share.public_link_state)}">{escape(share.public_link_state.replace("_", " "))}</span></div>
        {grants}
      </div>
    """


def _render_artifacts(review: MeetingReviewResponse) -> str:
    if not review.artifacts:
        return '<div class="muted">No exportable artifacts yet.</div>'
    rows = "".join(_render_artifact_state(review, artifact) for artifact in review.artifacts)
    return f'<div class="state-list">{rows}</div>'


def _render_artifact_state(review: MeetingReviewResponse, artifact: ArtifactEgressState) -> str:
    label = escape(artifact.label)
    reason = f'<span class="muted">{escape(artifact.reason)}</span>' if artifact.reason else ""
    if artifact.state == "available" and artifact.artifact_class != "package":
        action = (
            f'<a class="mini-link" href="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/downloads/'
            f'{escape(artifact.artifact_class)}">Download</a>'
        )
    elif artifact.state == "available":
        action = '<span class="chip available">Export ready</span>'
    else:
        action = f'<span class="chip {escape(artifact.state)}">{escape(artifact.state.replace("_", " "))}</span>'
    return f"""
      <div class="state-row">
        <span><strong>{label}</strong><br>{reason}</span>
        {action}
      </div>
    """


def _render_activity(review: MeetingReviewResponse) -> str:
    activity = review.activity
    if activity is None or not activity.items:
        return '<div class="muted">No access activity yet.</div>'
    rows = "".join(
        f"""
        <div class="activity-item">
          <div class="state-row"><strong>{escape(item.event_type.replace("_", " "))}</strong><span class="chip {escape(item.outcome)}">{escape(item.outcome)}</span></div>
          <div class="muted">{escape(item.actor_label)} · {escape(item.created_at.strftime("%Y-%m-%d %H:%M"))}</div>
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
        f'<button type="button" title="{escape(action.reason or action.label)}" {"disabled" if action.state != "available" else ""}>{escape(action.label)}</button>'
        for action in actions
    )


def _render_top_actions(review: MeetingReviewResponse, *, embedded: bool) -> str:
    if embedded:
        return '<button type="button" disabled>Open in browser</button>'
    export_disabled = "disabled" if review.governance.export.state != "available" else ""
    share_disabled = "disabled" if review.governance.share.state != "available" else ""
    return f"""
      <button type="button" disabled>{escape(review.template.label)}</button>
      <button type="button" {export_disabled}>{escape(review.governance.export.label)}</button>
      <button type="button" {share_disabled}>{escape(review.governance.share.label)}</button>
      <button type="button" disabled>More</button>
    """


def _notes_copy(review: MeetingReviewResponse) -> str:
    if review.notes.unavailable_reason == "generation_future":
        return "AI notes are reserved for a later feature. No summary in 016."
    if review.notes.unavailable_reason == "processing":
        return "Notes will stay unavailable until transcript processing finishes."
    return "Notes are not available for this meeting."


def _empty_title(review: MeetingReviewResponse) -> str:
    if review.processing.state in {"processing", "submitted"}:
        return "Транскрипт готовится"
    if review.processing.state == "failed":
        return "Обработка остановилась"
    if review.processing.state == "blocked":
        return "Обработка требует проверки"
    return "Транскрипт недоступен"


def _empty_body(review: MeetingReviewResponse) -> str:
    if review.processing.reason_label:
        return review.processing.reason_label
    if review.processing.state in {"processing", "submitted"}:
        return "Мы показываем только подтвержденные данные и не создаем фальшивый текст."
    return "Проверьте статус обработки позже."


def _duration(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{second}s"


def _date_label(item: MeetingListItem) -> str:
    if item.started_at is None:
        return "No date"
    return item.started_at.strftime("%b %-d")


def _sort_label(sort: str) -> str:
    return {
        "updated_desc": "Newest first",
        "updated_asc": "Oldest first",
        "duration_desc": "Longest first",
        "duration_asc": "Shortest first",
    }.get(sort, "Newest first")


def _base_path(embedded: bool) -> str:
    return "/desktop/meetings" if embedded else "/meetings"
