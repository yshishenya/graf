import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate-windows-pr-junit.py"
EXPECTED = (
    "RecordingAudioTimelineTests",
    "WebViewRoutePolicyTests",
    "WebViewBridgeEnvelopeTests",
    "NativeHashFailureTests",
    "NativeCustodyProtectionFailureTests",
)


@pytest.mark.parametrize("defect", [None, "missing", "duplicate", "disabled", "skipped", "failure", "bad-totals", "absent"])
def test_windows_pr_requires_all_five_actual_passes(tmp_path, defect):
    report = tmp_path / "ctest.xml"
    if defect != "absent":
        suite = ET.Element("testsuite", tests="5", failures="0")
        cases = [ET.SubElement(suite, "testcase", name=name, status="run") for name in EXPECTED]
        if defect == "missing":
            suite.remove(cases[-1])
        elif defect == "duplicate":
            cases[-1].set("name", EXPECTED[0])
        elif defect == "disabled":
            cases[-1].set("status", "notrun")
        elif defect in {"skipped", "failure"}:
            ET.SubElement(cases[-1], defect)
        elif defect == "bad-totals":
            suite.set("failures", "1")
        ET.ElementTree(suite).write(report)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--report", str(report)], capture_output=True, text=True, check=False,
    )
    if defect is None:
        assert result.returncode == 0 and "5/5" in result.stdout
    else:
        assert result.returncode == 1 and "5/5" not in result.stdout


def test_windows_pr_uses_the_reviewed_target_list():
    result = subprocess.run([sys.executable, str(SCRIPT), "--list"], capture_output=True, text=True, check=True)
    assert tuple(result.stdout.splitlines()) == EXPECTED


@pytest.mark.parametrize("defect", [None, "wrapper", "arguments", "will-fail", "pass-regex", "duplicate", "missing-exe"])
def test_windows_pr_checks_the_actual_ctest_commands(tmp_path, defect):
    tests = []
    for name in EXPECTED:
        binary = tmp_path / f"{name}.exe"
        binary.touch()
        tests.append({"name": name, "command": [str(binary)], "properties": [
            {"name": "WORKING_DIRECTORY", "value": str(tmp_path)},
        ]})
    target = tests[-1]
    if defect == "wrapper":
        target["command"] = tests[0]["command"]
    elif defect == "arguments":
        target["command"].append("--skip")
    elif defect in {"will-fail", "pass-regex"}:
        target["properties"].append({"name": defect.replace("-", "_").upper(), "value": True})
    elif defect == "duplicate":
        tests[-1] = tests[0]
    elif defect == "missing-exe":
        Path(target["command"][0]).unlink()
    plan = tmp_path / "ctest-plan.json"
    plan.write_text(json.dumps({"kind": "ctestInfo", "version": {"major": 1}, "tests": tests}))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--commands", str(plan), "--build-dir", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == (0 if defect is None else 1), result.stderr
