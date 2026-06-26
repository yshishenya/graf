from __future__ import annotations

import secrets
from datetime import UTC, datetime
from html import escape
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    ArtifactDeletionState,
    ArtifactEgressState,
    DeletionVerificationReport,
    LocalPurgeTask,
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    NotesActionCategoryState,
    TranscriptSegmentView,
)
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    get_principal,
    get_web_owner_tenant_scope,
)
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.providers import build_provider_registry
from twobrain_rec_server.auth.sessions import (
    callback_expiry,
    hash_token,
    issue_auth_session,
)
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review, list_cabinet_meetings
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Meeting,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.deletion.service import deletion_report_response

router = APIRouter(tags=["cabinet-web"])

WebTenantDependency = Depends(get_web_owner_tenant_scope)
PrincipalDependency = Depends(get_principal)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)
LoginWorkspaceQuery = Query(default=None)
LoginNextQuery = Query(default="/meetings", alias="next", max_length=512)
LoginErrorQuery = Query(default=None, max_length=120)
SignupModeQuery = Query(default=None, max_length=32, alias="mode")
LoginEmailForm = Form(..., max_length=240)
LoginCodeForm = Form(..., max_length=32)
LoginStateForm = Form(..., max_length=160)
LoginWorkspaceForm = Form(default=None)
LoginNextForm = Form(default="/meetings", alias="next", max_length=512)
EMAIL_LOGIN_PROVIDER = "email"
EMAIL_SIGNUP_PROVIDER = "email_signup"


@router.get("/favicon.ico", include_in_schema=False)
@router.get("/apple-touch-icon.png", include_in_schema=False)
@router.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def browser_icon_probe() -> Response:
    return Response(status_code=204)


