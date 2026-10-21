from unittest.mock import AsyncMock
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from tests.contract.test_public_protocol_guide import Parser
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.anonymous_aggregate import ANONYMOUS_PAGE_SURFACES
from twobrain_rec_server.public.analytics import PUBLIC_ANALYTICS_SURFACES
from twobrain_rec_server.public.content import (
    GUIDE_PATH,
    ONE_SIDED_AUDIO_PATH,
    PROTOCOL_GUIDE_PATH,
    PUBLIC_CONTENT_SURFACES,
    QUALITY_GUIDE_PATH,
    ZOOM_GUIDE_PATH,
)


def test_zoom_guide_is_indexable_with_only_anonymous_measurement(monkeypatch):
    import twobrain_rec_server.public.web as web

    recorder = AsyncMock(side_effect=lambda request, response, **kwargs: response)
    monkeypatch.setattr(web, "record_public_page_response", recorder)
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get(ZOOM_GUIDE_PATH + "?utm_source=example&token=synthetic-secret")
        assert response.status_code == 200 and "set-cookie" not in response.headers
        parser = Parser()
        parser.feed(response.text)
        assert parser.h1 == 1 and parser.scripts == 1
        assert parser.canonical == ["https://rec.2brain.pro" + ZOOM_GUIDE_PATH]
        assert parser.meta["description"] == parser.meta["og:description"]
        assert parser.meta["og:url"] == parser.canonical[0]
        assert "noindex" not in parser.meta.get("robots", "")
        assert "noindex" not in response.headers.get("x-robots-tag", "")
        assert "synthetic-secret" not in response.text
        assert ZOOM_GUIDE_PATH not in PUBLIC_CONTENT_SURFACES
        assert ZOOM_GUIDE_PATH not in PUBLIC_ANALYTICS_SURFACES
        assert ANONYMOUS_PAGE_SURFACES[ZOOM_GUIDE_PATH] == "public_zoom_recording_guide"
        recorder.assert_not_awaited()
        for href in set(parser.links):
            if href.startswith("#"):
                assert href[1:] in parser.ids
            elif href.startswith("/"):
                linked = client.get(href, headers={"accept": "text/html"})
                assert linked.status_code < 400
                if href == "/meetings":
                    assert len(linked.history) == 1 and linked.history[0].status_code == 303
                    assert linked.url.path == "/login" and linked.url.params["next"] == "/meetings"
        assert parser.links.count("/meetings") == 3
        article = response.text.split("<main", 1)[1].split("</main>", 1)[0]
        assert 'href="/login?next=/meetings"' not in article
        urls = [node.text for node in ElementTree.fromstring(client.get("/sitemap.xml").text).findall("{*}url/{*}loc")]
        assert urls.count(parser.canonical[0]) == 1 and len(urls) == len(set(urls))
        assert ZOOM_GUIDE_PATH in client.get("/guides").text
        mac = client.get(GUIDE_PATH).text
        ready_recording = mac.split("Если встреча уже записана</h3>")[1].split("</p>")[0]
        assert ZOOM_GUIDE_PATH in ready_recording
        assert mac.count('href="' + ZOOM_GUIDE_PATH + '"') == 1
        for path in (PROTOCOL_GUIDE_PATH, QUALITY_GUIDE_PATH, ONE_SIDED_AUDIO_PATH):
            assert ZOOM_GUIDE_PATH not in client.get(path).text
