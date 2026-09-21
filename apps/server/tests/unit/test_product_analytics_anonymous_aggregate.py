"""Unit contracts of the level 1 anonymous aggregate (T001, T009, T010, T075)."""

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics import anonymous_aggregate as aggregate
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    ANONYMOUS_AGGREGATE_SURFACES,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    PUBLIC_PAGE_PATHS,
    AnonymousAggregateBucket,
    build_anonymous_aggregate_bucket,
    build_anonymous_aggregate_bucket_from_attribution,
    build_minimum_bucket_size_disclosure,
    device_class_from_user_agent,
    is_disclosed_bucket,
    reportable_aggregate_criteria,
    sanitize_anonymous_aggregate_label,
    surface_for_public_path,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
    find_anonymous_aggregate_violations,
)
from twobrain_rec_server.product_analytics.traffic_class import (
    REPORTED_TRAFFIC_CLASSES,
    classify_public_traffic,
)
from twobrain_rec_server.public.analytics import PUBLIC_ANALYTICS_CONSENT_PATHS

MODULE_SOURCE = Path(aggregate.__file__).read_text(encoding="utf-8")


def test_anonymous_aggregate_module_never_imports_the_identity_module() -> None:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(MODULE_SOURCE)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(f"{module}.{alias.name}" for alias in node.names)

    assert imported, "the module must import something for this check to mean anything"
    offenders = sorted(name for name in imported if name.split(".")[-1] == "identity")
    assert offenders == [], (
        "level 1 must not import identity.py: pseudonyms are not anonymous, and "
        "the salt plus the raw identifier stay with the operator"
    )
    for pseudonym_symbol in ("stable_pseudonym", "stable_pseudonymous_user_id", "PSEUDONYM_PREFIX"):
        assert pseudonym_symbol not in MODULE_SOURCE


def test_anonymous_aggregate_module_states_the_identity_ban_in_its_docstring() -> None:
    docstring = aggregate.__doc__ or ""
    assert "MUST NOT import" in docstring
    assert "identity" in docstring
    assert "pseudonym" in docstring.lower()


def test_public_aggregate_paths_match_the_public_route_inventory() -> None:
    assert set(PUBLIC_PAGE_PATHS) == set(PUBLIC_ANALYTICS_CONSENT_PATHS)
    assert surface_for_public_path("/privacy") == "public_privacy"
    assert surface_for_public_path("/analytics-consent") == "public_analytics_consent"
    assert surface_for_public_path("/download/") == "public_download"
    assert surface_for_public_path("/cabinet") is None
    assert len(ANONYMOUS_AGGREGATE_SURFACES) == len(set(ANONYMOUS_AGGREGATE_SURFACES))


def test_bucket_carries_only_allowlisted_dimensions() -> None:
    bucket = build_anonymous_aggregate_bucket(path="/", source="yandex_direct", medium="cpc")

    assert set(bucket.as_dict()) == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS)
    assert set(bucket.as_row()) == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS) | {"id"}
    assert find_anonymous_aggregate_violations(bucket.as_dict()) == ()


def test_private_paths_are_never_counted() -> None:
    for path in ("/meetings", "/cabinet", "/api/v1/health/live", "", "/download/raw.wav"):
        with pytest.raises(ValueError):
            build_anonymous_aggregate_bucket(path=path)


def test_a_query_string_never_reaches_the_stored_path() -> None:
    for path in (
        "/download?utm_source=yandex_direct",
        "/?token=abc#fragment",
        "/privacy?email=customer@example.com",
    ):
        with pytest.raises(ValueError):
            build_anonymous_aggregate_bucket(path=path)

    bucket = build_anonymous_aggregate_bucket(path="/download")
    assert bucket.landing_path == "/download"
    assert "?" not in bucket.landing_path
    assert "#" not in bucket.landing_path


@pytest.mark.parametrize(
    "unsafe",
    [
        "customer@example.com",
        "user.name@example.ru",
        "+7 999 111 22 33",
        "79991112233",
        "1234567890",
        "IvanPetrov",
        "ivan.petrov",
        "Ivan.Petrov",
        "Иван",
        "https://private.example/signed?token=abc",
        "access_token",
        "signed_url",
        "a" * 97,
        "",
        "  ",
        None,
        42,
    ],
)
def test_unsafe_campaign_labels_are_dropped(unsafe) -> None:
    assert sanitize_anonymous_aggregate_label(unsafe) is None


