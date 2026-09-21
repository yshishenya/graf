"""Consent copy consistency: site, code and published documents (T065, FR-046).

The public templates belong to the site agent, so this comparison never edits
them: it renders the pages, compares what they say with what the code measures,
and reports every disagreement by name. Published documents are checked one by
one so a revision in one document cannot mask a stale revision in another.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.consent_copy import (
    EXTERNAL_PENDING_CONFIRMATIONS,
    PUBLISHED_DOCUMENT_RELATIVE_PATHS,
    REGISTERED_USER_POLICY_PAGE,
    REQUIRED_REGISTERED_USER_DISCLOSURES,
    REQUIRED_SITE_DISCLOSURES,
    SITE_PAGE_PATHS,
    PublishedConsentCopy,
    code_consent_terms,
    collect_published_consent_documents,
    consent_copy_consistency,
    normalize_consent_copy_text,
    read_controller_consent_copy,
    read_site_consent_copy,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = SERVER_ROOT / "src/twobrain_rec_server/public/templates/public"
PUBLIC_ANALYTICS_SETTINGS = {
    "public_analytics_enabled": True,
    "public_analytics_validation_mode": "render_only",
    "public_analytics_yandex_metrica_id": "12345678",
    "public_analytics_replay_enabled": True,
}

EXPECTED_CONSENT_REVISION = "2026-09-15.1"

COMPARISON_DIMENSIONS = (
    "site_revision_missing",
    "site_revision_outdated",
    "category_not_disclosed",
    "category_not_in_code",
    "site_disclosure_missing",
    "claim_not_stated",
    "surface_not_disclosed",
    "named_path_not_measured",
    "replay_boundary_not_disclosed",
    "storage_key_not_disclosed",
    "published_document_missing",
    "published_copy_version_not_named",
    "site_page_not_rendered",
    "registered_user_policy_missing",
    "registered_user_disclosure_missing",
)


def _render_site_pages() -> dict[str, str]:
    """Render the consent-bearing pages exactly as a visitor receives them."""

    app = create_app(
        Settings(
            database_url="postgresql+asyncpg://nobody@127.0.0.1:1/none",
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
            **PUBLIC_ANALYTICS_SETTINGS,
        )
    )
    pages: dict[str, str] = {}
    with TestClient(app) as client:
        for name, path in SITE_PAGE_PATHS.items():
            response = client.get(path)
            assert response.status_code == 200, f"{path} did not render"
            pages[name] = response.text
    return pages


@pytest.fixture(scope="module")
def consistency_report():
    site = read_site_consent_copy(
        _render_site_pages(), static_root=TEMPLATE_ROOT, server_root=SERVER_ROOT
    )
    published = collect_published_consent_documents(REPO_ROOT)
    return consent_copy_consistency(
        site,
        published,
        code_consent_terms(),
        external_pending=EXTERNAL_PENDING_CONFIRMATIONS,
    )


def _divergences_with_codes(report, codes: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        divergence.as_dict() for divergence in report.divergences if divergence.code in codes
    ]


def test_every_published_document_names_the_runtime_revision(consistency_report) -> None:
    """T093: each repository copy names the exact runtime consent revision."""

    assert consistency_report.consistent is True
    assert consistency_report.divergences == ()
    assert consistency_report.copy_version == EXPECTED_CONSENT_REVISION
    assert PUBLISHED_DOCUMENT_RELATIVE_PATHS == (
        "docs/analytics/product-activation-analytics.md",
        "specs/273-paid-traffic-analytics/contracts/operations.md",
    )


def test_a_stale_published_document_is_not_masked_by_another_document() -> None:
    """A combined-text match must not make one stale document pass."""

    published = PublishedConsentCopy(
        documents={
            PUBLISHED_DOCUMENT_RELATIVE_PATHS[0]: (
                f"Проверяемая редакция текста согласия — `{EXPECTED_CONSENT_REVISION}`."
            ),
            PUBLISHED_DOCUMENT_RELATIVE_PATHS[1]: (
                "Проверяемая редакция текста согласия — `2026-08-01.1`."
            ),
        }
    )

    report = consent_copy_consistency(
        read_site_consent_copy(_render_site_pages(), static_root=None, server_root=SERVER_ROOT),
        published,
        code_consent_terms(),
    )

    assert [divergence.as_dict() for divergence in report.divergences] == [
        {
            "code": "published_copy_version_not_named",
            "place": PUBLISHED_DOCUMENT_RELATIVE_PATHS[1],
            "detail": (
                "the published copy does not name revision "
                f"{EXPECTED_CONSENT_REVISION} directly"
            ),
        }
    ]


def test_a_missing_published_document_is_not_replaced_by_combined_text() -> None:
    """A missing copy remains a named divergence even when another copy is valid."""

    published = PublishedConsentCopy(
        documents={
            PUBLISHED_DOCUMENT_RELATIVE_PATHS[0]: (
                f"Проверяемая редакция текста согласия — `{EXPECTED_CONSENT_REVISION}`."
            )
        }
    )

    report = consent_copy_consistency(
        read_site_consent_copy(_render_site_pages(), static_root=None, server_root=SERVER_ROOT),
        published,
        code_consent_terms(),
    )

    assert [divergence.as_dict() for divergence in report.divergences] == [
        {
            "code": "published_document_missing",
            "place": PUBLISHED_DOCUMENT_RELATIVE_PATHS[1],
            "detail": "the repository copy of a published document is absent",
        }
    ]


def test_rendered_pages_state_the_revision_the_runtime_uses(consistency_report) -> None:
    """FR-046: a visitor must be able to tell which copy they agreed to."""

    rows = _divergences_with_codes(
        consistency_report, ("site_revision_missing", "site_revision_outdated")
    )

    assert rows == [], rows
    assert consistency_report.copy_version == "2026-09-15.1"


def test_site_copy_discloses_every_category_the_code_can_grant(consistency_report) -> None:
    """The published copy must cover exactly the categories the controller knows."""

    rows = _divergences_with_codes(
        consistency_report, ("category_not_disclosed", "category_not_in_code")
    )

    assert rows == [], rows
    assert consistency_report.categories == (
        "necessary",
        "analytics",
        "advertising_attribution",
        "behavior_replay",
    )


def test_site_copy_states_the_claim_boundaries_the_measurement_relies_on(
    consistency_report,
) -> None:
    """Opt-in, refusal, revocation and the anonymous count must all be stated."""

    rows = _divergences_with_codes(
        consistency_report, ("site_disclosure_missing", "claim_not_stated")
    )

    assert rows == [], rows


def test_the_anonymous_count_claim_is_compared_as_a_whole_sentence() -> None:
    """FR-005: a stem would also match the opposite statement."""

    claim = REQUIRED_SITE_DISCLOSURES["anonymous_count_runs_without_consent"]

    assert claim == "Обезличенный счет ведется без согласия"
    assert len(claim.split()) >= 5, "a claim must be a sentence, not a stem"
    # The opposite wording must not satisfy the comparison.
    opposite = normalize_consent_copy_text(
        "Обезличенный счет посещений не ведется: он включается только после согласия."
    )
    assert claim not in opposite


def test_the_consent_banner_is_part_of_the_compared_copy() -> None:
    """FR-005: the text the modal shows is visitor-facing copy, not a comment.

    The claim is removed from every rendered page and kept only in the banner, so
    the comparison passes only if the banner really is part of the copy it reads.
    """
    claim = REQUIRED_SITE_DISCLOSURES["anonymous_count_runs_without_consent"]
    pages = {
        name: page.replace(claim, "измерение")
        for name, page in _render_site_pages().items()
    }
    published = collect_published_consent_documents(REPO_ROOT)
    banner = read_controller_consent_copy(
        SERVER_ROOT / "src/twobrain_rec_server/public/static/public/analytics.js"
    )

    assert claim in banner, "the modal must state the anonymous count claim"
    assert "Отказаться" in banner, "the modal must say how to refuse (FR-005)"

    with_banner = read_site_consent_copy(pages, static_root=None, server_root=SERVER_ROOT)
    without_banner = read_site_consent_copy(pages, static_root=None, server_root=Path("/nonexistent"))

    def _claims(site) -> list[dict[str, str]]:
        report = consent_copy_consistency(site, published, code_consent_terms())
        return [
            divergence.as_dict()
            for divergence in report.divergences
            if divergence.code == "claim_not_stated"
            and divergence.place == "anonymous_count_runs_without_consent"
        ]

    assert _claims(with_banner) == []
    assert _claims(without_banner) != []


def test_the_policy_discloses_registered_user_basis_retention_and_purposes(
    consistency_report,
) -> None:
    """FR-026: basis, retention and purposes are named in the visitor's policy."""

    rows = _divergences_with_codes(
        consistency_report,
        ("registered_user_policy_missing", "registered_user_disclosure_missing"),
    )

    assert rows == [], rows
    policy = normalize_consent_copy_text(
        read_site_consent_copy(_render_site_pages(), static_root=None).page(
            REGISTERED_USER_POLICY_PAGE
        )
    )
    for marker, claim in REQUIRED_REGISTERED_USER_DISCLOSURES.items():
        assert claim in policy, (marker, claim)
    assert "1095" in policy
    assert "90" in policy


