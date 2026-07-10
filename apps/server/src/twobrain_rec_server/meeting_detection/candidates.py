from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SERVER_CANDIDATE_MIN_SCORE = 4
NON_TARGET_SUPPRESSIONS = {
    "browser_bundle",
    "audio_utility",
    "system_service",
    "media_player",
    "audio_editor",
    "game",
    "screen_recorder",
    "known_non_target",
    "workspace_upload_disabled",
}


@dataclass(slots=True)
class CandidateAggregate:
    platform: str
    bundle_id: str | None
    display_name: str | None
    signing_team_id: str | None = None
    version_samples: list[str] = field(default_factory=list)
    candidate_score: int = 0
    candidate_reasons: set[str] = field(default_factory=set)
    suppression_reasons: set[str] = field(default_factory=set)
    stable_observation_count: int = 0
    reporting_installation_count: int = 1
    manual_record_nearby_count: int = 0
    calendar_or_join_hint_count: int = 0


def upload_allowed(rollup: dict[str, Any]) -> bool:
    return (
        rollup.get("identityMode") == "raw_candidate_allowed"
        and rollup.get("uploadEligibility") == "server_candidate_upload"
        and int(rollup.get("candidateScore", 0)) >= SERVER_CANDIDATE_MIN_SCORE
        and bool(rollup.get("bundleId"))
        and bool(rollup.get("displayName"))
        and not is_explicit_non_target(rollup.get("suppressionReasons", []))
    )


def is_explicit_non_target(suppression_reasons: list[str] | tuple[str, ...] | set[str]) -> bool:
    return bool(set(suppression_reasons) & NON_TARGET_SUPPRESSIONS)


def aggregate_unknown_native_rollups(rollups: list[dict[str, Any]]) -> list[CandidateAggregate]:
    aggregates: dict[tuple[str, str | None], CandidateAggregate] = {}
    for rollup in rollups:
        if not upload_allowed(rollup):
            continue
        key = (str(rollup.get("platform", "macos")), rollup.get("bundleId"))
        aggregate = aggregates.setdefault(
            key,
            CandidateAggregate(
                platform=key[0],
                bundle_id=rollup.get("bundleId"),
                display_name=rollup.get("displayName"),
                signing_team_id=rollup.get("signingTeamId"),
            ),
        )
        aggregate.candidate_score = max(aggregate.candidate_score, int(rollup.get("candidateScore", 0)))
        aggregate.candidate_reasons.update(rollup.get("candidateReasons", []))
        aggregate.suppression_reasons.update(rollup.get("suppressionReasons", []))
        aggregate.stable_observation_count += int(rollup.get("stableObservationCount", 0))
        aggregate.manual_record_nearby_count += int(rollup.get("manualRecordNearbyCount", 0))
        aggregate.calendar_or_join_hint_count += int(rollup.get("calendarOrJoinHintCount", 0))
        version = rollup.get("version")
        if version and version not in aggregate.version_samples and len(aggregate.version_samples) < 10:
            aggregate.version_samples.append(str(version))
    return list(aggregates.values())
