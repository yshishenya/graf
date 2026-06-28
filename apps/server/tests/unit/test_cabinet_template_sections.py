from pathlib import Path

from markupsafe import Markup

from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.cabinet.templates import get_cabinet_templates

SERVER_ROOT = Path(__file__).resolve().parents[2] / "src" / "twobrain_rec_server"
CABINET_CSS = SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.css"


def test_section_component_catalog_covers_composed_cabinet_regions() -> None:
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/sections.html" as sections %}
        {{ sections.sidebar_navigation(nav_items, active="meetings") }}
        {{ sections.workspace_header("Команда 2brain", "Онлайн-кабинет", "2B") }}
        {{ sections.meeting_row("Проектный синк", "/meetings/1", "Готово", "audio", "26 июн", selected=True) }}
        {{ sections.selection_toolbar(2, 5, destructive_enabled=True) }}
        {{ sections.playback_controls("Запись встречи", available=True, duration="12:40") }}
        {{ sections.detail_side_panel("Доступ", "Только безопасные сведения") }}
        {{ sections.confirmation_dialog("Удалить запись?", "Действие ограничено GRAF") }}
        {{ sections.status_banner("Готово", "Запись доступна", "normal") }}
        {{ sections.empty_state("Нет записей", "Создайте первую запись") }}
        {{ sections.unavailable_state("Сервер недоступен", "Запись остается локальной") }}
        {{ sections.auth_form("Вход", "/login/email/start") }}
        """
    )

    html = template.render(
        nav_items=[
            {"id": "meetings", "href": "/meetings", "icon": "audio", "label": "Встречи", "count": 5},
            {"id": "account", "href": "/account", "icon": "bookmark", "label": "Аккаунт", "count": None},
        ]
    )

    for class_name in [
        "cabinet-sidebar-nav",
        "cabinet-workspace-header",
        "cabinet-meeting-row",
        "cabinet-selection-toolbar",
        "cabinet-playback-controls",
        "cabinet-detail-panel",
        "cabinet-confirmation-dialog",
        "cabinet-banner",
        "cabinet-empty",
        "cabinet-unavailable",
        "cabinet-auth-form",
    ]:
        assert class_name in html
    assert 'aria-label="Навигация кабинета"' in html
    assert 'role="toolbar"' in html
    assert 'role="dialog"' in html
    assert 'data-state="selected"' in html
    assert 'data-state="destructive"' in html
    assert "Запись остается локальной" in html


def test_cabinet_shell_macro_renders_shared_sidebar_contract() -> None:
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/sections.html" as sections %}
        {{ sections.cabinet_shell(navigation, embedded=embedded, content=content, static_url=cabinet_static_url) }}
        """
    )
    navigation = view_models.CabinetNavigationModel(
        active="meetings",
        items=(
            view_models.CabinetNavigationItem("search", "Поиск", "#", "search", enabled=False),
            view_models.CabinetNavigationItem("meetings", "Мои встречи", "/meetings", "calendar-days"),
            view_models.CabinetNavigationItem(
                "settings",
                "Настройки",
                "/settings/integrations/calendar",
                "settings",
            ),
        ),
    )

    html = template.render(
        cabinet_static_url="/static/cabinet",
        navigation=navigation,
        embedded=False,
        content=Markup('<main class="cabinet-main" id="content">Контент</main>'),
    )

    assert html.count("data-cabinet-shell") == 1
    assert '<aside class="sidebar" id="cabinet-sidebar" data-cabinet-navigation>' in html
    assert 'aria-label="Навигация кабинета"' in html
    assert html.count('aria-current="page"') == 1
    assert 'href="/meetings"' in html
    assert 'href="/settings/integrations/calendar"' in html
    assert 'aria-disabled="true" tabindex="-1"' in html
    assert 'src="/static/cabinet/graf-wordmark-dark.png"' in html
    assert 'data-cabinet-rail-toggle' in html
    assert "Пробный период 7 дней" in html
    assert '<main class="cabinet-main" id="content">Контент</main>' in html


def test_section_css_covers_interaction_and_overflow_states() -> None:
    css = CABINET_CSS.read_text()

    for marker in [
        '.cabinet-button[data-state="disabled"]',
        '.cabinet-button[data-state="loading"]',
        ".cabinet-button.is-destructive",
        ".cabinet-tab.is-selected",
        ".cabinet-tooltip:focus-within",
        ".cabinet-text--overflow",
        ".cabinet-playback-controls[data-state=\"unavailable\"]",
        ".cabinet-confirmation-dialog[data-state=\"destructive\"]",
    ]:
        assert marker in css


def test_section_csrf_field_renders_only_when_token_is_available() -> None:
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/sections.html" as sections %}
        {{ sections.csrf_field(token) }}
        {{ sections.csrf_field(None) }}
        """
    )

    html = template.render(token='safe-token"><script>')

    assert 'name="csrf_token"' in html
    assert "safe-token&#34;&gt;&lt;script&gt;" in html
    assert html.count('name="csrf_token"') == 1
