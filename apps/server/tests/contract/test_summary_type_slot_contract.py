from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.summary_type_slots import (
    AUTO_TEMPLATE_KEY,
    MINUTES_TEMPLATE_KEY,
    empty_type_slots,
    two_type_revision_fixtures,
)
from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = REPO_ROOT / "apps/server"
RUNTIME_ROOT = SERVER_ROOT / "src/twobrain_rec_server"
SCRIPTS_ROOT = SERVER_ROOT / "scripts"
MEETING_ID = UUID("50000000-0000-0000-0000-000000000001")

QUERY_OWNER_CLASSES = {
    "apps/server/scripts/cleanup_smoke_artifacts.py": "test_cleanup",
    "apps/server/scripts/prove_meeting_outcome_live.py": "legacy_proof",
    "apps/server/scripts/reconcile_initial_outcomes.py": "legacy_reconciliation",
    "apps/server/src/twobrain_rec_server/api/cabinet.py": "api_read_and_candidate_compatibility",
    "apps/server/src/twobrain_rec_server/api/schemas.py": "api_contract",
    "apps/server/src/twobrain_rec_server/cabinet/egress.py": "egress_read",
    "apps/server/src/twobrain_rec_server/cabinet/exports.py": "export_read",
    "apps/server/src/twobrain_rec_server/cabinet/queries.py": "cabinet_read",
    "apps/server/src/twobrain_rec_server/cabinet/rendering.py": "render_read",
    "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js": "ui_contract",
    "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html": "ui_contract",
    "apps/server/src/twobrain_rec_server/cabinet/view_models.py": "view_model",
    "apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py": "browser_read",
    "apps/server/src/twobrain_rec_server/db/models/__init__.py": "model_registration",
    "apps/server/src/twobrain_rec_server/db/models/meeting.py": "legacy_pointer_model",
    "apps/server/src/twobrain_rec_server/db/models/outcomes.py": "outcome_model",
    "apps/server/src/twobrain_rec_server/db/rls_validation.py": "rls_inventory",
    "apps/server/src/twobrain_rec_server/deletion/service.py": "deletion_owner",
    "apps/server/src/twobrain_rec_server/outcomes/ai_service.py": "publication_owner",
    "apps/server/src/twobrain_rec_server/outcomes/service.py": "generation_owner",
    "apps/server/src/twobrain_rec_server/outcomes/store.py": "lineage_store",
}


def test_summary_slot_is_a_pointer_only_with_named_scope_contracts() -> None:
    assert models.MeetingSummarySlot.__tablename__ == "meeting_summary_slots"
    assert "meeting_summary_slots" in Base.metadata.tables

    slot = Base.metadata.tables["meeting_summary_slots"]
    assert {"workspace_id", "meeting_id", "template_key", "current_outcome_set_id"}.issubset(
        set(slot.c.keys())
    )
    assert not {
        "summary_text",
        "transcript_text",
        "prompt_definition",
        "raw_response_json",
        "publication_receipt_digest",
    }.intersection(slot.c)

    constraints = {constraint.name for constraint in slot.constraints if constraint.name}
    assert "uq_meeting_summary_slots_workspace_meeting_type" in constraints
    assert "fk_meeting_summary_slots_meeting_workspace" in constraints
    assert "fk_meeting_summary_slots_current_outcome_target" in constraints


def test_meeting_and_outcome_targets_have_named_composite_keys() -> None:
    meeting_constraints = {
        constraint.name for constraint in Base.metadata.tables["meetings"].constraints if constraint.name
    }
    outcome_constraints = {
        constraint.name
        for constraint in Base.metadata.tables["meeting_outcome_sets"].constraints
        if constraint.name
    }
    assert "uq_meetings_id_workspace_id" in meeting_constraints
    assert "uq_meeting_outcome_sets_target" in outcome_constraints


def test_summary_type_fixtures_are_two_type_and_content_free() -> None:
    lineages = two_type_revision_fixtures(WORKSPACE_ID, MEETING_ID)
    assert {lineage.template_key for lineage in lineages} == {
        AUTO_TEMPLATE_KEY,
        MINUTES_TEMPLATE_KEY,
    }
    assert all(lineage.current_outcome_set_id != lineage.replacement_outcome_set_id for lineage in lineages)

    slots = empty_type_slots(WORKSPACE_ID, MEETING_ID)
    assert {slot.template_key for slot in slots} == {AUTO_TEMPLATE_KEY, MINUTES_TEMPLATE_KEY}
    assert all(slot.current_outcome_set_id is None for slot in slots)
    assert all(not hasattr(slot, "text") for slot in slots)
    assert {slot.id for slot in slots} == {lineage.slot_id for lineage in lineages}


def test_runtime_outcome_query_owner_inventory_has_no_unclassified_newest_row_fallback() -> None:
    """The inventory is intentionally closed: new owners must be classified first."""

    observed: set[str] = set()
    for root in (RUNTIME_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".py", ".js", ".html"}:
                continue
            if "db/migrations/versions" in str(path):
                continue
            source = path.read_text(encoding="utf-8")
            if "MeetingOutcomeSet" in source or "meeting_outcome_sets" in source or "current_outcome_set_id" in source:
                observed.add(str(path.relative_to(REPO_ROOT)))

    assert observed == set(QUERY_OWNER_CLASSES), sorted(observed - set(QUERY_OWNER_CLASSES))

    forbidden_line = re.compile(
        r"(?:MeetingOutcomeSet|meeting_outcome_sets).*?"
        r"(?:created_at|generated_at).*?(?:desc|limit|first|max)",
        re.IGNORECASE,
    )
    findings = [
        f"{path}: {QUERY_OWNER_CLASSES[path]}"
        for path in sorted(QUERY_OWNER_CLASSES)
        if any(
            forbidden_line.search(line)
            for line in (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
        )
    ]
    assert findings == [], "unclassified newest-row query owners: " + ", ".join(findings)
