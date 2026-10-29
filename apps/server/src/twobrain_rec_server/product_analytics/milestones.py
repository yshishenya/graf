"""First activation milestones: the properties they carry and their one-time rule.

Every milestone of the funnel is a *first* event: the first launch, the first
connected account, the first recording, the first result, the first value. The
module keeps three promises that make the funnel readable:

* each conversion event carries the campaign it came from — the labels of the
  visit, plus the explicit state that says whether the campaign is known at all
  (FR-018);
* each conversion event carries the reliability of its campaign link —
  ``linked``, ``weak`` or ``unknown`` — and never a fabricated attribution
  (FR-023, FR-024);
* a repeated submission of the same milestone is not counted twice, on the
  server side as well as in the app (FR-025).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models.identity import UserIdentity
from twobrain_rec_server.db.models.product_analytics import (
    ACCOUNT_ACTIVATION_EVENTS,
    ProductActivationMilestone,
)
from twobrain_rec_server.product_analytics.attribution import (
    CAMPAIGN_LABEL_FIELDS,
    CAMPAIGN_LABEL_STATE_KNOWN,
    campaign_labels_for_event,
    normalize_attribution_reliability,
    resolve_conversion_reliability,
)
from twobrain_rec_server.product_analytics.event_catalog import PRODUCT_ACTIVATION_EVENT_NAMES
from twobrain_rec_server.product_analytics.events import (
    ProductActivationEvent,
    build_activation_event,
)
from twobrain_rec_server.product_analytics.forbidden_fields import assert_no_forbidden_fields
from twobrain_rec_server.product_analytics.identity import (
    build_safe_identity,
    is_safe_pseudonymous_id,
)

FIRST_MILESTONE_EVENTS = PRODUCT_ACTIVATION_EVENT_NAMES
USEFUL_RESULT_TYPES = ("transcript", "summary", "outcome", "action_items", "approved_equivalent")

MILESTONE_DEDUPE_RULE = "first_milestone_per_pseudonymous_user"
MILESTONE_STATUS_ACCEPTED = "accepted"
MILESTONE_STATUS_ACCEPTED_UNLINKED = "accepted_unlinked"
MILESTONE_STATUS_DUPLICATE = "duplicate"
MILESTONE_DEDUPE_MAX_ENTRIES = 100_000


@dataclass(slots=True)
class FirstMilestoneLedger:
    emitted: set[tuple[str, str]] = field(default_factory=set)

    def should_emit(self, stable_pseudonymous_user_id: str, event_name: str) -> bool:
        if event_name not in FIRST_MILESTONE_EVENTS:
            raise ValueError("event is not a first milestone")
        return (stable_pseudonymous_user_id, event_name) not in self.emitted

    def record(self, stable_pseudonymous_user_id: str, event_name: str) -> bool:
        if not self.should_emit(stable_pseudonymous_user_id, event_name):
            return False
        self.emitted.add((stable_pseudonymous_user_id, event_name))
        return True


def is_first_milestone_event(event_name: str) -> bool:
    return event_name in FIRST_MILESTONE_EVENTS


@dataclass(frozen=True, slots=True)
class MilestoneAcceptance:
    """The server-side decision about one incoming milestone."""

    accepted: bool
    status: str
    dedupe_key: str | None = None
    reason: str | None = None

    @property
    def duplicate(self) -> bool:
        return self.status == MILESTONE_STATUS_DUPLICATE


class MilestoneEmissionGuard:
    """Count a first milestone once per pseudonymous user (FR-025).

    The milestone is decided *before* anything is delivered to a provider, so a
    repeated submission neither reaches PostHog nor becomes a second Yandex
    offline conversion. The default instance is per process: it covers repeated
    submissions of one running product, and it is honest about the boundary —
    a restart forgets the ledger, while the app keeps its own durable copy.
    """

    def __init__(
        self,
        *,
        ledger: FirstMilestoneLedger | None = None,
        max_entries: int = MILESTONE_DEDUPE_MAX_ENTRIES,
    ) -> None:
        self.ledger = ledger or FirstMilestoneLedger()
        self.max_entries = max(1, int(max_entries))

    def accept(
        self,
        *,
        stable_pseudonymous_user_id: str | None,
        event_name: str,
    ) -> MilestoneAcceptance:
        if not is_first_milestone_event(event_name):
            raise ValueError("event is not a first milestone")
        if not stable_pseudonymous_user_id:
            # Without a pseudonymous identity there is nothing to deduplicate
            # against; the unlinked count stays visible instead of being hidden.
            return MilestoneAcceptance(True, MILESTONE_STATUS_ACCEPTED_UNLINKED, None)
        if not is_safe_pseudonymous_id(stable_pseudonymous_user_id):
            raise ValueError("milestone identity is not a safe pseudonymous identity")
        dedupe_key = milestone_dedupe_key(stable_pseudonymous_user_id, event_name)
        if not self.ledger.should_emit(stable_pseudonymous_user_id, event_name):
            return MilestoneAcceptance(
                False,
                MILESTONE_STATUS_DUPLICATE,
                dedupe_key,
                reason="milestone_already_counted",
            )
        self._trim()
        self.ledger.record(stable_pseudonymous_user_id, event_name)
        return MilestoneAcceptance(True, MILESTONE_STATUS_ACCEPTED, dedupe_key)

    def counted(self, *, stable_pseudonymous_user_id: str, event_name: str) -> bool:
        return (stable_pseudonymous_user_id, event_name) in self.ledger.emitted

    def reset(self) -> None:
        self.ledger.emitted.clear()

    def _trim(self) -> None:
        while len(self.ledger.emitted) >= self.max_entries:
            self.ledger.emitted.pop()


def milestone_dedupe_key(stable_pseudonymous_user_id: str, event_name: str) -> str:
    return f"{stable_pseudonymous_user_id}|{event_name}"


_DEFAULT_MILESTONE_GUARD = MilestoneEmissionGuard()


def default_milestone_guard() -> MilestoneEmissionGuard:
    return _DEFAULT_MILESTONE_GUARD


def milestone_attribution_properties(
    *,
    attribution_reliability: str | None = None,
    campaign_known: bool | None = None,
    account_connected: bool = False,
    fallback_recovered: bool = False,
    bridge_present: bool = False,
    graf_attribution_id: str | None = None,
    campaign_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The attribution properties every conversion milestone carries (FR-018).

    Two things always travel with a conversion event: the campaign labels of the
    visit and the level of the link.

    The labels come from the campaign context of the visit, are re-checked by
    the single shared sanitizer and are named after the same contract as the
    visit record, so one reading answers both "which campaign" and "how sure".
    A campaign that is not known is reported as ``campaign_label_state``
    ``unknown`` with every label empty: the event never invents a source and
    never reads as a direct entry (FR-024).

    The reliability level is always present too. When nothing is known the event
    is honestly marked ``unknown``.
    """
    labels, label_state = campaign_labels_for_event(campaign_context)
    # A caller that carries no label may still know that the campaign is real —
    # the label set of the visit is not the only evidence of it — so an explicit
    # claim is honored, while silence stays ``unknown`` (FR-024).
    known = (
        label_state == CAMPAIGN_LABEL_STATE_KNOWN
        if campaign_known is None
        else bool(campaign_known)
    )
    level = normalize_attribution_reliability(attribution_reliability)
    if level is None:
        level = resolve_conversion_reliability(
            campaign_known=known,
            account_connected=account_connected,
            fallback_recovered=fallback_recovered,
        )
    properties: dict[str, Any] = {
        "attribution_reliability": level,
        "bridge_present": bool(bridge_present),
        "campaign_label_state": label_state,
        **labels,
    }
    if graf_attribution_id:
        properties["graf_attribution_id"] = graf_attribution_id
    # Only the labels are untrusted here: the reliability level, the state and
    # the presence flag are produced by this module from a closed vocabulary.
    assert_no_forbidden_fields({field: labels[field] for field in CAMPAIGN_LABEL_FIELDS})
    return properties


