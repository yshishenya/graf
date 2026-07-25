from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_SRC = REPO_ROOT / "apps" / "server" / "src"
if str(SERVER_SRC) not in sys.path:
    sys.path.insert(0, str(SERVER_SRC))

from twobrain_rec_server.api.schemas import (  # noqa: E402
    ArtifactDeletionState,
    ArtifactEgressState,
    DeletionVerificationReport,
    GovernanceActionState,
    GovernanceActionSummary,
    LifecycleActivityItem,
    LocalPurgeTask,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    NotesActionCategoryState,
    NotesActionTruthState,
    NotesReviewState,
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SpeakerReviewState,
    TranscriptReviewState,
)
from twobrain_rec_server.cabinet.rendering import (  # noqa: E402
    render_deletion_report_fragment,
    render_deletion_report_page,
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.templates import cabinet_html_response  # noqa: E402
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY  # noqa: E402
from twobrain_rec_server.domain.statuses import (  # noqa: E402
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)

STATIC_DIR = SERVER_SRC / "twobrain_rec_server" / "cabinet" / "static" / "cabinet"
FORBIDDEN_EVIDENCE_MARKERS = (
    "SAFE_TRANSCRIPT_TEXT",
    "storage_object_key",
    "signed_url",
    "external_job_id",
    "/Users/",
    "sk-",
    "password",
)
FORBIDDEN_FRONTEND_MARKERS = (
    "tailwind",
    "daisyui",
    "flowbite",
    "shadcn",
    "react",
    "vue",
    "svelte",
    "webpack",
    "vite",
    "googleapis",
    "gstatic",
    "jsdelivr",
    "cdnjs",
)


def _governance() -> GovernanceActionSummary:
    return GovernanceActionSummary(
        share=GovernanceActionState(state="available", label="Share", reason="Login-required sharing", destructive=False),
        export=GovernanceActionState(state="disabled", label="Export package", reason="No package", destructive=False),
        download=GovernanceActionState(state="disabled", label="Download", reason="No artifact", destructive=False),
        retention=GovernanceActionState(state="planned", label="Retention policy planned", reason="future", destructive=False),
        delete=GovernanceActionState(
            state="available",
            label="Delete this meeting everywhere 2brain Rec controls",
            reason="Owner request allowed",
            destructive=True,
        ),
    )


def _access() -> MeetingAccessState:
    return MeetingAccessState(
        state="owner",
        label="Owner",
        reason="You own this meeting.",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )


def _item() -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title="Синтетическая встреча",
        started_at=datetime(2026, 6, 26, 8, 0, tzinfo=UTC),
        ended_at=datetime(2026, 6, 26, 8, 20, tzinfo=UTC),
        duration_seconds=1200,
        source="desktop_recording",
        status="ready",
        status_label="Готово",
        status_reason=None,
        primary_action="open",
        transcript_available=True,
        diarization_available=True,
        notes_available=True,
        updated_at=datetime(2026, 6, 26, 8, 25, tzinfo=UTC),
        access=_access(),
        artifacts=[
            ArtifactEgressState(
                artifact_class="audio",
                state="available",
                label="Audio",
                reason=None,
                action="download",
            )
        ],
        governance=_governance(),
        future_slots=[
            SlotState(state="planned", label="Star", reason="future"),
            SlotState(state="planned", label="Tag", reason="future"),
        ],
    )


def _list_response() -> MeetingListResponse:
    return MeetingListResponse(
        items=[_item()],
        filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
        generated_at=datetime.now(UTC),
    )


def _review() -> MeetingReviewResponse:
    item = _item()
    category = NotesActionCategoryState(
        state="not_found",
        label="Не найдено",
        reason="Синтетическая встреча не содержит надежной опоры для этой категории.",
        readiness_impact="closes_gap",
        copy_key="notes.outcomes.not_found",
    )
    return MeetingReviewResponse(
        meeting=item,
        provenance=MeetingProvenance(
            source_roles=["local_microphone", "incoming_system"],
            processing_dependency="mediascribe",
            content_policy="authorized_detail_only",
        ),
        processing=ProcessingReviewState(
            state="ready",
            stage="imported",
            reason_code=None,
            reason_label=None,
            content_available=True,
            transcript_available=True,
            diarization_available=True,
            summary_available=False,
            updated_at=datetime.now(UTC),
            next_action="none",
        ),
        transcript=TranscriptReviewState(available=False, language="ru", degraded_reason="metadata_safe_fixture", search_enabled=False, segments=[]),
        speakers=SpeakerReviewState(available=False, assignment_state="reserved", degraded_reason="metadata_safe_fixture", speakers=[]),
        notes=NotesReviewState(available=False, sections=[], unavailable_reason="processing"),
        playback=PlaybackReviewState(
            available=False,
            duration_seconds=1200,
            unavailable_reason="no_audio",
            playback_path=None,
            policy_label="Аудио не загружается в runtime evidence",
            source_mode="none",
            included_sources=[],
            speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        ),
        governance=_governance(),
        access=_access(),
        share=SharePanelState(
            team_visibility="disabled",
            active_grants=[],
            copy_link_state="available",
            public_link_state="disabled_by_default",
        ),
        artifacts=[],
        activity=MeetingActivityResponse(meeting_id=item.meeting_id, items=[]),
        notes_action_truth=NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="stored_output",
        ),
        deletion_truth_copy="Files already downloaded or exported are outside 2brain Rec deletion control.",
        assistant=SlotState(state="planned", label="Assistant", reason="future"),
        template=SlotState(state="planned", label="Template", reason="future"),
    )


