from __future__ import annotations

from pathlib import Path

import pytest

from twobrain_rec_server.deployment import scan_deployment_evidence_text

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_032_quickstart_closeout_names_required_metadata_only_evidence() -> None:
    text = (REPO_ROOT / "specs/032-rls-live-enforcement/quickstart.md").read_text(encoding="utf-8")

    for expected in (
        "local/test gate result",
        "production deployed commit",
        "production Alembic revision",
        "production covered table count",
        "production RLS enabled/forced count",
        "stale wording scan result",
        "forbidden content scan result",
    ):
        assert expected in text


def test_deployment_evidence_scan_accepts_032_safe_rls_truth_record() -> None:
    scan_deployment_evidence_text(
        "\n".join(
            [
                "production_rls_state_result=pass",
                "environment=live_production",
                "live_production_probe=read_only_metadata",
                "live_production_enforcement=enabled",
                "deployed_commit=3fd2162",
                "alembic_revision=0005_rls_hardening",
                "covered_table_count=28",
                "rls_enabled_and_forced_count=28",
                "failed_table_names=none",
            ]
        )
    )


@pytest.mark.parametrize(
    "content",
    [
        "production_rls_state_result=pass\nlive_production_enforcement=not_changed",
        "production_rls_state_result=pass\npassword=secret",
        "production_rls_state_result=pass\nAuthorization: Bearer abc",
    ],
)
def test_deployment_evidence_scan_rejects_032_forbidden_content(content: str) -> None:
    with pytest.raises(ValueError):
        scan_deployment_evidence_text(content)