def test_a_policy_that_stops_disclosing_registered_user_processing_is_detected() -> None:
    """A missing disclosure is reported by name, not averaged away by the site."""

    stripped = {
        name: page.replace("исполнения договора и законного интереса", "основания")
        for name, page in _render_site_pages().items()
    }
    site = read_site_consent_copy(stripped, static_root=None)
    report = consent_copy_consistency(
        site, collect_published_consent_documents(REPO_ROOT), code_consent_terms()
    )

    assert any(
        divergence.code == "registered_user_disclosure_missing"
        and divergence.place == "registered_user_legal_basis"
        for divergence in report.divergences
    )


def test_site_copy_names_every_measured_surface_and_the_replay_boundary(
    consistency_report,
) -> None:
    rows = _divergences_with_codes(
        consistency_report,
        (
            "surface_not_disclosed",
            "named_path_not_measured",
            "replay_boundary_not_disclosed",
            "storage_key_not_disclosed",
        ),
    )

    assert rows == [], rows


def test_every_rendered_page_was_read(consistency_report) -> None:
    """A page that failed to render would silently skip its own comparison."""

    assert consistency_report.copy_version
    assert _divergences_with_codes(consistency_report, ("site_page_not_rendered",)) == []
    assert SITE_PAGE_PATHS == {
        "analytics_consent": "/analytics-consent",
        "cookies": "/cookies",
        "privacy": "/privacy",
        "terms": "/terms",
    }


