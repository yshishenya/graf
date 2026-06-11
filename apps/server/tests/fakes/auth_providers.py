from datetime import datetime
from uuid import uuid4

from twobrain_rec_server.auth.providers.base import (
    ProviderAdapter,
    ProviderCredentials,
    ProviderHttpClient,
    ProviderIdentity,
)


class StaticProviderAdapter(ProviderAdapter):
    """Deterministic provider adapter for tests."""

    def __init__(
        self,
        provider: str,
        *,
        label: str,
        auth_base_url: str,
        default_subject: str | None = None,
        requires_email: bool = False,
    ) -> None:
        self.provider = provider
        self.label = label
        self.auth_base_url = auth_base_url
        self.requires_email = requires_email
        self.accepts_direct_callback_claims = True
        self._default_subject = default_subject or f"{provider}:{uuid4()}"

    def parse_callback(self, query: dict[str, str], *, expected_state: str) -> ProviderIdentity:
        subject = query.get("code") or query.get("id") or self._default_subject
        return super().parse_callback(query | {"code": subject}, expected_state=expected_state)

    def verify_callback(
        self,
        query: dict[str, str],
        *,
        expected_state: str,
        credentials: ProviderCredentials,
        http_client: ProviderHttpClient,
        now: datetime | None = None,
    ) -> ProviderIdentity:
        _ = credentials, http_client, now
        return self.parse_callback(query, expected_state=expected_state)


def fake_provider_map() -> dict[str, ProviderAdapter]:
    return {
        "yandex": StaticProviderAdapter(
            "yandex",
            label="Yandex Test",
            auth_base_url="https://test.example/yandex",
            default_subject="yandex:test-user-001",
            requires_email=True,
        ),
        "vk": StaticProviderAdapter(
            "vk",
            label="VK Test",
            auth_base_url="https://test.example/vk",
            default_subject="vk:test-user-002",
            requires_email=True,
        ),
        "telegram": StaticProviderAdapter(
            "telegram",
            label="Telegram Test",
            auth_base_url="https://test.example/telegram",
            default_subject="telegram:test-user-003",
            requires_email=False,
        ),
    }