@dataclass(frozen=True, slots=True)
class FirstValueDecision:
    eligible: bool
    reason: str
    useful_result_type: str | None = None


def first_value_decision(
    *,
    result_state: str,
    useful_output_present: bool,
    useful_result_type: str | None,
    imported_or_historical: bool = False,
) -> FirstValueDecision:
    if imported_or_historical:
        return FirstValueDecision(False, "imported_or_historical_result")
    if result_state != "ready":
        return FirstValueDecision(False, "result_not_ready")
    if not useful_output_present:
        return FirstValueDecision(False, "useful_output_absent")
    if useful_result_type not in USEFUL_RESULT_TYPES:
        return FirstValueDecision(False, "unsupported_useful_result_type")
    return FirstValueDecision(True, "ready_useful_result_viewed", useful_result_type)


def is_first_value_eligible(
    *,
    result_state: str,
    useful_output_present: bool,
    useful_result_type: str | None,
    imported_or_historical: bool = False,
) -> bool:
    return first_value_decision(
        result_state=result_state,
        useful_output_present=useful_output_present,
        useful_result_type=useful_result_type,
        imported_or_historical=imported_or_historical,
    ).eligible


# These SQL primitives do not commit or send. The trusted ingress must perform
# fresh legal/readiness checks, commit admission, then let maintenance deliver.
async def admit_account_milestone(
    db: AsyncSession,
    event: ProductActivationEvent,
    *,
    account_id: UUID,
    source_kind: str,
    requested_providers: tuple[str, ...] = (),
    before_insert: Callable[[], tuple[str, ...]] | None = None,
) -> tuple[ProductActivationMilestone, bool]:
    """Atomically keep one immutable account decision and its fixed intents."""

    if not isinstance(account_id, UUID):
        raise ValueError("trusted account UUID required")
    if event.event_name not in ACCOUNT_ACTIVATION_EVENTS:
        raise ValueError("account milestone required")
    if source_kind not in {"browser", "desktop", "server"}:
        raise ValueError("trusted milestone source required")
    if set(requested_providers) - {"posthog", "yandex"}:
        raise ValueError("unknown milestone provider")
    identity = build_safe_identity(user_source_id=str(account_id)).stable_pseudonymous_user_id
    if event.stable_pseudonymous_user_id != identity:
        raise ValueError("milestone identity does not match trusted account")
    now = datetime.now(UTC)
    if event.occurred_at.tzinfo is None or event.occurred_at > now:
        raise ValueError("milestone occurrence time is not verified")
    # Account close takes the same identity lock before purge. A delayed auth
    # background task must not reinsert a first decision after that purge.
    active_account = await db.scalar(
        select(UserIdentity.id)
        .where(
            UserIdentity.id == account_id,
            UserIdentity.status == "active",
        )
        .with_for_update(read=True)
    )
    if active_account is None:
        raise ValueError("milestone account is not active")
    # Revalidate at storage ingress; a dataclass constructed by a caller is not
    # itself evidence that the catalog/forbidden-field boundary was passed.
    payload = build_activation_event(
        event.event_name,
        stable_pseudonymous_user_id=identity,
        occurred_at=event.occurred_at,
        properties=event.properties,
    ).as_payload()
    if len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()) > 16384:
        raise ValueError("milestone payload exceeds 16 KiB")
    # Refresh permissions AFTER waiting for the account lock, directly before
    # constructing/executing the INSERT. No transport runs in this callback.
    if before_insert is not None:
        requested_providers = before_insert()
        if set(requested_providers) - {"posthog", "yandex"}:
            raise ValueError("unknown milestone provider")
    event_id = uuid5(
        UUID("2979ac36-e0b5-57cd-9355-8336fdf99b79"), f"{account_id}:{event.event_name}"
    )
    now = datetime.now(UTC)
    values = dict(
        id=uuid4(),
        account_id=account_id,
        event_name=event.event_name,
        event_id=event_id,
        occurred_at=event.occurred_at,
        accepted_at=now,
        safe_payload=payload,
        source_kind=source_kind,
        updated_at=now,
    )
    for provider in ("posthog", "yandex"):
        requested = provider in requested_providers
        values[f"{provider}_state"] = "pending" if requested else "not_requested"
        values[f"{provider}_reason"] = "accepted" if requested else "not_requested"
    statement = (
        insert(ProductActivationMilestone)
        .values(**values)
        .on_conflict_do_nothing()
        .returning(ProductActivationMilestone)
    )
    row = (await db.execute(statement)).scalar_one_or_none()
    if row is not None:
        return row, True
    row = await db.scalar(
        select(ProductActivationMilestone).where(
            ProductActivationMilestone.account_id == account_id,
            ProductActivationMilestone.event_name == event.event_name,
        )
    )
    if row is None:
        raise RuntimeError("milestone decision unavailable")
    return row, False


