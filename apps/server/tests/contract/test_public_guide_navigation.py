from html.parser import HTMLParser

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.content import PUBLIC_CONTENT_PAGES


class Header(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "header":
            self.inside = True
        if self.inside and tag == "a":
            self.links.append(data)
        if self.inside and tag == "img":
            self.images.append(data)

    def handle_endtag(self, tag):
        if tag == "header":
            self.inside = False


def test_content_header_is_consistent_crawlable_and_marks_section():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        for path in ["/guides", *(page.path for page in PUBLIC_CONTENT_PAGES)]:
            response = client.get(path)
            assert response.status_code == 200
            header = Header()
            header.feed(response.text)
            assert [item["href"] for item in header.links] == [
                "/", "/", "/guides", "/login?next=/meetings", "/download"
            ]
            active = [item for item in header.links if "aria-current" in item]
            assert len(active) == 1 and active[0]["href"] == "/guides"
            assert active[0]["aria-current"] == ("page" if path == "/guides" else "location")
            assert header.images[0]["alt"] == "ГРАФ"
            assert "content-header.css" in response.text
            assert "<script" not in response.text
            assert not any("data-analytics" in key for item in header.links for key in item)


def test_landing_header_links_to_guides_in_both_presentations():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get("/")
        header = Header()
        header.feed(response.text)
        assert sum(item["href"] == "/guides" for item in header.links) == 2
        assert 'aria-controls="mobile-navigation"' in response.text
        assert 'id="mobile-navigation"' in response.text
