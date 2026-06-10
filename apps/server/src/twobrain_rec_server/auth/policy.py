from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.providers import SUPPORTED_PROVIDER_IDS, build_provider_registry
from twobrain_rec_server.auth.providers.base import ProviderProfile
from twobrain_rec_server.db.models import WorkspaceAuthPolicy, WorkspaceConsentCopy


@dataclass(frozen=True, slots=True)
class AuthPolicySnapshot:
    workspace_id: UUID
    providers: list[ProviderProfile]
    allow_provider_self_enrollment: bool
    require_ru_local: bool
    residency_region_tag: str
    consent_text_version: str
    consent_language: str
    consent_content_markdown: str


def default_ru_consent_copy(*, residency_region_tag: str) -> str:
    return (
        "Вход через выбранного провайдера использует идентификатор аккаунта, имя профиля "
        "и, если провайдер передал их как подтвержденные, email или телефон. 2brain Rec "
        f"сохраняет эти поля, сессию, устройство и аудит в рабочей области; для RU-local "
        f"политики хранение ограничено регионом `{residency_region_tag}`. Сырые OAuth "
        "токены и полный payload провайдера не сохраняются в логах."
    )


def _provider_toggle(policy: WorkspaceAuthPolicy, provider: str) -> bool:
    mapping = {
        "yandex": policy.allow_yandex,
        "vk": policy.allow_vk,
        "telegram": policy.allow_telegram,
        "tid": policy.allow_tid,
        "sber_id": policy.allow_sber_id,
        "mts_id": policy.allow_mts_id,
        "esia": policy.allow_esia,
    }
    return mapping.get(provider, False)


def _policy_toggles(policy: WorkspaceAuthPolicy) -> dict[str, bool]:
    return {
        "yandex": policy.allow_yandex,
        "vk": policy.allow_vk,
        "telegram": policy.allow_telegram,
        "tid": policy.allow_tid,
        "sber_id": policy.allow_sber_id,
        "mts_id": policy.allow_mts_id,
        "esia": policy.allow_esia,
    }


def _policy_update_map(values: WorkspaceAuthPolicy | dict[str, object]) -> dict[str, object]:
    """Convert a mutable source to safe DB update payload."""

    if isinstance(values, WorkspaceAuthPolicy):
        return {
            "allow_yandex": values.allow_yandex,
            "allow_vk": values.allow_vk,
            "allow_telegram": values.allow_telegram,
            "allow_tid": values.allow_tid,
            "allow_sber_id": values.allow_sber_id,
            "allow_mts_id": values.allow_mts_id,
            "allow_esia": values.allow_esia,
            "allow_provider_self_enrollment": values.allow_provider_self_enrollment,
            "require_ru_local": values.require_ru_local,
            "residency_region_tag": values.residency_region_tag,
            "consent_text_version": values.consent_text_version,
        }
    payload: dict[str, object] = {}
    for name in (
        "allow_yandex",
        "allow_vk",
        "allow_telegram",
        "allow_tid",
        "allow_sber_id",
        "allow_mts_id",
        "allow_esia",
        "allow_provider_self_enrollment",
        "require_ru_local",
        "residency_region_tag",
        "consent_text_version",
    ):
        if name in values:
            payload[name] = values[name]
    return payload


def _build_provider_profiles(
    *,
    toggles: Mapping[str, bool],
    adapters: dict[str, object],
) -> list[ProviderProfile]:
    providers: list[ProviderProfile] = []
    for provider in SUPPORTED_PROVIDER_IDS:
        adapter = adapters.get(provider)
        label = provider
        requires_email = True
        if adapter is not None:
            label = getattr(adapter, "label", provider)
            requires_email = getattr(adapter, "requires_email", False)
        providers.append(
            ProviderProfile(
                provider=provider,
                enabled=bool(toggles.get(provider, False)),
                label=label,
                requires_email=requires_email,
            )
        )
    return providers


def is_provider_enabled_in_policy(policy: WorkspaceAuthPolicy, provider: str) -> bool:
    return _provider_toggle(policy, provider)


