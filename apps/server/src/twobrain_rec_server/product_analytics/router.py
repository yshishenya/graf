from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import case, or_, select, text

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import ProductActivationMilestone
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.product_analytics.advertising_transfer import (
    BLOCKER_MEASUREMENT_CONSENT_REVOKED,
    BLOCKER_RECIPIENT_REVOKED,
    BLOCKER_RETRANSFER_REFUSED,
)
from twobrain_rec_server.product_analytics.events import (
    ProductActivationEvent,
    build_activation_event,
)
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.legal_basis_gate import (
    activation_milestone_write_blockers,
)
from twobrain_rec_server.product_analytics.milestones import (
    claim_milestone_delivery,
    finish_milestone_delivery,
    quarantine_milestone_deliveries,
)
from twobrain_rec_server.product_analytics.posthog_client import (
    PostHogClientWrapper,
    ProviderDeliveryResult,
    ProviderTransportResponse,
)
from twobrain_rec_server.product_analytics.provider_delivery_gate import (
    resolve_provider_delivery_gate,
)
from twobrain_rec_server.product_analytics.yandex_offline import YandexOfflineConversionExporter


class ParallelMeasurementRouter:
    def __init__(self, settings: Settings) -> None:
        self.posthog = PostHogClientWrapper.from_settings(settings)
        self.yandex_offline = YandexOfflineConversionExporter.from_settings(settings)

    def dispatch(self, event: ProductActivationEvent) -> list[ProviderDeliveryResult]:
        return [
            self.posthog.capture(event),
            self.yandex_offline.export(event),
        ]


DELIVERY_CONTEXT = MaintenanceTenantContext(
    operation_name="activation_milestone_delivery", actor_id="graf-maintenance",
    reason_category="activation_delivery", feature_area="product_analytics",
)


async def _require_delivery_database(db) -> None:
    """An empty RLS-filtered scan must not masquerade as successful delivery."""
    row = (await db.execute(text(
        "SELECT session_user, current_user, current_setting('row_security'), "
        "rolsuper, rolbypassrls, "
        "rec_setting('app.context_kind'), rec_setting('app.maintenance_operation'), "
        "rec_setting('app.maintenance_feature_area') FROM pg_roles WHERE rolname=current_user"
    ))).one()
    if tuple(row) != (
        "twobrain_rec_maintenance", "twobrain_rec_maintenance", "on", False, False,
        "maintenance", "activation_milestone_delivery", "product_analytics",
    ):
        raise PermissionError("protected activation maintenance role required")


def _delivery_blocker(settings, provider, event):
    blockers = activation_milestone_write_blockers(settings)
    if blockers:
        return "purpose_withdrawn" if "legal_basis_withdrawn" in blockers else "basis_unavailable"
    gate = resolve_provider_delivery_gate(settings, provider=provider)
    if not gate.allowed:
        if "legal_basis_withdrawn" in gate.blockers and gate.withdrawals.withdrawal(gate.level_key) is not None:
            return "purpose_withdrawn"
        if {"posthog_disabled", "yandex_offline_disabled"}.intersection(gate.blockers):
            return "provider_disabled"
        return "basis_unavailable"
    if provider == "yandex":
        decision = YandexOfflineConversionExporter.from_settings(settings).transfer_decision(event)
        if not decision.allowed:
            revoked = {
                BLOCKER_MEASUREMENT_CONSENT_REVOKED, BLOCKER_RECIPIENT_REVOKED,
                BLOCKER_RETRANSFER_REFUSED,
            }.intersection(decision.blockers)
            return "purpose_withdrawn" if revoked else "basis_unavailable"
    return None


async def _milestone_http_transport(url, headers, body, timeout):
    # Native cancellable I/O bounds the whole request, including response headers.
    # Existing wrappers still own destination, secrets, validation and formatting.
    async with asyncio.timeout(min(timeout, 5.0)):
        async with httpx.AsyncClient(timeout=min(timeout, 5.0), follow_redirects=False) as client:
            async with client.stream("POST", url, headers=headers, content=body) as response:
                return ProviderTransportResponse(response.status_code)


