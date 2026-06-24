from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_TRANSCRIPT_TEXT,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import set_artifact_policy


def test_cabinet_web_detail_renders_access_artifacts_and_activity_without_private_identifiers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed", package_export="allowed")
    client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "Владелец" in response.text
    assert "Видимость для команды" in response.text
    assert "Расшифровка" in response.text
    assert "Скачать" in response.text
    assert "скачивание завершено" in response.text.lower()
    assert "Уже скачанные или экспортированные файлы" in response.text
    assert 'data-boundary-copy="Files already downloaded' in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text
    assert "storage_object_key" not in response.text
    assert "share_token_hash" not in response.text
