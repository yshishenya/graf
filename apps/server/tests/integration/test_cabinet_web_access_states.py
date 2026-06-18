from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_TRANSCRIPT_TEXT,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import set_artifact_policy


def test_cabinet_web_detail_hides_operator_panels_and_private_identifiers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed", package_export="allowed")
    client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "<h3>Access</h3>" not in response.text
    assert "<h3>Artifacts</h3>" not in response.text
    assert "Team visibility" not in response.text
    assert "Download transcript" not in response.text
    assert "download completed" not in response.text.lower()
    assert "Files already downloaded" not in response.text
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text
    assert "storage_object_key" not in response.text
    assert "share_token_hash" not in response.text