async def _deliver_claim(sessions, settings, row, provider):
    """Bridge the existing synchronous wrappers to bounded asynchronous I/O."""
    loop = asyncio.get_running_loop()
    attempt_id = getattr(row, f"{provider}_attempt_id")

    def send():
        entered = False
        pre_send_blocker = None
        try:
            payload = row.safe_payload
            event = build_activation_event(
                row.event_name,
                stable_pseudonymous_user_id=payload.get("stable_pseudonymous_user_id"),
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                properties=payload["properties"],
            )
            if event.stable_pseudonymous_user_id != build_safe_identity(
                user_source_id=str(row.account_id)
            ).stable_pseudonymous_user_id:
                return "payload_rejected"

            async def guarded_transport(url, headers, body, timeout):
                nonlocal entered, pre_send_blocker
                async with asyncio.timeout(5):
                    async with sessions() as db:
                        await apply_tenant_context(db, DELIVERY_CONTEXT)
                        await _require_delivery_database(db)
                        exists = await db.scalar(select(ProductActivationMilestone.id).where(
                            ProductActivationMilestone.id == row.id,
                            getattr(ProductActivationMilestone, f"{provider}_state") == "dispatching",
                            getattr(ProductActivationMilestone, f"{provider}_attempt_id") == attempt_id,
                        ))
                    if exists is None:
                        pre_send_blocker = "purpose_withdrawn"
                        raise PermissionError("purpose_withdrawn")
                    blocker = _delivery_blocker(settings, provider, event)
                    if blocker:
                        pre_send_blocker = blocker
                        raise PermissionError(blocker)
                    entered = True
                    return await _milestone_http_transport(url, headers, body, min(timeout, 5.0))

            def transport(url, headers, body, timeout):
                return asyncio.run_coroutine_threadsafe(
                    guarded_transport(url, headers, body, timeout), loop
                ).result()

            blocker = _delivery_blocker(settings, provider, event)
            if blocker:
                return blocker
            client = (PostHogClientWrapper if provider == "posthog"
                      else YandexOfflineConversionExporter).from_settings(settings)
            client.transport = transport
            client.timeout_seconds = 5.0
            result = (client.capture(event, event_id=row.event_id) if provider == "posthog"
                      else client.export(event, event_id=row.event_id))
            # Provider wrappers catch OSError (including PermissionError).
            # Preserve the proven refusal recorded before any network entry.
            if pre_send_blocker:
                return pre_send_blocker
            if entered:
                if result.status in {"live_safe_sent", "live_safe_uploaded"}:
                    return "http_accepted"
                return "transport_ambiguous" if result.status == "network_error" else "http_ambiguous"
            if result.status in {"payload_rejected", "identity_missing", "not_applicable"}:
                return "payload_rejected"
            if result.status == "configuration_error":
                return "technical_pre_send"
            return "provider_disabled" if result.status == "disabled" else "basis_unavailable"
        except PermissionError as error:
            if not entered and error.args and error.args[0] in {
                "purpose_withdrawn", "basis_unavailable", "provider_disabled",
            }:
                return error.args[0]
            return "transport_ambiguous" if entered else "basis_unavailable"
        except (ValueError, KeyError, TypeError):
            return "transport_ambiguous" if entered else "payload_rejected"
        except Exception:
            return "transport_ambiguous" if entered else "technical_pre_send"

    task = asyncio.create_task(asyncio.to_thread(send))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # Cancellation of await does not stop a thread. Drain its bounded I/O;
        # leave the committed dispatching claim for quarantine, never resend it.
        await asyncio.shield(task)
        raise


async def reconcile_activation_milestones_once(sessions, *, settings: Settings) -> int:
    if activation_milestone_write_blockers(settings):
        return 0
    async with sessions() as db:
        await apply_tenant_context(db, DELIVERY_CONTEXT)
        await _require_delivery_database(db)
        stale = or_(*(
            (getattr(ProductActivationMilestone, f"{provider}_state") == "dispatching")
            & (getattr(ProductActivationMilestone, f"{provider}_attempted_at")
               < datetime.now(UTC) - timedelta(seconds=60))
            for provider in ("posthog", "yandex")
        ))
        ids = list(await db.scalars(select(ProductActivationMilestone.id).where(or_(
            ProductActivationMilestone.posthog_state.in_(("pending", "pre_send_retry")),
            ProductActivationMilestone.yandex_state.in_(("pending", "pre_send_retry")),
            stale,
        )).order_by(case((stale, 0), else_=1), ProductActivationMilestone.accepted_at,
                    ProductActivationMilestone.id).limit(20)))
        await quarantine_milestone_deliveries(db, milestone_ids=tuple(ids))
        await db.commit()
    for milestone_id in ids:
        for provider in ("posthog", "yandex"):
            async with sessions() as db:
                await apply_tenant_context(db, DELIVERY_CONTEXT)
                await _require_delivery_database(db)
                row = await claim_milestone_delivery(db, milestone_id=milestone_id, provider=provider)
                await db.commit()
            if row is None:
                continue
            outcome = await _deliver_claim(sessions, settings, row, provider)
            async with sessions() as db:
                await apply_tenant_context(db, DELIVERY_CONTEXT)
                await _require_delivery_database(db)
                await finish_milestone_delivery(
                    db, milestone_id=row.id, provider=provider,
                    attempt_id=getattr(row, f"{provider}_attempt_id"), outcome=outcome,
                )
                await db.commit()
    return len(ids)
