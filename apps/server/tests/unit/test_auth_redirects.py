from __future__ import annotations

import pytest

from twobrain_rec_server.auth.redirects import safe_first_party_path


@pytest.mark.parametrize(
    "value",
    [
        "https://attacker.example",
        "//attacker.example",
        "/\\attacker.example",
        "/%5cattacker.example",
        "/%2fattacker.example",
        "/meetings\r\nLocation: https://attacker.example",
        "javascript:alert(1)",
    ],
)
def test_safe_first_party_path_rejects_browser_authority_forms(value: str) -> None:
    assert safe_first_party_path(value) is None


def test_safe_first_party_path_preserves_local_path_query_and_fragment() -> None:
    assert safe_first_party_path(" /desktop/meetings?tab=mine#today ") == (
        "/desktop/meetings?tab=mine#today"
    )
