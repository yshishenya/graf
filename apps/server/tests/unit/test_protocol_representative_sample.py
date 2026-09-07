from copy import deepcopy
from uuid import uuid4

import pytest

from tests.fixtures.meeting_protocol import protocol_bundle
from twobrain_rec_server.cli.meeting_protocol_eval import CONTROL_CASES
from twobrain_rec_server.outcomes import prompt_bundle as prompts


def sample_fixture():
    run = uuid4()
    bundle = protocol_bundle()
    _, _, export_hash = prompts.build_root_export(bundle)
    sources = [{"meeting_id": str(uuid4()), "source_hash": str(n) * 64,
                "selection_status": "available"} for n in range(1, 4)]
    return run, bundle, {
        "schema_version": "graf-outcome-sample-v1", "run_id": str(run),
        "root_export_hash": export_hash, "inventory_hash": "a" * 64,
        "real_sources": sources, "long_meeting_id": sources[0]["meeting_id"],
        "controls": {case: str(uuid4()) for case in CONTROL_CASES},
    }


def test_representative_sample_is_embedded_and_hash_bound():
    run, bundle, sample = sample_fixture()
    saved = prompts.build_evaluation_snapshot(bundle, project_id="synthetic-project", run_id=run,
                                              sample_manifest=sample)
    _, authority = prompts.validate_evaluation_snapshot(saved)
    assert authority["sample_manifest_hash"] == prompts._digest(sample)
    changed = deepcopy(saved)
    changed["sample_manifest"]["long_meeting_id"] = sample["real_sources"][1]["meeting_id"]
    with pytest.raises(prompts.PromptBundleError, match="evaluation_authority_invalid"):
        prompts.validate_evaluation_snapshot(changed)


@pytest.mark.parametrize("mutation", ["duplicate", "missing_control", "foreign_long", "foreign_run"])
def test_representative_sample_rejects_invalid_identity(mutation):
    run, bundle, sample = sample_fixture()
    if mutation == "duplicate":
        sample["real_sources"][1] = sample["real_sources"][0]
    elif mutation == "missing_control":
        sample["controls"].pop(CONTROL_CASES[0])
    elif mutation == "foreign_long":
        sample["long_meeting_id"] = str(uuid4())
    else:
        sample["run_id"] = str(uuid4())
    with pytest.raises(ValueError):
        prompts.build_evaluation_snapshot(bundle, project_id="synthetic-project", run_id=run,
                                          sample_manifest=sample)
