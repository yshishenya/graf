#!/usr/bin/env python3
import argparse
import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import httpx

try:
    from scripts.create_test_artifact import DESCRIPTORS, FILES, read_package
    from scripts.smoke_target import read_private_auth_material, validate_origin
except ModuleNotFoundError:
    from create_test_artifact import DESCRIPTORS, FILES, read_package
    from smoke_target import read_private_auth_material, validate_origin

from twobrain_rec_server.config import LOCAL_DEV_SMOKE_IDS, SMOKE_IDENTITY_CLASS


def _validate_smoke_identity(*values: str) -> None:
    identifiers = {UUID(value) for value in values}
    if identifiers & LOCAL_DEV_SMOKE_IDS:
        raise ValueError("smoke upload must not use local development seed identifiers")


class JsonHttpClient:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str],
        timeout: int = 30,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.timeout = timeout
        self.transport = transport

    def post_json(self, path: str, payload: dict) -> dict:
        return self._request("POST", path, json.dumps(payload).encode("utf-8"), "application/json")

    def put_bytes(self, path: str, payload: bytes, headers: dict[str, str]) -> dict:
        return self._request("PUT", path, payload, "application/octet-stream", headers)

    def _request(
        self,
        method: str,
        path: str,
        payload: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        # Never forward smoke credentials through an HTTP redirect.
        with httpx.Client(
            transport=self.transport, timeout=self.timeout, follow_redirects=False
        ) as client:
            response = client.request(
                method,
                f"{self.base_url}{path}",
                content=payload,
                headers=self.headers | {"Content-Type": content_type} | (extra_headers or {}),
            )
        if not response.is_success:
            raise RuntimeError(f"{method} {path} failed with {response.status_code}")
        return response.json() if response.content else {}


def upload_package(
    client: JsonHttpClient, artifact: Path, *, stop_after_parts: int | None = None
) -> dict:
    manifest, payloads = read_package(artifact)
    duration_seconds = manifest["duration_seconds"]
    meeting = client.post_json(
        "/api/v1/meetings",
        {
            "local_recording_id": artifact.name,
            "duration_seconds": duration_seconds,
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
        },
    )
    meeting_id = meeting["meeting_id"]
    session = client.post_json(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        {
            "expected_tracks": list(FILES),
            "expected_track_sizes": {role: len(data) for role, data in payloads.items()},
            "manifest_sha256": sha256(payloads["manifest"]).hexdigest(),
        },
    )
    session_id = session["session_id"]
    tracks = []
    for role in FILES:
        data = payloads[role]
        digest = sha256(data).hexdigest()
        client.put_bytes(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            data,
            {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        )
        codec, rate, channels = DESCRIPTORS[role]
        tracks.append(
            {
                "track_role": role,
                "codec": codec,
                "sample_rate_hz": rate,
                "channel_count": channels,
                "duration_seconds": duration_seconds,
                "byte_length": len(data),
                "sha256": digest,
            }
        )
        if stop_after_parts and len(tracks) >= stop_after_parts:
            return {"meeting_id": meeting_id, "session_id": session_id, "stopped": True}
    finalized = client.post_json(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        {"manifest_sha256": sha256(payloads["manifest"]).hexdigest(), "tracks": tracks},
    )
    return {
        "meeting_id": meeting_id,
        "session_id": session_id,
        "media_revision_id": session["media_revision_id"],
        "uploaded_parts": len(tracks),
        "meeting_status": finalized["meeting"]["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--token", help=argparse.SUPPRESS)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stop-after-parts", type=int)
    parser.add_argument("--smoke-dry-run", action="store_true")
    args = parser.parse_args()

    try:
        api_origin = validate_origin(args.api)
    except ValueError as exc:
        parser.error(str(exc))

    if args.token and args.token_file:
        parser.error("--token and --token-file are mutually exclusive")
    if args.token:
        parser.error("--token is not supported; use --token-file")
    if args.token_file and not args.run_id and not args.smoke_dry_run:
        parser.error("--run-id is required with --token-file")

    if args.smoke_dry_run:
        _validate_smoke_identity(args.organization, args.workspace, args.user, args.device)
        print(
            json.dumps(
                {
                    "would_upload": True,
                    "api": api_origin,
                    "artifact_path": str(args.artifact),
                    "smoke_identity_class": SMOKE_IDENTITY_CLASS,
                    "side_effect_assertions": {
                        "mediascribe_jobs_created": 0,
                        "temporal_workflows_started": 0,
                        "notes_jobs_created": 0,
                        "retention_jobs_created": 0,
                        "deletion_jobs_created": 0,
                        "content_bearing_langfuse_traces_created": 0,
                    },
                },
                sort_keys=True,
            )
        )
        return

    headers = {
        "X-Organization-Id": args.organization,
        "X-Workspace-Id": args.workspace,
        "X-User-Id": args.user,
        "X-Device-Id": args.device,
    }
    bearer_token = args.token
    if args.token_file:
        bearer_token = read_private_auth_material(args.token_file, expected_run_id=args.run_id)
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    client = JsonHttpClient(base_url=api_origin, headers=headers)
    print(json.dumps(upload_package(client, args.artifact, stop_after_parts=args.stop_after_parts)))


if __name__ == "__main__":
    main()
