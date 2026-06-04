#!/usr/bin/env python3
import argparse
import json
from hashlib import sha256
from pathlib import Path


def write_track(path: Path, size: int) -> str:
    data = (b"2brain-rec-test-audio" * ((size // 21) + 1))[:size]
    path.write_bytes(data)
    return sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    mic_sha = write_track(args.out / "mic.wav", 1024)
    incoming_sha = write_track(args.out / "incoming.wav", 1024)
    manifest = {
        "duration_seconds": args.duration_seconds,
        "tracks": [
            {"role": "microphone", "path": "mic.wav", "sha256": mic_sha},
            {"role": "system", "path": "incoming.wav", "sha256": incoming_sha},
        ],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    (args.out / "manifest.json").write_bytes(manifest_bytes)
    print(json.dumps({"manifest_sha256": sha256(manifest_bytes).hexdigest(), "out": str(args.out)}))


if __name__ == "__main__":
    main()
