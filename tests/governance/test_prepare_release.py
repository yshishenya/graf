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


def github_release_env(root: Path, published_tag: str) -> dict[str, str]:
    target = subprocess.check_output(
        ["git", "rev-parse", f"{published_tag}^{{commit}}"],
        cwd=root,
        text=True,
    ).strip()
    bin_dir = root / "fake-bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        "if [ \"$1 $2\" = \"release view\" ]; then\n"
        f"  printf '%s\\n' '{{\"tagName\":\"{published_tag}\",\"targetCommitish\":\"{target}\","
        "\"isDraft\":false,\"isPrerelease\":false,\"publishedAt\":\"2026-09-02T05:21:01Z\"}'\n"
        "else\n"
        f"  printf '%s\\n' '[{{\"tagName\":\"{published_tag}\",\"isDraft\":false,"
        "\"isPrerelease\":false,\"publishedAt\":\"2026-09-02T05:21:01Z\"}]'\n"
        "fi\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    return {**release_env(), "PATH": f"{bin_dir}:{os.environ['PATH']}"}


def fragment(feature: int, summary: str) -> str:
    return f'''schema_version: 1
feature_id: {feature}
category: Changed
summary: "{summary}"
issue: {6000 + feature}
tasks: [T001]
compatibility: "нет"
release_notes: "{summary}"
known_limitations: ["нет"]
'''


def configure_github_release_repo(root: Path, published_tag: str) -> None:
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    subprocess.run(["git", "tag", published_tag], cwd=root, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:example/graf.git"], cwd=root, check=True)


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


def test_prepare_release_folds_every_section_after_latest_published_github_release(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.3] - 2026-09-03

### Изменено
- Третья подготовленная запись. (Фича 216, issue #6216)
- Вторая подготовленная запись. (Фича 215, issue #6215)

## [2026.09.02.2] - 2026-09-02

### Изменено
- Вторая подготовленная запись. (Фича 215, issue #6215)

## [2026.09.02.1] - 2026-09-02

### Изменено
- Реально опубликованная запись.
""",
        encoding="utf-8",
    )
    for version, feature_id, summary in (
        ("2026.09.02.2", 215, "Вторая подготовленная запись"),
        ("2026.09.02.3", 216, "Третья подготовленная запись"),
    ):
        directory = root / "changes" / "releases" / f"v{version}"
        directory.mkdir(parents=True)
        (directory / f"F{feature_id}.yaml").write_text(fragment(feature_id, summary), encoding="utf-8")
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1"),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [2026.09.04.1]" in changelog
    assert "Вторая подготовленная запись" in changelog
    assert "Третья подготовленная запись" in changelog
    assert "Процесс собирает release metadata" in changelog
    assert "## [2026.09.02.2]" not in changelog
    assert "## [2026.09.02.3]" not in changelog
    assert "## [2026.09.02.1]" in changelog
    archive = root / "changes" / "releases" / "v2026.09.04.1"
    assert {path.name for path in archive.glob("F*.yaml")} == {"F215.yaml", "F216.yaml", "F217.yaml"}


def test_prepare_release_rejects_duplicate_feature_across_unpublished_and_current_fragments(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.2] - 2026-09-02

### Изменено
- Старая подготовленная запись. (Фича 217, issue #6217)

## [2026.09.02.1] - 2026-09-02

### Изменено
- Реально опубликованная запись.
""",
        encoding="utf-8",
    )
    pending = root / "changes" / "releases" / "v2026.09.02.2"
    pending.mkdir(parents=True)
    (pending / "F217.yaml").write_text(fragment(217, "Старая подготовленная запись"), encoding="utf-8")
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1"),
    )

    assert result.returncode != 0
    assert "duplicate pending feature_id 217" in result.stdout + result.stderr
    assert "## [2026.09.04.1]" not in (root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_prepare_release_rejects_conflicting_unpublished_text_for_one_feature(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.3] - 2026-09-03

### Изменено
- Новая формулировка. (Фича 215, issue #6215)

## [2026.09.02.2] - 2026-09-02

### Изменено
- Старая формулировка. (Фича 215, issue #6215)

## [2026.09.02.1] - 2026-09-02

### Изменено
- Реально опубликованная запись.
""",
        encoding="utf-8",
    )
    pending = root / "changes" / "releases" / "v2026.09.02.2"
    pending.mkdir(parents=True)
    (pending / "F215.yaml").write_text(fragment(215, "Старая формулировка"), encoding="utf-8")
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1"),
    )

    assert result.returncode != 0
    assert "conflicting unpublished changelog entries for Feature 215" in result.stdout + result.stderr


def test_prepare_release_rejects_orphan_unpublished_fragment_directory(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.1] - 2026-09-02

### Изменено
- Реально опубликованная запись.
""",
        encoding="utf-8",
    )
    orphan = root / "changes" / "releases" / "v2026.09.03.1"
    orphan.mkdir(parents=True)
    (orphan / "F218.yaml").write_text(fragment(218, "Потерянная запись"), encoding="utf-8")
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1"),
    )

    assert result.returncode != 0
    assert "orphan unpublished fragment directory" in result.stdout + result.stderr
