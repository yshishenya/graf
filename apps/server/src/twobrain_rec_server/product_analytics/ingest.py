from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy import text
from sqlalchemy.engine import make_url

from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context
from twobrain_rec_server.product_analytics.activation_fence import activation_fence
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
        validation_mode = self.settings.product_analytics_validation_mode
        if activation_milestone_write_blockers(self.settings):
            return refused("admission_blocked")
        async def save_decision():
            async with sessionmaker() as db:
                await apply_tenant_context(db, WorkspaceAuthContext(
                    organization_id=principal.organization_id,
                    workspace_id=workspace_id,
                    user_id=principal.user_id,
                    context_kind="auth_bootstrap",
                ))
                async def before_insert() -> tuple[str, ...]:
                    # Read from this held transaction, never from the ready file.
                    rows = (await db.execute(text("""
                        SELECT pg_catalog.current_database() AS db_name, d.oid::bigint AS db_oid,
                               c.system_identifier::text AS cluster_id, a.version_num AS schema_revision,
                               u.created_at AS account_created_at, pg_catalog.clock_timestamp() AS db_now
                        FROM pg_catalog.pg_database AS d
                        CROSS JOIN pg_catalog.pg_control_system() AS c
                        CROSS JOIN public.alembic_version AS a
                        JOIN public.user_identities AS u ON u.id=:account_id
                        WHERE d.datname=pg_catalog.current_database()
                    """), {"account_id": principal.user_id})).mappings().all()
                    if (len(rows) != 1 or rows[0]["db_name"] != make_url(self.settings.database_url).database
                            or rows[0]["schema_revision"] != schema_head):
                        raise PermissionError("activation_database_binding_unverified")
                    actual = rows[0]
                    # No await after these final fresh checks: a SELECT may have
                    # waited while the operator revoked the basis or readiness.
                    if (self.settings.product_analytics_validation_mode != validation_mode
                            or activation_milestone_write_blockers(self.settings)):
                        raise PermissionError("milestone admission blocked")
                    ready = fence.read_ready(expected={
                        "source_sha": source_sha, "image_id": image_id,
                        **{key: actual[key] for key in ("cluster_id", "db_name", "db_oid", "schema_revision")},
                    })
                    if validation_mode == "local_only":
                        created = actual["account_created_at"]
                        if (created is None or created.tzinfo is None
                                or not datetime.fromisoformat(ready["started_at"]) < created <= actual["db_now"]):
                            raise PermissionError("activation_account_outside_t0")
                        if not self.settings.product_analytics_local_only_configuration_valid():
                            raise PermissionError("local_only configuration changed")
                        return ()
                    return tuple(
                        provider for provider in ("posthog", "yandex")
                        if (provider != "yandex" or (
                            event.event_name in yandex_offline_conversion_event_names()
                            and YandexOfflineConversionExporter.from_settings(self.settings).transfer_decision(event).allowed
                        ))
                        and resolve_provider_delivery_gate(self.settings, provider=provider).allowed
                    )
                row, created = await admit_account_milestone(
                    db, event, account_id=principal.user_id,
                    source_kind=source_kind, before_insert=before_insert,
                )
                saved_event = build_activation_event(
                    row.event_name,
                    stable_pseudonymous_user_id=identity,
                    occurred_at=row.occurred_at,
                    properties=row.safe_payload["properties"],
                )
                await db.commit()
            return saved_event, created

        try:
            with ExitStack() as stack:
                try:
                    source_sha = os.environ["GRAF_DEV_SOURCE_SHA"]
                    image_id = os.environ["GRAF_PRODUCT_ACTIVATION_IMAGE_ID"]
                    if (re.fullmatch(r"[0-9a-f]{40}", source_sha) is None
                            or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None):
                        return refused("admission_blocked")
                    schema_head = ScriptDirectory(str(
                        Path(__file__).resolve().parents[1] / "db" / "migrations"
                    )).get_current_head()
                    if schema_head is None:
                        return refused("admission_blocked")
                    fence = stack.enter_context(activation_fence(
                        Path(os.environ["GRAF_PRODUCT_ACTIVATION_STATE_FILE"]),
                        owner_uid=int(os.environ["GRAF_PRODUCT_ACTIVATION_OWNER_UID"]),
                    ))
                except (KeyError, ValueError, OSError, CommandError):
                    return refused("admission_blocked")
                # AsyncSession.__aexit__ shields a separate close task. Keep one
                # uncancelled owner of the entire session, including that close,
                # so repeated request cancellation cannot release SH early.
                operation = asyncio.create_task(save_decision())
                cancelled = None
                while True:
                    try:
                        await asyncio.shield(operation)
                        break
                    except asyncio.CancelledError as exc:
                        if cancelled is None:
                            cancelled = exc
                        if operation.done():
                            break
                    except Exception:
                        break  # Extract the owner's exception below, even after cancellation.
                try:
                    saved_event, created = operation.result()
                finally:
                    if cancelled is not None:
                        raise cancelled
        except PermissionError:
            return refused("admission_blocked")
        except Exception:  # analytics failure must not undo sign-in or a recording
            return refused("database_unavailable")
        return ProductAnalyticsIngestResult(
            True, "accepted" if created else MILESTONE_STATUS_DUPLICATE, saved_event, []
        )


def _parse_occurred_at(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("occurred_at must be an ISO-8601 timestamp")
