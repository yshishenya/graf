from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_release  # noqa: E402
import issue_canon_common as common  # noqa: E402
import normalize_issue_canon as normalize  # noqa: E402


def canonical_body(task: str = "T001") -> str:
    sections = []
    for section in common.REQUIRED_SECTIONS:
        content = f"- Spec tasks: {task}" if section == "## Контекст" else "Содержимое"
        sections.append(f"{section}\n\n{content}")
    return "\n\n".join(sections) + "\n"


def canonical_issue(**overrides: object) -> dict:
    issue = {
        "number": 7,
        "title": "[012][P1][tests] T001: Добавить проверку",
        "body": canonical_body(),
        "labels": [
            {"name": "feature:012"},
            {"name": "priority:P1"},
            {"name": "area:tests"},
            {"name": "type:test-gap"},
        ],
        "state": "OPEN",
    }
    issue.update(overrides)
    return issue


class RepoSlugTests(unittest.TestCase):
    def assert_slug(self, remote: str, expected: str) -> None:
        result = subprocess.CompletedProcess([], 0, stdout=remote + "\n", stderr="")
        with patch.object(common, "run", return_value=result):
            self.assertEqual(common.repo_slug(Path("/tmp/repo")), expected)

    def test_parses_supported_github_remotes(self) -> None:
        for remote in (
            "git@github.com:yshishenya/example.git",
            "https://github.com/yshishenya/example.git",
            "ssh://git@github.com/yshishenya/example.git",
        ):
            with self.subTest(remote=remote):
                self.assert_slug(remote, "yshishenya/example")

    def test_rejects_non_github_remote(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout="https://example.com/a/b.git\n", stderr="")
        with patch.object(common, "run", return_value=result), self.assertRaises(SystemExit):
            common.repo_slug(Path("/tmp/repo"))


class ValidationTests(unittest.TestCase):
    def test_canonical_issue_is_valid(self) -> None:
        self.assertEqual(common.validate_issue(canonical_issue()), [])

    def test_title_must_match_the_entire_string(self) -> None:
        issue = canonical_issue(title="[012][P1][tests] T001: Добавить проверку ")
        self.assertIn("title does not match", common.validate_issue(issue)[0])

    def test_conflicting_structural_labels_are_rejected(self) -> None:
        issue = canonical_issue(
            labels=canonical_issue()["labels"]
            + [{"name": "feature:011"}, {"name": "priority:P2"}]
        )
        errors = common.validate_issue(issue)
        self.assertIn("conflicting feature labels: feature:011", errors)
        self.assertIn("conflicting priority labels: priority:P2", errors)

    def test_missing_sections_and_labels_are_reported(self) -> None:
        issue = canonical_issue(body="T001", labels=[])
        errors = common.validate_issue(issue)
        self.assertIn("missing label feature:012", errors)
        self.assertIn("missing label priority:P1", errors)
        self.assertIn("missing type:* label", errors)
        self.assertTrue(any(error.startswith("missing body section") for error in errors))


