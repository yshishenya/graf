import re
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / "apps/server/src/twobrain_rec_server/public"
PAGES = {
    "/transcription": "Расшифровка аудио и видео в текст",
    "/meeting-minutes": "Протокол встречи из записи: итоги, решения и задачи",
    "/record-without-bot": "Запись и расшифровка звонков без бота",
}
FOOTER_LINKS = (
    '          <a href="/transcription">Расшифровка аудио и видео</a>\n',
    '          <a href="/meeting-minutes">Протокол встречи</a>\n',
    '          <a href="/record-without-bot">Запись без бота</a>\n',
)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def test_search_pages_discovery_metadata_and_product_boundaries():
    app = create_app(Settings(public_base_url="https://rec.2brain.pro"))
    with TestClient(app) as client:
        titles, descriptions, contents = set(), set(), set()
        for path, heading in PAGES.items():
            response = client.get(path + "?utm_content=private@example.com&x=%3Cscript%3E")
            assert response.status_code == 200
            parser = PageParser()
            parser.feed(response.text)
            tags = parser.tags
            assert len([t for t, _ in tags if t == "h1"]) == 1
            assert ("html", {"lang": "ru"}) in tags
            assert heading in response.text
            assert response.headers["x-frame-options"] == "DENY"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert ("link", {"rel": "canonical", "href": "https://rec.2brain.pro" + path}) in tags
            assert 'property="og:title"' in response.text
            descriptions.add(
                next(
                    a["content"] for t, a in tags if t == "meta" and a.get("name") == "description"
                )
            )
            titles.add(re.search(r"<title>(.*?)</title>", response.text).group(1))
            contents.add(" ".join(parser.text))
            links = {a["href"] for t, a in tags if t == "a" and "href" in a}
            assert {"/", "/download", *PAGES} - {path} <= links
            for link in links:
                if link.startswith("/") and not link.startswith("/login"):
                    assert client.get(link).status_code == 200
            assert all(
                a.get("alt") and a.get("width") and a.get("height") for t, a in tags if t == "img"
            )
            assert "private@example.com" not in response.text
            assert "graf-public-analytics-config" not in response.text
            assert not [a for t, a in tags if t in {"script", "form"}]
            assert "Windows" in response.text and "macOS 14.5" in response.text
            assert not any(a.get("href", "").endswith((".msix", ".exe")) for t, a in tags)
        assert len(titles) == len(descriptions) == len(contents) == 3
        sitemap = ElementTree.fromstring(client.get("/sitemap.xml").text)
        locations = {
            node.text for node in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        }
        assert {"https://rec.2brain.pro" + path for path in PAGES} <= locations
        assert "https://rec.2brain.pro/guides/zapis-vstrechi-na-mac-bez-bota" in locations
        assert len(locations) == len(list(sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")))
        assert client.get("/not-a-search-page").status_code == 404
        main = client.get("/").text
        assert all(link.strip() in main for link in FOOTER_LINKS)


def test_search_links_are_in_the_landing_footer():
    text = (PUBLIC / "templates/public/landing.html").read_text()
    content, footer = text.split('<footer class="site-footer">', 1)
    for link in FOOTER_LINKS:
        assert link not in content
        assert footer.count(link) == 1


def test_search_metadata_is_independent_of_host_and_query():
    app = create_app(Settings(public_base_url="https://rec.2brain.pro"))
    with TestClient(app) as client:
        response = client.get("/transcription?x=unsafe", headers={"host": "wrong.example"})
        assert response.status_code == 200
        assert 'href="https://rec.2brain.pro/transcription"' in response.text
        assert "wrong.example" not in response.text
        assert "?x=unsafe" not in response.text
