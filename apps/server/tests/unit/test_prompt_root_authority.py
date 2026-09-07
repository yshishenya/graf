"""Admission integrity stays distinct from permission to execute this runtime."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.fixtures.prompt_authority import artifact_binding, digest, promotion_row
from twobrain_rec_server.outcomes import prompt_bundle
from twobrain_rec_server.outcomes.prompt_bundle import (
    ArtifactBinding,
    PromptBundleError,
    load_execution_authority,
    validate_promotion_row,
)


@pytest.mark.parametrize("filename", [
    "config.py",
    "db/models/outcomes.py",
    "db/migrations/versions/0087_prompt_root_promotion.py",
    "cli/meeting_protocol_eval.py",
    "cli/meeting_protocol_eval_runtime.py",
])
def test_runtime_contract_hash_binds_authority_boundaries(monkeypatch, filename):
    baseline = prompt_bundle.runtime_contract_hash()
    target = Path(prompt_bundle.__file__).parent.parent / filename
    read_bytes = Path.read_bytes

    def changed_boundary(path):
        contents = read_bytes(path)
        return contents + b"\n# synthetic authority boundary change\n" if path == target else contents

    monkeypatch.setattr(Path, "read_bytes", changed_boundary)
    assert prompt_bundle.runtime_contract_hash() != baseline


def load_row(row, previous=None, *, pinned=None):
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), get=AsyncMock(return_value=previous))
    settings = SimpleNamespace(
        langfuse_project_id=row.project_id, env="production",
        outcome_root_prompt_version=None, outcome_prompt_label="production",
    )
    return asyncio.run(load_execution_authority(db, settings, pinned=pinned))


@pytest.mark.parametrize("version", [True, False, 1.0, "1", 0, 2, None])
def test_artifact_version_rejects_coercions_and_unknown_versions(version):
    binding = dict(artifact_id=str(uuid4()), schema_version="graf-outcome-promotion-event-v1",
                   artifact_version=version, hash="a" * 64)
    with pytest.raises(ValueError):
        ArtifactBinding.model_validate(binding)


def test_exact_integer_artifact_version_is_valid():
    row = promotion_row()
    assert ArtifactBinding.model_validate(artifact_binding(row, "event")).artifact_version == 1
    bundle, authority = load_row(row)
    assert bundle.root.root_prompt_version == 42
    assert load_row(row, pinned=authority)[1] == authority


def test_historical_predecessor_is_integrity_checked_but_not_executable():
    previous = promotion_row(root_version=41, runtime_hash="f" * 64, is_current=False)
    current = promotion_row(previous=previous)
    assert load_row(current, previous)[0].root.root_prompt_version == 42
    with pytest.raises(PromptBundleError):
        validate_promotion_row(previous)
    with pytest.raises(PromptBundleError):
        load_row(previous)
    with pytest.raises(PromptBundleError):
        load_row(previous, pinned={
            "kind": "production", "candidate_root": previous.event_json["target"],
            "event": artifact_binding(previous, "event"),
        })


@pytest.mark.parametrize("field", ["root_export", "activation", "qualification", "event"])
@pytest.mark.parametrize("rehash", [False, True])
def test_predecessor_requires_all_full_typed_bodies(field, rehash):
    previous = promotion_row(root_version=41, runtime_hash="f" * 64)
    getattr(previous, f"{field}_json")["unexpected"] = True
    if rehash:
        setattr(previous, f"{field}_hash", digest(getattr(previous, f"{field}_json")))
    current = promotion_row(previous=previous)
    with pytest.raises(PromptBundleError):
        load_row(current, previous)


@pytest.mark.parametrize("change", ["row_id", "project_id", "source_version", "event_id"])
def test_predecessor_binding_must_match_the_loaded_row(change):
    previous = promotion_row(root_version=41)
    current = promotion_row(previous=previous)
    if change == "row_id":
        previous.id = uuid4()
    elif change == "project_id":
        previous.project_id = "another-project"
    elif change == "source_version":
        previous.expected_source_version += 1
    else:
        copied = promotion_row(root_version=41)
        previous.event_json = copied.event_json
        previous.event_hash = copied.event_hash
        current = promotion_row(previous=previous)
    with pytest.raises(PromptBundleError):
        load_row(current, previous)


def test_current_authority_and_previous_event_are_both_required():
    previous = promotion_row(root_version=41)
    current = promotion_row(previous=previous)
    with pytest.raises(PromptBundleError):
        load_row(current)
    other = promotion_row()
    with pytest.raises(PromptBundleError):
        load_row(current, previous, pinned=validate_promotion_row(other)[1])
