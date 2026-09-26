"""Consent copy consistency between the site, the code and the documents (FR-046).

Before a paid launch the wording a visitor actually reads has to describe what
the measurement actually does. Three places carry that wording and they drift
apart silently:

* the **site** — the rendered consent page, the cookie policy, the privacy
  policy and the terms, which are the visitor-facing text;
* the **code** — :mod:`public.analytics` and the browser controller, which
  decide the revision, the storage key, the categories and the surfaces;
* the **published documents** — the repository copies that reviewers read.

This module compares the three and reports named divergences instead of
asserting anything on its own. Templates and documents are only ever read: the
report is what a reviewer acts on.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from twobrain_rec_server.config import Settings

# Category identifiers are the contract with the browser controller; the Russian
# labels are what a visitor reads. A category counts as disclosed when either
# form is present, because the controller injects the identifiers into the page
# config and the templates spell out the labels.
CONSENT_CATEGORY_LABELS: Mapping[str, tuple[str, ...]] = {
    "necessary": ("Необходимые",),
    "analytics": ("Аналитика",),
    "advertising_attribution": ("Рекламная атрибуция",),
    "behavior_replay": ("Поведенческая запись",),
}

# Statements that must survive in the visitor-facing text. Each is a claim the
# measurement relies on, not a stylistic choice, so the markers are the exact
# published sentences rather than paraphrases: a rewrite either keeps the claim
# or fails this comparison loudly. The wording is compared after whitespace
# normalization, so a sentence split across source lines still matches.
REQUIRED_SITE_DISCLOSURES: Mapping[str, str] = {
    "consent_is_opt_in": "неразрешенными",
    "refusal_stops_optional_measurement": "снять отдельные разрешения",
    "revocation_does_not_delete_transferred_data": "не удаляет автоматически данные, уже переданные",
    "anonymous_count_runs_without_consent": "Обезличенный счет ведется без согласия",
}

# FR-026: what a registered user's analytics data rests on and how long it is
# kept. Both are claims the published policy has to state, so they are compared
# as sentences rather than as numbers alone.
REQUIRED_REGISTERED_USER_DISCLOSURES: Mapping[str, str] = {
    "registered_user_legal_basis": "исполнения договора и законного интереса",
    "registered_user_retention": "метки кампании в записи о клиенте — 1095 дней",
    "registered_user_purposes": "не выходит за эти цели",
}

# The policy that carries the registered-user disclosure is compared as a
# document, not only through the combined site text, so a page that stops
# publishing it is reported by name.
REGISTERED_USER_POLICY_PAGE = "privacy"

# The public analytics controller is a first-party relay; the disclosure must
# say so rather than claim a direct third-party embed.
REQUIRED_SITE_EVIDENCE: Mapping[str, tuple[str, ...]] = {
    "storage_key": ("graf_public_cookie_consent",),
    "consent_storage_allowed": ("localStorage",),
    "behaviour_replay_boundary": ("Вебвизор",),
    "form_analytics_disabled": ("Анализ форм",),
    "advanced_matching_disabled": ("advanced matching",),
    "internal_replay_disabled": ("PostHog replay",),
    "first_party_relay": ("first-party",),
    "replay_stays_on_public_pages": ("карта кликов и карта прокрутки",),
}

# Surfaces the copy has to name, and the replay boundary the controller
# enforces. The controller declares every measured path itself; the copy only
# has to name the two pages a visitor can recognise, while any page path the
# copy does name must really be measured.
REQUIRED_NAMED_SURFACES = ("/", "/download")
NAMED_PATH_PATTERN = re.compile(r"<code>(/[a-z0-9/-]*)</code>")
REPLAY_SURFACE_MARKERS = ("Вебвизор", "карта кликов")

REVISION_PATTERNS: Mapping[str, re.Pattern[str]] = {
    "analytics_consent": re.compile(r"Редакция\s+(\d{4}-\d{2}-\d{2}\.\d+)"),
    "cookies": re.compile(r"Редакция\s+(\d{4}-\d{2}-\d{2}\.\d+)"),
    "privacy": re.compile(r"Редакция\s+от\s+(\d{1,2}\s+[а-яё]+\s+\d{4})"),
    "terms": re.compile(r"раскрытие аналитики\s+(\d{4}-\d{2}-\d{2}\.\d+)"),
}

SITE_PAGE_PATHS = {
    "analytics_consent": "/analytics-consent",
    "cookies": "/cookies",
    "privacy": "/privacy",
    "terms": "/terms",
}

# The banner is visitor-facing text too, but it lives in the browser controller
# rather than in a template. It is read from the controller and compared with the
# same rules as a page, because a claim that only exists in the modal is a claim
# the visitor reads (FR-005).
CONTROLLER_CONSENT_COPY_PAGE = "analytics_controller"
PUBLIC_ANALYTICS_CONTROLLER_RELATIVE_PATH = (
    "src/twobrain_rec_server/public/static/public/analytics.js"
)
CONSENT_MODAL_DESCRIPTION_PATTERN = re.compile(
    r"consentModal:\s*\{(?P<body>.*?)\n\s*\},", re.DOTALL
)
CONSENT_MODAL_DESCRIPTION_FIELD_PATTERN = re.compile(
    r"description:\s*(?P<body>.*?),\n", re.DOTALL
)
JS_STRING_LITERAL_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"')
WHITESPACE_PATTERN = re.compile(r"\s+")
PUBLISHED_REVISION_PATTERN = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}\.\d+)(?!\d)")

PUBLISHED_DOCUMENT_RELATIVE_PATHS = (
    "docs/analytics/product-activation-analytics.md",
    "specs/273-paid-traffic-analytics/contracts/operations.md",
)

# What this comparison cannot decide on its own. The list is published with the
# report so the gap is visible instead of being silently treated as verified.
EXTERNAL_PENDING_CONFIRMATIONS = (
    "provider retention setting in the analytics cabinet",
    "published policy copies hosted outside this repository",
    "the published privacy and cookie policies hosted outside this repository may "
    "state the measurement revision as a revision token instead of the copy "
    "version; only a reviewer can confirm which revision that token refers to",
)


@dataclass(frozen=True, slots=True)
class SiteConsentCopy:
    """The wording the site actually shows, once rendered."""

    pages: Mapping[str, str] = field(default_factory=dict)

    def combined(self) -> str:
        """Return every visitor-facing string as one comparable text.

        Whitespace is collapsed because a sentence may be split across source
        lines in a template or across concatenated literals in the controller:
        the claim is what matters, not where the author wrapped the line.
        """
        return normalize_consent_copy_text("\n".join(self.pages.values()))

    def page(self, name: str) -> str:
        return self.pages.get(name, "")

    def missing_pages(self) -> tuple[str, ...]:
        return tuple(name for name in REVISION_PATTERNS if name not in self.pages)


@dataclass(frozen=True, slots=True)
class PublishedConsentCopy:
    """The repository copies of the published documents that mention measurement."""

    documents: Mapping[str, str] = field(default_factory=dict)

    def combined(self) -> str:
        return "\n".join(self.documents.values())

    def missing_documents(self) -> tuple[str, ...]:
        return tuple(path for path in PUBLISHED_DOCUMENT_RELATIVE_PATHS if path not in self.documents)


@dataclass(frozen=True, slots=True)
class ConsentCopyDivergence:
    """One named disagreement between the site, the code and the documents."""

    code: str
    place: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "place": self.place, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ConsentCopyConsistencyReport:
    copy_version: str
    categories: tuple[str, ...]
    divergences: tuple[ConsentCopyDivergence, ...]
    unverified: tuple[str, ...]

    @property
    def consistent(self) -> bool:
        return not self.divergences

    @property
    def verdict(self) -> str:
        return "consistent" if self.consistent else "divergent"

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "consistent": self.consistent,
            "copy_version": self.copy_version,
            "categories": list(self.categories),
            "divergences": [divergence.as_dict() for divergence in self.divergences],
            "unverified": list(self.unverified),
        }


def normalize_consent_copy_text(text: str) -> str:
    """Collapse whitespace so a claim can be compared as one sentence."""
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def read_controller_consent_copy(controller_path: Path) -> str:
    """Return the consent modal text the controller shows, or an empty string.

    Only the modal description is read: it is the sentence a visitor sees before
    deciding, and it is the one part of the controller that makes a claim about
    measurement rather than implementing it.
    """
    if not controller_path.is_file():
        return ""
    source = controller_path.read_text(encoding="utf-8")
    modal = CONSENT_MODAL_DESCRIPTION_PATTERN.search(source)
    if modal is None:
        return ""
    field = CONSENT_MODAL_DESCRIPTION_FIELD_PATTERN.search(modal.group("body"))
    if field is None:
        return ""
    parts = JS_STRING_LITERAL_PATTERN.findall(field.group("body"))
    return normalize_consent_copy_text(" ".join(parts))


def read_site_consent_copy(
    rendered_pages: Mapping[str, str],
    *,
    static_root: Path | None = None,
    server_root: Path | None = None,
) -> SiteConsentCopy:
    """Collect the rendered pages, falling back to the templates when absent.

    Rendering normally happens through the application; the template files are a
    fallback so a reviewer can run the comparison without a running server. The
    consent banner of the browser controller is read as well, because it is
    visitor-facing text that no rendered page contains (FR-005).
    """

    pages = {name: text for name, text in rendered_pages.items() if text}
    if static_root is not None:
        for name, template_name in (
            ("analytics_consent", "analytics_consent.html"),
            ("cookies", "cookies.html"),
            ("privacy", "privacy.html"),
            ("terms", "terms.html"),
        ):
            pages.setdefault(name, (static_root / template_name).read_text(encoding="utf-8"))
    if server_root is not None:
        banner = read_controller_consent_copy(
            server_root / PUBLIC_ANALYTICS_CONTROLLER_RELATIVE_PATH
        )
        if banner:
            pages.setdefault(CONTROLLER_CONSENT_COPY_PAGE, banner)
    return SiteConsentCopy(pages=pages)


def collect_published_consent_documents(repo_root: Path) -> PublishedConsentCopy:
    """Read the repository copies; a missing copy is reported as a divergence."""

    documents: dict[str, str] = {}
    for relative in PUBLISHED_DOCUMENT_RELATIVE_PATHS:
        candidate = repo_root / relative
        if candidate.is_file():
            documents[relative] = candidate.read_text(encoding="utf-8")
    return PublishedConsentCopy(documents=documents)


def consent_revision_from_page(name: str, page_html: str) -> str | None:
    pattern = REVISION_PATTERNS.get(name)
    if pattern is None:
        return None
    match = pattern.search(page_html)
    return match.group(1) if match else None


def published_document_has_revision(document_text: str, copy_version: str) -> bool:
    """Return whether one repository document names the exact runtime revision.

    Repository copies use prose rather than one shared heading, so revision
    extraction is intentionally format-neutral here. The bounded token pattern
    prevents accepting a revision embedded in a longer numeric token while still
    allowing Markdown code, table cells, and ordinary text.
    """

    return copy_version in PUBLISHED_REVISION_PATTERN.findall(document_text)


def _disclosed_categories(site: SiteConsentCopy) -> tuple[tuple[str, ...], tuple[str, ...]]:
    combined = site.combined()
    disclosed: list[str] = []
    absent: list[str] = []
    for category, labels in CONSENT_CATEGORY_LABELS.items():
        if category in combined or any(label in combined for label in labels):
            disclosed.append(category)
        else:
            absent.append(category)
    return tuple(disclosed), tuple(absent)


def consent_copy_divergences(
    site: SiteConsentCopy,
    published: PublishedConsentCopy,
    code_terms: Mapping[str, Any],
) -> tuple[ConsentCopyDivergence, ...]:
    """Compare the three copies and name every disagreement."""

    divergences: list[ConsentCopyDivergence] = []
    combined_site = site.combined()
    copy_version = str(code_terms["copy_version"])

    for page in site.missing_pages():
        divergences.append(
            ConsentCopyDivergence(
                "site_page_not_rendered",
                page,
                f"the page {SITE_PAGE_PATHS[page]} was not read, so its copy is unknown",
            )
        )
    for document in published.missing_documents():
        divergences.append(
            ConsentCopyDivergence(
                "published_document_missing",
                document,
                "the repository copy of a published document is absent",
            )
        )

    for page in REVISION_PATTERNS:
        if page not in site.pages:
            continue
        revision = consent_revision_from_page(page, site.page(page))
        if revision is None:
            divergences.append(
                ConsentCopyDivergence(
                    "site_revision_missing",
                    page,
                    "the page does not state the copy revision a visitor is reading",
                )
            )
        elif page in {"analytics_consent", "cookies", "terms"} and revision != copy_version:
            divergences.append(
                ConsentCopyDivergence(
                    "site_revision_outdated",
                    page,
                    f"the page shows revision {revision}, the runtime copy version is {copy_version}",
                )
            )

    # Check each repository copy independently. A combined-text check can pass
    # when one document names the runtime revision and another document is stale:
    # the current token from the first copy masks the missing token in the second.
    # The document path is part of the divergence so an operator can repair the
    # exact published copy rather than treating the repository as one document.
    for document in PUBLISHED_DOCUMENT_RELATIVE_PATHS:
        document_copy = published.documents.get(document)
        if document_copy is None:
            continue
        if not published_document_has_revision(document_copy, copy_version):
            divergences.append(
                ConsentCopyDivergence(
                    "published_copy_version_not_named",
                    document,
                    f"the published copy does not name revision {copy_version} directly",
                )
            )

    disclosed, absent = _disclosed_categories(site)
    code_categories = tuple(str(category) for category in code_terms["categories"])
    for category in code_categories:
        if category not in disclosed:
            divergences.append(
                ConsentCopyDivergence(
                    "category_not_disclosed",
                    category,
                    "a category the controller can grant is absent from the published copy",
                )
            )
    for category in disclosed:
        if category not in code_categories:
            divergences.append(
                ConsentCopyDivergence(
                    "category_not_in_code",
                    category,
                    "the copy offers a category the code does not know",
                )
            )

    storage_key = str(code_terms["storage_key"])
    if storage_key not in combined_site:
        divergences.append(
            ConsentCopyDivergence(
                "storage_key_not_disclosed",
                "site",
                f"neither the decision text nor the controller names {storage_key}",
            )
        )
    for marker, markers in REQUIRED_SITE_EVIDENCE.items():
        if not any(marker_text in combined_site for marker_text in markers):
            divergences.append(
                ConsentCopyDivergence(
                    "site_disclosure_missing",
                    marker,
                    "the visitor-facing text does not state this boundary",
                )
            )

    for marker, description in REQUIRED_SITE_DISCLOSURES.items():
        if description not in combined_site:
            divergences.append(
                ConsentCopyDivergence(
                    "claim_not_stated", marker, f"the copy does not state: {description}"
                )
            )

    # FR-026: the registered-user disclosure is checked in the policy a visitor
    # reads, so a page that stops carrying it is named rather than averaged away
    # by the rest of the site.
    policy_page = site.page(REGISTERED_USER_POLICY_PAGE)
    if not policy_page:
        divergences.append(
            ConsentCopyDivergence(
                "registered_user_policy_missing",
                REGISTERED_USER_POLICY_PAGE,
                "the policy page that discloses registered-user processing was not read",
            )
        )
    else:
        normalized_policy = normalize_consent_copy_text(policy_page)
        for marker, description in REQUIRED_REGISTERED_USER_DISCLOSURES.items():
            if description not in normalized_policy:
                divergences.append(
                    ConsentCopyDivergence(
                        "registered_user_disclosure_missing",
                        marker,
                        f"the policy does not state: {description}",
                    )
                )

    measured_surfaces = tuple(str(surface) for surface in code_terms["measured_surfaces"])
    for surface in REQUIRED_NAMED_SURFACES:
        if f"<code>{surface}</code>" not in combined_site and f"`{surface}`" not in combined_site:
            divergences.append(
                ConsentCopyDivergence(
                    "surface_not_disclosed",
                    surface,
                    "a measured surface is not named in the copy",
                )
            )
    for named_path in sorted(set(NAMED_PATH_PATTERN.findall(combined_site))):
        if named_path == "/":
            continue
        if named_path not in measured_surfaces:
            divergences.append(
                ConsentCopyDivergence(
                    "named_path_not_measured",
                    named_path,
                    "the copy names a page the controller does not measure",
                )
            )
    for marker in REPLAY_SURFACE_MARKERS:
        if marker not in combined_site:
            divergences.append(
                ConsentCopyDivergence(
                    "replay_boundary_not_disclosed",
                    "behavior_replay",
                    f"the copy does not state the replay boundary ({marker})",
                )
            )

    return tuple(divergences)


def code_consent_terms() -> dict[str, Any]:
    """Terms the runtime holds, read from the module that enforces them."""

    from twobrain_rec_server.public.analytics import (
        COOKIECONSENT_VERSION,
        PUBLIC_ANALYTICS_CONSENT_CATEGORIES,
        PUBLIC_ANALYTICS_CONSENT_PATHS,
        PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY,
        PUBLIC_ANALYTICS_CONSENT_VERSION,
        PUBLIC_ANALYTICS_REPLAY_SURFACES,
        PUBLIC_ANALYTICS_SURFACES,
    )

    return {
        "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        "configured_copy_version": Settings().public_analytics_consent_copy_version,
        "product_copy_version": Settings().product_analytics_consent_copy_version,
        "cookieconsent_version": COOKIECONSENT_VERSION,
        "storage_key": PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY,
        "categories": tuple(PUBLIC_ANALYTICS_CONSENT_CATEGORIES),
        "consent_paths": tuple(PUBLIC_ANALYTICS_CONSENT_PATHS),
        "measured_surfaces": tuple(PUBLIC_ANALYTICS_SURFACES),
        "replay_surfaces": tuple(PUBLIC_ANALYTICS_REPLAY_SURFACES),
        "replay_allowed_without_consent": False,
        "advanced_matching_enabled": False,
        "form_analytics_enabled": False,
    }


def consent_copy_consistency(
    site: SiteConsentCopy,
    published: PublishedConsentCopy,
    code_terms: Mapping[str, Any],
    *,
    external_pending: Iterable[str] = (),
) -> ConsentCopyConsistencyReport:
    """The report a reviewer reads before a paid launch (FR-046, SC-013)."""

    rows = consent_copy_divergences(site, published, code_terms)
    return ConsentCopyConsistencyReport(
        copy_version=str(code_terms["copy_version"]),
        categories=tuple(str(category) for category in code_terms["categories"]),
        divergences=rows,
        unverified=tuple(external_pending),
    )