def _provider_columns(provider: str):

    if provider not in {"posthog", "yandex"}:
        raise ValueError("unknown milestone provider")
    return ProductActivationMilestone, getattr(ProductActivationMilestone, f"{provider}_state")


async def claim_milestone_delivery(
    db: AsyncSession,
    *,
    milestone_id: UUID,
    provider: str,
) -> ProductActivationMilestone | None:
    """Claim once; the caller MUST commit before entering the transport."""

    model, state = _provider_columns(provider)
    # One in-flight request per recipient across workers. The short transaction
    # lock serializes claims; committed dispatching holds the slot during HTTP.
    if not await db.scalar(select(func.pg_try_advisory_xact_lock(273, 1 if provider == "posthog" else 2))):
        return None
    if await db.scalar(select(select(model.id).where(state == "dispatching").exists())):
        return None
    now = datetime.now(UTC)
    attempt_id = uuid4()
    return (
        await db.execute(
            update(model)
            .where(
                model.id == milestone_id,
                state.in_(("pending", "pre_send_retry")),
            )
            .values(
                **{
                    f"{provider}_state": "dispatching",
                    f"{provider}_reason": "dispatch_started",
                    f"{provider}_attempt_id": attempt_id,
                    f"{provider}_attempted_at": now,
                    "updated_at": now,
                }
            )
            .returning(model)
        )
    ).scalar_one_or_none()


