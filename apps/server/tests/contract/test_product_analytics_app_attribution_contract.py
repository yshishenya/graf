"""FR-022: приложение связывает кампанию с аккаунтом при входе.

Сквозной путь приложения проверяется целиком на настоящих маршрутах: страница
загрузки создает мост атрибуции, приложение запоминает ссылку, встроенный
кабинет открывает маршрут входа с метками кампании, и метки вместе с
идентификатором моста становятся атрибутом записи о клиенте.

Вход существующего аккаунта — это и есть путь, которым приложение подключает
аккаунт, поэтому проверяется именно он: регистрация здесь только создает
аккаунт. Правило «первая метка не перезаписывается» принадлежит хранилищу
(``ON CONFLICT (account_id) DO NOTHING``) и проверяется вторым входом.
"""

from __future__ import annotations

import asyncio
import json
import re
from html.parser import HTMLParser
from uuid import uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.cabinet.web_routes import auth_email_flow as auth_email_flow_module
from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
)
from twobrain_rec_server.public.analytics import PUBLIC_VISIT_ATTRIBUTION_COOKIE

ACQUISITION_TABLE = "client_acquisition_attributes"
BRIDGE_ID_PREFIX = "graf_attr_"
BROWSER_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    )
}


def _rows(database_url: str, table: str) -> list[dict]:
    async def _read() -> list[dict]:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    sa.text(f'select * from "{table}" order by "created_at"')
                )
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()

    return asyncio.run(_read())


class _OpenAppLink(HTMLParser):
    """Ссылка, которую страница загрузки отдает приложению."""

    def __init__(self) -> None:
        super().__init__()
        self.bridge_id: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        if attributes.get("data-analytics-cta") == "download_page_open_app":
            value = attributes.get("data-graf-attribution-id")
            if value:
                self.bridge_id = str(value)


def _open_app_bridge_id(html: str) -> str:
    parser = _OpenAppLink()
    parser.feed(html)
    assert parser.bridge_id is not None, "the download page did not offer the app link"
    assert parser.bridge_id.startswith(BRIDGE_ID_PREFIX)
    return parser.bridge_id


