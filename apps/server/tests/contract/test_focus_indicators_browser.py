"""Exercise the shipped focus styles in a real browser, including forced colors."""
import subprocess
from pathlib import Path

import pytest


@pytest.mark.browser
def test_fields_have_one_contour_and_actions_keep_keyboard_focus() -> None:
    script = Path(__file__).parents[1] / "browser/focus-indicators.test.cjs"
    subprocess.run(["node", str(script)], check=True, capture_output=True, text=True, timeout=90)
