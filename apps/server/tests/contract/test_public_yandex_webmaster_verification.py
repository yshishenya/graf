"""Public Webmaster proof is rendered only for the approved production hostname."""

from html.parser import HTMLParser

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.web import router


class VerificationMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = False
        self.verification = []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "yandex-verification":
            self.verification.append((self.in_head, attributes.get("content")))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False


@pytest.mark.parametrize(
    "base_url,expected",
    [
        ("https://rec.2brain.pro", [(True, "de5457f669a9f4ed")]),
        ("https://example.test", []),
        ("https://rec.2brain.pro.example.test", []),
    ],
)
def test_webmaster_meta_is_one_head_tag_on_the_approved_host(base_url, expected):
    app = FastAPI()
    # Even a foreign host configured with the production canonical URL must not
    # publish this operator's proof on a customer's self-hosted installation.
    app.state.settings = Settings(
        public_base_url="https://rec.2brain.pro",
        public_analytics_enabled=False,
        product_analytics_enabled=False,
    )
    app.include_router(router)
    with TestClient(app, base_url=base_url) as client:
        response = client.get("/")
        assert response.status_code == 200
        parser = VerificationMetaParser()
        parser.feed(response.text)
        assert parser.verification == expected
        # This verification method does not depend on enabling the optional SDK.
        assert "graf-public-analytics-config" not in response.text
        assert "mc.yandex.ru" not in response.text


@pytest.mark.parametrize("path", ["/download", "/guides", "/privacy"])
def test_webmaster_meta_is_not_added_to_other_public_pages(path):
    app = FastAPI()
    app.state.settings = Settings(public_analytics_enabled=False, product_analytics_enabled=False)
    app.include_router(router)
    with TestClient(app, base_url="https://rec.2brain.pro") as client:
        response = client.get(path)
        assert response.status_code == 200
        parser = VerificationMetaParser()
        parser.feed(response.text)
        assert parser.verification == []
