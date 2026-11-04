"""Run interaction checks against the actual sharing templates and public renderer."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jinja2 import Template

from twobrain_rec_server.cabinet.rendering import render_public_meeting_reader

ROOT = Path(__file__).resolve().parents[2]
FRAGMENT = ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html"


def reader(*, embedded=False):
    return render_public_meeting_reader(
        projection={
            "meeting_label": "Учебная встреча — проверка всех материалов",
            "occurred_at": datetime(2026, 11, 3, tzinfo=UTC),
            "duration_seconds": 180,
            "summary_sections": [{"category": "summary", "text": "Синтетические итоги"}],
            "protocol": None,
            "media_version": "a" * 24,
            "playback_available": True,
            "transcript": [
                {
                    "speaker": "Говорящий",
                    "speaker_key": "speaker-1",
                    "text": "Проверка расшифровки",
                    "start_ms": 14000,
                    "end_ms": 16000,
                    "time": "0:14",
                },
                {"speaker": "Говорящий", "speaker_key": "speaker-2", "text": "Другая реплика",
                 "start_ms": 18000, "end_ms": 20000, "time": "0:18"},
            ],
            "speakers": [
                {"speaker_key": f"speaker-{index+1}", "label": "Говорящий", "confirmed": True,
                 "talk_time_percent": 50, "segments": [{"start_seconds": start, "end_seconds": start+2}]}
                for index, start in enumerate([14, 18])
            ],
        },
        playback_url="/audio",
        continue_url="/continue?workspace_id=synthetic",
        native_url="grafrec-dev://shared-meeting?v=1",
        embedded=embedded,
        authenticated=embedded,
    )


@pytest.mark.browser
@pytest.mark.parametrize("script", ["public-sharing", "sharing-owner", "sharing-auth-return"])
def test_sharing_user_journeys_in_browser(tmp_path, script):
    html = (
        reader()
        if script == "public-sharing"
        else (
            '<button data-share-dialog-open aria-controls="meeting-share-dialog">Поделиться</button>'
            + Template(FRAGMENT.read_text()).render(
                meeting_id="synthetic-meeting", share_workspace_id=None
            )
        )
    )
    fixture = tmp_path / "sharing.html"
    fixture.write_text(html)
    result = subprocess.run(
        ["node", str(ROOT / f"tests/browser/{script}.test.cjs"), str(fixture)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_embedded_reader_keeps_navigation_in_application():
    html = reader(embedded=True)
    assert 'href="/desktop/meetings"' in html
    assert "data-public-native hidden" in html
    assert 'data-authenticated="true"' in html
