from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_FRAGMENT = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html"
)
POLICY_RENDERING = SERVER_ROOT / "src/twobrain_rec_server/cabinet/review_policy_rendering.py"
CABINET_JS = SERVER_ROOT / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"


def test_more_menu_is_compact_ordered_and_keeps_details_separate() -> None:
    source = GOVERNANCE_FRAGMENT.read_text(encoding="utf-8")

    assert 'data-meeting-context-panel="more"' in source
    assert 'class="meeting-actions-menu"' in source
    assert 'role="menu"' in source
    assert "Экспортировать…" in source
    assert "Расшифровка или итоги" in source
    assert "Скачать аудио…" in source
    assert "Исходная запись" in source
    assert "Сведения о встрече" in source
    assert "{{ delete_action }}" in source
    assert source.index("Экспортировать…") < source.index("Скачать аудио…")
    assert source.index("Скачать аудио…") < source.index("Сведения о встрече")
    assert source.index("Сведения о встрече") < source.index("{{ delete_action }}")
    assert 'data-meeting-context-panel="details"' in source
    assert 'aria-labelledby="meeting-details-title"' in source
    assert "{{ artifacts }}" in source
    assert "{{ delete_confirmation }}" in source
    assert source.index('role="menu"') < source.index('id="meeting-details-dialog"')
    assert source.index('id="meeting-details-dialog"') < source.index("{{ artifacts }}")
    assert "governance" not in source.casefold()
    assert '<h2 id="meeting-context-more-title">Ещё</h2>' not in source


def test_delete_confirmation_is_a_focused_named_dialog_with_retained_observability_copy() -> None:
    source = POLICY_RENDERING.read_text(encoding="utf-8")
    script = CABINET_JS.read_text(encoding="utf-8")

    assert "data-meeting-delete-dialog" in source
    assert 'aria-labelledby="meeting-delete-title"' in source
    assert "data-meeting-delete-dialog-cancel" in source
    assert "data-meeting-delete-dialog-confirm" in source
    assert "Generation Call" in source
    assert "Langfuse" in source
    assert "Temporal History" in source
    assert "удалены не будут" in source
    assert "initMeetingDeleteDialog" in script
    assert 'dialog.addEventListener("cancel"' in script
    assert 'event.key !== "Tab"' in script
    assert "returnFocus.focus" in script


def test_more_menu_hides_unavailable_capability_actions_instead_of_rendering_a_cockpit() -> None:
    source = GOVERNANCE_FRAGMENT.read_text(encoding="utf-8")

    assert "{% if content_export_available %}" in source
    assert "{% if audio_download_available %}" in source
    assert 'role="menu"' in source
    assert "{{ artifacts }}" not in source[source.index('role="menu"') : source.index('id="meeting-details-dialog"')]
    assert "Активность" not in source[source.index('role="menu"') : source.index('id="meeting-details-dialog"')]
    assert "capability matrix" not in source.casefold()


def test_more_menu_preserves_default_link_action_before_closing() -> None:
    script = CABINET_JS.read_text(encoding="utf-8")
    menu_start = script.index('panels.filter((panel) => panel.getAttribute("role") === "menu")')
    handler_start = script.index('panel.addEventListener("click", (event) => {', menu_start)
    handler_end = script.index("      });", handler_start) + len("      });")
    handler = script[handler_start:handler_end]

    assert 'const item = event.target.closest?.(\'[role="menuitem"]\');' in handler
    assert 'if (item.matches("a[href]")) {' in handler
    assert "window.setTimeout(() => closePanel(panel), 0);" in handler
    assert handler.index("window.setTimeout") < handler.rindex("closePanel(panel);")
