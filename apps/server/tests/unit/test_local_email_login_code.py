from unittest.mock import patch

from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _issue_email_login_code
from twobrain_rec_server.config import Settings


def test_local_email_login_uses_fixed_code_only_for_local_http_auth() -> None:
    settings = Settings(
        env="development",
        local_http_auth_cookie_enabled=True,
        local_email_login_code="000000",
    )

    assert _issue_email_login_code(settings) == "000000"


def test_fixed_local_email_login_code_is_ignored_outside_local_http_auth() -> None:
    settings = Settings(
        env="development",
        local_http_auth_cookie_enabled=False,
        local_email_login_code="000000",
    )

    with patch(
        "twobrain_rec_server.cabinet.web_routes.auth_email_flow.secrets.randbelow",
        return_value=123456,
    ):
        assert _issue_email_login_code(settings) == "123456"
