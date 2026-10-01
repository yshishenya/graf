from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

PATH = "/guides/protokol-vstrechi-iz-zapisi"


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = []
        self.meta = {}
        self.links = []
        self.ids = set()
        self.h1 = 0
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "script":
            self.scripts += 1
        if tag == "a":
            self.links.append(a["href"])
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical.append(a["href"])
        if tag == "meta":
            self.meta[a.get("name") or a.get("property")] = a.get("content", "")


def test_protocol_guide_is_indexable_and_links_resolve_without_tracking():
    with TestClient(create_app(Settings(public_base_url="https://rec.2brain.pro", public_analytics_enabled=True))) as c:
        r = c.get(PATH + "?utm_source=example")
        assert r.status_code == 200
        p = Parser()
        p.feed(r.text)
        assert p.canonical == ["https://rec.2brain.pro" + PATH]
        assert p.meta["og:url"] == p.canonical[0]
        assert p.meta["description"] == p.meta["og:description"]
        assert "учебный диалог" in p.meta["description"]
        assert "Протокол встречи из записи: пример решений и задач — ГРАФ" in r.text
        assert p.h1 == 1 and p.scripts == 0
        assert "noindex" not in p.meta.get("robots", "")
        assert "noindex" not in r.headers.get("x-robots-tag", "")
        for link in set(p.links):
            if link.startswith("#"):
                assert link[1:] in p.ids
            else:
                assert c.get(link).status_code == 200
        assert "/guides/zapis-vstrechi-na-mac-bez-bota" in p.links
        sitemap = ElementTree.fromstring(c.get("/sitemap.xml").text)
        urls = [x.text for x in sitemap.findall("{*}url/{*}loc")]
        assert urls.count(p.canonical[0]) == 1
        assert "https://rec.2brain.pro/guides/zapis-vstrechi-na-mac-bez-bota" in urls
        assert len(urls) == len(set(urls))


def test_example_keeps_unknowns_conditions_and_plaintext_template_order():
    template = Path(__file__).parents[2] / "src/twobrain_rec_server/public/templates/public/meeting_protocol_guide.html"
    text = template.read_text()
    assert "диалог, участники и ситуация вымышлены" in text
    assert "Протокол составлен вручную" in text
    assert text.index("Это не результат обработки записи в ГРАФ") < text.index('id="dialogue"')
    alexey = text.split('id="task-alexey"')[1].split("</div>")[0]
    irina = text.split('id="task-irina"')[1].split("</div>")[0]
    safari = text.split('id="task-safari"')[1].split("</div>")[0]
    assert "13 ноября 2026 года, до 15:00 по Москве" in alexey
    assert "После получения макета" in irina and "Не согласован" in irina
    assert "15:00" not in irina and "Не назначен" in safari
    assert "предложено Алексеем, дата не утверждена" in text
    copy = text.split("<pre>")[1].split("</pre>")[0]
    headings = ["Протокол встречи\nДата:", "Краткий итог:", "Решения:", "Задачи:", "Открытые вопросы:", "Предложения без решения:", "Уточнения после встречи:"]
    offsets = [copy.index(h) for h in headings]
    assert offsets == sorted(offsets)
    assert "[имя / не назначен]" in copy and "[дата и время / не согласован]" in copy
    assert "<" not in copy
