"""Provider deletion reconciliation without over-claiming user erasure."""

from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.mediascribe.schemas import MediaScribeDeletionResponse


@dataclass(frozen=True, slots=True)
class DeletionReconciliation:
    state: str
    confirmed: bool
    receipt_id: str | None
    next_retry_seconds: int | None


def reconcile_deletion_response(
    response: MediaScribeDeletionResponse,
    *,
    local_state: str = "deleting",
) -> DeletionReconciliation:
    """Map provider ``202 cancelling``/receipt states to GRAF-safe truth."""

    state = response.state.value if hasattr(response.state, "value") else response.state
    if state == "completed" and response.deleted:
        return DeletionReconciliation(
            state="completed",
            confirmed=True,
            receipt_id=response.id,
            next_retry_seconds=None,
        )
    return DeletionReconciliation(
        state=local_state if local_state in {"deleting", "requested"} else "deleting",
        confirmed=False,
        receipt_id=response.id,
        next_retry_seconds=response.retry_after_seconds,
    )
