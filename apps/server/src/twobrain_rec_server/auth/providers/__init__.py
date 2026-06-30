from collections.abc import Iterable

from .base import (
    PROVIDER_TELEGRAM,
    PROVIDER_VK,
    PROVIDER_YANDEX,
    ProviderAdapter,
    ProviderProfile,
    TelegramAdapter,
    VkAdapter,
    YandexAdapter,
    normalize_provider,
)
from .base import (
    SUPPORTED_PROVIDER_IDS as SUPPORTED_PROVIDER_IDS,
)


def build_provider_registry() -> dict[str, ProviderAdapter]:
    return {
        PROVIDER_YANDEX: YandexAdapter(),
        PROVIDER_VK: VkAdapter(),
        PROVIDER_TELEGRAM: TelegramAdapter(),
    }


def get_provider_adapter(provider: str) -> ProviderAdapter:
    registry = build_provider_registry()
    return registry[normalize_provider(provider)]


def provider_profiles(adapters: Iterable[ProviderAdapter] | None = None) -> list[ProviderProfile]:
    adapters = list(adapters or build_provider_registry().values())
    return [
        ProviderProfile(
            provider=adapter.provider,
            enabled=True,
            label=adapter.label,
            requires_email=adapter.requires_email,
        )
        for adapter in adapters
    ]