async def get_web_request_db_session(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


WebDbDependency = Depends(get_web_request_db_session)


async def get_web_login_db_session(request: Request):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        yield session


LoginDbDependency = Depends(get_web_login_db_session)

CSS = """
:root {
  color-scheme: dark;
  --bg: #191a1c;
  --panel: #202224;
  --surface: #242629;
  --surface-2: #26282c;
  --surface-3: #2f3237;
  --line: #30343a;
  --line-soft: rgba(255,255,255,.07);
  --text: #e8eaee;
  --muted: #a8adb5;
  --subtle: #7c828b;
  --accent: #8c73ff;
  --blue: #2f91ff;
  --green: #2fc9a6;
  --amber: #f0a742;
  --red: #ff6b6b;
  --pink: #d96aa6;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, ui-sans-serif, sans-serif;
}
* { box-sizing: border-box; }
html, body { min-height: 100%; margin: 0; background: var(--bg); color: var(--text); overflow-x: hidden; }
body { font-size: 13px; line-height: 1.38; letter-spacing: 0; font-weight: 500; -webkit-font-smoothing: antialiased; text-rendering: geometricPrecision; }
body.auth-leaving .auth-panel {
  opacity: 0;
  transform: translateY(-4px) scale(.992);
  filter: blur(1px);
}
body.auth-leaving .auth-page::before { opacity: .35; }
a { color: inherit; text-decoration: none; }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, .button:focus-visible {
  outline: 2px solid #b6aaff;
  outline-offset: 2px;
}
button, .button, input, select {
  font: inherit;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--text);
  border-radius: 7px;
  min-height: 32px;
}
button, .button {
  min-width: 0;
  max-width: 100%;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  overflow-wrap: anywhere;
}
button[disabled], .is-disabled { color: var(--muted); cursor: not-allowed; opacity: .72; }
input, select { padding: 0 10px; width: 100%; min-width: 0; }
.primary { background: var(--blue); border-color: var(--blue); color: white; font-weight: 700; }
.quiet { background: transparent; }
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 184px minmax(0, 1fr); }
.app-shell.desktop-embedded { grid-template-columns: minmax(0, 1fr); }
.sidebar {
  background: var(--panel);
  border-right: 1px solid var(--line);
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.brand { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 10px; align-items: center; }
.workspace { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 8px; align-items: center; }
.brand-mark, .avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-weight: 800;
}
.brand-mark { background: #7a2b82; color: white; }
.avatar { background: #f0f2f5; color: #24272b; width: 28px; height: 28px; border-radius: 7px; }
.workspace-title { font-weight: 750; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workspace-subtitle, .muted { color: var(--muted); font-size: 12px; }
.nav { display: grid; gap: 4px; }
.nav a {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 7px;
  padding: 0 9px;
  color: #d6dae1;
}
.nav a.active, .nav a:hover { background: var(--surface-3); }
.nav-count { margin-left: auto; min-width: 20px; min-height: 20px; border-radius: 999px; background: #71347e; display: grid; place-items: center; font-size: 12px; }
.sidebar-foot { margin-top: auto; display: grid; gap: 8px; }
.trial { background: #3b3270; border-radius: 7px; padding: 9px 10px; font-weight: 700; }
.main { min-width: 0; padding: 28px clamp(24px, 7vw, 118px) 92px; }
.detail-page-main { padding-bottom: 192px; }
.desktop-embedded .main { padding: 22px clamp(18px, 4vw, 64px) 28px; }
.desktop-embedded .detail-page-main { padding-bottom: 192px; }
.topline { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 18px; }
.page-title { display: grid; gap: 2px; min-width: 0; }
h1 { margin: 0; font-size: 24px; line-height: 1.15; letter-spacing: 0; font-weight: 700; }
.page-subtitle { color: var(--muted); font-weight: 600; }
.crumbs { display: flex; gap: 9px; align-items: center; min-width: 0; color: var(--muted); flex-wrap: wrap; }
.crumbs strong { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: min(62vw, 760px); }
.action-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 12px 0 20px; max-width: 980px; }
.metric {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: var(--surface);
  min-height: 86px;
  padding: 14px;
  display: grid;
  gap: 4px;
}
.metric strong { font-size: 22px; }
.metric span { color: var(--muted); }
.toolbar {
  max-width: 980px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 132px 132px 132px auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.section-title { margin: 22px 0 10px; color: #c6cad1; font-size: 12px; font-weight: 700; }
.upcoming {
  background: var(--surface);
  border-radius: 8px;
  padding: 14px 16px;
  display: grid;
  gap: 10px;
  border: 1px solid var(--line-soft);
  max-width: 980px;
}
.calendar-row { display: grid; grid-template-columns: 42px minmax(0, 1fr); gap: 12px; align-items: center; }
.date-badge { width: 36px; min-height: 38px; border: 1px solid var(--line); border-radius: 7px; display: grid; place-items: center; font-size: 11px; color: #dfe3ea; }
.list-card { max-width: 980px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #1d1f21; }
.meeting-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) minmax(128px, auto) minmax(112px, auto);
  gap: 12px;
  align-items: center;
  min-height: 58px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}
.meeting-row:last-child { border-bottom: 0; }
.meeting-row:hover { background: #282c31; }
.row-icon { color: var(--muted); font-size: 16px; }
.row-title { font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.row-meta { color: var(--muted); font-size: 12px; display: flex; gap: 9px; flex-wrap: wrap; }
.row-actions { display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--line);
  border-radius: 999px;
  min-height: 24px;
  min-width: 0;
  max-width: 100%;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  color: #d9dde4;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.chip.ready, .chip.owner, .chip.team, .chip.shared, .chip.available, .chip.completed { color: var(--green); border-color: rgba(47,201,166,.48); background: rgba(47,201,166,.08); }
.chip.processing, .chip.submitted, .chip.uploading, .chip.partial, .chip.requested { color: var(--accent); border-color: rgba(125,107,255,.48); background: rgba(125,107,255,.08); }
.chip.local_only, .chip.deferred, .chip.unavailable, .chip.disabled, .chip.missing, .chip.deleted_future { color: var(--subtle); }
.chip.failed, .chip.blocked, .chip.denied, .chip.policy_blocked, .chip.owner_only, .chip.audit_unavailable { color: var(--red); border-color: rgba(255,107,107,.48); background: rgba(255,107,107,.08); }
.chip.warning { color: var(--amber); border-color: rgba(240,167,66,.5); background: rgba(240,167,66,.08); }
.icon-button { width: 30px; height: 30px; border-radius: 7px; padding: 0; color: var(--muted); }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) 316px; gap: 18px; align-items: start; }
.detail-main { min-width: 0; display: grid; gap: 16px; }
.tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--line); margin-bottom: 16px; }
.tab {
  appearance: none;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--muted);
  font-weight: 750;
  padding: 0;
  cursor: pointer;
}
.tab.active { color: #dcd7ff; border-color: var(--accent); }
.tab-panel[hidden] { display: none; }
.panel {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: var(--surface);
  padding: 16px;
  min-width: 0;
}
.panel h2, .panel h3, .right-panel h3 { margin: 0; font-size: 15px; letter-spacing: 0; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.revision-status { display: grid; gap: 6px; border-bottom: 1px solid var(--line-soft); padding-bottom: 12px; }
.revision-status .row-meta { gap: 6px; }
.notes-outcomes { display: grid; gap: 8px; }
.notes-outcome-row { padding: 10px 0; border-bottom: 1px solid var(--line-soft); }
.notes-outcome-row:last-child { border-bottom: 0; }
.notes-outcome-row .outcome-item { grid-column: 1 / -1; display: grid; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.transcript { display: grid; gap: 14px; }
.segment { display: grid; grid-template-columns: 76px 112px minmax(0, 1fr); gap: 12px; min-width: 0; }
.timestamp { color: var(--accent); font-size: 12px; font-weight: 750; }
.timestamp-seek { appearance: none; border: 0; background: transparent; padding: 0; cursor: pointer; text-align: left; }
.timestamp-seek:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }
.speaker { display: flex; align-items: center; gap: 7px; font-weight: 750; font-size: 12px; color: #d5d8de; min-width: 0; }
.dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); flex: 0 0 auto; }
.text { color: #e6e8ec; overflow-wrap: anywhere; word-break: break-word; min-width: 0; }
.empty-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--muted);
  padding: 24px;
}
.empty-state strong { display: block; color: var(--text); margin-bottom: 6px; }
.right-panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  display: grid;
  gap: 14px;
  position: sticky;
  top: 24px;
  min-width: 0;
}
.speaker-lane { display: grid; gap: 7px; }
.lane-track { height: 8px; background: #343941; border-radius: 999px; overflow: hidden; }
.lane-fill { height: 100%; background: var(--accent); border-radius: inherit; }
.governance { display: grid; gap: 8px; }
.governance button { justify-content: flex-start; width: 100%; }
.state-list { display: grid; gap: 7px; }
.state-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: center; min-width: 0; }
.state-row strong, .state-row span { min-width: 0; overflow-wrap: anywhere; }
.mini-link { color: #dcd7ff; font-weight: 750; font-size: 12px; }
.activity-list { display: grid; gap: 8px; }
.activity-item { border-top: 1px solid var(--line-soft); padding-top: 8px; display: grid; gap: 2px; }
.truth-copy { color: var(--muted); font-size: 12px; line-height: 1.35; }
.delete-confirmation { border: 1px solid rgba(255,107,107,.35); border-radius: 8px; padding: 12px; display: grid; gap: 10px; background: rgba(255,107,107,.05); }
.delete-confirmation strong { color: #ffd6d6; }
.report-layout { max-width: 980px; display: grid; gap: 18px; padding-bottom: 96px; }
.report-band { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); padding: 16px; display: grid; gap: 12px; }
.report-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.playback-bar {
  position: fixed;
  left: 184px;
  right: 0;
  bottom: 0;
  min-height: 132px;
  border-top: 1px solid var(--line);
  background: rgba(33,36,40,.98);
  box-shadow: 0 -18px 44px rgba(0,0,0,.28);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  padding: 14px clamp(18px, 4vw, 56px) 12px;
  color: var(--muted);
  z-index: 30;
}
.desktop-embedded .playback-bar { left: 0; }
.playback-bar.is-unavailable {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.playback-audio { display: none; }
.playback-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
.playback-round {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  padding: 0;
  background: #2d3035;
  border-color: #3b4047;
  color: #eef0f4;
  font-weight: 850;
}
.playback-round.primary-play {
  width: 42px;
  height: 42px;
  background: #f1f3f6;
  border-color: #f1f3f6;
  color: #1e2125;
}
.playback-speed {
  min-width: 46px;
  border: 0;
  background: transparent;
  color: #e5e7eb;
  font-weight: 800;
}
.playback-progress-row {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 54px;
  gap: 10px;
  align-items: center;
}
.playback-time {
  color: #c7cbd2;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}
.playback-time:last-child { text-align: right; }
.playback-progress {
  width: 100%;
  accent-color: var(--accent);
}
.speaker-timeline {
  display: grid;
  gap: 7px;
}
.timeline-lane {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) 42px;
  gap: 10px;
  align-items: center;
}
.timeline-label {
  color: #d9dde4;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.timeline-track {
  position: relative;
  height: 8px;
  border-radius: 999px;
  background: #353940;
  overflow: hidden;
}
.timeline-segment {
  position: absolute;
  top: 0;
  bottom: 0;
  min-width: 2px;
  border-radius: 999px;
  background: var(--accent);
}
.timeline-lane:nth-child(6n+1) .timeline-segment { background: #ffd24a; }
.timeline-lane:nth-child(6n+2) .timeline-segment { background: #ff6b6b; }
.timeline-lane:nth-child(6n+3) .timeline-segment { background: #2fc9c0; }
.timeline-lane:nth-child(6n+4) .timeline-segment { background: #7a65ff; }
.timeline-lane:nth-child(6n+5) .timeline-segment { background: #aaa49a; }
.timeline-lane:nth-child(6n+6) .timeline-segment { background: #d96aa6; }
.timeline-share {
  text-align: right;
  color: var(--muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 76% 4%, rgba(105,78,255,.27), transparent 27%),
    linear-gradient(120deg, #181a1d 0%, #17191c 46%, #211d38 100%);
}
.auth-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(112deg, rgba(255,255,255,.035) 0 1px, transparent 1px 45%),
    linear-gradient(292deg, rgba(255,255,255,.025) 0 1px, transparent 1px 45%);
  opacity: .55;
  pointer-events: none;
}
.auth-panel {
  width: min(376px, 100%);
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(35,37,40,.96);
  padding: 24px;
  display: grid;
  gap: 18px;
  box-shadow: 0 22px 52px rgba(0,0,0,.42);
  position: relative;
  z-index: 1;
  animation: rec-panel-in .24s cubic-bezier(.2,.8,.2,1) both;
  transition:
    opacity .16s cubic-bezier(.2,.8,.2,1),
    transform .16s cubic-bezier(.2,.8,.2,1),
    filter .16s cubic-bezier(.2,.8,.2,1);
}
.auth-panel h1 { font-size: 20px; text-align: center; }
.auth-brand-wordmark { text-align: center; font-size: 25px; line-height: 1; font-weight: 850; }
.auth-subtitle { color: var(--muted); font-size: 12px; line-height: 1.35; text-align: center; }
.auth-actions { display: grid; gap: 8px; }
.auth-actions > *, .email-mode > *, .auth-form > * {
  animation: rec-item-in .22s cubic-bezier(.2,.8,.2,1) both;
}
.auth-actions > *:nth-child(2), .email-mode > *:nth-child(2), .auth-form > *:nth-child(2) { animation-delay: .025s; }
.auth-actions > *:nth-child(3), .email-mode > *:nth-child(3), .auth-form > *:nth-child(3) { animation-delay: .05s; }
.auth-actions > *:nth-child(4), .email-mode > *:nth-child(4), .auth-form > *:nth-child(4) { animation-delay: .075s; }
.auth-provider {
  min-height: 32px;
  border: 1px solid #4a4e57;
  border-radius: 7px;
  background: #24272b;
  color: #eef0f4;
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  font-weight: 750;
  font-size: 13px;
}
.auth-provider:hover { border-color: #6860a8; background: #2a2d33; }
.auth-provider[aria-disabled="true"] { color: var(--muted); pointer-events: none; }
.provider-mark { color: #f7f8fb; font-weight: 850; text-align: center; }
.provider-pill {
  min-height: 18px;
  border-radius: 999px;
  padding: 0 6px;
  background: #745df3;
  color: #f7f5ff;
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 800;
}
.auth-divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 11px;
  color: var(--subtle);
  font-size: 12px;
}
.auth-divider::before, .auth-divider::after { content: ""; height: 1px; background: var(--line); }
.auth-form { display: grid; gap: 10px; }
.auth-form label { display: grid; gap: 7px; color: #c5c9d0; font-size: 12px; font-weight: 750; }
.auth-form input { min-height: 34px; border-color: #555a64; background: #26292e; }
.auth-form .primary {
  min-height: 34px;
  background: #7057ff;
  border-color: #7057ff;
}
.auth-form .primary:hover { background: #7c66ff; border-color: #7c66ff; }
.auth-secondary {
  text-align: center;
  display: grid;
  gap: 18px;
  color: #d7d9df;
}
.auth-signup { color: #d7d9df; font-size: 13px; }
.auth-signup a, .auth-legal a { color: #c9c1ff; font-weight: 750; }
.auth-legal {
  position: absolute;
  z-index: 1;
  left: 24px;
  right: 24px;
  bottom: 24px;
  max-width: 540px;
  margin: 0 auto;
  text-align: center;
  color: #a4a9b2;
  font-size: 11px;
  line-height: 1.45;
}
.auth-alert { border: 1px solid rgba(255,107,107,.35); border-radius: 8px; padding: 10px 12px; background: rgba(255,107,107,.07); color: #ffd6d6; font-size: 12px; font-weight: 750; }
.code-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin: 12px 0 8px;
}
.code-slot {
  height: 46px;
  padding: 0;
  text-align: center;
  font-size: 22px;
  font-weight: 800;
  border-radius: 7px;
  border-color: #3f444d;
  background: #1d2024;
  caret-color: #a89cff;
}
.code-slot:focus {
  border-color: #765fff;
  box-shadow: 0 0 0 1px #765fff;
}
.code-hint { text-align: center; color: var(--muted); font-size: 11px; font-weight: 650; }
.auth-resend {
  border: 0;
  background: transparent;
  color: #c5bbff;
  justify-self: center;
  min-height: 32px;
  padding: 0;
  font-weight: 800;
}
.auth-resend:hover { color: #ded8ff; }
.email-mode {
  display: grid;
  gap: 14px;
}
.email-mode-trigger {
  min-height: 34px;
  border-radius: 7px;
  border: 1px solid #4a4e57;
  background: #24272b;
  color: #eef0f4;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 800;
}
.email-mode-trigger:hover { color: #fff; background: #2a2d33; border-color: #6860a8; }
.signup-email-form { display: grid; gap: 12px; }
.auth-help { text-align: center; color: #a9abb4; text-decoration: underline; text-underline-offset: 2px; }
.cabinet-main {
  min-height: 100vh;
  background: var(--bg);
  padding: 34px clamp(24px, 5vw, 96px) 92px;
}
.desktop-embedded .cabinet-main {
  min-height: 100vh;
  padding: 24px clamp(18px, 4vw, 64px) 80px;
}
.cabinet-workspace { width: 100%; max-width: 1120px; }
.desktop-embedded .cabinet-workspace { width: 100%; max-width: min(1120px, calc(100vw - 48px)); margin: 0 auto; }
.cabinet-topbar {
  min-height: 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}
.cabinet-titleline { display: flex; align-items: center; gap: 9px; min-width: 0; color: var(--muted); font-weight: 500; }
.cabinet-titleline strong { color: var(--text); font-weight: 700; }
.cabinet-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  animation: rec-item-in .22s cubic-bezier(.2,.8,.2,1) both;
}
.upcoming.cabinet-card {
  max-width: none;
  padding: 12px 14px;
  gap: 9px;
}
.cabinet-card .section-title { margin: 0 0 4px; }
.calendar-day {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 11px;
  align-items: start;
}
.calendar-events { display: grid; gap: 8px; }
.calendar-event { border-left: 3px solid #9cd9ff; padding-left: 10px; min-height: 28px; }
.calendar-event strong, .meeting-title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 650; }
.meeting-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin: 18px 0 8px;
  min-height: 28px;
}
.meeting-toolbar .section-title { margin: 0; }
.selection-toolbar {
  display: flex;
  justify-content: flex-start;
  gap: 10px;
  align-items: center;
}
.selection-toolbar[hidden] { display: none; }
.selection-toggle {
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: 5px;
  background: var(--accent);
  color: #17191c;
}
.selection-count { font-weight: 800; color: #f0edff; white-space: nowrap; }
.selection-actions { display: flex; align-items: center; gap: 6px; justify-content: flex-start; }
.selection-divider { width: 1px; height: 22px; margin: 0 4px; background: var(--line); }
.danger-button { color: #ffd6d6; border-color: rgba(255,107,107,.5); background: rgba(255,107,107,.08); }
.toolbar-icons { display: flex; align-items: center; gap: 8px; }
.icon-control {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #b5bac3;
  display: inline-grid;
  place-items: center;
}
.icon-control:hover { background: #2d3034; }
.icon-control:disabled, .icon-control.is-disabled {
  color: #8f949d;
  cursor: not-allowed;
}
.icon-control:disabled:hover { background: transparent; }
.ui-icon {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.tooltip-wrap {
  position: relative;
  display: inline-grid;
  place-items: center;
}
.tooltip-wrap:hover::after, .tooltip-wrap:focus-visible::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 50%;
  top: calc(100% + 8px);
  z-index: 20;
  width: max-content;
  max-width: 220px;
  transform: translateX(-50%);
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #24272a;
  color: var(--text);
  box-shadow: 0 12px 28px rgba(0,0,0,.32);
  font-size: 12px;
  white-space: normal;
}
.new-button {
  min-height: 28px;
  min-width: 54px;
  padding: 0 12px;
  border-radius: 7px;
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.list-card.cabinet-card {
  max-width: none;
  min-height: 210px;
  background: #1d1f21;
  border-color: var(--line);
}
.meeting-row {
  color: #dfe2e8;
}
.meeting-row.cabinet-row {
  grid-template-columns: 24px 20px minmax(0, 1fr) 32px 64px;
  min-height: 46px;
  padding: 4px 12px;
  gap: 8px;
}
.meeting-row.cabinet-row:hover { background: #2c2f33; }
.meeting-row.is-selected { background: #302860; }
.meeting-row .row-check {
  appearance: none;
  width: 16px;
  height: 16px;
  min-height: 16px;
  padding: 0;
  border: 1px solid #686e78;
  border-radius: 4px;
  background: transparent;
}
.meeting-row .row-check:checked {
  background: var(--accent);
  border-color: var(--accent);
}
.meeting-row .row-check:checked::after {
  content: "✓";
  display: grid;
  place-items: center;
  color: #17191c;
  font-size: 12px;
  font-weight: 900;
}
.row-icon { display: grid; place-items: center; color: #a7adb7; font-size: 13px; }
.meeting-date { color: #c1c6cf; font-size: 12px; text-align: right; white-space: nowrap; }
.row-delete {
  width: 24px;
  height: 24px;
  font-size: 11px;
  border-color: transparent;
  background: transparent;
  color: #ffc7c7;
  opacity: 0;
  display: inline-grid;
  place-items: center;
}
.meeting-row:hover .row-delete, .meeting-row:focus-within .row-delete {
  opacity: 1;
}
.delete-dialog {
  width: min(440px, calc(100vw - 36px));
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  padding: 22px;
  box-shadow: 0 24px 70px rgba(0,0,0,.5);
}
.delete-dialog::backdrop { background: rgba(0,0,0,.62); }
.delete-dialog h2 { margin: 0 0 16px; font-size: 22px; line-height: 1.2; }
.delete-dialog p { margin: 0 0 12px; color: #eef0f4; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.dialog-error { color: #ffd6d6; font-size: 12px; margin-top: 12px; }
.dialog-error[hidden] { display: none; }
.floating-search {
  position: fixed;
  left: 50%;
  bottom: 16px;
  width: min(430px, calc(100vw - 320px));
  transform: translateX(-50%);
  min-height: 40px;
  border: 1px solid #42464e;
  background: var(--surface);
  color: #aeb4be;
  border-radius: 999px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  box-shadow: 0 12px 34px rgba(0,0,0,.26);
  font-size: 13px;
}
.desktop-embedded .floating-search {
  left: 50%;
  right: auto;
  bottom: 16px;
  width: min(366px, calc(100vw - 48px));
  transform: translateX(-50%);
}
.desktop-embedded .empty-state { min-height: 210px; }
.desktop-embedded .meeting-row:hover { transform: none; }
.auth-provider, .email-mode-trigger, .code-slot, .meeting-row, .icon-control, .new-button {
  transition:
    background-color .16s cubic-bezier(.2,.8,.2,1),
    border-color .16s cubic-bezier(.2,.8,.2,1),
    color .16s cubic-bezier(.2,.8,.2,1),
    transform .16s cubic-bezier(.2,.8,.2,1),
    opacity .16s cubic-bezier(.2,.8,.2,1);
}
.auth-provider:active, .email-mode-trigger:active, .new-button:active { transform: translateY(1px) scale(.995); }
.meeting-row:hover { transform: translateX(2px); }
.code-slot { animation: rec-slot-in .18s cubic-bezier(.2,.8,.2,1) both; }
.code-slot:nth-child(2) { animation-delay: .02s; }
.code-slot:nth-child(3) { animation-delay: .04s; }
.code-slot:nth-child(4) { animation-delay: .06s; }
.code-slot:nth-child(5) { animation-delay: .08s; }
.code-slot:nth-child(6) { animation-delay: .1s; }
@keyframes rec-panel-in {
  from { opacity: 0; transform: translateY(10px) scale(.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes rec-item-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes rec-slot-in {
  from { opacity: 0; transform: translateY(5px) scale(.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes rec-fade-in {
  from { opacity: 0; filter: blur(2px); }
  to { opacity: 1; filter: blur(0); }
}
@keyframes rec-fade-out {
  from { opacity: 1; filter: blur(0); }
  to { opacity: 0; filter: blur(1px); }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .001ms !important;
  }
}
@media (max-width: 980px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .main { width: 100%; max-width: 100vw; overflow-x: hidden; padding: 18px; }
  .detail-page-main { padding-bottom: 172px; }
  .cabinet-main { padding: 18px 14px 172px; }
  .cabinet-workspace { max-width: none; }
  .topline { flex-direction: column; align-items: stretch; }
  .action-row { justify-content: flex-start; }
  .metric-grid { grid-template-columns: 1fr; }
  .toolbar { grid-template-columns: 1fr 1fr; }
  .toolbar button { grid-column: span 2; }
  .detail-layout { grid-template-columns: 1fr; }
  .right-panel { position: static; }
  .meeting-row { grid-template-columns: 24px minmax(0, 1fr); padding: 12px; }
  .meeting-row.cabinet-row { grid-template-columns: 20px minmax(0, 1fr) 28px auto; min-height: 48px; }
  .meeting-row.cabinet-row .meeting-date { grid-column: 3; }
  .meeting-row.cabinet-row .row-delete { grid-column: 4; opacity: 1; }
  .meeting-toolbar { align-items: flex-start; flex-wrap: wrap; }
  .selection-actions { justify-content: flex-start; }
  .meeting-row > .state-list, .meeting-row > .row-actions { grid-column: 2; justify-self: start; }
  .segment { display: block; }
  .segment .speaker, .segment .text { margin-top: 6px; }
  .report-grid { grid-template-columns: 1fr; }
  .playback-bar {
    left: 0;
    min-height: 118px;
    gap: 6px;
    padding: 10px 14px 9px;
    background: #212428;
  }
  .playback-controls { gap: 8px; }
  .playback-round { width: 30px; height: 30px; font-size: 12px; }
  .playback-round.primary-play { width: 38px; height: 38px; }
  .playback-speed { min-width: 38px; font-size: 12px; }
  .playback-progress-row { grid-template-columns: 48px minmax(0, 1fr) 48px; gap: 8px; }
  .speaker-timeline { gap: 5px; }
  .timeline-lane { grid-template-columns: 72px minmax(0, 1fr) 38px; }
  .timeline-label, .timeline-share { font-size: 11px; }
  .timeline-track { height: 7px; }
  .floating-search { left: 14px; right: 14px; width: auto; transform: none; }
  .auth-legal { position: relative; inset: auto; margin-top: -8px; }
}
@media (max-width: 540px) {
  .toolbar { grid-template-columns: 1fr; }
  .toolbar button { grid-column: auto; }
  .playback-bar { padding-inline: 12px; }
  .timeline-lane { grid-template-columns: 68px minmax(0, 1fr) 34px; gap: 7px; }
}
"""


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def browser_login_page(
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    providers = []
    load_error = error
    if resolved_workspace_id is not None and db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail as exc:
            load_error = exc.code
    elif resolved_workspace_id is not None and db is None:
        load_error = "auth_dependency_unavailable"
    return HTMLResponse(
        render_login_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
        )
    )


@router.get("/sign-up", response_class=HTMLResponse, include_in_schema=False)
async def browser_signup_page(
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    mode: str | None = SignupModeQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    providers = []
    load_error = error
    if resolved_workspace_id is not None and db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail as exc:
            load_error = exc.code
    elif resolved_workspace_id is not None and db is None:
        load_error = "auth_dependency_unavailable"
    return HTMLResponse(
        render_signup_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
            mode=mode,
        )
    )


@router.post("/login/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_login_start(
    request: Request,
    email: str = LoginEmailForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_invalid",
            ),
            status_code=400,
        )
    workspace, user = await _resolve_email_login_user(
        db,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
    )
    if workspace is None or user is None:
        if workspace is not None:
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=workspace.id,
                outcome="failure",
                error_code="email_identity_not_found",
            )
            await db.commit()
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_start_unavailable",
            ),
            status_code=400,
        )
    code = _issue_email_login_code()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        code=code,
        ttl_seconds=ttl_seconds,
    )
    dev_code = code if _should_echo_email_code(request) else None
    if dev_code is None:
        try:
            await email_delivery.send_email_login_code(
                settings=request.app.state.settings,
                recipient_email=normalized_email,
                code=code,
                ttl_seconds=ttl_seconds,
            )
        except email_delivery.EmailLoginDeliveryError:
            state.result = "failed"
            state.used_at = datetime.now(UTC)
            state.error_code = "email_delivery_unavailable"
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=resolved_workspace_id,
                outcome="failure",
                error_code="email_delivery_unavailable",
            )
            await db.commit()
            return HTMLResponse(
                render_login_page(
                    workspace_id=resolved_workspace_id,
                    providers=[],
                    next_path=safe_next,
                    error="email_delivery_unavailable",
                ),
                status_code=503,
            )
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        outcome="success",
    )
    await db.commit()
    return HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            workspace_id=resolved_workspace_id,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
        )
    )


