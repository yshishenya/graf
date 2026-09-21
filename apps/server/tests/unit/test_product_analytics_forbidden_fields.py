"""Границы проверки запрещённых полей: дата — не телефон (FR-008).

Общий предикат значений отвергает всё, что похоже на контактные данные,
секрет или локальный путь. Отвергать при этом служебное время события нельзя:
``occurred_at`` — обязательное поле каждой вехи, и метка времени вида
``2026-09-18T12:00:00+00:00`` не является ничьим номером телефона.

Правило одно и то же для всех трёх сущностей: даты и время из проверки
телефона исключаются, а настоящий номер телефона, почта, токен, локальный
путь и запрещённое имя поля отвергаются по-прежнему.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from twobrain_rec_server.product_analytics.acquisition import (
    build_client_acquisition_attribute,
    build_visit_attribution,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ForbiddenFieldViolation,
    assert_no_forbidden_fields,
    assert_no_security_credential_fields,
    find_anonymous_aggregate_violations,
    find_client_acquisition_violations,
    find_forbidden_fields,
    find_security_credential_fields,
    find_visit_attribution_violations,
)
from twobrain_rec_server.product_analytics.identity import build_safe_identity

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

ISO_DATES_AND_TIMES = (
    "2026-09-18",
    "2026-09-18T12:00:00+00:00",
    "2026-09-18T12:00:00Z",
    "2026-09-18T12:00:00.123456+00:00",
    "2026-09-18 12:00:00+00:00",
    "2026-09-18 12:00:00Z",
    "2026-09-18T12:00",
    "2026-01-01/2026-09-18",
    "2026-09-01 - 2026-09-18",
    "2026.09.18",
    "1234-56-78",
)

PHONE_NUMBERS = (
    "+7 916 123-45-67",
    "+7 (916) 123-45-67",
    "8-916-123-45-67",
    "8 916 123 45 67",
    "8 (916) 123-45-67",
    "+79161234567",
    "89161234567",
    "9161234567",
    "916 123 45 67",
    "+1 (555) 123-4567",
    "+44 20 7946 0958",
    "8-800-555-35-35",
)


@pytest.mark.parametrize("value", ISO_DATES_AND_TIMES)
def test_a_date_or_a_time_is_never_read_as_a_phone_number(value: str) -> None:
    assert find_forbidden_fields({"occurred_at": value}) == ()
    assert find_forbidden_fields({"expires_at": value, "first_seen_at": value}) == ()
    assert_no_forbidden_fields({"occurred_at": value})


@pytest.mark.parametrize("value", PHONE_NUMBERS)
def test_a_real_phone_number_is_still_refused(value: str) -> None:
    findings = find_forbidden_fields({"note": value})

    assert findings == ("$.note",)
    with pytest.raises(ForbiddenFieldViolation):
        assert_no_forbidden_fields({"note": value})


def test_a_phone_number_written_beside_a_timestamp_is_still_refused() -> None:
    # Дата не прячет то, что написано рядом с ней: маскируется только сам
    # токен даты, остальное значение проверяется как обычно.
    assert find_forbidden_fields({"note": "2026-09-18T12:00:00+00:00 +7 916 123-45-67"}) == (
        "$.note",
    )
    assert find_forbidden_fields(
        {"note": "позвонить 2026-09-18 12:00:00 по номеру 8-916-123-45-67"}
    ) == ("$.note",)


def test_email_a_token_and_a_local_path_are_still_refused() -> None:
    assert find_forbidden_fields({"note": "customer@example.com"}) == ("$.note",)
    assert find_forbidden_fields({"note": "access_token=abcdef123456"}) == ("$.note",)
    assert find_forbidden_fields({"note": "/Users/ivan/secret/meeting.m4a"}) == ("$.note",)
    assert find_security_credential_fields({"note": "C:\\Users\\ivan\\secret.txt"}) == ("$.note",)
    with pytest.raises(ForbiddenFieldViolation):
        assert_no_security_credential_fields({"note": "signed_url=https://example.test/a"})


def test_forbidden_field_names_are_unaffected() -> None:
    payload = {
        "full_name": "Иван Петров",
        "email": "customer@example.com",
        "phone": "89161234567",
        "local_path": "/Users/ivan/meeting.m4a",
        "transcript": "текст встречи",
    }

    assert set(find_forbidden_fields(payload)) == {
        "$.full_name",
        "$.email",
        "$.phone",
        "$.local_path",
        "$.transcript",
    }


@pytest.mark.parametrize(
    "value",
    (
        "42",
        "7",
        "2026",
        "1.2.3",
        "1.2.3-beta.4",
        "2026-09-18T12:00:00+00:00",
        "graf_pseudo_user_0123456789abcdef",
    ),
)
def test_a_short_number_a_version_and_a_pseudonym_are_not_phones(value: str) -> None:
    assert find_forbidden_fields({"value": value}) == ()


@pytest.mark.parametrize("value", ("1234567890", "1234567890123456789", "123456789012345678"))
def test_a_bare_run_of_ten_or_more_digits_stays_refused(value: str) -> None:
    # Ослабления нет: неразмеченная длинная серия цифр по-прежнему считается
    # контактным значением, поэтому идентификатор клика в событие не попадает.
    assert find_forbidden_fields({"value": value}) == ("$.value",)


def test_the_timestamp_of_a_real_event_is_not_a_forbidden_field() -> None:
    """Дефект целиком: метка времени вехи больше не отвергается (FR-008).

    Событие собирается настоящим построителем, поэтому проверяется ровно тот
    payload, который уходит провайдеру, включая ``occurred_at``.
    """
    identity = build_safe_identity(user_source_id=str(uuid4()))
    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id=identity.stable_pseudonymous_user_id,
        occurred_at=NOW,
        properties={"auth_method_category": "email", "account_connection_state": "connected"},
    )

    payload = event.as_payload()
    assert payload["occurred_at"] == NOW.isoformat()
    assert find_forbidden_fields(payload) == ()
    assert find_security_credential_fields(payload) == ()


def test_the_level_two_entities_accept_their_own_timestamps() -> None:
    visit = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q3_b2c_launch_ru",
        first_seen_at=NOW,
    )
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q3_b2c_launch_ru",
        captured_at=NOW,
        linked_automatically=True,
    )

    assert visit.as_dict()["first_seen_at"] == NOW.isoformat()
    assert find_visit_attribution_violations(visit.as_dict()) == ()
    assert find_client_acquisition_violations(attribute.as_analytics_dict()) == ()
    assert find_anonymous_aggregate_violations(
        {"bucket_date": "2026-09-18", "surface": "public_download", "visits": 1}
    ) == ()


def test_the_level_two_entities_keep_refusing_contact_data() -> None:
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        captured_at=NOW,
    ).as_analytics_dict()
    attribute["term"] = "+7 916 123-45-67"

    assert find_client_acquisition_violations(attribute) == ("$.term",)
    assert find_visit_attribution_violations(
        {"attribution_ref": "graf_visit_a1b2c3d4", "landing_path": "/download", "term": "x@y.ru"}
    ) == ("$.term",)
