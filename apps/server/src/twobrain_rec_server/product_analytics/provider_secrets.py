from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProviderSecretError(ValueError):
    """Raised when a provider secret file is missing, empty, or unreadable."""


@dataclass(frozen=True, slots=True)
class ProviderSecretInventoryEntry:
    logical_name: str
    source: str
    target: str
    owner_role: str
    rotation_note: str
    committed_default: str
    propagation_test: str
    evidence_state: str = "missing"

    def as_dict(self) -> dict[str, str]:
        return {
            "logical_name": self.logical_name,
            "source": self.source,
            "target": self.target,
            "owner_role": self.owner_role,
            "rotation_note": self.rotation_note,
            "committed_default": self.committed_default,
            "propagation_test": self.propagation_test,
            "evidence_state": self.evidence_state,
        }


@dataclass(frozen=True, slots=True)
class ProviderSecretFile:
    logical_name: str
    value: str
    redacted_value: str = "configured_redacted"

    def __repr__(self) -> str:
        return f"ProviderSecretFile(logical_name={self.logical_name!r}, redacted_value={self.redacted_value!r})"

    def as_redacted_dict(self) -> dict[str, str]:
        return {
            "logical_name": self.logical_name,
            "value": self.redacted_value,
        }


@dataclass(frozen=True, slots=True)
class ProviderSecretFileStatus:
    logical_name: str
    present: bool
    redacted_value: str
    evidence_state: str
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "logical_name": self.logical_name,
            "present": self.present,
            "redacted_value": self.redacted_value,
            "evidence_state": self.evidence_state,
            "reason": self.reason,
        }


def redact_provider_value(value: object | None) -> str:
    if value is None:
        return "not_configured"
    if isinstance(value, str) and value.strip() == "":
        return "not_configured"
    return "configured_redacted"


def read_secret_file(path: Path, *, logical_name: str) -> ProviderSecretFile:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ProviderSecretError(f"{logical_name} secret file missing") from exc
    except OSError as exc:
        raise ProviderSecretError(f"{logical_name} secret file unreadable") from exc
    if not value:
        raise ProviderSecretError(f"{logical_name} secret file empty")
    return ProviderSecretFile(logical_name=logical_name, value=value)


def secret_file_status(path: Path | None, *, logical_name: str) -> ProviderSecretFileStatus:
    if path is None:
        return ProviderSecretFileStatus(
            logical_name=logical_name,
            present=False,
            redacted_value="not_configured",
            evidence_state="missing",
            reason="path_not_configured",
        )
    try:
        read_secret_file(path, logical_name=logical_name)
    except ProviderSecretError as exc:
        return ProviderSecretFileStatus(
            logical_name=logical_name,
            present=False,
            redacted_value="not_configured",
            evidence_state="missing",
            reason=str(exc),
        )
    return ProviderSecretFileStatus(
        logical_name=logical_name,
        present=True,
        redacted_value="configured_redacted",
        evidence_state="redacted_recorded",
    )


def default_provider_secret_inventory() -> tuple[ProviderSecretInventoryEntry, ...]:
    return (
        ProviderSecretInventoryEntry(
            "POSTHOG_PROJECT_KEY",
            "runtime secret file",
            "rec-api and rendered first-party PostHog config",
            "product analytics operator",
            "Rotate by replacing the PostHog project key outside git, swapping the runtime secret file, and rerunning provider smoke.",
            "empty",
            "file exists, value redacted, route can read without logging",
        ),
        ProviderSecretInventoryEntry(
            "POSTHOG_SECRET_KEY",
            "runtime secret file",
            "posthog stack",
            "infrastructure operator",
            "Rotate by replacing the stack secret file, restarting PostHog, and verifying health without printing it.",
            "placeholder",
            "stack config contains secret mount and no value in evidence",
        ),
        ProviderSecretInventoryEntry(
            "POSTHOG_DB_PASSWORD",
            "runtime secret file",
            "posthog database",
            "infrastructure operator",
            "Rotate through database credential update, stack restart, and redacted backup/restore verification.",
            "placeholder",
            "compose config contains secret mount and backup evidence redacts value",
        ),
        ProviderSecretInventoryEntry(
            "POSTHOG_REDIS_PASSWORD",
            "runtime secret file if Redis auth is enabled",
            "posthog redis",
            "infrastructure operator",
            "Rotate with Redis credential replacement, stack restart, and redacted smoke confirmation.",
            "placeholder",
            "redis secret is absent or mounted without evidence value",
        ),
        ProviderSecretInventoryEntry(
            "POSTHOG_OBJECT_STORAGE_SECRET",
            "runtime secret file if object storage is enabled",
            "posthog object/blob storage",
            "infrastructure operator",
            "Rotate with object-storage credential replacement and replay-disabled/default state verification.",
            "placeholder",
            "storage status is recorded without secret value",
        ),
        ProviderSecretInventoryEntry(
            "YANDEX_COUNTER_ID",
            "runtime environment/provider dashboard",
            "rec-api, page renderer, smoke runner",
            "growth analytics operator",
            "Rotate through a counter migration/update record, runtime config swap, page-scope smoke, and redacted evidence.",
            "empty",
            "numeric presence check only",
        ),
        ProviderSecretInventoryEntry(
            "YANDEX_OAUTH_TOKEN",
            "runtime secret file",
            "offline conversion uploader",
            "growth analytics operator",
            "Rotate by issuing a new token outside git, swapping the runtime secret file, and rerunning upload auth smoke.",
            "empty",
            "upload auth check without printing token",
        ),
        ProviderSecretInventoryEntry(
            "PRODUCT_ANALYTICS_FLAGS",
            "runtime environment",
            "rec-api, rendered pages, desktop config",
            "release operator",
            "Rotate/change through reviewed runtime deploy or rollback with smoke proving expected enabled/disabled states.",
            "disabled",
            "compose config and runtime env check",
        ),
    )
