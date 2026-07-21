import json
from pathlib import Path

import pytest

from twobrain_rec_server.meeting_detection.registry import (
    MeetingTargetRegistryError,
    registry_entries,
    registry_etag,
    validate_registry_document,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_DATA = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json"
)


def _seed_document() -> dict[str, object]:
    return json.loads(REGISTRY_DATA.read_text(encoding="utf-8"))


def test_migration_registry_is_valid_and_honest_about_prompt_targets() -> None:
    document = validate_registry_document(_seed_document())
    prompt_targets = {
        target["id"]
        for target in document["targets"]
        if target["mode"] == "prompt_enabled"
    }

    native_targets = {
        target["id"]
        for target in document["targets"]
        if target["platform"] == "macos"
        and target["targetFamily"] == "native_app"
        and target.get("nativeBundleIds")
    }
    bundle_ids = [
        bundle_id.lower()
        for target in document["targets"]
        for bundle_id in target.get("nativeBundleIds", [])
    ]

    assert len(document["targets"]) == 85
    assert len(native_targets) == 79
    assert prompt_targets == native_targets
    assert len(bundle_ids) == len(set(bundle_ids)) == 87
    assert all(
        target["mode"] == "manual_or_browser_only"
        for target in document["targets"]
        if target["targetFamily"] == "browser_meeting"
    )


def test_registry_etag_is_stable_for_canonical_json() -> None:
    document = _seed_document()
    first = registry_etag(document)
    second = registry_etag(json.loads(json.dumps(document, sort_keys=True)))

    assert first == second
    assert len(first) == 64


def test_registry_entries_normalize_target_fields() -> None:
    entries = registry_entries(_seed_document())
    telemost = next(entry for entry in entries if entry["target_id"] == "yandex_telemost")

    assert telemost["mode"] == "prompt_enabled"
    assert telemost["native_bundle_ids"] == ["ru.yandex.desktop.telemost"]
    assert telemost["required_signals"] == ["macos_audio_hal_assertion"]


def test_prompt_enabled_native_target_requires_verified_bundle_identity() -> None:
    document = _seed_document()
    document["targets"][0] = {
        **document["targets"][0],
        "evidence": "verify_required",
    }

    with pytest.raises(MeetingTargetRegistryError):
        validate_registry_document(document)


def test_browser_target_cannot_depend_only_on_generic_browser_mic_signal() -> None:
    document = _seed_document()
    document["targets"].append(
        {
            "id": "bad_browser",
            "displayName": "Bad Browser",
            "market": "global",
            "platform": "browser",
            "targetFamily": "browser_meeting",
            "mode": "diagnostic_only",
            "evidence": "seed",
            "requiredSignals": ["macos_audio_hal_assertion"],
        }
    )

    with pytest.raises(MeetingTargetRegistryError):
        validate_registry_document(document)


def test_browser_target_requires_metadata_and_calendar_join_intent() -> None:
    document = _seed_document()
    document["targets"].append(
        {
            "id": "bad_browser_missing_join",
            "displayName": "Bad Browser Missing Join",
            "market": "global",
            "platform": "browser",
            "targetFamily": "browser_meeting",
            "mode": "diagnostic_only",
            "evidence": "seed",
            "requiredSignals": ["browser_metadata"],
            "browserServicePatterns": [
                {
                    "serviceFamily": "google_meet",
                    "hostCategory": "first_party",
                    "patternClass": "meeting_room",
                }
            ],
        }
    )

    with pytest.raises(MeetingTargetRegistryError):
        validate_registry_document(document)


def test_registry_rejects_duplicate_target_ids() -> None:
    document = _seed_document()
    document["targets"].append(document["targets"][0])

    with pytest.raises(MeetingTargetRegistryError):
        validate_registry_document(document)


def test_registry_rejects_case_insensitive_duplicate_bundle_ids() -> None:
    document = _seed_document()
    document["targets"].append(
        {
            **document["targets"][0],
            "id": "duplicate_zoom_bundle",
            "nativeBundleIds": ["US.ZOOM.XOS"],
        }
    )

    with pytest.raises(MeetingTargetRegistryError, match="duplicate nativeBundleId"):
        validate_registry_document(document)


def test_registry_accepts_safe_non_target_rules() -> None:
    document = _seed_document()
    document["nonTargetRules"] = [
        {
            "platform": "macos",
            "ruleKind": "bundle_id",
            "ruleValue": "com.apple.Safari",
            "reasonCode": "browser_bundle",
        }
    ]

    assert validate_registry_document(document)["nonTargetRules"][0]["ruleValue"] == "com.apple.Safari"


def test_registry_rejects_unsafe_non_target_rules() -> None:
    document = _seed_document()
    document["nonTargetRules"] = [
        {
            "platform": "macos",
            "ruleKind": "display_name_token",
            "ruleValue": "https://example.test/private",
            "reasonCode": "browser_bundle",
        }
    ]

    with pytest.raises(MeetingTargetRegistryError):
        validate_registry_document(document)
