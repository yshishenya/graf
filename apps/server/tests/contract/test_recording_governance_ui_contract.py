from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_FRAGMENT = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html"
)
POLICY_RENDERING = SERVER_ROOT / "src/twobrain_rec_server/cabinet/review_policy_rendering.py"
CABINET_JS = SERVER_ROOT / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"


def test_more_menu_keeps_export_audio_download_and_delete_contextual() -> None:
    source = GOVERNANCE_FRAGMENT.read_text(encoding="utf-8")

    assert 'data-meeting-context-panel="more"' in source
    assert "Экспортировать…" in source
    assert "{{ artifacts }}" in source
    assert "{{ delete_confirmation }}" in source
    assert "governance" not in source.casefold()
    assert "disabled" not in source


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
    assert "capability matrix" not in source.casefold()
