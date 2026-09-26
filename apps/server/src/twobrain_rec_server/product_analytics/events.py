from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from twobrain_rec_server.product_analytics.event_catalog import get_event_definition
from twobrain_rec_server.product_analytics.forbidden_fields import (
    SAFE_IDENTIFIER_FIELDS,
    ForbiddenFieldViolation,
    find_forbidden_fields,
)
from twobrain_rec_server.product_analytics.identity import is_safe_pseudonymous_id

# Identifier fields carry an opaque pseudonym or an opaque bridge identifier,
# never content. The generic value predicate reads a long run of digits inside
# such a value as a phone number, so it is not applied to them: an identifier
# is checked by its own shape instead. Without this, a conversion milestone
# whose identifier happens to contain ten digits in a row would be dropped
# (FR-022, FR-023).
_IDENTIFIER_VALUE_ALPHABET = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
)
_IDENTIFIER_VALUE_MAX_LENGTH = 96


def _assert_no_forbidden_event_fields(properties: Mapping[str, Any]) -> None:
    content = {key: value for key, value in properties.items() if key not in SAFE_IDENTIFIER_FIELDS}
    findings = list(find_forbidden_fields(content))
    findings.extend(
        f"$.{key}"
        for key, value in properties.items()
        if key in SAFE_IDENTIFIER_FIELDS and not _is_safe_identifier_value(value)
    )
    if findings:
        raise ForbiddenFieldViolation(tuple(findings))


def _is_safe_identifier_value(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return True
    if not isinstance(value, str):
        return False
    if not 1 <= len(value) <= _IDENTIFIER_VALUE_MAX_LENGTH:
        return False
    return all(character in _IDENTIFIER_VALUE_ALPHABET for character in value)


@dataclass(frozen=True, slots=True)
class ProductActivationEvent:
    event_name: str
    surface: str
    owner: str
    occurred_at: datetime
    stable_pseudonymous_user_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    delivery_mode: str = "server_mediated"

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_name": self.event_name,
            "surface": self.surface,
            "owner": self.owner,
            "occurred_at": self.occurred_at.isoformat(),
            "delivery_mode": self.delivery_mode,
            "properties": dict(self.properties),
        }
        if self.stable_pseudonymous_user_id:
            payload["stable_pseudonymous_user_id"] = self.stable_pseudonymous_user_id
        return payload


def build_activation_event(
    event_name: str,
    *,
    stable_pseudonymous_user_id: str | None = None,
    occurred_at: datetime | None = None,
    properties: Mapping[str, Any] | None = None,
) -> ProductActivationEvent:
    definition = get_event_definition(event_name)
    safe_properties = dict(properties or {})
    _assert_no_forbidden_event_fields(safe_properties)
    unknown_fields = sorted(set(safe_properties) - set(definition.allowed_fields))
    if unknown_fields:
        raise ValueError(f"analytics event contains fields outside allowlist: {', '.join(unknown_fields)}")
    if stable_pseudonymous_user_id and not is_safe_pseudonymous_id(stable_pseudonymous_user_id):
        raise ValueError("stable_pseudonymous_user_id is not a safe pseudonymous analytics identity")
    return ProductActivationEvent(
        event_name=definition.event_name,
        surface=definition.surface,
        owner=definition.owner,
        occurred_at=occurred_at or datetime.now(UTC),
        stable_pseudonymous_user_id=stable_pseudonymous_user_id,
        properties=safe_properties,
        delivery_mode=definition.delivery_mode,
    )