def _deletion_report() -> DeletionVerificationReport:
    expires_at = datetime.now(UTC) + timedelta(days=7)
    return DeletionVerificationReport(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_states=[
            ArtifactDeletionState(
                artifact_class="audio_object",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Server audio purge requested",
                safe_reason="artifact_lifecycle_state",
            )
        ],
        backup=ArtifactDeletionState(
            artifact_class="backup",
            control_scope=DeletionControlScope.BACKUP,
            state=DeletionArtifactState.PENDING_EXPIRY,
            label="Backup expiry pending",
            safe_reason="backup_expiry_pending",
        ),
        dependencies=[],
        post_egress_limits=[],
        local_purge=[
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS,
                state=LocalPurgeTaskState.PENDING,
                safe_reason="delete_requested",
                expires_at=expires_at,
            )
        ],
        activity=[
            LifecycleActivityItem(
                event_id=uuid4(),
                event_type="deletion_requested",
                actor_label="Owner/Admin",
                outcome="accepted",
                safe_reason="user_request",
                created_at=datetime.now(UTC),
            )
        ],
    )


def _add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": passed, "detail": detail})


def _forbidden_found(content: str, markers: tuple[str, ...]) -> list[str]:
    lowered = content.lower()
    return [marker for marker in markers if marker.lower() in lowered]


def run_checks() -> dict[str, Any]:
    list_response = _list_response()
    review = _review()
    list_page = render_meeting_list_page(list_response)
    embedded_list_page = render_meeting_list_page(list_response, embedded=True)
    detail_page = render_meeting_detail_page(review)
    embedded_detail_page = render_meeting_detail_page(review, embedded=True)
    settings_page = render_settings_page()
    embedded_settings_page = render_settings_page(embedded=True)
    deletion_report_page = render_deletion_report_page("Синтетическая встреча", _deletion_report())
    list_fragment = render_meeting_list_fragment(list_response)
    detail_fragment = render_meeting_detail_fragment(review)
    deletion_report_fragment = render_deletion_report_fragment("Синтетическая встреча", _deletion_report())
    css = (STATIC_DIR / "cabinet.css").read_text()
    js = (STATIC_DIR / "cabinet.js").read_text()
    hx_response = cabinet_html_response(list_fragment, hx_request=True)

    html_surfaces = {
        "standalone_list": list_page,
        "embedded_list": embedded_list_page,
        "standalone_detail": detail_page,
        "embedded_detail": embedded_detail_page,
        "standalone_settings": settings_page,
        "embedded_settings": embedded_settings_page,
        "deletion_report": deletion_report_page,
        "list_fragment": list_fragment,
        "detail_fragment": detail_fragment,
        "deletion_report_fragment": deletion_report_fragment,
    }
    all_html = "\n".join(html_surfaces.values())
    checks: list[dict[str, Any]] = []

    _add_check(checks, "standalone_shell", "<!doctype html>" in list_page and 'data-surface-mode="standalone_browser"' in list_page, "full browser shell is rendered")
    _add_check(checks, "embedded_shell", 'class="app-shell desktop-embedded"' in embedded_list_page, "desktop WebView uses embedded shell mode")
    _add_check(
        checks,
        "settings_shell",
        'data-settings-overview' in settings_page
        and 'href="/settings/integrations/calendar"' in settings_page
        and 'data-active-nav="settings"' in settings_page,
        "settings overview exposes the calendar category",
    )
    _add_check(checks, "native_controls_absent_from_webview", "Record live" not in embedded_detail_page and "Screen Recording" not in embedded_detail_page, "native capture copy stays outside WebView")
    _add_check(checks, "list_fragment_bounded", "<!doctype html>" not in list_fragment and 'data-cabinet-fragment="meeting-list"' in list_fragment, "list HTMX response is a bounded fragment")
    _add_check(checks, "detail_fragment_bounded", "<!doctype html>" not in detail_fragment and 'data-cabinet-fragment="meeting-detail"' in detail_fragment, "detail HTMX response is a bounded fragment")
    _add_check(checks, "deletion_report_fragment_bounded", "<!doctype html>" not in deletion_report_fragment and 'data-cabinet-fragment="deletion-report"' in deletion_report_fragment, "deletion report HTMX response is a bounded fragment")
    _add_check(checks, "hx_vary_header", hx_response.headers.get("Vary") == "HX-Request", "HTMX responses declare Vary: HX-Request")
    _add_check(checks, "responsive_contract", "@media (max-width: 980px)" in css and "@media (max-width: 540px)" in css, "desktop and mobile-width breakpoints exist")
    _add_check(checks, "focus_contract", ":focus-visible" in css and "min-height: 46px;" in css, "focus visibility and target sizing are styled")
    _add_check(
        checks,
        "ephemeral_js",
        "localStorage" not in js
        and 'sessionStorage.removeItem("htmx-history-cache")' in js
        and 'sessionStorage.removeItem("htmx-current-path-for-history")' in js
        and "sessionStorage.setItem(candidateStorageKey, JSON.stringify({" in js
        and "poll_url: candidate.poll_url" in js
        and "template: activeTemplate" in js
        and "htmx:afterSwap" in js,
        "private fragment history is cleared while only the metadata-only pending candidate state survives a same-tab refresh",
    )
    _add_check(checks, "no_frontend_toolchain_markers", not _forbidden_found(css + "\n" + js, FORBIDDEN_FRONTEND_MARKERS), "static cabinet assets avoid excluded frontend stacks")
    _add_check(checks, "metadata_safe_html", not _forbidden_found(all_html, FORBIDDEN_EVIDENCE_MARKERS), "rendered synthetic evidence omits private markers")

    result = "pass" if all(check["passed"] for check in checks) else "fail"
    return {
        "feature": "058-web-cabinet-htmx-shell",
        "result": result,
        "surface_count": len(html_surfaces),
        "checks": checks,
    }


def main() -> int:
    evidence = run_checks()
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