class NormalizationTests(unittest.TestCase):
    def test_canonical_title_is_idempotent(self) -> None:
        issue = canonical_issue()
        self.assertEqual(normalize.canonical_title(issue, "999"), issue["title"])

    def test_legacy_title_receives_task_id(self) -> None:
        issue = canonical_issue(
            title="[012][P1][tests] Добавить проверку",
            body="Spec tasks: T044",
        )
        self.assertEqual(
            normalize.canonical_title(issue, None),
            "[012][P1][tests] T044: Добавить проверку",
        )

    def test_generated_body_preserves_original_context(self) -> None:
        issue = canonical_issue(body="Исходное описание")
        body = normalize.canonical_body(issue, issue["title"])
        self.assertIn("Исходное описание", body)
        self.assertIn("- Spec tasks: T001", body)
        for section in common.REQUIRED_SECTIONS:
            self.assertIn(section, body)

    def test_noop_normalization_does_not_call_github(self) -> None:
        with (
            patch.object(normalize, "repo_root", return_value=ROOT),
            patch.object(normalize, "repo_slug", return_value="owner/repo"),
            patch.object(normalize, "current_feature", return_value="012"),
            patch.object(normalize, "list_open_issues", return_value=[canonical_issue()]),
            patch.object(normalize, "run") as run,
            patch.object(sys, "argv", ["normalize_issue_canon.py"]),
        ):
            self.assertEqual(normalize.main(), 0)
        run.assert_not_called()

    def test_normalization_removes_conflicting_labels(self) -> None:
        issue = canonical_issue(
            labels=canonical_issue()["labels"]
            + [{"name": "feature:099"}, {"name": "priority:P3"}]
        )
        with (
            patch.object(normalize, "repo_root", return_value=ROOT),
            patch.object(normalize, "repo_slug", return_value="owner/repo"),
            patch.object(normalize, "current_feature", return_value="012"),
            patch.object(normalize, "list_open_issues", return_value=[issue]),
            patch.object(normalize, "run") as run,
            patch.object(sys, "argv", ["normalize_issue_canon.py"]),
        ):
            self.assertEqual(normalize.main(), 0)
        args = run.call_args.args[0]
        self.assertEqual(args[:6], ["gh", "issue", "edit", "7", "--repo", "owner/repo"])
        remove_index = args.index("--remove-label")
        self.assertEqual(args[remove_index + 1], "feature:099,priority:P3")

    def test_normalization_does_not_remove_labels_without_a_valid_title(self) -> None:
        issue = canonical_issue()
        with (
            patch.object(normalize, "repo_root", return_value=ROOT),
            patch.object(normalize, "repo_slug", return_value="owner/repo"),
            patch.object(normalize, "current_feature", return_value="012"),
            patch.object(normalize, "list_open_issues", return_value=[issue]),
            patch.object(normalize, "canonical_title", return_value="invalid\ntitle"),
            patch.object(normalize, "run") as run,
            patch.object(sys, "argv", ["normalize_issue_canon.py"]),
        ):
            self.assertEqual(normalize.main(), 0)
        args = run.call_args.args[0]
        self.assertNotIn("--remove-label", args)


class LabelTests(unittest.TestCase):
    def test_existing_matching_label_is_a_noop(self) -> None:
        existing = {"priority:P1": ("d93f0b", "High")}
        with patch.object(common, "run_with_retry") as run:
            common.ensure_label("owner/repo", "priority:P1", "d93f0b", "High", existing)
        run.assert_not_called()

    def test_missing_label_is_created_and_cached(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        existing: dict[str, tuple[str, str]] = {}
        with patch.object(common, "run_with_retry", return_value=result) as run:
            common.ensure_label("owner/repo", "priority:P1", "d93f0b", "High", existing)
        self.assertEqual(existing["priority:P1"], ("d93f0b", "High"))
        self.assertIn("create", run.call_args.args[0])


class ReleaseBuildTests(unittest.TestCase):
    def test_release_archive_is_deterministic_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            result_a = build_release.build(Path(first))
            result_b = build_release.build(Path(second))
            archive = Path(result_a["archive"])
            self.assertEqual(result_a["sha256"], result_b["sha256"])
            self.assertEqual(result_a["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            with ZipFile(archive) as package:
                names = set(package.namelist())
            self.assertIn("github-issue-canon/extension.yml", names)
            self.assertIn("github-issue-canon/scripts/validate_issue_canon.py", names)
            self.assertFalse(any("__pycache__" in name for name in names))

    def test_checksum_file_matches_archive(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            result = build_release.build(Path(output))
            checksum = Path(result["checksum"]).read_text(encoding="utf-8")
        self.assertEqual(
            checksum,
            f"{result['sha256']}  github-issue-canon-{result['version']}.zip\n",
        )

    def test_publish_job_uses_verified_notes_without_checkout(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        package, publish = workflow.split("\n  publish:\n", 1)
        self.assertIn("git for-each-ref", package)
        self.assertIn("%(contents:subject)%0a%0a%(contents:body)", package)
        self.assertNotIn("--format='%(contents)'", package)
        self.assertIn("dist/release-notes.md", package)
        self.assertIn("--notes-file dist/release-notes.md", publish)
        self.assertNotIn("actions/checkout@", publish)
        self.assertNotIn("--notes-from-tag", publish)


class RuntimeArtifactTests(unittest.TestCase):
    def test_command_imports_do_not_write_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / "scripts"
            scripts.mkdir()
            for source in (ROOT / "scripts").glob("*.py"):
                shutil.copy2(source, scripts / source.name)
            for module in (
                "ensure_issue_canon",
                "normalize_issue_canon",
                "validate_issue_canon",
            ):
                subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        f"import runpy; runpy.run_path('{module}.py')",
                    ],
                    cwd=scripts,
                    check=True,
                )
            self.assertFalse(
                any(path.suffix in {".pyc", ".pyo"} for path in scripts.rglob("*"))
            )


if __name__ == "__main__":
    unittest.main()
