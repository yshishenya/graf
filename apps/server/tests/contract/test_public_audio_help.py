from pathlib import Path
from unittest.mock import AsyncMock
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from tests.contract.test_public_guide_navigation import Header
from tests.contract.test_public_protocol_guide import Parser
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.analytics import PUBLIC_ANALYTICS_SURFACES
from twobrain_rec_server.public.content import (
    GUIDE_PATH,
    HELP_PATH,
    ONE_SIDED_AUDIO_PATH,
    PUBLIC_CONTENT_SURFACES,
)


@pytest.mark.parametrize("path", [HELP_PATH, ONE_SIDED_AUDIO_PATH])
def test_help_metadata_links_and_section_without_measurement(path, monkeypatch):
    import twobrain_rec_server.public.web as web

    recorder = AsyncMock(side_effect=lambda request, response, **kwargs: response)
    monkeypatch.setattr(web, "record_public_page_response", recorder)
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get(path + "?utm_source=example&token=synthetic-secret")
        assert response.status_code == 200
        assert "set-cookie" not in response.headers
        assert path not in PUBLIC_CONTENT_SURFACES
        assert path not in PUBLIC_ANALYTICS_SURFACES
        p = Parser()
        p.feed(response.text)
        assert p.h1 == 1 and p.scripts == 0
        assert p.canonical == ["https://rec.2brain.pro" + path]
        assert p.meta["og:url"] == p.canonical[0]
        assert p.meta["description"] == p.meta["og:description"]
        assert "noindex" not in p.meta.get("robots", "")
        assert "noindex" not in response.headers.get("x-robots-tag", "")
        assert "synthetic-secret" not in response.text
        for href in set(p.links):
            if href.startswith("#"):
                assert href[1:] in p.ids
            elif href.startswith("/"):
                assert client.get(href).status_code < 400
        header = Header()
        header.feed(response.text)
        active = [item for item in header.links if "aria-current" in item]
        assert len(active) == 1 and active[0]["href"] == HELP_PATH
        assert active[0]["aria-current"] == ("page" if path == HELP_PATH else "location")
        urls = [x.text for x in ElementTree.fromstring(client.get("/sitemap.xml").text).findall("{*}url/{*}loc")]
        assert len(urls) == len(set(urls))
        assert urls.count("https://rec.2brain.pro" + path) == 1
    # Other public links use the existing recorder; only these two routes bypass it.
    for call in recorder.call_args_list:
        assert call.args[0].url.path not in (HELP_PATH, ONE_SIDED_AUDIO_PATH)


def test_help_has_concrete_audio_branches_and_code_grounded_labels():
    root = Path(__file__).resolve().parents[4]
    labels = (root / "apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift").read_text()
    controls = (root / "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift").read_text()
    onboarding = (root / "apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift").read_text()
    with TestClient(create_app(Settings())) as client:
        text = client.get(ONE_SIDED_AUDIO_PATH).text
        for label in (
            "Системный звук", "Микрофон", "Встреча", "Уровни записи", "Включить микрофон",
            "Микрофон есть, звук встречи тихий", "Звук встречи есть, микрофон тихий",
        ):
            assert label in labels and label in text
        assert "По умолчанию macOS" in controls and "По умолчанию macOS" in text
        for label in ("Открыть настройки", "Проверить еще раз", "Запись экрана и системного звука"):
            assert label in onboarding and label in text
        for expected in (
            "Слышно только меня", "Слышно только собеседника", "macOS 14.5",
            "Видео экрана ГРАФ не сохраняет", "Одни индикаторы", "не возвращает звук",
            "не подтверждается", "не публикуйте запись",
        ):
            assert expected.casefold() in text.casefold()
        assert text.count("<h1>") == 1
        assert 'href="' + ONE_SIDED_AUDIO_PATH + '"' in client.get(HELP_PATH).text
        assert ONE_SIDED_AUDIO_PATH in client.get(GUIDE_PATH).text
        for version in ("14.0", "15.0", "26"):
            assert f"mchld6aa7d23/{version}/mac/{version}" in text


@pytest.mark.browser
def test_help_mobile_text_zoom_and_keyboard_in_real_browser(tmp_path):
    import os
    import shutil
    import subprocess

    root = Path(__file__).resolve().parents[2]
    node = shutil.which("node")
    assert node is not None, "Node is required for the Help browser gate"
    with TestClient(create_app(Settings())) as client:
        for name, path in (
            ("help", HELP_PATH), ("audio", ONE_SIDED_AUDIO_PATH),
            ("hub", "/guides"), ("guide", GUIDE_PATH),
        ):
            (tmp_path / f"{name}.html").write_text(client.get(path).text)
    modules = os.environ.get("GRAF_NODE_MODULES", str(root / "tests/browser/node_modules"))
    result = subprocess.run(
        [node, str(root / "tests/browser/public-audio-help.test.cjs"), str(tmp_path)],
        cwd=root,
        env={**os.environ, "NODE_PATH": modules},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "public_audio_help_browser=pass" in result.stdout
