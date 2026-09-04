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


def github_release_env(
    root: Path,
    published_tag: str,
    *,
    target_commitish: str | None = None,
    remote_target: str | None = None,
) -> dict[str, str]:
    target = subprocess.check_output(
        ["git", "rev-parse", f"{published_tag}^{{commit}}"],
        cwd=root,
        text=True,
    ).strip()
    release_target = target_commitish or target
    remote_target = remote_target or target
    bin_dir = root / "fake-bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"api\" ]; then\n"
        f"  printf '%s\\n' '{{\"ref\":\"refs/tags/{published_tag}\",\"object\":{{\"sha\":\"{remote_target}\",\"type\":\"commit\"}}}}'\n"
        "elif [ \"$1 $2\" = \"release view\" ]; then\n"
        f"  printf '%s\\n' '{{\"tagName\":\"{published_tag}\",\"targetCommitish\":\"{release_target}\","
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
    assert "<!-- Release features:" in changelog
    assert all(f"F{feature}" in changelog for feature in (215, 216, 217))
    archive = root / "changes" / "releases" / "v2026.09.04.1"
    assert {path.name for path in archive.glob("F*.yaml")} == {"F215.yaml", "F216.yaml", "F217.yaml"}


def test_prepare_release_can_rerun_same_unpublished_version(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    configure_github_release_repo(root, "v2026.09.02.1")
    changelog_path = root / "CHANGELOG.md"
    changelog_path.write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.04.1] - 2026-09-04

<!-- Release features: F217 -->

### Исправлено
- Короткая продуктовая запись.

## [2026.09.02.1] - 2026-09-02

### Изменено
- Уже опубликованная запись.
        """,
        encoding="utf-8",
    )
    archive = root / "changes" / "releases" / "v2026.09.04.1"
    archive.mkdir(parents=True)
    shutil.move(root / "changes" / "unreleased" / "F217.yaml", archive / "F217.yaml")
    env = github_release_env(root, "v2026.09.02.1")
    before = changelog_path.read_text(encoding="utf-8")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert changelog_path.read_text(encoding="utf-8") == before
    assert (archive / "F217.yaml").is_file()
    assert "Prepared release section in CHANGELOG.md for v2026.09.04.1" in result.stdout

    (root / "changes" / "unreleased" / "F218.yaml").write_text(
        fragment(218, "Новая запись"),
        encoding="utf-8",
    )
    with_new_fragment = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert with_new_fragment.returncode == 0, with_new_fragment.stdout + with_new_fragment.stderr
    updated = changelog_path.read_text(encoding="utf-8")
    assert updated.count("Короткая продуктовая запись.") == 1
    assert "Процесс собирает release metadata" not in updated
    assert "Новая запись (Фича 218" in updated
    assert (archive / "F218.yaml").is_file()


def test_prepare_release_rejects_archive_destination_collision_before_mutation(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    configure_github_release_repo(root, "v2026.09.02.1")
    changelog_path = root / "CHANGELOG.md"
    changelog_path.write_text(
        """# История изменений

## [Unreleased]

### Изменено
- Новая запись.

## [2026.09.04.1] - 2026-09-04

### Изменено
- Архивная запись.

## [2026.09.02.1] - 2026-09-02

### Изменено
- Уже опубликованная запись.
""",
        encoding="utf-8",
    )
    archive = root / "changes" / "releases" / "v2026.09.04.1"
    archive.mkdir(parents=True)
    archived_fragment = archive / "F217.yaml"
    archived_fragment.write_text(fragment(999, "Архивная запись"), encoding="utf-8")
    current_fragment = root / "changes" / "unreleased" / "F217.yaml"
    before = {
        changelog_path: changelog_path.read_bytes(),
        archived_fragment: archived_fragment.read_bytes(),
        current_fragment: current_fragment.read_bytes(),
    }

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1"),
    )

    assert result.returncode != 0
    assert "multiple fragments map to archive destination F217.yaml" in result.stdout + result.stderr
    assert all(path.read_bytes() == content for path, content in before.items())


def test_prepare_release_uses_github_tag_commit_when_release_target_is_branch(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    changelog_path = root / "CHANGELOG.md"
    changelog_path.write_text(
        changelog_path.read_text(encoding="utf-8").replace(
            "## [Unreleased]",
            "## [2026.09.02.1] - 2026-09-02\n\n### Изменено\n- Уже опубликованная запись.\n\n## [Unreleased]",
            1,
        ),
        encoding="utf-8",
    )
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1", target_commitish="master"),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "## [2026.09.04.1]" in (root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_prepare_release_rejects_github_tag_that_does_not_match_local_tag(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    configure_github_release_repo(root, "v2026.09.02.1")

    result = subprocess.run(
        ["bash", "scripts/prepare-release.sh", "2026.09.04.1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=github_release_env(root, "v2026.09.02.1", remote_target="b" * 40),
    )

    assert result.returncode != 0
    assert "does not match its published GitHub Release target" in result.stdout + result.stderr
    assert "## [2026.09.04.1]" not in (root / "CHANGELOG.md").read_text(encoding="utf-8")


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
    assert "multiple fragments map to archive destination F217.yaml" in result.stdout + result.stderr
    assert "## [2026.09.04.1]" not in (root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_prepare_release_uses_archived_fragment_for_concise_unmarked_entries(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.3] - 2026-09-03

### Изменено
- Старая формулировка.

### Важно
- Требуется ручное обновление.

## [2026.09.02.2] - 2026-09-02

### Изменено
- Старая формулировка.

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

    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- Старая формулировка." in changelog
    assert changelog.count("- Старая формулировка.") == 1
    assert "### Важно\n- Требуется ручное обновление." in changelog
    assert "Фича 215" not in changelog


def test_prepare_release_restores_archived_fragment_missing_from_pending_changelog(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "CHANGELOG.md").write_text(
        """# История изменений

## [Unreleased]

### Изменено
- _Пока нет записей._

## [2026.09.02.2] - 2026-09-02

<!-- Release features: F215 F2150 -->

### Изменено
- Восстановленная запись (Фича 2150, issue #8150)

## [2026.09.02.1] - 2026-09-02

### Изменено
- Реально опубликованная запись.
""",
        encoding="utf-8",
    )
    pending = root / "changes" / "releases" / "v2026.09.02.2"
    pending.mkdir(parents=True)
    (pending / "F215.yaml").write_text(fragment(215, "Восстановленная запись"), encoding="utf-8")
    (pending / "F2150.yaml").write_text(fragment(2150, "Восстановленная запись"), encoding="utf-8")
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
    assert "- Восстановленная запись (Фича 2150, issue #8150)" in changelog
    assert "- Восстановленная запись (Фича 215, issue #6215" in changelog


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
