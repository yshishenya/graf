#!/usr/bin/env python3
"""Run metadata-only production proof for automatic outcome review and sharing."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import UUID

from prove_owner_review_live import _request_json
from smoke_target import read_private_auth_material, validate_origin


@dataclass(slots=True)
class OutcomeLiveProof:
    proof_id: str
    target_origin: str
    run_id: str
    meeting_id: str
    health_live: int | str
    health_ready: int | str
    candidate_state: str
    accept_state: str
    share_state: str
    public_projection_state: str
    cleanup_state: str = "deferred"
    route_status: dict[str, int | str] = field(default_factory=dict)
    failure_code: str | None = None


def _safe_json(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    lowered = serialized.lower()
    for forbidden in ["bearer ", "authorization", "x-auth-session", "session_token", "cookie", "set-cookie", "@"]:
        if forbidden in lowered:
            raise SystemExit(f"unsafe proof payload contains forbidden marker: {forbidden}")
    return serialized


def _proof(origin: str, run_id: str, meeting_id: UUID, token_file: Path, timeout: int) -> OutcomeLiveProof:
    token = read_private_auth_material(token_file, expected_run_id=run_id)
    route_status: dict[str, int | str] = {}
    live_status, _, live_code = _request_json(origin, "/api/v1/health/live")
    ready_status, _, ready_code = _request_json(origin, "/api/v1/health/ready")
    route_status["health_live"] = live_status or live_code or "blocked"
    route_status["health_ready"] = ready_status or ready_code or "blocked"
    if live_status != 200 or ready_status != 200:
        return OutcomeLiveProof("feature-139-meeting-outcome-live", origin, run_id, str(meeting_id), route_status["health_live"], route_status["health_ready"], "blocked", "blocked", "blocked", "blocked", route_status=route_status, failure_code=live_code or ready_code)

    candidate_state = "blocked"
    candidate: dict[str, object] | None = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, payload, code = _request_json(origin, f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates", token)
        route_status["candidates"] = status or code or "blocked"
        candidates = (payload or {}).get("candidates", []) if payload else []
        matching = [item for item in candidates if item.get("template_key") == "graf-auto-v1"]
        candidate = matching[0] if matching else None
        candidate_state = str(candidate.get("state")) if candidate else "missing"
        if candidate_state in {"ready", "failed", "blocked", "stale", "expired", "closed"}:
            break
        time.sleep(3)

    if candidate is None or candidate_state != "ready":
        return OutcomeLiveProof("feature-139-meeting-outcome-live", origin, run_id, str(meeting_id), route_status["health_live"], route_status["health_ready"], candidate_state, "blocked", "blocked", "blocked", route_status=route_status, failure_code="candidate_not_ready")

    candidate_id = str(candidate["candidate_id"])
    expected_current = candidate.get("current_outcome_set_id")
    accept_status, accepted, accept_code = _request_json(
        origin,
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/accept",
        token,
        method="POST",
        payload={"expected_current_outcome_set_id": expected_current},
    )
    route_status["accept"] = accept_status or accept_code or "blocked"
    accept_state = "accepted" if accept_status == 200 and (accepted or {}).get("state") == "accepted" else "blocked"
    if accept_state != "accepted":
        return OutcomeLiveProof("feature-139-meeting-outcome-live", origin, run_id, str(meeting_id), route_status["health_live"], route_status["health_ready"], candidate_state, accept_state, "blocked", "blocked", route_status=route_status, failure_code=accept_code or "accept_failed")

    share_status, share, share_code = _request_json(
        origin,
        f"/api/v1/cabinet/meetings/{meeting_id}/shares",
        token,
        method="POST",
        payload={"audience_type": "link", "content_scope": "summary_only", "can_download": False, "can_export": False},
    )
    route_status["share_create"] = share_status or share_code or "blocked"
    share_state = "created" if share_status == 201 and share and share.get("share_url") else "blocked"
    if share_state != "created":
        return OutcomeLiveProof("feature-139-meeting-outcome-live", origin, run_id, str(meeting_id), route_status["health_live"], route_status["health_ready"], candidate_state, accept_state, share_state, "blocked", route_status=route_status, failure_code=share_code or "share_create_failed")

    share_url = str(share["share_url"])
    if not share_url.startswith("/"):
        raise SystemExit("production share URL must be relative")
    public_status, _, public_code = _request_json(origin, share_url)
    route_status["share_read"] = public_status or public_code or "blocked"
    projection_state = "ready" if public_status == 200 else "blocked"
    return OutcomeLiveProof("feature-139-meeting-outcome-live", origin, run_id, str(meeting_id), route_status["health_live"], route_status["health_ready"], candidate_state, accept_state, share_state, projection_state, route_status=route_status, failure_code=public_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run metadata-only production outcome proof")
    parser.add_argument("--api", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--meeting-id", required=True, type=UUID)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    origin = validate_origin(args.api)
    if not args.execute:
        proof = OutcomeLiveProof("feature-139-meeting-outcome-live", origin, args.run_id, str(args.meeting_id), "deferred", "deferred", "deferred", "deferred", "deferred", "deferred")
    else:
        proof = _proof(origin, args.run_id, args.meeting_id, args.token_file, args.timeout_seconds)
    output = _safe_json(asdict(proof))
    sys.stdout.write(output + "\n")
    if args.execute and not all(value in {"accepted", "created", "ready"} for value in (proof.accept_state, proof.share_state, proof.public_projection_state)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
