"""F268 copy-convention guard: no «ё» in user copy, единый словарь терминов.

Каждый шаблон кабинета и публичного сайта проверяется на букву «ё» в видимом
тексте. Из проверки исключены только комментарии ``<!-- ... -->`` и
``{# ... #}``: они не показываются пользователю. Других исключений нет;
macOS-исключение «Mute микрофона» находится вне серверной области.

Python-модули презентации кабинета сканируются по строковым литералам
(без docstring): запрещены «Транскрипт», «YooKassa», «не доступны» и буква «ё».
"""

import ast
import re
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[2]
SRC = SERVER_ROOT / "src" / "twobrain_rec_server"
TEMPLATE_ROOTS = (
    SRC / "cabinet" / "templates",
    SRC / "public" / "templates",
)
CABINET_COPY_MODULES = (
    "cabinet/rendering.py",
    "cabinet/view_models.py",
    "cabinet/deletion_rendering.py",
    "cabinet/meeting_protocol.py",
    "cabinet/rendering_shared.py",
)
COMMENT_PATTERN = re.compile(r"<!--.*?-->|\{#.*?#\}", re.DOTALL)
FORBIDDEN_TERMS = ("Транскрипт", "YooKassa", "не доступны")
YO = "ё"


def _template_files() -> tuple[Path, ...]:
    return tuple(sorted(path for root in TEMPLATE_ROOTS for path in root.rglob("*.html")))


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _user_strings(relative_path: str) -> list[str]:
    tree = ast.parse((SRC / relative_path).read_text(encoding="utf-8"))
    docstrings = _docstring_ids(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


@pytest.mark.parametrize("path", _template_files(), ids=lambda path: str(path.relative_to(SRC)))
def test_templates_have_no_forbidden_copy(path: Path) -> None:
    visible = COMMENT_PATTERN.sub("", path.read_text(encoding="utf-8"))
    assert YO not in visible, f"user copy must use «е», not «ё»: {path}"
    for term in FORBIDDEN_TERMS:
        assert term not in visible, f"forbidden copy «{term}» in {path}"


@pytest.mark.parametrize("relative_path", CABINET_COPY_MODULES)
def test_cabinet_python_copy_has_no_forbidden_variants(relative_path: str) -> None:
    for literal in _user_strings(relative_path):
        for term in FORBIDDEN_TERMS:
            assert term not in literal, f"forbidden copy «{term}» in {relative_path}: {literal!r}"
        assert YO not in literal, f"user copy must use «е», not «ё»: {relative_path}: {literal!r}"
