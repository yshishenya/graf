"""Transfers to an advertising platform: basis, disclosure and revocation.

Feature 273 keeps *measurement* and *transfer* apart, because a transfer sends
the data of one visitor to somebody outside GRAF. Three requirements meet at
this boundary and nowhere else:

* FR-028 — an offline-conversion transfer happens only when the basis is
  confirmed *and* the visitor has actually been told about the transfer. A
  configuration flag is a declaration, not a confirmation, so the basis is read
  from a recorded confirmation and the disclosure is read from the
  visitor-facing copy the site really publishes;
* FR-029 — advertising distributed to a subscriber through telecommunication
  networks needs the *prior consent of the subscriber*. That consent is a
  different thing from the optional measurement consent of the visitor, so it
  carries its own record kind, and a measurement consent can never satisfy it
  (``subscriber_prior_consent_from_measurement_consent`` exists to make that
  mistake impossible rather than merely unlikely);
* FR-049 — a withdrawn consent stops further transfers to that recipient, the
  same data is never sent again, and the revocation leaves a trace that shows it
  reached the recipient. The trace is metadata only.

Everything fails closed. A missing record, an unreadable register, a foreign
recipient, an out-of-date disclosure revision or a revoked recipient produces a
decision with named blockers, and the caller must not transfer anything.

The records live outside git in the metadata-only state-file format the launch
approvals already use. Only role identifiers, purpose tokens, dates and opaque
references cross into a record: a person's name, an address, a phone number or
a live link is refused by :func:`assert_metadata_only_trace`.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from twobrain_rec_server.product_analytics.approvals import (
    APPROVAL_SCOPE_PATTERN,
    APPROVER_ROLE_PATTERN,
    FORBIDDEN_APPROVER_MARKERS,
)
from twobrain_rec_server.product_analytics.consent_copy import consent_revision_from_page
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_forbidden_fields,
    find_security_credential_fields,
)

# --- Purposes and recipients ------------------------------------------------

# Uploading offline conversions into the advertising cabinet (FR-028).
TRANSFER_PURPOSE_OFFLINE_CONVERSIONS = "yandex_offline_conversions"
# Distributing advertising to a subscriber through telecommunication networks,
# for example a call, a message or an addressable audience export (FR-029).
TRANSFER_PURPOSE_TELECOM_ADVERTISING = "telecom_network_advertising"

ADVERTISING_TRANSFER_PURPOSES = (
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS,
    TRANSFER_PURPOSE_TELECOM_ADVERTISING,
)

# Article 18 of the advertising law attaches to advertising *distributed* to a
# subscriber, so only this purpose needs the prior consent of the subscriber.
# An offline-conversion upload is a different purpose and must not borrow that
# consent, and the subscriber consent must not be asked for measurement.
TELECOM_ADVERTISING_PURPOSES = frozenset({TRANSFER_PURPOSE_TELECOM_ADVERTISING})

RECIPIENT_YANDEX_METRICA = "yandex_metrica"
ADVERTISING_TRANSFER_RECIPIENTS = (RECIPIENT_YANDEX_METRICA,)

TRANSFER_RECIPIENT_BY_PURPOSE: Mapping[str, str] = {
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS: RECIPIENT_YANDEX_METRICA,
    TRANSFER_PURPOSE_TELECOM_ADVERTISING: RECIPIENT_YANDEX_METRICA,
}

# --- Consent vocabulary -----------------------------------------------------

# The optional category of the visit decision that allows advertising
# attribution. It is the visitor's decision, and its absence means "not
# allowed" for the transfer as well.
ADVERTISING_ATTRIBUTION_CATEGORY = "advertising_attribution"

CONSENT_STATE_GRANTED = "granted"
CONSENT_STATE_DENIED = "denied"
CONSENT_STATE_REVOKED = "revoked"
CONSENT_STATE_UNKNOWN = "unknown"
CONSENT_STATES = (
    CONSENT_STATE_GRANTED,
    CONSENT_STATE_DENIED,
    CONSENT_STATE_REVOKED,
    CONSENT_STATE_UNKNOWN,
)

# The kind of a consent record. Two records with the same state but different
# kinds authorise different things, which is exactly the separation FR-029 asks
# for.
GRANT_KIND_OPTIONAL_MEASUREMENT_CONSENT = "optional_measurement_consent"
GRANT_KIND_SUBSCRIBER_PRIOR_CONSENT = "subscriber_prior_consent"
GRANT_KINDS = (GRANT_KIND_OPTIONAL_MEASUREMENT_CONSENT, GRANT_KIND_SUBSCRIBER_PRIOR_CONSENT)

SUBSCRIBER_PRIOR_CONSENT_SCOPE = "telecom_network_advertising"

# --- Basis vocabulary -------------------------------------------------------

BASIS_STATE_CONFIRMED = "confirmed"
BASIS_STATE_UNCONFIRMED = "unconfirmed"

# What the confirmation says the transfer rests on. A level 3 transfer rests on
# the consent of the visitor, so no other basis is accepted here.
TRANSFER_BASIS_KINDS = ("consent",)

# A recorded legal confirmation authorises an advertising transfer only when it
# names the transfer. FR-047 records the basis of levels 1 and 2, and that
# general scope deliberately does not authorise a level 3 transfer to an
# advertising platform.
TRANSFER_BASIS_SCOPES: Mapping[str, tuple[str, ...]] = {
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS: (
        "offline_conversion_transfer_basis",
        "advertising_transfer_basis",
    ),
    TRANSFER_PURPOSE_TELECOM_ADVERTISING: ("telecom_advertising_basis",),
}

# --- Disclosure vocabulary --------------------------------------------------

# Statements the visitor-facing copy has to make before an offline-conversion
# transfer may happen. Each statement is a marker set: the site copy is written
# by hand, so a stem is matched instead of one exact sentence.
REQUIRED_TRANSFER_DISCLOSURE_STATEMENTS: Mapping[str, tuple[str, ...]] = {
    "advertising_platform_named": ("метрик", "яндекс", "yandex", "advertising platform"),
    "offline_conversions_named": ("офлайн-конверси", "offline conversion"),
    "advertising_attribution_visible": (
        ADVERTISING_ATTRIBUTION_CATEGORY,
        "рекламная атрибуция",
    ),
}

# FR-029 governs the telecom purpose through the prior consent of the
# subscriber, which the subscriber gives explicitly, so no separate disclosure
# statement set is declared for it. A purpose without a declared set would need
# one before it could ever be allowed; an empty requirement is therefore only
# honest for a purpose whose consent is itself the visitor-facing act.
TRANSFER_DISCLOSURE_STATEMENTS: Mapping[str, tuple[str, ...]] = {
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS: tuple(REQUIRED_TRANSFER_DISCLOSURE_STATEMENTS),
}

DISCLOSURE_STATE_MISSING = "missing"
DISCLOSURE_STATE_CURRENT = "current"
DISCLOSURE_STATE_OUTDATED = "outdated"
DISCLOSURE_STATE_INCOMPLETE = "incomplete"

# --- Revocation vocabulary --------------------------------------------------

REVOCATION_DELIVERY_PENDING = "pending"
REVOCATION_DELIVERY_CONFIRMED = "confirmed"
REVOCATION_DELIVERY_FAILED = "failed"
REVOCATION_DELIVERY_STATES = (
    REVOCATION_DELIVERY_PENDING,
    REVOCATION_DELIVERY_CONFIRMED,
    REVOCATION_DELIVERY_FAILED,
)

# --- Named blockers ---------------------------------------------------------

BLOCKER_PURPOSE_UNKNOWN = "advertising_transfer_purpose_unknown"
BLOCKER_RECIPIENT_MISMATCH = "advertising_transfer_recipient_mismatch"
BLOCKER_BASIS_MISSING = "advertising_legal_basis_missing"
BLOCKER_BASIS_NOT_CONFIRMED = "advertising_legal_basis_not_confirmed"
BLOCKER_BASIS_OUT_OF_SCOPE = "advertising_legal_basis_out_of_scope"
BLOCKER_DISCLOSURE_MISSING = "visitor_disclosure_missing"
BLOCKER_DISCLOSURE_OUTDATED = "visitor_disclosure_outdated"
BLOCKER_DISCLOSURE_INCOMPLETE = "visitor_disclosure_incomplete"
BLOCKER_MEASUREMENT_CONSENT_MISSING = "advertising_attribution_consent_missing"
BLOCKER_MEASUREMENT_CONSENT_DENIED = "advertising_attribution_consent_denied"
BLOCKER_MEASUREMENT_CONSENT_REVOKED = "advertising_attribution_consent_revoked"
BLOCKER_SUBSCRIBER_CONSENT_MISSING = "subscriber_prior_consent_missing"
BLOCKER_SUBSCRIBER_CONSENT_NOT_SEPARATE = "subscriber_prior_consent_not_separate"
BLOCKER_SUBSCRIBER_CONSENT_OUT_OF_SCOPE = "subscriber_prior_consent_out_of_scope"
BLOCKER_SUBSCRIBER_CONSENT_DENIED = "subscriber_prior_consent_denied"
BLOCKER_SUBSCRIBER_CONSENT_REVOKED = "subscriber_prior_consent_revoked"
BLOCKER_RECIPIENT_REVOKED = "recipient_revocation_recorded"
BLOCKER_RETRANSFER_REFUSED = "retransfer_of_revoked_data_refused"

# Statuses the delivery layer reports. They are deliberately different from
# each other so an operator can tell "no basis" from "the recipient was
# revoked" without reading the metadata.
STATUS_TRANSFER_NOT_AUTHORISED = "transfer_not_authorised"
STATUS_TRANSFER_REVOKED = "recipient_revoked"

REVOCATION_TRACE_MARKER = "revocation_trace"

# --- The state file ---------------------------------------------------------

ADVERTISING_TRANSFER_STATE_FILE_ENV = "GRAF_PRODUCT_ANALYTICS_ADVERTISING_TRANSFER_STATE_FILE"
ADVERTISING_TRANSFER_STATE_DIR_ENV = "GRAF_PRODUCT_ANALYTICS_ADVERTISING_TRANSFER_STATE_DIR"
DEFAULT_ADVERTISING_TRANSFER_STATE_DIR = "/var/lib/graf-product-analytics-advertising-transfer"
DEFAULT_ADVERTISING_TRANSFER_STATE_NAME = "advertising-transfers"
ADVERTISING_TRANSFER_STATE_VERSION = "1"
BASIS_RECORD_KEYWORD = "basis"
REVOCATION_RECORD_KEYWORD = "revocation"
REFUSAL_RECORD_KEYWORD = "revocation_refusal"
RECORD_KEYWORDS = (BASIS_RECORD_KEYWORD, REVOCATION_RECORD_KEYWORD, REFUSAL_RECORD_KEYWORD)

TRANSFER_REF_PATTERN = re.compile(r"^[a-z][a-z0-9_]{7,79}$")
REASON_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The opaque reference of a transfer is a hex digest. The shared checker reads a
# long run of digits as a possible phone number, so a reference is recognised by
# this exact shape and replaced before the checker runs: nothing else is masked.
OPAQUE_TRANSFER_REFERENCE_RE = re.compile(r"graf_yandex_dedupe_[0-9a-f]{8,64}")
OPAQUE_TRANSFER_REFERENCE_PLACEHOLDER = "opaque_transfer_reference"


class AdvertisingTransferTraceViolation(ValueError):
    """Raised when a trace would carry personal data or a credential (FR-049)."""

    def __init__(self, paths: tuple[str, ...]) -> None:
        super().__init__("advertising transfer trace is not metadata only: " + ", ".join(paths))
        self.paths = paths


# --- Records ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LegalBasisConfirmation:
    """A recorded confirmation that an advertising transfer has a legal basis.

    ``confirmed_by`` is a role identifier and ``scope`` says what exactly was
    confirmed. The record is written by a person and read by the transfer path,
    which is what makes the basis a fact instead of a flag.
    """

    purpose: str
    recipient: str
    basis: str
    state: str
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    scope: str | None = None
    evidence_ref: str | None = None
    reason: str | None = None

    def recorded(self) -> bool:
        return self.state == BASIS_STATE_CONFIRMED

    def authorises(self, *, purpose: str, recipient: str) -> bool:
        return (
            self.recorded()
            and self.purpose == purpose
            and self.recipient == recipient
            and self.scope in TRANSFER_BASIS_SCOPES.get(purpose, ())
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "recipient": self.recipient,
            "basis": self.basis,
            "state": self.state,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at,
            "scope": self.scope,
            "evidence_ref": self.evidence_ref,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class RecipientRevocationRecord:
    """The trace that a withdrawal was carried to one external recipient.

    ``delivery_state`` is the part FR-049 asks to be verifiable: it says whether
    the recipient was actually told, and ``delivered_at`` says when. No visitor
    and no account is named here — the recipient, the purpose and the moment are
    the whole record.
    """

    recipient: str
    purposes: tuple[str, ...]
    revoked_at: str
    delivery_state: str
    delivery_method: str
    delivered_at: str | None = None
    evidence_ref: str | None = None

    def covers(self, purpose: str) -> bool:
        """Whether this revocation withdraws the consent for that purpose.

        A record that names no purpose withdraws the consent for every purpose
        of that recipient: an empty list is read as "all", never as "none".
        """

        return not self.purposes or purpose in self.purposes

    def as_dict(self) -> dict[str, Any]:
        return {
            "recipient": self.recipient,
            "purposes": list(self.purposes),
            "revoked_at": self.revoked_at,
            "delivery_state": self.delivery_state,
            "delivery_method": self.delivery_method,
            "delivered_at": self.delivered_at,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class TransferRefusalRecord:
    """One transfer that was refused after a revocation.

    FR-049 forbids a second transfer of the same data, so the opaque reference
    of a refused transfer is kept: the same reference is refused again instead
    of being sent on a later retry.
    """

    recipient: str
    purpose: str
    transfer_ref: str
    refused_at: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "recipient": self.recipient,
            "purpose": self.purpose,
            "transfer_ref": self.transfer_ref,
            "refused_at": self.refused_at,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class VisitorDisclosure:
    """What the visitor-facing copy states, and under which revision.

    The record is derived from the page the visitor reads, so it cannot be
    produced by a flag: an empty ``copy_version`` means the site does not state
    a revision, and a statement missing from ``statements`` means the visitor
    was not told about that part of the transfer.
    """

    copy_version: str
    surface: str
    statements: tuple[str, ...]
    recorded_at: str | None = None

    def covers(self, purpose: str) -> bool:
        required = TRANSFER_DISCLOSURE_STATEMENTS.get(purpose, ())
        return all(statement in self.statements for statement in required)

    def missing_statements(self, purpose: str) -> tuple[str, ...]:
        required = TRANSFER_DISCLOSURE_STATEMENTS.get(purpose, ())
        return tuple(statement for statement in required if statement not in self.statements)

    def as_dict(self) -> dict[str, Any]:
        return {
            "copy_version": self.copy_version,
            "surface": self.surface,
            "statements": list(self.statements),
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class OptionalMeasurementConsent:
    """The optional visit decision about measurement (level 3).

    It is the decision a visitor makes on the page and can withdraw at any
    moment. ``unknown`` means no decision was seen, which is not a permission.
    """

    category: str = ADVERTISING_ATTRIBUTION_CATEGORY
    state: str = CONSENT_STATE_UNKNOWN
    grant_kind: str = GRANT_KIND_OPTIONAL_MEASUREMENT_CONSENT
    decided_at: str | None = None
    copy_version: str | None = None

    def granted(self) -> bool:
        return self.state == CONSENT_STATE_GRANTED

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "state": self.state,
            "grant_kind": self.grant_kind,
            "decided_at": self.decided_at,
            "copy_version": self.copy_version,
        }


@dataclass(frozen=True, slots=True)
class SubscriberPriorConsent:
    """The prior consent of the subscriber for advertising via telecom networks.

    FR-029 asks for consent obtained *before* the advertising is distributed,
    and obtained for the advertising itself. The record therefore carries its
    own ``grant_kind`` and its own ``scope``: a measurement decision, however
    explicit, has neither.
    """

    state: str
    scope: str
    grant_kind: str = GRANT_KIND_SUBSCRIBER_PRIOR_CONSENT
    decided_at: str | None = None
    evidence_ref: str | None = None

    def granted_for(self, purpose: str) -> bool:
        return (
            self.state == CONSENT_STATE_GRANTED
            and self.grant_kind == GRANT_KIND_SUBSCRIBER_PRIOR_CONSENT
            and self.scope == SUBSCRIBER_PRIOR_CONSENT_SCOPE
            and purpose in TELECOM_ADVERTISING_PURPOSES
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "scope": self.scope,
            "grant_kind": self.grant_kind,
            "decided_at": self.decided_at,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class AdvertisingTransferDecision:
    """Whether one transfer may happen, and every reason it may not.

    ``blockers`` are named codes and ``facts`` holds metadata only: no visitor,
    no account, no identity value of any kind.
    """

    purpose: str
    recipient: str
    allowed: bool
    blockers: tuple[str, ...]
    facts: dict[str, Any] = field(default_factory=dict)
    revocation_trace: dict[str, Any] | None = None

    @property
    def status(self) -> str:
        """The delivery status a provider client reports for this decision."""

        if self.allowed:
            return "allowed"
        if BLOCKER_RECIPIENT_REVOKED in self.blockers or BLOCKER_RETRANSFER_REFUSED in self.blockers:
            return STATUS_TRANSFER_REVOKED
        return STATUS_TRANSFER_NOT_AUTHORISED

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "purpose": self.purpose,
            "recipient": self.recipient,
            "allowed": self.allowed,
            "blockers": list(self.blockers),
            "facts": dict(self.facts),
        }
        if self.revocation_trace is not None:
            payload[REVOCATION_TRACE_MARKER] = dict(self.revocation_trace)
        return payload


@dataclass(frozen=True, slots=True)
class AdvertisingTransferRegister:
    """The recorded confirmations, revocations and refusals, or their absence."""

    available: bool
    state_path: str
    bases: tuple[LegalBasisConfirmation, ...] = ()
    revocations: tuple[RecipientRevocationRecord, ...] = ()
    refusals: tuple[TransferRefusalRecord, ...] = ()
    file_errors: tuple[str, ...] = ()

    def basis(self, *, purpose: str, recipient: str) -> LegalBasisConfirmation | None:
        for record in self.bases:
            if record.purpose == purpose and record.recipient == recipient:
                return record
        return None

    def revocation(self, *, recipient: str, purpose: str) -> RecipientRevocationRecord | None:
        for record in self.revocations:
            if record.recipient == recipient and record.covers(purpose):
                return record
        return None

    def refusal(self, *, recipient: str, transfer_ref: str) -> TransferRefusalRecord | None:
        for record in self.refusals:
            if record.recipient == recipient and record.transfer_ref == transfer_ref:
                return record
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "state_path": self.state_path,
            "file_errors": list(self.file_errors),
            "bases": [record.as_dict() for record in self.bases],
            "revocations": [record.as_dict() for record in self.revocations],
            "refusals": [record.as_dict() for record in self.refusals],
        }


# --- Register parsing -------------------------------------------------------


def advertising_transfer_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(ADVERTISING_TRANSFER_STATE_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(ADVERTISING_TRANSFER_STATE_DIR_ENV) or (
        DEFAULT_ADVERTISING_TRANSFER_STATE_DIR
    )
    return os.path.join(directory, DEFAULT_ADVERTISING_TRANSFER_STATE_NAME)


def read_advertising_transfer_register(
    environ: Mapping[str, str] | None = None,
    *,
    today: date | None = None,
) -> AdvertisingTransferRegister:
    """Read the transfer records; a missing or broken file authorises nothing."""

    path = advertising_transfer_state_file_path(environ)
    try:
        with open(path, encoding="utf-8") as state_file:
            text = state_file.read()
    except (OSError, UnicodeError):
        # No file means no recorded basis, no revocation and no refusal. The
        # caller still fails closed on the missing basis, so an absent file
        # cannot upgrade a transfer.
        return AdvertisingTransferRegister(
            available=False,
            state_path=path,
            file_errors=("advertising_transfer_state_file_unavailable",),
        )

    current_day = date.today() if today is None else today
    file_errors: list[str] = []
    if _header_value(text, "advertising_transfer_state_version") != (
        ADVERTISING_TRANSFER_STATE_VERSION
    ):
        file_errors.append("advertising_transfer_state_version_unsupported")

    bases: list[LegalBasisConfirmation] = []
    revocations: list[RecipientRevocationRecord] = []
    refusals: list[TransferRefusalRecord] = []
    for keyword, record in _records(text):
        if keyword == BASIS_RECORD_KEYWORD:
            bases.append(_basis_record(record, today=current_day))
        elif keyword == REVOCATION_RECORD_KEYWORD:
            revocations.append(_revocation_record(record))
        elif keyword == REFUSAL_RECORD_KEYWORD:
            refusals.append(_refusal_record(record))

    register = AdvertisingTransferRegister(
        available=True,
        state_path=path,
        bases=tuple(bases),
        revocations=tuple(revocations),
        refusals=tuple(refusals),
        file_errors=tuple(file_errors),
    )
    if file_errors:
        # A register that declares an unsupported format cannot be trusted to
        # authorise anything, so every basis is dropped. The revocations and
        # refusals stay: they only ever withhold a transfer, and losing them
        # would be the one direction that fails open (FR-049).
        return AdvertisingTransferRegister(
            available=True,
            state_path=path,
            revocations=register.revocations,
            refusals=register.refusals,
            file_errors=register.file_errors,
        )
    return register


def _header_value(text: str, key: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.split(maxsplit=1)[0] in RECORD_KEYWORDS:
            break
        name, separator, value = stripped.partition("=")
        if separator and name.strip() == key:
            return value.strip()
    return None


def _records(text: str) -> tuple[tuple[str, dict[str, str]], ...]:
    """Split the file into ``(keyword, tokens)`` records, first value winning."""

    records: list[tuple[str, dict[str, str]]] = []
    current: dict[str, str] | None = None
    keyword = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first = stripped.split(maxsplit=1)[0]
        if first in RECORD_KEYWORDS:
            current = {}
            keyword = first
            records.append((keyword, current))
            stripped = stripped[len(keyword) :].strip()
        elif current is None:
            continue
        for token in stripped.split():
            name, separator, value = token.partition("=")
            if separator:
                current.setdefault(name, value)
    return tuple(records)


def _basis_record(record: Mapping[str, str], *, today: date) -> LegalBasisConfirmation:
    purpose = record.get("purpose") or ""
    recipient = record.get("recipient") or ""
    basis = record.get("basis") or ""
    reason = _basis_record_reason(record, purpose, recipient, basis, today=today)
    state = BASIS_STATE_UNCONFIRMED if reason else BASIS_STATE_CONFIRMED
    return LegalBasisConfirmation(
        purpose=purpose,
        recipient=recipient,
        basis=basis,
        state=state,
        confirmed_by=_role_identifier(record.get("confirmed_by")),
        confirmed_at=record.get("confirmed_at"),
        scope=_scope_identifier(record.get("scope")),
        evidence_ref=_scope_identifier(record.get("evidence_ref")),
        reason=reason,
    )


def _basis_record_reason(
    record: Mapping[str, str],
    purpose: str,
    recipient: str,
    basis: str,
    *,
    today: date,
) -> str | None:
    if record.get("state") != BASIS_STATE_CONFIRMED:
        return "state_not_confirmed"
    if purpose not in ADVERTISING_TRANSFER_PURPOSES:
        return "purpose_unknown"
    if recipient not in ADVERTISING_TRANSFER_RECIPIENTS:
        return "recipient_unknown"
    if basis not in TRANSFER_BASIS_KINDS:
        return "basis_kind_unsupported"
    if _role_identifier(record.get("confirmed_by")) is None:
        return "confirmed_by_is_not_a_role_identifier"
    confirmed_at = _iso_date(record.get("confirmed_at"))
    if confirmed_at is None:
        return "confirmed_at_is_invalid"
    if confirmed_at > today:
        return "confirmed_at_is_in_the_future"
    if _scope_identifier(record.get("scope")) is None:
        return "scope_is_invalid"
    return None


def _revocation_record(record: Mapping[str, str]) -> RecipientRevocationRecord:
    purposes = tuple(
        purpose
        for purpose in (record.get("purposes") or "").split(",")
        if purpose in ADVERTISING_TRANSFER_PURPOSES
    )
    delivery_state = record.get("delivery_state") or REVOCATION_DELIVERY_PENDING
    if delivery_state not in REVOCATION_DELIVERY_STATES:
        # An unknown delivery state is not a confirmation; the transfer stays
        # blocked anyway, and the trace reports what is actually known.
        delivery_state = REVOCATION_DELIVERY_PENDING
    delivered_at = record.get("delivered_at")
    if delivered_at is not None and _iso_date(delivered_at) is None:
        delivered_at = None
    if delivery_state == REVOCATION_DELIVERY_CONFIRMED and delivered_at is None:
        # A confirmation without a moment is not a confirmed delivery: the
        # trace says "pending" instead of claiming the recipient was told.
        delivery_state = REVOCATION_DELIVERY_PENDING
    return RecipientRevocationRecord(
        recipient=record.get("recipient") or "",
        purposes=purposes,
        revoked_at=record.get("revoked_at") or "",
        delivery_state=delivery_state,
        delivery_method=_reason_token(record.get("method")) or "unspecified",
        delivered_at=delivered_at,
        evidence_ref=_scope_identifier(record.get("evidence_ref")),
    )


def _refusal_record(record: Mapping[str, str]) -> TransferRefusalRecord:
    return TransferRefusalRecord(
        recipient=record.get("recipient") or "",
        purpose=record.get("purpose") or "",
        transfer_ref=_transfer_ref(record.get("transfer_ref")) or "",
        refused_at=record.get("refused_at") or "",
        reason=_reason_token(record.get("reason")) or "unspecified",
    )


def _role_identifier(value: str | None) -> str | None:
    if not value or any(marker in value for marker in FORBIDDEN_APPROVER_MARKERS):
        return None
    return value if APPROVER_ROLE_PATTERN.fullmatch(value) else None


def _scope_identifier(value: str | None) -> str | None:
    if not value or any(marker in value for marker in FORBIDDEN_APPROVER_MARKERS):
        return None
    return value if APPROVAL_SCOPE_PATTERN.fullmatch(value) else None


def evidence_reference_token(value: str | None) -> str | None:
    """Validate a reference to stored evidence, or return ``None``.

    An evidence reference names a document that lives outside the repository, so
    it stays a scope-shaped ASCII token: anything else — a path, an address, a
    sentence — is dropped instead of being written into a state file or an
    evidence line.
    """

    return _scope_identifier(value)


def _reason_token(value: str | None) -> str | None:
    if not value or any(marker in value for marker in FORBIDDEN_APPROVER_MARKERS):
        return None
    return value if REASON_PATTERN.fullmatch(value) else None


def _transfer_ref(value: str | None) -> str | None:
    if not value:
        return None
    return value if TRANSFER_REF_PATTERN.fullmatch(value) else None


def _iso_date(value: str | None) -> date | None:
    if not value or not DATE_PATTERN.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# --- Builders ---------------------------------------------------------------


def build_visitor_disclosure(
    pages: Mapping[str, str],
    *,
    surface: str = "analytics_consent",
    recorded_at: str | None = None,
) -> VisitorDisclosure:
    """Derive the disclosure record from the copy the visitor actually reads.

    ``pages`` are the rendered consent-copy pages (or the packaged templates
    that produce them). The revision is read from the same page the consent
    controller compares against, so a rewrite of the copy either keeps the
    statement or fails this comparison loudly.
    """

    combined = "\n".join(text for text in pages.values() if text)
    lowered = combined.lower()
    statements = tuple(
        statement
        for statement, markers in REQUIRED_TRANSFER_DISCLOSURE_STATEMENTS.items()
        if any(marker in lowered for marker in markers)
    )
    return VisitorDisclosure(
        copy_version=consent_revision_from_page(surface, pages.get(surface, "")) or "",
        surface=surface,
        statements=statements,
        recorded_at=recorded_at,
    )


def optional_measurement_consent_from_categories(
    categories: object,
    *,
    decided_at: str | None = None,
    copy_version: str | None = None,
) -> OptionalMeasurementConsent:
    """Read the visitor's decision from the consent categories of an event.

    Only an explicit presence of ``advertising_attribution`` is a permission.
    A missing, malformed or partial list is ``unknown``, which the transfer gate
    treats as "not allowed".
    """

    if not isinstance(categories, (list, tuple)):
        return OptionalMeasurementConsent(decided_at=decided_at, copy_version=copy_version)
    normalized = tuple(str(category) for category in categories)
    if ADVERTISING_ATTRIBUTION_CATEGORY not in normalized:
        return OptionalMeasurementConsent(decided_at=decided_at, copy_version=copy_version)
    return OptionalMeasurementConsent(
        state=CONSENT_STATE_GRANTED,
        decided_at=decided_at,
        copy_version=copy_version,
    )


def optional_measurement_consent_from_event(event: Any) -> OptionalMeasurementConsent:
    """The visitor decision carried by a product event, if it carries one."""

    properties = getattr(event, "properties", None)
    if not isinstance(properties, Mapping):
        return OptionalMeasurementConsent()
    return optional_measurement_consent_from_categories(properties.get("consent_categories"))


def subscriber_prior_consent_from_measurement_consent(
    consent: OptionalMeasurementConsent,
    *,
    decided_at: str | None = None,
) -> SubscriberPriorConsent:
    """Build the wrong record on purpose, so nobody can conflate the two.

    FR-029 wants the prior consent of the subscriber for advertising, not the
    optional consent of the visitor for measurement. A caller that reaches for
    the measurement decision gets a record whose kind is
    ``optional_measurement_consent``, and the transfer gate refuses it with
    :data:`BLOCKER_SUBSCRIBER_CONSENT_NOT_SEPARATE`.
    """

    return SubscriberPriorConsent(
        state=consent.state,
        scope=SUBSCRIBER_PRIOR_CONSENT_SCOPE,
        grant_kind=GRANT_KIND_OPTIONAL_MEASUREMENT_CONSENT,
        decided_at=decided_at or consent.decided_at,
    )


def required_basis_scopes(purpose: str) -> tuple[str, ...]:
    return TRANSFER_BASIS_SCOPES.get(purpose, ())


def transfer_needs_subscriber_prior_consent(purpose: str) -> bool:
    """Whether this purpose distributes advertising through telecom networks."""

    return purpose in TELECOM_ADVERTISING_PURPOSES


# --- The gate ---------------------------------------------------------------


def evaluate_advertising_transfer(
    *,
    purpose: str,
    recipient: str,
    basis: LegalBasisConfirmation | None,
    disclosure: VisitorDisclosure | None,
    measurement_consent: OptionalMeasurementConsent | None,
    subscriber_prior_consent: SubscriberPriorConsent | None = None,
    register: AdvertisingTransferRegister | None = None,
    transfer_ref: str | None = None,
    expected_disclosure_revision: str | None = None,
) -> AdvertisingTransferDecision:
    """Decide one transfer. A missing record is a refusal, never a default.

    The gate is pure: it reads the records it is given and names every reason it
    refuses. It never asks a configuration flag, because a flag can withhold a
    permission but cannot provide a legal basis.
    """

    blockers: list[str] = []
    facts: dict[str, Any] = {
        "basis_state": None,
        "basis_scope": None,
        "basis_confirmed_at": None,
        "basis_evidence_ref": None,
        "disclosure_state": DISCLOSURE_STATE_MISSING,
        "disclosure_copy_version": None,
        "disclosure_missing_statements": [],
        "measurement_consent_state": None,
        "subscriber_consent_state": None,
        "revocation_delivery_state": None,
    }

    if purpose not in ADVERTISING_TRANSFER_PURPOSES:
        blockers.append(BLOCKER_PURPOSE_UNKNOWN)
    declared_recipient = TRANSFER_RECIPIENT_BY_PURPOSE.get(purpose)
    if declared_recipient is not None and declared_recipient != recipient:
        blockers.append(BLOCKER_RECIPIENT_MISMATCH)

    blockers.extend(
        _basis_blockers(
            purpose=purpose,
            recipient=recipient,
            basis=basis,
            facts=facts,
        )
    )
    blockers.extend(
        _disclosure_blockers(
            purpose=purpose,
            disclosure=disclosure,
            expected_revision=expected_disclosure_revision,
            facts=facts,
        )
    )
    blockers.extend(_measurement_consent_blockers(measurement_consent, facts=facts))
    if transfer_needs_subscriber_prior_consent(purpose):
        blockers.extend(
            _subscriber_consent_blockers(
                purpose=purpose,
                consent=subscriber_prior_consent,
                facts=facts,
            )
        )

    revocation_trace: dict[str, Any] | None = None
    if register is not None:
        revocation = register.revocation(recipient=recipient, purpose=purpose)
        if revocation is not None:
            blockers.append(BLOCKER_RECIPIENT_REVOKED)
            facts["revocation_delivery_state"] = revocation.delivery_state
            revocation_trace = recipient_revocation_trace(
                register, recipient=recipient, purpose=purpose
            )
        if transfer_ref and register.refusal(recipient=recipient, transfer_ref=transfer_ref):
            blockers.append(BLOCKER_RETRANSFER_REFUSED)
            if revocation_trace is None:
                revocation_trace = recipient_revocation_trace(
                    register, recipient=recipient, purpose=purpose
                )

    if transfer_ref:
        facts["transfer_ref"] = transfer_ref
    unique_blockers = tuple(dict.fromkeys(blockers))
    return AdvertisingTransferDecision(
        purpose=purpose,
        recipient=recipient,
        allowed=not unique_blockers,
        blockers=unique_blockers,
        facts=facts,
        revocation_trace=revocation_trace,
    )


def _basis_blockers(
    *,
    purpose: str,
    recipient: str,
    basis: LegalBasisConfirmation | None,
    facts: dict[str, Any],
) -> tuple[str, ...]:
    if basis is None:
        return (BLOCKER_BASIS_MISSING,)
    facts["basis_state"] = basis.state
    facts["basis_scope"] = basis.scope
    facts["basis_confirmed_at"] = basis.confirmed_at
    facts["basis_evidence_ref"] = basis.evidence_ref
    if basis.purpose != purpose or basis.recipient != recipient:
        return (BLOCKER_BASIS_OUT_OF_SCOPE,)
    if not basis.recorded():
        return (BLOCKER_BASIS_NOT_CONFIRMED,)
    if basis.scope not in required_basis_scopes(purpose):
        return (BLOCKER_BASIS_OUT_OF_SCOPE,)
    return ()


def _disclosure_blockers(
    *,
    purpose: str,
    disclosure: VisitorDisclosure | None,
    expected_revision: str | None,
    facts: dict[str, Any],
) -> tuple[str, ...]:
    if not TRANSFER_DISCLOSURE_STATEMENTS.get(purpose):
        # A purpose whose consent is itself the visitor-facing act (FR-029)
        # declares no disclosure statement set.
        return ()
    if disclosure is None:
        return (BLOCKER_DISCLOSURE_MISSING,)
    facts["disclosure_copy_version"] = disclosure.copy_version
    missing = disclosure.missing_statements(purpose)
    if missing:
        facts["disclosure_state"] = DISCLOSURE_STATE_INCOMPLETE
        facts["disclosure_missing_statements"] = list(missing)
        return (BLOCKER_DISCLOSURE_INCOMPLETE,)
    if not disclosure.copy_version:
        facts["disclosure_state"] = DISCLOSURE_STATE_MISSING
        return (BLOCKER_DISCLOSURE_MISSING,)
    if expected_revision is not None and disclosure.copy_version != expected_revision:
        facts["disclosure_state"] = DISCLOSURE_STATE_OUTDATED
        return (BLOCKER_DISCLOSURE_OUTDATED,)
    facts["disclosure_state"] = DISCLOSURE_STATE_CURRENT
    return ()


def _measurement_consent_blockers(
    consent: OptionalMeasurementConsent | None,
    *,
    facts: dict[str, Any],
) -> tuple[str, ...]:
    if consent is None or consent.category != ADVERTISING_ATTRIBUTION_CATEGORY:
        return (BLOCKER_MEASUREMENT_CONSENT_MISSING,)
    facts["measurement_consent_state"] = consent.state
    if consent.state == CONSENT_STATE_GRANTED:
        return ()
    if consent.state == CONSENT_STATE_REVOKED:
        return (BLOCKER_MEASUREMENT_CONSENT_REVOKED,)
    if consent.state == CONSENT_STATE_DENIED:
        return (BLOCKER_MEASUREMENT_CONSENT_DENIED,)
    return (BLOCKER_MEASUREMENT_CONSENT_MISSING,)


def _subscriber_consent_blockers(
    *,
    purpose: str,
    consent: SubscriberPriorConsent | None,
    facts: dict[str, Any],
) -> tuple[str, ...]:
    if consent is None:
        return (BLOCKER_SUBSCRIBER_CONSENT_MISSING,)
    facts["subscriber_consent_state"] = consent.state
    if consent.grant_kind != GRANT_KIND_SUBSCRIBER_PRIOR_CONSENT:
        # The optional measurement consent never authorises advertising
        # distributed through telecommunication networks (FR-029).
        return (BLOCKER_SUBSCRIBER_CONSENT_NOT_SEPARATE,)
    if consent.scope != SUBSCRIBER_PRIOR_CONSENT_SCOPE:
        return (BLOCKER_SUBSCRIBER_CONSENT_OUT_OF_SCOPE,)
    if consent.state == CONSENT_STATE_GRANTED:
        return ()
    if consent.state == CONSENT_STATE_REVOKED:
        return (BLOCKER_SUBSCRIBER_CONSENT_REVOKED,)
    if consent.state == CONSENT_STATE_DENIED:
        return (BLOCKER_SUBSCRIBER_CONSENT_DENIED,)
    return (BLOCKER_SUBSCRIBER_CONSENT_MISSING,)


# --- The trace --------------------------------------------------------------


def recipient_revocation_trace(
    register: AdvertisingTransferRegister,
    *,
    recipient: str,
    purpose: str,
) -> dict[str, Any] | None:
    """Show that the revocation reached the recipient, and nothing else.

    The trace answers FR-049: which recipient, which purposes, when the consent
    was withdrawn, whether the recipient confirmed the withdrawal, by which
    method and when, and which transfers were refused afterwards. It names no
    visitor and no account, and :func:`assert_metadata_only_trace` refuses a
    value that looks like personal data or a credential.
    """

    revocation = register.revocation(recipient=recipient, purpose=purpose)
    if revocation is None:
        return None
    refusal_records = tuple(
        record
        for record in register.refusals
        if record.recipient == recipient and record.purpose == purpose and record.transfer_ref
    )
    refusal_refs = tuple(record.transfer_ref for record in refusal_records)
    trace = {
        **revocation.as_dict(),
        "retransfer_refused": bool(refusal_records),
        # Keep the original list-of-references field for consumers that only need
        # to answer whether a reference was refused.  The records carry the
        # per-refusal facts needed to render an accurate trace.
        "refused_transfer_refs": list(dict.fromkeys(refusal_refs)),
        "refused_transfer_records": [record.as_dict() for record in refusal_records],
    }
    assert_metadata_only_trace(trace)
    return trace


def assert_metadata_only_trace(payload: Mapping[str, Any]) -> None:
    """Refuse a trace that carries personal data or a security credential.

    The opaque transfer reference is a hex digest, and the shared checker reads a
    long run of digits as a possible phone number. Exactly that shape is
    replaced before the check runs, so the reference stays usable while every
    other value — including one smuggled into a reference field — is still
    checked for names, addresses, credentials and paths.
    """

    view = _metadata_only_view(payload)
    findings = find_forbidden_fields(view) + find_security_credential_fields(view)
    unique = tuple(dict.fromkeys(findings))
    if unique:
        raise AdvertisingTransferTraceViolation(unique)


def _metadata_only_view(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        return {key: _metadata_only_view(value) for key, value in payload.items()}
    if isinstance(payload, str):
        return OPAQUE_TRANSFER_REFERENCE_RE.sub(OPAQUE_TRANSFER_REFERENCE_PLACEHOLDER, payload)
    if isinstance(payload, (list, tuple, set, frozenset)):
        return [_metadata_only_view(item) for item in payload]
    return payload


def revocation_trace_lines(trace: Mapping[str, Any]) -> tuple[str, ...]:
    """Render a trace as the metadata-only state lines the operator keeps.

    New traces carry ``refused_transfer_records`` so every refusal keeps its own
    timestamp.  Traces produced before that field existed only carry
    ``refused_transfer_refs``; those legacy traces use the revocation timestamp as
    their best available value and are never mixed with the new representation.
    """

    assert_metadata_only_trace(trace)
    lines = [
        f"{REVOCATION_RECORD_KEYWORD} recipient={trace.get('recipient')} "
        f"purposes={','.join(str(purpose) for purpose in trace.get('purposes', ()))} "
        f"revoked_at={trace.get('revoked_at')} "
        f"delivery_state={trace.get('delivery_state')} "
        f"method={trace.get('delivery_method')} "
        f"delivered_at={trace.get('delivered_at') or '-'} "
        f"evidence_ref={trace.get('evidence_ref') or '-'}"
    ]

    if "refused_transfer_records" in trace:
        records = trace["refused_transfer_records"]
        if not isinstance(records, (list, tuple)):
            raise ValueError("refused_transfer_records must be a list or tuple")
        for record in records:
            if not isinstance(record, Mapping):
                raise ValueError("refused_transfer_records entries must be mappings")
            if "transfer_ref" not in record or "refused_at" not in record:
                raise ValueError("refused transfer records require transfer_ref and refused_at")
            lines.append(
                f"{REFUSAL_RECORD_KEYWORD} recipient={record.get('recipient', trace.get('recipient'))} "
                f"purpose={record.get('purpose', '')} transfer_ref={record['transfer_ref']} "
                f"refused_at={record['refused_at']} reason={record.get('reason', 'unspecified')}"
            )
        return tuple(lines)

    # Legacy traces have no per-refusal timestamp. Keep their old rendering
    # exactly, but do not use this fallback for a trace that declares the new
    # records field.
    purposes = trace.get("purposes", ())
    legacy_purpose = next(iter(purposes), "") if isinstance(purposes, (list, tuple)) else ""
    for transfer_ref in trace.get("refused_transfer_refs", ()):
        lines.append(
            f"{REFUSAL_RECORD_KEYWORD} recipient={trace.get('recipient')} "
            f"purpose={legacy_purpose} transfer_ref={transfer_ref} "
            f"refused_at={trace.get('revoked_at')} reason={BLOCKER_RECIPIENT_REVOKED}"
        )
    return tuple(lines)


def append_advertising_transfer_lines(path: str, lines: tuple[str, ...]) -> None:
    """Publish metadata-only lines atomically and without duplicate records.

    The existing file is read and validated before any replacement is attempted.
    A file with an unterminated final line is treated as a torn/malformed write and
    rejected, because appending to it would silently merge two records. The new
    contents are written to a sibling temporary file and made visible with one
    ``os.replace`` call, so a validation or write failure leaves the old file
    untouched.
    """

    pending_lines = tuple(lines)
    for line in pending_lines:
        if not isinstance(line, str) or not line or "\n" in line or "\r" in line:
            raise ValueError("advertising transfer lines must be non-empty single lines")
        assert_metadata_only_trace({"line": line})

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    # ponytail: one advisory lock per metadata file; shard only if transfer volume makes it a bottleneck.
    with open(f"{path}.lock", "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            try:
                with open(path, encoding="utf-8", newline="") as state_file:
                    existing = state_file.read()
                path_exists = True
            except FileNotFoundError:
                existing = ""
                path_exists = False

            if existing and not existing.endswith("\n"):
                raise ValueError("advertising transfer state file has malformed trailing content")

            existing_lines = set(existing.splitlines())
            additions: list[str] = []
            for line in pending_lines:
                if line not in existing_lines:
                    additions.append(line)
                    existing_lines.add(line)

            # Preserve the old append helper's create-on-empty-call behaviour,
            # while making repeated calls true no-ops once the file already exists.
            if path_exists and not additions:
                return

            content = existing + "".join(f"{line}\n" for line in additions)
            temporary_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    newline="",
                    dir=directory,
                    prefix=f".{os.path.basename(path)}.",
                    suffix=".tmp",
                    delete=False,
                ) as state_file:
                    temporary_path = state_file.name
                    state_file.write(content)
                    state_file.flush()
                    os.fsync(state_file.fileno())
                os.replace(temporary_path, path)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    with contextlib.suppress(FileNotFoundError):
                        os.unlink(temporary_path)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