@pytest.mark.parametrize(
    "safe",
    [
        "yandex_direct",
        "cpc",
        "2026q3_b2c_launch_ru",
        "hero_a",
        "meeting_recorder",
        "campaign-42",
        "brand:launch.2026",
    ],
)
def test_legitimate_campaign_labels_are_kept(safe: str) -> None:
    assert sanitize_anonymous_aggregate_label(safe) == safe


def test_source_and_medium_are_lowercased_like_the_public_layer() -> None:
    bucket = build_anonymous_aggregate_bucket(
        path="/download", source="Yandex_Direct", medium="CPC"
    )

    assert bucket.source == "yandex_direct"
    assert bucket.medium == "cpc"


def test_unsafe_labels_never_reach_a_bucket() -> None:
    bucket = build_anonymous_aggregate_bucket(
        path="/",
        source="Email",
        medium="cpc",
        campaign="customer@example.com",
        content="https://private.example/signed?token=abc",
        term="+7 999 111 22 33",
    )

    assert bucket.source == "email"
    assert bucket.medium == "cpc"
    assert bucket.campaign is None
    assert bucket.content is None
    assert bucket.term is None


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (None, "unknown"),
        ("", "unknown"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "desktop"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "desktop"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile", "mobile"),
        ("Mozilla/5.0 (Linux; Android 13; Pixel 7) Mobile", "mobile"),
        ("Mozilla/5.0 (iPad; CPU OS 17_0) Mobile", "tablet"),
        ("Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit", "tablet"),
        ("curl/8.4.0", "unknown"),
    ],
)
def test_user_agent_is_reduced_to_a_device_class(user_agent: str | None, expected: str) -> None:
    assert device_class_from_user_agent(user_agent) == expected


def test_user_agent_string_is_never_part_of_a_bucket() -> None:
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    bucket = build_anonymous_aggregate_bucket(
        path="/",
        device_class=device_class_from_user_agent(user_agent),
    )

    assert bucket.device_class == "desktop"
    assert user_agent not in str(bucket.as_dict())


def test_unknown_dimension_values_fall_back_to_unknown() -> None:
    bucket = build_anonymous_aggregate_bucket(
        path="/", device_class="toaster", referrer_category="telepathy"
    )

    assert bucket.device_class == "unknown"
    assert bucket.referrer_category == "unknown"


def test_bucket_hour_is_validated_and_optional() -> None:
    assert build_anonymous_aggregate_bucket(path="/").bucket_hour is None
    assert build_anonymous_aggregate_bucket(path="/", bucket_hour=13).bucket_hour == 13
    for invalid in (-1, 24, 99):
        with pytest.raises(ValueError):
            build_anonymous_aggregate_bucket(path="/", bucket_hour=invalid)


def test_bucket_date_follows_the_occurrence_moment_in_utc() -> None:
    moment = datetime(2026, 9, 18, 22, 30, tzinfo=UTC)
    bucket = build_anonymous_aggregate_bucket(path="/", occurred_at=moment)

    assert bucket.bucket_date.isoformat() == "2026-09-18"


def test_bucket_counter_must_be_positive() -> None:
    assert build_anonymous_aggregate_bucket(path="/", visits=4).visits == 4
    for invalid in (0, -3):
        with pytest.raises(ValueError):
            build_anonymous_aggregate_bucket(path="/", visits=invalid)


def test_bucket_is_built_from_the_public_attribution_mapping() -> None:
    bucket = build_anonymous_aggregate_bucket_from_attribution(
        {
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": "2026q3_b2c_launch_ru",
            "utm_content": "customer@example.com",
            "utm_term": None,
            "referrer_category": "paid",
        },
        path="/download",
    )

    assert bucket.source == "yandex_direct"
    assert bucket.medium == "cpc"
    assert bucket.campaign == "2026q3_b2c_launch_ru"
    assert bucket.content is None
    assert bucket.referrer_category == "paid"
    assert bucket.surface == "public_download"


