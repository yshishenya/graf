from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from tests.contract.test_public_protocol_guide import Parser
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.content import (
    GUIDES_PATH,
    PUBLIC_CONTENT_PAGES,
    PUBLIC_CONTENT_SURFACES,
    ZOOM_GUIDE_PATH,
    ContentSection,
    content_for_section,
)


def test_hub_is_indexable_and_links_join_the_published_guides():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get(GUIDES_PATH + "?utm_source=example")
        assert response.status_code == 200
        parser = Parser()
        parser.feed(response.text)
        assert parser.h1 == 1 and parser.scripts == 0
        assert parser.canonical == ["https://rec.2brain.pro/guides"]
        assert parser.meta["og:url"] == parser.canonical[0]
        assert parser.meta["description"] == parser.meta["og:description"]
        assert "noindex" not in parser.meta.get("robots", "")
        assert "noindex" not in response.headers.get("x-robots-tag", "")
        assert "Руководства по записи" in response.text
        assert response.text.count('class="guide-card"') == 4
        first, second, third, zoom = PUBLIC_CONTENT_PAGES
        assert response.text.index(first.path) < response.text.index(second.path)
        assert response.text.index(third.path) < response.text.index(zoom.path)
        for link in parser.links:
            if link.startswith("#"):
                assert link[1:] in parser.ids
            else:
                assert client.get(link).status_code == 200
        for page in PUBLIC_CONTENT_PAGES:
            article = client.get(page.path)
            p = Parser()
            p.feed(article.text)
            assert GUIDES_PATH in p.links
            assert all(sibling.path in p.links for sibling in PUBLIC_CONTENT_PAGES if sibling != page and sibling.path != ZOOM_GUIDE_PATH)
            assert p.canonical == ["https://rec.2brain.pro" + page.path]
        xml = ElementTree.fromstring(client.get("/sitemap.xml").text)
        urls = [node.text for node in xml.findall("{*}url/{*}loc")]
        assert len(urls) == len(set(urls))
        for path in PUBLIC_CONTENT_SURFACES:
            assert urls.count("https://rec.2brain.pro" + path) == 1
        for empty in ("/news",):
            assert client.get(empty).status_code == 404
            assert "https://rec.2brain.pro" + empty not in urls
        landing = client.get("/").text
        footer = landing.split('class="footer-links"')[1].split("</div>")[0]
        assert footer.count('href="/guides"') == 1


def test_unpublished_sections_have_no_entries_or_measurement_surfaces():
    assert len(content_for_section(ContentSection.GUIDES)) == 4
    assert len(content_for_section(ContentSection.HELP)) == 1
    assert content_for_section(ContentSection.NEWS) == ()
    assert "/help" not in PUBLIC_CONTENT_SURFACES
    assert "/news" not in PUBLIC_CONTENT_SURFACES


@pytest.mark.parametrize(
    "path,surface",
    [
        ("/guides", "public_guides"),
        ("/guides/proverka-kachestva-rasshifrovki-vstrechi", "public_transcription_quality_guide"),
        ("/guides/zapis-vstrechi-na-mac-bez-bota", "public_mac_meeting_guide"),
    ],
)
def test_hub_and_recording_guide_preserve_existing_measurement(
    path,
    surface,
    client,
    postgres_seeded_database_url,
    monkeypatch,
    tmp_path,
):
    import asyncio
    import json

    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from twobrain_rec_server.public.analytics import PUBLIC_VISIT_ATTRIBUTION_COOKIE

    monkeypatch.setenv(
        "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE", str(tmp_path / "missing.json")
    )

    async def read_rows(table):
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(sa.text(f"select * from {table}"))
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()

    response = client.get(
        path + "?utm_source=example&utm_medium=organic&utm_campaign=protocol&token=synthetic-secret"
    )
    assert response.status_code == 200 and "<script" not in response.text
    assert PUBLIC_VISIT_ATTRIBUTION_COOKIE in response.cookies
    assert client.get(path).status_code == 200
    buckets = asyncio.run(read_rows("anonymous_page_aggregate_buckets"))
    assert len(buckets) == 1 and buckets[0]["visits"] == 2
    assert buckets[0]["surface"] == surface
    assert buckets[0]["landing_path"] == path
    assert buckets[0]["source"] == "example" and buckets[0]["campaign"] == "protocol"
    visits = asyncio.run(read_rows("public_visit_attributions"))
    assert len(visits) == 1
    assert visits[0]["landing_path"] == path and visits[0]["campaign"] == "protocol"
    assert "synthetic-secret" not in json.dumps([buckets, visits], default=str)
    client.get("/download")
    downloads = [
        row
        for row in asyncio.run(read_rows("anonymous_page_aggregate_buckets"))
        if row["surface"] == "public_download"
    ]
    assert len(downloads) == 1 and downloads[0]["landing_path"] == path
    assert downloads[0]["campaign"] == "protocol"
    client.app.state.settings.product_analytics_anonymous_aggregate_enabled = False
    assert client.get(path).status_code == 200
    guide_rows = [
        row
        for row in asyncio.run(read_rows("anonymous_page_aggregate_buckets"))
        if row["surface"] == surface
    ]
    assert guide_rows[0]["visits"] == 2
