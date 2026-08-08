import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CABINET_ROOT = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet"
RENDERING_SHARED = CABINET_ROOT / "rendering_shared.py"
VISIBLE_TEMPLATES = (
    CABINET_ROOT / "templates/cabinet/pages/meeting_detail_content.html",
    CABINET_ROOT / "templates/cabinet/fragments/meeting_governance.html",
    CABINET_ROOT / "templates/cabinet/fragments/meeting_share.html",
)
CAPTURE_CONTROL = (
    REPO_ROOT / "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift"
)


def _ui_text_values() -> list[str]:
    tree = ast.parse(RENDERING_SHARED.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "UI_TEXT"
    )
    values = ast.literal_eval(assignment.value)
    return list(values.values())


def _visible_template_text(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", source)).strip()


def test_visible_workflow_copy_is_russian_product_copy_without_competitor_expression() -> None:
    visible = " ".join(_visible_template_text(path) for path in VISIBLE_TEMPLATES)
    visible += " " + " ".join(_ui_text_values())
    folded = visible.casefold()

    for expected in ("Итоги", "Расшифровка", "Поделиться", "Пригласить", "Удалить"):
        assert expected in visible
    for forbidden in ("krisp", "summarize", "meeting minutes", "project sync"):
        assert forbidden not in folded


def test_visible_copy_does_not_expose_debug_or_local_implementation_terms() -> None:
    visible = " ".join(_visible_template_text(path) for path in VISIBLE_TEMPLATES)
    visible += " " + " ".join(_ui_text_values())
    folded = visible.casefold()

    for forbidden in (
        "stack trace",
        "traceback",
        "localhost",
        "/users/",
        "payload",
        "worker queue",
        "endpoint",
    ):
        assert forbidden not in folded


def test_ui_transcript_and_summary_language_labels_stay_distinct() -> None:
    values = _ui_text_values()
    labels = {value for value in values if value.startswith("Язык ")}

    assert labels == {"Язык интерфейса", "Язык расшифровки", "Язык итогов"}
    assert "output_language" not in RENDERING_SHARED.read_text(encoding="utf-8")
    assert "Locale.current" not in CAPTURE_CONTROL.read_text(encoding="utf-8")


def test_capture_control_copy_is_russian_clean_room_and_keeps_escape_for_dismissal() -> None:
    source = CAPTURE_CONTROL.read_text(encoding="utf-8")
    folded = source.casefold()

    for expected in ("Источник записи недоступен", "Остановите запись", "Настроить доступы"):
        assert expected in source
    for forbidden in ("krisp", "summarize", "meeting minutes", "webview"):
        assert forbidden not in folded
    assert '.keyboardShortcut(.escape, modifiers: [])' not in source
