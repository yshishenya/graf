from twobrain_rec_server.api.schemas import ArtifactEgressState
from twobrain_rec_server.cabinet.view_models import governance_summary


def test_governance_enables_download_and_export_from_available_artifact_states() -> None:
    governance = governance_summary(
        artifacts=[
            ArtifactEgressState(
                artifact_class="transcript",
                state="available",
                label="Download transcript",
                reason="allowed",
                action="download",
            ),
            ArtifactEgressState(
                artifact_class="package",
                state="available",
                label="Export package",
                reason="allowed",
                action="export",
            ),
        ]
    )

    assert governance.share.state == "available"
    assert governance.download.state == "available"
    assert governance.export.state == "available"


def test_governance_keeps_download_and_export_disabled_without_available_artifacts() -> None:
    governance = governance_summary(
        artifacts=[
            ArtifactEgressState(
                artifact_class="audio",
                state="policy_blocked",
                label="Disabled by policy",
                reason="blocked",
                action="disabled",
            )
        ]
    )

    assert governance.download.state == "disabled"
    assert governance.export.state == "disabled"
