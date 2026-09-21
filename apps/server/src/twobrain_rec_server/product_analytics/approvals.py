"""Launch approvals of feature 273: who confirmed what and when (FR-044, FR-047).

A paid campaign launch is authorised by *records*, never by a configuration
flag. A flag says only "this server may talk to a provider"; it cannot say that
a named role reviewed a named thing on a named date. The two are therefore kept
apart:

* :mod:`provider_config` and :mod:`readiness` keep reading the technical flags
  for provider setup and smoke work;
* the launch gate reads :func:`build_launch_approval_gate`, which is derived
  from the approval state file and stays blocked for any missing, unparseable
  or expired record.

The records live outside git, in the metadata-only state-file format already
used by the scheduled operations tasks (`backup-state`, `restore-state`,
`retention-state`). Only role identifiers cross into the repository: a person's
name, an email address or a live link must never be written into a record, and
the parser refuses a record whose approver is not a role identifier.

File format (one record per line, first value of a key wins)::

    approval_state_version=1
    approval kind=legal state=recorded approved_by=product_owner
      approved_at=2026-09-18 scope=levels_1_and_2_legal_basis evidence_ref=...
    approval kind=privacy state=recorded approved_by=privacy_reviewer ...
    approval kind=rollback state=recorded approved_by=infra_operator ...
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from twobrain_rec_server.config import Settings

# The approval register is a separate category from the backup, restore and
# retention evidence, so it gets its own directory instead of sharing the
# backup state directory.
APPROVAL_STATE_FILE_ENV = "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE"
APPROVAL_STATE_DIR_ENV = "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_DIR"
DEFAULT_APPROVAL_STATE_DIR = "/var/lib/graf-product-analytics-approvals"
DEFAULT_APPROVAL_STATE_NAME = "launch-approvals"
APPROVAL_STATE_VERSION = "1"
APPROVAL_RECORD_KEYWORD = "approval"

# Approval states of `data-model.md` §"Одобрение запуска".
APPROVAL_STATE_MISSING = "missing"
APPROVAL_STATE_RECORDED = "recorded"
APPROVAL_STATE_EXPIRED = "expired"
APPROVAL_STATE_UNREADABLE = "unreadable"
APPROVAL_STATES = (
    APPROVAL_STATE_MISSING,
    APPROVAL_STATE_RECORDED,
    APPROVAL_STATE_EXPIRED,
    APPROVAL_STATE_UNREADABLE,
)

# An approver is a role, not a person. The pattern is the same snake_case role
# vocabulary the alert rules already use (`infra_operator`,
# `analytics_operator`, `product_owner`), so a record that carries a personal
# name, an email address or a link is rejected instead of being trusted.
APPROVER_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,39}$")
APPROVAL_SCOPE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,79}$")
FORBIDDEN_APPROVER_MARKERS = ("@", "http://", "https://", "/", "\\")

# Every kind authorises the launch, so no kind may be skipped: a record that is
# absent, unreadable or expired withholds the permission (FR-044).
APPROVAL_KINDS = ("legal", "privacy", "security", "qa", "rollback", "delivery", "check")
REQUIRED_APPROVAL_KINDS = APPROVAL_KINDS


@dataclass(frozen=True, slots=True)
class LaunchApprovalKindSpec:
    kind: str
    title: str
    requirement: str
    confirmed_by_role: str
    instruction: str


# `contracts/operations.md` §"Состояние готовности и одобрения" names six kinds:
# legal, privacy, security, check, rollback, delivery. This module records seven
# because `qa` is the verification evidence FR-044 asks for on top of the review
# kinds, and it already exists as a readiness state.
LAUNCH_APPROVAL_KIND_SPECS: tuple[LaunchApprovalKindSpec, ...] = (
    LaunchApprovalKindSpec(
        "legal",
        "Legal basis of measurement levels 1 and 2",
        "FR-047",
        "product_owner",
        "The content review happened on 2026-09-18 (legal-basis.md); the owner "
        "still records it here, because a verbal confirmation is not a record.",
    ),
    LaunchApprovalKindSpec(
        "privacy",
        "Privacy review of the measured scope",
        "FR-047",
        "privacy_reviewer",
        "Confirm the three measurement levels and the forbidden-value list.",
    ),
    LaunchApprovalKindSpec(
        "security",
        "Security review of access and provider boundaries",
        "FR-047",
        "security_reviewer",
        "Confirm access model, provider boundary and credential suppression.",
    ),
    LaunchApprovalKindSpec(
        "qa",
        "Verification of the measured result",
        "FR-044",
        "qa_reviewer",
        "Confirm the funnel and the readiness evidence actually observed.",
    ),
    LaunchApprovalKindSpec(
        "rollback",
        "Measurement rollback rehearsal",
        "FR-045",
        "infra_operator",
        "Rehearse the rollback on a live scenario; a description is not enough.",
    ),
    LaunchApprovalKindSpec(
        "delivery",
        "Provider delivery schedule in the cabinet",
        "FR-044",
        "analytics_operator",
        "The provider retention and delivery setting lives in the cabinet and "
        "can only be checked there.",
    ),
    LaunchApprovalKindSpec(
        "check",
        "Standalone paid launch decision",
        "FR-044",
        "release_owner",
        "Lifting the paid launch block is a separate release decision; the "
        "review below only reports the state.",
    ),
)

BLOCKER_APPROVAL_STATE_FILE_UNAVAILABLE = "approval_state_file_unavailable"
BLOCKER_APPROVAL_STATE_VERSION_UNSUPPORTED = "approval_state_version_unsupported"
BLOCKER_APPROVAL_KIND_MISSING = "approval_missing"
BLOCKER_APPROVAL_KIND_EXPIRED = "approval_expired"
BLOCKER_APPROVAL_KIND_UNREADABLE = "approval_unreadable"
BLOCKER_APPROVAL_RECORD_COUNT = "approval_record_count_mismatch"

# Technical configuration that must hold for a paid campaign to run at all.
# These are the readiness blocker labels raised by `readiness.py`; listing them
# here keeps the launch gate from approving a launch while the measurement
# configuration itself is blocked.
CAMPAIGN_CONFIGURATION_BLOCKERS = (
    "product_analytics_disabled",
    "validation_mode_disabled",
    "posthog_not_ready",
    "analytics_operations_not_ready",
    "live_provider_delivery_not_approved",
    "yandex_all_pages_not_ready",
    "yandex_offline_not_ready",
    # A withdrawn level basis has to stop a paid launch, not only lower the
    # readiness verdict: launching traffic while a level may no longer process
    # would spend money on measurement that must not run (FR-044, FR-048).
    "legal_basis_withdrawn",
    "analytics_access_governance_not_ready",
    "legal_not_approved",
    "dashboard_not_ready",
    "provider_smoke_not_approved",
    "provider_disabled",
    "posthog_disabled",
    "yandex_all_pages_disabled",
    "yandex_offline_disabled",
    "missing_posthog_host",
    "missing_posthog_project_key_file",
    "missing_yandex_counter_id",
    "missing_yandex_oauth_token_file",
)


@dataclass(frozen=True, slots=True)
class LaunchApproval:
    """One recorded approval: who confirmed what, and when."""

    kind: str
    state: str
    approved_by: str | None = None
    approved_at: str | None = None
    scope: str | None = None
    evidence_ref: str | None = None
    valid_until: str | None = None
    max_age_days: int | None = None
    reason: str | None = None

    @property
    def recorded(self) -> bool:
        return self.state == APPROVAL_STATE_RECORDED

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "state": self.state,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "scope": self.scope,
            "evidence_ref": self.evidence_ref,
            "valid_until": self.valid_until,
            "max_age_days": self.max_age_days,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class LaunchApprovalRegister:
    """Every launch approval kind, including the ones still missing."""

    available: bool
    state_path: str
    approvals: dict[str, LaunchApproval]
    file_errors: tuple[str, ...] = ()

    def approval(self, kind: str) -> LaunchApproval:
        return self.approvals.get(kind) or LaunchApproval(kind, APPROVAL_STATE_MISSING)

    def missing_kinds(self) -> tuple[str, ...]:
        return tuple(
            kind for kind in APPROVAL_KINDS if self.approval(kind).state != APPROVAL_STATE_RECORDED
        )

    def as_dict(self, *, include_records: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "available": self.available,
            # The state file is operator infrastructure, not API data.  Never
            # expose its absolute path through readiness/catalog responses.
            "states": {kind: self.approval(kind).state for kind in APPROVAL_KINDS},
            "kinds": [spec.kind for spec in LAUNCH_APPROVAL_KIND_SPECS],
            "missing_kinds": list(self.missing_kinds()),
            "file_errors": list(self.file_errors),
        }
        if include_records:
            payload["records"] = [self.approval(kind).as_dict() for kind in APPROVAL_KINDS]
        return payload


@dataclass(frozen=True, slots=True)
class LaunchApprovalGate:
    """The computed launch gate: what is missing and whether launch is allowed."""

    register: LaunchApprovalRegister
    missing_kinds: tuple[str, ...]
    blockers: tuple[str, ...]
    configuration_blockers: tuple[str, ...]
    campaign_launch_allowed: bool

    @property
    def states(self) -> dict[str, str]:
        return {kind: self.register.approval(kind).state for kind in APPROVAL_KINDS}

    def as_dict(self, *, include_records: bool = False) -> dict[str, Any]:
        return {
            **self.register.as_dict(include_records=include_records),
            "blockers": list(self.blockers),
            "configuration_blockers": list(self.configuration_blockers),
            "campaign_launch_allowed": self.campaign_launch_allowed,
        }


def approval_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(APPROVAL_STATE_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(APPROVAL_STATE_DIR_ENV) or DEFAULT_APPROVAL_STATE_DIR
    return os.path.join(directory, DEFAULT_APPROVAL_STATE_NAME)


def _read_state_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as state_file:
            return state_file.read()
    except (OSError, UnicodeError):
        return None


def _header_values(text: str) -> dict[str, str]:
    """Top-level keys above the first record; record lines never leak into it."""

    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _starts_record(stripped):
            break
        key, separator, value = stripped.partition("=")
        if separator:
            values.setdefault(key.strip(), value.strip())
    return values


def _starts_record(line: str) -> bool:
    """Whether the whole first token is the record keyword.

    ``approved_by=...`` must not be mistaken for a record start, so the keyword
    is matched as a complete token rather than as a prefix.
    """

    return line.split(maxsplit=1)[0] == APPROVAL_RECORD_KEYWORD


def _record_tokens(text: str) -> tuple[dict[str, str], ...]:
    """Split the file into records: one keyword-led line, key=value tokens.

    Continuation lines that do not start with the record keyword belong to the
    record above them, matching the retention evidence format.
    """

    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _starts_record(stripped):
            current = {}
            records.append(current)
            stripped = stripped[len(APPROVAL_RECORD_KEYWORD) :].strip()
        elif current is None:
            continue
        for token in stripped.split():
            key, separator, value = token.partition("=")
            if separator:
                current.setdefault(key, value)
    return tuple(records)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _optional_positive_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _role_identifier(value: str | None) -> str | None:
    if not value:
        return None
    if any(marker in value for marker in FORBIDDEN_APPROVER_MARKERS):
        return None
    return value if APPROVER_ROLE_PATTERN.fullmatch(value) else None


def _scope_identifier(value: str | None) -> str | None:
    """What was approved, as a short reference rather than a description.

    A free-form sentence would be the easiest place to leak a person's name or
    an address into a file that gets copied around, so the scope carries the
    same shape as an evidence reference.
    """

    if not value:
        return None
    if any(marker in value for marker in FORBIDDEN_APPROVER_MARKERS):
        return None
    return value if APPROVAL_SCOPE_PATTERN.fullmatch(value) else None


def _record_reason(record: Mapping[str, str], today: date) -> str | None:
    """Return why a record cannot be trusted, or ``None`` when it can."""

    if _role_identifier(record.get("approved_by")) is None:
        return "approved_by_is_not_a_role_identifier"
    approved_at = _parse_date(record.get("approved_at"))
    if approved_at is None:
        return "approved_at_is_invalid"
    if approved_at > today:
        # A confirmation dated in the future cannot be a confirmation.
        return "approved_at_is_in_the_future"
    if _scope_identifier(record.get("scope")) is None:
        return "scope_is_invalid"
    valid_until = record.get("valid_until")
    if valid_until is not None:
        parsed_until = _parse_date(valid_until)
        if parsed_until is None:
            return "valid_until_is_invalid"
        if today > parsed_until:
            return "valid_until_passed"
    max_age_days = record.get("max_age_days")
    if max_age_days is not None and _optional_positive_int(max_age_days) is None:
        return "max_age_days_is_invalid"
    return None


def _recorded_approval(
    kind: str,
    record: Mapping[str, str],
    *,
    approved_at: str,
    max_age_days: int | None,
) -> LaunchApproval:
    return LaunchApproval(
        kind,
        APPROVAL_STATE_RECORDED,
        approved_by=_role_identifier(record.get("approved_by")),
        approved_at=approved_at,
        scope=record.get("scope"),
        evidence_ref=record.get("evidence_ref"),
        valid_until=record.get("valid_until"),
        max_age_days=max_age_days,
    )


def _restate(approval: LaunchApproval, state: str, reason: str) -> LaunchApproval:
    return LaunchApproval(
        kind=approval.kind,
        state=state,
        approved_by=approval.approved_by,
        approved_at=approval.approved_at,
        scope=approval.scope,
        evidence_ref=approval.evidence_ref,
        valid_until=approval.valid_until,
        max_age_days=approval.max_age_days,
        reason=reason,
    )


def _build_approval(
    kind: str,
    record: Mapping[str, str] | None,
    *,
    today: date,
) -> LaunchApproval:
    if record is None:
        return LaunchApproval(kind, APPROVAL_STATE_MISSING, reason="no_record")
    declared_state = record.get("state")
    if declared_state == "missing":
        return LaunchApproval(kind, APPROVAL_STATE_MISSING, reason="declared_missing")
    if declared_state != APPROVAL_STATE_RECORDED:
        # Only an explicit "recorded" record counts. Anything else — an absent
        # state, an unknown state, a future state — stays blocking.
        return LaunchApproval(kind, APPROVAL_STATE_MISSING, reason="state_not_recorded")

    approved_at = record.get("approved_at")
    max_age_days = _optional_positive_int(record.get("max_age_days"))
    reason = _record_reason(record, today)
    if reason == "valid_until_passed":
        return _restate(
            _recorded_approval(kind, record, approved_at=approved_at or "", max_age_days=max_age_days),
            APPROVAL_STATE_EXPIRED,
            reason,
        )
    if reason is not None:
        return _restate(
            LaunchApproval(
                kind,
                APPROVAL_STATE_UNREADABLE,
                approved_by=record.get("approved_by"),
                approved_at=approved_at,
                scope=record.get("scope"),
                evidence_ref=record.get("evidence_ref"),
                valid_until=record.get("valid_until"),
                max_age_days=max_age_days,
            ),
            APPROVAL_STATE_UNREADABLE,
            reason,
        )

    approval = _recorded_approval(
        kind, record, approved_at=approved_at or "", max_age_days=max_age_days
    )
    parsed_at = _parse_date(approved_at)
    if parsed_at is not None and max_age_days is not None and (today - parsed_at).days > max_age_days:
        return _restate(approval, APPROVAL_STATE_EXPIRED, "max_age_days_passed")
    return approval


def read_launch_approval_register(
    environ: Mapping[str, str] | None = None,
    *,
    today: date | None = None,
) -> LaunchApprovalRegister:
    """Read the approval register; a missing or broken file approves nothing."""

    environment = os.environ if environ is None else environ
    current_day = date.today() if today is None else today
    path = approval_state_file_path(environment)
    text = _read_state_text(path)

    if text is None:
        return LaunchApprovalRegister(
            available=False,
            state_path=path,
            approvals={
                kind: LaunchApproval(kind, APPROVAL_STATE_MISSING, reason="state_file_unreadable")
                for kind in APPROVAL_KINDS
            },
            file_errors=(BLOCKER_APPROVAL_STATE_FILE_UNAVAILABLE,),
        )

    file_errors: list[str] = []
    header = _header_values(text)
    if header.get("approval_state_version") != APPROVAL_STATE_VERSION:
        file_errors.append(BLOCKER_APPROVAL_STATE_VERSION_UNSUPPORTED)

    records: dict[str, dict[str, str]] = {}
    duplicate_or_unknown: list[str] = []
    for record in _record_tokens(text):
        kind = record.get("kind")
        if kind not in APPROVAL_KINDS or kind in records:
            # A duplicate is not merged and not ignored: it is reported, and
            # both copies are dropped so a second line cannot upgrade a record.
            duplicate_or_unknown.append(kind or "missing_kind")
            if kind in records:
                del records[kind]
            continue
        records[kind] = record

    approvals = {
        kind: _build_approval(kind, records.get(kind), today=current_day) for kind in APPROVAL_KINDS
    }
    if duplicate_or_unknown:
        # The whole register is untrustworthy when it declares the same kind
        # twice: the caller cannot tell which confirmation is the real one.
        file_errors.append(BLOCKER_APPROVAL_RECORD_COUNT)
        approvals = {
            kind: _restate(approval, APPROVAL_STATE_UNREADABLE, "duplicate_or_unknown_record")
            for kind, approval in approvals.items()
        }

    if BLOCKER_APPROVAL_STATE_VERSION_UNSUPPORTED in file_errors:
        approvals = {
            kind: _restate(approval, APPROVAL_STATE_UNREADABLE, "approval_state_version_unsupported")
            for kind, approval in approvals.items()
        }

    return LaunchApprovalRegister(
        available=True,
        state_path=path,
        approvals=approvals,
        file_errors=tuple(file_errors),
    )


def launch_approval_blockers(register: LaunchApprovalRegister) -> tuple[str, ...]:
    """Blocker codes that stop the paid launch in the given register."""

    blockers: list[str] = list(register.file_errors)
    for kind in APPROVAL_KINDS:
        approval = register.approval(kind)
        if approval.state == APPROVAL_STATE_RECORDED:
            continue
        if approval.state == APPROVAL_STATE_EXPIRED:
            blockers.append(f"{BLOCKER_APPROVAL_KIND_EXPIRED}:{kind}")
        elif approval.state == APPROVAL_STATE_UNREADABLE:
            blockers.append(f"{BLOCKER_APPROVAL_KIND_UNREADABLE}:{kind}")
        else:
            blockers.append(f"{BLOCKER_APPROVAL_KIND_MISSING}:{kind}")
    return tuple(dict.fromkeys(blockers))


def launch_configuration_blockers(readiness_blockers: tuple[str, ...]) -> tuple[str, ...]:
    """Technical readiness blockers that also stop a paid campaign launch."""

    return tuple(
        blocker for blocker in readiness_blockers if blocker in CAMPAIGN_CONFIGURATION_BLOCKERS
    )


def build_launch_approval_gate(
    readiness_blockers: tuple[str, ...] = (),
    *,
    environ: Mapping[str, str] | None = None,
    today: date | None = None,
    register: LaunchApprovalRegister | None = None,
) -> LaunchApprovalGate:
    """Compute the paid launch gate from records and configuration.

    Fail closed: without a readable register every kind is missing, so the
    gate is blocked and names what is absent (SC-013, FR-044). A technical flag
    is never consulted here — ``readiness_blockers`` can only *withhold* the
    permission, never grant it.
    """

    resolved = (
        register if register is not None else read_launch_approval_register(environ, today=today)
    )
    blockers = launch_approval_blockers(resolved)
    configuration = launch_configuration_blockers(tuple(readiness_blockers))
    return LaunchApprovalGate(
        register=resolved,
        missing_kinds=resolved.missing_kinds(),
        blockers=blockers,
        configuration_blockers=configuration,
        campaign_launch_allowed=not blockers and not configuration,
    )


def campaign_launch_allowed_for_settings(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Whether a paid campaign may be launched for this configuration.

    Used by the provider configuration view so that the catalogue and the
    readiness report cannot disagree about the launch gate. The technical
    settings can only withhold the permission; the permission itself still
    comes from the recorded approvals.
    """

    if not (
        settings.product_analytics_enabled
        and settings.product_analytics_validation_mode != "disabled"
        and settings.product_analytics_live_provider_delivery_allowed()
    ):
        return False
    return build_launch_approval_gate(environ=environ).campaign_launch_allowed
