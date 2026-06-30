from pathlib import Path

import pytest

from tests.fixtures.cabinet_components import COMPONENT_STATE_NAMES
from twobrain_rec_server.cabinet.templates import (
    CABINET_STATIC_URL,
    get_cabinet_templates,
    render_template,
    trusted_component_html,
)

SERVER_ROOT = Path(__file__).resolve().parents[2] / "src" / "twobrain_rec_server"
CABINET_CSS = SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.css"
CABINET_WEB = SERVER_ROOT / "cabinet" / "web.py"
CABINET_RENDERING = SERVER_ROOT / "cabinet" / "rendering.py"
CABINET_TEMPLATES = SERVER_ROOT / "cabinet" / "templates"


def test_cabinet_template_package_smoke_renders_base_shell() -> None:
    html = render_template(
        "cabinet/base.html",
        title="Проверка",
        surface_mode="standalone_browser",
        content=trusted_component_html("<main>ok</main>", source="cabinet.shell"),
    )

    assert "<title>Проверка - GRAF</title>" in html
    assert '<meta name="robots" content="noindex,nofollow">' in html
    assert f'href="{CABINET_STATIC_URL}/favicon.ico"' in html
    assert f'href="{CABINET_STATIC_URL}/favicon-32.png"' in html
    assert f'href="{CABINET_STATIC_URL}/apple-touch-icon.png"' in html
    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in html
    assert '<meta name="htmx-config" content=\'{"allowEval":false,"allowScriptTags":false}\'' in html
    assert f'src="{CABINET_STATIC_URL}/htmx-2.0.10.min.js"' in html
    assert f'src="{CABINET_STATIC_URL}/cabinet.js?v=' in html
    assert "<main>ok</main>" in html


def test_trusted_component_html_requires_reviewed_source() -> None:
    html = trusted_component_html("<main>ok</main>", source="cabinet.shell")

    assert "<main>ok</main>" in str(html)
    with pytest.raises(ValueError):
        trusted_component_html("<main>unsafe</main>", source="local.page")


def test_cabinet_html_trust_boundaries_are_guarded() -> None:
    web_source = CABINET_WEB.read_text()
    rendering_source = CABINET_RENDERING.read_text()
    assert "from markupsafe import Markup" not in web_source
    assert "Markup(" not in web_source
    assert "def render_meeting_list_page(" not in web_source
    assert "def _render_meeting_row(" not in web_source
    assert "def render_meeting_list_page(" in rendering_source

    safe_templates = [
        path.relative_to(CABINET_TEMPLATES).as_posix()
        for path in CABINET_TEMPLATES.rglob("*.html")
        if "|safe" in path.read_text()
    ]
    assert safe_templates == ["cabinet/components/icons.html"]


def test_cabinet_templates_autoescape_untrusted_values() -> None:
    html = render_template(
        "cabinet/base.html",
        title="<script>alert(1)</script>",
        surface_mode="standalone_browser",
        content="<strong>not trusted</strong>",
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<strong>not trusted</strong>" not in html
    assert "&lt;strong&gt;not trusted&lt;/strong&gt;" in html


def test_cabinet_icon_macro_uses_lucide_style_contract() -> None:
    template = get_cabinet_templates().from_string(
        '{% import "cabinet/components/icons.html" as icons %}{{ icons.icon("trash") }}'
    )

    html = template.render()

    assert 'data-icon="trash"' in html
    assert 'viewBox="0 0 24 24"' in html
    assert 'stroke-width="2"' in html
    assert "currentColor" in html


def test_cabinet_css_locks_token_radius_focus_and_icon_baseline() -> None:
    css = CABINET_CSS.read_text()

    assert "--bg:" in css
    assert "--surface:" in css
    assert "--accent:" in css
    assert "border-radius: 8px;" in css
    assert ":focus-visible" in css
    assert "outline: 2px solid" in css
    assert ".ui-icon" in css
    assert "stroke-width: 2;" in css


def test_primitive_component_catalog_covers_controls_and_states() -> None:
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/primitives.html" as ui %}
        {{ ui.button("Сохранить") }}
        {{ ui.button("Удалить", variant="danger", destructive=True) }}
        {{ ui.button("Загрузка", loading=True) }}
        {{ ui.icon_button("trash", "Удалить запись", destructive=True) }}
        {{ ui.link("Открыть", "/meetings") }}
        {{ ui.input("q", "Поиск", placeholder="Найти") }}
        {{ ui.input("email", "Email", error="Нужен email") }}
        {{ ui.select("status", "Статус", options, "ready") }}
        {{ ui.checkbox("selected", "Выбрать", checked=True) }}
        {{ ui.chip("Готово", "selected") }}
        {{ ui.badge("Ошибка", "error") }}
        {{ ui.tab("Итоги", "panel-outcomes", selected=True) }}
        {{ ui.tooltip("Подсказка", "Только безопасная метаинформация") }}
        {{ ui.loader("Загрузка записей") }}
        {{ ui.text("Текст", "muted") }}
        {{ ui.status_label("Недоступно", "unavailable") }}
        """
    )

    html = template.render(options=[("ready", "Готово"), ("processing", "В обработке")])

    for class_name in [
        "cabinet-button",
        "cabinet-icon-button",
        "cabinet-link",
        "cabinet-field",
        "cabinet-checkbox",
        "cabinet-chip",
        "cabinet-badge",
        "cabinet-tab",
        "cabinet-tooltip",
        "cabinet-loader",
        "cabinet-text",
        "cabinet-status",
    ]:
        assert class_name in html
    for state in ["normal", "loading", "selected", "destructive", "error", "unavailable"]:
        assert f'data-state="{state}"' in html
    assert 'role="tab"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-label="Удалить запись"' in html


def test_primitive_components_support_long_russian_overflow_text() -> None:
    long_label = (
        "Очень длинное безопасное русское название встречи без приватного содержания "
        "для проверки переносов и обрезки внутри компактного элемента интерфейса"
    )
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/primitives.html" as ui %}
        {{ ui.button(long_label) }}
        {{ ui.text(long_label, overflow=True) }}
        """
    )

    html = template.render(long_label=long_label)

    assert long_label in html
    assert "cabinet-text--overflow" in html
    assert f'title="{long_label}"' in html
    assert "overflow-wrap: anywhere;" in CABINET_CSS.read_text()
    assert "overflow_text" in COMPONENT_STATE_NAMES
