"""Focused contract tests for authoritative merge-group PR verification."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import json

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "verify-merge-group-mapping.py"
SPEC = importlib.util.spec_from_file_location("verify_merge_group_mapping", SCRIPT)
assert SPEC and SPEC.loader
mapping = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mapping)


def _identity(*numbers: int) -> dict[str, object]:
    return {"event_name": "merge_group", "pull_request_numbers": list(numbers)}


def _event(*numbers: int) -> list[dict[str, int]]:
    return [{"number": number} for number in numbers]


FIXTURES = Path(__file__).parent / "fixtures" / "feature_227"


def _authoritative() -> dict[str, object]:
    return json.loads((FIXTURES / "merge_group_api.json").read_text(encoding="utf-8"))


def _full_identity(*numbers: int) -> dict[str, object]:
    return {
        **_identity(*numbers),
        "target_sha": "a" * 40,
        "base_sha": "b" * 40,
        "merge_group_id": "mg-227-1",
    }


def _fetch(number: int) -> dict[str, object]:
    heads = {42: "c" * 40, 43: "d" * 40}
    return {
        "number": number,
        "state": "open",
        "head": {"sha": heads[number]},
        "base": {"sha": "b" * 40},
    }


def test_verify_accepts_complete_mapping_and_open_prs() -> None:
    result = mapping.verify(
        _identity(7, 8),
        _event(7, 8),
        lambda number: {"number": number, "state": "open"},
    )

    assert result == {"verified": True, "pull_request_numbers": [7, 8]}


def test_verify_rejects_conflicting_event_mapping() -> None:
    with pytest.raises(mapping.MappingError, match="mappings disagree"):
        mapping.verify(_identity(7, 8), _event(7, 9), lambda number: {"number": number, "state": "open"})


def test_verify_rejects_closed_pr() -> None:
    with pytest.raises(mapping.MappingError, match="not open"):
        mapping.verify(_identity(7), _event(7), lambda number: {"number": number, "state": "closed"})


def test_verify_rejects_api_number_mismatch() -> None:
    with pytest.raises(mapping.MappingError, match="no matching PR"):
        mapping.verify(_identity(7), _event(7), lambda number: {"number": 99, "state": "open"})


def test_verify_rejects_api_error() -> None:
    def fetch(_number: int) -> dict[str, object]:
        raise RuntimeError("network unavailable")

    with pytest.raises(mapping.MappingError, match="API lookup failed"):
        mapping.verify(_identity(7), _event(7), fetch)


def test_verify_requires_authoritative_mapping_for_sha_bound_identity() -> None:
    with pytest.raises(mapping.MappingError, match="authoritative GitHub API mapping is required"):
        mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch)


def test_verify_accepts_complete_authoritative_mapping_and_sha_provenance() -> None:
    result = mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch, _authoritative())

    assert result == {
        "verified": True,
        "pull_request_numbers": [42, 43],
        "target_sha": "a" * 40,
        "base_sha": "b" * 40,
        "merge_group_id": "mg-227-1",
        "mapping_source": "github-api:associated-pull-requests",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_sha", "e" * 40, "target_sha does not match"),
        ("base_sha", "f" * 40, "base_sha does not match"),
        ("merge_group_id", "mg-other", "merge-group ID does not match"),
    ],
)
def test_verify_rejects_authoritative_event_identity_conflicts(field: str, value: str, message: str) -> None:
    authoritative = _authoritative()
    authoritative[field] = value
    with pytest.raises(mapping.MappingError, match=message):
        mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch, authoritative)


def test_verify_rejects_incomplete_authoritative_mapping() -> None:
    authoritative = _authoritative()
    authoritative["pull_requests"] = authoritative["pull_requests"][:1]
    with pytest.raises(mapping.MappingError, match="mappings disagree"):
        mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch, authoritative)


def test_verify_rejects_authoritative_pr_without_both_shas() -> None:
    authoritative = _authoritative()
    authoritative["pull_requests"][0]["base"] = {}
    with pytest.raises(mapping.MappingError, match="must include head and base SHA"):
        mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch, authoritative)


def test_verify_rejects_authoritative_detail_sha_conflict() -> None:
    authoritative = _authoritative()
    authoritative["pull_requests"][0]["head"]["sha"] = "e" * 40
    with pytest.raises(mapping.MappingError, match="head SHA disagrees"):
        mapping.verify(_full_identity(42, 43), _event(42, 43), _fetch, authoritative)


@pytest.mark.parametrize(
    ("identity", "rows"),
    [
        ({"event_name": "pull_request", "pull_request_numbers": [7]}, _event(7)),
        (_identity(), []),
        (_identity(7, 7), _event(7, 7)),
        (_identity(7), [{"number": 0}]),
        (_identity(7), [{"number": "7"}]),
    ],
)
def test_verify_rejects_invalid_mapping(identity: dict[str, object], rows: list[object]) -> None:
    with pytest.raises(mapping.MappingError):
        mapping.verify(identity, rows, lambda number: {"number": number, "state": "open"})
