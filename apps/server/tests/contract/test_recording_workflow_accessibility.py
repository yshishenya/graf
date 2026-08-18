from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CABINET_ROOT = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet"
MEETING_DETAIL = CABINET_ROOT / "templates/cabinet/pages/meeting_detail_content.html"
SHARE_DIALOG = CABINET_ROOT / "templates/cabinet/fragments/meeting_share.html"
GOVERNANCE_DIALOG = CABINET_ROOT / "templates/cabinet/fragments/meeting_governance.html"
RENDERING = CABINET_ROOT / "rendering.py"
POLICY_RENDERING = CABINET_ROOT / "review_policy_rendering.py"
JAVASCRIPT = CABINET_ROOT / "static/cabinet/cabinet.js"
STYLES = CABINET_ROOT / "static/cabinet/cabinet.css"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_meeting_detail_has_exactly_two_keyboard_operable_content_tabs() -> None:
    page = _source(MEETING_DETAIL)
    script = _source(JAVASCRIPT)

    assert page.count('role="tab"') == 2
    assert ">Итоги</button>" in page
    assert ">Расшифровка</button>" in page
    assert page.count('role="tabpanel"') == 2
    assert 'role="tablist"' in page
    assert "ArrowLeft" in script
    assert "ArrowRight" in script
    assert 'event.key === "Home"' in script
    assert 'event.key === "End"' in script
    assert "tab.tabIndex = selected ? 0 : -1" in script


def test_meeting_review_continuity_exposes_lane_hint_resize_separator_and_sticky_tabs() -> None:
    page = _source(MEETING_DETAIL)
    rendering = _source(RENDERING)
    script = _source(JAVASCRIPT)
    styles = _source(STYLES)

    assert 'class="tabs meeting-detail-tabs"' in page
    assert "data-speaker-timeline-shell" in rendering
    assert "data-speaker-timeline-resize" in rendering
    assert 'role="separator"' in rendering
    assert 'aria-orientation="horizontal"' in rendering
    assert "data-speaker-timeline-hint" in rendering
    assert "переместить воспроизведение к фрагменту записи" in rendering
    assert "data-speaker-timeline-resize" in script
    assert "aria-valuemin" in script
    assert "meeting-detail-tabs" in styles
    assert "scroll-margin-top" in styles


def test_modal_dialogs_are_named_trap_focus_and_return_it_to_the_opener() -> None:
    share = _source(SHARE_DIALOG)
    governance = _source(GOVERNANCE_DIALOG)
    policy = _source(POLICY_RENDERING)
    rendering = _source(RENDERING)
    script = _source(JAVASCRIPT)

    assert 'aria-labelledby="share-dialog-title"' in share
    assert 'aria-modal="true"' in share
    assert 'data-share-recipient-input' in share
    assert 'data-share-recipient-results' in share
    assert 'data-share-recipient-confirmation' in share
    assert 'aria-label="Найденные люди"' in share
    assert 'role="combobox"' in share
    assert 'role="listbox"' in share
    assert 'aria-activedescendant' in script
    assert 'aria-labelledby="meeting-details-title"' in governance
    assert 'aria-modal="true"' in governance
    assert 'aria-haspopup="menu"' in rendering
    assert 'aria-controls="meeting-context-more"' in rendering
    assert 'aria-expanded="false"' in rendering
    assert 'role="menu"' in governance
    assert 'role="menuitem"' in governance
    assert 'aria-labelledby="meeting-delete-title"' in policy
    assert 'tabindex="-1" data-meeting-delete-dialog-title' in policy
    assert 'tabindex="1"' not in "".join((share, governance, policy))
    assert "const modalFocusTargets" in script
    assert "const trapModalFocus" in script
    assert "results?.querySelectorAll('[role=\"option\"]')" in script
    assert 'button.setAttribute("aria-label"' in script
    assert 'button.setAttribute("role", "option")' in script
    assert 'button.setAttribute("aria-selected", "false")' in script
    assert 'event.key !== "Tab"' in script
    assert "opener.focus({ preventScroll: true })" in script
    assert "returnFocus.focus({ preventScroll: true })" in script
    assert 'dialog.querySelector("[data-meeting-delete-dialog-title]")?.focus' in script


def test_more_menu_has_complete_keyboard_model_and_visible_return_target() -> None:
    governance = _source(GOVERNANCE_DIALOG)
    script = _source(JAVASCRIPT)
    css = _source(STYLES)

    for key in ("ArrowUp", "ArrowDown", "Home", "End", "Escape"):
        assert key in script
    assert "menuItems" in script
    assert "restoreMeetingActionFocus" in script
    assert 'data-meeting-panel-open="details"' in governance
    assert "data-meeting-panel-close" in governance
    assert ".meeting-action-item" in css
    assert "min-height: 48px" in css


def test_format_selector_exposes_one_labelled_listbox_with_bounded_quick_choices() -> None:
    source = _source(RENDERING) + _source(MEETING_DETAIL) + _source(JAVASCRIPT)

    assert "data-summary-format-button" in source
    assert 'aria-haspopup="listbox"' in source
    assert "data-summary-format-listbox" in source
    assert 'role="listbox"' in source
    assert 'role="option"' in source
    assert 'data-recommended-limit="4"' in source
    assert "Все форматы…" in source
    for key in ("ArrowUp", "ArrowDown", "Home", "End", "Escape"):
        assert key in source


def test_async_status_is_polite_and_normal_states_have_at_most_one_primary_action() -> None:
    page = _source(MEETING_DETAIL)
    share = _source(SHARE_DIALOG)
    rendering = _source(RENDERING)

    assert 'role="status"' in page
    assert 'aria-live="polite"' in page
    assert share.count('aria-live="polite"') >= 2
    assert rendering.count("class=\"primary\"") <= 1
    assert share.count('class="primary"') <= 1


def test_workflow_surfaces_cover_responsive_theme_motion_contrast_and_visible_focus() -> None:
    css = _source(STYLES)

    assert "@media (max-width: 620px)" in css
    assert "@media (prefers-color-scheme: light)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (prefers-contrast: more)" in css
    assert "@media (forced-colors: active)" in css
    assert "overscroll-behavior: contain" in css
    assert ":focus-visible" in css
    assert "outline: 2px solid var(--focus-ring)" in css
    assert "transition: all" not in css
