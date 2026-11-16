import json
import os
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


def test_t124_ctest_and_version_probe_share_windows_powershell_environment():
    import yaml

    workflow = SCRIPT.parents[1] / ".github/workflows/windows-pr.yml"
    steps = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)["jobs"]["windows"]["steps"]
    suites = [step for step in steps if "-R '^PublicAppInstallerTests$'" in step.get("run", "")]
    assert len(suites) == 1
    suite = suites[0]
    # pwsh -> ctest -> PS5 inherits PS7 module paths; a direct version probe does not.
    assert suite["shell"] == "powershell", "CTest must inherit a Windows PowerShell environment, not PS7 module paths"
    assert suite["run"].count("-R '^PublicAppInstallerTests$'") == 2
    assert "System32/WindowsPowerShell/v1.0/powershell.exe" in suite["run"]
    assert "& $engine -NoLogo -NoProfile -NonInteractive -Command" in suite["run"]
    assert "-c $check" not in suite["run"]
    for variable in ("checkPlan", "checkReport"):
        assert suite["run"].splitlines().count(f"${variable} | python -I -") == 1
        validator = suite["run"].split(f"${variable} = @'\n", 1)[1].split("\n'@", 1)[0]
        assert validator.isascii(), "PS5 stdin uses ASCII unless an explicit encoding is configured"


@pytest.mark.parametrize("defect", [None, "missing-marker", "duplicate-marker", "ctest-failure"])
def test_t124_actual_report_validator_reads_ps5_tee_bytes(tmp_path, defect):
    import yaml

    workflow = SCRIPT.parents[1] / ".github/workflows/windows-pr.yml"
    steps = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)["jobs"]["windows"]["steps"]
    run = next(step["run"] for step in steps if step.get("id") == "t124")
    validator = run.split("$checkReport = @'\n", 1)[1].split("\n'@", 1)[0]
    suite = ET.Element("testsuite", tests="1", failures="0")
    ET.SubElement(suite, "testcase", name="PublicAppInstallerTests", status="run")
    ET.ElementTree(suite).write(tmp_path / "t124-ctest.xml")
    marker = "128: PUBLIC_APPINSTALLER_TESTS cases=111 public_release_ready=false\r\n"
    log = "Synthetic PS5 Tee-Object output\r\n" + marker * (0 if defect == "missing-marker" else 2 if defect == "duplicate-marker" else 1)
    raw = b"\xff\xfe" + log.encode("utf-16-le")
    path = tmp_path / "t124-ctest.log"
    path.write_bytes(raw)
    result = subprocess.run(
        [sys.executable, "-I", "-c", validator], capture_output=True, text=True, check=False,
        env=dict(os.environ, REPORT_DIR=str(tmp_path), T124_CTEST_EXIT="8" if defect == "ctest-failure" else "0"),
    )
    assert result.returncode == (0 if defect is None else 1), result.stderr
    if defect in {"missing-marker", "duplicate-marker"}:
        assert "Missing or duplicate T124 suite completion marker." in result.stderr
    elif defect == "ctest-failure":
        assert "T124 CTest failed or timed out: 8" in result.stderr
    assert path.read_bytes() == raw  # Validate the original BOM/UTF16LE bytes without rewriting.


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
