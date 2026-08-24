from __future__ import annotations

from uuid import UUID

from twobrain_rec_server.cli.summary_slots import SlotMetadata, summarize_slot_metadata


def _row(**overrides: object) -> SlotMetadata:
    values: dict[str, object] = {
        "slot_id": UUID("10000000-0000-0000-0000-000000000001"),
        "workspace_id": UUID("20000000-0000-0000-0000-000000000001"),
        "meeting_id": UUID("30000000-0000-0000-0000-000000000001"),
        "template_key": "graf-auto-v1",
        "is_meeting_default": True,
        "current_outcome_set_id": UUID("40000000-0000-0000-0000-000000000001"),
        "current_binding_class": "verified_complete",
        "legacy_migration_proof_hash": None,
        "meeting_workspace_id": UUID("20000000-0000-0000-0000-000000000001"),
        "meeting_current_outcome_set_id": UUID("40000000-0000-0000-0000-000000000001"),
        "meeting_deleted": False,
        "outcome_id": UUID("40000000-0000-0000-0000-000000000001"),
        "outcome_workspace_id": UUID("20000000-0000-0000-0000-000000000001"),
        "outcome_meeting_id": UUID("30000000-0000-0000-0000-000000000001"),
        "outcome_template_key": "graf-auto-v1",
    }
    values.update(overrides)
    return SlotMetadata(**values)


def test_summary_slot_report_is_clean_for_one_verified_default() -> None:
    report = summarize_slot_metadata([_row()])

    assert report["status"] == "ok"
    assert report["slot_count"] == 1
    assert report["violations"] == {}


def test_summary_slot_report_only_returns_bounded_metadata_violations() -> None:
    report = summarize_slot_metadata(
        [
            _row(
                current_outcome_set_id=None,
                current_binding_class="verified_complete",
                meeting_current_outcome_set_id=None,
                outcome_id=None,
            )
        ],
        truncated=True,
    )

    assert report["status"] == "attention"
    assert report["truncated"] is True
    assert report["violations"] == {"empty_slot_has_binding_metadata": 1}
