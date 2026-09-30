from html.parser import HTMLParser
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

GUIDE_PATH = "/guides/zapis-vstrechi-na-mac-bez-bota"


class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.canonicals = []
        self.h1_count = 0
        self.meta = {}
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonicals.append(attributes.get("href"))
        if tag == "meta":
            self.meta[attributes.get("name") or attributes.get("property")] = attributes.get("content", "")
        if tag == "h1":
            self.h1_count += 1
        if tag == "script":
            self.scripts.append(attributes.get("src", "inline"))


def test_guide_is_crawlable_and_sitemap_uses_query_free_canonical():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get(GUIDE_PATH + "?utm_source=example")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "noindex" not in response.headers.get("x-robots-tag", "")
        parser = GuideParser()
        parser.feed(response.text)
        assert parser.canonicals == ["https://rec.2brain.pro" + GUIDE_PATH]
        assert "noindex" not in parser.meta.get("robots", "")
        assert parser.meta["og:url"] == parser.canonicals[0]
        assert parser.meta["description"] == parser.meta["og:description"]
        assert parser.meta["viewport"] == "width=device-width, initial-scale=1"
        assert parser.h1_count == 1
        sitemap = ElementTree.fromstring(client.get("/sitemap.xml").text)
        locations = [item.text for item in sitemap.findall("{*}url/{*}loc")]
        assert locations.count(parser.canonicals[0]) == 1
        assert len(locations) == len(set(locations))
        assert client.get("/robots.txt").status_code == 200


def test_guide_links_resolve_and_has_no_optional_tracking_or_unverified_sales_claims():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro", public_analytics_enabled=True))) as client:
        response = client.get(GUIDE_PATH)
        parser = GuideParser()
        parser.feed(response.text)
        assert not parser.scripts
        for link in set(parser.links):
            path, _, fragment = link.partition("#")
            if not path:
                assert fragment in parser.ids
                continue
            target = client.get(path)
            assert target.status_code == 200
            if fragment:
                target_parser = GuideParser()
                target_parser.feed(target.text)
                assert fragment in target_parser.ids
        assert "/download" in parser.links
        assert "macOS 14.5" in response.text
        assert "Apple Silicon" in response.text
        assert "Intel" in response.text
        assert "проверьте" in response.text.lower()
        assert "оплата откроется" not in response.text.lower()
        assert "7 дней" not in response.text
        assert "phc_" not in response.text
        assert client.get("/guides/nonexistent").status_code == 404
