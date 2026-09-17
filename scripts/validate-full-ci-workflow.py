#!/usr/bin/env python3
"""Fail-closed contract check for the release-only GitHub Full CI workflow."""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


FORBIDDEN = (
    "cd-remote.sh",
    "gh release",
    "git push",
    "git reset --hard",
    "ci-local.sh --full",
    "continue-on-error: true",
)

SERVER_JOBS = ("server-static", "server-phases", "server-parallel")
SHARD_COUNT = 4
RESULT_FILES = (
    "server-static-result.json",
    "server-phases-result.json",
    "server-shard-0-result.json",
    "server-shard-1-result.json",
    "server-shard-2-result.json",
    "server-shard-3-result.json",
    "macos-result.json",
)
# The parts may only prove completeness together, so the aggregating job must
# keep every one of these fail-closed coverage checks.
COVERAGE_PROOF = (
    'root / f"parallel-full-nodeids-{index}.txt"',
    'root / f"shard-nodeids-{index}.txt"',
    "shard coverage evidence missing for shard",
    "shards collected different test sets",
    "shard union does not cover the full parallel test set",
    "shard union repeats test cases",
)


def job_block(text: str, job: str) -> str:
    """Return one top-level job without its successors."""
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.rstrip() == f"  {job}:"), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.fullmatch(r"  [A-Za-z0-9_.-]+:", lines[index].rstrip()):
            end = index
            break
    return "\n".join(lines[start:end])


