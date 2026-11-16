#!/usr/bin/env python3
"""Require a real CTest pass for every selected Windows PR test."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TESTS = (
    "RecordingAudioTimelineTests",
    "WebViewRoutePolicyTests",
    "WebViewBridgeEnvelopeTests",
    "NativeHashFailureTests",
    "NativeCustodyProtectionFailureTests",
)


def validate(report: Path) -> None:
    root = ET.parse(report).getroot()
    cases = list(root.iter("testcase"))
    if root.tag != "testsuite" or len(cases) != len(TESTS) or {
        case.get("name") for case in cases
    } != set(TESTS):
        raise ValueError("expected exactly one result for each Windows PR test")
    if root.get("tests") != str(len(TESTS)) or any(
        root.get(key, "0") != "0" for key in ("disabled", "skipped", "errors", "failures")
    ):
        raise ValueError("CTest reported unsuccessful or inconsistent totals")
    for case in cases:
        if case.get("status") != "run" or any(
            child.tag in {"disabled", "skipped", "error", "failure"} for child in case
        ):
            raise ValueError(f"{case.get('name')} did not pass")


def validate_commands(commands: Path, build_dir: Path) -> None:
    plan = json.loads(commands.read_text(encoding="utf-8-sig"))
    build_dir = build_dir.resolve(strict=True)
    tests = plan["tests"]
    if plan["kind"] != "ctestInfo" or plan["version"]["major"] != 1 or len(tests) != len(TESTS) or {
        test["name"] for test in tests
    } != set(TESTS):
        raise ValueError("expected exactly five CTest commands")
    for test in tests:
        name = test["name"]
        expected = build_dir / f"{name}.exe"
        command = test["command"]
        if (len(command) != 1 or not Path(command[0]).is_absolute()
                or Path(command[0]).resolve(strict=True) != expected or not expected.is_file()):
            raise ValueError(f"{name} must execute its build target directly")
        properties = test.get("properties", [])
        if (len(properties) != 1 or properties[0]["name"] != "WORKING_DIRECTORY"
                or Path(properties[0]["value"]).resolve(strict=True) != build_dir):
            raise ValueError(f"{name} has unexpected CTest properties")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--report", type=Path)
    mode.add_argument("--commands", type=Path)
    parser.add_argument("--build-dir", type=Path)
    args = parser.parse_args()
    if args.list:
        print(*TESTS, sep="\n")
        return 0
    try:
        if args.commands:
            if args.build_dir is None:
                parser.error("--commands requires --build-dir")
            validate_commands(args.commands, args.build_dir)
            return 0
        validate(args.report)
    except (OSError, ValueError, TypeError, KeyError, IndexError, ET.ParseError) as error:
        print(f"Windows PR: {error}", file=sys.stderr)
        return 1
    print(f"Windows PR: {len(TESTS)}/{len(TESTS)} expected tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
