"""Execute the shared observer in both supported browser engines on synthetic pages."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.browser
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_real_result_visibility_observer(engine):
    script = Path(__file__).parents[1] / "browser/result-visibility.test.cjs"
    result = subprocess.run(
        ["node", str(script)], env=dict(os.environ, GRAF_BROWSER=engine),
        capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("PASS: ")
