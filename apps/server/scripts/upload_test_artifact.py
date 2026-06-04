#!/usr/bin/env python3
import argparse
import json
from hashlib import sha256
from pathlib import Path

import httpx


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
    args = parser.parse_args()

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
    with httpx.Client(base_url=args.api, headers=headers, timeout=30) as client:
        meeting = client.post(
            "/api/v1/meetings",
            json={"local_recording_id": args.artifact.name, "duration_seconds": duration_seconds},
        )
        meeting.raise_for_status()
        meeting_id = meeting.json()["meeting_id"]
        session = client.post(
            f"/api/v1/meetings/{meeting_id}/upload-sessions",
            json={
                "expected_tracks": [role for role, _filename in files],
                "expected_track_sizes": expected_track_sizes,
            },
        )
        session.raise_for_status()
        session_id = session.json()["session_id"]
        uploaded = 0
        tracks = []
        for role, _filename in files:
            data = payloads[role]
            digest = sha256(data).hexdigest()
            response = client.put(
                f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
                headers={"X-Byte-Offset": "0", "X-Content-SHA256": digest},
                content=data,
            )
            response.raise_for_status()
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
        finalized = client.post(
            f"/api/v1/upload-sessions/{session_id}/finalize",
            json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
        )
        finalized.raise_for_status()
        print(
            json.dumps(
                {
                    "meeting_id": meeting_id,
                    "session_id": session_id,
                    "uploaded_parts": uploaded,
                    "meeting_status": finalized.json()["meeting"]["status"],
                }
            )
        )


if __name__ == "__main__":
    main()
