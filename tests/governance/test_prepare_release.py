from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def fixture(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "prepare-release.sh", tmp_path / "scripts" / "prepare-release.sh")
    shutil.copy2(
        ROOT / "scripts" / "validate-changelog-fragments.py",
        tmp_path / "scripts" / "validate-changelog-fragments.py",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Добавлено
- _Пока нет записей._

### Изменено
- Уже существующая запись.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [Unreleased Template]

Шаблон сохраняется.
""",
        encoding="utf-8",
    )
    fragment_dir = tmp_path / "changes" / "unreleased"
    fragment_dir.mkdir(parents=True)
    (fragment_dir / "F217.yaml").write_text(
        """schema_version: 1
feature_id: 217
category: Changed
summary: "Процесс собирает release metadata"
issue: 6170
tasks: [T001, T002]
compatibility: "нет"
release_notes: |
  Первая release note.
  Вторая release note.
known_limitations:
  - "Первое ограничение."
  - "Второе ограничение."
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def release_env() -> dict[str, str]:
    return {**os.environ, "GRAF_RELEASE_OPERATOR": "test-release-operator"}


def test_prepare_release_preserves_multiline_release_metadata(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2099.01.01.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=release_env(),
    )

    assert result.returncode == 0, result.stderr
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "release notes: Первая release note. Вторая release note." in changelog
    assert "ограничения: Первое ограничение.; Второе ограничение." in changelog
    assert "- Уже существующая запись." in changelog
    assert "Первая release note.\n  Вторая" not in changelog
    assert (root / "changes" / "releases" / "v2099.01.01.1" / "F217.yaml").is_file()


def test_prepare_release_rejects_only_placeholder_unreleased_content(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "changes" / "unreleased" / "F217.yaml").unlink()
    changelog_path = root / "CHANGELOG.md"
    changelog_path.write_text(
        changelog_path.read_text(encoding="utf-8").replace("- Уже существующая запись.", "- _Пока нет записей._"),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2099.01.01.2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=release_env(),
    )

    assert result.returncode != 0
    assert "no concrete entries" in result.stdout + result.stderr


def test_prepare_release_requires_explicit_release_operator(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    env = {key: value for key, value in os.environ.items() if key != "GRAF_RELEASE_OPERATOR"}
    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2099.01.01.3"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0
    assert "GRAF_RELEASE_OPERATOR" in result.stdout + result.stderr


def test_prepare_release_rejects_frozen_candidate_for_current_head(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    candidate = root / ".dev" / "release" / "candidates" / "rc-current.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(
        f'{{"status": "frozen", "source_sha": "{sha}"}}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2099.01.01.4"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=release_env(),
    )

    assert result.returncode != 0
    assert "frozen release candidate" in result.stdout + result.stderr
