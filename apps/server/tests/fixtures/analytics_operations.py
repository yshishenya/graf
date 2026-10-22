"""Explicit metadata fixtures for the current analytics guard contract."""
import json
from pathlib import Path


def write_runtime_guard(directory: Path, *, now: int) -> dict[str, str]:
    guard = directory / "runtime-guard"
    guard.mkdir(exist_ok=True)
    (guard / "alert-state").write_text(
        "alert_state_version=2\ncapacity_ready=true\ncapacity_input_verified=true\n"
        "capacity_budget_accepted=true\nprotection_status=observed\n"
        f"recorded_at_epoch={now}\ncapacity_sample_epoch={now}\n"
        f"capacity_budget_deadline_epoch={now + 3600}\n"
        f"capacity_inventory_version={'a' * 64}\ncapacity_budget_version={'c' * 64}\n"
    )
    (guard / "protection-state.json").write_text(json.dumps({
        "protection_state_version": 1, "status": "observed", "recorded_at_epoch": now, "reasons": [],
    }))
    return {"GRAF_POSTHOG_GUARD_STATE_DIR": str(guard)}


# Synthetic result of a complete native restore; never represents a live receipt.
CONSISTENT_RESTORE_LINES = (
    "consistency=cold_project_v1",
    "native_read=pass",
    "posthog_read=pass",
    "cleanup=pass",
    "retention_recheck=pass",
    "deletion_recheck=pass",
    "manifest_sha256=" + "a" * 64,
    "runtime_sha256=" + "b" * 64,
    "storage_classes=postgres,clickhouse",
    "verified_classes=postgres,clickhouse",
)
CONSISTENT_RESTORE_TEXT = "\n".join(CONSISTENT_RESTORE_LINES) + "\n"
