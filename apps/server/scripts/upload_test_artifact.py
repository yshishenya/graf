#!/usr/bin/env python3
import argparse
import json
from hashlib import sha256
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stop-after-parts", type=int)
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Organization-Id": args.workspace,
        "X-Workspace-Id": args.workspace,
        "X-User-Id": args.workspace,
        "X-Device-Id": args.device,
    }
    with httpx.Client(base_url=args.api, headers=headers, timeout=30) as client:
        meeting = client.post(
            "/api/v1/meetings",
            json={"local_recording_id": args.artifact.name, "duration_seconds": 60},
        )
        meeting.raise_for_status()
        meeting_id = meeting.json()["meeting_id"]
        session = client.post(f"/api/v1/meetings/{meeting_id}/upload-sessions", json={})
        session.raise_for_status()
        session_id = session.json()["session_id"]
        uploaded = 0
        for role, filename in [("manifest", "manifest.json"), ("microphone", "mic.wav"), ("system", "incoming.wav")]:
            data = (args.artifact / filename).read_bytes()
            response = client.put(
                f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
                headers={"X-Byte-Offset": "0", "X-Content-SHA256": sha256(data).hexdigest()},
                content=data,
            )
            response.raise_for_status()
            uploaded += 1
            if args.stop_after_parts and uploaded >= args.stop_after_parts:
                print(json.dumps({"session_id": session_id, "stopped": True}))
                return
        print(json.dumps({"session_id": session_id, "uploaded_parts": uploaded}))


if __name__ == "__main__":
    main()