async def finish_milestone_delivery(
    db: AsyncSession,
    *,
    milestone_id: UUID,
    provider: str,
    attempt_id: UUID,
    outcome: str,
) -> bool:
    """Only the current attempt can finish; uncertainty is never a retry."""

    outcomes = {
        "technical_pre_send": ("pre_send_retry", "technical_pre_send"),
        "http_accepted": ("submitted", "http_accepted"),
        "transport_ambiguous": ("ambiguous", "transport_ambiguous"),
        "http_ambiguous": ("ambiguous", "http_ambiguous"),
        "purpose_withdrawn": ("cancelled", "purpose_withdrawn"),
        "payload_rejected": ("rejected", "payload_rejected"),
        "basis_unavailable": ("pending", "basis_unavailable"),
        "provider_disabled": ("pending", "provider_disabled"),
    }
    if outcome not in outcomes:
        raise ValueError("unknown milestone outcome")
    model, state = _provider_columns(provider)
    next_state, reason = outcomes[outcome]
    result = await db.execute(
        update(model)
        .where(
            model.id == milestone_id,
            state == "dispatching",
            getattr(model, f"{provider}_attempt_id") == attempt_id,
        )
        .values(
            **{
                f"{provider}_state": next_state,
                f"{provider}_reason": reason,
                "updated_at": datetime.now(UTC),
            }
        )
        .returning(model.id)
    )
    return result.scalar_one_or_none() is not None


async def delete_account_activation_decisions(db: AsyncSession, *, account_id: UUID) -> int:
    """Exact ledger erasure shared by account finalization and isolated replay.

    Caller owns identity/drain locking and the transaction; this never commits.
    """

    result = await db.execute(
        delete(ProductActivationMilestone).where(ProductActivationMilestone.account_id == account_id)
    )
    return int(result.rowcount)


async def quarantine_milestone_deliveries(
    db: AsyncSession,
    *,
    after_restore: bool = False,
    milestone_ids: tuple[UUID, ...] | None = None,
) -> int:
    """Never resend an interrupted transport or an unconfirmed restored intent.

    This does not reopen admission after restore: a missing post-backup row
    cannot be detected here. Readiness stays closed until separate reconciliation.
    """

    total = 0
    now = datetime.now(UTC)
    for provider in ("posthog", "yandex"):
        model, state = _provider_columns(provider)
        condition = (
            state.in_(("pending", "pre_send_retry", "dispatching", "submitted"))
            if after_restore
            else (
                (state == "dispatching")
                & (getattr(model, f"{provider}_attempted_at") < now - timedelta(seconds=60))
            )
        )
        if milestone_ids is not None:
            condition &= model.id.in_(milestone_ids)
        result = await db.execute(
            update(model)
            .where(condition)
            .values(
                **{
                    f"{provider}_state": "ambiguous",
                    f"{provider}_reason": "restore_quarantine"
                    if after_restore
                    else "interrupted_dispatch",
                    "updated_at": now,
                }
            )
        )
        total += result.rowcount
    return total