@router.post("/sign-up/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_signup_start(
    request: Request,
    email: str = LoginEmailForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_invalid",
            ),
            status_code=400,
        )
    workspace = await _resolve_email_workspace(db, workspace_id=resolved_workspace_id)
    if workspace is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_start_unavailable",
            ),
            status_code=400,
        )
    code = _issue_email_login_code()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        code=code,
        ttl_seconds=ttl_seconds,
        provider=EMAIL_SIGNUP_PROVIDER,
    )
    dev_code = code if _should_echo_email_code(request) else None
    if dev_code is None:
        try:
            await email_delivery.send_email_login_code(
                settings=request.app.state.settings,
                recipient_email=normalized_email,
                code=code,
                ttl_seconds=ttl_seconds,
            )
        except email_delivery.EmailLoginDeliveryError:
            state.result = "failed"
            state.used_at = datetime.now(UTC)
            state.error_code = "email_delivery_unavailable"
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=resolved_workspace_id,
                outcome="failure",
                error_code="email_delivery_unavailable",
                metadata={"flow": "registration"},
            )
            await db.commit()
            return HTMLResponse(
                render_signup_page(
                    workspace_id=resolved_workspace_id,
                    providers=[],
                    next_path=safe_next,
                    error="email_delivery_unavailable",
                ),
                status_code=503,
            )
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        outcome="success",
        metadata={"flow": "registration"},
    )
    await db.commit()
    return HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            workspace_id=resolved_workspace_id,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
            flow="signup",
        )
    )


@router.post("/login/email/verify", include_in_schema=False, response_model=None)
async def browser_email_login_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    normalized_email = _normalize_email(email)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if resolved_workspace_id is None or normalized_email is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                workspace_id=resolved_workspace_id,
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
            ),
            status_code=400,
        )
    result = await _consume_email_login_code(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
        code=code,
        state_nonce=state,
        next_path=safe_next,
    )
    if isinstance(result, HTMLResponse):
        return result
    redirect = RedirectResponse(safe_next, status_code=303)
    _set_browser_auth_cookie(redirect, token=result.token, expires_at=result.expires_at)
    return redirect


@router.post("/sign-up/email/verify", include_in_schema=False, response_model=None)
async def browser_email_signup_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    normalized_email = _normalize_email(email)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if resolved_workspace_id is None or normalized_email is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                workspace_id=resolved_workspace_id,
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
                flow="signup",
            ),
            status_code=400,
        )
    result = await _consume_email_login_code(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
        code=code,
        state_nonce=state,
        next_path=safe_next,
        provider=EMAIL_SIGNUP_PROVIDER,
        allow_registration=True,
    )
    if isinstance(result, HTMLResponse):
        return result
    redirect = RedirectResponse(safe_next, status_code=303)
    _set_browser_auth_cookie(redirect, token=result.token, expires_at=result.expires_at)
    return redirect


@router.get("/login/{provider}/start", include_in_schema=False, response_model=None)
async def browser_login_provider_start(
    provider: str,
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    _ = provider
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    providers = []
    if db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail:
            providers = []
    return HTMLResponse(
        render_login_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error="provider_future",
        ),
        status_code=501,
    )


