from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

TELEMETRY_GATE_STATES = (
    "not_seen",
    "accepted",
    "withdrawn",
    "terms_update_required",
    "refused_updated_terms",
    "limited_to_account_legal_export_deletion",
)

_ALLOWED_TRANSITIONS = {
    "not_seen": {"accepted"},
    "accepted": {"terms_update_required", "withdrawn"},
    "terms_update_required": {"accepted", "refused_updated_terms"},
    "withdrawn": {"limited_to_account_legal_export_deletion"},
    "refused_updated_terms": {"limited_to_account_legal_export_deletion"},
    "limited_to_account_legal_export_deletion": set(),
}


@dataclass(frozen=True, slots=True)
class ProductTelemetryGateRecord:
    state: str = "not_seen"
    gate_version: str = "094.1"
    copy_version: str = "2026-07-09.1"
    required_terms_version: str = "pending-legal"
    privacy_policy_version: str = "pending-legal"
    personal_data_processing_version: str = "pending-legal"
    accepted_by_pseudonymous_user_id: str | None = None
    accepted_at: datetime | None = None
    accepted_surface: str | None = None
    direct_desktop_egress_disclosed: bool = False
    replay_boundaries_disclosed: bool = True
    retention_deletion_disclosed: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "gate_version": self.gate_version,
            "copy_version": self.copy_version,
            "required_terms_version": self.required_terms_version,
            "privacy_policy_version": self.privacy_policy_version,
            "personal_data_processing_version": self.personal_data_processing_version,
            "accepted_by_pseudonymous_user_id": self.accepted_by_pseudonymous_user_id,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "accepted_surface": self.accepted_surface,
            "direct_desktop_egress_disclosed": self.direct_desktop_egress_disclosed,
            "replay_boundaries_disclosed": self.replay_boundaries_disclosed,
            "retention_deletion_disclosed": self.retention_deletion_disclosed,
        }


def transition_gate_state(
    record: ProductTelemetryGateRecord,
    target_state: str,
    *,
    pseudonymous_user_id: str | None = None,
    accepted_surface: str | None = None,
) -> ProductTelemetryGateRecord:
    if target_state not in TELEMETRY_GATE_STATES:
        raise ValueError("unknown telemetry gate state")
    if target_state not in _ALLOWED_TRANSITIONS[record.state]:
        raise ValueError(f"telemetry gate cannot transition from {record.state} to {target_state}")
    if target_state == "accepted":
        return ProductTelemetryGateRecord(
            state="accepted",
            gate_version=record.gate_version,
            copy_version=record.copy_version,
            required_terms_version=record.required_terms_version,
            privacy_policy_version=record.privacy_policy_version,
            personal_data_processing_version=record.personal_data_processing_version,
            accepted_by_pseudonymous_user_id=pseudonymous_user_id,
            accepted_at=datetime.now(UTC),
            accepted_surface=accepted_surface,
            direct_desktop_egress_disclosed=record.direct_desktop_egress_disclosed,
            replay_boundaries_disclosed=record.replay_boundaries_disclosed,
            retention_deletion_disclosed=record.retention_deletion_disclosed,
        )
    return ProductTelemetryGateRecord(
        state=target_state,
        gate_version=record.gate_version,
        copy_version=record.copy_version,
        required_terms_version=record.required_terms_version,
        privacy_policy_version=record.privacy_policy_version,
        personal_data_processing_version=record.personal_data_processing_version,
        direct_desktop_egress_disclosed=record.direct_desktop_egress_disclosed,
        replay_boundaries_disclosed=record.replay_boundaries_disclosed,
        retention_deletion_disclosed=record.retention_deletion_disclosed,
    )


def is_product_use_allowed(state: str) -> bool:
    return state == "accepted"


def requires_acceptance(state: str) -> bool:
    return state in {"not_seen", "terms_update_required"}


def analytics_collection_allowed(state: str) -> bool:
    return state == "accepted"


def limited_access_only(state: str) -> bool:
    return state in {"withdrawn", "refused_updated_terms", "limited_to_account_legal_export_deletion"}


def build_required_disclosure(*, direct_desktop_egress: bool = False) -> dict[str, object]:
    return {
        "gate_version": "094.1",
        "copy_version": "2026-07-09.1",
        "normal_product_use_requires_acceptance": True,
        "one_time_personal_acceptance": True,
        "providers": {
            "posthog": "primary product analytics workspace after approval",
            "yandex": "parallel web/ad/Webvisor/offline-conversion surface after approval",
        },
        "direct_desktop_egress_disclosed": direct_desktop_egress,
        "forbidden_collection": [
            "raw identity",
            "meeting content",
            "audio",
            "transcript",
            "calendar text",
            "local paths",
            "tokens",
            "signed URLs",
            "device names",
        ],
        "minimum_retention_days": 90,
        "withdrawal_behavior": "normal product use stops; account/legal/export/deletion flows stay available",
    }
