#!/usr/bin/env python3
"""Fail-closed checks for GRAF-specific Spec Kit governance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


STAGES = (
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


def read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: cannot read: {exc}")
        return ""


def validate(root: Path, *, run_doctor: bool = True) -> list[str]:
    errors: list[str] = []
    if run_doctor:
        try:
            result = subprocess.run(
                ["speckit-bootstrap", ".", "--doctor", "--frozen"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                errors.append(f"bootstrap frozen doctor failed: {detail}")
        except OSError as exc:
            errors.append(f"bootstrap frozen doctor failed: {exc}")

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
    agents = " ".join(read(agents_path, errors).split())
    flow = " ".join(read(flow_path, errors).split())
    sequence = " → ".join(STAGES)
    if sequence not in agents:
        errors.append(f"{agents_path}: full GRAF workflow is missing or out of order")
    skill_sequence = " ".join(f"$speckit-{stage}" for stage in STAGES)
    if skill_sequence not in flow:
        errors.append(f"{flow_path}: full GRAF skill sequence is missing or out of order")

    combined = f"{agents}\n{flow}".lower()
    if "reviewer-owned" not in combined or "must not mark" not in combined:
        errors.append(f"{flow_path}: reviewer-owned checklist rule is missing")
    if (
        "upstream six-step" not in combined
        or "must not" not in combined
        or "significant/high-risk" not in combined
    ):
        errors.append(f"{flow_path}: shortened upstream workflow boundary is missing")
    if "validation/release gates" not in combined:
        errors.append(f"{flow_path}: validation/release closeout is missing")

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
) -> None:
    (root / ".specify").mkdir(parents=True)
    (root / ".agents/skills/speckit-specify").mkdir(parents=True)
    (root / "docs/agent-guidance").mkdir(parents=True)
    stages = STAGES if converge else STAGES[:-1]
    sequence = " → ".join(stages) + " → validation/release gates"
    ownership = "reviewer-owned" if reviewer_owned else "reviewed"
    policy = (
        f"{sequence}. Upstream six-step MUST NOT replace significant/high-risk flow. "
        f"Checklist state is {ownership}; implementation must not mark items complete."
    )
    (root / "AGENTS.md").write_text(policy, encoding="utf-8")
    skill_sequence = "\n".join(f"$speckit-{stage}" for stage in stages)
    (root / "docs/agent-guidance/spec-kit-flow.md").write_text(
        f"{skill_sequence}\n{policy}\n", encoding="utf-8"
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
        )
        for index, (name, options) in enumerate(cases, start=1):
            root = base / f"negative-{index}"
            write_fixture(root, **options)
            if not validate(root, run_doctor=False):
                raise AssertionError(f"negative fixture was not rejected: {name}")
    print("spec-kit-governance self-test: OK (positive + 4 negative classes)")


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
