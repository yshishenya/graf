from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet"


def test_cabinet_shell_preserves_primary_routes_and_landmarks() -> None:
    sections = (TEMPLATES / "components/sections.html").read_text(encoding="utf-8")
    list_page = (TEMPLATES / "pages/meeting_list_content.html").read_text(encoding="utf-8")
    detail_page = (TEMPLATES / "pages/meeting_detail_content.html").read_text(encoding="utf-8")
    list_fragment = (TEMPLATES / "fragments/meeting_list.html").read_text(encoding="utf-8")
    detail_fragment = (TEMPLATES / "fragments/meeting_detail.html").read_text(encoding="utf-8")
    browser_routes = (
        ROOT / "src/twobrain_rec_server/cabinet/web_routes/browser.py"
    ).read_text(encoding="utf-8")

    assert 'href="/meetings"' in sections
    assert "navigation.items" in sections
    for marker in ("/meetings", "/shared-with-me"):
        assert marker in browser_routes
    assert 'href="/settings"' in sections
    all_templates = sections + list_page + detail_page + list_fragment + detail_fragment
    for marker in ('id="cabinet-main"', 'id="meeting-list-region"', 'id="meeting-detail-region"'):
        assert marker in all_templates


def test_meeting_list_keeps_htmx_and_interaction_hooks() -> None:
    source = (TEMPLATES / "pages/meeting_list_content.html").read_text(encoding="utf-8")

    for marker in (
        'data-hx-target="#meeting-list-region"',
        'data-hx-select="#meeting-list-region"',
        'data-hx-swap="outerHTML"',
        "data-filter-disclosure",
        "data-sort-disclosure",
        "data-filter-reset",
        "data-manual-upload-open",
        "data-selection-toolbar",
    ):
        assert marker in source


def test_meeting_detail_keeps_tabs_dialogs_and_recovery_hooks() -> None:
    source = (TEMPLATES / "pages/meeting_detail_content.html").read_text(encoding="utf-8")

    for marker in (
        'id="detail-tab-outcomes"',
        'id="detail-tab-recording"',
        'id="detail-panel-outcomes"',
        'id="detail-panel-recording"',
        'id="summary-format-dialog"',
        "data-processing-check",
        "data-processing-new-attempt",
        "data-processing-refresh",
        "data-meeting-detail-recovery-template",
    ):
        assert marker in source


def test_responsive_shell_has_one_column_standalone_and_preserves_no_js_fallback() -> None:
    sections = (TEMPLATES / "components/sections.html").read_text(encoding="utf-8")
    css = (ROOT / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css").read_text(
        encoding="utf-8"
    )

    assert '<noscript class="cabinet-mobile-noscript">' in sections
    assert '<nav class="cabinet-mobile-nav"' in sections
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.desktop-embedded) > .sidebar'
        in css
    )
