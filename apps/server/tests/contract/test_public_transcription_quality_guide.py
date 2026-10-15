from xml.etree import ElementTree

from fastapi.testclient import TestClient

from tests.contract.test_public_protocol_guide import Parser
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.content import PUBLIC_CONTENT_PAGES, QUALITY_GUIDE_PATH


def test_quality_guide_is_indexable_and_marks_examples_without_product_accuracy_claim():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro"))) as client:
        response = client.get(QUALITY_GUIDE_PATH + "?utm_source=example&token=synthetic-secret")
        assert response.status_code == 200
        parser = Parser()
        parser.feed(response.text)
        assert parser.canonical == ["https://rec.2brain.pro" + QUALITY_GUIDE_PATH]
        assert parser.meta["og:url"] == parser.canonical[0]
        assert parser.meta["description"] == parser.meta["og:description"]
        assert parser.h1 == 1 and parser.scripts == 0
        assert "noindex" not in parser.meta.get("robots", "")
        assert "noindex" not in response.headers.get("x-robots-tag", "")
        assert "Все примеры учебные" in response.text
        assert "Имена, реплики и таймкоды ниже вымышлены" in response.text
        assert "не результат ГРАФ" in response.text
        assert "не приводится WER или процент точности ГРАФ" in response.text
        assert "Срок не согласован" in response.text
        assert "synthetic-secret" not in response.text
        external = [link for link in parser.links if link.startswith("https://")]
        assert set(external) == {
            "https://docs.cloud.google.com/speech-to-text/docs/multiple-voices",
            "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-custom-speech-evaluate-data#evaluate-word-error-rate-wer",
        }
        for link in parser.links:
            if link.startswith("#"):
                assert link[1:] in parser.ids
            elif not link.startswith("https://"):
                assert client.get(link).status_code == 200
        for page in PUBLIC_CONTENT_PAGES:
            if page.path != QUALITY_GUIDE_PATH:
                assert QUALITY_GUIDE_PATH in client.get(page.path).text
        urls = [node.text for node in ElementTree.fromstring(client.get("/sitemap.xml").text).findall("{*}url/{*}loc")]
        assert urls.count(parser.canonical[0]) == 1 and len(urls) == len(set(urls))
