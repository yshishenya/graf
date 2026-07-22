from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    CONTENT_EXPORT_FORMATS_BY_SCOPE,
    ArtifactEgressState,
    ContentExportCapabilityResponse,
    ContentExportReadiness,
    MeetingAccessState,
)
from twobrain_rec_server.cabinet import egress, exports
from twobrain_rec_server.cabinet.view_models import governance_summary


def _owner_access(*, can_export: bool = True) -> MeetingAccessState:
    return MeetingAccessState(
        state="owner",
        label="Owner",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=can_export,
    )


def _content_exports(
    *, transcript: str, summary: str, combined: str
) -> ContentExportCapabilityResponse:
    return ContentExportCapabilityResponse(
        processing_result_id=uuid4(),
        outcome_set_id=uuid4(),
        transcript=ContentExportReadiness(state=transcript),
        summary=ContentExportReadiness(state=summary),
        combined=ContentExportReadiness(state=combined),
        formats={
            scope: list(formats) for scope, formats in CONTENT_EXPORT_FORMATS_BY_SCOPE.items()
        },
        duration_seconds=60,
    )


def test_meeting_governance_composes_feature_120_content_export_with_existing_audio_actions() -> (
    None
):
    governance = governance_summary(
        access=_owner_access(),
        artifacts=[
            ArtifactEgressState(
                artifact_class="audio",
                state="available",
                label="Audio",
                action="download",
            ),
            ArtifactEgressState(
                artifact_class="package",
                state="missing",
                label="Package",
                action="disabled",
            ),
        ],
        content_exports=_content_exports(
            transcript="available",
            summary="processing",
            combined="missing",
        ),
        can_delete=True,
    )

    assert governance.download.state == "available"
    assert governance.export.state == "available"
    assert governance.export.label == "Экспортировать…"
    assert governance.delete.state == "available"


def test_feature_120_availability_and_policy_are_both_required_for_content_export() -> None:
    unavailable = _content_exports(
        transcript="processing",
        summary="missing",
        combined="missing",
    )

    not_ready = governance_summary(
        access=_owner_access(),
        content_exports=unavailable,
    )
    denied = governance_summary(
        access=_owner_access(can_export=False),
        content_exports=_content_exports(
            transcript="available",
            summary="available",
            combined="available",
        ),
    )

    assert not_ready.export.state == "disabled"
    assert denied.export.state == "disabled"


def test_feature_121_reuses_feature_120_format_matrix_and_renderer() -> None:
    assert exports.FORMAT_COMPATIBILITY is CONTENT_EXPORT_FORMATS_BY_SCOPE
    assert egress.render_content_export is exports.render_content_export
    assert set(exports.FORMAT_COMPATIBILITY) == {"transcript", "summary", "combined"}
    assert set(exports.FORMAT_COMPATIBILITY["transcript"]) == {
        "txt",
        "md",
        "csv",
        "xlsx",
        "json",
        "srt",
    }
