from uuid import uuid4

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_TRANSCRIPT_TEXT,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import set_artifact_policy
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_cabinet_web_detail_renders_access_artifacts_and_activity_without_private_identifiers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed", package_export="allowed")
    client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert 'data-cabinet-shell' in response.text
    assert 'data-cabinet-navigation' in response.text
    assert 'data-active-nav="meetings"' in response.text
    assert "Поделиться" in response.text
    assert "Ещё" in response.text
    assert "Расшифровка" in response.text
    assert "Экспортировать…" in response.text
    assert "Файлы" in response.text
    assert "Спикеры" in response.text
    assert "Активность" in response.text
    assert "скачивание завершено" in response.text.lower()
    assert "Уже скачанные или экспортированные файлы" in response.text
    assert 'data-boundary-copy="Files already downloaded' in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text
    assert "storage_object_key" not in response.text
    assert "share_token_hash" not in response.text


def test_cabinet_web_unavailable_meetings_render_safe_html_and_keep_hx_problem_details(client) -> None:
    seeds = seed_cabinet_meetings(client)

    for base_path in ("/meetings", "/desktop/meetings"):
        denied_path = f"{base_path}/{seeds.foreign_id}"
        unavailable_paths = (
            denied_path,
            f"{base_path}/{uuid4()}",
            f"{base_path}/not-a-uuid",
        )
        for path in unavailable_paths:
            response = client.get(path, headers=auth_headers())

            assert response.status_code == 404
            assert response.headers["content-type"].startswith("text/html")
            assert "Страница недоступна" in response.text
            assert f'href="{base_path}"' in response.text
            assert "meeting_not_found" not in response.text
            assert str(seeds.foreign_id) not in response.text
            assert PRIVATE_EXTERNAL_JOB_ID not in response.text
            assert SAFE_TRANSCRIPT_TEXT not in response.text
            assert "storage_object_key" not in response.text
            assert "share_token_hash" not in response.text

        hx_response = client.get(
            denied_path,
            headers=auth_headers() | {"HX-Request": "true"},
        )
        assert hx_response.status_code == 404
        assert hx_response.headers["content-type"].startswith("application/problem+json")
        assert hx_response.json()["code"] == "meeting_not_found"


def test_cabinet_web_deletion_report_preserves_bounded_lifecycle_truth(client) -> None:
    seeds = seed_cabinet_meetings(client)
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202

    response = client.get(
        f"/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert "Отчет удаления" in response.text
    assert BOUNDED_DELETE_COPY in response.text
    assert "storage_object_key" not in response.text
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text
