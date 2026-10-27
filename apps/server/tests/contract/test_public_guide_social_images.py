import struct
from html.parser import HTMLParser
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs = dict(attrs)
            key = attrs.get("property") or attrs.get("name")
            assert key not in self.tags, f"duplicate meta: {key}"
            self.tags[key] = attrs.get("content")


def test_two_guide_previews_are_public_pngs_on_the_canonical_origin():
    # Request Host and campaign parameters must never enter a cached preview URL.
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro")),
                    base_url="https://request.invalid") as client:
        for slug in ("rasshifrovka-zapisi-zoom", "protokol-vstrechi-iz-zapisi"):
            response = client.get(f"/guides/{slug}?utm_source=example&token=synthetic-secret")
            assert response.status_code == 200
            parser = MetaParser()
            parser.feed(response.text)
            tags = parser.tags
            assert tags["twitter:card"] == "summary_large_image"
            assert tags["twitter:image"] == tags["og:image"]
            assert tags["twitter:image:alt"] == tags["og:image:alt"]
            assert "ГРАФ" in tags["og:image:alt"]
            assert (tags["og:image:width"], tags["og:image:height"]) == ("1200", "630")
            assert tags["og:image:type"] == "image/png"
            url = urlsplit(tags["og:image"])
            assert (url.scheme, url.netloc) == ("https", "rec.2brain.pro")
            assert url.query.startswith("v=") and len(url.query) == 14
            assert url.path.startswith("/static/public/")
            image = client.get(url.path + "?" + url.query)
            assert image.status_code == 200
            assert image.headers["content-type"] == "image/png"
            assert "immutable" in image.headers["cache-control"]
            assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", image.content[16:24]) == (1200, 630)
            assert len(image.content) < 50000
            assert "noindex" not in image.headers.get("x-robots-tag", "")
        for path in ("/", "/download", "/privacy", "/guides", "/transcription"):
            parser = MetaParser()
            response = client.get(path)
            assert response.status_code == 200
            parser.feed(response.text)
            assert parser.tags["twitter:card"] == "summary"
            assert "og:image" not in parser.tags and "twitter:image" not in parser.tags
