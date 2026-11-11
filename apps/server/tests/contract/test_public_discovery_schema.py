import json
import re

import pytest
from fastapi.testclient import TestClient

from tests.contract.test_public_protocol_guide import Parser
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.content import GUIDE_PATH, QUALITY_GUIDE_PATH

BASE = "https://rec.2brain.pro"


def jsonld(html):
    return [
        json.loads(data)
        for data in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ]


def test_home_site_name_matches_visible_brand_and_configured_canonical():
    with TestClient(create_app(Settings(public_base_url=BASE))) as client:
        response = client.get("/?utm_source=example", headers={"host": "untrusted.example"})
    data = jsonld(response.text)
    site = [item for item in data if item.get("@type") == "WebSite"]
    assert site == [{"@context": "https://schema.org", "@type": "WebSite", "name": "ГРАФ", "url": BASE + "/"}]
    assert {item["@type"] for item in data} == {"WebSite", "SoftwareApplication", "FAQPage"}
    assert 'property="og:site_name" content="ГРАФ"' in response.text


@pytest.mark.parametrize("path", [GUIDE_PATH, QUALITY_GUIDE_PATH])
def test_guide_schema_matches_visible_article_and_has_no_executable_scripts(path):
    with TestClient(create_app(Settings(public_base_url=BASE))) as client:
        response = client.get(path + "?token=synthetic-secret", headers={"host": "untrusted.example"})
    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    data = jsonld(response.text)
    assert len(data) == 1
    article, breadcrumbs = data[0]["@graph"]
    heading = re.search(r"<h1>(.*?)</h1>", response.text, re.S).group(1)
    assert article == {
        "@type": "Article",
        "headline": heading,
        "mainEntityOfPage": BASE + path,
        "inLanguage": "ru",
        "author": {"@type": "Organization", "name": "Редакция ГРАФ"},
    }
    assert "редакция граф" in response.text.lower()
    assert breadcrumbs == {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Руководства", "item": BASE + "/guides"},
            {"@type": "ListItem", "position": 2, "name": heading, "item": BASE + path},
        ],
    }
    assert '<a href="/guides">Все руководства</a>' in response.text
    parser = Parser()
    parser.feed(response.text)
    assert parser.canonical == [BASE + path]
    assert parser.h1 == 1
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", response.text, re.S)
    assert len(scripts) == 1 and scripts[0][0].strip() == 'type="application/ld+json"'
    assert "synthetic-secret" not in json.dumps(data)
    assert "untrusted.example" not in json.dumps(data)
