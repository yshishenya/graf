"""Shared writer gate for legal-basis withdrawals (FR-048).

The lifecycle module describes and executes a basis-loss disposition.  This
module is the small request-path guard used immediately before level 1 and
level 2 writes.  It deliberately does not call providers, alter readiness, or
raise into a public page/auth flow: measurement remains best-effort, while a
recorded withdrawal stops only the affected level.

A missing register is compatible with the existing rollout.  It means that no
withdrawal is currently recorded, not that every writer should fail and take
the product down.  Unknown writer levels and an explicitly disabled level are
still refused before a SQL statement can be constructed/executed.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    ANONYMOUS_AGGREGATE_LEVEL,
    ATTRIBUTION_PROFILES_LEVEL,
    BasisWithdrawal,
    read_basis_withdrawal_register,
)

logger = logging.getLogger(__name__)

# The writer gate is intentionally limited to the locally owned levels requested
# by FR-048.  Provider writers have their own provider/consent gate and are not
# changed here.
WRITER_LEVELS = (ANONYMOUS_AGGREGATE_LEVEL, ATTRIBUTION_PROFILES_LEVEL)

WRITE_ALLOWED = "allowed"
WRITE_BLOCKED_WITHDRAWN = "legal_basis_withdrawn"
WRITE_BLOCKED_SETTINGS = "measurement_level_disabled"
WRITE_BLOCKED_UNKNOWN_LEVEL = "unknown_measurement_level"


@dataclass(frozen=True, slots=True)
class LegalBasisWriteDecision:
    """Owned scalar decision returned by the shared writer gate."""

    level_key: str
    allowed: bool
    reason: str
    withdrawal: BasisWithdrawal | None = None

    @property
    def blocked(self) -> bool:
        return not self.allowed


def legal_basis_write_gate(
    level_key: str,
    *,
    settings: Settings | Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> LegalBasisWriteDecision:
    """Decide whether a local analytics writer may perform its SQL write.

    The decision is deliberately cheap and synchronous so callers can check it
    before building/executing a SQL statement.  ``environ`` is injectable for
    tests and for operator-managed state-file locations; production callers use
    the process environment through :func:`read_basis_withdrawal_register`.

    Level 1 honours its existing explicit setting.  Level 2 has no independent
    writer switch in the current product: its existing best-effort registration
    and visit writes remain enabled unless their legal basis is explicitly
    withdrawn.  In particular, ``product_analytics_enabled`` is not consulted
    here because it controls the optional provider rollout, not these existing
    local registration paths.
    """

    if level_key not in WRITER_LEVELS:
        return LegalBasisWriteDecision(
            level_key=level_key,
            allowed=False,
            reason=WRITE_BLOCKED_UNKNOWN_LEVEL,
        )

    runtime_settings = settings if settings is not None else _safe_get_settings()
    if level_key == ANONYMOUS_AGGREGATE_LEVEL and not bool(
        getattr(runtime_settings, "product_analytics_anonymous_aggregate_enabled", True)
    ):
        return LegalBasisWriteDecision(
            level_key=level_key,
            allowed=False,
            reason=WRITE_BLOCKED_SETTINGS,
        )

    # A missing/unreadable register is not treated as a global product outage:
    # there is no affected level to stop.  A valid recorded withdrawal is the
    # only state that blocks an otherwise configured writer.
    register = read_basis_withdrawal_register(environ)
    withdrawal = register.withdrawal(level_key)
    if withdrawal is not None:
        return LegalBasisWriteDecision(
            level_key=level_key,
            allowed=False,
            reason=WRITE_BLOCKED_WITHDRAWN,
            withdrawal=withdrawal,
        )

    return LegalBasisWriteDecision(
        level_key=level_key,
        allowed=True,
        reason=WRITE_ALLOWED,
    )


def legal_basis_write_allowed(
    level_key: str,
    *,
    settings: Settings | Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return only the boolean used by simple best-effort writer wrappers."""

    return legal_basis_write_gate(level_key, settings=settings, environ=environ).allowed


def _safe_get_settings() -> Settings | Any:
    """Read process settings without turning a measurement check into an outage."""

    try:
        return get_settings()
    except Exception as exc:  # noqa: BLE001 - page/auth behaviour is best effort
        logger.warning("analytics legal-basis settings were unavailable: error=%s", exc.__class__.__name__)
        # The level 1 setting defaults on when no settings object can be read;
        # the withdrawal register remains authoritative for explicit basis loss.
        return None


__all__ = [
    "LegalBasisWriteDecision",
    "WRITE_ALLOWED",
    "WRITE_BLOCKED_SETTINGS",
    "WRITE_BLOCKED_UNKNOWN_LEVEL",
    "WRITE_BLOCKED_WITHDRAWN",
    "WRITER_LEVELS",
    "legal_basis_write_allowed",
    "legal_basis_write_gate",
]
