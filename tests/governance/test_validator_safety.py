from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_harness_validators():
    path = ROOT / "harness" / "src" / "dev_harness" / "validators.py"
    spec = importlib.util.spec_from_file_location("harness_validators", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_validator_rejects_invalid_expiry_without_traceback(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
owner: platform
expiry: 2099-02-30
removal trigger: migration complete
retirement task: T217
risk: bounded compatibility risk
validation: focused migration test
reason: required for existing clients
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("invalid ISO expiry date" in error for error in errors)


def test_legacy_validator_requires_exact_classification_and_exception_labels(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
ownerish: platform
expiry: 2099-12-31
removal trigger: migration complete
retirement task: T217
risk: bounded compatibility risk
validation: focused migration test
reason: required for existing clients

## Other section
Classification: `untouched`
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("needs owner" in error for error in errors)
    assert not any("exactly one Classification" in error for error in errors)


def test_legacy_exception_requires_risk_validation_and_reason(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
owner: platform
expiry: 2099-12-31
removal trigger: migration complete
retirement task: T217
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("needs risk" in error for error in errors)
    assert any("needs validation" in error for error in errors)
    assert any("needs reason" in error for error in errors)


def test_agent_context_requires_object_branch_and_full_source_sha(tmp_path: Path) -> None:
    validator = load_script("validate-agent-context")
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text("[]\n", encoding="utf-8")
    assert any("object" in error for error in validator.validate(tmp_path))

    pointer.write_text(
        json.dumps(
            {
                "feature_directory": "specs/001-example",
                "feature_id": "001",
                "owner": "test",
                "risk_lane": "low",
                "owned_paths": ["specs/001-example"],
                "branch": "test/001-example",
                "source_sha": "abc1234",
            }
        ),
        encoding="utf-8",
    )
    assert any("full 40-character" in error for error in validator.validate(tmp_path))


def test_changelog_required_fields_must_be_top_level(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    directory = tmp_path / "changes" / "unreleased"
    directory.mkdir(parents=True)
    (directory / "F217.yaml").write_text(
        """metadata:
  feature_id: 217
  schema_version: 1
  category: Changed
  summary: "Русское описание"
  issue: 1
  tasks: [T001]
  compatibility: "нет"
  release_notes: "Русские заметки"
""",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("missing schema_version" in error for error in errors)
    assert any("feature_id" in error for error in errors)


def test_changelog_empty_required_field_is_rejected(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    directory = tmp_path / "changes" / "unreleased"
    directory.mkdir(parents=True)
    (directory / "F217.yaml").write_text(
        """schema_version: 1
feature_id:
category: Changed
summary: "Русское описание"
issue: 1
tasks: [T001]
compatibility: "нет"
release_notes: "Русские заметки"
""",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("missing feature_id" in error for error in errors)


def test_package_safety_allows_documentation_examples_but_rejects_credentials(tmp_path: Path) -> None:
    validator = load_harness_validators()
    (tmp_path / "README.md").write_text("Use `secret:` and `password =` as field names.\n", encoding="utf-8")
    assert validator.package_safety(tmp_path) == []

    (tmp_path / "config.py").write_text('password = "not-a-real-but-long-value"\n', encoding="utf-8")
    errors = validator.package_safety(tmp_path)
    assert any("forbidden secret/private content" in error for error in errors)
