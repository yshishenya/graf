#!/usr/bin/env python3
"""Run a metadata-only read proof for the slot-backed outcome lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
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
    summary_state: str
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


def _summary_result_state(payload: dict[str, object]) -> str:
    catalog_entry = payload.get("catalog_entry")
    if isinstance(catalog_entry, dict):
        return str(catalog_entry.get("result_state") or payload.get("result_state") or "unknown")
    return str(payload.get("result_state") or "unknown")


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

    status, payload, code = _request_json(
        origin,
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1",
        token,
    )
    route_status["summary_read"] = status or code or "blocked"
    if payload is None:
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
            failure_code=code or "summary_read_unavailable",
        )

    summary_state = _summary_result_state(payload)
    slot_state = "current" if payload.get("outcome_set_id") else "unpublished"
    return OutcomeLiveProof(
        proof_id,
        origin,
        run_id,
        str(meeting_id),
        route_status["health_live"],
        route_status["health_ready"],
        summary_state,
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
        proof.summary_state in {"ready", "absent"}
        and proof.slot_state in {"unpublished", "current"}
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
