"""Unit contracts of the advertising-transfer gate (T079, T080, T082).

The gate exists because three requirements are about a legal basis and not
about convenience:

* FR-028 — an offline-conversion transfer is allowed only under a confirmed
  basis, and only when the visitor was actually told about the transfer;
* FR-029 — advertising distributed through telecommunication networks needs the
  prior consent of the subscriber, which is a different consent from the
  optional measurement consent;
* FR-049 — a withdrawn consent stops further transfers to that recipient, the
  same data is never transferred again, and the revocation leaves a
  metadata-only trace up to the recipient.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics import advertising_transfer
from twobrain_rec_server.product_analytics.advertising_transfer import (
    ADVERTISING_TRANSFER_STATE_FILE_ENV,
    BLOCKER_BASIS_MISSING,
    BLOCKER_BASIS_NOT_CONFIRMED,
    BLOCKER_BASIS_OUT_OF_SCOPE,
    BLOCKER_DISCLOSURE_INCOMPLETE,
    BLOCKER_DISCLOSURE_MISSING,
    BLOCKER_DISCLOSURE_OUTDATED,
    BLOCKER_MEASUREMENT_CONSENT_DENIED,
    BLOCKER_MEASUREMENT_CONSENT_MISSING,
    BLOCKER_MEASUREMENT_CONSENT_REVOKED,
    BLOCKER_PURPOSE_UNKNOWN,
    BLOCKER_RECIPIENT_MISMATCH,
    BLOCKER_RECIPIENT_REVOKED,
    BLOCKER_RETRANSFER_REFUSED,
    BLOCKER_SUBSCRIBER_CONSENT_MISSING,
    BLOCKER_SUBSCRIBER_CONSENT_NOT_SEPARATE,
    BLOCKER_SUBSCRIBER_CONSENT_OUT_OF_SCOPE,
    STATUS_TRANSFER_NOT_AUTHORISED,
    STATUS_TRANSFER_REVOKED,
    AdvertisingTransferTraceViolation,
    OptionalMeasurementConsent,
    TransferRefusalRecord,
    assert_metadata_only_trace,
    build_visitor_disclosure,
    evaluate_advertising_transfer,
    optional_measurement_consent_from_categories,
    read_advertising_transfer_register,
    recipient_revocation_trace,
    required_basis_scopes,
    revocation_trace_lines,
    subscriber_prior_consent_from_measurement_consent,
)

OFFLINE_PURPOSE = "yandex_offline_conversions"
TELECOM_PURPOSE = "telecom_network_advertising"
RECIPIENT = "yandex_metrica"
CONSENT_REVISION = "2026-09-15.1"

# The copy a visitor reads when the transfer really is disclosed: it names the
# advertising platform, the offline conversions and the optional category.
DISCLOSED_PAGES = {
    "analytics_consent": (
        f"Редакция {CONSENT_REVISION} от 15 сентября 2026 года. "
        "Категория «Рекламная атрибуция» отдельно разрешает передачу данных "
        "в рекламную платформу Яндекс Метрика для офлайн-конверсий."
    ),
    "cookies": "Cookie «Рекламная атрибуция» хранит только решение посетителя.",
}
# The same page names the platform but never the offline-conversion transfer.
UNDISCLOSED_PAGES = {
    "analytics_consent": (
        f"Редакция {CONSENT_REVISION}. Категория «Рекламная атрибуция» разрешает "
        "измерение на сайте и передачу данных в рекламную платформу Яндекс Метрика."
    ),
}

BASIS_LINE = (
    "basis recipient=yandex_metrica purpose=yandex_offline_conversions "
    "state=confirmed basis=consent confirmed_by=privacy_reviewer "
    "confirmed_at=2026-09-18 scope=offline_conversion_transfer_basis "
    "evidence_ref=ev-273-transfer-basis"
)
TELECOM_BASIS_LINE = (
    "basis recipient=yandex_metrica purpose=telecom_network_advertising "
    "state=confirmed basis=consent confirmed_by=privacy_reviewer "
    "confirmed_at=2026-09-18 scope=telecom_advertising_basis "
    "evidence_ref=ev-273-telecom-basis"
)
REVOCATION_LINE = (
    "revocation recipient=yandex_metrica "
    "purposes=yandex_offline_conversions revoked_at=2026-09-18 "
    "delivery_state=confirmed method=provider_support_request "
    "delivered_at=2026-09-19 evidence_ref=ev-273-revocation"
)


def _register(tmp_path: Path, *lines: str, version: str = "1"):
    path = tmp_path / "advertising-transfers"
    header = f"advertising_transfer_state_version={version}"
    path.write_text("\n".join((header, *lines)) + "\n", encoding="utf-8")
    return read_advertising_transfer_register(
        {ADVERTISING_TRANSFER_STATE_FILE_ENV: str(path)}
    )


def _confirmed_basis(tmp_path: Path):
    register = _register(tmp_path, BASIS_LINE)
    basis = register.basis(purpose=OFFLINE_PURPOSE, recipient=RECIPIENT)
    assert basis is not None and basis.recorded(), basis
    return basis


def _disclosure(pages=None):
    return build_visitor_disclosure(DISCLOSED_PAGES if pages is None else pages)


def _granted_consent() -> OptionalMeasurementConsent:
    return OptionalMeasurementConsent(state="granted")


def _transfer(tmp_path: Path, **overrides):
    arguments = {
        "purpose": OFFLINE_PURPOSE,
        "recipient": RECIPIENT,
        "basis": _confirmed_basis(tmp_path),
        "disclosure": _disclosure(),
        "measurement_consent": _granted_consent(),
        "expected_disclosure_revision": CONSENT_REVISION,
    }
    arguments.update(overrides)
    return evaluate_advertising_transfer(**arguments)


# --- FR-028: a confirmed basis is a record, not a default -------------------


def test_transfer_without_a_recorded_basis_is_refused(tmp_path: Path) -> None:
    decision = _transfer(tmp_path, basis=None)

    assert decision.allowed is False
    assert BLOCKER_BASIS_MISSING in decision.blockers
    assert decision.status == STATUS_TRANSFER_NOT_AUTHORISED


def test_missing_register_authorises_nothing(tmp_path: Path) -> None:
    register = read_advertising_transfer_register(
        {ADVERTISING_TRANSFER_STATE_FILE_ENV: str(tmp_path / "absent")}
    )

    assert register.available is False
    assert register.basis(purpose=OFFLINE_PURPOSE, recipient=RECIPIENT) is None
    decision = _transfer(tmp_path, basis=None, register=register)
    assert decision.allowed is False
    assert BLOCKER_BASIS_MISSING in decision.blockers


def test_basis_recorded_with_another_scope_does_not_authorise_the_transfer(
    tmp_path: Path,
) -> None:
    register = _register(
        tmp_path,
        BASIS_LINE.replace(
            "scope=offline_conversion_transfer_basis", "scope=levels_1_and_2_legal_basis"
        ),
    )
    basis = register.basis(purpose=OFFLINE_PURPOSE, recipient=RECIPIENT)

    assert basis is not None
    assert basis.recorded() is True
    decision = _transfer(tmp_path, basis=basis)
    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_BASIS_OUT_OF_SCOPE,)
    assert "offline_conversion_transfer_basis" in required_basis_scopes(OFFLINE_PURPOSE)


def test_basis_for_another_recipient_is_refused(tmp_path: Path) -> None:
    basis = _confirmed_basis(tmp_path)

    decision = _transfer(tmp_path, recipient="other_advertising_platform", basis=basis)

    assert decision.allowed is False
    assert BLOCKER_RECIPIENT_MISMATCH in decision.blockers


def test_unrecorded_basis_state_is_refused(tmp_path: Path) -> None:
    register = _register(tmp_path, BASIS_LINE.replace("state=confirmed", "state=proposed"))
    basis = register.basis(purpose=OFFLINE_PURPOSE, recipient=RECIPIENT)

    assert basis is not None
    assert basis.recorded() is False
    decision = _transfer(tmp_path, basis=basis)
    assert decision.allowed is False
    assert BLOCKER_BASIS_NOT_CONFIRMED in decision.blockers


def test_unsupported_register_version_drops_every_basis_but_keeps_revocations(
    tmp_path: Path,
) -> None:
    register = _register(tmp_path, BASIS_LINE, REVOCATION_LINE, version="2")

    assert register.file_errors == ("advertising_transfer_state_version_unsupported",)
    assert register.bases == ()
    assert len(register.revocations) == 1, "a protective record must not be dropped"
    decision = _transfer(tmp_path, basis=None, register=register)
    assert BLOCKER_BASIS_MISSING in decision.blockers
    assert BLOCKER_RECIPIENT_REVOKED in decision.blockers


def test_unknown_purpose_is_refused(tmp_path: Path) -> None:
    decision = _transfer(tmp_path, purpose="print_advertising")

    assert decision.allowed is False
    assert BLOCKER_PURPOSE_UNKNOWN in decision.blockers


# --- FR-028: the disclosure to the visitor is a condition -------------------


def test_transfer_without_a_visitor_disclosure_is_refused(tmp_path: Path) -> None:
    decision = _transfer(tmp_path, disclosure=None)

    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_DISCLOSURE_MISSING,)
    assert decision.facts["disclosure_state"] == "missing"


def test_disclosure_that_never_names_the_offline_transfer_is_refused(
    tmp_path: Path,
) -> None:
    decision = _transfer(tmp_path, disclosure=_disclosure(UNDISCLOSED_PAGES))

    assert decision.allowed is False
    assert BLOCKER_DISCLOSURE_INCOMPLETE in decision.blockers
    assert decision.facts["disclosure_missing_statements"] == ["offline_conversions_named"]


def test_disclosure_from_a_previous_revision_is_refused(tmp_path: Path) -> None:
    decision = _transfer(tmp_path, expected_disclosure_revision="2026-10-01.1")

    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_DISCLOSURE_OUTDATED,)


def test_disclosure_without_a_stated_revision_is_refused(tmp_path: Path) -> None:
    pages = {
        "analytics_consent": DISCLOSED_PAGES["analytics_consent"].replace(
            f"Редакция {CONSENT_REVISION} от 15 сентября 2026 года. ", ""
        )
    }

    decision = _transfer(tmp_path, disclosure=_disclosure(pages))

    assert decision.allowed is False
    assert BLOCKER_DISCLOSURE_MISSING in decision.blockers


def test_complete_disclosure_under_the_current_revision_is_accepted(tmp_path: Path) -> None:
    decision = _transfer(tmp_path)

    assert decision.allowed is True
    assert decision.blockers == ()
    assert decision.facts["disclosure_state"] == "current"
    assert decision.facts["disclosure_copy_version"] == CONSENT_REVISION


# --- FR-028: the visitor's own decision is required ------------------------


def test_transfer_without_the_visitor_decision_is_refused(tmp_path: Path) -> None:
    decision = _transfer(tmp_path, measurement_consent=None)

    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_MEASUREMENT_CONSENT_MISSING,)


@pytest.mark.parametrize(
    ("state", "blocker"),
    (
        ("denied", BLOCKER_MEASUREMENT_CONSENT_DENIED),
        ("revoked", BLOCKER_MEASUREMENT_CONSENT_REVOKED),
        ("unknown", BLOCKER_MEASUREMENT_CONSENT_MISSING),
    ),
)
def test_negative_visitor_decision_is_never_a_permission(
    tmp_path: Path, state: str, blocker: str
) -> None:
    decision = _transfer(tmp_path, measurement_consent=OptionalMeasurementConsent(state=state))

    assert decision.allowed is False
    assert decision.blockers == (blocker,)


def test_visitor_decision_is_read_from_the_event_categories_only_when_present() -> None:
    assert optional_measurement_consent_from_categories(
        ["necessary", "analytics", "advertising_attribution"]
    ).granted() is True
    assert optional_measurement_consent_from_categories(["necessary", "analytics"]).granted() is False
    assert optional_measurement_consent_from_categories(None).granted() is False
    assert optional_measurement_consent_from_categories("advertising_attribution").granted() is False


# --- FR-029: the subscriber consent is a separate consent ------------------


def test_telecom_advertising_needs_the_prior_consent_of_the_subscriber(tmp_path: Path) -> None:
    decision = evaluate_advertising_transfer(
        purpose=TELECOM_PURPOSE,
        recipient=RECIPIENT,
        basis=None,
        disclosure=None,
        measurement_consent=_granted_consent(),
    )

    assert decision.allowed is False
    assert BLOCKER_SUBSCRIBER_CONSENT_MISSING in decision.blockers


def test_measurement_consent_never_authorises_advertising_through_telecom_networks(
    tmp_path: Path,
) -> None:
    borrowed = subscriber_prior_consent_from_measurement_consent(_granted_consent())
    decision = evaluate_advertising_transfer(
        purpose=TELECOM_PURPOSE,
        recipient=RECIPIENT,
        basis=None,
        disclosure=None,
        measurement_consent=_granted_consent(),
        subscriber_prior_consent=borrowed,
    )

    assert borrowed.grant_kind == "optional_measurement_consent"
    assert decision.allowed is False
    assert BLOCKER_SUBSCRIBER_CONSENT_NOT_SEPARATE in decision.blockers


def test_separate_prior_subscriber_consent_authorises_the_telecom_transfer(
    tmp_path: Path,
) -> None:
    from twobrain_rec_server.product_analytics.advertising_transfer import SubscriberPriorConsent

    register = _register(tmp_path, TELECOM_BASIS_LINE)
    decision = evaluate_advertising_transfer(
        purpose=TELECOM_PURPOSE,
        recipient=RECIPIENT,
        basis=register.basis(purpose=TELECOM_PURPOSE, recipient=RECIPIENT),
        # FR-029 governs this purpose through prior consent, so the disclosure
        # statement set of the offline-conversion transfer does not apply here.
        disclosure=None,
        measurement_consent=_granted_consent(),
        subscriber_prior_consent=SubscriberPriorConsent(
            state="granted",
            scope="telecom_network_advertising",
            decided_at="2026-09-18",
        ),
    )

    assert decision.allowed is True, decision.blockers


def test_a_basis_of_one_purpose_does_not_authorise_another_purpose(tmp_path: Path) -> None:
    register = _register(tmp_path, TELECOM_BASIS_LINE)

    decision = _transfer(
        tmp_path,
        basis=register.basis(purpose=TELECOM_PURPOSE, recipient=RECIPIENT),
    )

    assert decision.allowed is False
    assert BLOCKER_BASIS_OUT_OF_SCOPE in decision.blockers


def test_subscriber_consent_for_another_scope_is_refused(tmp_path: Path) -> None:
    from twobrain_rec_server.product_analytics.advertising_transfer import SubscriberPriorConsent

    register = _register(tmp_path, TELECOM_BASIS_LINE)
    decision = evaluate_advertising_transfer(
        purpose=TELECOM_PURPOSE,
        recipient=RECIPIENT,
        basis=register.basis(purpose=TELECOM_PURPOSE, recipient=RECIPIENT),
        disclosure=None,
        measurement_consent=_granted_consent(),
        subscriber_prior_consent=SubscriberPriorConsent(
            state="granted",
            scope="service_notifications",
            decided_at="2026-09-18",
        ),
    )

    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_SUBSCRIBER_CONSENT_OUT_OF_SCOPE,)


# --- FR-049: revocation stops the transfer and leaves a trace --------------


def test_recorded_revocation_stops_the_transfer(tmp_path: Path) -> None:
    register = _register(tmp_path, BASIS_LINE, REVOCATION_LINE)

    decision = _transfer(tmp_path, register=register)

    assert decision.allowed is False
    assert BLOCKER_RECIPIENT_REVOKED in decision.blockers
    assert decision.status == STATUS_TRANSFER_REVOKED
    assert decision.facts["revocation_delivery_state"] == "confirmed"


def test_revocation_trace_reaches_the_recipient_without_personal_data(
    tmp_path: Path,
) -> None:
    register = _register(tmp_path, BASIS_LINE, REVOCATION_LINE)

    trace = recipient_revocation_trace(register, recipient=RECIPIENT, purpose=OFFLINE_PURPOSE)

    assert trace is not None
    assert trace["recipient"] == RECIPIENT
    assert trace["purposes"] == [OFFLINE_PURPOSE]
    assert trace["revoked_at"] == "2026-09-18"
    assert trace["delivery_state"] == "confirmed"
    assert trace["delivered_at"] == "2026-09-19"
    assert trace["delivery_method"] == "provider_support_request"
    assert trace["evidence_ref"] == "ev-273-revocation"

    lines = revocation_trace_lines(trace)
    assert any("revocation recipient=yandex_metrica" in line for line in lines)
    assert all("graf_pseudo" not in line for line in lines)

    # Each refusal line preserves the refusal's own timestamp, not the
    # revocation timestamp. Legacy traces without records still use the old
    # fallback, but new traces must be exact.
    transfer_ref = "graf_yandex_dedupe_0123456789abcdef0123456789abcdef"
    trace_with_refusal = {
        **trace,
        "refused_transfer_records": [
            {
                "recipient": RECIPIENT,
                "purpose": OFFLINE_PURPOSE,
                "transfer_ref": transfer_ref,
                "refused_at": "2026-09-20",
                "reason": "recipient_revocation_recorded",
            }
        ],
    }
    refusal_lines = revocation_trace_lines(trace_with_refusal)
    assert any(
        f"transfer_ref={transfer_ref} refused_at=2026-09-20" in line
        for line in refusal_lines
    )
    assert all("refused_at=2026-09-18" not in line for line in refusal_lines[1:])

    # The trace is metadata only, and a value that looks like a person is
    # refused instead of being written down.
    assert_metadata_only_trace(trace)
    with pytest.raises(AdvertisingTransferTraceViolation):
        assert_metadata_only_trace({"evidence_ref": "customer@example.com"})
    with pytest.raises(AdvertisingTransferTraceViolation):
        assert_metadata_only_trace({"raw_user_id": "42"})


def test_revocation_of_another_recipient_does_not_stop_this_transfer(
    tmp_path: Path,
) -> None:
    register = _register(
        tmp_path,
        BASIS_LINE,
        REVOCATION_LINE.replace("recipient=yandex_metrica", "recipient=other_platform"),
    )

    decision = _transfer(tmp_path, register=register)

    assert decision.allowed is True, decision.blockers


def test_revocation_without_a_purpose_list_stops_every_purpose(tmp_path: Path) -> None:
    register = _register(
        tmp_path,
        BASIS_LINE,
        REVOCATION_LINE.replace("purposes=yandex_offline_conversions ", ""),
    )

    decision = _transfer(tmp_path, register=register)

    assert decision.allowed is False
    assert BLOCKER_RECIPIENT_REVOKED in decision.blockers


def test_claimed_confirmation_without_a_moment_is_reported_as_pending(
    tmp_path: Path,
) -> None:
    register = _register(
        tmp_path,
        BASIS_LINE,
        REVOCATION_LINE.replace(" delivered_at=2026-09-19", ""),
    )

    decision = _transfer(tmp_path, register=register)

    assert decision.allowed is False
    assert decision.facts["revocation_delivery_state"] == "pending"
    assert decision.revocation_trace is not None
    assert decision.revocation_trace["delivered_at"] is None


def test_refused_transfer_is_refused_again_instead_of_being_resent(
    tmp_path: Path,
) -> None:
    transfer_ref = "graf_yandex_dedupe_0123456789abcdef0123456789abcdef"
    register = _register(
        tmp_path,
        BASIS_LINE,
        REVOCATION_LINE,
        "revocation_refusal recipient=yandex_metrica "
        f"purpose={OFFLINE_PURPOSE} transfer_ref={transfer_ref} "
        "refused_at=2026-09-20 reason=recipient_revocation_recorded",
    )
    assert register.refusal(recipient=RECIPIENT, transfer_ref=transfer_ref) is not None

    decision = _transfer(tmp_path, register=register, transfer_ref=transfer_ref)

    assert decision.allowed is False
    assert BLOCKER_RETRANSFER_REFUSED in decision.blockers
    assert decision.status == STATUS_TRANSFER_REVOKED
    assert decision.revocation_trace is not None
    assert transfer_ref in decision.revocation_trace["refused_transfer_refs"]
    assert decision.revocation_trace["refused_transfer_records"] == [
        {
            "recipient": RECIPIENT,
            "purpose": OFFLINE_PURPOSE,
            "transfer_ref": transfer_ref,
            "refused_at": "2026-09-20",
            "reason": "recipient_revocation_recorded",
        }
    ]
    refusal_lines = revocation_trace_lines(decision.revocation_trace)
    assert any(
        f"transfer_ref={transfer_ref} refused_at=2026-09-20" in line
        for line in refusal_lines
    )


def test_retransfer_refusal_survives_a_register_without_the_revocation_record(
    tmp_path: Path,
) -> None:
    transfer_ref = "graf_yandex_dedupe_0123456789abcdef0123456789abcdef"
    register = _register(
        tmp_path,
        BASIS_LINE,
        "revocation_refusal recipient=yandex_metrica "
        f"purpose={OFFLINE_PURPOSE} transfer_ref={transfer_ref} "
        "refused_at=2026-09-20 reason=recipient_revocation_recorded",
    )

    decision = _transfer(tmp_path, register=register, transfer_ref=transfer_ref)

    assert decision.allowed is False
    assert decision.blockers == (BLOCKER_RETRANSFER_REFUSED,)
    assert decision.revocation_trace is None, "there is no revocation to trace, only a refusal"


def test_refusal_record_is_metadata_only() -> None:
    record = TransferRefusalRecord(
        recipient=RECIPIENT,
        purpose=OFFLINE_PURPOSE,
        transfer_ref="graf_yandex_dedupe_0123456789abcdef0123456789abcdef",
        refused_at="2026-09-20",
        reason="recipient_revocation_recorded",
    )

    assert_metadata_only_trace(record.as_dict())


def test_append_transfer_lines_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "advertising-transfers"
    lines = (
        "revocation recipient=yandex_metrica purposes=yandex_offline_conversions "
        "revoked_at=2026-09-18 delivery_state=confirmed method=provider_support_request "
        "delivered_at=2026-09-19 evidence_ref=ev-273-revocation",
        "revocation_refusal recipient=yandex_metrica purpose=yandex_offline_conversions "
        "transfer_ref=graf_yandex_dedupe_0123456789abcdef0123456789abcdef "
        "refused_at=2026-09-20 reason=recipient_revocation_recorded",
    )

    advertising_transfer.append_advertising_transfer_lines(str(path), lines)
    first = path.read_text(encoding="utf-8")
    advertising_transfer.append_advertising_transfer_lines(str(path), lines)

    assert path.read_text(encoding="utf-8") == first
    assert first.count("revocation recipient=") == 1
    assert first.count("revocation_refusal recipient=") == 1


def test_append_transfer_lines_serializes_concurrent_distinct_records(tmp_path: Path) -> None:
    path = tmp_path / "advertising-transfers"
    lines = tuple(
        "revocation_refusal recipient=yandex_metrica purpose=yandex_offline_conversions "
        f"transfer_ref=graf_yandex_dedupe_{index:032x} refused_at=2026-09-20 "
        "reason=recipient_revocation_recorded"
        for index in range(8)
    )

    with ThreadPoolExecutor(max_workers=len(lines)) as executor:
        futures = [
            executor.submit(
                advertising_transfer.append_advertising_transfer_lines,
                str(path),
                (line,),
            )
            for line in lines
        ]
        for future in futures:
            future.result()

    stored = path.read_text(encoding="utf-8")
    assert all(stored.count(line) == 1 for line in lines)


def test_append_transfer_lines_rejects_malformed_trailing_content_without_write(
    tmp_path: Path,
) -> None:
    path = tmp_path / "advertising-transfers"
    original = "advertising_transfer_state_version=1\npartial trailing record"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="malformed trailing content"):
        advertising_transfer.append_advertising_transfer_lines(
            str(path),
            ("revocation recipient=yandex_metrica purposes= revoked_at=2026-09-18",),
        )

    assert path.read_text(encoding="utf-8") == original


def test_append_transfer_lines_validates_all_lines_before_replacing(tmp_path: Path) -> None:
    path = tmp_path / "advertising-transfers"
    path.write_text("advertising_transfer_state_version=1\n", encoding="utf-8")
    original = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        advertising_transfer.append_advertising_transfer_lines(
            str(path),
            (
                "revocation recipient=yandex_metrica purposes= revoked_at=2026-09-18",
                "not metadata: customer@example.com",
            ),
        )

    assert path.read_text(encoding="utf-8") == original
