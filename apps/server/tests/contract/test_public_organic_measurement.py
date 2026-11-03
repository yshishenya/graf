import asyncio
import json
import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.product_analytics.acquisition import (
    build_client_acquisition_attribute,
    build_visit_attribution,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    ANONYMOUS_PAGE_SURFACES,
    PUBLIC_PAGE_SURFACES,
    surface_for_public_path,
)
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
)
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_SURFACES,
    PUBLIC_VISIT_ATTRIBUTION_COOKIE,
    PUBLIC_VISIT_ATTRIBUTION_VERSION,
)

PAGES = {
    '/transcription': 'public_transcription',
    '/meeting-minutes': 'public_meeting_minutes',
    '/record-without-bot': 'public_record_without_bot',
    '/guides/rasshifrovka-zapisi-zoom': 'public_zoom_recording_guide',
}


def rows(database_url, query):
    async def read():
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                return [dict(row._mapping) for row in await connection.execute(text(query))]
        finally:
            await engine.dispose()
    return asyncio.run(read())


@pytest.mark.parametrize('path,surface', PAGES.items())
def test_search_entry_counts_current_page_without_cookie_or_profile(
    path, surface, client, postgres_seeded_database_url, monkeypatch,
):
    import twobrain_rec_server.public.analytics as analytics
    import twobrain_rec_server.public.templates as templates

    client.app.state.settings.env = "production"
    client.app.state.settings.public_analytics_enabled = True
    client.app.state.settings.public_analytics_yandex_metrica_id = "123456"
    # A forged cookie must never enter anonymous content measurement.
    client.cookies.set(PUBLIC_VISIT_ATTRIBUTION_COOKIE, 'synthetic-untrusted-cookie')
    def reject_cookie_read(*args, **kwargs):
        raise AssertionError('anonymous-only content must not read attribution cookie')
    monkeypatch.setattr(analytics, 'read_public_visit_attribution', reject_cookie_read)
    monkeypatch.setattr(templates, 'read_public_visit_attribution', reject_cookie_read)
    for _ in range(2):
        response = client.get(
            path + '?utm_source=example&utm_campaign=private@example.com&yclid=synthetic-secret',
            headers={'referer': 'https://yandex.ru/search/?text=synthetic', 'user-agent': 'Mozilla/5.0'},
        )
        assert response.status_code == 200
        assert 'set-cookie' not in response.headers
        # JSON-LD describes the article and cannot run analytics or JavaScript.
        scripts = re.findall(r"<script([^>]*)>(.*?)</script>", response.text, re.S)
        for attrs, data in scripts:
            assert attrs.strip() == 'type="application/ld+json"'
            assert isinstance(json.loads(data), dict)
        assert '<script' not in re.sub(r"<script[^>]*>.*?</script>", "", response.text, flags=re.S)
        assert client.cookies.get(PUBLIC_VISIT_ATTRIBUTION_COOKIE) == 'synthetic-untrusted-cookie'
    buckets = rows(postgres_seeded_database_url, 'select * from anonymous_page_aggregate_buckets')
    assert len(buckets) == 1 and buckets[0]['visits'] == 2
    bucket = buckets[0]
    assert bucket['surface'] == surface and bucket['landing_path'] == path
    assert bucket['source'] == 'example' and bucket['campaign'] is None
    assert bucket['traffic_class'] == 'external'
    assert path not in PUBLIC_ANALYTICS_SURFACES
    assert 'private@example.com' not in json.dumps(buckets, default=str)
    assert 'synthetic-secret' not in json.dumps(buckets, default=str)
    assert rows(postgres_seeded_database_url, 'select count(*) as n from public_visit_attributions') == [{'n': 0}]
    assert rows(postgres_seeded_database_url, 'select count(*) as n from client_acquisition_attributes') == [{'n': 0}]


@pytest.mark.parametrize('path', PAGES)
@pytest.mark.parametrize('category,referer,agent,traffic', [
    ('organic', 'https://yandex.ru/search/', 'Mozilla/5.0', 'external'),
    ('referral', 'https://example.org/article', 'Mozilla/5.0', 'external'),
    ('direct', None, 'Mozilla/5.0', 'external'),
    ('direct', None, 'Googlebot', 'automated'),
])
def test_search_entry_preserves_source_and_traffic_classes(
    path, category, referer, agent, traffic, client, postgres_seeded_database_url,
):
    headers = {'user-agent': agent}
    if referer:
        headers['referer'] = referer
    assert client.get(path, headers=headers).status_code == 200
    bucket, = rows(postgres_seeded_database_url, 'select * from anonymous_page_aggregate_buckets')
    assert bucket['referrer_category'] == category and bucket['traffic_class'] == traffic


