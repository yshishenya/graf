#!/usr/bin/env python3
import argparse
import json
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

from twobrain_rec_server.config import LOCAL_DEV_SMOKE_IDS, SMOKE_IDENTITY_CLASS


def _validate_smoke_identity(*values: str) -> None:
    identifiers = {UUID(value) for value in values}
    if identifiers & LOCAL_DEV_SMOKE_IDS:
        raise ValueError("smoke upload must not use local development seed identifiers")


class JsonHttpClient:
    def __init__(self, base_url: str, headers: dict[str, str], timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.timeout = timeout

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
        request = Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers=self.headers | {"Content-Type": content_type} | (extra_headers or {}),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with {exc.code}: {detail}") from exc
        return json.loads(body.decode("utf-8")) if body else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--token")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stop-after-parts", type=int)
    parser.add_argument("--smoke-dry-run", action="store_true")
    args = parser.parse_args()

    if args.smoke_dry_run:
        _validate_smoke_identity(args.organization, args.workspace, args.user, args.device)
        print(
            json.dumps(
                {
                    "would_upload": True,
                    "api": args.api,
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
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    files = [
        ("manifest", "manifest.json"),
        ("microphone", "mic.wav"),
        ("system", "incoming.wav"),
    ]
    payloads = {
        role: (args.artifact / filename).read_bytes()
        for role, filename in files
    }
    manifest = json.loads(payloads["manifest"])
    duration_seconds = int(manifest.get("duration_seconds", 60))
    expected_track_sizes = {role: len(data) for role, data in payloads.items()}
    client = JsonHttpClient(base_url=args.api, headers=headers)
    meeting = client.post_json(
        "/api/v1/meetings",
        {"local_recording_id": args.artifact.name, "duration_seconds": duration_seconds},
    )
    meeting_id = meeting["meeting_id"]
    session = client.post_json(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        {
            "expected_tracks": [role for role, _filename in files],
            "expected_track_sizes": expected_track_sizes,
        },
    )
    session_id = session["session_id"]
    uploaded = 0
    tracks = []
    for role, _filename in files:
        data = payloads[role]
        digest = sha256(data).hexdigest()
        client.put_bytes(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            data,
            {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        )
        tracks.append(
            {
                "track_role": role,
                "codec": "pcm_s16le",
                "sample_rate_hz": 48_000,
                "channel_count": 1,
                "duration_seconds": duration_seconds,
                "byte_length": len(data),
                "sha256": digest,
            }
        )
        uploaded += 1
        if args.stop_after_parts and uploaded >= args.stop_after_parts:
            print(json.dumps({"session_id": session_id, "stopped": True}))
            return
    finalized = client.post_json(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        {"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    print(
        json.dumps(
            {
                "meeting_id": meeting_id,
                "session_id": session_id,
                "uploaded_parts": uploaded,
                "meeting_status": finalized["meeting"]["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