def test_the_report_names_what_it_cannot_verify(consistency_report) -> None:
    """An external confirmation stays visible instead of being assumed."""

    assert consistency_report.unverified == EXTERNAL_PENDING_CONFIRMATIONS
    unverified = consistency_report.as_dict()["unverified"]
    assert "provider retention setting in the analytics cabinet" in unverified
    assert any("revision token" in item for item in unverified)
    assert not any("published copies" in item for item in unverified)


def test_a_divergence_is_detected_before_the_launch() -> None:
    """Acceptance scenario 3: shifted copy is found, not shipped."""

    pages = _render_site_pages()
    shifted = dict(pages)
    shifted["cookies"] = shifted["cookies"].replace(
        "Редакция 2026-09-15.1", "Редакция 2026-08-01.1"
    )
    site = read_site_consent_copy(shifted, static_root=None)
    published = collect_published_consent_documents(REPO_ROOT)
    report = consent_copy_consistency(site, published, code_consent_terms())

    codes = {divergence.code for divergence in report.divergences}
    places = {divergence.place for divergence in report.divergences}

    assert report.consistent is False
    assert "site_revision_outdated" in codes
    assert "cookies" in places


def test_a_category_that_disappears_from_the_copy_is_detected() -> None:
    """A category the code can grant must stay visible to the visitor."""

    stripped = {
        name: re.sub(r"behavior[ _]replay|Поведенческая запись", "", page, flags=re.IGNORECASE)
        for name, page in _render_site_pages().items()
    }
    site = read_site_consent_copy(stripped, static_root=None)
    report = consent_copy_consistency(
        site, collect_published_consent_documents(REPO_ROOT), code_consent_terms()
    )

    rows = [
        divergence.as_dict()
        for divergence in report.divergences
        if divergence.code == "category_not_disclosed"
    ]

    assert report.consistent is False
    assert rows == [
        {
            "code": "category_not_disclosed",
            "place": "behavior_replay",
            "detail": "a category the controller can grant is absent from the published copy",
        }
    ]


def test_a_page_that_stops_naming_a_measured_surface_is_detected() -> None:
    stripped = {
        name: page.replace("<code>/download</code>", "<code>download</code>")
        for name, page in _render_site_pages().items()
    }
    site = read_site_consent_copy(stripped, static_root=None)
    report = consent_copy_consistency(
        site, collect_published_consent_documents(REPO_ROOT), code_consent_terms()
    )

    assert any(
        divergence.code == "surface_not_disclosed" and divergence.place == "/download"
        for divergence in report.divergences
    )


def test_the_comparison_covers_every_named_dimension(consistency_report) -> None:
    """The dimension list is documentation of what this comparison decides."""

    observed = {divergence.code for divergence in consistency_report.divergences}
    assert observed <= set(COMPARISON_DIMENSIONS)


def test_the_code_copy_version_matches_the_configured_default() -> None:
    """The runtime constant and the configured copy version must not drift."""

    terms = code_consent_terms()

    assert terms["copy_version"] == terms["configured_copy_version"]
    assert terms["product_copy_version"] != terms["copy_version"], (
        "the internal product consent copy version is a separate revision; if it "
        "becomes the same value, re-check which pages it governs"
    )
