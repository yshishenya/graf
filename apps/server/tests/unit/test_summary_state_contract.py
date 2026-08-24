from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import (
    SummaryCopyCapabilityV1,
    SummaryStateEventV1,
    SummaryTypeCatalogEntryV1,
    SummaryTypeCatalogResponse,
)
from twobrain_rec_server.cabinet.rendering import _summary_render_lifecycle


def _entry(
    key: str,
    *,
    full_rank: int,
    quick_rank: int | None,
) -> SummaryTypeCatalogEntryV1:
    return SummaryTypeCatalogEntryV1(
        catalog_version="test-v1",
        template_key=key,
        template_version=1,
        resolved_locale="ru-RU",
        localized_name=key,
        localized_description="test",
        catalog_group="built_in",
        group_rank=1,
        category="general",
        quick_rank=quick_rank,
        full_rank=full_rank,
        availability_state="available",
        provenance={"source": "graf_extension", "rights_state": "not_applicable"},
        result_state="absent",
        generation_state="idle",
        source_state="current",
    )


def test_catalog_snapshot_rejects_noncanonical_order_and_duplicate_ranks() -> None:
    first = _entry("zeta", full_rank=1, quick_rank=1)
    second = _entry("alpha", full_rank=2, quick_rank=2)

    with pytest.raises(ValidationError):
        SummaryTypeCatalogResponse(
            catalog_version="test-v1",
            resolved_locale="ru-RU",
            entries=[second, first],
        )

    with pytest.raises(ValidationError):
        SummaryTypeCatalogResponse(
            catalog_version="test-v1",
            resolved_locale="ru-RU",
            entries=[
                first,
                _entry("alpha", full_rank=1, quick_rank=1),
            ],
        )


def test_copy_capability_is_either_exactly_bound_or_metadata_only() -> None:
    outcome_id = uuid4()
    bound = SummaryCopyCapabilityV1(
        outcome_set_id=outcome_id,
        outcome_content_hash="a" * 64,
        displayed_revision=outcome_id,
    )
    assert bound.authorized is True

    disabled = SummaryCopyCapabilityV1(authorized=False, reason_code="summary_not_ready")
    assert disabled.model_dump() == {
        "kind": "summary",
        "authorized": False,
        "outcome_set_id": None,
        "outcome_content_hash": None,
        "displayed_revision": None,
        "reason_code": "summary_not_ready",
    }

    with pytest.raises(ValidationError):
        SummaryCopyCapabilityV1(
            authorized=False,
            reason_code="summary_not_ready",
            outcome_set_id=outcome_id,
        )


def test_summary_event_rejects_private_controls_and_requires_positive_version() -> None:
    entry = _entry("graf-auto-v1", full_rank=1, quick_rank=1)
    with pytest.raises(ValidationError):
        SummaryStateEventV1(
            event_id=UUID("00000000-0000-0000-0000-000000000001"),
            meeting_id=UUID("00000000-0000-0000-0000-000000000002"),
            template_key="graf-auto-v1",
            state_version=0,
            catalog_entry=entry,
            copy_capability=SummaryCopyCapabilityV1(
                authorized=False,
                reason_code="summary_not_ready",
            ),
            my_actions=True,
        )


def test_server_rendered_summary_lifecycle_keeps_content_and_source_states_separate() -> None:
    stale_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="stored_output",
            summary=SimpleNamespace(state="available"),
        ),
        content_exports=SimpleNamespace(
            summary=SimpleNamespace(reason="stored_summary_revision_stale"),
        ),
        processing=SimpleNamespace(state="ready"),
        transcript=SimpleNamespace(available=True),
        template=SimpleNamespace(state="available", reason="graf-auto-v1", template_id=None),
    )
    assert _summary_render_lifecycle(stale_review) == {
        "result_state": "ready",
        "generation_state": "idle",
        "source_state": "stale",
        "availability_state": "available",
        "reason_code": "stored_summary_revision_stale",
    }

    processing_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="processing_status",
            summary=SimpleNamespace(state="processing"),
        ),
        content_exports=None,
        processing=SimpleNamespace(state="processing"),
        transcript=SimpleNamespace(available=False),
        template=SimpleNamespace(state="available", reason="graf-auto-v1", template_id=None),
    )
    assert _summary_render_lifecycle(processing_review) == {
        "result_state": "absent",
        "generation_state": "preparing",
        "source_state": "not_ready",
        "availability_state": "available",
        "reason_code": "transcript_not_ready",
    }

    unsupported_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="stored_output",
            summary=SimpleNamespace(state="not_inferable"),
        ),
        content_exports=None,
        processing=SimpleNamespace(state="ready"),
        transcript=SimpleNamespace(available=True),
        template=SimpleNamespace(state="available", reason="graf-auto-v1", template_id=None),
    )
    assert _summary_render_lifecycle(unsupported_review)["generation_state"] == (
        "no_supported_content"
    )

    failed_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="not_supported",
            summary=SimpleNamespace(state="unavailable"),
        ),
        content_exports=None,
        processing=SimpleNamespace(state="failed"),
        transcript=SimpleNamespace(available=False),
        template=SimpleNamespace(state="available", reason="graf-auto-v1", template_id=None),
    )
    failed = _summary_render_lifecycle(failed_review)
    assert (failed["source_state"], failed["reason_code"]) == (
        "transcript_failed",
        "transcript_failed",
    )

    empty_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="not_supported",
            summary=SimpleNamespace(state="unavailable"),
        ),
        content_exports=None,
        processing=SimpleNamespace(state="partial"),
        transcript=SimpleNamespace(available=False),
        template=SimpleNamespace(state="available", reason="graf-auto-v1", template_id=None),
    )
    empty = _summary_render_lifecycle(empty_review)
    assert (empty["source_state"], empty["reason_code"]) == ("empty", "source_empty")

    retired_review = SimpleNamespace(
        notes_action_truth=SimpleNamespace(
            source_basis="stored_output",
            summary=SimpleNamespace(state="available"),
        ),
        content_exports=None,
        processing=SimpleNamespace(state="ready"),
        transcript=SimpleNamespace(available=True),
        template=SimpleNamespace(
            state="available", reason="retired-format-v1", template_id=None
        ),
    )
    retired = _summary_render_lifecycle(retired_review)
    assert (retired["availability_state"], retired["reason_code"]) == (
        "retired",
        "summary_type_retired",
    )
