from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import UserIdentity
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context
from twobrain_rec_server.product_analytics.delivery_gap import AnalyticsDeliveryGap
from twobrain_rec_server.product_analytics.event_catalog import (
    yandex_offline_conversion_event_names,
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
    MILESTONE_STATUS_DUPLICATE,
    admit_account_milestone,
)
from twobrain_rec_server.product_analytics.posthog_client import ProviderDeliveryResult
from twobrain_rec_server.product_analytics.provider_delivery_gate import (
    resolve_provider_delivery_gate,
)
from twobrain_rec_server.product_analytics.telemetry_gate import analytics_collection_allowed
from twobrain_rec_server.product_analytics.yandex_offline import YandexOfflineConversionExporter

if TYPE_CHECKING:
    from twobrain_rec_server.cabinet.result_visibility import ResultViewBinding


@dataclass(frozen=True, slots=True)
class _AccountAdmissionContext:
    db: AsyncSession
    started_at: datetime | None = None
    recheck: Callable[[], None] | None = None


@asynccontextmanager
async def _account_session(sessionmaker):
    async with sessionmaker() as db:
        yield _AccountAdmissionContext(db)


@dataclass(frozen=True, slots=True)
class ProductAnalyticsIngestResult:
    accepted: bool
    status: str
    event: ProductActivationEvent | None
    provider_results: list[ProviderDeliveryResult]
    delivery_gap: AnalyticsDeliveryGap | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "event": self.event.as_payload() if self.event else None,
            "provider_results": [result.as_dict() for result in self.provider_results],
            "delivery_gap": self.delivery_gap.as_dict() if self.delivery_gap else None,
        }