def test_bucket_key_is_the_upsert_conflict_target() -> None:
    first = build_anonymous_aggregate_bucket(path="/", source="yandex_direct")
    same = build_anonymous_aggregate_bucket(path="/", source="yandex_direct", visits=5)
    other = build_anonymous_aggregate_bucket(path="/", source="google")

    assert first.bucket_key() == same.bucket_key()
    assert first.bucket_key() != other.bucket_key()
    assert len(first.bucket_key()) == 12


def test_minimum_bucket_size_rule_hides_small_buckets() -> None:
    assert MINIMUM_AGGREGATE_BUCKET_SIZE == 3
    assert is_disclosed_bucket(1) is False
    assert is_disclosed_bucket(2) is False
    assert is_disclosed_bucket(3) is True
    assert is_disclosed_bucket(1, minimum_bucket_size=1) is True

    disclosure = build_minimum_bucket_size_disclosure(suppressed_buckets=2)
    assert disclosure["minimum_bucket_size"] == MINIMUM_AGGREGATE_BUCKET_SIZE
    assert disclosure["suppressed_buckets"] == 2
    assert "not disclosed" in disclosure["caveat"]


def test_report_criteria_combine_traffic_class_and_bucket_size() -> None:
    rendered = " ".join(str(criteria) for criteria in reportable_aggregate_criteria())

    assert "traffic_class" in rendered
    assert "visits" in rendered


def test_internal_and_service_traffic_is_counted_but_not_reportable() -> None:
    internal = build_anonymous_aggregate_bucket(path="/", traffic_class="internal")
    support = build_anonymous_aggregate_bucket(path="/", traffic_class="support")
    automated = build_anonymous_aggregate_bucket(path="/", traffic_class="automated")
    external = build_anonymous_aggregate_bucket(path="/")

    assert internal.traffic_class == "internal"
    assert support.traffic_class == "support"
    assert automated.traffic_class == "automated"
    assert external.traffic_class == "external"
    assert external.is_reportable() is True
    for bucket in (internal, support, automated):
        assert bucket.is_reportable() is False
        # The marker survives storage: it is a label, not an identifier.
        assert bucket.as_dict()["traffic_class"] == bucket.traffic_class
    assert REPORTED_TRAFFIC_CLASSES == ("external",)


def test_unknown_traffic_class_fails_closed_to_external_but_unreportable_unknown() -> None:
    bucket = build_anonymous_aggregate_bucket(path="/", traffic_class="mystery")

    assert bucket.traffic_class == "external"
    assert aggregate.is_disclosed_bucket(bucket.visits) is False
    assert aggregate.AnonymousAggregateBucket is AnonymousAggregateBucket


def test_configured_operator_address_and_network_are_internal_only() -> None:
    assert classify_public_traffic(
        client_host="198.51.100.24",
        internal_hosts=("198.51.100.24",),
    ) == "internal"
    assert classify_public_traffic(
        client_host="10.20.4.8",
        internal_hosts=("10.20.0.0/16",),
    ) == "internal"
    assert classify_public_traffic(
        client_host="203.0.113.9",
        internal_hosts=("10.20.0.0/16",),
    ) == "external"
    assert classify_public_traffic(
        client_host="10.20.4.8",
        internal_hosts=(),
    ) == "external"


def test_operator_marker_classifies_a_request_without_keeping_identifiers() -> None:
    marker = classify_public_traffic(
        headers={"x-graf-traffic-class": "test"},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        client_host="127.0.0.1",
        internal_hosts=("127.0.0.1",),
    )
    crawler = classify_public_traffic(user_agent="Googlebot/2.1 (+http://www.google.com/bot.html)")

    assert marker == "test"
    assert crawler == "automated"


def test_public_query_marker_cannot_exclude_a_visit_from_reports() -> None:
    assert classify_public_traffic(
        query_params={"graf_traffic_class": "support"},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        client_host="203.0.113.9",
        internal_hosts=(),
    ) == "external"


def test_device_class_from_a_bucket_is_the_only_device_dimension() -> None:
    bucket = build_anonymous_aggregate_bucket(path="/", device_class="mobile")

    assert list(bucket.as_dict()) == [
        "bucket_date",
        "bucket_hour",
        "surface",
        "landing_path",
        "source",
        "medium",
        "campaign",
        "content",
        "term",
        "device_class",
        "referrer_category",
        "traffic_class",
        "visits",
    ]
