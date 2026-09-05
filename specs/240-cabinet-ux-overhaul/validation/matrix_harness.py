"""Synthetic release matrix, using production renderers and existing test data."""
from datetime import datetime, UTC
from uuid import UUID
from fastapi import Request
from fastapi.responses import HTMLResponse
from tests.fixtures.cabinet_audit_ui_harness import app
from tests.fixtures.calendar_visual_ui_harness import _profile, _theme_review, _meeting_response
from tests.unit.test_cabinet_web_shell import _review
from twobrain_rec_server.cabinet import rendering, auth_rendering
from twobrain_rec_server.cabinet.view_models import SharedWithMeMeetingItem
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.cabinet.web_routes.referrals import _referral_landing_html


@app.get('/qa/{surface}/{state}', response_class=HTMLResponse)
async def matrix(request: Request, surface: str, state: str):
    profile = _profile(request)
    embedded = request.query_params.get('embedded') == '1'
    common = dict(profile=profile, embedded=embedded, csrf_token='synthetic-csrf')
    if surface == 'referral':
        return HTMLResponse(_referral_landing_html(state=state, expires_at_label='10 сентября'))
    if surface == 'auth':
        next_path = '/desktop/meetings' if embedded else '/meetings'
        kwargs = dict(workspace_id=UUID(int=1), providers=[], next_path=next_path)
        if state.startswith('signup'):
            return HTMLResponse(auth_rendering.render_signup_page(**kwargs, mode='email' if state == 'signup-email' else None))
        if state == 'code':
            return HTMLResponse(auth_rendering.render_email_code_page(email='synthetic@example.test', state_nonce='synthetic', next_path=next_path, error='email_code_wrong'))
        return HTMLResponse(auth_rendering.render_login_page(**kwargs, error='email_connected_relogin_required' if state == 'success' else ('email_code_expired' if state == 'error' else None)))
    if surface == 'detail':
        if state == 'unavailable':
            return HTMLResponse(rendering.render_meeting_unavailable_page(**common))
        review = _theme_review() if state == 'ready' else _review()
        if state in ('partial', 'failed'):
            review.processing = review.processing.model_copy(update={'state': state})
        return HTMLResponse(rendering.render_meeting_detail_page(review, **common))
    if surface == 'settings':
        return HTMLResponse(rendering.render_settings_page(category=state, **common))
    if surface == 'list':
        response = _meeting_response('populated' if state == 'ready' else 'empty')
        if state == 'filtered':
            response.filters.q = 'Синтетический поиск'
        return HTMLResponse(rendering.render_meeting_list_page(response, **common))
    if surface == 'shared':
        if state == 'summary':
            return HTMLResponse(rendering.render_shared_meeting_summary_page(meeting_title='Синтетическая встреча', occurred_at=datetime(2026,9,1,tzinfo=UTC), duration_seconds=60, summary_sections=[], authenticated=True, embedded=embedded))
        if state == 'blocked':
            return HTMLResponse(rendering.render_meeting_unavailable_page(**common))
        items = (SharedWithMeMeetingItem('Синтетическая встреча','1 сентября','1 минута','Готово','Полный доступ',('/desktop' if embedded else '')+'/meetings/synthetic-theme'),) if state == 'ready' else ()
        return HTMLResponse(rendering.render_shared_with_me_page(items, **common))
    if surface == 'billing':
        content = render_template(
            'cabinet/pages/billing_overview_content.html', embedded=embedded,
            plan=plan_descriptor('free'), plan_code='free', storage_used=0,
            storage_capacity=250_000_000, storage_threshold='normal',
            processing_used=0, processing_used_label='0 минут',
            free_processing_limit_label='300 минут', storage_capacity_label='250 MB',
            storage_capacity_exact_label='250 000 000', processing_threshold='normal',
            processing_threshold_label='В норме', billing_enabled=state == 'ready',
            billing_owner=True, trial_result='unavailable' if state == 'error' else None,
        )
        return HTMLResponse(_page_shell('Тариф', content, **common))
    return HTMLResponse('Unknown synthetic state', status_code=404)
