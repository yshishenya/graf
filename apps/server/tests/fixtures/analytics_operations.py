"""Explicit metadata fixtures for the current analytics guard contract."""
import json
from pathlib import Path


def write_runtime_guard(directory: Path, *, now: int) -> dict[str, str]:
    guard = directory / "runtime-guard"
    guard.mkdir(exist_ok=True)
    (guard / "alert-state").write_text(
        "alert_state_version=3\nmeasurement_scope=posthog\ncapacity_ready=true\ncapacity_input_verified=true\n"
        "capacity_budget_accepted=true\nprotection_status=observed\n"
        f"recorded_at_epoch={now}\ncapacity_sample_epoch={now}\n"
        f"capacity_budget_deadline_epoch={now + 3600}\n"
        f"capacity_inventory_version={'a' * 64}\ncapacity_budget_version={'c' * 64}\n"
    )
    (guard / "protection-state.json").write_text(json.dumps({
        "protection_state_version": 2, "measurement_scope": "posthog", "status": "observed", "recorded_at_epoch": now, "reasons": [],
    }))
    return {"GRAF_POSTHOG_GUARD_STATE_DIR": str(guard)}


# Self-declared synthetic receipt; without the T118 verifier it must remain blocked.
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


def stub_verified_restore(monkeypatch) -> None:
    """Isolate transport/page-policy tests from the unfinished T118 verifier.

    This injects typed evidence in the test process only; it does not make the
    self-declared receipt acceptable to the real operations consumer.
    """
    from dataclasses import replace

    from twobrain_rec_server.product_analytics import provider_readiness
    collect = provider_readiness.collect_analytics_operations_evidence
    monkeypatch.setattr(provider_readiness, "collect_analytics_operations_evidence",
                        lambda *args, **kwargs: replace(collect(*args, **kwargs), restore_consistent=True))
