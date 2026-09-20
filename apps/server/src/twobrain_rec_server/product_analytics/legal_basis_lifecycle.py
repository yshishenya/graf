"""Ending processing when the legal basis of a measurement level falls away (FR-048).

A measurement level exists because it has a legal basis. When that basis is
gone, three things have to happen in this order and none of them is optional:

1. **processing stops** — :func:`level_processing_allowed` answers ``False`` for
   every level whose basis is not confirmed, and the transfer path refuses the
   advertising transfer of that level (:mod:`advertising_transfer`);
2. **the affected data is deleted or anonymised** — :func:`plan_processing_stop`
   derives one action per registered retention category of the level, and
   :func:`apply_basis_loss_disposition` executes the ones GRAF stores itself;
3. **the deadline comes from the retention rules** — every action carries
   ``due_at = basis_lost_at + enforced retention term`` read from
   :mod:`retention`, so FR-048 introduces no new number and cannot drift away
   from FR-036 and FR-050.

A level owns the registered retention categories declared in
:data:`LEVEL_RETENTION_CATEGORIES`. A category without a declared disposition is
a configuration error, never an implicit "keep it": the same fail-closed rule
FR-050 applies to a missing term.

What this module cannot do by itself: level 3 data lives in a provider
(ClickHouse inside PostHog and the Yandex counter), so its disposition is a
provider request and the evidence records the method and the deadline instead of
pretending a local delete happened.

The withdrawal records live outside git in the metadata-only state-file format
the launch approvals and the scheduled operations tasks already use.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from twobrain_rec_server.product_analytics.advertising_transfer import (
    REASON_PATTERN,
    AdvertisingTransferTraceViolation,
    evidence_reference_token,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_forbidden_fields,
    find_security_credential_fields,
)
from twobrain_rec_server.product_analytics.provider_config import (
    ANONYMOUS_AGGREGATE_RETENTION_CATEGORY,
    ATTRIBUTION_PROFILES_RETENTION_CATEGORY,
    MEASUREMENT_LEVEL_KEYS,
    PROVIDER_ANALYTICS_RETENTION_CATEGORY,
    ProductAnalyticsProviderConfig,
)
from twobrain_rec_server.product_analytics.retention import (
    AnalyticsRetentionRule,
    retention_deadline,
    retention_rule,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.ext.asyncio import AsyncSession

ANONYMOUS_AGGREGATE_LEVEL = "anonymous_aggregate"
ATTRIBUTION_PROFILES_LEVEL = "attribution_profiles"
PROVIDER_ANALYTICS_LEVEL = "provider_analytics"

# The retention categories each level stores its data under. Level 1 owns the
# aggregate only. Level 2 owns the visit attribution window and the campaign
# attribute copied onto the account. Level 3 owns what the providers hold: the
# product events, the provider page events and the offline conversions that
# FR-028 governs.
LEVEL_RETENTION_CATEGORIES: Mapping[str, tuple[str, ...]] = {
    ANONYMOUS_AGGREGATE_LEVEL: (ANONYMOUS_AGGREGATE_RETENTION_CATEGORY,),
    ATTRIBUTION_PROFILES_LEVEL: (
        ATTRIBUTION_PROFILES_RETENTION_CATEGORY,
        "visit_attribution",
    ),
    PROVIDER_ANALYTICS_LEVEL: (
        PROVIDER_ANALYTICS_RETENTION_CATEGORY,
        "yandex_page_events",
        "yandex_offline_conversions",
    ),
}

# The legal basis each level rests on, named so a report can show what was lost.
LEVEL_BASIS_KINDS: Mapping[str, str] = {
    ANONYMOUS_AGGREGATE_LEVEL: "no_personal_data",
    ATTRIBUTION_PROFILES_LEVEL: "contract_and_legitimate_interest",
    PROVIDER_ANALYTICS_LEVEL: "consent",
}

LEGAL_BASIS_CONFIRMED = "confirmed"
LEGAL_BASIS_NOT_CONFIRMED = "not_confirmed"
LEGAL_BASIS_WITHDRAWN = "withdrawn"
LEGAL_BASIS_STATES = (
    LEGAL_BASIS_CONFIRMED,
    LEGAL_BASIS_NOT_CONFIRMED,
    LEGAL_BASIS_WITHDRAWN,
)

PROCESSING_STATE_STOPPED = "stopped"

# How an affected category is dealt with. ``delete`` removes the rows, and
# ``anonymise`` removes the attribution values while the record itself stays
# (FR-048 allows either).
DISPOSITION_DELETE = "delete"
DISPOSITION_ANONYMISE = "anonymise"
DISPOSITIONS = (DISPOSITION_DELETE, DISPOSITION_ANONYMISE)

# GRAF deletes its own rows, and asks a provider for what the provider holds.
EXECUTION_LOCAL = "local_delete_or_anonymise"
EXECUTION_PROVIDER_REQUEST = "provider_deletion_request"

# What happens to each registered category when its level loses its basis. The
# choice follows the retention rule of the category: the aggregate carries no
# identifier and is simply removed, the campaign attribute is part of an account
# record and is anonymised in place, and the provider-held categories can only be
# requested from the provider.
CATEGORY_DISPOSITIONS: Mapping[str, str] = {
    ANONYMOUS_AGGREGATE_RETENTION_CATEGORY: DISPOSITION_DELETE,
    ATTRIBUTION_PROFILES_RETENTION_CATEGORY: DISPOSITION_ANONYMISE,
    "visit_attribution": DISPOSITION_DELETE,
    PROVIDER_ANALYTICS_RETENTION_CATEGORY: DISPOSITION_DELETE,
    "yandex_page_events": DISPOSITION_DELETE,
    "yandex_offline_conversions": DISPOSITION_DELETE,
}

BASIS_WITHDRAWAL_STATE_FILE_ENV = "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE"
BASIS_WITHDRAWAL_STATE_DIR_ENV = "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_DIR"
DEFAULT_BASIS_WITHDRAWAL_STATE_DIR = "/var/lib/graf-product-analytics-legal-basis"
DEFAULT_BASIS_WITHDRAWAL_STATE_NAME = "legal-basis-withdrawals"
BASIS_WITHDRAWAL_STATE_VERSION = "1"
WITHDRAWAL_RECORD_KEYWORD = "basis_withdrawal"


class LegalBasisLifecycleError(ValueError):
    """Raised when a level or a category has no declared lifecycle."""


@dataclass(frozen=True, slots=True)
class LevelLegalBasis:
    """The basis of one measurement level, as it stands right now."""

    level_key: str
    basis_kind: str
    state: str
    reason: str | None = None
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    evidence_ref: str | None = None

    @property
    def processing_allowed(self) -> bool:
        return self.state == LEGAL_BASIS_CONFIRMED

    def as_dict(self) -> dict[str, Any]:
        return {
            "level_key": self.level_key,
            "basis_kind": self.basis_kind,
            "state": self.state,
            "reason": self.reason,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class BasisWithdrawal:
    """One recorded moment at which the basis of a level stopped holding."""

    level_key: str
    withdrawn_at: str
    reason: str
    evidence_ref: str | None = None

    def withdrawn_on(self) -> date:
        return date.fromisoformat(self.withdrawn_at)

    def as_dict(self) -> dict[str, Any]:
        return {
            "level_key": self.level_key,
            "withdrawn_at": self.withdrawn_at,
            "reason": self.reason,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class BasisWithdrawalRegister:
    available: bool
    state_path: str
    withdrawals: tuple[BasisWithdrawal, ...] = ()
    file_errors: tuple[str, ...] = ()

    def withdrawal(self, level_key: str) -> BasisWithdrawal | None:
        for record in self.withdrawals:
            if record.level_key == level_key:
                return record
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "state_path": self.state_path,
            "file_errors": list(self.file_errors),
            "withdrawals": [record.as_dict() for record in self.withdrawals],
        }


@dataclass(frozen=True, slots=True)
class LegalBasisLossAction:
    """One category to delete or anonymise, with its retention-derived deadline."""

    category: str
    storage: str
    enforcement: str
    disposition: str
    method: str
    deletion_truth: str
    retention_days: int
    due_at: datetime
    execution: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "storage": self.storage,
            "enforcement": self.enforcement,
            "disposition": self.disposition,
            "method": self.method,
            "deletion_truth": self.deletion_truth,
            "retention_days": self.retention_days,
            "due_at": self.due_at.isoformat(),
            "execution": self.execution,
        }


@dataclass(frozen=True, slots=True)
class LegalBasisLossDisposition:
    """The plan for one level whose basis fell away: stop, then erase in term."""

    level_key: str
    reason: str
    basis_lost_at: datetime
    processing_state: str
    actions: tuple[LegalBasisLossAction, ...]

    @property
    def deadline(self) -> datetime:
        """The binding deadline: every action must be done by its own term."""

        return min(action.due_at for action in self.actions)

    def as_dict(self) -> dict[str, Any]:
        return {
            "level_key": self.level_key,
            "reason": self.reason,
            "basis_lost_at": self.basis_lost_at.isoformat(),
            "processing_state": self.processing_state,
            "deadline": self.deadline.isoformat(),
            "actions": [action.as_dict() for action in self.actions],
        }


@dataclass(frozen=True, slots=True)
class BasisLossErasureResult:
    """What actually happened to one category, as metadata-only evidence."""

    level_key: str
    category: str
    disposition: str
    execution: str
    rows_affected: int
    due_at: datetime
    erased_at: datetime

    @property
    def within_deadline(self) -> bool:
        return self.erased_at <= self.due_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "level_key": self.level_key,
            "category": self.category,
            "disposition": self.disposition,
            "execution": self.execution,
            "rows_affected": self.rows_affected,
            "due_at": self.due_at.isoformat(),
            "erased_at": self.erased_at.isoformat(),
            "within_deadline": self.within_deadline,
        }


# --- Basis state ------------------------------------------------------------


def level_retention_categories(level_key: str) -> tuple[str, ...]:
    categories = LEVEL_RETENTION_CATEGORIES.get(level_key)
    if not categories:
        raise LegalBasisLifecycleError(f"measurement level has no declared storage: {level_key}")
    return categories


def level_basis_kind(level_key: str) -> str:
    basis_kind = LEVEL_BASIS_KINDS.get(level_key)
    if basis_kind is None:
        raise LegalBasisLifecycleError(f"measurement level has no declared legal basis: {level_key}")
    return basis_kind


def measurement_level_basis_states(
    config: ProductAnalyticsProviderConfig,
    *,
    withdrawals: BasisWithdrawalRegister | None = None,
) -> tuple[LevelLegalBasis, ...]:
    """Describe the basis of every level, and whether it still holds.

    A level that is switched off is ``not_confirmed`` and a level with a
    recorded withdrawal is ``withdrawn``. Both stop processing, and the record
    says which of the two happened, because only the second one means data that
    was collected under a basis now has to be erased.
    """

    register = withdrawals if withdrawals is not None else BasisWithdrawalRegister(False, "")
    states: list[LevelLegalBasis] = []
    for level in config.measurement_levels:
        withdrawal = register.withdrawal(level.key)
        if withdrawal is not None:
            states.append(
                LevelLegalBasis(
                    level_key=level.key,
                    basis_kind=level_basis_kind(level.key),
                    state=LEGAL_BASIS_WITHDRAWN,
                    reason=withdrawal.reason,
                    confirmed_at=withdrawal.withdrawn_at,
                    evidence_ref=withdrawal.evidence_ref,
                )
            )
            continue
        states.append(
            LevelLegalBasis(
                level_key=level.key,
                basis_kind=level_basis_kind(level.key),
                state=LEGAL_BASIS_CONFIRMED if level.enabled else LEGAL_BASIS_NOT_CONFIRMED,
                reason=None if level.enabled else "level_not_enabled",
            )
        )
    return tuple(states)


def level_processing_allowed(
    level_key: str,
    bases: Iterable[LevelLegalBasis],
) -> bool:
    """Whether the level may process anything at all.

    Fail closed: an unknown level and a level without a confirmed basis are both
    refused, so a caller cannot process first and ask later.
    """

    for basis in bases:
        if basis.level_key == level_key:
            return basis.processing_allowed
    return False


def withdrawn_level_keys(bases: Iterable[LevelLegalBasis]) -> tuple[str, ...]:
    return tuple(basis.level_key for basis in bases if basis.state == LEGAL_BASIS_WITHDRAWN)


# --- Withdrawal records -----------------------------------------------------


def basis_withdrawal_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(BASIS_WITHDRAWAL_STATE_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(BASIS_WITHDRAWAL_STATE_DIR_ENV) or DEFAULT_BASIS_WITHDRAWAL_STATE_DIR
    return os.path.join(directory, DEFAULT_BASIS_WITHDRAWAL_STATE_NAME)


def read_basis_withdrawal_register(
    environ: Mapping[str, str] | None = None,
    *,
    today: date | None = None,
) -> BasisWithdrawalRegister:
    """Read the recorded withdrawals; an unreadable file is reported, not guessed."""

    path = basis_withdrawal_state_file_path(environ)
    try:
        with open(path, encoding="utf-8") as state_file:
            text = state_file.read()
    except (OSError, UnicodeError):
        # No file means no recorded withdrawal. That is not a permission to
        # keep data: processing is still stopped wherever the basis is not
        # confirmed, and this register only ever *adds* a lost basis.
        return BasisWithdrawalRegister(available=False, state_path=path)

    file_errors: list[str] = []
    if _header_value(text) != BASIS_WITHDRAWAL_STATE_VERSION:
        file_errors.append("legal_basis_state_version_unsupported")

    current_day = date.today() if today is None else today
    withdrawals: list[BasisWithdrawal] = []
    for record in _records(text):
        withdrawal = _withdrawal_record(record, today=current_day)
        if withdrawal is not None:
            withdrawals.append(withdrawal)
    return BasisWithdrawalRegister(
        available=True,
        state_path=path,
        withdrawals=tuple(withdrawals),
        file_errors=tuple(file_errors),
    )


def _header_value(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.split(maxsplit=1)[0] == WITHDRAWAL_RECORD_KEYWORD:
            break
        name, separator, value = stripped.partition("=")
        if separator and name.strip() == "legal_basis_state_version":
            return value.strip()
    return None


def _records(text: str) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.split(maxsplit=1)[0] == WITHDRAWAL_RECORD_KEYWORD:
            current = {}
            records.append(current)
            stripped = stripped[len(WITHDRAWAL_RECORD_KEYWORD) :].strip()
        elif current is None:
            continue
        for token in stripped.split():
            name, separator, value = token.partition("=")
            if separator:
                current.setdefault(name, value)
    return tuple(records)


def _withdrawal_record(record: Mapping[str, str], *, today: date) -> BasisWithdrawal | None:
    level_key = record.get("level") or ""
    if level_key not in MEASUREMENT_LEVEL_KEYS:
        return None
    if record.get("state") != LEGAL_BASIS_WITHDRAWN:
        return None
    withdrawn_at = record.get("withdrawn_at") or ""
    try:
        withdrawn_on = date.fromisoformat(withdrawn_at)
    except ValueError:
        return None
    if withdrawn_on > today:
        # A withdrawal dated in the future has not happened yet.
        return None
    reason = record.get("reason") or "unspecified"
    if REASON_PATTERN.fullmatch(reason) is None:
        return None
    raw_evidence_ref = record.get("evidence_ref")
    evidence_ref = evidence_reference_token(raw_evidence_ref) if raw_evidence_ref else None
    if raw_evidence_ref and evidence_ref is None:
        # An evidence reference stays an ASCII token: a value that is not one is
        # dropped instead of being copied into the evidence lines.
        return None
    return BasisWithdrawal(
        level_key=level_key,
        withdrawn_at=withdrawn_at,
        reason=reason,
        evidence_ref=evidence_ref,
    )


# --- The plan ---------------------------------------------------------------


def plan_processing_stop(
    *,
    level_key: str,
    basis_lost_at: datetime,
    reason: str,
    affected_categories: Iterable[str] | None = None,
) -> LegalBasisLossDisposition:
    """Stop the level and put every affected category on a dated clock (FR-048).

    The deadline of each action is the enforced retention term of its own
    category, read from :mod:`retention`. An unknown category, or a category
    without a declared disposition, is a configuration error: guessing a term
    here would be exactly the "keep it forever" default FR-050 forbids.
    """

    moment = _aware(basis_lost_at)
    categories = tuple(affected_categories) if affected_categories is not None else (
        level_retention_categories(level_key)
    )
    if not categories:
        raise LegalBasisLifecycleError(f"level {level_key} has no affected category")
    actions = tuple(_loss_action(category, since=moment) for category in categories)
    return LegalBasisLossDisposition(
        level_key=level_key,
        reason=reason,
        basis_lost_at=moment,
        processing_state=PROCESSING_STATE_STOPPED,
        actions=actions,
    )


def _loss_action(category: str, *, since: datetime) -> LegalBasisLossAction:
    disposition = CATEGORY_DISPOSITIONS.get(category)
    if disposition is None:
        raise LegalBasisLifecycleError(
            f"retention category {category!r} has no declared basis-loss disposition"
        )
    rule = retention_rule(category)
    return LegalBasisLossAction(
        category=category,
        storage=rule.storage,
        enforcement=rule.enforcement,
        disposition=disposition,
        method=rule.provider_delete_method,
        deletion_truth=rule.deletion_truth,
        retention_days=rule.enforced_retention_days(),
        due_at=retention_deadline(rule, since=since),
        execution=(
            EXECUTION_LOCAL if _is_graf_stored(rule) else EXECUTION_PROVIDER_REQUEST
        ),
    )


def _is_graf_stored(rule: AnalyticsRetentionRule) -> bool:
    """Whether GRAF itself can delete the rows of this category right now."""

    return rule.storage == "graf_postgres" and rule.enforcement == "scheduled_purge"


def lost_basis_dispositions(
    config: ProductAnalyticsProviderConfig,
    *,
    withdrawals: BasisWithdrawalRegister,
    now: datetime,
) -> tuple[LegalBasisLossDisposition, ...]:
    """One plan per level whose basis was withdrawn, dated by the record."""

    moment = _aware(now)
    plans: list[LegalBasisLossDisposition] = []
    for level_key in withdrawn_level_keys(
        measurement_level_basis_states(config, withdrawals=withdrawals)
    ):
        withdrawal = withdrawals.withdrawal(level_key)
        if withdrawal is None:  # pragma: no cover - withdrawn_level_keys implies a record
            continue
        lost_at = datetime.combine(withdrawal.withdrawn_on(), datetime.min.time(), tzinfo=UTC)
        if lost_at > moment:
            lost_at = moment
        plans.append(
            plan_processing_stop(
                level_key=level_key,
                basis_lost_at=lost_at,
                reason=withdrawal.reason,
            )
        )
    return tuple(plans)


# --- The execution ----------------------------------------------------------


async def apply_basis_loss_disposition(
    session: AsyncSession,
    disposition: LegalBasisLossDisposition,
    *,
    erased_at: datetime | None = None,
    commit: bool = True,
) -> tuple[BasisLossErasureResult, ...]:
    """Erase or anonymise what GRAF stores, and record the provider requests.

    The erasure happens immediately, which is necessarily within the retention
    deadline. Categories the provider holds cannot be deleted from here, so
    their result carries ``rows_affected = 0`` and the recorded method; the
    deadline in :class:`BasisLossErasureResult` is what the operator is held to.
    """

    # Imported here so the planner, the readiness report and the tests can use
    # the lifecycle without loading the ORM.
    from sqlalchemy import delete, update

    from twobrain_rec_server.db.models.product_analytics import (
        AnonymousPageAggregateBucket,
        ClientAcquisitionAttribute,
        PublicVisitAttribution,
    )

    moment = _aware(erased_at or datetime.now(UTC))
    results: list[BasisLossErasureResult] = []
    for action in disposition.actions:
        if action.execution != EXECUTION_LOCAL:
            results.append(
                _result(disposition, action, rows=0, erased_at=moment)
            )
            continue
        if action.category == ANONYMOUS_AGGREGATE_RETENTION_CATEGORY:
            statement = delete(AnonymousPageAggregateBucket)
        elif action.category == "visit_attribution":
            statement = delete(PublicVisitAttribution)
        elif action.category == ATTRIBUTION_PROFILES_RETENTION_CATEGORY:
            statement = update(ClientAcquisitionAttribute).values(
                source=None,
                medium=None,
                campaign=None,
                content=None,
                term=None,
                yclid=None,
            )
        else:  # pragma: no cover - a new local category must declare its statement
            raise LegalBasisLifecycleError(
                f"retention category {action.category!r} has no erasure statement"
            )
        outcome = await session.execute(statement)
        results.append(
            _result(disposition, action, rows=int(outcome.rowcount or 0), erased_at=moment)
        )
    if commit:
        await session.commit()
    return tuple(results)


def _result(
    disposition: LegalBasisLossDisposition,
    action: LegalBasisLossAction,
    *,
    rows: int,
    erased_at: datetime,
) -> BasisLossErasureResult:
    return BasisLossErasureResult(
        level_key=disposition.level_key,
        category=action.category,
        disposition=action.disposition,
        execution=action.execution,
        rows_affected=rows,
        due_at=action.due_at,
        erased_at=erased_at,
    )


def basis_loss_evidence_lines(
    results: Iterable[BasisLossErasureResult],
    *,
    reason: str,
) -> tuple[str, ...]:
    """Render metadata-only evidence: what was erased, and by when it had to be."""

    lines: list[str] = []
    for result in results:
        payload = {**result.as_dict(), "reason": reason}
        assert_metadata_only_evidence(payload)
        lines.append(
            "basis_loss "
            f"level={result.level_key} "
            f"category={result.category} "
            f"disposition={result.disposition} "
            f"execution={result.execution} "
            f"rows_affected={result.rows_affected} "
            f"due_at={result.due_at.date().isoformat()} "
            f"erased_at={result.erased_at.date().isoformat()} "
            f"within_deadline={str(result.within_deadline).lower()} "
            f"reason={reason}"
        )
    return tuple(lines)


def assert_metadata_only_evidence(payload: Mapping[str, Any]) -> None:
    """Refuse evidence that carries personal data or a credential."""

    findings = find_forbidden_fields(payload) + find_security_credential_fields(payload)
    unique = tuple(dict.fromkeys(findings))
    if unique:
        raise AdvertisingTransferTraceViolation(unique)


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


__all__ = [
    "ANONYMOUS_AGGREGATE_LEVEL",
    "ATTRIBUTION_PROFILES_LEVEL",
    "BASIS_WITHDRAWAL_STATE_FILE_ENV",
    "BasisLossErasureResult",
    "BasisWithdrawal",
    "BasisWithdrawalRegister",
    "CATEGORY_DISPOSITIONS",
    "DISPOSITION_ANONYMISE",
    "DISPOSITION_DELETE",
    "EXECUTION_LOCAL",
    "EXECUTION_PROVIDER_REQUEST",
    "LEGAL_BASIS_CONFIRMED",
    "LEGAL_BASIS_NOT_CONFIRMED",
    "LEGAL_BASIS_WITHDRAWN",
    "LEVEL_BASIS_KINDS",
    "LEVEL_RETENTION_CATEGORIES",
    "LegalBasisLifecycleError",
    "LegalBasisLossAction",
    "LegalBasisLossDisposition",
    "LevelLegalBasis",
    "PROCESSING_STATE_STOPPED",
    "PROVIDER_ANALYTICS_LEVEL",
    "apply_basis_loss_disposition",
    "basis_loss_evidence_lines",
    "basis_withdrawal_state_file_path",
    "level_basis_kind",
    "level_processing_allowed",
    "level_retention_categories",
    "lost_basis_dispositions",
    "measurement_level_basis_states",
    "plan_processing_stop",
    "read_basis_withdrawal_register",
    "withdrawn_level_keys",
]
