from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_CHECK = PROJECT_ROOT / "specs" / "058-web-cabinet-htmx-shell" / "evidence" / "cabinet_runtime_check.py"


def _load_runtime_check():
    spec = importlib.util.spec_from_file_location("cabinet_runtime_check", RUNTIME_CHECK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cabinet_runtime_check_returns_metadata_safe_pass_evidence() -> None:
    module = _load_runtime_check()

    evidence = module.run_checks()

    assert evidence["feature"] == "058-web-cabinet-htmx-shell"
    assert evidence["result"] == "pass"
    assert evidence["surface_count"] >= 6
    assert all(check["passed"] for check in evidence["checks"])
    serialized = json.dumps(evidence, ensure_ascii=False)
    for forbidden in (
        "SAFE_TRANSCRIPT_TEXT",
        "storage_object_key",
        "signed_url",
        "external_job_id",
        "/Users/",
        "sk-",
        "password",
    ):
        assert forbidden not in serialized


def test_cabinet_runtime_check_script_outputs_json() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNTIME_CHECK)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    evidence = json.loads(completed.stdout)

    assert evidence["result"] == "pass"
    assert {check["name"] for check in evidence["checks"]} >= {
        "standalone_shell",
        "embedded_shell",
        "list_fragment_bounded",
        "detail_fragment_bounded",
        "deletion_report_fragment_bounded",
        "hx_vary_header",
        "metadata_safe_html",
    }
