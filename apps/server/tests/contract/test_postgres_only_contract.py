from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FORBIDDEN_TOKENS = ("sqli" + "te", "aio" + "sqli" + "te")
ACTIVE_PATHS = (
    ROOT / "apps/server/src",
    ROOT / "apps/server/scripts",
    ROOT / "apps/server/tests",
    ROOT / "apps/server/pyproject.toml",
    ROOT / "apps/server/constraints.txt",
    ROOT / "apps/server/uv.lock",
)


def _active_files() -> list[Path]:
    files: list[Path] = []
    for path in ACTIVE_PATHS:
        if path.is_file():
            files.append(path)
        else:
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and "__pycache__" not in candidate.parts
                and "tests" not in candidate.parts
            )
    return files


def test_active_server_paths_do_not_restore_retired_embedded_database_support() -> None:
    matches = [
        str(path.relative_to(ROOT))
        for path in _active_files()
        if any(token in path.read_text(encoding="utf-8", errors="replace").lower() for token in FORBIDDEN_TOKENS)
    ]

    assert matches == []
