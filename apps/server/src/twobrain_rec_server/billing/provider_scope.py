"""Bounded, read-only tenant resolution for provider child notifications.

The normal metadata-bearing webhook remains an inbox-only path. A cabinet
refund/receipt has no tenant metadata, so authenticate its parent before using
that parent's workspace. This does not reconcile money or create a refund.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import UUID

from twobrain_rec_server.billing.provider_events import (
    ProviderEvent,
    ProviderEventError,
    validate_provider_identifier,
)
from twobrain_rec_server.billing.reconciliation import (
    ProviderScope,
    extract_payment_observation,
    extract_receipt_observation,
    extract_refund_observation,
)
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    provider_environment,
)
from twobrain_rec_server.config import Settings

SCOPE_RESOLUTION_TIMEOUT_SECONDS = 8
CHILD_SCOPE_EVENTS = frozenset(
    {"refund.succeeded", "receipt.succeeded", "receipt.waiting_for_cancellation"}
)


class ProviderScopeUnavailable(RuntimeError):
    """A parent is not yet available; do not acknowledge the notification."""


def _same_reference(actual: object, expected: str) -> None:
    if not isinstance(actual, str) or not actual:
        raise ProviderScopeUnavailable("provider reference is incomplete")
    if actual != expected:
        raise ProviderEventError("provider object reference conflicts")


def _scope_hint(payload: dict, workspace_id: UUID, operation_id: UUID) -> None:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return
    for field, expected in (("workspace_id", workspace_id), ("operation_id", operation_id)):
        if metadata.get(field) and metadata[field] != str(expected):
            raise ProviderEventError("provider scope hint conflicts")


async def resolve_child_scope(
    event: ProviderEvent, incoming: dict, settings: Settings
) -> tuple[ProviderEvent, dict, ProviderScope]:
    """Read at most receipt -> refund -> payment, under one eight-second deadline.

    Only the immutable event scope is filled; preserve the original event id,
    timestamp and fingerprint so retries remain identical to the received signal.
    The caller must still validate the local operation/invoice in tenant context.
    """
    if event.workspace_id is not None or event.event_type not in CHILD_SCOPE_EVENTS:
        raise ProviderEventError("provider scope resolution is not applicable")
    for field in ("payment_id", "refund_id"):
        if field in incoming:
            validate_provider_identifier(incoming[field])
    if "status" in incoming and not isinstance(incoming["status"], str):
        raise ProviderEventError("provider event status is malformed")
    if (
        event.event_type.startswith("receipt.")
        and "type" in incoming
        and (not isinstance(incoming["type"], str) or incoming["type"] not in {"payment", "refund"})
    ):
        raise ProviderEventError("provider event receipt type is malformed")
    if not settings.billing_yookassa_shop_id:
        raise YooKassaConfigurationError("provider shop is unavailable")
    scope = ProviderScope(
        environment=provider_environment(settings.billing_yookassa_environment),
        shop_id=settings.billing_yookassa_shop_id,
    )
    children = [incoming]
    refund = None
    receipt_payment_id = None
    async with asyncio.timeout(SCOPE_RESOLUTION_TIMEOUT_SECONDS):
        async with YooKassaClient(settings) as provider:
            parent_id = event.object_id
            parent_kind = "refund"
            if event.event_type.startswith("receipt."):
                receipt = await provider.get_receipt(event.object_id)
                _same_reference(receipt.get("id"), event.object_id)
                for field in ("type", "status"):
                    if not isinstance(receipt.get(field), str):
                        raise ProviderScopeUnavailable("provider receipt is incomplete")
                if receipt.get("type") == "payment" and receipt.get("refund_id") is not None:
                    raise ProviderEventError("provider receipt parent conflicts")
                try:
                    observed = extract_receipt_observation(receipt, scope=scope)
                except (ValueError, TypeError) as exc:
                    raise ProviderScopeUnavailable("provider receipt is incomplete") from exc
                if event.event_type == "receipt.succeeded" and observed.status != "succeeded":
                    raise ProviderScopeUnavailable("provider receipt is not ready")
                for field in ("type", "payment_id", "refund_id"):
                    if field in incoming and incoming[field] != receipt.get(field):
                        raise ProviderEventError("provider receipt parent conflicts")
                parent_kind, parent_id = observed.parent_kind, observed.provider_parent_id
                receipt_payment_id = observed.related_payment_id
                children.append(receipt)
            if parent_kind == "refund":
                payload = await provider.get_refund(parent_id)
                _same_reference(payload.get("id"), parent_id)
                if payload.get("status") != "succeeded":
                    raise ProviderScopeUnavailable("provider refund is not ready")
                try:
                    refund = extract_refund_observation(payload, scope=scope)
                except (ValueError, TypeError) as exc:
                    raise ProviderScopeUnavailable("provider refund is incomplete") from exc
                if event.event_type == "refund.succeeded" and "payment_id" in incoming:
                    _same_reference(incoming["payment_id"], refund.provider_payment_id)
                if receipt_payment_id is not None:
                    _same_reference(receipt_payment_id, refund.provider_payment_id)
                children.append(payload)
                parent_id = refund.provider_payment_id
            payment = await provider.get_payment(validate_provider_identifier(parent_id))
            _same_reference(payment.get("id"), parent_id)
            recipient = payment.get("recipient")
            if not isinstance(recipient, dict) or not isinstance(recipient.get("account_id"), str):
                raise ProviderScopeUnavailable("provider shop is incomplete")
            if recipient["account_id"] != scope.shop_id:
                raise ProviderEventError("provider shop conflicts")
            if not isinstance(payment.get("test"), bool):
                raise ProviderScopeUnavailable("provider environment is incomplete")
            if payment["test"] is not (scope.environment == "test"):
                raise ProviderEventError("provider environment conflicts")
            try:
                observed_payment = extract_payment_observation(payment, scope=scope)
            except (ValueError, TypeError) as exc:
                raise ProviderScopeUnavailable("provider payment is incomplete") from exc
            if refund is not None:
                if observed_payment.status != "succeeded" or payment.get("paid") is not True:
                    raise ProviderScopeUnavailable("provider payment is not ready")
                if (
                    refund.currency != observed_payment.currency
                    or refund.amount_minor > observed_payment.amount_minor
                ):
                    raise ProviderEventError("provider refund amount conflicts")
            metadata = payment.get("metadata")
            if (
                not isinstance(metadata, dict)
                or not metadata.get("workspace_id")
                or not metadata.get("operation_id")
            ):
                raise ProviderScopeUnavailable("provider payment scope is incomplete")
            try:
                workspace_id = UUID(str(metadata["workspace_id"]))
                operation_id = UUID(str(metadata["operation_id"]))
            except ValueError as exc:
                raise ProviderScopeUnavailable("provider payment scope is malformed") from exc
            if event.operation_id is not None and event.operation_id != operation_id:
                raise ProviderEventError("provider operation hint conflicts")
            for child in children:
                _scope_hint(child, workspace_id, operation_id)
    return replace(event, workspace_id=workspace_id, operation_id=operation_id), payment, scope