async def load_workspace_auth_policy(
    db: AsyncSession,
    workspace_id: UUID,
    *,
    create_missing: bool = True,
) -> WorkspaceAuthPolicy:
    policy = await db.scalar(select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == workspace_id))
    if policy is None:
        if not create_missing:
            return WorkspaceAuthPolicy(
                workspace_id=workspace_id,
                allow_yandex=True,
                allow_vk=True,
                allow_telegram=True,
                allow_tid=False,
                allow_sber_id=False,
                allow_mts_id=False,
                allow_esia=False,
                allow_provider_self_enrollment=False,
                require_ru_local=True,
                residency_region_tag="ru",
                consent_text_version="v1",
            )
        policy = WorkspaceAuthPolicy(workspace_id=workspace_id)
        db.add(policy)
        await db.flush()
    return policy


async def get_workspace_consent_copy(
    db: AsyncSession,
    policy: WorkspaceAuthPolicy,
) -> WorkspaceConsentCopy | None:
    return await db.scalar(
        select(WorkspaceConsentCopy).where(
            WorkspaceConsentCopy.workspace_id == policy.workspace_id,
            WorkspaceConsentCopy.language == "ru",
            WorkspaceConsentCopy.version == policy.consent_text_version,
            WorkspaceConsentCopy.is_active.is_(True),
        )
    )


async def ensure_workspace_consent_copy(
    db: AsyncSession,
    policy: WorkspaceAuthPolicy,
) -> WorkspaceConsentCopy:
    consent = await get_workspace_consent_copy(db, policy)
    if consent is not None:
        return consent
    consent = WorkspaceConsentCopy(
        workspace_id=policy.workspace_id,
        language="ru",
        version=policy.consent_text_version,
        content_markdown=default_ru_consent_copy(residency_region_tag=policy.residency_region_tag),
        is_active=True,
        published_at=datetime.now(UTC),
    )
    db.add(consent)
    await db.flush()
    return consent


async def update_workspace_auth_policy(
    db: AsyncSession,
    workspace_id: UUID,
    policy_updates: dict[str, object],
) -> AuthPolicySnapshot:
    current = await load_workspace_auth_policy(db, workspace_id)
    payload = _policy_update_map(policy_updates)
    if payload:
        await db.execute(
            update(WorkspaceAuthPolicy)
            .where(WorkspaceAuthPolicy.workspace_id == workspace_id)
            .values(**payload)
        )
        # keep in-memory snapshot consistent with request-scoped values used in this call.
        for field, value in payload.items():
            setattr(current, field, value)
    return await read_auth_providers(
        db,
        workspace_id,
        adapters=build_provider_registry(),
        persist_defaults=True,
    )


async def read_auth_providers(
    db: AsyncSession,
    workspace_id: UUID,
    *,
    adapters: dict[str, object],
    workspace_provider_overrides: dict[str, bool] | None = None,
    persist_defaults: bool = False,
) -> AuthPolicySnapshot:
    policy = await load_workspace_auth_policy(db, workspace_id, create_missing=persist_defaults)
    consent = (
        await ensure_workspace_consent_copy(db, policy)
        if persist_defaults
        else await get_workspace_consent_copy(db, policy)
    )
    toggles = _policy_toggles(policy)
    if workspace_provider_overrides:
        for provider, enabled in workspace_provider_overrides.items():
            toggles[provider] = enabled
    return AuthPolicySnapshot(
        workspace_id=workspace_id,
        providers=_build_provider_profiles(toggles=toggles, adapters=adapters),
        allow_provider_self_enrollment=policy.allow_provider_self_enrollment,
        require_ru_local=policy.require_ru_local,
        residency_region_tag=policy.residency_region_tag,
        consent_text_version=policy.consent_text_version,
        consent_language=consent.language if consent is not None else "ru",
        consent_content_markdown=(
            consent.content_markdown
            if consent is not None
            else default_ru_consent_copy(residency_region_tag=policy.residency_region_tag)
        ),
    )


def is_provider_enabled(policy: WorkspaceAuthPolicy, provider: str) -> bool:
    try:
        normalized = provider.lower()
    except AttributeError:
        return False
    return _provider_toggle(policy, normalized)
