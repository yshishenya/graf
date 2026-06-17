#!/usr/bin/env python3
"""Produce metadata-safe owner review route evidence.

The script never prints token, cookie, request header, meeting title, transcript,
or private account content. Execute mode uses the token file only in memory and
emits route/status metadata that is safe to copy into the 036 evidence pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib import error, parse, request


@dataclass(slots=True)
class OwnerReviewProof:
    proof_id: str
    target_origin: str
    run_id: str
    auth_method: str
    session_material_committed: bool
    list_state: str
    detail_state: str
    governance_state: str
    cleanup_state: str
    evidence_files: list[str] = field(default_factory=list)
    forbidden_content_scan: str = "pending"
    failure_code: str | None = None
    route_status: dict[str, int | str] = field(default_factory=dict)
    meeting_count_state: str | None = None


def _origin(value: str) -> str:
    parsed = parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("api must be an http(s) origin")
    return f"{parsed.scheme}://{parsed.netloc}"


def _safe_json(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    lowered = serialized.lower()
    for forbidden in ["bearer ", "x-auth-session", "session_token", "cookie", "set-cookie", "/users/", "@"]:
        if forbidden in lowered:
            raise SystemExit(f"unsafe proof payload contains forbidden marker: {forbidden}")
    return serialized


def _request_json(origin: str, path: str, token: str) -> tuple[int, dict[str, Any] | None, str | None]:
    url = f"{origin}{path}"
    req = request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None, None
    except error.HTTPError as exc:
        safe_code = None
        try:
            body = exc.read().decode("utf-8")
            if body:
                safe_code = str((json.loads(body) or {}).get("code") or "")
        except Exception:
            safe_code = None
        return exc.code, None, safe_code or f"http_{exc.code}"
    except error.URLError:
        return 0, None, "network_unavailable"


def build_dry_run_proof(*, origin: str, run_id: str) -> OwnerReviewProof:
    return OwnerReviewProof(
        proof_id="feature-036-owner-review-live",
        target_origin=origin,
        run_id=run_id,
        auth_method="blocked",
        session_material_committed=False,
        list_state="deferred",
        detail_state="deferred",
        governance_state="deferred",
        cleanup_state="not_needed",
        failure_code="dry_run",
        route_status={},
    )


def build_execute_proof(*, origin: str, run_id: str, token_file: Path) -> OwnerReviewProof:
    token = token_file.read_text(encoding="utf-8").strip()
    list_status, list_payload, list_code = _request_json(origin, "/api/v1/cabinet/meetings", token)
    route_status: dict[str, int | str] = {"list": list_status or list_code or "blocked"}
    list_state = "ready" if list_status == 200 else "blocked"
    detail_state = "deferred"
    governance_state = "deferred"
    failure_code = list_code
    meeting_count_state = None

    if list_payload is not None:
        items = list_payload.get("items") or []
        meeting_count_state = "empty" if not items else "non_empty"
        if not items:
            detail_state = "empty"
            governance_state = "deferred"
        else:
            first_id = str(items[0].get("meeting_id") or "")
            if first_id:
                detail_status, detail_payload, detail_code = _request_json(
                    origin,
                    f"/api/v1/cabinet/meetings/{parse.quote(first_id)}",
                    token,
                )
                route_status["detail"] = detail_status or detail_code or "blocked"
                detail_state = "ready" if detail_status == 200 else "blocked"
                governance_state = (
                    "ready"
                    if detail_payload is not None and isinstance(detail_payload.get("governance"), dict)
                    else "blocked"
                )
                failure_code = detail_code

    return OwnerReviewProof(
        proof_id="feature-036-owner-review-live",
        target_origin=origin,
        run_id=run_id,
        auth_method="session_header",
        session_material_committed=False,
        list_state=list_state,
        detail_state=detail_state,
        governance_state=governance_state,
        cleanup_state="deferred",
        failure_code=failure_code,
        route_status=route_status,
        meeting_count_state=meeting_count_state,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Produce metadata-safe owner review route evidence.")
    parser.add_argument("--api", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    origin = _origin(args.api)
    if args.execute and args.dry_run:
        raise SystemExit("choose either --dry-run or --execute")
    if args.execute:
        proof = build_execute_proof(origin=origin, run_id=args.run_id, token_file=args.token_file)
    else:
        proof = build_dry_run_proof(origin=origin, run_id=args.run_id)
    sys.stdout.write(_safe_json(asdict(proof)) + "\n")


if __name__ == "__main__":
    main()