def _start_email_step(client: TestClient, path: str, email: str) -> tuple[str, str]:
    """Открывает шаг входа или регистрации и возвращает его состояние и код."""
    started = client.post(
        path,
        data={"email": email, "next": "/meetings"},
        headers=BROWSER_HEADERS,
    )
    assert started.status_code == 200, started.text[:400]
    state_match = re.search(r'name="state" value="([^"]+)"', started.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
    assert state_match is not None, "the step did not publish its state"
    assert code_match is not None, "the step did not publish its local code"
    cookie_name = auth_email_flow_module._email_auth_browser_cookie_name(
        state_nonce=state_match.group(1),
        secure=True,
    )
    browser_nonce = started.cookies.get(cookie_name)
    assert browser_nonce is not None
    client.cookies.set(cookie_name, browser_nonce, domain="testserver.local", path="/")
    return state_match.group(1), code_match.group(1)


def _complete_signup(client: TestClient, email: str) -> None:
    state, code = _start_email_step(client, "/sign-up/email/start", email)
    completed = client.post(
        "/sign-up/email/verify",
        data={"email": email, "code": code, "state": state, "next": "/meetings"},
        headers=BROWSER_HEADERS,
        follow_redirects=False,
    )
    assert completed.status_code == 303, completed.text[:400]


def _sign_in(client: TestClient, email: str, *, app_query: dict[str, str] | None = None) -> None:
    """Вход существующего аккаунта — так же, как его открывает приложение."""
    state, code = _start_email_step(client, "/login/email/start", email)
    completed = client.post(
        "/login/email/verify",
        params=app_query or {},
        data={"email": email, "code": code, "state": state, "next": "/meetings"},
        headers=BROWSER_HEADERS,
        follow_redirects=False,
    )
    assert completed.status_code == 303, completed.text[:400]


def _new_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


def _forget_visit_cookie(client: TestClient) -> None:
    """Снимает cookie визита: у встроенного входа своего визита нет."""
    if PUBLIC_VISIT_ATTRIBUTION_COOKIE in client.cookies:
        client.cookies.delete(
            PUBLIC_VISIT_ATTRIBUTION_COOKIE, domain="testserver.local", path="/"
        )
    assert PUBLIC_VISIT_ATTRIBUTION_COOKIE not in client.cookies


def _drop_attribute_rows(database_url: str) -> None:
    """Оставляет аккаунт без записи атрибута: так выглядит первый вход.

    Аккаунт, созданный до появления атрибуции, строки не имеет — и именно для
    него FR-022 требует записать кампанию при входе.
    """

    async def _delete() -> None:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                await connection.execute(sa.text(f'delete from "{ACQUISITION_TABLE}"'))
        finally:
            await engine.dispose()

    asyncio.run(_delete())


def _account_without_attribute(client: TestClient, database_url: str, prefix: str) -> str:
    """Создает настоящий аккаунт и убирает его первую запись атрибута."""
    email = _new_email(prefix)
    _complete_signup(client, email)
    _forget_visit_cookie(client)
    _drop_attribute_rows(database_url)
    assert _rows(database_url, ACQUISITION_TABLE) == []
    return email


def test_the_app_link_of_the_download_page_becomes_the_campaign_of_the_account(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-022: ссылка → вход в кабинет → запись о клиенте."""
    campaign = f"273_app_{uuid4().hex[:8]}"
    download_page = client.get(
        "/download",
        params={
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": campaign,
            "utm_content": "creative_app",
        },
        headers=BROWSER_HEADERS,
    )
    assert download_page.status_code == 200
    # Приложение получает идентификатор атрибуции при первом запуске: страница
    # загрузки выдает настоящую ссылку с настоящим мостом (FR-022).
    bridge_id = _open_app_bridge_id(download_page.text)

    # Аккаунт уже существует и записи атрибута не имеет: проверяется именно
    # вход, а не регистрация.
    email = _account_without_attribute(client, postgres_seeded_database_url, "app-handoff")

    # Приложение открывает встроенный вход с метками кампании и мостом: тот же
    # набор параметров собирает ``ProductAttributionHandoff.signInQueryItems``.
    _sign_in(
        client,
        email,
        app_query={
            "graf_attribution_ref": bridge_id,
            "graf_attribution_fallback": "1",
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": campaign,
            "utm_content": "creative_app",
        },
    )

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1, "the sign-in did not record exactly one attribute"
    attribute = rows[0]
    assert attribute["source"] == "yandex_direct"
    assert attribute["medium"] == "cpc"
    assert attribute["campaign"] == campaign
    assert attribute["content"] == "creative_app"
    # Идентификатор моста сохранен в записи о клиенте (FR-022).
    assert attribute["graf_attribution_id"] == bridge_id
    assert attribute["attribution_rule"] == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert attribute["attribution_confidence"] == "linked"


def test_the_bridge_alone_is_enough_to_attach_the_campaign_of_the_visit(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-022: приложение может передать только идентификатор моста."""
    campaign = f"273_bridge_{uuid4().hex[:8]}"
    download_page = client.get(
        "/download",
        params={"utm_source": "yandex_direct", "utm_campaign": campaign},
        headers=BROWSER_HEADERS,
    )
    assert download_page.status_code == 200
    bridge_id = _open_app_bridge_id(download_page.text)

    email = _account_without_attribute(client, postgres_seeded_database_url, "bridge-only")

    _sign_in(client, email, app_query={"graf_attribution_ref": bridge_id})

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    assert rows[0]["campaign"] == campaign
    assert rows[0]["graf_attribution_id"] == bridge_id


def test_a_forged_cookie_without_a_durable_visit_row_cannot_attach_campaign(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """A valid-looking client cookie is not an authentication capability."""
    email = _account_without_attribute(client, postgres_seeded_database_url, "forged-cookie")
    forged = {
        "v": 1,
        "utm_source": "forged_source",
        "utm_medium": "cpc",
        "utm_campaign": "forged_campaign",
        "landing_path": "/download",
        "first_seen_at": "2026-09-18T12:00:00+00:00",
        "attribution_ref": "graf_visit_0123456789abcdef",
    }
    client.cookies.set(
        PUBLIC_VISIT_ATTRIBUTION_COOKIE,
        json.dumps(forged, separators=(",", ":")),
        domain="testserver.local",
        path="/",
    )

    _sign_in(client, email)

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    assert rows[0]["attribution_confidence"] == "unknown"
    assert rows[0]["campaign"] is None
    assert rows[0]["graf_attribution_id"] is None


def test_a_second_sign_in_never_rewrites_the_first_campaign(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-022: первая метка остается, второй вход ее не перезаписывает."""
    first_campaign = f"273_app_first_{uuid4().hex[:8]}"
    second_campaign = f"273_app_second_{uuid4().hex[:8]}"
    first_bridge = _open_app_bridge_id(
        client.get(
            "/download",
            params={"utm_source": "yandex_direct", "utm_campaign": first_campaign},
            headers=BROWSER_HEADERS,
        ).text
    )
    second_bridge = _open_app_bridge_id(
        client.get(
            "/download",
            params={"utm_source": "vk", "utm_campaign": second_campaign},
            headers=BROWSER_HEADERS,
        ).text
    )

    email = _account_without_attribute(client, postgres_seeded_database_url, "app-repeat")
    _sign_in(client, email, app_query={"graf_attribution_ref": first_bridge})

    first_rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(first_rows) == 1
    assert first_rows[0]["campaign"] == first_campaign

    _sign_in(
        client,
        email,
        app_query={"graf_attribution_ref": second_bridge, "utm_campaign": second_campaign},
    )

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1, "a second sign-in created a second attribute"
    assert rows[0]["campaign"] == first_campaign
    assert rows[0]["graf_attribution_id"] == first_bridge
    assert rows[0]["campaign"] != second_campaign


def test_a_sign_in_without_a_campaign_is_unknown_and_never_direct(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-022, FR-024: вход без кампании остается неизвестным."""
    email = _account_without_attribute(client, postgres_seeded_database_url, "app-unknown")

    _sign_in(client, email)

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    assert rows[0]["attribution_confidence"] == "unknown"
    assert rows[0]["attribution_confidence"] != "direct"
    for name in ("source", "medium", "campaign", "content", "term", "graf_attribution_id"):
        assert rows[0][name] is None, name
