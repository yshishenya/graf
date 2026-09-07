from __future__ import annotations

import pathlib

from twobrain_rec_server.outcomes.prompt_optimization import (
    ADAPTER_VERSION,
    CHECKPOINT_PREFIX,
    JUDGE_NAMES,
    OPTIMIZER_VERSION,
)


def test_optimizer_contract_is_gepa_only_synthetic_and_no_auto_promotion() -> None:
    assert OPTIMIZER_VERSION == "0.1.4"
    assert ADAPTER_VERSION == "graf-gepa-v1"
    assert CHECKPOINT_PREFIX.startswith("_system/prompt-optimization")
    assert len(JUDGE_NAMES) == 3
    source = (
        pathlib.Path(__file__).parents[2]
        / "src/twobrain_rec_server/outcomes/prompt_optimization.py"
    ).read_text(encoding="utf-8")
    assert "import dspy" not in source
    assert "jepa" not in source.lower()
    assert "labels=[]" in source
    assert "update_prompt(" not in source
    assert "_system/prompts/verified-production/" not in source