class ProductAnalyticsIngestService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ingest(
        self,
        payload: Mapping[str, Any],
        *,
        telemetry_gate_state: str = "accepted",
    ) -> ProductAnalyticsIngestResult:
        """Validate only. Legacy callers cannot count or deliver without a DB/account."""
        if not self.settings.product_analytics_enabled:
            return ProductAnalyticsIngestResult(False, "disabled", None, [])
        if not analytics_collection_allowed(telemetry_gate_state):
            return ProductAnalyticsIngestResult(False, "telemetry_gate_required", None, [])
        event = build_activation_event(
            str(payload.get("event_name", "")),
            stable_pseudonymous_user_id=payload.get("stable_pseudonymous_user_id"),
            occurred_at=_parse_occurred_at(payload.get("occurred_at")),
            properties=payload.get("properties") if isinstance(payload.get("properties"), Mapping) else {},
        )
        return ProductAnalyticsIngestResult(False, "trusted_context_required", event, [])

    async def ingest_authenticated(
        self,
        payload: Mapping[str, Any],
        *,
        principal: AuthenticatedPrincipal | None,
        sessionmaker,
        source_kind: str,
        telemetry_gate_state: str = "accepted",
    ) -> ProductAnalyticsIngestResult:
        """Common HTTP/server-auth admission. Own the transaction; never send here."""
        validated = self.ingest(payload, telemetry_gate_state=telemetry_gate_state)
        event = validated.event
        if event is None:
            return validated

        def refused(status: str) -> ProductAnalyticsIngestResult:
            return ProductAnalyticsIngestResult(False, status, None, [])

        if event.event_name == "desktop_first_opened":
            # No existing trusted install key. A client-chosen ID is not one.
            return refused("install_key_unverified")
        if principal is None:
            return refused("authentication_required")
        identity = build_safe_identity(user_source_id=str(principal.user_id)).stable_pseudonymous_user_id
        if event.stable_pseudonymous_user_id != identity or event.properties.get(
            "stable_pseudonymous_user_id", identity
        ) != identity:
            return refused("identity_mismatch")
        if source_kind not in {"desktop", "server"}:
            return refused("trigger_unverified")
        if event.event_name == "desktop_account_connected" and source_kind != "server":
            return refused("trigger_unverified")
        if event.event_name in {"first_result_viewed", "first_value_session_completed"}:
            # T112 will provide an owner/ready/visible-result server trigger.
            return refused("trigger_unverified")
        workspace_id = principal.session_workspace_id
        if workspace_id is None and len(principal.workspace_ids) == 1:
            workspace_id = next(iter(principal.workspace_ids))
        if workspace_id is None or workspace_id not in principal.workspace_ids:
            return refused("authentication_required")
        if sessionmaker is None:
            return refused("database_unavailable")
        if activation_milestone_write_blockers(self.settings):
            return refused("admission_blocked")
        try:
            async with self._account_transaction(principal, workspace_id, sessionmaker) as context:
                row, created = await self._admit_event(
                    context, event, account_id=principal.user_id, source_kind=source_kind,
                )
                saved_event = build_activation_event(
                    row.event_name,
                    stable_pseudonymous_user_id=identity,
                    occurred_at=row.occurred_at,
                    properties=row.safe_payload["properties"],
                )
        except PermissionError:
            return refused("admission_blocked")
        except Exception:  # analytics failure must not undo sign-in or a recording
            return refused("database_unavailable")
        return ProductAnalyticsIngestResult(
            True, "accepted" if created else MILESTONE_STATUS_DUPLICATE, saved_event, []
        )

    @asynccontextmanager
    async def _result_period_context(self, sessionmaker):
        """T113 has no trusted runtime verifier. No date/config/request can open it.

        Its future protected context must own its DB session and filesystem/DB
        fences through commit/cleanup, and provide started_at plus a fresh guard.
        Tests may substitute that context; the real source remains closed.
        """
        yield None

    def _check_admission(self, context: _AccountAdmissionContext) -> None:
        if activation_milestone_write_blockers(self.settings):
            raise PermissionError("milestone admission blocked")
        if context.recheck is not None:
            context.recheck()

    @asynccontextmanager
    async def _account_transaction(self, principal, workspace_id, sessionmaker, *, require_period=False):
        source = self._result_period_context(sessionmaker) if require_period else _account_session(sessionmaker)
        async with source as context:
            if context is None or (require_period and (
                not isinstance(context.started_at, datetime) or context.started_at.utcoffset() is None
                or context.started_at > datetime.now(UTC)
                or context.recheck is None
            )):
                raise PermissionError("milestone period unverified")
            # Reserve the rest of the outer 2s budget for connection cleanup.
            async with asyncio.timeout(1.5 if require_period else None):
                self._check_admission(context)
                db = context.db
                if require_period:
                    await db.execute(text("SET LOCAL lock_timeout = '250ms'"))
                    await db.execute(text("SET LOCAL statement_timeout = '500ms'"))
                await apply_tenant_context(db, WorkspaceAuthContext(
                    organization_id=principal.organization_id, workspace_id=workspace_id,
                    user_id=principal.user_id, context_kind="auth_bootstrap",
                ))
                if require_period and await db.scalar(select(UserIdentity.id).where(
                    UserIdentity.id == principal.user_id, UserIdentity.status == "active",
                ).with_for_update(read=True)) is None:
                    raise PermissionError("milestone account unavailable")
                yield context
                self._check_admission(context)
                await db.commit()

    async def _admit_event(self, context, event, *, account_id, source_kind):
        def before_insert():
            self._check_admission(context)
            return tuple(
                provider for provider in ("posthog", "yandex")
                if (provider != "yandex" or (
                    event.event_name in yandex_offline_conversion_event_names()
                    and YandexOfflineConversionExporter.from_settings(self.settings).transfer_decision(event).allowed
                ))
                and resolve_provider_delivery_gate(self.settings, provider=provider).allowed
            )

        return await admit_account_milestone(
            context.db, event, account_id=account_id,
            source_kind=source_kind, before_insert=before_insert,
        )

    async def admit_result_view(
        self, *, principal: AuthenticatedPrincipal | None, workspace_id: UUID,
        sessionmaker,
        verify_view: Callable[[AsyncSession, datetime], Awaitable[ResultViewBinding | None]],
        surface: str,
    ) -> bool:
        """Internal pair admission; the verifier must lock/recheck auth/source/proof.

        No HTTP/event payload supplies this callback or the protected period.
        No route is wired yet. A binding alone is not a fresh access decision.
        """
        if (
            principal is None or not principal.auth_via_session or principal.session_id is None
            or workspace_id not in principal.workspace_ids
            or principal.session_workspace_id != workspace_id or sessionmaker is None
            or surface not in {"cabinet_web", "cabinet_desktop"}
        ):
            return False
        try:
            async with asyncio.timeout(2):
                async with self._account_transaction(
                    principal, workspace_id, sessionmaker, require_period=True,
                ) as context:
                    binding = await verify_view(context.db, context.started_at)
                    if (
                        binding is None or binding.source.owner_id != principal.user_id
                        or binding.source.workspace_id != workspace_id
                        or binding.auth_session_id != principal.session_id
                        or binding.session_device_id != principal.session_device_id
                    ):
                        raise PermissionError("result view unavailable")
                    # Reuse the catalog builders without creating an import cycle with web routes.
                    from twobrain_rec_server.cabinet.web import (
                        build_first_result_viewed_product_analytics_payload,
                        build_first_value_product_analytics_payload,
                    )

                    identity = build_safe_identity(user_source_id=str(principal.user_id)).stable_pseudonymous_user_id
                    payloads = (
                        build_first_result_viewed_product_analytics_payload(
                            stable_pseudonymous_user_id=identity, result_state="ready",
                            useful_output_present=True, surface=surface,
                        ),
                        build_first_value_product_analytics_payload(
                            stable_pseudonymous_user_id=identity, result_state="ready",
                            useful_output_present=True, useful_result_type=binding.block_type,
                            first_recording_completed=binding.source.first_recording_completed,
                        ),
                    )
                    for payload in payloads:
                        if payload is None or (event := self.ingest(payload).event) is None:
                            raise PermissionError("result event unavailable")
                        await self._admit_event(
                            context, event, account_id=principal.user_id,
                            source_kind="browser" if surface == "cabinet_web" else "desktop",
                        )
            return True
        except Exception:
            return False


def _parse_occurred_at(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("occurred_at must be an ISO-8601 timestamp")
