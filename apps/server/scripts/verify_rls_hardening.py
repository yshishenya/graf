#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT / "src"))

RLS_VALIDATION_PATH = SERVER_ROOT / "src/twobrain_rec_server/db/rls_validation.py"
spec = importlib.util.spec_from_file_location("rls_validation", RLS_VALIDATION_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load rls validation module")
rls_validation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rls_validation
spec.loader.exec_module(rls_validation)
RLSValidationReport = rls_validation.RLSValidationReport
RLSProbeEvidence = rls_validation.RLSProbeEvidence
REQUIRED_RLS_PROBES = rls_validation.REQUIRED_RLS_PROBES

POSTGRES_POLICY_SUITE = "tests/integration/test_rls_postgres_policies.py"


def main() -> int:
    if not os.getenv("RLS_TEST_DATABASE_URL"):
        report = RLSValidationReport(environment="postgres_test")
        for line in report.evidence_lines():
            print(line)
        print("reason=postgres_test_database_required")
        return 0

    result = subprocess.run(
        ["uv", "run", "--extra", "dev", "pytest", "-q", POSTGRES_POLICY_SUITE],
        cwd=SERVER_ROOT,
        check=False,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    if result.returncode == 0:
        report = RLSValidationReport(
            environment="postgres_test",
            probes=[
                RLSProbeEvidence(name=probe_name, result="pass", environment="postgres_test")
                for probe_name in REQUIRED_RLS_PROBES
            ],
        )
        for line in report.evidence_lines():
            print(line)
        print(f"probe_suite={POSTGRES_POLICY_SUITE}")
        return 0
    report = RLSValidationReport(environment="postgres_test")
    for line in report.evidence_lines():
        print(line)
    print(f"probe_suite={POSTGRES_POLICY_SUITE}")
    print(f"probe_command_exit_code={result.returncode}")
    print("reason=rls_probe_command_failed")
    if result.stdout.strip():
        print("probe_stdout_present=true")
    if result.stderr.strip():
        print("probe_stderr_present=true")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
