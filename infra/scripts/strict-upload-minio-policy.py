#!/usr/bin/env python3
"""Print one policy for a dedicated strict-upload principal on the GRAF ingest bucket."""

import argparse
import json
from pathlib import Path

PROTECTION = Path(__file__).resolve().parents[1] / "minio/strict-upload-protection.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("writer", "cleaner", "discovery"))
    parser.add_argument("--epoch", type=int, help="irreversibly allocated active generation, writer only")
    args = parser.parse_args()
    if args.role == "writer":
        if args.epoch is None or not 0 < args.epoch <= 2**63 - 1:
            parser.error("writer requires an allocated positive bigint epoch")
    elif args.epoch is not None:
        parser.error("--epoch applies only to the writer")

    protection = json.loads(PROTECTION.read_text())
    objects, bucket = protection["Statement"]
    if args.role == "writer":
        resources = [
            f"{resource.removesuffix('*')}{args.epoch}/*" for resource in objects["Resource"]
        ]
        actions = ["s3:PutObject"]
    elif args.role == "cleaner":
        resources = objects["Resource"]
        actions = ["s3:GetObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
    else:
        resources = bucket["Resource"]
        actions = ["s3:ListBucketMultipartUploads"]
    print(json.dumps({
        "Version": protection["Version"],
        "Statement": [{"Effect": "Allow", "Action": actions, "Resource": resources}],
    }, indent=2))


if __name__ == "__main__":
    main()