@pytest.mark.parametrize('path', PAGES)
@pytest.mark.parametrize('mode', ['disabled', 'withdrawn', 'database_missing', 'database_failure'])
def test_measurement_failure_never_blocks_content_or_writes_a_bucket(
    path, mode, client, postgres_seeded_database_url, monkeypatch, tmp_path,
):
    from unittest.mock import AsyncMock

    import twobrain_rec_server.public.web as web

    if mode == 'disabled':
        client.app.state.settings.product_analytics_anonymous_aggregate_enabled = False
    elif mode == 'withdrawn':
        register = tmp_path / 'withdrawal'
        register.write_text(
            'legal_basis_state_version=1\n'
            'basis_withdrawal level=anonymous_aggregate state=withdrawn '
            'withdrawn_at=2026-09-18 reason=legal_basis_withdrawn evidence_ref=ev-f289\n'
        )
        monkeypatch.setenv(BASIS_WITHDRAWAL_STATE_FILE_ENV, str(register))
    else:
        async def unavailable_session():
            yield None if mode == 'database_missing' else AsyncMock(execute=AsyncMock(side_effect=RuntimeError('synthetic')))
        client.app.dependency_overrides[web.get_public_web_db_session] = unavailable_session
    try:
        response = client.get(path + '?utm_source=example')
        assert response.status_code == 200 and 'set-cookie' not in response.headers
        assert rows(postgres_seeded_database_url, 'select count(*) as n from anonymous_page_aggregate_buckets') == [{'n': 0}]
    finally:
        if mode.startswith('database_'):
            client.app.dependency_overrides.pop(web.get_public_web_db_session, None)


def test_anonymous_inventory_does_not_include_help_private_or_unknown_paths():
    assert {path: ANONYMOUS_PAGE_SURFACES.get(path) for path in PAGES} == PAGES
    assert not set(PAGES) & set(PUBLIC_ANALYTICS_SURFACES)
    assert not set(PAGES) & set(PUBLIC_PAGE_SURFACES)
    assert all(surface_for_public_path(path) is None for path in PAGES)
    assert all(path not in ANONYMOUS_PAGE_SURFACES for path in (
        '/help', '/help/na-mac-slyshno-tolko-odnu-storonu', '/news', '/meetings', '/guides/unknown',
    ))


@pytest.mark.parametrize('path', PAGES)
@pytest.mark.parametrize('stage', ['prepare', 'write'])
def test_real_database_timeout_returns_content_and_next_request_works(
    path, stage, client, postgres_seeded_database_url, monkeypatch,
):
    import twobrain_rec_server.product_analytics.anonymous_aggregate as aggregate
    import twobrain_rec_server.public.web as web

    async def slow_database(session, *args, **kwargs):
        await session.execute(text('select pg_sleep(5)'))

    with monkeypatch.context() as patch:
        if stage == 'prepare':
            patch.setattr(web, 'apply_tenant_context', slow_database)
        else:
            patch.setattr(aggregate, 'record_anonymous_aggregate_bucket', slow_database)
        response = client.get(path)
        assert response.status_code == 200
        assert 'set-cookie' not in response.headers
    # Recovery is a functional check, not a latency benchmark on a shared Mac.
    # The stalled request above uses the production 250 ms limits.
    with monkeypatch.context() as patch:
        patch.setattr(web, 'PUBLIC_WEB_DB_PHASE_TIMEOUT_SECONDS', 2)
        patch.setattr(aggregate, 'ANONYMOUS_AGGREGATE_WRITE_TIMEOUT_SECONDS', 2)
        assert client.get(path).status_code == 200
    assert rows(postgres_seeded_database_url,
                'select sum(visits) as n from anonymous_page_aggregate_buckets') == [{'n': 1}]


@pytest.mark.parametrize('path', PAGES)
@pytest.mark.parametrize('builder', [build_visit_attribution, build_client_acquisition_attribute])
def test_anonymous_only_path_is_rejected_by_both_attribution_builders(path, builder):
    kwargs = {'account_id': uuid4()} if builder is build_client_acquisition_attribute else {}
    with pytest.raises(ValueError):
        builder(landing_path=path, source='synthetic', **kwargs)


@pytest.mark.parametrize('path', PAGES)
def test_forged_anonymous_landing_cookie_cannot_create_level_two_visit(
    path, client, postgres_seeded_database_url,
):
    from types import SimpleNamespace

    from twobrain_rec_server.public.analytics import read_public_visit_attribution

    forged = json.dumps({
        'v': PUBLIC_VISIT_ATTRIBUTION_VERSION,
        'utm_source': 'synthetic',
        'utm_campaign': 'boundary-check',
        'landing_path': path,
        'referrer_category': 'referral',
        'first_seen_at': datetime.now(UTC).isoformat(),
    })
    client.cookies.set(PUBLIC_VISIT_ATTRIBUTION_COOKIE, forged)
    response = client.get('/download')
    assert response.status_code == 200
    assert rows(postgres_seeded_database_url,
                'select count(*) as n from public_visit_attributions') == [{'n': 0}]
    assert rows(postgres_seeded_database_url,
                'select count(*) as n from client_acquisition_attributes') == [{'n': 0}]
    visit = read_public_visit_attribution(SimpleNamespace(
        url=SimpleNamespace(path='/download', scheme='https'),
        query_params={}, headers={},
        cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: forged},
    ))
    assert visit['attribution_status'] == 'invalid'
    assert visit['utm_source'] is None and visit['utm_campaign'] is None
    assert visit['landing_path'] == '/download'
