from __future__ import annotations

import hashlib
from dataclasses import dataclass

from twobrain_rec_server.product_analytics.forbidden_fields import assert_no_forbidden_fields

PSEUDONYM_PREFIX = "graf_pseudo_"


@dataclass(frozen=True, slots=True)
class AnalyticsIdentity:
    stable_pseudonymous_user_id: str
    posthog_distinct_id: str
    workspace_pseudonym: str | None = None
    account_pseudonym: str | None = None
    device_class: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "stable_pseudonymous_user_id": self.stable_pseudonymous_user_id,
            "posthog_distinct_id": self.posthog_distinct_id,
            "workspace_pseudonym": self.workspace_pseudonym,
            "account_pseudonym": self.account_pseudonym,
            "device_class": self.device_class,
        }


def stable_pseudonymous_user_id(raw_user_id: str, *, salt: str = "graf-product-analytics-v1") -> str:
    digest = hashlib.sha256(f"{salt}:{raw_user_id}".encode()).hexdigest()
    return f"{PSEUDONYM_PREFIX}user_{digest[:32]}"


def stable_pseudonym(kind: str, raw_value: str, *, salt: str = "graf-product-analytics-v1") -> str:
    normalized_kind = kind.strip().lower()
    if normalized_kind not in {"user", "workspace", "account", "bridge"}:
        raise ValueError("unsupported analytics pseudonym kind")
    digest = hashlib.sha256(f"{salt}:{normalized_kind}:{raw_value}".encode()).hexdigest()
    return f"{PSEUDONYM_PREFIX}{normalized_kind}_{digest[:32]}"


def build_safe_identity(
    *,
    user_source_id: str,
    workspace_source_id: str | None = None,
    account_source_id: str | None = None,
    device_class: str | None = None,
) -> AnalyticsIdentity:
    identity = AnalyticsIdentity(
        stable_pseudonymous_user_id=stable_pseudonym("user", user_source_id),
        posthog_distinct_id=stable_pseudonym("user", user_source_id),
        workspace_pseudonym=stable_pseudonym("workspace", workspace_source_id) if workspace_source_id else None,
        account_pseudonym=stable_pseudonym("account", account_source_id) if account_source_id else None,
        device_class=device_class,
    )
    assert_no_forbidden_fields(identity.as_dict())
    return identity


def is_safe_pseudonymous_id(value: str) -> bool:
    return value.startswith(PSEUDONYM_PREFIX) and "@" not in value and "/" not in value and "\\" not in value
