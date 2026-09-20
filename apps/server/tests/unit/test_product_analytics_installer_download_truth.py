"""FR-019: фактическое скачивание установщика отличимо от нажатия кнопки (T054).

Кнопка на странице — это намерение, а скачивание — это факт: пакет действительно
уходит в браузер. Первый запуск приложения остаётся отдельной вехой, которую
может прислать только само приложение.
"""

from collections.abc import Iterator
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.event_catalog import (
    ANONYMOUS_AGGREGATE_SIGNAL_NAMES,
    FULL_ACTIVATION_FUNNEL,
    PRODUCT_ACTIVATION_EVENT_NAMES,
    PUBLIC_ACQUISITION_EVENT_NAMES,
    aggregate_signal_delivers_to_provider,
    anonymous_aggregate_signal_names,
    get_anonymous_aggregate_signal,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
)
from twobrain_rec_server.product_analytics.milestones import is_first_milestone_event
from twobrain_rec_server.public.downloads import is_installer_artifact

INSTALLER_CTA = "download_page_installer"
OPEN_APP_CTA = "download_page_open_app"
INSTALLER_SIGNAL = "public_installer_download_aggregate"
INSTALLER_CLICK_EVENT = "public_installer_download_clicked"
FIRST_LAUNCH_MILESTONE = "desktop_first_opened"
IDENTIFIER_FIELD_NAMES = (
    "session_id",
    "anonymous_id",
    "cookie",
    "user_agent",
    "device_fingerprint",
    "yclid",
)


class _DownloadPageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: dict[str, dict[str, str | None]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        cta = attributes.get("data-analytics-cta")
        if cta:
            self.links[cta] = attributes


def _page_links(client: TestClient) -> dict[str, dict[str, str | None]]:
    response = client.get("/download")
    assert response.status_code == 200
    parser = _DownloadPageLinks()
    parser.feed(response.text)
    return parser.links


@pytest.fixture(scope="module")
def download_page_client() -> Iterator[TestClient]:
    # Рендер страницы не зависит от базы данных и не ходит в сеть.
    yield TestClient(create_app(Settings()))


def test_the_page_separates_the_button_from_the_app_handoff(
    download_page_client: TestClient,
) -> None:
    links = _page_links(download_page_client)

    installer = links[INSTALLER_CTA]
    assert "download" in installer
    assert str(installer["href"]).startswith("/static/public/downloads/")
    assert installer["data-analytics-target"] == "installer_package"

    # Кнопка открытия приложения — отдельный элемент со ссылкой атрибуции.
    open_app = links[OPEN_APP_CTA]
    assert str(open_app["href"]).startswith("grafrec://attribution?")
    assert str(open_app["data-graf-attribution-id"]).startswith("graf_attr_")
    assert open_app["href"] != installer["href"]


def test_the_installer_package_really_reaches_the_browser(
    download_page_client: TestClient,
) -> None:
    installer_url = str(_page_links(download_page_client)[INSTALLER_CTA]["href"])

    download = download_page_client.get(installer_url)

    # Установщик реально отдаётся: это факт скачивания, а не нажатие кнопки.
    assert download.status_code == 200
    assert len(download.content) > 0
    assert len(download.content) == int(download.headers["content-length"])


def test_only_the_installer_file_counts_as_a_delivery() -> None:
    """FR-019: посредник отдачи считает установщик, а не любой файл статики."""
    assert is_installer_artifact("downloads/graf.pkg") is True
    assert is_installer_artifact("/downloads/GRAF-2026.09.18.1.dmg") is True

    assert is_installer_artifact("landing.css") is False
    assert is_installer_artifact("fonts/onest-latin.woff2") is False
    assert is_installer_artifact("downloads/appcast.xml") is False
    assert is_installer_artifact("cabinet/graf.pkg") is False
    assert is_installer_artifact("") is False
    assert is_installer_artifact(None) is False


def test_a_broken_counter_never_breaks_the_download() -> None:
    """FR-058: недоступная запись счётчика — это пробел измерения, не отказ.

    Приложение собрано с базой, до которой нельзя дойти, поэтому запись счётчика
    заведомо не проходит. Файл при этом обязан уйти в браузер целиком: измерение
    не имеет права задерживать или ломать скачивание.
    """
    settings = Settings(
        database_url="postgresql+asyncpg://nobody:nobody@127.0.0.1:1/absent",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
    )
    client = TestClient(create_app(settings))

    installer_url = str(_page_links(client)[INSTALLER_CTA]["href"])
    download = client.get(installer_url)

    assert download.status_code == 200
    assert len(download.content) > 0
    assert len(download.content) == int(download.headers["content-length"])


def test_the_installer_download_aggregate_is_anonymous() -> None:
    signal = get_anonymous_aggregate_signal(INSTALLER_SIGNAL)

    assert INSTALLER_SIGNAL in ANONYMOUS_AGGREGATE_SIGNAL_NAMES
    assert INSTALLER_SIGNAL in anonymous_aggregate_signal_names()
    assert signal.delivery_mode == "anonymous_aggregate"
    assert signal.posthog_destination == "none"
    assert signal.yandex_destination == "none"
    assert aggregate_signal_delivers_to_provider(INSTALLER_SIGNAL) is False
    assert tuple(signal.allowed_fields) == ANONYMOUS_AGGREGATE_ALLOWED_FIELDS
    for identifier in IDENTIFIER_FIELD_NAMES:
        assert identifier not in signal.allowed_fields


def test_the_first_launch_stays_a_separate_milestone_from_the_click() -> None:
    # Клик по кнопке скачивания — публичное событие, а не веха активации.
    assert INSTALLER_CLICK_EVENT in PUBLIC_ACQUISITION_EVENT_NAMES
    assert INSTALLER_CLICK_EVENT not in PRODUCT_ACTIVATION_EVENT_NAMES
    assert is_first_milestone_event(INSTALLER_CLICK_EVENT) is False

    # Первый запуск приложения — веха, и её место в воронке сразу после клика.
    assert FIRST_LAUNCH_MILESTONE in PRODUCT_ACTIVATION_EVENT_NAMES
    assert FIRST_LAUNCH_MILESTONE in FULL_ACTIVATION_FUNNEL
    assert is_first_milestone_event(FIRST_LAUNCH_MILESTONE) is True
    assert (INSTALLER_CLICK_EVENT, *PRODUCT_ACTIVATION_EVENT_NAMES) == FULL_ACTIVATION_FUNNEL
    assert (
        FULL_ACTIVATION_FUNNEL.index(FIRST_LAUNCH_MILESTONE)
        == FULL_ACTIVATION_FUNNEL.index(INSTALLER_CLICK_EVENT) + 1
    )