def validate(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read workflow: {exc}"]
    errors: list[str] = []
    # A shell line continuation must not hide one command from the checks.
    commands = re.sub(r"\\[ \t]*\n[ \t]*", " ", text)
    required = {
        "workflow name": r"(?m)^name:\s*release-full\s*$",
        "manual trigger": r"(?m)^\s*workflow_dispatch:\s*$",
        "candidate input": r"(?ms)candidate_id:.*?required:\s*true",
        "SHA input": r"(?ms)requested_sha:.*?required:\s*true",
        "read-only contents": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*$",
        "read-only actions": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*\n\s*actions:\s*read\s*$",
        "candidate concurrency": r"(?ms)^concurrency:\s*.*?group:.*inputs\.candidate_id",
        "no cancellation": r"(?m)^\s*cancel-in-progress:\s*false\s*$",
        "reservation job": r"(?ms)^\s*reserve:\s*\n.*?actions/upload-artifact@v4",
        "artifact lookup": r"actions/artifacts",
        "server static job": r"(?ms)^\s*server-static:\s*\n.*?runs-on:\s*ubuntu-latest",
        "server phases job": r"(?ms)^\s*server-phases:\s*\n.*?runs-on:\s*ubuntu-latest",
        "server parallel job": r"(?ms)^\s*server-parallel:\s*\n.*?runs-on:\s*ubuntu-latest",
        "shard matrix": r"(?ms)^\s*server-parallel:\s*\n.*?matrix:\s*\n\s*shard:\s*\[\s*0\s*,\s*1\s*,\s*2\s*,\s*3\s*\]",
        "macOS job": r"(?ms)^\s*macos-full:\s*\n.*?runs-on:\s*macos-14",
        "aggregate job": r"(?ms)^\s*aggregate:\s*\n.*?needs:\s*\[?reserve.*?server-static.*?server-phases.*?server-parallel.*?macos-full",
        "exact checkout": r"ref:\s*\$\{\{\s*inputs\.requested_sha\s*\}\}",
        "postgres serial phases": r"run_local_postgres_tests\.sh\s+--focused\s+--partitioned\s+--phases\s+strict,performance",
        "postgres parallel shard": r"run_local_postgres_tests\.sh\s+--focused\s+--partitioned\s+--phases\s+parallel\s+--shard\s+\$\{\{\s*matrix\.shard\s*\}\}/4",
        "release performance gate": r"GRAF_PERFORMANCE_GATE=required",
        "release worker count": r"GRAF_TEST_WORKERS=\d+\s+bash\s+apps/server/scripts/run_local_postgres_tests\.sh",
        "shard coverage upload": r"parallel-full-nodeids-\$\{\{\s*matrix\.shard\s*\}\}\.txt",
        "postgres phase verification": r"scripts/verify_rls_hardening\.py",
        "macOS tests": r"bash\s+apps/macos/Scripts/run-swift-tests\.sh",
        "macOS arm64 assertion": r"uname\s+-m.*arm64",
        "contract validation": r"swift\s+run\s+--package-path\s+apps/macos\s+ContractValidation",
        "evidence producer": r"scripts/emit-ci-evidence\.py",
        "evidence validator": r"scripts/validate-ci-evidence\.py",
        "authoritative flag": r"--authoritative-full",
        "zero skipped gates": r"--skipped-gate(?:\s+)?(?:none|\[\])|[\"']?skipped_gates[\"']?\s*[:=]\s*\[\]",
        "component SHAs": r"--component-sha",
        "download artifact": r"actions/download-artifact@v4",
        "merged component download": r"(?ms)actions/download-artifact@v4\s*\n\s*with:\s*\n\s*pattern:.*\n\s*merge-multiple:\s*true",
        "aggregate dependency": r"needs:\s*\[?reserve.*server-static.*server-phases.*server-parallel.*macos-full",
        "candidate collision guard": r"candidate_already_reserved",
    }
    for label, pattern in required.items():
        if not re.search(pattern, text if label not in ("postgres serial phases", "postgres parallel shard", "release performance gate", "release worker count") else commands):
            errors.append(f"missing workflow invariant: {label}")
    if re.search(r"(?m)^\s*pull_request\s*:", text):
        errors.append("release-full must not run on pull_request")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            errors.append(f"forbidden workflow content: {forbidden}")
    if re.search(r"(?m)^\s*(contents|actions|checks|pull-requests):\s*write\s*$", text):
        errors.append("release-full permissions must remain read-only")
    if len(re.findall(r"actions/checkout@v4", text)) < 4:
        errors.append("reserve and every component job must checkout exact SHA")
    if re.search(r"(?mi)^\s*[-]?[ ]*uses:\s*actions/(?:checkout|upload-artifact|download-artifact)@v[0-3]\b", text):
        errors.append("GitHub artifact/checkout actions must use v4")
    if "GRAF_CI_CANDIDATE_FILE" in text:
        errors.append("workflow must not depend on a local ignored candidate file")
    if "authoritative_full=true" not in text and "--authoritative-full" not in text:
        errors.append("aggregate must explicitly produce authoritative_full=true")
    blocks = {job: job_block(text, job) for job in (*SERVER_JOBS, "aggregate", "reserve", "macos-full")}
    for job, block in blocks.items():
        if not block:
            errors.append(f"missing job: {job}")
    if "run_local_postgres_tests.sh" in blocks["server-static"]:
        errors.append("static job must not run PostgreSQL tests; they belong to the phase jobs")
    if "run_local_postgres_tests.sh" not in blocks["server-phases"]:
        errors.append("server-phases must run the partitioned serial phases")
    if "run_local_postgres_tests.sh" not in blocks["server-parallel"]:
        errors.append("server-parallel must run one parallel shard")
    if "--shard" not in blocks["server-parallel"]:
        errors.append("server-parallel must declare its shard")
    if f"shard: [{', '.join(str(index) for index in range(SHARD_COUNT))}]" not in blocks["server-parallel"]:
        errors.append(f"server-parallel must run exactly {SHARD_COUNT} shards")
    for index in range(SHARD_COUNT):
        if f"server-shard-{index}-result.json" not in text:
            errors.append(f"aggregate must expect the result file of shard {index}")
    for result in RESULT_FILES:
        if result not in blocks["aggregate"]:
            errors.append(f"aggregate must validate {result}")
    for marker in COVERAGE_PROOF:
        if marker not in blocks["aggregate"]:
            errors.append(f"aggregate must prove shard coverage: {marker}")
    if f"range({SHARD_COUNT})" not in blocks["aggregate"]:
        errors.append(f"aggregate must check all {SHARD_COUNT} shard coverage pairs")
    for job, block in blocks.items():
        match = re.search(r"(?m)^\s+timeout-minutes:\s*(\d+)\s*$", block)
        if match is None:
            errors.append(f"job must declare a bounded timeout: {job}")
        elif not 1 <= int(match.group(1)) <= 60:
            errors.append(f"job timeout must stay within one hour: {job}")
    first_test = re.search(r"pytest\s|run_local_postgres_tests\.sh", commands)
    for command in (
        "PYTHONPATH=src uv run --extra dev ruff check .",
        "python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts",
    ):
        if commands.count(command) != 1 or first_test is None or commands.find(command) > first_test.start():
            errors.append(f"static command must run once before tests: {command}")
    return errors


def self_test() -> int:
    good = """name: release-full
on:
  workflow_dispatch:
    inputs:
      candidate_id:
        required: true
      requested_sha:
        required: true
permissions:
  contents: read
  actions: read
concurrency:
  group: graf-${{ inputs.candidate_id }}
  cancel-in-progress: false
jobs:
  reserve:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.requested_sha }}
      - run: gh api repos/o/r/actions/artifacts
      - run: echo candidate_already_reserved
      - uses: actions/upload-artifact@v4
  server-static:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - run: cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
      - run: python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
      - run: pytest -q tests/governance
      - uses: actions/upload-artifact@v4
        with:
          name: graf-full-component-server-${{ needs.reserve.outputs.artifact_key }}-${{ github.run_id }}-static
  server-phases:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - run: GRAF_TEST_WORKERS=4 GRAF_PERFORMANCE_GATE=required bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned --phases strict,performance -q
      - run: (cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py)
      - uses: actions/upload-artifact@v4
        with:
          name: graf-full-component-server-${{ needs.reserve.outputs.artifact_key }}-${{ github.run_id }}-phases
  server-parallel:
    runs-on: ubuntu-latest
    timeout-minutes: 40
    strategy:
      matrix:
        shard: [0, 1, 2, 3]
    steps:
      - uses: actions/checkout@v4
      - run: GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned --phases parallel --shard ${{ matrix.shard }}/4 -q
      - uses: actions/upload-artifact@v4
        with:
          name: graf-full-component-server-${{ needs.reserve.outputs.artifact_key }}-${{ github.run_id }}-shard-${{ matrix.shard }}
          path: |
            ${{ runner.temp }}/server-shard-${{ matrix.shard }}-result.json
            ${{ runner.temp }}/test-timings/parallel-full-nodeids-${{ matrix.shard }}.txt
            ${{ runner.temp }}/test-timings/shard-nodeids-${{ matrix.shard }}.txt
  macos-full:
    runs-on: macos-14
    timeout-minutes: 45
    steps:
      - run: test "$(uname -m)" = arm64
      - run: bash apps/macos/Scripts/run-swift-tests.sh
      - run: swift run --package-path apps/macos ContractValidation
  aggregate:
    needs: [reserve, server-static, server-phases, server-parallel, macos-full]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: graf-full-component-*-${{ needs.reserve.outputs.artifact_key }}-*
          merge-multiple: true
      - run: |
          python3 - "$component_dir" <<'PY'
          for index in range(4):
              full_path = root / f"parallel-full-nodeids-{index}.txt"
              shard_path = root / f"shard-nodeids-{index}.txt"
              if not full_path.is_file() or not shard_path.is_file():
                  raise SystemExit(f"shard coverage evidence missing for shard {index}")
              full_lists[index] = full
              union.extend(shard)
          if len(digests) != 1:
              raise SystemExit("shards collected different test sets")
          if sorted(union) != expected_nodes:
              raise SystemExit("shard union does not cover the full parallel test set")
          if len(union) != len(set(union)):
              raise SystemExit("shard union repeats test cases")
          PY
          for result in ("server-static-result.json", "server-phases-result.json",
                         "server-shard-0-result.json", "server-shard-1-result.json",
                         "server-shard-2-result.json", "server-shard-3-result.json",
                         "macos-result.json"):
              printf '%s\\n' "$result"
      - run: python3 scripts/emit-ci-evidence.py --authoritative-full --component-sha server=${{ inputs.requested_sha }} --skipped-gate []
      - run: python3 scripts/validate-ci-evidence.py evidence.json
      - uses: actions/upload-artifact@v4
"""
    with tempfile.TemporaryDirectory(prefix="graf-full-workflow-") as directory:
        path = Path(directory) / "workflow.yml"
        path.write_text(good, encoding="utf-8")
        errors = validate(path)
        assert errors == [], errors
        path.write_text(good.replace("cancel-in-progress: false", "cancel-in-progress: true"), encoding="utf-8")
        assert any("no cancellation" in item for item in validate(path))
        path.write_text(good.replace("bash apps/macos/Scripts/run-swift-tests.sh", "echo tests"), encoding="utf-8")
        assert any("macOS tests" in item for item in validate(path))
        path.write_text(
            good.replace("raise SystemExit(\"shard union does not cover the full parallel test set\")", "pass"),
            encoding="utf-8",
        )
        assert any("shard coverage" in item for item in validate(path))
        path.write_text(
            good.replace("      - run: pytest -q tests/governance", "      - run: bash apps/server/scripts/run_local_postgres_tests.sh --full"),
            encoding="utf-8",
        )
        assert any("static job must not run PostgreSQL tests" in item for item in validate(path))
        path.write_text(good.replace("--shard ${{ matrix.shard }}/4", "--shard ${{ matrix.shard }}/5"), encoding="utf-8")
        assert any("postgres parallel shard" in item for item in validate(path))
    print("full-ci-workflow self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path, nargs="?", default=Path(".github/workflows/release-full.yml"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate(args.workflow)
    if errors:
        for error in errors:
            print(f"full-ci-workflow: ERROR: {error}")
        return 1
    print("full-ci-workflow: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
