from __future__ import annotations

from types import SimpleNamespace

from twobrain_rec_server.outcomes.prompt_optimization import (
    PromptOptimizationAdapter,
)


def test_validation_retry_uses_distinct_observable_call_key() -> None:
    adapter = PromptOptimizationAdapter.__new__(PromptOptimizationAdapter)
    calls: list[str] = []

    def fake_call(**kwargs):
        calls.append(str(kwargs["example_id"]))
        return SimpleNamespace(validated_result={"attempt": len(calls)})

    adapter._call = fake_call  # type: ignore[method-assign]

    def validator(value: object) -> dict[str, int]:
        if value == {"attempt": 1}:
            raise ValueError("semantic contract is temporarily invalid")
        return value  # type: ignore[return-value]

    call, result = adapter._call_with_validation_retry(
        phase="task",
        snapshot=SimpleNamespace(),
        prompt_text="{}",
        variables={},
        example_id="example-1",
        validator=validator,
    )

    assert calls == ["example-1", "example-1:validation-retry-1"]
    assert call.validated_result == {"attempt": 2}
    assert result == {"attempt": 2}
