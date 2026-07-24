from __future__ import annotations

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    SAFE_TRANSCRIPT_TEXT,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import add_retained_playback_m4a


def test_browser_and_embedded_share_the_two_tab_meeting_workspace(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id)

    pages = [
        (
            client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers()),
            f"/meetings/{seeds.ready_id}/share",
        ),
        (
            client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers()),
            f"/desktop/meetings/{seeds.ready_id}/share",
        ),
    ]

    for response, share_url in pages:
        assert response.status_code == 200
        html = response.text
        assert html.count('role="tab"') == 2
        assert ">Итоги</button>" in html
        assert ">Расшифровка</button>" in html
        assert "Запись и расшифровка" not in html
        assert "data-share-dialog-open" in html
        assert f'hx-get="{share_url}"' in html
        assert 'id="meeting-share-host"' in html
        assert 'data-meeting-panel-open="more"' in html
        assert '<aside class="right-panel">' not in html
        assert SAFE_TRANSCRIPT_TEXT in html
        assert 'data-playback-state="available"' in html

    for share_url in (
        f"/meetings/{seeds.ready_id}/share",
        f"/desktop/meetings/{seeds.ready_id}/share",
    ):
        response = client.get(share_url, headers=auth_headers())
        assert response.status_code == 200
        assert 'data-share-dialog' in response.text
        assert 'data-share-recipient-input' in response.text


def test_meeting_player_is_outside_switchable_content_and_truth_stays_contextual(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id)

    response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert html.index('data-detail-panel="outcomes"') < html.index("data-playback-shell")
    assert html.index('data-detail-panel="recording"') < html.index("data-playback-shell")
    assert 'id="meeting-share-host"' in html
    assert 'class="meeting-actions-menu"' in html
    assert 'data-meeting-context-panel="more"' in html
    assert 'id="meeting-details-dialog"' in html
    assert "Медиа-ревизия" in html
    assert "Файлы" in html
    assert 'role="menu" aria-label="Действия со встречей"' in html
    assert "data-export-dialog-open" not in html


def test_browser_and_embedded_denied_meeting_render_only_generic_unavailable_state(client) -> None:
    seeds = seed_cabinet_meetings(client)

    pages = [
        client.get(f"/meetings/{seeds.foreign_id}", headers=auth_headers()),
        client.get(f"/desktop/meetings/{seeds.foreign_id}", headers=auth_headers()),
    ]

    for response in pages:
        assert response.status_code == 404
        html = response.text
        assert "Встреча больше недоступна" in html
        assert "Foreign private meeting" not in html
        assert "foreign-private-recording" not in html
        assert SAFE_TRANSCRIPT_TEXT not in html
        assert "data-playback-shell" not in html