@router.get("/meetings", response_class=HTMLResponse, include_in_schema=False)
async def meeting_list_page(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
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


@router.get("/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def meeting_detail_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
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


@router.get(
    "/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def meeting_deletion_report_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    report = await deletion_report_response(db, meeting=meeting)
    return HTMLResponse(render_deletion_report_page(meeting.title or "Deleted meeting", report))


@router.get("/desktop/meetings", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_list_page(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
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


@router.get("/desktop/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_detail_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
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


@router.get(
    "/desktop/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def embedded_meeting_deletion_report_page(
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    report = await deletion_report_response(db, meeting=meeting)
    return HTMLResponse(render_deletion_report_page(meeting.title or "Deleted meeting", report, embedded=True))


def _render_login_provider_actions(providers: list, *, next_path: str) -> str:
    if not providers:
        return '<span class="chip disabled">OAuth позже</span>'
    actions: list[str] = []
    for provider in providers:
        provider_id = str(getattr(provider, "provider", "") or "").strip()
        label = _login_provider_label(provider_id, str(getattr(provider, "label", "") or provider_id))
        mark = _login_provider_mark(provider_id, label)
        actions.append(
            f"""
            <span class="auth-provider" aria-disabled="true">
              <span class="provider-mark">{escape(mark)}</span>
              <span>{escape(label)}</span>
              <span class="provider-pill">скоро</span>
            </span>
            """
        )
    return "\n".join(actions)


def _login_provider_label(provider_id: str, fallback: str) -> str:
    labels = {
        "yandex": "Продолжить через Яндекс ID",
        "vk": "Продолжить через VK ID",
        "telegram": "Продолжить через Telegram",
    }
    return labels.get(provider_id, f"Продолжить через {fallback}")


def _login_provider_mark(provider_id: str, label: str) -> str:
    marks = {
        "yandex": "Я",
        "vk": "VK",
        "telegram": "TG",
    }
    return marks.get(provider_id, label[:2].upper())


def render_login_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    error_html = _render_login_error(error)
    if workspace_id is None:
        provider_html = """
          <div class="truth-copy">Кабинет входа не настроен. Проверьте серверные настройки.</div>
        """
    else:
        provider_html = _render_login_provider_actions(providers, next_path=safe_next)
    content = f"""
      <main class="auth-page">
        <section class="auth-panel" aria-label="Вход в кабинет">
          <div class="auth-brand-wordmark">2brain Rec</div>
          <div>
            <h1>Войти в кабинет</h1>
            <div class="auth-subtitle">Используйте корпоративный способ входа или получите одноразовый код на рабочую почту.</div>
          </div>
          {error_html}
          <div class="state-list">
            <div class="muted">Другие способы входа</div>
            <div class="auth-actions">{provider_html}</div>
          </div>
          <div class="auth-divider">или</div>
          <form class="auth-form" action="/login/email/start" method="post">
            <label>
              Рабочая почта
              <input name="email" type="email" placeholder="name@company.ru" autocomplete="email" required>
            </label>
            <input type="hidden" name="next" value="{escape(safe_next)}">
            <button class="primary" type="submit">Продолжить</button>
          </form>
          <div class="auth-secondary">
            <a class="mini-link" href="/login/sso/start?{urlencode({"next": safe_next})}" aria-disabled="true">Войти через SSO</a>
            <div class="auth-signup">Нет аккаунта? <a href="/sign-up?{urlencode({"next": safe_next})}">Зарегистрироваться</a></div>
          </div>
        </section>
        <p class="auth-legal">Продолжая, вы соглашаетесь с <a href="#" aria-disabled="true">Условиями использования</a> и <a href="#" aria-disabled="true">Политикой конфиденциальности</a>. Аудио и транскрипты не показываются до успешного входа.</p>
      </main>
    """
    return _standalone_page("Вход", content)


def render_signup_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
    mode: str | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    email_mode = str(mode or "").lower() == "email"
    error_html = _render_login_error(error)
    if workspace_id is None:
        provider_html = """
          <div class="truth-copy">Кабинет регистрации не настроен. Проверьте серверные настройки.</div>
        """
    else:
        provider_html = _render_login_provider_actions(providers, next_path=safe_next)
    if email_mode:
        registration_body = f"""
          <a class="email-mode-trigger" href="/sign-up?{urlencode({"next": safe_next})}">Продолжить другим способом</a>
          <div class="auth-divider">или</div>
          <form class="auth-form signup-email-form" action="/sign-up/email/start" method="post">
            <label>
              Рабочая почта
              <input name="email" type="email" placeholder="name@company.ru" autocomplete="email" required>
            </label>
            <input type="hidden" name="next" value="{escape(safe_next)}">
            <button class="primary" type="submit">Зарегистрироваться</button>
          </form>
        """
    else:
        registration_body = f"""
          <div class="auth-actions">{provider_html}</div>
          <a class="mini-link auth-help" href="#" aria-disabled="true">Зачем 2brain Rec доступ к календарю?</a>
          <div class="auth-divider">или</div>
          <a class="email-mode-trigger" href="/sign-up?{urlencode({"next": safe_next, "mode": "email"})}">
            <span class="provider-mark">@</span><span>Продолжить с email</span>
          </a>
        """
    content = f"""
      <main class="auth-page">
        <section class="auth-panel" aria-label="Регистрация">
          <div class="auth-brand-wordmark">2brain Rec</div>
          <div>
            <h1>Зарегистрируйтесь бесплатно</h1>
          </div>
          {error_html}
          <div class="email-mode">{registration_body}</div>
          <div class="auth-secondary">
            <div class="auth-signup">Уже есть аккаунт? <a href="/login?{urlencode({"next": safe_next})}">Войти</a></div>
          </div>
        </section>
        <p class="auth-legal">Продолжая, вы соглашаетесь с <a href="#" aria-disabled="true">Условиями использования</a> и <a href="#" aria-disabled="true">Политикой конфиденциальности</a>. Код подтверждения отправляется только на указанную почту.</p>
      </main>
    """
    return _standalone_page("Регистрация", content)


def render_email_code_page(
    *,
    email: str,
    workspace_id: UUID | None,
    state_nonce: str,
    next_path: str,
    dev_code: str | None = None,
    error: str | None = None,
    flow: str = "login",
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    verify_path = "/sign-up/email/verify" if flow == "signup" else "/login/email/verify"
    resend_path = "/sign-up/email/start" if flow == "signup" else "/login/email/start"
    back_path = "/sign-up" if flow == "signup" else "/login"
    page_title = "Подтвердите почту" if flow == "signup" else "Подтвердите вход"
    subtitle = (
        f"Проверьте {escape(email)}: мы отправили 6-значный код для создания аккаунта."
        if flow == "signup"
        else f"Проверьте {escape(email)}: мы отправили 6-значный код для входа."
    )
    dev_code_html = ""
    if dev_code is not None:
        dev_code_html = f"""
          <div class="delete-confirmation">
            <strong>Dev code</strong>
            <div class="truth-copy">Код для локальной проверки: <strong>{escape(dev_code)}</strong></div>
          </div>
        """
    content = f"""
      <main class="auth-page">
        <section class="auth-panel" aria-label="Код входа">
          <div class="auth-brand-wordmark">2brain Rec</div>
          <div>
            <h1>{page_title}</h1>
            <div class="auth-subtitle">{subtitle}</div>
          </div>
          <div class="code-hint">Проверьте почту и введите код ниже.</div>
          {_render_login_error(error)}
          {dev_code_html}
          <form class="auth-form" action="{verify_path}" method="post" data-code-form>
            <div class="code-grid" role="group" aria-label="6-значный код">
              {_render_code_slots()}
            </div>
            <input data-code-hidden name="code" type="hidden" autocomplete="one-time-code">
            <input type="hidden" name="email" value="{escape(email)}">
            <input type="hidden" name="state" value="{escape(state_nonce)}">
            <input type="hidden" name="next" value="{escape(safe_next)}">
            <button class="primary" type="submit">Продолжить</button>
          </form>
          <form class="auth-form" action="{resend_path}" method="post">
            <input type="hidden" name="email" value="{escape(email)}">
            <input type="hidden" name="next" value="{escape(safe_next)}">
            <button class="auth-resend" type="submit">Отправить код еще раз</button>
          </form>
          <div class="auth-secondary">
            <a class="mini-link" href="{back_path}?{urlencode({"next": safe_next})}">Изменить почту</a>
          </div>
        </section>
        <p class="auth-legal">Код действует ограниченное время. Не пересылайте его другим людям.</p>
        {_render_code_entry_script()}
      </main>
    """
    return _standalone_page("Код входа", content)


def _render_code_slots() -> str:
    return "\n".join(
        f'<input class="code-slot" inputmode="numeric" pattern="[0-9]*" maxlength="1" aria-label="Цифра {index}" data-code-slot>'
        for index in range(1, 7)
    )


def _render_code_entry_script() -> str:
    return """
        <script>
        (() => {
          const form = document.querySelector("[data-code-form]");
          if (!form) return;
          const slots = Array.from(form.querySelectorAll("[data-code-slot]"));
          const hidden = form.querySelector("[data-code-hidden]");
          const sync = () => { hidden.value = slots.map((slot) => slot.value).join(""); };
          slots.forEach((slot, index) => {
            slot.addEventListener("input", () => {
              slot.value = slot.value.replace(/\\D/g, "").slice(0, 1);
              sync();
              if (slot.value && slots[index + 1]) slots[index + 1].focus();
            });
            slot.addEventListener("keydown", (event) => {
              if (event.key === "Backspace" && !slot.value && slots[index - 1]) {
                slots[index - 1].focus();
              }
            });
            slot.addEventListener("paste", (event) => {
              const text = (event.clipboardData || window.clipboardData).getData("text").replace(/\\D/g, "").slice(0, 6);
              if (!text) return;
              event.preventDefault();
              slots.forEach((target, offset) => { target.value = text[offset] || ""; });
              sync();
              const next = slots[Math.min(text.length, slots.length) - 1];
              if (next) next.focus();
            });
          });
          form.addEventListener("submit", sync);
          slots[0]?.focus();
        })();
        </script>
    """


def _render_auth_transition_script() -> str:
    return """
        <script>
        (() => {
          const page = document.querySelector(".auth-page");
          if (!page || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
          page.addEventListener("click", (event) => {
            const link = event.target.closest("a[href]");
            if (!link) return;
            if (link.getAttribute("aria-disabled") === "true") return;
            if (link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            const url = new URL(link.href, window.location.href);
            if (url.origin !== window.location.origin) return;
            event.preventDefault();
            document.body.classList.add("auth-leaving");
            window.setTimeout(() => { window.location.href = url.href; }, 130);
          });
        })();
        </script>
    """


def render_meeting_list_page(response: MeetingListResponse, *, embedded: bool = False) -> str:
    rows = "\n".join(
        _render_meeting_row(item, embedded=embedded)
        for item in response.items
    )
    if not rows:
        rows = '<div class="empty-state">Нет встреч для выбранного фильтра.</div>'
    new_control = '<button class="new-button" type="button" aria-disabled="true">Новая</button>'
    content = f"""
      <main class="cabinet-main">
        <div class="cabinet-workspace">
          <div class="cabinet-topbar">
            <div class="cabinet-titleline"><strong>Мои встречи</strong><span>{escape(_sort_label(response.filters.sort))}</span></div>
            <div class="toolbar-icons">
              <button class="icon-control" type="button" aria-label="Сохраненные" aria-disabled="true">□</button>
              <button class="icon-control" type="button" aria-label="Фильтры" aria-disabled="true">≡</button>
              <button class="icon-control" type="button" aria-label="Сортировка" aria-disabled="true">↕</button>
              {new_control}
            </div>
          </div>
          <section class="upcoming cabinet-card" aria-label="Ближайшие встречи">
            <div class="section-title">Ближайшие</div>
            <div class="calendar-day">
              <div class="date-badge">Сегодня<br>17</div>
              <div class="calendar-events">
                <div class="calendar-event"><strong>Командный синк</strong><div class="muted">11:30 - 13:00</div></div>
                <div class="calendar-event"><strong>Ревью релиза</strong><div class="muted">12:00 - 13:00</div></div>
              </div>
            </div>
            <div class="calendar-day">
              <div class="date-badge">19<br>июн</div>
              <div class="calendar-events">
                <div class="calendar-event"><strong>Планирование запуска</strong><div class="muted">15:00 - 16:00</div></div>
              </div>
            </div>
          </section>
          <div class="meeting-toolbar">
            <div class="section-title" data-list-title>Записи встреч</div>
            <div class="selection-toolbar" data-selection-toolbar hidden data-visible-total="{len(response.items)}">
              <button class="selection-toggle" type="button" data-clear-selection aria-label="Снять выбор">{_ui_icon("minus")}</button>
              <div class="selection-count" data-selection-count>Выбрано 0 / {len(response.items)}</div>
              <div class="selection-actions">
                <span class="tooltip-wrap" tabindex="0" data-tooltip="Скачивание появится позже" aria-label="Скачивание появится позже">
                  <button class="icon-control is-disabled" type="button" disabled aria-disabled="true" data-download-disabled aria-label="Скачать выбранные записи">{_ui_icon("download")}</button>
                </span>
                <span class="selection-divider" aria-hidden="true"></span>
                <button class="icon-control danger-button" type="button" aria-label="Удалить выбранные записи" data-selection-delete>{_ui_icon("trash")}</button>
              </div>
            </div>
            <div class="toolbar-icons">
              <button class="icon-control" type="button" aria-label="Сохранить" aria-disabled="true">□</button>
              <button class="icon-control" type="button" aria-label="Фильтры" aria-disabled="true">≡</button>
              <button class="icon-control" type="button" aria-label="Сортировка" aria-disabled="true">↕</button>
              <button class="new-button" type="button" aria-disabled="true">Новая</button>
            </div>
          </div>
          <section class="list-card cabinet-card" aria-label="Записи встреч" data-meeting-list>
            {rows}
          </section>
          {_render_list_delete_dialog()}
        </div>
        <div class="floating-search">Спросите что-нибудь...</div>
      </main>
      {_meeting_list_script()}
    """
    return _page_shell("Мои встречи", content, embedded=embedded)


def _meeting_list_script() -> str:
    script = """
      <script>
      (() => {
        const list = document.querySelector("[data-meeting-list]");
        const toolbar = document.querySelector("[data-selection-toolbar]");
        const listTitle = document.querySelector("[data-list-title]");
        const countLabel = document.querySelector("[data-selection-count]");
        const deleteSelected = document.querySelector("[data-selection-delete]");
        const clearSelection = document.querySelector("[data-clear-selection]");
        const dialog = document.querySelector("[data-delete-dialog]");
        if (!list || !toolbar || !countLabel || !deleteSelected || !dialog) return;

        const title = dialog.querySelector("[data-delete-title]");
        const count = dialog.querySelector("[data-delete-count]");
        const cancel = dialog.querySelector("[data-delete-cancel]");
        const confirm = dialog.querySelector("[data-delete-confirm]");
        const error = dialog.querySelector("[data-delete-error]");
        let pendingRows = [];

        const selectedRows = () => Array.from(list.querySelectorAll("[data-meeting-row]"))
          .filter((row) => row.querySelector("[data-meeting-select]")?.checked);

        const plural = (value, one, few, many) => {
          const mod10 = value % 10;
          const mod100 = value % 100;
          if (mod10 === 1 && mod100 !== 11) return one;
          if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
          return many;
        };

        const deletingLabel = (value) => `Вы удаляете ${value} ${plural(value, "запись", "записи", "записей")}.`;
        const totalRows = () => list.querySelectorAll("[data-meeting-row]").length;

        const updateSelection = () => {
          const rows = selectedRows();
          countLabel.textContent = `Выбрано ${rows.length} / ${totalRows()}`;
          toolbar.hidden = rows.length === 0;
          if (listTitle) listTitle.hidden = rows.length > 0;
          list.querySelectorAll("[data-meeting-row]").forEach((row) => {
            row.classList.toggle("is-selected", row.querySelector("[data-meeting-select]")?.checked === true);
          });
        };

        const openDeleteDialog = (rows) => {
          pendingRows = rows.filter(Boolean);
          if (!pendingRows.length) return;
          if (error) error.hidden = true;
          if (title) title.textContent = pendingRows.length === 1 ? dialog.dataset.titleOne : dialog.dataset.titleMany;
          if (count) count.textContent = deletingLabel(pendingRows.length);
          if (typeof dialog.showModal === "function") {
            dialog.showModal();
          } else {
            dialog.setAttribute("open", "");
          }
        };

        const closeDeleteDialog = () => {
          pendingRows = [];
          if (typeof dialog.close === "function") {
            dialog.close();
          } else {
            dialog.removeAttribute("open");
          }
        };

        const showEmptyStateIfNeeded = () => {
          if (!list.querySelector("[data-meeting-row]")) {
            list.innerHTML = '<div class="empty-state">Записей больше нет.</div>';
          }
        };

        list.addEventListener("change", (event) => {
          if (event.target.closest("[data-meeting-select]")) updateSelection();
        });

        list.addEventListener("click", (event) => {
          const deleteButton = event.target.closest("[data-row-delete]");
          if (deleteButton) {
            openDeleteDialog([deleteButton.closest("[data-meeting-row]")]);
            return;
          }
          const row = event.target.closest("[data-meeting-row]");
          if (!row || event.target.closest("a,button,input")) return;
          const checkbox = row.querySelector("[data-meeting-select]");
          if (!checkbox) return;
          checkbox.checked = !checkbox.checked;
          updateSelection();
        });

        deleteSelected.addEventListener("click", () => openDeleteDialog(selectedRows()));
        cancel?.addEventListener("click", closeDeleteDialog);
        clearSelection?.addEventListener("click", () => {
          selectedRows().forEach((row) => {
            row.querySelector("[data-meeting-select]").checked = false;
          });
          updateSelection();
        });

        confirm?.addEventListener("click", async () => {
          if (!pendingRows.length) return;
          confirm.disabled = true;
          confirm.textContent = "Удаляем...";
          let failures = 0;
          for (const row of pendingRows) {
            const meetingId = row.dataset.meetingId;
            try {
              const response = await fetch(`/api/v1/cabinet/meetings/${meetingId}/deletion-requests`, {
                method: "POST",
                credentials: "same-origin",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({confirmation_boundary: "__BOUNDARY__"})
              });
              if (!response.ok) {
                failures += 1;
                row.querySelector("[data-meeting-select]").checked = false;
              } else {
                row.remove();
              }
            } catch (_err) {
              failures += 1;
            }
          }
          confirm.disabled = false;
          confirm.textContent = "Удалить";
          updateSelection();
          showEmptyStateIfNeeded();
          if (failures && error) {
            error.textContent = failures === 1 ? "Не удалось удалить одну запись. Попробуйте еще раз." : `Не удалось удалить ${failures} ${plural(failures, "запись", "записи", "записей")}. Попробуйте еще раз.`;
            error.hidden = false;
            pendingRows = [];
            return;
          }
          closeDeleteDialog();
        });

        updateSelection();
      })();
      </script>
    """
    return script.replace("__BOUNDARY__", BOUNDED_DELETE_COPY)


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
    recording_tab = "Расшифровка" if embedded else "Запись и расшифровка"
    speaker_lanes = _render_speaker_lanes(review)
    media_revision_id = escape(str(review.provenance.media_revision_id or ""))
    local_media_revision_id = escape(review.provenance.local_media_revision_id or "")
    content = f"""
      <main class="main detail-page-main" data-media-revision-id="{media_revision_id}" data-local-media-revision-id="{local_media_revision_id}">
        <div class="topline">
          <div class="crumbs"><a href="{_base_path(embedded)}">Мои встречи</a><span>/</span><strong>{escape(review.meeting.title)}</strong><span>{escape(_ui_text(review.meeting.status_label))}</span>{_render_access_chip(review.meeting.access)}</div>
          <div class="action-row">{_render_top_actions(review, embedded=embedded)}</div>
        </div>
        <div class="tabs" role="tablist" aria-label="Содержимое встречи">
          <button type="button" class="tab" role="tab" id="detail-tab-outcomes" aria-selected="false" aria-controls="detail-panel-outcomes" data-detail-tab="outcomes">Итоги</button>
          <button type="button" class="tab active" role="tab" id="detail-tab-recording" aria-selected="true" aria-controls="detail-panel-recording" data-detail-tab="recording">{recording_tab}</button>
        </div>
        <div class="detail-layout">
          <section class="detail-main">
            <section class="tab-panel" role="tabpanel" id="detail-panel-outcomes" aria-labelledby="detail-tab-outcomes" data-detail-panel="outcomes" hidden>
              {_render_notes_outcomes(review)}
            </section>
            <section class="tab-panel active" role="tabpanel" id="detail-panel-recording" aria-labelledby="detail-tab-recording" data-detail-panel="recording">
              <div class="transcript">{transcript}</div>
            </section>
          </section>
          <aside class="right-panel">
            {_render_revision_status(review)}
            <h3>Доступ</h3>
            {_render_access_summary(review)}
            <h3>Поделиться</h3>
            {_render_share_panel(review)}
            <h3>Файлы</h3>
            {_render_artifacts(review)}
            <div class="truth-copy" data-boundary-copy="{escape(review.deletion_truth_copy or "")}">{escape(_ui_text(review.deletion_truth_copy or ""))}</div>
            <h3>Удаление</h3>
            {_render_delete_confirmation(review, embedded=embedded)}
            <h3>Спикеры</h3>
            {speaker_lanes}
            <h3>Управление</h3>
            <div class="governance">{_render_governance(review)}</div>
            <h3>Активность</h3>
            {_render_activity(review)}
            <h3>Ассистент</h3>
            <button type="button" disabled>{escape(_ui_text(review.assistant.label))}</button>
            <h3>Шаблон</h3>
            <button type="button" disabled>{escape(_ui_text(review.template.label))}</button>
          </aside>
        </div>
        {_detail_tabs_script()}
        {_render_playback(review)}
      </main>
    """
    return _page_shell(review.meeting.title, content, embedded=embedded)


def _detail_tabs_script() -> str:
    return """
      <script>
        (() => {
          const tabs = Array.from(document.querySelectorAll("[data-detail-tab]"));
          const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
          if (!tabs.length || !panels.length) return;
          const activate = (name) => {
            tabs.forEach((tab) => {
              const selected = tab.dataset.detailTab === name;
              tab.classList.toggle("active", selected);
              tab.setAttribute("aria-selected", selected ? "true" : "false");
            });
            panels.forEach((panel) => {
              const selected = panel.dataset.detailPanel === name;
              panel.classList.toggle("active", selected);
              panel.hidden = !selected;
            });
          };
          tabs.forEach((tab) => {
            tab.addEventListener("click", () => activate(tab.dataset.detailTab || "recording"));
          });
          if (window.location.hash === "#outcomes") activate("outcomes");
        })();
      </script>
    """


def render_deletion_report_page(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool = False,
) -> str:
    content = f"""
      <main class="main">
        <div class="topline">
          <div class="crumbs"><a href="{_base_path(embedded)}">Мои встречи</a><span>/</span><strong>{escape(meeting_title)}</strong><span>Отчет удаления</span></div>
          <div class="action-row"><a class="button" href="{_base_path(embedded)}">Назад</a></div>
        </div>
        <section class="report-layout" aria-label="Отчет удаления">
          <div class="report-band">
            <h3>Жизненный цикл</h3>
            <div class="state-row"><strong>{escape(_ui_text(report.overall_state.value))}</strong><span class="chip deleted_future">только метаданные</span></div>
            <div class="truth-copy" data-boundary-copy="{escape(report.bounded_copy)}">{escape(_ui_text(report.bounded_copy))}</div>
          </div>
          <div class="report-grid">
            {_render_report_band("Файлы под контролем 2brain Rec", report.artifact_states)}
            {_render_report_band("Резервные копии", [report.backup])}
            {_render_report_band("Внешние зависимости", report.dependencies)}
            {_render_report_band("Ограничения после выгрузки", report.post_egress_limits)}
          </div>
          <div class="report-band">
            <h3>Очистка на устройстве</h3>
            {_render_local_purge_tasks(report.local_purge)}
          </div>
          <div class="report-band">
            <h3>События удаления</h3>
            {_render_lifecycle_activity(report.activity)}
          </div>
        </section>
      </main>
    """
    return _page_shell("Отчет удаления", content, embedded=embedded)


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


def _standalone_page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - 2brain Rec</title>
  <style>{CSS}</style>
</head>
<body>
  {content}
  {_render_auth_transition_script()}
</body>
</html>"""


async def _load_browser_login_providers(db: AsyncSession, workspace_id: UUID) -> list:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    snapshot = await read_auth_providers(db, workspace_id, adapters=build_provider_registry())
    return list(snapshot.providers)


async def _record_email_login_audit(
    db: AsyncSession,
    *,
    request: Request,
    workspace_id: UUID,
    outcome: str = "success",
    user_id: UUID | None = None,
    error_code: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    audit_metadata = {"flow": "email_login"}
    if metadata:
        audit_metadata.update(metadata)
    if error_code is not None:
        audit_metadata["error_code"] = error_code
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type="email_auth_started" if user_id is None else "email_auth_completed",
        provider="email",
        outcome=outcome,
        actor_ip=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
        user_id=user_id,
        actor_user_id=user_id,
        metadata=audit_metadata,
    )


async def _create_email_login_state(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    next_path: str,
    code: str,
    ttl_seconds: int,
    provider: str = EMAIL_LOGIN_PROVIDER,
) -> AuthCallbackState:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    state = AuthCallbackState(
        provider=provider,
        state_nonce=secrets.token_urlsafe(24),
        workspace_id=workspace_id,
        requested_redirect=_safe_browser_next_path(next_path),
        expected_state=hash_token(_normalize_email_code(code)),
        expires_at=callback_expiry(ttl_seconds=ttl_seconds),
        result="pending",
    )
    db.add(state)
    await db.flush()
    await db.refresh(state)
    return state


async def _consume_email_login_code(
    db: AsyncSession,
    *,
    request: Request,
    workspace_id: UUID | None,
    email: str,
    code: str,
    state_nonce: str,
    next_path: str,
    provider: str = EMAIL_LOGIN_PROVIDER,
    allow_registration: bool = False,
):
    now = datetime.now(UTC)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state_nonce))
    state = await db.scalar(
        select(AuthCallbackState).where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state_nonce,
        )
    )
    flow = "signup" if allow_registration else "login"
    if state is None:
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    if workspace_id is not None and state.workspace_id != workspace_id:
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    workspace_id = state.workspace_id
    if state.result != "pending":
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    expires_at = state.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        state.result = "expired"
        state.used_at = now
        state.error_code = "email_code_expired"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_expired",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_expired",
            flow=flow,
        )
    if state.expected_state != hash_token(_normalize_email_code(code)):
        state.error_code = "email_code_invalid"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_invalid",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    workspace, user = await _resolve_email_login_user(db, workspace_id=workspace_id, email=email)
    if workspace is not None and user is None and allow_registration:
        user = await _ensure_email_registration_user(
            db,
            workspace=workspace,
            email=email,
            now=now,
        )
    if workspace is None or user is None:
        state.result = "failed"
        state.used_at = now
        state.error_code = "email_identity_not_found"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_invalid",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    device = await _resolve_email_browser_device(db, workspace=workspace, user=user, now=now)
    issued = await issue_auth_session(
        db,
        user_id=user.id,
        workspace_id=workspace.id,
        device_id=device.id,
        provider="email",
        ttl_seconds=request.app.state.settings.auth_session_ttl_seconds,
        claims_fingerprint=hash_token(f"email:{email}:{workspace.id}"),
        now=now,
    )
    db.add(
        AuthSessionDeviceBinding(
            auth_session_id=issued.id,
            registered_device_id=device.id,
            device_state="trusted",
            last_heartbeat_at=now,
        )
    )
    state.result = "completed"
    state.used_at = now
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=workspace.id,
        outcome="success",
        user_id=user.id,
        metadata={"flow": "registration"} if allow_registration else None,
    )
    await db.commit()
    return issued


async def _resolve_email_login_user(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    email: str,
) -> tuple[Workspace | None, UserIdentity | None]:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        return None, None
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            context_kind="auth_bootstrap",
        ),
    )
    candidates = (
        await db.execute(
            select(ExternalIdentity, UserIdentity)
            .join(UserIdentity, UserIdentity.id == ExternalIdentity.user_id)
            .where(
                UserIdentity.organization_id == workspace.organization_id,
                UserIdentity.status == "active",
                func.lower(ExternalIdentity.email) == email,
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    ).all()
    for identity, user in candidates:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace.id,
                organization_id=workspace.organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == identity.user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is not None:
            return workspace, user
    return workspace, None


async def _resolve_email_workspace(db: AsyncSession, *, workspace_id: UUID) -> Workspace | None:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    return await db.get(Workspace, workspace_id)


async def _ensure_email_registration_user(
    db: AsyncSession,
    *,
    workspace: Workspace,
    email: str,
    now: datetime,
) -> UserIdentity:
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            context_kind="auth_bootstrap",
        ),
    )
    existing = (
        await db.execute(
            select(ExternalIdentity, UserIdentity)
            .join(UserIdentity, UserIdentity.id == ExternalIdentity.user_id)
            .where(
                UserIdentity.organization_id == workspace.organization_id,
                UserIdentity.status == "active",
                func.lower(ExternalIdentity.email) == email,
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    ).first()
    if existing is not None:
        identity, user = existing
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace.id,
                organization_id=workspace.organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == identity.user_id,
            )
        )
        if membership is None:
            db.add(
                WorkspaceMembership(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="member",
                    status="active",
                )
            )
            await db.flush()
        else:
            membership.status = "active"
        identity.is_verified = True
        identity.last_seen_at = now
        return user

    display_name = email.partition("@")[0].replace(".", " ").replace("_", " ").title() or email
    user = UserIdentity(
        organization_id=workspace.organization_id,
        external_subject=f"email:{email}",
        display_name=display_name,
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            user_id=user.id,
            context_kind="auth_bootstrap",
        ),
    )
    db.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            role="member",
            status="active",
        )
    )
    db.add(
        ExternalIdentity(
            user_id=user.id,
            provider=EMAIL_LOGIN_PROVIDER,
            provider_subject=email,
            provider_username=email,
            email=email,
            display_name=display_name,
            is_verified=True,
            subject_issued_at=now,
            last_seen_at=now,
            meta={"flow": "browser_registration"},
        )
    )
    await db.flush()
    return user


async def _resolve_email_browser_device(
    db: AsyncSession,
    *,
    workspace: Workspace,
    user: UserIdentity,
    now: datetime,
) -> RegisteredDevice:
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=workspace.organization_id,
            workspace_id=workspace.id,
            user_id=user.id,
        ),
    )
    device_public_id = f"browser-email:{user.id}"
    device = await db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.workspace_id == workspace.id,
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.device_public_id == device_public_id,
        )
    )
    if device is None:
        device = RegisteredDevice(
            workspace_id=workspace.id,
            user_id=user.id,
            device_public_id=device_public_id,
            platform="web",
            client_version="email-login",
            status="active",
            registration_state="approved",
            trusted_by=user.id,
            last_seen_at=now,
        )
        db.add(device)
        await db.flush()
        await db.refresh(device)
        return device
    device.platform = "web"
    device.client_version = "email-login"
    device.status = "active"
    device.registration_state = "approved"
    device.last_seen_at = now
    return device


def _email_code_error_response(
    *,
    email: str,
    workspace_id: UUID | None,
    state_nonce: str,
    next_path: str,
    error: str,
    flow: str = "login",
) -> HTMLResponse:
    return HTMLResponse(
        render_email_code_page(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error=error,
            flow=flow,
        ),
        status_code=400,
    )


def _set_browser_auth_cookie(response, *, token: str, expires_at: datetime) -> None:
    token_expires_at = expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=UTC)
    max_age = max(0, int((token_expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=AUTH_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _normalize_email(value: str) -> str | None:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized or len(normalized) > 240:
        return None
    local, _, domain = normalized.partition("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        return None
    return normalized


def _issue_email_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_email_code(value: str) -> str:
    return "".join(char for char in value.strip() if char.isdigit())


def _should_echo_email_code(request: Request) -> bool:
    return request.app.state.settings.env.lower() != "production"


def _resolve_browser_login_workspace_id(request: Request, workspace_id: UUID | None) -> UUID | None:
    if workspace_id is not None:
        return workspace_id
    settings = request.app.state.settings
    configured = getattr(settings, "web_login_workspace_id", None)
    if configured is not None:
        return configured
    return None


def _safe_browser_next_path(value: str | None) -> str:
    if value is None:
        return "/meetings"
    stripped = value.strip()
    if not stripped or not stripped.startswith("/") or stripped.startswith("//"):
        return "/meetings"
    if any(char in stripped for char in "\r\n"):
        return "/meetings"
    return stripped


def _render_login_error(error: str | None) -> str:
    if not error:
        return ""
    messages = {
        "missing_auth_context": "Нужен вход, чтобы открыть кабинет встреч.",
        "auth_session_invalid": "Сессия не найдена. Войдите снова.",
        "auth_session_expired": "Сессия истекла. Войдите снова.",
        "device_revoked": "Доступ этого устройства отозван. Войдите с доверенного браузера.",
        "workspace_required": "Нужен workspace id для входа в self-hosted кабинет.",
        "provider_missing": "Этот способ входа не настроен.",
        "provider_disabled": "Этот способ входа выключен политикой кабинета.",
        "provider_future": "Этот способ входа появится позже. Сейчас используйте вход по email.",
        "auth_dependency_unavailable": "Сервис входа временно недоступен.",
        "email_invalid": "Введите корректный email.",
        "email_start_unavailable": "Не удалось отправить код для этого кабинета. Проверьте workspace id и email.",
        "email_delivery_unavailable": "Почтовая доставка временно недоступна. Попробуйте запросить код еще раз.",
        "email_code_invalid": "Код не подошел. Проверьте письмо и попробуйте еще раз.",
        "email_code_expired": "Код истек. Запросите новый код.",
    }
    message = messages.get(error, "Не удалось открыть сессию кабинета. Попробуйте войти снова.")
    return f'<div class="delete-confirmation"><strong>{escape(message)}</strong></div>'
def _sidebar() -> str:
    return """
    <aside class="sidebar">
      <div class="workspace"><div class="avatar">2</div><div><div class="workspace-title">Личный</div><div class="workspace-subtitle">Бесплатный план</div></div></div>
      <button class="primary" type="button" disabled>Пригласить</button>
      <nav class="nav" aria-label="Кабинет">
        <a href="#" aria-disabled="true">⌕ Поиск</a>
        <a href="/meetings" class="active">▤ Мои встречи</a>
        <a href="#" aria-disabled="true">♢ Общие</a>
        <a href="#" aria-disabled="true">○ Действия <span class="nav-count">6</span></a>
        <a href="#" aria-disabled="true">⌁ Активность</a>
        <a href="#" aria-disabled="true">⚙ Настройки</a>
      </nav>
      <div class="sidebar-foot"><div class="trial">Пробный период 7 дней</div><div class="muted">2brain Rec</div></div>
    </aside>
    """


UI_TEXT: dict[str, str] = {
    "Access": "Доступ",
    "Access state is unavailable.": "Статус доступа недоступен.",
    "Action Items": "Действия",
    "Assistant": "Ассистент",
    "Available": "Доступно",
    "Can view": "Может смотреть",
    "Blocked": "Заблокировано",
    "Copy link": "Ссылка",
    "Decisions": "Решения",
    "Delete planned": "Удаление запланировано",
    "Delete this meeting everywhere 2brain Rec controls": "Удалить встречу в системах 2brain Rec",
    "Delete this meeting everywhere 2brain Rec controls.": "Удалить встречу везде, где ее контролирует 2brain Rec.",
    "Disabled": "Выключено",
    "Disabled by policy": "Заблокировано",
    "Download": "Скачать",
    "Evidence": "Фрагменты",
    "Export": "Экспорт",
    "Export package": "Экспорт",
    "Export ready": "Экспорт готов",
    "Failed": "Сбой",
    "Files already downloaded or exported are outside 2brain Rec deletion control.": "Уже скачанные или экспортированные файлы находятся вне последующего удаления в 2brain Rec.",
    "Files already downloaded or exported are outside later 2brain Rec revocation. Deleting a meeting can remove what 2brain Rec controls, not copies already saved elsewhere.": "Уже скачанные или экспортированные файлы находятся вне последующего отзыва в 2brain Rec. Удаление встречи может убрать то, что контролирует 2brain Rec, но не копии, уже сохраненные где-то еще.",
    "Follow-ups": "Продолжение",
    "Incoming system": "Входящий звук",
    "Key points": "Ключевое",
    "Local only": "Только локально",
    "Local microphone": "Микрофон",
    "Meeting processing needs operator review before outcomes can be trusted.": "Обработку встречи нужно проверить оператору, прежде чем доверять итогам.",
    "More": "Еще",
    "No access activity yet.": "Событий доступа пока нет.",
    "No active user grants.": "Активных доступов для пользователей нет.",
    "No exportable artifacts yet.": "Файлы для выгрузки пока недоступны.",
    "No lifecycle activity yet.": "Событий жизненного цикла пока нет.",
    "No lifecycle rows yet.": "Строк жизненного цикла пока нет.",
    "No local purge acknowledgement has been received yet.": "Подтверждение локальной очистки еще не получено.",
    "Not available": "Недоступно",
    "Notes": "Итоги",
    "On": "Вкл",
    "Off": "Выкл",
    "Open in browser": "Открыть в браузере",
    "Outcome deferred": "Итоги отложены",
    "Outcome source": "Источник итогов",
    "Outcomes blocked": "Итоги заблокированы",
    "Outcomes deferred": "Итоги отложены",
    "Outcomes processing": "Итоги готовятся",
    "Outcomes unavailable": "Итоги недоступны",
    "Owner": "Владелец",
    "owner": "владелец",
    "Partial": "Частично готово",
    "Processing": "Расшифровка",
    "Processing result could not be imported safely.": "Результат обработки не удалось безопасно импортировать.",
    "Public links": "Публичные ссылки",
    "Questions": "Вопросы",
    "Ready": "Готово",
    "Report": "Отчет",
    "Request deletion": "Запросить удаление",
    "Retention policy planned": "Правила хранения",
    "Retention controls will show policy truth before activation.": "Правила хранения появятся после активации политики.",
    "Risks": "Риски",
    "Share": "Поделиться",
    "Sharing is unavailable for this meeting.": "Поделиться этой встречей сейчас нельзя.",
    "Speaker lanes are reserved until diarization is available.": "Спикеры появятся после диаризации.",
    "Star": "Избранное",
    "Submitted": "Загружено",
    "Summary": "Кратко",
    "Summary unavailable": "Краткое резюме недоступно",
    "Tag": "Тег",
    "Team": "Команда",
    "Team visibility": "Видимость для команды",
    "Template": "Шаблон",
    "Transcript": "Расшифровка",
    "Transcript and generated outcomes may still be processing.": "Расшифровка и итоги еще могут обрабатываться.",
    "Transcript is still processing.": "Расшифровка еще готовится.",
    "Transcript review is available, but generated meeting outcomes are not part of this stored result.": "Расшифровка доступна, но сгенерированные итоги не входят в этот сохраненный результат.",
    "Uploading": "Загружается",
    "Unavailable": "Недоступно",
    "You own this meeting.": "Это ваша встреча.",
    "accepted": "принято",
    "acknowledged": "подтверждено",
    "active": "активен",
    "artifact lifecycle state": "состояние файла",
    "auth required": "нужен вход",
    "auth_required": "нужен вход",
    "allowed": "разрешено",
    "available": "доступно",
    "backup expiry pending": "ожидает срока хранения резервной копии",
    "backup_expiry_pending": "ожидает срока хранения резервной копии",
    "completed": "готово",
    "delete requested": "удаление запрошено",
    "delete_requested": "удаление запрошено",
    "deletion requested": "удаление запрошено",
    "deletion_requested": "удаление запрошено",
    "Desktop device": "Десктоп",
    "dependency unconfirmed": "зависимость не подтверждена",
    "dependency_unconfirmed": "зависимость не подтверждена",
    "disabled": "выключено",
    "disabled by default": "выключено по умолчанию",
    "disabled_by_default": "выключено по умолчанию",
    "download completed": "скачивание завершено",
    "download requested": "скачивание запрошено",
    "enabled": "включено",
    "external deletion support is not confirmed": "удаление во внешнем сервисе не подтверждено",
    "External deletion support is not confirmed": "Удаление во внешнем сервисе не подтверждено",
    "local purge acknowledged": "локальная очистка подтверждена",
    "local_purge_acknowledged": "локальная очистка подтверждена",
    "local buffers purged": "локальные буферы очищены",
    "local_buffers_purged": "локальные буферы очищены",
    "metadata only": "только метаданные",
    "Owner/Admin": "Владелец/админ",
    "outside 2brain rec control": "вне контроля 2brain Rec",
    "outside_control": "вне контроля 2brain Rec",
    "pending": "ожидает",
    "Planned; this does not promise deletion outside 2brain Rec control.": "Запланировано; это не обещает удаление вне контроля 2brain Rec.",
    "policy blocked": "по политике",
    "policy_blocked": "по политике",
    "processing": "обработка",
    "purge_local_buffers": "локальные буферы",
    "purge_local_exports": "локальные экспорты",
    "confirm_local_expiry": "подтвердить локальное истечение",
    "Server audio purge requested": "Очистка серверного аудио запрошена",
    "unreachable": "недоступно",
    "Workspace policy disables this artifact egress.": "Политика рабочего пространства запрещает выгрузку этого файла.",
    "You": "Вы",
}


def _ui_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.replace("_", " ")
    return UI_TEXT.get(value, UI_TEXT.get(normalized, normalized))


def _speaker_display_label(label: str) -> str:
    if label.startswith("Speaker "):
        suffix = label.removeprefix("Speaker ").strip()
        return f"Спикер {suffix}" if suffix else "Спикер"
    return _ui_text(label)


def _notes_source_label(source_basis: str) -> str:
    return {
        "blocked": "заблокировано",
        "not_supported": "не поддерживается",
        "policy_deferral": "отложено политикой",
        "processing_status": "статус обработки",
        "stored_output": "сохраненные итоги",
    }.get(source_basis, _ui_text(source_basis))


def _notes_title(title: str) -> str:
    return {
        "Summary": "Кратко",
        "Key points": "Ключевое",
        "Decisions": "Решения",
        "Action Items": "Действия",
        "Follow-ups": "Продолжение",
        "Risks": "Риски",
        "Questions": "Вопросы",
        "Evidence": "Фрагменты",
    }.get(title, _ui_text(title))


def _ui_icon(name: str) -> str:
    paths = {
        "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="M7 10l5 5 5-5"></path><path d="M12 15V3"></path>',
        "minus": '<path d="M5 12h14"></path>',
        "trash": '<path d="M3 6h18"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path>',
    }
    return f'<svg class="ui-icon" data-icon="{name}" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>'


def _render_meeting_row(item: MeetingListItem, *, embedded: bool, selected: bool = False) -> str:
    href = f"{_base_path(embedded)}/{item.meeting_id}"
    selected_class = " is-selected" if selected else ""
    source_icon = "▣" if item.source == "screen_recording" else "◁"
    title = escape(item.title)
    return f"""
      <article class="meeting-row cabinet-row{selected_class}" data-meeting-row data-meeting-id="{item.meeting_id}" data-meeting-title="{title}">
        <input class="row-check" type="checkbox" data-meeting-select aria-label="Выбрать запись {title}">
        <span class="row-icon">{source_icon}</span>
        <a class="meeting-title" href="{href}">
          <span class="row-title">{title} <span class="muted">{_duration(item.duration_seconds)}</span></span>
          <span class="row-meta"><span>{escape(_ui_text(item.status_label))}</span></span>
        </a>
        <button class="row-delete icon-button" type="button" data-row-delete aria-label="Удалить запись {title}" title="Удалить">{_ui_icon("trash")}</button>
        <span class="meeting-date">{_date_label(item)}</span>
      </article>
    """


def _render_list_delete_dialog() -> str:
    bounded_copy = "Запись будет удалена везде, где ее контролирует 2brain Rec. Уже скачанные или экспортированные копии могут оставаться вне контроля 2brain Rec."
    return f"""
      <dialog class="delete-dialog" data-delete-dialog data-title-one="Удалить запись?" data-title-many="Удалить записи?">
        <h2 data-delete-title>Удалить запись?</h2>
        <p><span data-delete-count>Вы удаляете 1 запись.</span> Это действие нельзя отменить.</p>
        <p class="truth-copy" data-bounded-delete-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(bounded_copy)}</p>
        <div class="dialog-actions">
          <button type="button" class="quiet" data-delete-cancel>Отмена</button>
          <button type="button" class="danger-button" data-delete-confirm>Удалить</button>
        </div>
        <div class="dialog-error" data-delete-error hidden>Не удалось удалить запись. Попробуйте еще раз.</div>
      </dialog>
    """


def _render_transcript(segments: list[TranscriptSegmentView]) -> str:
    return "\n".join(
        f"""
          <article class="segment">
            {_render_timestamp(segment)}
            <div class="speaker"><span class="dot"></span>{escape(_speaker_display_label(segment.speaker_label))}</div>
            <div class="text">{escape(segment.text)}</div>
          </article>
        """
        for segment in segments
    )


def _render_timestamp(segment: TranscriptSegmentView) -> str:
    if segment.seekable and segment.seek_seconds is not None:
        return (
            f'<button class="timestamp timestamp-seek" type="button" '
            f'data-seek-seconds="{escape(str(segment.seek_seconds))}">{escape(segment.timestamp_label)}</button>'
        )
    return f'<div class="timestamp">{escape(segment.timestamp_label)}</div>'


def _render_playback(review: MeetingReviewResponse) -> str:
    if review.playback.available and review.playback.playback_path:
        speed_options = ",".join(f"{speed:g}" for speed in review.playback.speed_options)
        return f"""
          <section class="playback-bar detail-playback" data-playback-shell data-source-mode="{escape(review.playback.source_mode)}">
            <audio class="playback-audio" data-playback-player preload="metadata" src="{escape(review.playback.playback_path)}"></audio>
            <div class="playback-controls" aria-label="Управление воспроизведением">
              <button type="button" class="playback-round" data-playback-skip="-15" aria-label="Назад на 15 секунд">15</button>
              <button type="button" class="playback-round primary-play" data-playback-toggle aria-label="Воспроизвести">Play</button>
              <button type="button" class="playback-round" data-playback-skip="15" aria-label="Вперед на 15 секунд">15</button>
              <button type="button" class="playback-speed" data-playback-speed-toggle data-speed-options="{escape(speed_options)}">1x</button>
            </div>
            <div class="playback-progress-row">
              <span class="playback-time" data-playback-current>00:00</span>
              <input class="playback-progress" data-playback-progress type="range" min="0" max="{review.playback.duration_seconds}" step="0.1" value="0" aria-label="Позиция записи">
              <span class="playback-time" data-playback-duration>{_timecode(review.playback.duration_seconds)}</span>
            </div>
            {_render_playback_speaker_timeline(review)}
          </section>
          {_playback_script()}
        """
    return f"""
      <section class="playback-bar detail-playback is-unavailable" data-source-mode="{escape(review.playback.source_mode)}">
        <span>{escape(review.playback.policy_label)}</span>
        <span>{_duration(review.playback.duration_seconds)}</span>
      </section>
    """


def _playback_script() -> str:
    return """
      <script>
        (() => {
          const player = document.querySelector("[data-playback-player]");
          if (!player) return;
          const toggle = document.querySelector("[data-playback-toggle]");
          const current = document.querySelector("[data-playback-current]");
          const duration = document.querySelector("[data-playback-duration]");
          const progress = document.querySelector("[data-playback-progress]");
          const speedToggle = document.querySelector("[data-playback-speed-toggle]");
          const formatTime = (seconds) => {
            if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
            const rounded = Math.floor(seconds);
            const minutes = Math.floor(rounded / 60);
            const rest = String(rounded % 60).padStart(2, "0");
            return `${String(minutes).padStart(2, "0")}:${rest}`;
          };
          const syncTime = () => {
            if (current) current.textContent = formatTime(player.currentTime);
            if (progress) progress.value = String(player.currentTime || 0);
            if (duration && Number.isFinite(player.duration)) duration.textContent = formatTime(player.duration);
          };
          player.addEventListener("loadedmetadata", () => {
            if (progress && Number.isFinite(player.duration)) progress.max = String(player.duration);
            syncTime();
          });
          player.addEventListener("timeupdate", syncTime);
          player.addEventListener("play", () => {
            if (toggle) toggle.textContent = "Pause";
          });
          player.addEventListener("pause", () => {
            if (toggle) toggle.textContent = "Play";
          });
          if (toggle) {
            toggle.addEventListener("click", () => {
              if (player.paused) player.play().catch(() => {});
              else player.pause();
            });
          }
          document.querySelectorAll("[data-playback-skip]").forEach((button) => {
            button.addEventListener("click", () => {
              const delta = Number.parseFloat(button.dataset.playbackSkip || "0");
              if (!Number.isFinite(delta)) return;
              const max = Number.isFinite(player.duration) ? player.duration : Number.POSITIVE_INFINITY;
              player.currentTime = Math.max(0, Math.min(max, player.currentTime + delta));
              syncTime();
            });
          });
          if (progress) {
            progress.addEventListener("input", () => {
              const next = Number.parseFloat(progress.value || "0");
              if (Number.isFinite(next)) {
                player.currentTime = next;
                syncTime();
              }
            });
          }
          document.querySelectorAll("[data-seek-seconds]").forEach((button) => {
            button.addEventListener("click", () => {
              const seekSeconds = Number.parseFloat(button.dataset.seekSeconds || "0");
              if (!Number.isFinite(seekSeconds)) return;
              player.currentTime = seekSeconds;
              syncTime();
              player.play().catch(() => {});
            });
          });
          if (speedToggle) {
            const speeds = (speedToggle.dataset.speedOptions || "1").split(",")
              .map((value) => Number.parseFloat(value))
              .filter((value) => Number.isFinite(value) && value > 0);
            speedToggle.addEventListener("click", () => {
              const currentSpeed = player.playbackRate || 1;
              const index = speeds.findIndex((speed) => Math.abs(speed - currentSpeed) < 0.001);
              const nextSpeed = speeds[(index + 1) % speeds.length] || 1;
              player.playbackRate = nextSpeed;
              speedToggle.textContent = `${nextSpeed}x`;
            });
          }
        })();
      </script>
    """


def _render_playback_speaker_timeline(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return '<div class="speaker-timeline" data-speaker-timeline></div>'
    duration = max(1, review.playback.duration_seconds)
    lanes = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        segments = []
        for segment in speaker.segments:
            start = max(0.0, float(segment.start_seconds))
            end = min(float(duration), max(start, float(segment.end_seconds)))
            left = min(100.0, max(0.0, start / duration * 100))
            width = min(100.0 - left, max(0.2, (end - start) / duration * 100))
            segment_label = f"{speaker_label} {_timecode(int(start))}-{_timecode(int(end))}"
            segments.append(
                f'<span class="timeline-segment" data-lane-segment title="{escape(segment_label)}" '
                f'aria-label="{escape(segment_label)}" style="left:{left:.2f}%;width:{width:.2f}%"></span>'
            )
        lanes.append(
            f"""
            <div class="timeline-lane" data-speaker-lane="{escape(speaker.speaker_key)}">
              <span class="timeline-label">{escape(speaker_label)}</span>
              <span class="timeline-track">{"".join(segments)}</span>
              <span class="timeline-share">{speaker.talk_time_percent}%</span>
            </div>
            """
        )
    return f'<div class="speaker-timeline" data-speaker-timeline>{"".join(lanes)}</div>'


def _render_speaker_lanes(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return f'<div class="muted">{escape(_ui_text("Speaker lanes are reserved until diarization is available."))}</div>'
    return "\n".join(
        f"""
        <div class="speaker-lane">
          <div class="row-meta"><strong>{escape(_speaker_display_label(speaker.label))}</strong><span>{speaker.talk_time_percent}%</span></div>
          <div class="lane-track"><div class="lane-fill" style="width:{speaker.talk_time_percent}%"></div></div>
        </div>
        """
        for speaker in review.speakers.speakers
    )


def _render_revision_status(review: MeetingReviewResponse) -> str:
    media_revision_id = escape(str(review.provenance.media_revision_id or ""))
    local_media_revision_id = escape(review.provenance.local_media_revision_id or "")
    label = escape(_ui_text(review.meeting.status_label))
    reason = escape(_ui_text(review.processing.reason_label or review.processing.reason_code) or "Текущая медиа-ревизия")
    return f"""
      <section class="revision-status" aria-label="Статус медиа-ревизии" data-media-revision-id="{media_revision_id}" data-local-media-revision-id="{local_media_revision_id}">
        <span class="chip {escape(review.meeting.status)}">{label}</span>
        <span class="row-meta"><span>Медиа-ревизия</span><span>{reason}</span></span>
      </section>
    """


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
        <strong>{escape(_ui_text("Delete this meeting everywhere 2brain Rec controls"))}</strong>
        <div class="truth-copy" data-boundary-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(_ui_text(BOUNDED_DELETE_COPY))}</div>
        <div class="state-row">
          <span class="muted">Резервные копии, локальные буферы, метаданные провайдера и уже переданные копии показываются отдельно.</span>
          <a class="mini-link" href="{report_href}">{escape(_ui_text("Report"))}</a>
        </div>
        <button type="button" disabled>{escape(_ui_text("Request deletion"))}</button>
      </div>
    """


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


def _render_notes_outcomes(review: MeetingReviewResponse) -> str:
    outcomes = [
        ("summary", "Summary", review.notes_action_truth.summary),
        ("key_points", "Key points", review.notes_action_truth.key_points),
        ("decisions", "Decisions", review.notes_action_truth.decisions),
        ("action_items", "Action Items", review.notes_action_truth.action_items),
        ("followups", "Follow-ups", review.notes_action_truth.followups),
        ("risks", "Risks", review.notes_action_truth.risks),
        ("questions", "Questions", review.notes_action_truth.questions),
        ("evidence", "Evidence", review.notes_action_truth.evidence),
    ]
    rows = "".join(_render_notes_outcome_row(category, title, state) for category, title, state in outcomes)
    source = escape(_notes_source_label(review.notes_action_truth.source_basis))
    source_basis = escape(review.notes_action_truth.source_basis)
    return f"""
      <div class="notes" data-outcome-source-basis="{source_basis}">
        <h3>{escape(_ui_text("Итоги встречи"))}</h3>
        <div class="state-list notes-outcomes">
          {rows}
        </div>
        <div class="muted">{escape(_ui_text("Outcome source"))}: {source}</div>
      </div>
    """


def _render_notes_outcome_row(category: str, title: str, state: NotesActionCategoryState) -> str:
    state_name = escape(state.state)
    items = "".join(_render_outcome_item(item) for item in state.items)
    return f"""
      <div class="state-row notes-outcome-row" data-outcome-category="{escape(category)}" data-outcome-state="{state_name}">
        <span><strong>{escape(_notes_title(title))}</strong><br><span class="muted">{escape(_ui_text(state.reason))}</span></span>
        <span class="chip {state_name}">{escape(_ui_text(state.label))}</span>
        {items}
      </div>
    """


def _render_outcome_item(item) -> str:
    text = escape(item.text or "")
    if not text:
        return ""
    refs = ", ".join(
        _timecode(int(ref.start_seconds or 0))
        for ref in item.source_refs[:2]
        if ref.start_seconds is not None
    )
    refs_html = f'<span class="muted">Источник: {escape(refs)}</span>' if refs else ""
    return f'<div class="outcome-item"><span>{text}</span>{refs_html}</div>'


def _render_top_actions(review: MeetingReviewResponse, *, embedded: bool) -> str:
    if embedded:
        return f'<button type="button" disabled>{escape(_ui_text("Open in browser"))}</button>'
    export_disabled = "disabled" if review.governance.export.state != "available" else ""
    share_disabled = "disabled" if review.governance.share.state != "available" else ""
    return f"""
      <button type="button" disabled>{escape(_ui_text(review.template.label))}</button>
      <button type="button" {export_disabled}>{escape(_ui_text(review.governance.export.label))}</button>
      <button type="button" {share_disabled}>{escape(_ui_text(review.governance.share.label))}</button>
      <button type="button" disabled>{escape(_ui_text("More"))}</button>
    """


async def _authorized_lifecycle_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> Meeting:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == viewer_user_id,
            WorkspaceMembership.status == "active",
        )
    )
    role = membership.role if membership is not None else None
    if meeting.created_by_user_id != viewer_user_id and role not in {"owner", "admin"}:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting


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
        return _ui_text(review.processing.reason_label)
    if review.processing.state in {"processing", "submitted"}:
        return "Мы показываем только подтвержденные данные и не создаем фальшивый текст."
    return "Проверьте статус обработки позже."


def _timecode(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{second:02d}"


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
        return "Без даты"
    months = {
        1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
        7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
    }
    return f"{item.started_at.day} {months[item.started_at.month]}"


def _sort_label(sort: str) -> str:
    return {
        "updated_desc": "Сначала новые",
        "updated_asc": "Сначала старые",
        "duration_desc": "Сначала длинные",
        "duration_asc": "Сначала короткие",
    }.get(sort, "Сначала новые")


def _base_path(embedded: bool) -> str:
    return "/desktop/meetings" if embedded else "/meetings"
