from twobrain_rec_server.meeting_detection.candidates import (
    aggregate_unknown_native_rollups,
    upload_allowed,
)


def _candidate_rollup(**overrides: object) -> dict[str, object]:
    rollup: dict[str, object] = {
        "platform": "macos",
        "identityMode": "raw_candidate_allowed",
        "uploadEligibility": "server_candidate_upload",
        "candidateScore": 5,
        "candidateReasons": ["stable_mic_duration", "vks_name_token"],
        "suppressionReasons": [],
        "bundleId": "ru.example.vks",
        "displayName": "Example VKS",
        "signingTeamId": "ABCDE12345",
        "version": "1.0.0",
        "stableObservationCount": 3,
        "manualRecordNearbyCount": 1,
        "calendarOrJoinHintCount": 1,
    }
    rollup.update(overrides)
    return rollup


def test_upload_allowed_requires_raw_high_score_identity() -> None:
    assert upload_allowed(_candidate_rollup())
    assert not upload_allowed(_candidate_rollup(candidateScore=3))
    assert not upload_allowed(_candidate_rollup(identityMode="redacted"))
    assert not upload_allowed(_candidate_rollup(bundleId=None))


def test_upload_allowed_suppresses_explicit_non_targets() -> None:
    assert not upload_allowed(_candidate_rollup(suppressionReasons=["browser_bundle"]))
    assert not upload_allowed(_candidate_rollup(suppressionReasons=["audio_utility"]))


def test_aggregate_unknown_native_rollups_combines_same_bundle() -> None:
    aggregates = aggregate_unknown_native_rollups(
        [
            _candidate_rollup(version="1.0.0", stableObservationCount=2),
            _candidate_rollup(version="1.1.0", stableObservationCount=4, candidateScore=7),
            _candidate_rollup(bundleId="com.google.Chrome", suppressionReasons=["browser_bundle"]),
        ]
    )

    assert len(aggregates) == 1
    aggregate = aggregates[0]
    assert aggregate.bundle_id == "ru.example.vks"
    assert aggregate.candidate_score == 7
    assert aggregate.stable_observation_count == 6
    assert aggregate.version_samples == ["1.0.0", "1.1.0"]
    assert aggregate.candidate_reasons == {"stable_mic_duration", "vks_name_token"}
