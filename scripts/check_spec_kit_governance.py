#!/usr/bin/env python3
"""Fail-closed checks for GRAF-specific Spec Kit governance."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


if sys.version_info < (3, 9):
    raise SystemExit("spec-kit-governance: Python 3.9 or newer is required")


SKILL_STAGES = (
    "specify",
    "clarify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "taskstoissues",
    "implement",
    "converge",
)
CLOSEOUT_STAGE = "validation/release gates"


def read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: cannot read: {exc}")
        return ""


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)", text
    )
    return match.group(1) if match else ""


def validate(root: Path, *, run_doctor: bool = True) -> list[str]:
    errors: list[str] = []
    if run_doctor:
        try:
            result = subprocess.run(
                ["speckit-bootstrap", ".", "--doctor", "--frozen"],
                cwd=root,
                text=True,
                capture_output=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )
            if result.returncode:
                detail = "\n".join(
                    output.strip()
                    for output in (result.stdout, result.stderr)
                    if output.strip()
                )
                errors.append(
                    f"{root / '.specify/speckit-bootstrap.lock.json'}: "
                    f"bootstrap frozen doctor failed: {detail}"
                )
        except OSError as exc:
            errors.append(
                f"{root / '.specify/speckit-bootstrap.lock.json'}: "
                f"bootstrap frozen doctor failed: {exc}"
            )

    lock_path = root / ".specify/speckit-bootstrap.lock.json"
    try:
        lock = json.loads(read(lock_path, errors))
    except json.JSONDecodeError as exc:
        errors.append(f"{lock_path}: invalid JSON: {exc}")
        lock = {}

    if lock.get("schema_version") != 3:
        errors.append(f"{lock_path}: schema_version must be 3")
    skills = lock.get("project_skills")
    if not isinstance(skills, dict) or not skills:
        errors.append(f"{lock_path}: project_skills must be a non-empty object")
    else:
        for name in skills:
            path = root / ".agents/skills" / name / "SKILL.md"
            if not path.is_file():
                errors.append(f"{path}: locked project-local skill is missing")

    agents_path = root / "AGENTS.md"
    flow_path = root / "docs/agent-guidance/spec-kit-flow.md"
    agents = read(agents_path, errors)
    flow = read(flow_path, errors)
    sequence = " → ".join((*SKILL_STAGES, CLOSEOUT_STAGE))
    agents_sequence = re.search(
        r"The canonical significant/high-risk GRAF path is\s+`([^`]+)`", agents
    )
    if not agents_sequence or " ".join(agents_sequence.group(1).split()) != sequence:
        errors.append(f"{agents_path}: full GRAF workflow is missing or out of order")
    command_section = markdown_section(flow, "## Command Sequence")
    command_block = re.search(r"(?ms)```text\s*$\n(.*?)^```", command_section)
    expected_commands = (
        "$speckit-constitution",
        *[f"$speckit-{stage}" for stage in SKILL_STAGES],
        CLOSEOUT_STAGE,
    )
    actual_commands = tuple(
        line.strip()
        for line in (command_block.group(1).splitlines() if command_block else ())
        if line.strip()
    )
    if actual_commands != expected_commands:
        errors.append(f"{flow_path}: full GRAF skill sequence is missing or out of order")

    checklist_rule = re.compile(
        r"custom checklist(?: checkbox)? state is reviewer-owned\b.{0,500}?"
        r"\bimplementation\b.{0,200}?\bmust not mark\b",
        re.IGNORECASE | re.DOTALL,
    )
    if not checklist_rule.search(agents) or not checklist_rule.search(
        markdown_section(flow, "## 4. Checklist")
    ):
        errors.append(f"{flow_path}: reviewer-owned checklist rule is missing")
    combined = f"{agents}\n{flow}".lower()
    if (
        "upstream six-step" not in combined
        or "must not" not in combined
        or "significant/high-risk" not in combined
    ):
        errors.append(f"{flow_path}: shortened upstream workflow boundary is missing")
    ignore_path = root / ".specify/.gitignore"
    ignored = {
        line.strip()
        for line in read(ignore_path, errors).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for entry in ("feature.json", "extensions/*/local-config.yml"):
        if entry not in ignored:
            errors.append(f"{ignore_path}: missing managed entry {entry!r}")
    return errors


def write_fixture(
    root: Path,
    *,
    converge: bool = True,
    reviewer_owned: bool = True,
    schema: int = 3,
    project_skills: bool = True,
    wrong_order: bool = False,
    decoy_workflow: bool = False,
) -> None:
    (root / ".specify").mkdir(parents=True)
    (root / ".agents/skills/speckit-specify").mkdir(parents=True)
    (root / "docs/agent-guidance").mkdir(parents=True)
    stages = list(SKILL_STAGES if converge else SKILL_STAGES[:-1])
    if wrong_order:
        stages[4], stages[5] = stages[5], stages[4]
    sequence = " → ".join((*stages, CLOSEOUT_STAGE))
    valid_sequence = " → ".join((*SKILL_STAGES, CLOSEOUT_STAGE))
    ownership = "reviewer-owned" if reviewer_owned else "reviewed"
    policy = (
        f"The canonical significant/high-risk GRAF path is `{sequence}`. "
        "Upstream six-step MUST NOT replace significant/high-risk flow. "
        f"Custom checklist state is {ownership}; implementation must not mark items complete."
    )
    decoy = f"\n\nHistory example: {valid_sequence}." if decoy_workflow else ""
    (root / "AGENTS.md").write_text(policy + decoy, encoding="utf-8")
    skill_sequence = "\n".join(
        ("$speckit-constitution", *[f"$speckit-{stage}" for stage in stages], CLOSEOUT_STAGE)
    )
    valid_skill_sequence = "\n".join(
        (
            "$speckit-constitution",
            *[f"$speckit-{stage}" for stage in SKILL_STAGES],
            CLOSEOUT_STAGE,
        )
    )
    decoy = (
        f"\n## History\n\n```text\n{valid_skill_sequence}\n```\n"
        if decoy_workflow
        else ""
    )
    (root / "docs/agent-guidance/spec-kit-flow.md").write_text(
        "## Command Sequence\n\n"
        f"```text\n{skill_sequence}\n```\n\n"
        "## 4. Checklist\n\n"
        f"Custom checklist checkbox state is {ownership}; implementation "
        "must not mark items complete.\n\n"
        "## Boundary\n\n"
        "Upstream six-step MUST NOT replace significant/high-risk flow.\n"
        f"{decoy}",
        encoding="utf-8",
    )
    (root / ".specify/speckit-bootstrap.lock.json").write_text(
        json.dumps(
            {
                "schema_version": schema,
                "project_skills": {"speckit-specify": "fixture"} if project_skills else {},
            }
        ),
        encoding="utf-8",
    )
    (root / ".agents/skills/speckit-specify/SKILL.md").write_text(
        "fixture\n", encoding="utf-8"
    )
    (root / ".specify/.gitignore").write_text(
        "feature.json\nextensions/*/local-config.yml\n", encoding="utf-8"
    )


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="graf-speckit-governance-") as directory:
        base = Path(directory)
        positive = base / "positive"
        write_fixture(positive)
        if errors := validate(positive, run_doctor=False):
            raise AssertionError(f"positive fixture failed: {errors}")

        cases = (
            ("missing convergence", {"converge": False}),
            ("missing reviewer ownership", {"reviewer_owned": False}),
            ("missing project skills", {"project_skills": False}),
            ("unsupported lock schema", {"schema": 2}),
            ("wrong workflow order", {"wrong_order": True}),
            (
                "decoy workflow outside canonical sections",
                {"converge": False, "decoy_workflow": True},
            ),
        )
        for index, (name, options) in enumerate(cases, start=1):
            root = base / f"negative-{index}"
            write_fixture(root, **options)
            if not validate(root, run_doctor=False):
                raise AssertionError(f"negative fixture was not rejected: {name}")
    print("spec-kit-governance self-test: OK (positive + 6 negative classes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    root = Path(__file__).resolve().parent.parent
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"spec-kit-governance: ERROR: {error}", file=sys.stderr)
        return 1
    print("spec-kit-governance: OK (bootstrap integrity + GRAF invariants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
