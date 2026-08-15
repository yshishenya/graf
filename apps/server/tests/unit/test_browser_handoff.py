from cryptography.fernet import Fernet

from twobrain_rec_server.auth.browser_handoff import (
    open_desktop_billing_session,
    seal_desktop_billing_session,
)


def test_desktop_billing_handoff_seals_session_without_exposing_bearer() -> None:
    key = Fernet.generate_key()
    token = "desktop-session-token"

    sealed = seal_desktop_billing_session(token, key=key)

    assert token not in sealed
    assert open_desktop_billing_session(sealed, key=key) == token


def test_desktop_billing_handoff_rejects_wrong_key_and_tampering() -> None:
    key = Fernet.generate_key()
    sealed = seal_desktop_billing_session("desktop-session-token", key=key)

    assert open_desktop_billing_session(sealed, key=Fernet.generate_key()) is None
    assert open_desktop_billing_session(sealed[:-1] + "x", key=key) is None
