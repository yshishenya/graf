"""T088 auth attribution selection: exact session refs and one selected visit."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from twobrain_rec_server.api import auth as auth_module
from twobrain_rec_server.product_analytics.acquisition import VisitAttribution
from twobrain_rec_server.public.analytics import (
    PUBLIC_VISIT_ATTRIBUTION_COOKIE,
    PUBLIC_VISIT_ATTRIBUTION_VERSION,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _request(*, refs: list[str], current_ref: str | None = None, query: dict[str, str] | None = None):
    payload = {
        "v": PUBLIC_VISIT_ATTRIBUTION_VERSION,
        "utm_source": "forged-browser-source",
        "utm_campaign": "forged-browser-campaign",
        "landing_path": "/download",
        "first_seen_at": NOW.isoformat(),
        "attribution_ref": current_ref or refs[0],
        "attribution_refs": refs,
    }
    return SimpleNamespace(
        query_params=dict(query or {}),
        cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: json.dumps(payload)},
        headers={},
        url=SimpleNamespace(path="/login", scheme="https"),
    )


def _visit(
    ref: str,
    *,
    first_seen_at: datetime,
    source: str | None = "yandex_direct",
    campaign: str | None = "campaign",
) -> VisitAttribution:
    return VisitAttribution(
        attribution_ref=ref,
        landing_path="/download",
        first_seen_at=first_seen_at,
        expires_at=first_seen_at + timedelta(days=90),
        source=source,
        campaign=campaign,
    )


@pytest.mark.asyncio
async def test_auth_snapshot_loads_bounded_exact_refs_and_selects_newest_non_direct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refs = [f"graf_visit_{index:016x}" for index in range(10)]
    query_ref = "graf_visit_abcdef0123456789"
    older = _visit(refs[1], first_seen_at=NOW - timedelta(days=10), campaign="same")
    newer = _visit(refs[2], first_seen_at=NOW - timedelta(days=2), campaign="same")
    seen: list[str] = []

    async def load(_db, attribution_refs, *, now):
        seen.extend(attribution_refs)
        return (older, newer)

    monkeypatch.setattr(auth_module, "load_visit_attributions_by_refs", load)
    snapshot = await auth_module._durable_attribution_snapshot(
        _request(refs=refs, current_ref=refs[0], query={"attribution_ref": query_ref}),
        db=object(),
        now=NOW,
    )

    assert len(seen) <= 8
    assert seen[0] == query_ref
    assert snapshot.selected_visit is newer
    assert snapshot.handoff is not None
    assert snapshot.handoff.campaign_context["utm_campaign"] == "same"
    assert snapshot.attribution["attribution_ref"] == newer.attribution_ref


@pytest.mark.asyncio
async def test_auth_snapshot_ignores_expired_future_direct_and_unknown_visits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired = _visit(
        "graf_visit_0123456789abcdef",
        first_seen_at=NOW - timedelta(days=90),
        campaign="expired",
    )
    future = _visit(
        "graf_visit_abcdef0123456789",
        first_seen_at=NOW + timedelta(minutes=1),
        campaign="future",
    )
    direct = _visit(
        "graf_visit_0011223344556677",
        first_seen_at=NOW - timedelta(days=1),
        source=None,
        campaign=None,
    )
    unknown = _visit(
        "graf_visit_8899aabbccddeeff",
        first_seen_at=NOW - timedelta(days=1),
        source=None,
        campaign=None,
    )

    async def load(_db, _refs, *, now):
        return (expired, future, direct, unknown)

    monkeypatch.setattr(auth_module, "load_visit_attributions_by_refs", load)
    snapshot = await auth_module._durable_attribution_snapshot(
        _request(refs=[expired.attribution_ref]),
        db=object(),
        now=NOW,
    )

    assert snapshot.selected_visit is None
    assert snapshot.handoff is None
    assert snapshot.attribution == {}


@pytest.mark.asyncio
async def test_raw_campaign_query_is_not_an_auth_attribution_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def load(_db, _refs, *, now):
        return ()

    monkeypatch.setattr(auth_module, "load_visit_attributions_by_refs", load)
    snapshot = await auth_module._durable_attribution_snapshot(
        _request(
            refs=["graf_visit_0123456789abcdef"],
            query={"utm_source": "raw", "utm_campaign": "raw-campaign"},
        ),
        db=object(),
        now=NOW,
    )

    assert snapshot.selected_visit is None
    assert snapshot.handoff is None
    assert snapshot.attribution == {}


@pytest.mark.asyncio
async def test_one_snapshot_exposes_same_selected_campaign_to_handoff_and_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _visit(
        "graf_visit_0123456789abcdef",
        first_seen_at=NOW - timedelta(hours=1),
        campaign="selected-campaign",
    )

    async def load(_db, _refs, *, now):
        return (selected,)

    monkeypatch.setattr(auth_module, "load_visit_attributions_by_refs", load)
    snapshot = await auth_module._durable_attribution_snapshot(
        _request(refs=[selected.attribution_ref]),
        db=object(),
        now=NOW,
    )

    assert snapshot.selected_visit is selected
    assert snapshot.handoff is not None
    assert snapshot.handoff.campaign_context["utm_campaign"] == selected.campaign
    assert snapshot.attribution["utm_campaign"] == selected.campaign
