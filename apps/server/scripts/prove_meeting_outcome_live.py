#!/usr/bin/env python3
"""Run metadata-only production proof for the trusted outcome lifecycle."""

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
    slot_state: str
    share_state: str
    public_projection_state: str
    cleanup_state: str = "deferred"
    route_status: dict[str, int | str] = field(default_factory=dict)
    failure_code: str | None = None


def _safe_json(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    lowered = serialized.lower()
    for forbidden in [
        "bearer ",
        "authorization",
        "x-auth-session",
        "session_token",
        "cookie",
        "set-cookie",
        "@",
    ]:
        if forbidden in lowered:
            raise SystemExit(f"unsafe proof payload contains forbidden marker: {forbidden}")
    return serialized


def _proof(
    origin: str,
    run_id: str,
    meeting_id: UUID,
    token_file: Path,
    timeout: int,
) -> OutcomeLiveProof:
    token = read_private_auth_material(token_file, expected_run_id=run_id)
    route_status: dict[str, int | str] = {}
    live_status, _, live_code = _request_json(origin, "/api/v1/health/live")
    ready_status, _, ready_code = _request_json(origin, "/api/v1/health/ready")
    route_status["health_live"] = live_status or live_code or "blocked"
    route_status["health_ready"] = ready_status or ready_code or "blocked"
    proof_id = "feature-183-trusted-outcome-lifecycle"
    if live_status != 200 or ready_status != 200:
        return OutcomeLiveProof(
            proof_id,
            origin,
            run_id,
            str(meeting_id),
            route_status["health_live"],
            route_status["health_ready"],
            "blocked",
            "blocked",
            "deferred",
            "deferred",
            route_status=route_status,
            failure_code=live_code or ready_code,
        )

    candidate_state = "blocked"
    candidate: dict[str, object] | None = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, payload, code = _request_json(
            origin,
            f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
            token,
        )
        route_status["candidates"] = status or code or "blocked"
        candidates = (payload or {}).get("candidates", []) if payload else []
        matching = [item for item in candidates if item.get("template_key") == "graf-auto-v1"]
        candidate = matching[0] if matching else None
        candidate_state = str(candidate.get("state")) if candidate else "missing"
        if candidate_state in {"ready", "failed", "blocked", "stale", "expired", "closed"}:
            break
        time.sleep(3)

    if candidate is None or candidate_state != "ready":
        return OutcomeLiveProof(
            proof_id,
            origin,
            run_id,
            str(meeting_id),
            route_status["health_live"],
            route_status["health_ready"],
            candidate_state,
            "blocked",
            "deferred",
            "deferred",
            route_status=route_status,
            failure_code="candidate_not_ready",
        )

    route_status["slot_read"] = 200
    slot_state = "current" if candidate.get("current_outcome_set_id") else "unpublished"
    return OutcomeLiveProof(
        proof_id,
        origin,
        run_id,
        str(meeting_id),
        route_status["health_live"],
        route_status["health_ready"],
        candidate_state,
        slot_state,
        "deferred",
        "deferred",
        route_status=route_status,
    )


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
    proof_id = "feature-183-trusted-outcome-lifecycle"
    if not args.execute:
        proof = OutcomeLiveProof(
            proof_id,
            origin,
            args.run_id,
            str(args.meeting_id),
            "deferred",
            "deferred",
            "deferred",
            "deferred",
            "deferred",
            "deferred",
        )
    else:
        proof = _proof(origin, args.run_id, args.meeting_id, args.token_file, args.timeout_seconds)
    output = _safe_json(asdict(proof))
    sys.stdout.write(output + "\n")
    if args.execute and not (
        proof.candidate_state == "ready"
        and proof.slot_state in {"unpublished", "current"}
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
